"""Application service for deliberate pilot update checks."""

from __future__ import annotations

from .domain import UpdateChannel, UpdateProjection, UpdateState
from .ports import NativeUpdatePort


class UpdateApplicationService:
    """Expose update state without leaking Sparkle or platform APIs into Qt widgets."""

    def __init__(
        self,
        adapter: NativeUpdatePort,
        *,
        current_version: str,
        build_version: str,
        channel: UpdateChannel = UpdateChannel.PILOT,
    ) -> None:
        self._adapter = adapter
        self._current_version = current_version
        self._build_version = build_version
        self._channel = channel
        self._state = UpdateState.READY if adapter.available else UpdateState.UNAVAILABLE
        self._message = (
            "Bereit für eine beaufsichtigte Updateprüfung."
            if adapter.available
            else "Updates sind in diesem Start nicht verfügbar. Nutze bei Bedarf das DMG."
        )

    def projection(self) -> UpdateProjection:
        state = self._state
        if self._adapter.available and state is not UpdateState.CHECKING:
            state = UpdateState.READY if self._adapter.can_check else UpdateState.CHECKING
        return UpdateProjection(
            current_version=self._current_version,
            build_version=self._build_version,
            channel=self._channel,
            state=state,
            last_checked_at=self._adapter.last_check_date(),
            message=self._message,
        )

    def check_for_updates(self) -> UpdateProjection:
        if not self._adapter.available:
            self._state = UpdateState.UNAVAILABLE
            self._message = (
                "Die Updateprüfung ist hier nicht verfügbar. Installiere ein neues DMG manuell."
            )
            return self.projection()
        if not self._adapter.can_check:
            self._state = UpdateState.CHECKING
            self._message = "Eine Updateprüfung läuft bereits."
            return self.projection()
        try:
            self._adapter.check_for_updates()
        except Exception:
            self._state = UpdateState.ERROR
            self._message = (
                "Die Updateprüfung konnte nicht gestartet werden. Das manuelle DMG bleibt verfügbar."
            )
            return self.projection()
        self._state = UpdateState.CHECKING
        self._message = (
            "Sparkle prüft den Pilotkanal. Verfügbare Versionen und Release-Hinweise "
            "werden in einem eigenen Fenster angezeigt."
        )
        return self.projection()
