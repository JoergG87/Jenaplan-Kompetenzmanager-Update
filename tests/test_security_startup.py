"""Productive auth-gate, pending-account and runtime split contracts."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.desktop_app import main as desktop_main
from src.desktop_app.runtime import (
    prepare_security_runtime_storage,
    runtime_paths,
)
from src.security.domain import (
    AuthenticationStatus,
    DeviceCredentialAuthenticationResult,
    DeviceCredentialAuthenticationStatus,
    RecoveryStatus,
    SecurityStoreError,
    SecurityStoreState,
)
from src.security.startup import (
    SecurityStartState,
    SecurityStartupDecision,
    SecurityStartupResolver,
    build_security_runtime,
    legacy_installation_present,
)
from src.desktop_app.security_controller import (
    run_startup_device_authentication,
    should_attempt_startup_device_authentication,
)
from src.core.app_preferences import (
    AppPreferences,
    AppPreferencesError,
    OnboardingStatus,
    normalize_display_name,
)


PASSWORD = "eine lange sichere Startpassphrase"
NEW_PASSWORD = "eine andere lange sichere Startpassphrase"


def _runtime(root: Path):
    paths = prepare_security_runtime_storage(data_root=root)
    return paths, build_security_runtime(paths)


def test_security_runtime_preparation_creates_no_product_storage(tmp_path: Path) -> None:
    paths = prepare_security_runtime_storage(data_root=tmp_path / "runtime")
    assert paths.root.is_dir()
    assert paths.security.is_dir()
    assert not paths.database.exists()
    assert not paths.documents.exists()
    assert not paths.exports.exists()
    assert not paths.backups.exists()
    assert not paths.logs.exists()


def test_startup_resolver_distinguishes_first_run_and_legacy_without_db_open(
    tmp_path: Path,
) -> None:
    paths, runtime = _runtime(tmp_path / "runtime")
    state = runtime.service.security_store_state()
    resolver = SecurityStartupResolver()
    assert resolver.resolve(state, legacy_installation_present=False).state is SecurityStartState.FIRST_RUN
    paths.database.write_bytes(b"not opened sqlite bytes")
    assert legacy_installation_present(paths)
    assert resolver.resolve(state, legacy_installation_present=True).state is SecurityStartState.LEGACY_ENROLLMENT


def test_pending_enrollment_activates_only_after_code_confirmation(tmp_path: Path) -> None:
    _paths, runtime = _runtime(tmp_path / "runtime")
    prepared = runtime.service.prepare_local_account_enrollment(PASSWORD)
    assert len(prepared.recovery_codes) == 10
    assert runtime.service.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING
    assert runtime.service.authenticate_password(PASSWORD).status is AuthenticationStatus.PASSWORD_RESET_REQUIRED
    assert runtime.service.confirm_local_account_enrollment(prepared.recovery_set_id)
    assert runtime.service.security_store_state().state is SecurityStoreState.READY
    assert runtime.service.authenticate_password(PASSWORD).status is AuthenticationStatus.AUTHENTICATED


def test_recovery_reset_stays_pending_across_reopen_until_codes_confirmed(
    tmp_path: Path,
) -> None:
    paths, runtime = _runtime(tmp_path / "runtime")
    enrolled = runtime.service.enroll_local_account(PASSWORD)
    epoch_before = runtime.repository.security_epoch()
    assert runtime.service.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status is RecoveryStatus.ACCEPTED
    assert runtime.repository.security_epoch() == epoch_before + 1
    prepared = runtime.service.prepare_recovery_password_reset(NEW_PASSWORD)
    assert runtime.service.security_store_state().state is SecurityStoreState.PASSWORD_RESET_PENDING
    assert runtime.repository.security_epoch() == epoch_before + 1

    reopened = build_security_runtime(paths)
    assert reopened.service.authenticate_password(NEW_PASSWORD).status is AuthenticationStatus.PASSWORD_RESET_REQUIRED
    assert reopened.service.confirm_recovery_password_reset(prepared.recovery_set_id)
    assert reopened.service.authenticate_password(NEW_PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert reopened.service.verify_and_consume_recovery_code(enrolled.recovery_codes[1]).status is RecoveryStatus.INVALID


def test_password_change_increments_epoch_and_keeps_recovery_set(tmp_path: Path) -> None:
    _paths, runtime = _runtime(tmp_path / "runtime")
    enrolled = runtime.service.enroll_local_account(PASSWORD)
    epoch = runtime.repository.security_epoch()
    assert runtime.service.change_password(PASSWORD, NEW_PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert runtime.repository.security_epoch() == epoch + 1
    assert runtime.service.authenticate_password(PASSWORD).status is AuthenticationStatus.INVALID_CREDENTIALS
    assert runtime.service.authenticate_password(NEW_PASSWORD).status is AuthenticationStatus.AUTHENTICATED
    assert runtime.service.verify_and_consume_recovery_code(enrolled.recovery_codes[0]).status is RecoveryStatus.ACCEPTED


def test_password_change_and_recovery_do_not_change_app_display_name(tmp_path: Path) -> None:
    paths, runtime = _runtime(tmp_path / "runtime")
    runtime.preferences.save(
        AppPreferences(
            15,
            "Laura 🌿",
            onboarding_status=OnboardingStatus.IN_PROGRESS,
            onboarding_current_step=2,
        )
    )
    enrolled = runtime.service.enroll_local_account(PASSWORD)
    assert b"Laura" not in paths.security_database.read_bytes()
    runtime.service.change_password(PASSWORD, NEW_PASSWORD)
    preferences = runtime.preferences.load()
    assert preferences.display_name == "Laura 🌿"
    assert preferences.onboarding_status is OnboardingStatus.IN_PROGRESS
    assert preferences.onboarding_current_step == 2
    assert runtime.service.verify_and_consume_recovery_code(
        enrolled.recovery_codes[0]
    ).status is RecoveryStatus.ACCEPTED
    prepared = runtime.service.prepare_recovery_password_reset(PASSWORD)
    assert runtime.service.confirm_recovery_password_reset(prepared.recovery_set_id)
    preferences = runtime.preferences.load()
    assert preferences.display_name == "Laura 🌿"
    assert preferences.onboarding_status is OnboardingStatus.IN_PROGRESS
    assert preferences.onboarding_current_step == 2
    assert b"Laura" not in paths.security_database.read_bytes()


def test_app_preferences_store_optional_unicode_name_and_validate_contract(
    tmp_path: Path,
) -> None:
    paths, runtime = _runtime(tmp_path / "runtime")
    assert runtime.preferences.load() == AppPreferences(15)
    for minutes in (5, 10, 15, 30, 60):
        runtime.preferences.save(AppPreferences(minutes, "Łucja 🌿"))
        assert runtime.preferences.load().inactivity_minutes == minutes
        assert runtime.preferences.load().display_name == "Łucja 🌿"
    with pytest.raises(ValueError):
        AppPreferences(0)
    assert normalize_display_name("  Laura  ") == "Laura"
    assert normalize_display_name("  ") is None
    assert normalize_display_name("L  au  ra") == "L  au  ra"
    with pytest.raises(ValueError):
        normalize_display_name("x" * 81)
    paths.app_preferences.write_text(
        '{"display_name":null,"format_version":1,"inactivity_minutes":0}\n'
    )
    with pytest.raises(AppPreferencesError):
        runtime.preferences.load()


def test_productive_start_order_keeps_product_runtime_and_shell_after_auth() -> None:
    source = inspect.getsource(desktop_main.main)
    restore_block = source.index('if "--restore-worker" in arguments:')
    root_preflight = source.index("_preflight_desktop_runtime_root(")
    security_paths = source.index("prepare_security_runtime_storage(data_root=data_root)")
    security_read_only = source.index("repository.require_current_read_only()")
    security_state = source.index("security_runtime.service.security_store_state()")
    auth = source.index("run_startup_authentication(")
    authenticated_context = source.index("_require_authenticated_cipher_context(")
    product_runtime = source.index("open_cipher_product_runtime(")
    adapter = source.index("_build_cipher_product_student_adapter(")
    shell = source.index("window = JenaplanDesktopApp(")
    assert (
        restore_block
        < root_preflight
        < security_paths
        < security_read_only
        < security_state
        < auth
        < authenticated_context
        < product_runtime
        < adapter
        < shell
    )
    assert "recover_interrupted_restore" not in source
    assert "_coordinate_product_database_startup" not in source
    assert "cipher_backup_restore_not_available" in source
    assert "DISABLE_AUTH" not in source
    assert "database_create_allowed=False" in source
    assert 'backup_extension=".jkmebackup"' in source
    assert "backup_restore_available=True" in source


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("session_user", "other-user"),
        ("state_installation", "other-installation"),
        ("account_user", "other-user"),
        ("account_installation", "other-installation"),
        ("epoch", 2),
    ],
)
def test_cipher_session_context_is_verified_before_product_runtime(
    field: str,
    replacement: object,
) -> None:
    session = SimpleNamespace(
        user_id="user-id", installation_id="installation-id", security_epoch=1
    )
    state = SimpleNamespace(user_id="user-id", installation_id="installation-id")
    account = SimpleNamespace(user_id="user-id", installation_id="installation-id")
    epoch = 1
    if field == "session_user":
        session.user_id = replacement
    elif field == "state_installation":
        state.installation_id = replacement
    elif field == "account_user":
        account.user_id = replacement
    elif field == "account_installation":
        account.installation_id = replacement
    else:
        epoch = int(replacement)

    with pytest.raises(RuntimeError, match="cipher_product_session_context_mismatch"):
        desktop_main._require_authenticated_cipher_context(
            session=session,
            security_state=state,
            account=account,
            security_epoch=epoch,
        )


def test_cipher_shell_source_blocks_legacy_transition_and_testdata_onboarding() -> None:
    shell_source = (Path(desktop_main.__file__).parent / "shell.py").read_text()
    transition = shell_source.index("def configure_school_year_transition_activation(")
    transition_guard = shell_source.index(
        "if not self.backup_restore_available:", transition
    )
    legacy_backup = shell_source.index("VerifiedSchoolYearTransitionBackupAdapter(", transition)
    assert transition < transition_guard < legacy_backup
    onboarding = shell_source.index("self.pilot_testdata_onboarding = (")
    onboarding_end = shell_source.index("self.update_service =", onboarding)
    onboarding_source = shell_source[onboarding:onboarding_end]
    assert "self.backup_restore_available" in onboarding_source
    assert 'selected_backup_extension == ".jkmbackup"' in onboarding_source


def test_startup_device_authentication_does_not_bypass_touch_id_preference() -> None:
    login = SecurityStartupDecision(
        SecurityStartState.LOGIN_REQUIRED, "SEC-LOGIN_REQUIRED"
    )
    locked = SecurityStartupDecision(SecurityStartState.LOCKED, "SEC-LOCKED")
    assert should_attempt_startup_device_authentication(
        decision=login, touch_id_preferred=False
    )
    assert not should_attempt_startup_device_authentication(
        decision=login, touch_id_preferred=True
    )
    assert not should_attempt_startup_device_authentication(
        decision=locked, touch_id_preferred=False
    )


@pytest.mark.parametrize(
    "status",
    [
        DeviceCredentialAuthenticationStatus.NOT_CONFIGURED,
        DeviceCredentialAuthenticationStatus.REJECTED,
        DeviceCredentialAuthenticationStatus.UNSUPPORTED,
        DeviceCredentialAuthenticationStatus.STORE_UNAVAILABLE,
    ],
)
def test_startup_device_credential_failure_never_creates_session(
    tmp_path: Path, status: DeviceCredentialAuthenticationStatus
) -> None:
    _paths, runtime = _runtime(tmp_path / status.value)
    runtime.service.enroll_local_account(PASSWORD)

    class CredentialService:
        def authenticate(self):
            return DeviceCredentialAuthenticationResult(status)

    assert run_startup_device_authentication(
        service=runtime.service,
        repository=runtime.repository,
        device_credentials=CredentialService(),
    ) is None


def test_valid_startup_device_credential_creates_fresh_epoch_bound_session(
    tmp_path: Path,
) -> None:
    _paths, runtime = _runtime(tmp_path / "valid-device")
    enrolled = runtime.service.enroll_local_account(PASSWORD)

    class CredentialService:
        def authenticate(self):
            return DeviceCredentialAuthenticationResult(
                DeviceCredentialAuthenticationStatus.AUTHENTICATED
            )

    result = run_startup_device_authentication(
        service=runtime.service,
        repository=runtime.repository,
        device_credentials=CredentialService(),
    )
    assert result is not None
    assert result.session.user_id == enrolled.user_id
    assert result.session.installation_id == enrolled.installation_id
    assert result.session.security_epoch == runtime.repository.security_epoch()


def test_store_marker_asymmetry_never_resolves_to_enrollment(tmp_path: Path) -> None:
    paths, runtime = _runtime(tmp_path / "runtime")
    runtime.service.enroll_local_account(PASSWORD)
    paths.enrollment_marker.unlink()
    decision = SecurityStartupResolver().resolve(
        runtime.service.security_store_state(),
        legacy_installation_present=True,
    )
    assert decision.state is SecurityStartState.INCONSISTENT
