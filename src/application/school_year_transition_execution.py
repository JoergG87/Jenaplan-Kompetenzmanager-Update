"""Atomic execution of one fully resolved transient school-year plan.

This isolated service requires an ACTIVE school-year maintenance capability
but remains intentionally unwired from Qt, the product shell, authentication,
or backup orchestration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import json
import sqlite3
from typing import Protocol

from src.application.school_year_transition_plan import (
    SchoolYearTransitionCourseDecision,
    SchoolYearTransitionPlan,
    SchoolYearTransitionPlanTargetStatus,
    school_year_transition_plan_sha256,
)
from src.core.school_year import (
    StudentAssignmentStatus,
    StudentMembershipAssignment,
)
from src.core.maintenance_gate import (
    MaintenanceCapability,
    MaintenanceCapabilityError,
    MaintenanceGate,
    MaintenancePurpose,
)
from src.core.sqlite_school_year_transition import (
    SchoolYearTransitionExecutionRepository,
    SchoolYearTransitionRepositoryError,
    StoredSchoolYearTransition,
)


ConnectionFactory = Callable[[], sqlite3.Connection]
TimestampProvider = Callable[[], datetime]


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


class ExecuteSchoolYearTransition:
    """Execute one source-bound plan in exactly one immediate transaction."""

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        maintenance_gate: MaintenanceGate,
        now_provider: TimestampProvider | None = None,
        repository_factory: RepositoryFactory | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._maintenance_gate = maintenance_gate
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
        maintenance_capability: MaintenanceCapability,
        maintenance_owner_id: str,
    ) -> SchoolYearTransitionExecutionResult:
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

        try:
            with self._maintenance_gate.exclusive_writer(
                maintenance_capability,
                owner_id=maintenance_owner_id,
                purpose=MaintenancePurpose.SCHOOL_YEAR_TRANSITION,
            ):
                return self._execute_authorized(
                    plan=plan,
                    token=token,
                    plan_hash=plan_hash,
                    expected_hash=expected_hash,
                    target_id=target_id,
                )
        except MaintenanceCapabilityError as error:
            raise SchoolYearTransitionExecutionError(error.code) from None

    def _execute_authorized(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        token: str,
        plan_hash: str,
        expected_hash: str,
        target_id: str,
    ) -> SchoolYearTransitionExecutionResult:
        connection = self._connection_factory()
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
            if school_year_transition_plan_sha256(plan) != expected_hash:
                raise SchoolYearTransitionExecutionError(
                    "transition_plan_sha256_mismatch"
                )

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
                result_counts_json=result_counts_json,
                completed_at=completed_at,
            )
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
            connection.commit()
            return _result_from_stored(stored)
        except SchoolYearTransitionExecutionError:
            if connection.in_transaction:
                connection.rollback()
            raise
        except SchoolYearTransitionRepositoryError as error:
            if connection.in_transaction:
                connection.rollback()
            raise SchoolYearTransitionExecutionError(error.code) from None
        except (sqlite3.Error, ValueError, TypeError):
            if connection.in_transaction:
                connection.rollback()
            raise SchoolYearTransitionExecutionError(
                "transition_execution_failed"
            ) from None
        finally:
            connection.close()


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


def _require_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SchoolYearTransitionExecutionError(
            "transition_completed_at_invalid"
        )
    return value
