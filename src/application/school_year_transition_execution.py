"""Atomic execution of one fully resolved transient school-year plan.

This isolated service owns the password-authorized maintenance request,
maintenance activation, verified backup, source revalidation, atomic
transition, and controlled gate release.  It remains intentionally unwired
from Qt or the product shell.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
import sqlite3
from typing import Protocol

from src.application.commands.school_year_transition_backup import (
    SchoolYearTransitionBackupEvidence,
)
from src.application.school_year_transition_plan import (
    SchoolYearTransitionCourseDecision,
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanTargetStatus,
    school_year_transition_plan_sha256,
)
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpAuthorization,
    SchoolYearTransitionStepUpError,
    SchoolYearTransitionStepUpService,
)
from src.core.school_year import (
    StudentAssignmentStatus,
    StudentMembershipAssignment,
)
from src.core.maintenance_gate import (
    MaintenanceCapability,
    MaintenanceCapabilityError,
    MaintenanceGate,
    MaintenanceGateError,
    MaintenancePurpose,
    MaintenanceState,
)
from src.core.database_compatibility import FINAL_SCHEMA_FINGERPRINT
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
    SchoolYearTransitionRepositoryError,
    StoredSchoolYearTransition,
)


ConnectionFactory = Callable[[], sqlite3.Connection]
TimestampProvider = Callable[[], datetime]
ProgressCallback = Callable[[str], None]


class SchoolYearTransitionExecutionError(RuntimeError):
    """Sanitized fail-closed execution failure with a stable technical code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionExecutionCounts:
    student_count: int
    enrolled_count: int
    exited_count: int
    advance_1_to_2_count: int
    advance_2_to_3_count: int
    other_course_count: int
    repeat_year_level_three_count: int
    group_change_count: int


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionExecutionResult:
    transition_id: str
    from_school_year_id: str
    to_school_year_id: str
    operation_token: str
    plan_sha256: str
    backup_sha256: str
    counts: SchoolYearTransitionExecutionCounts
    completed_at: datetime


class _ExecutionRepository(Protocol):
    def source_sha256(self) -> str: ...

    def find_by_operation_token(
        self, operation_token: str
    ) -> StoredSchoolYearTransition | None: ...

    def find_by_target_school_year_id(
        self, school_year_id: str
    ) -> StoredSchoolYearTransition | None: ...


RepositoryFactory = Callable[[sqlite3.Connection], _ExecutionRepository]


class _TransitionBackupService(Protocol):
    def create_and_verify(self) -> SchoolYearTransitionBackupEvidence: ...


class ExecuteSchoolYearTransition:
    """Execute one source-bound plan in exactly one immediate transaction."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        maintenance_gate: MaintenanceGate,
        step_up_service: SchoolYearTransitionStepUpService,
        backup_service: _TransitionBackupService | None,
        now_provider: TimestampProvider | None = None,
        repository_factory: RepositoryFactory | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._maintenance_gate = maintenance_gate
        self._step_up_service = step_up_service
        self._backup_service = backup_service
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._repository_factory = (
            repository_factory or SchoolYearTransitionExecutionRepository
        )

    def execute(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        operation_token: str,
        expected_plan_sha256: str,
        step_up_authorization: SchoolYearTransitionStepUpAuthorization,
        maintenance_owner_id: str,
        progress_callback: ProgressCallback | None = None,
    ) -> SchoolYearTransitionExecutionResult:
        owns_maintenance = False
        maintenance_capability: MaintenanceCapability | None = None
        try:
            token = _require_identifier(
                operation_token,
                "transition_operation_token_invalid",
            )
            expected_hash = _require_sha256(
                expected_plan_sha256,
                "transition_expected_plan_sha256_invalid",
            )
            _validate_executable_plan(plan)
            plan_hash = school_year_transition_plan_sha256(plan)
            if plan_hash != expected_hash:
                raise SchoolYearTransitionExecutionError(
                    "transition_plan_sha256_mismatch"
                )
            target_id = _target_school_year_id(plan)
            self._step_up_service.consume(
                step_up_authorization,
                plan=plan,
                purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
            )
            _report_progress(progress_callback, "writers_draining")
            maintenance_capability = self._maintenance_gate.request_maintenance(
                owner_id=maintenance_owner_id,
                purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
            )
            owns_maintenance = True
            if not self._maintenance_gate.activate(
                maintenance_capability,
                owner_id=maintenance_owner_id,
            ):
                raise SchoolYearTransitionExecutionError(
                    "transition_writers_not_drained"
                )
            with self._maintenance_gate.exclusive_writer(
                maintenance_capability,
                owner_id=maintenance_owner_id,
                purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
            ):
                existing = self._read_existing_receipt(
                    token=token,
                    plan_hash=plan_hash,
                    target_id=target_id,
                )
                if existing is not None:
                    result = _result_from_stored(existing)
                else:
                    result = self._execute_new_transition(
                        plan=plan,
                        token=token,
                        plan_hash=plan_hash,
                        expected_hash=expected_hash,
                        target_id=target_id,
                        progress_callback=progress_callback,
                    )
            self._release_maintenance(
                maintenance_capability,
                maintenance_owner_id,
            )
            owns_maintenance = False
            return result
        except SchoolYearTransitionStepUpError as error:
            raise SchoolYearTransitionExecutionError(error.code) from None
        except MaintenanceCapabilityError as error:
            if self._maintenance_gate.state is MaintenanceState.RECOVERY_REQUIRED:
                raise SchoolYearTransitionExecutionError(
                    "transition_recovery_required"
                ) from None
            raise SchoolYearTransitionExecutionError(error.code) from None
        except MaintenanceGateError:
            self._maintenance_gate.mark_recovery_required()
            raise SchoolYearTransitionExecutionError(
                "transition_recovery_required"
            ) from None
        finally:
            self._step_up_service.discard(step_up_authorization)
            if (
                owns_maintenance
                and maintenance_capability is not None
                and self._maintenance_gate.state in {
                    MaintenanceState.MAINTENANCE_PENDING,
                    MaintenanceState.MAINTENANCE_ACTIVE,
                }
            ):
                self._release_maintenance(
                    maintenance_capability,
                    maintenance_owner_id,
                )

    def _execute_new_transition(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        token: str,
        plan_hash: str,
        expected_hash: str,
        target_id: str,
        progress_callback: ProgressCallback | None,
    ) -> SchoolYearTransitionExecutionResult:
        source_state_sha256 = self._read_source_state()
        if source_state_sha256 != plan.source_sha256:
            raise SchoolYearTransitionExecutionError(
                "transition_sources_changed"
            )
        _report_progress(progress_callback, "backup_creating")
        evidence = self._create_backup_evidence()
        _validate_backup_evidence(
            evidence,
            expected_source_state_sha256=source_state_sha256,
            validated_at=self._now_provider(),
        )
        if school_year_transition_plan_sha256(plan) != expected_hash:
            raise SchoolYearTransitionExecutionError(
                "transition_plan_sha256_mismatch"
            )
        _report_progress(progress_callback, "assignments_checking")
        return self._execute_authorized(
            plan=plan,
            token=token,
            plan_hash=plan_hash,
            expected_hash=expected_hash,
            target_id=target_id,
            backup_evidence=evidence,
            progress_callback=progress_callback,
        )

    def _read_existing_receipt(
        self,
        *,
        token: str,
        plan_hash: str,
        target_id: str,
    ) -> StoredSchoolYearTransition | None:
        connection = self._connection_factory()
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            repository = self._repository_factory(connection)
            existing = repository.find_by_operation_token(token)
            if existing is not None:
                if (
                    existing.plan_sha256 == plan_hash
                    and existing.to_school_year_id == target_id
                ):
                    return existing
                raise SchoolYearTransitionExecutionError(
                    "transition_operation_token_conflict"
                )
            if repository.find_by_target_school_year_id(target_id) is not None:
                raise SchoolYearTransitionExecutionError(
                    "transition_target_school_year_conflict"
                )
            return None
        except SchoolYearTransitionExecutionError:
            raise
        except (sqlite3.Error, ValueError, TypeError):
            raise SchoolYearTransitionExecutionError(
                "transition_receipt_read_failed"
            ) from None
        finally:
            try:
                connection.close()
            except sqlite3.Error:
                raise SchoolYearTransitionExecutionError(
                    "transition_receipt_read_failed"
                ) from None

    def _read_source_state(self) -> str:
        connection = self._connection_factory()
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            return self._repository_factory(connection).source_sha256()
        except (sqlite3.Error, ValueError, TypeError):
            raise SchoolYearTransitionExecutionError(
                "transition_source_read_failed"
            ) from None
        finally:
            try:
                connection.close()
            except sqlite3.Error:
                raise SchoolYearTransitionExecutionError(
                    "transition_source_read_failed"
                ) from None

    def _create_backup_evidence(
        self,
    ) -> SchoolYearTransitionBackupEvidence:
        if self._backup_service is None:
            raise SchoolYearTransitionExecutionError(
                "transition_backup_evidence_missing"
            )
        try:
            evidence = self._backup_service.create_and_verify()
        except SchoolYearTransitionExecutionError:
            raise
        except Exception:
            raise SchoolYearTransitionExecutionError(
                "transition_backup_failed"
            ) from None
        if evidence is None:
            raise SchoolYearTransitionExecutionError(
                "transition_backup_evidence_missing"
            )
        return evidence

    def _release_maintenance(
        self,
        capability: MaintenanceCapability,
        owner_id: str,
    ) -> None:
        try:
            self._maintenance_gate.abort(capability, owner_id=owner_id)
        except MaintenanceGateError:
            self._maintenance_gate.mark_recovery_required()
            raise SchoolYearTransitionExecutionError(
                "transition_recovery_required"
            ) from None

    def _execute_authorized(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        token: str,
        plan_hash: str,
        expected_hash: str,
        target_id: str,
        backup_evidence: SchoolYearTransitionBackupEvidence,
        progress_callback: ProgressCallback | None,
    ) -> SchoolYearTransitionExecutionResult:
        connection = self._connection_factory()
        commit_attempted = False
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            repository = self._repository_factory(connection)

            existing = repository.find_by_operation_token(token)
            if existing is not None:
                if (
                    existing.plan_sha256 == plan_hash
                    and existing.to_school_year_id == target_id
                    and existing.backup_sha256
                    == backup_evidence.backup_sha256
                ):
                    connection.rollback()
                    return _result_from_stored(existing)
                raise SchoolYearTransitionExecutionError(
                    "transition_operation_token_conflict"
                )

            target_receipt = repository.find_by_target_school_year_id(target_id)
            if target_receipt is not None:
                raise SchoolYearTransitionExecutionError(
                    "transition_target_school_year_conflict"
                )

            _revalidate_sources(
                repository=repository,
                plan=plan,
                target_school_year_id=target_id,
            )
            if repository.source_sha256() != (
                backup_evidence.source_state_sha256
            ):
                raise SchoolYearTransitionExecutionError(
                    "transition_backup_source_state_mismatch"
                )
            if school_year_transition_plan_sha256(plan) != expected_hash:
                raise SchoolYearTransitionExecutionError(
                    "transition_plan_sha256_mismatch"
                )

            _report_progress(progress_callback, "school_year_activating")
            completed_at = _require_timestamp(self._now_provider())
            counts = _execution_counts(plan)
            result_counts_json = _counts_json(counts)
            repository.close_current_school_year(
                plan.current_school_year_id,
                completed_at,
            )
            repository.insert_current_school_year(
                school_year_id=target_id,
                label=plan.planned_school_year_label.strip(),
                start_date=plan.planned_school_year_start_date,
                end_date=plan.planned_school_year_end_date,
                created_at=completed_at,
            )
            for item in plan.items:
                status = (
                    StudentAssignmentStatus.EXITED
                    if item.target_status
                    is SchoolYearTransitionPlanTargetStatus.EXITED
                    else StudentAssignmentStatus.ENROLLED
                )
                repository.insert_assignment(
                    assignment_id=_assignment_id(token, item.student_id),
                    assignment=StudentMembershipAssignment(
                        student_id=item.student_id,
                        school_year_id=target_id,
                        group_id=item.target_group_id,
                        course_id=item.target_course_id,
                        assignment_status=status,
                        valid_from=plan.planned_school_year_start_date,
                        valid_to=plan.planned_school_year_end_date,
                    ),
                    created_at=completed_at,
                )
            stored = repository.insert_transition(
                transition_id=_transition_id(token),
                from_school_year_id=plan.current_school_year_id,
                to_school_year_id=target_id,
                operation_token=token,
                plan_sha256=plan_hash,
                backup_sha256=backup_evidence.backup_sha256,
                result_counts_json=result_counts_json,
                completed_at=completed_at,
            )
            _report_progress(progress_callback, "completion_checking")
            repository.verify_written_result(
                from_school_year_id=plan.current_school_year_id,
                to_school_year_id=target_id,
                expected_student_ids=tuple(
                    item.student_id for item in plan.items
                ),
                expected_enrolled_count=counts.enrolled_count,
                expected_exited_count=counts.exited_count,
                operation_token=token,
            )
            result = _result_from_stored(stored)
            commit_attempted = True
            connection.commit()
            commit_attempted = False
            return result
        except SchoolYearTransitionExecutionError:
            self._rollback_or_recovery(connection, commit_attempted)
            raise
        except SchoolYearTransitionRepositoryError as error:
            self._rollback_or_recovery(connection, commit_attempted)
            raise SchoolYearTransitionExecutionError(error.code) from None
        except (sqlite3.Error, ValueError, TypeError):
            self._rollback_or_recovery(connection, commit_attempted)
            if self._maintenance_gate.state is MaintenanceState.RECOVERY_REQUIRED:
                raise SchoolYearTransitionExecutionError(
                    "transition_recovery_required"
                ) from None
            raise SchoolYearTransitionExecutionError(
                "transition_execution_failed"
            ) from None
        finally:
            try:
                connection.close()
            except sqlite3.Error:
                self._maintenance_gate.mark_recovery_required()
                raise SchoolYearTransitionExecutionError(
                    "transition_recovery_required"
                ) from None

    def _rollback_or_recovery(
        self,
        connection: sqlite3.Connection,
        commit_attempted: bool,
    ) -> None:
        if commit_attempted:
            self._maintenance_gate.mark_recovery_required()
            return
        if not connection.in_transaction:
            return
        try:
            connection.rollback()
        except sqlite3.Error:
            self._maintenance_gate.mark_recovery_required()


def _report_progress(
    callback: ProgressCallback | None,
    phase: str,
) -> None:
    if callback is not None:
        callback(phase)


def _validate_executable_plan(plan: SchoolYearTransitionPlan) -> None:
    if not isinstance(plan, SchoolYearTransitionPlan):
        raise SchoolYearTransitionExecutionError("transition_plan_invalid")
    validation = plan.validate()
    if not validation.complete or any(
        not item.resolved for item in plan.items
    ):
        raise SchoolYearTransitionExecutionError(
            "transition_plan_not_fully_resolved"
        )
    if len({item.student_id for item in plan.items}) != len(plan.items):
        raise SchoolYearTransitionExecutionError(
            "transition_plan_student_duplicate"
        )
    _require_identifier(
        plan.current_school_year_id,
        "transition_current_school_year_missing",
    )
    _require_identifier(
        plan.current_school_year_label,
        "transition_current_school_year_invalid",
    )
    _require_identifier(
        plan.planned_school_year_label,
        "transition_target_school_year_invalid",
    )
    if (
        not isinstance(plan.planned_school_year_start_date, date)
        or isinstance(plan.planned_school_year_start_date, datetime)
        or not isinstance(plan.planned_school_year_end_date, date)
        or isinstance(plan.planned_school_year_end_date, datetime)
        or plan.planned_school_year_start_date
        > plan.planned_school_year_end_date
    ):
        raise SchoolYearTransitionExecutionError(
            "transition_target_school_year_dates_invalid"
        )
    _require_sha256(
        plan.source_sha256,
        "transition_source_sha256_missing",
    )
    for item in plan.items:
        _require_identifier(
            item.student_id,
            "transition_plan_student_invalid",
        )
        if item.target_status is SchoolYearTransitionPlanTargetStatus.EXITED:
            if (
                item.target_group_id is not None
                or item.target_course_id is not None
                or item.course_decision
                is not SchoolYearTransitionCourseDecision.EXITED
            ):
                raise SchoolYearTransitionExecutionError(
                    "transition_exited_assignment_invalid"
                )
        else:
            _require_identifier(
                item.target_group_id,
                "transition_target_group_missing",
            )
            _require_identifier(
                item.target_course_id,
                "transition_target_course_missing",
            )
        if (
            item.original_current_year_level == 3
            and item.course_decision
            in {
                SchoolYearTransitionCourseDecision.UNCHANGED,
                SchoolYearTransitionCourseDecision.ACCEPT_PROPOSAL,
                SchoolYearTransitionCourseDecision.LEAVE_UNRESOLVED,
            }
        ):
            raise SchoolYearTransitionExecutionError(
                "transition_year_level_three_decision_required"
            )


def _revalidate_sources(
    *,
    repository: _ExecutionRepository,
    plan: SchoolYearTransitionPlan,
    target_school_year_id: str,
) -> None:
    if repository.source_sha256() != plan.source_sha256:
        raise SchoolYearTransitionExecutionError(
            "transition_sources_changed"
        )
    current = repository.current_school_year()
    if (
        current is None
        or current.school_year_id != plan.current_school_year_id
        or current.label != plan.current_school_year_label
    ):
        raise SchoolYearTransitionExecutionError(
            "transition_current_school_year_changed"
        )
    if repository.target_school_year_exists(
        school_year_id=target_school_year_id,
        label=plan.planned_school_year_label.strip(),
        start_date=plan.planned_school_year_start_date,
        end_date=plan.planned_school_year_end_date,
    ):
        raise SchoolYearTransitionExecutionError(
            "transition_target_school_year_changed"
        )
    repository.validate_active_references(
        group_ids=tuple(
            sorted(
                {
                    item.target_group_id
                    for item in plan.items
                    if item.target_group_id is not None
                }
            )
        ),
        course_ids=tuple(
            sorted(
                {
                    item.target_course_id
                    for item in plan.items
                    if item.target_course_id is not None
                }
            )
        ),
    )


def _execution_counts(
    plan: SchoolYearTransitionPlan,
) -> SchoolYearTransitionExecutionCounts:
    validation = plan.validate()
    plan_counts = validation.counts
    return SchoolYearTransitionExecutionCounts(
        student_count=plan_counts.student_count,
        enrolled_count=(
            plan_counts.student_count - plan_counts.exited_count
        ),
        exited_count=plan_counts.exited_count,
        advance_1_to_2_count=plan_counts.advance_1_to_2_count,
        advance_2_to_3_count=plan_counts.advance_2_to_3_count,
        other_course_count=plan_counts.other_course_count,
        repeat_year_level_three_count=(
            plan_counts.repeat_year_level_three_count
        ),
        group_change_count=sum(
            item.target_status
            is not SchoolYearTransitionPlanTargetStatus.EXITED
            and item.target_group_id != item.current_group_id
            for item in plan.items
        ),
    )


def _counts_json(counts: SchoolYearTransitionExecutionCounts) -> str:
    return json.dumps(
        {
            "advance_1_to_2_count": counts.advance_1_to_2_count,
            "advance_2_to_3_count": counts.advance_2_to_3_count,
            "enrolled_count": counts.enrolled_count,
            "exited_count": counts.exited_count,
            "group_change_count": counts.group_change_count,
            "other_course_count": counts.other_course_count,
            "repeat_year_level_three_count": (
                counts.repeat_year_level_three_count
            ),
            "student_count": counts.student_count,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _result_from_stored(
    stored: StoredSchoolYearTransition,
) -> SchoolYearTransitionExecutionResult:
    try:
        values = json.loads(stored.result_counts_json)
        counts = SchoolYearTransitionExecutionCounts(
            student_count=int(values["student_count"]),
            enrolled_count=int(values["enrolled_count"]),
            exited_count=int(values["exited_count"]),
            advance_1_to_2_count=int(values["advance_1_to_2_count"]),
            advance_2_to_3_count=int(values["advance_2_to_3_count"]),
            other_course_count=int(values["other_course_count"]),
            repeat_year_level_three_count=int(
                values["repeat_year_level_three_count"]
            ),
            group_change_count=int(values["group_change_count"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise SchoolYearTransitionExecutionError(
            "transition_receipt_invalid"
        ) from None
    return SchoolYearTransitionExecutionResult(
        transition_id=stored.transition_id,
        from_school_year_id=stored.from_school_year_id,
        to_school_year_id=stored.to_school_year_id,
        operation_token=stored.operation_token,
        plan_sha256=stored.plan_sha256,
        backup_sha256=_require_real_backup_sha256(stored.backup_sha256),
        counts=counts,
        completed_at=stored.completed_at,
    )


def _target_school_year_id(plan: SchoolYearTransitionPlan) -> str:
    identity = json.dumps(
        {
            "label": plan.planned_school_year_label.strip(),
            "start_date": plan.planned_school_year_start_date.isoformat(),
            "end_date": plan.planned_school_year_end_date.isoformat(),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"SY-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"


def _transition_id(operation_token: str) -> str:
    value = hashlib.sha256(
        f"transition:{operation_token}".encode("utf-8")
    ).hexdigest()
    return f"SYT-{value[:32]}"


def _assignment_id(operation_token: str, student_id: str) -> str:
    value = hashlib.sha256(
        f"assignment:{operation_token}:{student_id}".encode("utf-8")
    ).hexdigest()
    return f"ASG-{value[:32]}"


def _require_identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchoolYearTransitionExecutionError(code)
    return value


def _require_sha256(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SchoolYearTransitionExecutionError(code)
    return value


def _require_real_backup_sha256(value: object) -> str:
    result = _require_sha256(value, "transition_backup_sha256_invalid")
    if result == "0" * 64:
        raise SchoolYearTransitionExecutionError(
            "transition_backup_sha256_invalid"
        )
    return result


def _validate_backup_evidence(
    evidence: object,
    *,
    expected_source_state_sha256: str,
    validated_at: datetime,
) -> None:
    if not isinstance(evidence, SchoolYearTransitionBackupEvidence):
        raise SchoolYearTransitionExecutionError(
            "transition_backup_evidence_invalid"
        )
    backup_id = evidence.backup_id
    if (
        not isinstance(backup_id, str)
        or not backup_id.startswith("SYB-")
        or len(backup_id) != 36
        or any(character not in "0123456789abcdef" for character in backup_id[4:])
    ):
        raise SchoolYearTransitionExecutionError(
            "transition_backup_id_invalid"
        )
    _require_real_backup_sha256(evidence.backup_sha256)
    _require_sha256(
        evidence.source_state_sha256,
        "transition_backup_source_state_invalid",
    )
    if evidence.source_state_sha256 != expected_source_state_sha256:
        raise SchoolYearTransitionExecutionError(
            "transition_backup_source_state_mismatch"
        )
    _require_sha256(
        evidence.source_schema_fingerprint,
        "transition_backup_schema_fingerprint_invalid",
    )
    if evidence.source_schema_fingerprint != FINAL_SCHEMA_FINGERPRINT:
        raise SchoolYearTransitionExecutionError(
            "transition_backup_schema_fingerprint_mismatch"
        )
    verified_at = _require_evidence_timestamp(evidence.verified_at)
    validation_time = _require_timestamp(validated_at)
    if verified_at > validation_time:
        raise SchoolYearTransitionExecutionError(
            "transition_backup_verified_at_invalid"
        )


def _require_evidence_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SchoolYearTransitionExecutionError(
            "transition_backup_verified_at_invalid"
        )
    return value.astimezone(UTC)


def _require_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SchoolYearTransitionExecutionError(
            "transition_completed_at_invalid"
        )
    return value
