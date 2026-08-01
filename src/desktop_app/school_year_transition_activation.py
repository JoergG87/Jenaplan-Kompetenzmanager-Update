"""Threaded desktop boundary for one confirmed school-year activation."""

from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Protocol

from PySide6.QtCore import QObject, QThread, Signal, Slot

from src.application.school_year_transition_execution import (
    ExecuteSchoolYearTransition,
    SchoolYearTransitionExecutionError,
    SchoolYearTransitionExecutionResult,
)
from src.application.school_year_transition_plan import (
    SchoolYearTransitionPlan,
    school_year_transition_plan_sha256,
)
from src.application.school_year_transition_step_up import (
    SchoolYearTransitionStepUpService,
)
from src.security.domain import AuthenticationStatus


class _TransitionExecutor(Protocol):
    def execute(self, **kwargs: object) -> SchoolYearTransitionExecutionResult: ...


@dataclass(frozen=True, slots=True)
class SchoolYearTransitionActivationErrorInfo:
    """Privacy-minimized failure passed back to the main thread."""

    code: str
    retry_after_seconds: int = 0


class SchoolYearTransitionActivationWorker(QObject):
    """Authenticate and invoke the existing executor away from Qt widgets."""

    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(
        self,
        *,
        plan: SchoolYearTransitionPlan,
        password: str,
        step_up_service: SchoolYearTransitionStepUpService,
        executor: _TransitionExecutor,
    ) -> None:
        super().__init__()
        self.plan = plan
        self.password = password
        self.step_up_service = step_up_service
        self.executor = executor

    @Slot()
    def run(self) -> None:
        try:
            authentication = self.step_up_service.authenticate(
                plan=self.plan,
                password=self.password,
            )
            self.password = ""
            if authentication.status is not AuthenticationStatus.AUTHENTICATED:
                self.failed.emit(
                    SchoolYearTransitionActivationErrorInfo(
                        _authentication_error_code(authentication.status),
                        authentication.retry_after_seconds,
                    )
                )
                return
            if authentication.authorization is None:
                self.failed.emit(
                    SchoolYearTransitionActivationErrorInfo(
                        "password_check_unavailable"
                    )
                )
                return
            result = self.executor.execute(
                plan=self.plan,
                operation_token=f"SYOP-{secrets.token_hex(16)}",
                expected_plan_sha256=school_year_transition_plan_sha256(
                    self.plan
                ),
                step_up_authorization=authentication.authorization,
                maintenance_owner_id=f"SYOWNER-{secrets.token_hex(16)}",
                progress_callback=self.progress.emit,
            )
        except SchoolYearTransitionExecutionError as error:
            self.failed.emit(
                SchoolYearTransitionActivationErrorInfo(error.code)
            )
        except Exception:
            self.failed.emit(
                SchoolYearTransitionActivationErrorInfo(
                    "transition_execution_failed"
                )
            )
        else:
            self.succeeded.emit(result)
        finally:
            self.password = ""
            self.finished.emit()


class SchoolYearTransitionActivationController(QObject):
    """Own exactly one transition worker until its thread has terminated."""

    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(
        self,
        *,
        step_up_service: SchoolYearTransitionStepUpService,
        executor: ExecuteSchoolYearTransition,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.step_up_service = step_up_service
        self.executor = executor
        self._thread: QThread | None = None
        self._worker: SchoolYearTransitionActivationWorker | None = None
        self._terminal_result: object | None = None
        self._terminal_error: object | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def start(self, *, plan: SchoolYearTransitionPlan, password: str) -> bool:
        if self.is_busy:
            return False
        self._terminal_result = None
        self._terminal_error = None
        thread = QThread(self)
        worker = SchoolYearTransitionActivationWorker(
            plan=plan,
            password=password,
            step_up_service=self.step_up_service,
            executor=self.executor,
        )
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress.emit)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.start()
        return True

    @Slot(object)
    def _on_succeeded(self, result: object) -> None:
        if self._terminal_result is None and self._terminal_error is None:
            self._terminal_result = result

    @Slot(object)
    def _on_failed(self, error: object) -> None:
        if self._terminal_result is None and self._terminal_error is None:
            self._terminal_error = error

    @Slot()
    def _on_thread_finished(self) -> None:
        thread = self._thread
        result = self._terminal_result
        error = self._terminal_error
        if thread is not None:
            thread.wait()
            thread.deleteLater()
        self._thread = None
        self._worker = None
        self._terminal_result = None
        self._terminal_error = None
        if error is not None:
            self.failed.emit(error)
        elif result is not None:
            self.succeeded.emit(result)
        else:
            self.failed.emit(
                SchoolYearTransitionActivationErrorInfo(
                    "transition_execution_failed"
                )
            )
        self.finished.emit()


def _authentication_error_code(status: AuthenticationStatus) -> str:
    if status is AuthenticationStatus.INVALID_CREDENTIALS:
        return "password_invalid"
    if status is AuthenticationStatus.THROTTLED:
        return "password_throttled"
    return "password_check_unavailable"
