"""Local first-steps onboarding state without domain ownership."""

from __future__ import annotations

from dataclasses import dataclass, replace

from src.core.app_preferences import (
    AppPreferences,
    AppPreferencesError,
    AppPreferencesFile,
    ONBOARDING_STEP_COUNT,
    OnboardingStatus,
)


@dataclass(frozen=True)
class OnboardingSession:
    """Current visible onboarding position and persistence mode."""

    current_step: int
    status: OnboardingStatus
    manual_preview: bool = False


class OnboardingController:
    """Persist and resume the local orientation flow through AppPreferences."""

    def __init__(
        self,
        preferences_file: AppPreferencesFile,
        *,
        preferences: AppPreferences | None = None,
        step_count: int = 5,
    ) -> None:
        self.preferences_file = preferences_file
        self.preferences = preferences if preferences is not None else self._load()
        if not 1 <= int(step_count) <= ONBOARDING_STEP_COUNT:
            raise ValueError("onboarding_step_count_invalid")
        self.step_count = int(step_count)
        self.session: OnboardingSession | None = None

    def should_open_automatically(self, *, packaged_smoke: bool = False) -> bool:
        if packaged_smoke:
            return False
        return self.preferences.onboarding_status in {
            OnboardingStatus.NOT_STARTED,
            OnboardingStatus.IN_PROGRESS,
        }

    def start(self, *, manual: bool = False) -> OnboardingSession:
        status = self.preferences.onboarding_status
        manual_preview = manual and status in {
            OnboardingStatus.COMPLETED,
            OnboardingStatus.DISMISSED,
        }
        if status is OnboardingStatus.IN_PROGRESS:
            step = self._bounded_step(self.preferences.onboarding_current_step)
        else:
            step = 0
        if not manual_preview and status is not OnboardingStatus.IN_PROGRESS:
            self._save(
                replace(
                    self.preferences,
                    onboarding_status=OnboardingStatus.IN_PROGRESS,
                    onboarding_current_step=step,
                )
            )
            status = OnboardingStatus.IN_PROGRESS
        self.session = OnboardingSession(step, status, manual_preview)
        return self.session

    def set_step(self, step: int) -> OnboardingSession:
        step = self._bounded_step(step)
        self._ensure_in_progress(step)
        assert self.session is not None
        return self.session

    def next_step(self) -> OnboardingSession:
        session = self.session or self.start(manual=True)
        return self.set_step(min(session.current_step + 1, self.step_count - 1))

    def previous_step(self) -> OnboardingSession:
        session = self.session or self.start(manual=True)
        return self.set_step(max(session.current_step - 1, 0))

    def mark_navigation(self) -> OnboardingSession:
        session = self.session or self.start(manual=True)
        self._ensure_in_progress(session.current_step)
        assert self.session is not None
        return self.session

    def complete(self) -> None:
        self._save(
            replace(
                self.preferences,
                onboarding_status=OnboardingStatus.COMPLETED,
                onboarding_current_step=self.step_count - 1,
            )
        )
        self.session = None

    def dismiss(self) -> None:
        step = self.session.current_step if self.session is not None else 0
        self._save(
            replace(
                self.preferences,
                onboarding_status=OnboardingStatus.DISMISSED,
                onboarding_current_step=self._bounded_step(step),
            )
        )
        self.session = None

    def _ensure_in_progress(self, step: int) -> None:
        self._save(
            replace(
                self.preferences,
                onboarding_status=OnboardingStatus.IN_PROGRESS,
                onboarding_current_step=step,
            )
        )
        self.session = OnboardingSession(
            step,
            OnboardingStatus.IN_PROGRESS,
            manual_preview=False,
        )

    def _save(self, preferences: AppPreferences) -> None:
        self.preferences_file.save(preferences)
        self.preferences = preferences

    def _load(self) -> AppPreferences:
        try:
            return self.preferences_file.load()
        except AppPreferencesError:
            return AppPreferences()

    def _bounded_step(self, step: int) -> int:
        return max(0, min(int(step), self.step_count - 1))
