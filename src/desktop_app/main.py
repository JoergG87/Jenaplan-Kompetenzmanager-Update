"""Entry point for the PySide6 desktop app and packaged-app smoke check."""

from __future__ import annotations

import json
import hashlib
import logging
import os
import sys
import tempfile
from dataclasses import replace
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from src.core.database_startup import (
        DatabaseStartupCoordinator,
        DatabaseStartupDecision,
    )
    from src.desktop_app.app import JenaplanDesktopApp

# Kept as a patchable sentinel for pre-existing startup-isolation tests. Qt is
# imported only after restore recovery has admitted normal startup.
QApplication = None

from src.desktop_app.runtime import (
    APP_DATA_DIR_ENV,
    APP_BUNDLE_ID,
    APP_NAME,
    RuntimePaths,
    RuntimeStorageError,
    application_data_root,
    begin_pre_auth_security_logging,
    configure_runtime_logging,
    discard_pre_auth_security_logging,
    flush_pre_auth_security_logging,
    load_build_info,
    prepare_security_runtime_storage,
    prepare_cipher_runtime_storage,
    prepare_runtime_storage,
    resource_path,
    runtime_paths,
)
from src.version import APP_VERSION
from src.core.runtime_root_protection import (
    RUNTIME_ROOT_PROTECTION_MARKER,
    RuntimeRootKind,
    RuntimeRootLifecycle,
    RuntimeRootProtection,
    RuntimeRootProtectionError,
    activate_pilot_product_root,
    inspect_runtime_root,
    publish_pilot_product_root,
)


PACKAGED_SMOKE_MARKER_ENV = "JENAPLAN_PACKAGED_SMOKE_MARKER"
PACKAGED_SMOKE_MARKER_VALUE = "isolated-v1"
PACKAGED_SMOKE_TEMP_PREFIX = "jenaplan-packaged-smoke-"
PACKAGED_KEYCHAIN_SMOKE_ARGUMENT = "--packaged-keychain-smoke"
PACKAGED_SMOKE_ARGUMENT = "--packaged-smoke-test"
PACKAGED_CIPHER_SEED_ARGUMENT = "--packaged-cipher-seed"
PACKAGED_CIPHER_SEED_VERIFY_ARGUMENT = "--packaged-cipher-seed-verify"
PACKAGED_RUNTIME_AUDIT_ARGUMENT = "--packaged-runtime-audit"


def _validated_packaged_smoke_data_root(
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Require an explicit marker and a dedicated system-temporary data root."""
    environment = os.environ if environ is None else environ
    if environment.get(PACKAGED_SMOKE_MARKER_ENV) != PACKAGED_SMOKE_MARKER_VALUE:
        raise RuntimeStorageError(
            "Packaged-Smoke ohne gueltigen expliziten Smoke-Marker abgelehnt."
        )
    from src.core import macos_test_package_profile as test_package
    profile = test_package.test_identity()
    if profile is not None:
        try:
            return test_package.active_internal_test_smoke_root(environment, sys.argv[1:])
        except (OSError, ValueError, TypeError):
            raise RuntimeStorageError("test_profile_invalid") from None
    raw_root = environment.get(APP_DATA_DIR_ENV, "")
    data_root = Path(raw_root).expanduser() if raw_root else Path()
    if not raw_root or not data_root.is_absolute():
        raise RuntimeStorageError(
            "Packaged-Smoke ohne absoluten isolierten Datenpfad abgelehnt."
        )
    temporary_root = Path(tempfile.gettempdir()).resolve()
    resolved_root = data_root.resolve(strict=False)
    try:
        relative = resolved_root.relative_to(temporary_root)
    except ValueError as error:
        raise RuntimeStorageError(
            "Packaged-Smoke ausserhalb der temporaeren Datenwurzel abgelehnt."
        ) from error
    smoke_component_index = next(
        (
            index
            for index, component in enumerate(relative.parts)
            if component.startswith(PACKAGED_SMOKE_TEMP_PREFIX)
        ),
        None,
    )
    if smoke_component_index is None:
        raise RuntimeStorageError(
            "Packaged-Smoke ohne eigenes temporaeres Smoke-Verzeichnis abgelehnt."
        )
    smoke_container = temporary_root.joinpath(
        *relative.parts[: smoke_component_index + 1]
    )
    if not smoke_container.is_dir() or smoke_container.is_symlink():
        raise RuntimeStorageError(
            "Das temporaere Smoke-Verzeichnis ist nicht sicher vorhanden."
        )
    try:
        protection = inspect_runtime_root(resolved_root)
    except RuntimeRootProtectionError as error:
        raise RuntimeStorageError(error.code) from None
    if protection is None or protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
        raise RuntimeStorageError("packaged_smoke_test_root_unmarked")
    return resolved_root


def _app_icon():
    """Return the application icon used for windows and the task switcher."""
    from PySide6.QtGui import QIcon

    icon_path = resource_path("assets", "app_icon.png")
    return QIcon(str(icon_path))


def _argument_value(arguments: list[str], name: str) -> str | None:
    if name not in arguments:
        return None
    index = arguments.index(name)
    if index + 1 >= len(arguments):
        raise RuntimeStorageError(f"Technisches Startargument ohne Wert: {name}")
    value = arguments[index + 1]
    del arguments[index : index + 2]
    return value


def _coordinate_product_database_startup(
    *,
    data_root: Path,
    restore_status: str,
    coordinator: DatabaseStartupCoordinator,
    prepare_storage: Callable[..., RuntimePaths],
    initialize_final_schema: Callable[[Path], None],
    new_database_initialization_allowed: bool,
) -> tuple[RuntimePaths, DatabaseStartupDecision]:
    """Gate product runtime preparation behind the read-only DB decision."""

    paths = runtime_paths(data_root)
    decision = coordinator.coordinate(
        paths.database,
        restore_status=restore_status,
        new_database_initialization_allowed=(
            new_database_initialization_allowed
        ),
    )
    if decision.final_schema_initialization_required:
        paths = prepare_storage(data_root=data_root)
        initialize_final_schema(paths.database)
        decision = coordinator.coordinate(
            paths.database,
            restore_status=restore_status,
            new_database_initialization_allowed=(
                new_database_initialization_allowed
            ),
        )
    elif decision.normal_runtime_allowed:
        paths = prepare_storage(data_root=data_root)
    return paths, decision


def _new_database_initialization_candidate(
    data_root: Path,
    *,
    runtime_lock_path: Path,
) -> bool:
    """Accept only a runtime root with no pre-existing product artifacts."""

    try:
        root = Path(data_root).resolve(strict=True)
        lock_path = Path(runtime_lock_path).resolve(strict=False)
        entries = set(root.iterdir())
        allowed = {
            lock_path,
            root / RUNTIME_ROOT_PROTECTION_MARKER,
        }
        protection = inspect_runtime_root(root)
        return (
            entries == allowed
            and lock_path.is_file()
            and not lock_path.is_symlink()
            and protection is not None
            and (
                protection.kind is RuntimeRootKind.SYNTHETIC_TEST
                or protection.lifecycle is RuntimeRootLifecycle.INITIALIZING
            )
        )
    except (OSError, RuntimeRootProtectionError):
        return False


def _preflight_desktop_runtime_root(
    data_root: Path,
    *,
    packaged_smoke: bool,
) -> tuple[RuntimeRootProtection | None, bool]:
    """Classify before the instance lock or Security Store can be written."""

    root = Path(data_root)
    if not root.exists() and not root.is_symlink():
        if packaged_smoke:
            raise RuntimeRootProtectionError("packaged_smoke_test_root_missing")
        return None, True
    if root.is_symlink() or not root.is_dir():
        raise RuntimeRootProtectionError("runtime_root_invalid")
    protection = inspect_runtime_root(root)
    entries = tuple(root.iterdir())
    if protection is None:
        if entries:
            raise RuntimeRootProtectionError("runtime_root_protection_missing")
        if packaged_smoke:
            raise RuntimeRootProtectionError("packaged_smoke_test_root_unmarked")
        return None, True
    if packaged_smoke and protection.kind is not RuntimeRootKind.SYNTHETIC_TEST:
        raise RuntimeRootProtectionError("packaged_smoke_test_root_invalid")
    if (
        not packaged_smoke
        and protection.kind is RuntimeRootKind.PILOT_PRODUCT
        and protection.lifecycle is RuntimeRootLifecycle.INITIALIZING
    ):
        raise RuntimeRootProtectionError("pilot_product_root_initialization_incomplete")
    return protection, False


def _require_existing_product_security(paths: RuntimePaths) -> None:
    """Reject missing/unsafe Security evidence without creating or repairing it."""

    required = (paths.security, paths.security_database, paths.enrollment_marker)
    if (
        not paths.security.is_dir()
        or paths.security.is_symlink()
        or any(not path.is_file() or path.is_symlink() for path in required[1:])
    ):
        raise RuntimeRootProtectionError("pilot_product_security_incomplete")


def _show_upgrade_startup_blocked(arguments: list[str], *, packaged_smoke: bool) -> None:
    """Existing UI error port, with no authentication, storage or repair action."""
    message = (
        "Der sichere Start wurde angehalten. Der lokale Installations- oder "
        "Upgradezustand ist nicht eindeutig prüfbar. Die Anwendung hat keine "
        "weitere Nutzung freigegeben. Bitte lassen Sie den vorhandenen "
        "Zustand durch den Support prüfen."
    )
    print(message, file=sys.stderr)
    if not packaged_smoke:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(arguments)
        dialog = QMessageBox()
        dialog.setOption(QMessageBox.Option.DontUseNativeDialog, True)
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle("Sicherer Start angehalten")
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()


def _build_cipher_product_student_adapter(product_runtime):
    """Inject the one keyed product runtime without constructing another DB."""
    from src.core.sqlite_store import SQLiteCompetencyRepository
    from src.desktop_app.adapters.student_desktop_adapter import (
        StudentDesktopAdapter,
    )
    from src.desktop_app.adapters.curriculum_desktop_adapter import (
        CurriculumDesktopAdapter,
    )

    entries = CurriculumDesktopAdapter().list_entries()
    repository = SQLiteCompetencyRepository(product_runtime.database)
    if product_runtime.first_run:
        repository.ensure_catalog_defaults(entries)
    repository.require_catalog_defaults(entries)

    return StudentDesktopAdapter(
        database=product_runtime.database,
        database_create_allowed=False,
        managed_document_store=product_runtime.documents,
    )


def _require_authenticated_cipher_context(
    *, session, security_state, account, security_epoch: int
) -> None:
    """Reject a stale or cross-installation session before any Cipher write."""
    from src.security.cipher_product_runtime import (
        CipherProductRuntimeError,
        CipherProductRuntimeOperation,
    )

    if (
        security_state.user_id != session.user_id
        or security_state.installation_id != session.installation_id
        or account.user_id != session.user_id
        or account.installation_id != session.installation_id
        or session.security_epoch != security_epoch
    ):
        raise CipherProductRuntimeError(
            "cipher_product_session_context_mismatch",
            operation=CipherProductRuntimeOperation.CLASSIFY,
        )


def main() -> int:
    """Start the desktop app."""
    arguments = list(sys.argv)
    maintenance_flags = [flag for flag in ("--migrate-v4-to-v7", "--complete-v7-migration") if flag in arguments]
    if maintenance_flags:
        try:
            if len(maintenance_flags) != 1 or any(flag in arguments for flag in (
                    "--restore-worker", "--final-v4-restore-confirm", "--final-v7-restore-confirm",
                    "--synthetic-v6-restore-confirm", "--synthetic-v7-restore-confirm")):
                raise RuntimeError("product_v7_maintenance_arguments_invalid")
            from src.desktop_app.product_v7_maintenance import run_product_v7_maintenance
            root = _argument_value(arguments, "--runtime-root")
            if root is None:
                raise RuntimeError("product_v7_maintenance_root_required")
            return run_product_v7_maintenance(Path(root), complete=maintenance_flags[0] == "--complete-v7-migration")
        except Exception as error:
            code = getattr(error, "code", "product_v7_maintenance_failed")
            # Only a fixed diagnostic token, never arbitrary exception text.
            if not isinstance(code, str) or not code or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in code):
                code = "product_v7_maintenance_failed"
            print("Wartung sicher angehalten; vorhandenen Bestand und Quellbackup erhalten. " + code, file=sys.stderr)
            if code == "product_v7_maintenance_failed":
                # Structural diagnostics only: no exception message, source
                # lines, local paths, account values or key material.
                import traceback
                print("Wartung: " + type(error).__name__, file=sys.stderr)
                for frame in traceback.extract_tb(error.__traceback__):
                    print("Wartung: " + Path(frame.filename).name + ":" + str(frame.lineno), file=sys.stderr)
            return 3
    if "--internal-native-test" in arguments:
        from src.core.macos_test_package_profile import test_identity
        if test_identity() is None or not getattr(sys, "frozen", False):
            print("Isolierter Teststart gesperrt.", file=sys.stderr)
            return 2
        # Dynamic import keeps this test-only module out of product bundles.
        native = __import__("scripts.macos_native_acceptance", fromlist=["run_frozen"])
        return native.run_frozen(arguments[2] if len(arguments) == 3 else "")
    if PACKAGED_RUNTIME_AUDIT_ARGUMENT in arguments:
        arguments.remove(PACKAGED_RUNTIME_AUDIT_ARGUMENT)
        return _run_packaged_runtime_audit()
    try:
        packaged_keychain_mode = _argument_value(
            arguments,
            PACKAGED_KEYCHAIN_SMOKE_ARGUMENT,
        )
    except RuntimeStorageError as error:
        print(f"Keychain-Pakettest abgelehnt: {error}", file=sys.stderr)
        return 2
    if packaged_keychain_mode is not None:
        from src.security.packaged_keychain_smoke import (
            run_packaged_keychain_smoke,
        )

        return run_packaged_keychain_smoke(
            packaged_keychain_mode,
            environ=os.environ,
        )
    for argument, verify_only in (
        (PACKAGED_CIPHER_SEED_ARGUMENT, False),
        (PACKAGED_CIPHER_SEED_VERIFY_ARGUMENT, True),
    ):
        try:
            cipher_seed_root = _argument_value(arguments, argument)
        except RuntimeStorageError as error:
            print(f"Cipher-Testbestand abgelehnt: {error}", file=sys.stderr)
            return 2
        if cipher_seed_root is not None:
            from scripts.seed_test_data import (
                build_cipher_pilot_test_root,
                verify_cipher_pilot_test_root,
            )

            try:
                result = (
                    verify_cipher_pilot_test_root(Path(cipher_seed_root))
                    if verify_only
                    else build_cipher_pilot_test_root(Path(cipher_seed_root))
                )
            except Exception as error:
                code = str(getattr(error, "code", "cipher_pilot_seed_failed"))
                print(f"Cipher-Testbestand blockiert: {code}", file=sys.stderr)
                return 2
            print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
            return 0
    if "--restore-worker" in arguments:
        from src.desktop_app.restore_worker import (
            RESTORE_MODE_FINAL_V4_ENCRYPTED,
            RESTORE_MODE_FINAL_V7_ENCRYPTED,
            RESTORE_MODE_SYNTHETIC_V7_ENCRYPTED,
            RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED,
            run as run_restore_worker,
        )

        try:
            mode_index = arguments.index("--restore-mode")
            restore_mode = arguments[mode_index + 1]
        except (ValueError, IndexError):
            restore_mode = None
        if restore_mode not in {RESTORE_MODE_FINAL_V4_ENCRYPTED, RESTORE_MODE_FINAL_V7_ENCRYPTED, RESTORE_MODE_SYNTHETIC_V6_ENCRYPTED, RESTORE_MODE_SYNTHETIC_V7_ENCRYPTED}:
            print(
                "App-Start abgelehnt: cipher_backup_restore_not_available.",
                file=sys.stderr,
            )
            return 3
        worker_arguments = arguments[1:]
        worker_arguments.remove("--restore-worker")
        return run_restore_worker(worker_arguments)

    try:
        packaged_smoke_mode = _argument_value(arguments, PACKAGED_SMOKE_ARGUMENT)
    except RuntimeStorageError as error:
        print(f"Packaged-App-Smoke abgelehnt: {error}", file=sys.stderr)
        return 2
    packaged_smoke = packaged_smoke_mode is not None
    if packaged_smoke:
        try:
            smoke_data_root = _validated_packaged_smoke_data_root()
        except RuntimeStorageError as error:
            print(f"Packaged-App-Smoke abgelehnt: {error}", file=sys.stderr)
            return 2
    else:
        smoke_data_root = None

    try:
        final_v7_restore_confirm = "--final-v7-restore-confirm" in arguments
        if final_v7_restore_confirm:
            if any(flag in arguments for flag in ("--final-v4-restore-confirm", "--synthetic-v6-restore-confirm", "--synthetic-v7-restore-confirm")):
                return 3
            arguments[arguments.index("--final-v7-restore-confirm")] = "--final-v4-restore-confirm"
        final_v4_restore_confirm = "--final-v4-restore-confirm" in arguments
        synthetic_v7_restore_confirm = "--synthetic-v7-restore-confirm" in arguments
        synthetic_v6_restore_confirm = "--synthetic-v6-restore-confirm" in arguments
        if synthetic_v7_restore_confirm and (synthetic_v6_restore_confirm or final_v4_restore_confirm):
            raise RuntimeStorageError("cipher_restore_confirm_arguments_conflict")
        if final_v4_restore_confirm and synthetic_v6_restore_confirm:
            raise RuntimeStorageError("cipher_restore_confirm_arguments_conflict")
        restore_confirm = final_v4_restore_confirm or synthetic_v6_restore_confirm or synthetic_v7_restore_confirm
        if restore_confirm:
            arguments.remove("--synthetic-v7-restore-confirm" if synthetic_v7_restore_confirm else "--synthetic-v6-restore-confirm" if synthetic_v6_restore_confirm else "--final-v4-restore-confirm")
            restore_runtime_root = _argument_value(arguments, "--runtime-root")
            restore_confirm_id = _argument_value(arguments, "--restore-id")
            restore_confirm_token = _argument_value(arguments, "--restore-token")
            inherited_lock_value = _argument_value(arguments, "--restore-lock-fd")
            if None in (
                restore_runtime_root,
                restore_confirm_id,
                restore_confirm_token,
                inherited_lock_value,
            ):
                raise RuntimeStorageError("cipher_restore_confirm_arguments_incomplete")
        else:
            restore_runtime_root = _argument_value(arguments, "--runtime-root")
            if restore_runtime_root is not None:
                from src.security.product_v7 import require_product_v7_scope
                require_product_v7_scope(Path(restore_runtime_root))
            restore_confirm_id = None
            restore_confirm_token = None
        resume_restore_id = _argument_value(arguments, "--restore-resume")
        resume_token = _argument_value(arguments, "--restore-token")
        if not restore_confirm:
            inherited_lock_value = _argument_value(arguments, "--restore-lock-fd")
        if resume_restore_id is not None or resume_token is not None:
            raise RuntimeStorageError("cipher_backup_restore_not_available")
        if inherited_lock_value is not None and not restore_confirm:
            raise RuntimeStorageError("cipher_backup_restore_not_available")
        inherited_lock_fd = (
            None if inherited_lock_value is None else int(inherited_lock_value)
        )
    except (RuntimeStorageError, RuntimeRootProtectionError, ValueError, OSError) as error:
        print(f"App-Start abgelehnt: {error}", file=sys.stderr)
        return 3

    data_root = Path(
        restore_runtime_root
        if restore_runtime_root is not None
        else (smoke_data_root or application_data_root())
    ).expanduser().absolute()
    from src.security.upgrade_startup import (
        ProductStartupInventory, ProductUpgradeStartupGuard, UpgradeStartupBlocked,
    )

    try:
        from src.core.macos_test_package_profile import test_identity
        internal_test = test_identity() is not None
        if internal_test:
            from src.security.internal_test_v6_composition import (
                InternalTestStartupInventory, InternalTestStartupGuard,
                require_internal_test_v6_context,
            )
            require_internal_test_v6_context(data_root)
            inventory_port = InternalTestStartupInventory()
        else:
            if synthetic_v6_restore_confirm or synthetic_v7_restore_confirm:
                raise RuntimeRootProtectionError("synthetic_v6_sealed_context_required")
            from src.security.product_v7 import ProductV7StartupInventory
            inventory_port = ProductV7StartupInventory()
        before_inventory = inventory_port.before_lock(data_root)
        root_protection, fresh_unmarked_root = _preflight_desktop_runtime_root(
            data_root,
            packaged_smoke=packaged_smoke,
        )
    except UpgradeStartupBlocked:
        _show_upgrade_startup_blocked(arguments, packaged_smoke=packaged_smoke)
        return 3
    except (RuntimeRootProtectionError, OSError, RuntimeError, ValueError) as error:
        print(f"App-Start blockiert: {getattr(error, 'code', 'runtime_root_unreadable')}", file=sys.stderr)
        _show_upgrade_startup_blocked(arguments, packaged_smoke=packaged_smoke)
        return 3
    from src.core.restore_runtime import (
        RuntimeInstanceLock,
    )

    lock = None
    runtime_stack = ExitStack()
    new_database_initialization_candidate = False
    v6_recovery_context = []
    try:
        lock = RuntimeInstanceLock(data_root, inherited_fd=inherited_lock_fd)
        lock.acquire()
        from src.security.product_v7 import ProductV7StartupGuard
        startup_guard = (InternalTestStartupGuard if internal_test else ProductV7StartupGuard)(lock, inventory=inventory_port)
        startup_guard.evaluate(before=before_inventory)
        if fresh_unmarked_root:
            root_protection = publish_pilot_product_root(
                data_root.resolve(strict=True),
                allowed_existing=(lock.path,),
            )
        else:
            root_protection, _ = _preflight_desktop_runtime_root(
                data_root, packaged_smoke=packaged_smoke,
            )
        from src.security.final_v4_live_restore import (
            confirm_final_v4_restore_startup,
            recover_interrupted_final_v4_restore,
        )

        if internal_test:
            from src.desktop_app.synthetic_v6_runtime_adapters import (
                recover_internal_test_v6_restore, confirm_internal_test_v6_restore,
            )
            # Restore kind comes from existing transaction evidence. A foreign
            # contract is never retried using another schema's verifier.
            from src.security.internal_test_v6_composition import internal_test_restore_kind
            from src.security.synthetic_v6_live_restore import SYNTHETIC_V6_LIVE_RESTORE_KIND
            from src.security.synthetic_v7_live_restore import SYNTHETIC_V7_LIVE_RESTORE_KIND
            kind = internal_test_restore_kind(data_root)
            if ((synthetic_v6_restore_confirm and kind != SYNTHETIC_V6_LIVE_RESTORE_KIND)
                    or (synthetic_v7_restore_confirm and kind != SYNTHETIC_V7_LIVE_RESTORE_KIND)):
                raise RuntimeStorageError("cipher_restore_schema_mismatch")
            if kind == SYNTHETIC_V7_LIVE_RESTORE_KIND:
                from src.desktop_app.synthetic_v7_runtime_adapters import (
                    recover_internal_test_v7_restore as recover_internal_test_v6_restore,
                    confirm_internal_test_v7_restore as confirm_internal_test_v6_restore)
            v6_restore = synthetic_v6_restore_confirm or synthetic_v7_restore_confirm or kind in (SYNTHETIC_V6_LIVE_RESTORE_KIND, SYNTHETIC_V7_LIVE_RESTORE_KIND)
        else:
            from src.security.internal_test_v6_composition import inspect_restore_kind
            from src.security.product_v7 import require_product_v7_scope
            from src.security.product_v7_restore import PRODUCT_V7_RESTORE_KIND
            from src.security.final_v4_live_restore import FINAL_V4_LIVE_RESTORE_KIND
            # Empty/initializing roots have no restore evidence and must retain
            # the existing V4 first-run path.
            kind = (inspect_restore_kind(data_root, require_context=require_product_v7_scope,
                allowed_kinds={PRODUCT_V7_RESTORE_KIND, FINAL_V4_LIVE_RESTORE_KIND})
                if (data_root / "restore-transactions").exists() or (data_root / "restore-handoffs").exists() else None)
            if final_v7_restore_confirm and kind != PRODUCT_V7_RESTORE_KIND:
                raise RuntimeStorageError("cipher_restore_schema_mismatch")
            if final_v4_restore_confirm and not final_v7_restore_confirm and kind == PRODUCT_V7_RESTORE_KIND:
                raise RuntimeStorageError("cipher_restore_schema_mismatch")
            v6_restore = False
        if not internal_test and kind == PRODUCT_V7_RESTORE_KIND:
            from src.desktop_app.product_v7_runtime_adapters import (
                recover_product_v7_runtime_restore, confirm_product_v7_runtime_restore)
            if final_v7_restore_confirm:
                confirm_product_v7_runtime_restore(data_root, str(restore_confirm_id), str(restore_confirm_token))
            else:
                recovery = recover_product_v7_runtime_restore(data_root, on_verified_rollback=v6_recovery_context.append)
                if recovery.status == "resume_required":
                    confirm_product_v7_runtime_restore(data_root, str(recovery.restore_id), str(recovery.resume_token))
        elif v6_restore:
            if final_v4_restore_confirm:
                raise RuntimeStorageError("cipher_restore_schema_mismatch")
            if synthetic_v6_restore_confirm or synthetic_v7_restore_confirm:
                confirm_internal_test_v6_restore(data_root, str(restore_confirm_id), str(restore_confirm_token))
            else:
                recovery = recover_internal_test_v6_restore(
                    data_root, on_verified_rollback=v6_recovery_context.append)
                if recovery.status == "resume_required":
                    confirm_internal_test_v6_restore(data_root, str(recovery.restore_id), str(recovery.resume_token))
        else:
            if final_v4_restore_confirm:
                confirm_final_v4_restore_startup(
                    runtime_root=data_root,
                    restore_id=str(restore_confirm_id),
                    token=str(restore_confirm_token),
                    product_paths=runtime_paths(data_root),
                )
            else:
                recovery = recover_interrupted_final_v4_restore(
                    runtime_root=data_root,
                    product_paths=runtime_paths(data_root),
                )
                if recovery.status == "resume_required":
                    confirm_final_v4_restore_startup(
                        runtime_root=data_root,
                        restore_id=str(recovery.restore_id),
                        token=str(recovery.resume_token),
                        product_paths=runtime_paths(data_root),
                    )
        # Recovery may legitimately replace components. Reinventory its result;
        # never use the pre-recovery snapshot to authorize a fresh installation.
        startup_guard.evaluate()
        new_database_initialization_candidate = (
            _new_database_initialization_candidate(
                data_root,
                runtime_lock_path=lock.path,
            )
        )
        if internal_test and not new_database_initialization_candidate and not v6_recovery_context:
            from src.security.internal_test_v6_composition import preflight_internal_test_existing_runtime
            preflight_internal_test_existing_runtime(data_root, lock=lock)
    except UpgradeStartupBlocked:
        if lock is not None:
            runtime_stack.close()
            lock.release()
        _show_upgrade_startup_blocked(arguments, packaged_smoke=packaged_smoke)
        return 3
    except (RuntimeError, OSError) as error:
        if lock is not None:
            runtime_stack.close()
            lock.release()
        print(
            "App-Start wegen eines unsicheren Runtime-Zustands abgelehnt: "
            f"{error}",
            file=sys.stderr,
        )
        if internal_test:
            _show_upgrade_startup_blocked(arguments, packaged_smoke=packaged_smoke)
        return 3

    from PySide6.QtWidgets import QApplication, QMessageBox
    from src.desktop_app.theme import apply_app_theme
    from src.security.domain import SecurityStoreError
    from src.core.app_preferences import AppPreferences, AppPreferencesError
    from src.security.session import InMemorySession
    from src.security.startup import (
        SecurityStartState,
        SecurityStartupDecision,
        SecurityStartupResolver,
        build_security_runtime,
        legacy_installation_present,
    )
    from src.desktop_app.security_controller import (
        run_startup_authentication,
        run_startup_device_authentication,
        should_attempt_startup_device_authentication,
    )
    from src.desktop_app.security_ui import AuthenticationDialog

    sys.argv[:] = arguments
    app = QApplication(arguments)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Jenaplan")
    app.setOrganizationDomain(APP_BUNDLE_ID)
    app.setDesktopFileName(APP_BUNDLE_ID)
    app.setWindowIcon(_app_icon())
    apply_app_theme(app)
    security_event_buffer = begin_pre_auth_security_logging()

    try:
        if (
            root_protection is not None
            and root_protection.kind is RuntimeRootKind.PILOT_PRODUCT
            and root_protection.lifecycle is RuntimeRootLifecycle.ACTIVE
        ):
            security_paths = runtime_paths(data_root)
            _require_existing_product_security(security_paths)
        else:
            security_paths = prepare_security_runtime_storage(data_root=data_root)
        security_runtime = build_security_runtime(security_paths)
        if (
            root_protection is not None
            and root_protection.kind is RuntimeRootKind.PILOT_PRODUCT
            and root_protection.lifecycle is RuntimeRootLifecycle.ACTIVE
        ):
            security_runtime.repository.require_current_read_only()
            from src.security.final_v4_support_recovery import (
                FinalV4PreAuthRecoveryFactory,
            )

            support_reset_backup_factory = FinalV4PreAuthRecoveryFactory(
                paths=security_paths,
                account_loader=security_runtime.repository.load_account,
                security_store_validator=(
                    security_runtime.repository.require_current_read_only
                ),
            )
        else:
            support_reset_backup_factory = None
        security_state = security_runtime.service.security_store_state()
        security_decision = SecurityStartupResolver().resolve(
            security_state,
            legacy_installation_present=legacy_installation_present(security_paths),
        )
        if packaged_smoke:
            session = _isolated_packaged_smoke_session(
                security_runtime.service,
                security_runtime.repository,
                security_decision,
                mode=str(packaged_smoke_mode),
                data_root=data_root,
            )
        else:
            try:
                pre_auth_preferences = security_runtime.preferences.load()
            except AppPreferencesError:
                pre_auth_preferences = AppPreferences()
            authentication = None
            if should_attempt_startup_device_authentication(
                decision=security_decision,
                touch_id_preferred=pre_auth_preferences.touch_id_preferred,
            ):
                device_authentication = run_startup_device_authentication(
                    service=security_runtime.service,
                    repository=security_runtime.repository,
                    device_credentials=security_runtime.device_credentials,
                )
            else:
                device_authentication = None
            if device_authentication is not None:
                session = device_authentication.session
            else:
                authentication = run_startup_authentication(
                    service=security_runtime.service,
                    repository=security_runtime.repository,
                    decision=security_decision,
                    device_credentials=security_runtime.device_credentials,
                    touch_id_preferred=pre_auth_preferences.touch_id_preferred,
                    support_reset=security_runtime.support_reset,
                    support_reset_backup_factory=support_reset_backup_factory,
                )
                session = authentication.session if authentication is not None else None
            if authentication is not None and authentication.enrollment_completed:
                try:
                    current_preferences = security_runtime.preferences.load()
                except AppPreferencesError:
                    current_preferences = AppPreferences()
                try:
                    security_runtime.preferences.save(
                        replace(
                            current_preferences,
                            display_name=authentication.enrollment_display_name,
                        )
                    )
                except (OSError, ValueError, RuntimeError):
                    pass
        if session is None:
            discard_pre_auth_security_logging(security_event_buffer)
            runtime_stack.close()
            lock.release()
            return 0
    except (
        RuntimeStorageError,
        RuntimeRootProtectionError,
        SecurityStoreError,
    ) as error:
        logging.getLogger("jenaplan.security").error(
            "fatal_security_error error_class=%s", type(error).__name__
        )
        if packaged_smoke:
            print("Security-Pakettest blockiert.", file=sys.stderr)
            discard_pre_auth_security_logging(security_event_buffer)
            runtime_stack.close()
            lock.release()
            return 1
        security_decision = SecurityStartupDecision(
            SecurityStartState.FATAL_SECURITY_ERROR,
            "SEC-FATAL_SECURITY_ERROR",
        )
        AuthenticationDialog(
            service=None,
            repository=None,
            decision=security_decision,
        ).exec()
        discard_pre_auth_security_logging(security_event_buffer)
        runtime_stack.close()
        lock.release()
        return 1

    try:
        try:
            preferences = security_runtime.preferences.load()
        except AppPreferencesError:
            preferences = AppPreferences()
        from src.security.cipher_product_runtime import (
            CipherProductRuntimeError,
            CipherProductRuntimeOperation,
            open_cipher_product_runtime,
        )

        security_state = security_runtime.service.security_store_state()
        account = security_runtime.repository.load_account()
        _require_authenticated_cipher_context(
            session=session,
            security_state=security_state,
            account=account,
            security_epoch=security_runtime.repository.security_epoch(),
        )
        v6_service = None
        lesson_time_templates_adapter = None
        if internal_test and not new_database_initialization_candidate:
            from src.security.internal_test_v6_composition import (
                build_internal_test_v6_backup_service, internal_test_schema_identity,
                open_internal_test_v6_runtime,
            )
            from src.core.timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION
            if v6_recovery_context:
                if (len(v6_recovery_context) != 1
                        or v6_recovery_context[0].installation_id != account.installation_id):
                    raise RuntimeError("synthetic_v6_recovery_account_mismatch")
                candidate = build_internal_test_v6_backup_service(data_root,
                    authenticated_account=account, loaded_keys=v6_recovery_context[0].loaded)
            else:
                candidate = build_internal_test_v6_backup_service(data_root, authenticated_account=account)
            from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION
            if internal_test_schema_identity(candidate) in (SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION.identity, SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity):
                v6_service = candidate
        if (not internal_test and not new_database_initialization_candidate
                and (data_root / "schema-upgrade-source/transaction-timetable-weeks-v1/completed.json").exists()):
            from src.security.product_v7 import build_product_v7_service, product_schema_identity, TARGET, open_product_v7_runtime
            candidate = build_product_v7_service(data_root, authenticated_account=account,
                loaded_keys=v6_recovery_context[0].loaded if v6_recovery_context else None)
            if product_schema_identity(candidate) == TARGET:
                v6_service = candidate
        if v6_service is not None:
            runtime_opener = open_internal_test_v6_runtime if internal_test else open_product_v7_runtime
            product_runtime = runtime_stack.enter_context(runtime_opener(v6_service, lock=lock))
            from src.desktop_app.adapters.lesson_time_templates_desktop_adapter import LessonTimeTemplatesDesktopAdapter
            lesson_time_templates_adapter = LessonTimeTemplatesDesktopAdapter(product_runtime.runtime)
        else:
            product_runtime = open_cipher_product_runtime(
                paths=security_paths,
                account_loader=lambda: account,
                authentication_confirmed=True,
                first_run_allowed=(
                    new_database_initialization_candidate
                    and security_decision.state is SecurityStartState.FIRST_RUN
                ),
            )
        if product_runtime.installation_id != session.installation_id:
            raise CipherProductRuntimeError(
                "cipher_product_session_context_mismatch",
                operation=CipherProductRuntimeOperation.CLASSIFY,
            )
        paths = prepare_cipher_runtime_storage(data_root=data_root)
        configure_runtime_logging(paths)
        flush_pre_auth_security_logging(security_event_buffer)
        from src.desktop_app.app import JenaplanDesktopApp
        from src.application.commands.final_v4_backup_restore import (
            FinalV4EncryptedBackupApplicationService,
            FinalV4EncryptedRestoreApplicationService,
        )
        from src.desktop_app.adapters.backup_restore_desktop_adapter import (
            BackupRestoreDesktopAdapter,
        )
        from src.desktop_app.security_controller import SecurityUiCoordinator
        from src.desktop_app.final_v4_runtime_adapters import (
            DesktopFinalV4RestoreWorkerLauncher,
        )
        from src.security.final_v4_backup_runtime import (
            build_final_v4_encrypted_backup_service,
        )
        from src.security.final_v4_support_recovery import (
            FinalV4SupportResetBackupFactory,
        )

        student_adapter = _build_cipher_product_student_adapter(product_runtime)
        if (
            product_runtime.first_run
            and root_protection is not None
            and root_protection.kind is RuntimeRootKind.PILOT_PRODUCT
        ):
            root_protection = activate_pilot_product_root(data_root)
        if v6_service is None:
            encrypted_backup_service = build_final_v4_encrypted_backup_service(
                opened_runtime=product_runtime.runtime,
                account_loader=lambda: account,
                environ=os.environ,
                product_paths=security_paths,
            )
            support_reset_backup_factory = FinalV4SupportResetBackupFactory(
                service=encrypted_backup_service,
                backup_root=paths.backups,
            )
            restore_application_type = FinalV4EncryptedRestoreApplicationService
            worker_launcher = DesktopFinalV4RestoreWorkerLauncher()
        else:
            from src.application.commands.synthetic_v6_backup_restore import SyntheticV6EncryptedRestoreApplicationService
            from src.desktop_app.synthetic_v6_runtime_adapters import DesktopSyntheticV6RestoreWorkerLauncher
            from src.security.synthetic_v7_backup_runtime import SyntheticV7EncryptedBackupService
            if type(v6_service) is SyntheticV7EncryptedBackupService:
                from src.application.commands.synthetic_v7_backup_restore import SyntheticV7EncryptedRestoreApplicationService as SyntheticV6EncryptedRestoreApplicationService
                from src.desktop_app.synthetic_v7_runtime_adapters import DesktopSyntheticV7RestoreWorkerLauncher as DesktopSyntheticV6RestoreWorkerLauncher
            if not internal_test:
                from src.application.commands.product_v7_backup_restore import ProductV7RestoreApplicationService as SyntheticV6EncryptedRestoreApplicationService
                from src.desktop_app.product_v7_runtime_adapters import DesktopProductV7RestoreWorkerLauncher as DesktopSyntheticV6RestoreWorkerLauncher
            encrypted_backup_service = v6_service
            # The existing support-reset backup strategy is V4-specific. No
            # V4 reset capability is passed into a V6 session.
            support_reset_backup_factory = None
            restore_application_type = SyntheticV6EncryptedRestoreApplicationService
            worker_launcher = DesktopSyntheticV6RestoreWorkerLauncher()
        encrypted_backup_application = FinalV4EncryptedBackupApplicationService(encrypted_backup_service)
        from src.security.startup import finalize_security_runtime
        def before_restore_handoff():
            finalize_security_runtime(security_runtime, paths, lock)
        encrypted_restore_application = restore_application_type(
            encrypted_backup_service, lock=lock, worker_launcher=worker_launcher,
            before_handoff=before_restore_handoff,
        )
        build_info = load_build_info()
        backup_restore_adapter = BackupRestoreDesktopAdapter(
            paths,
            app_version=APP_VERSION,
            build_commit=str(build_info.get("git_commit", "unknown")),
            source_tree_state=(
                str(build_info["source_tree_state"])
                if build_info.get("source_tree_state") is not None
                else None
            ),
            lock=lock,
            backup_service=encrypted_backup_application,
            restore_service=encrypted_restore_application,
            enabled=True,
            backup_extension=".jkmebackup",
        )

        window = JenaplanDesktopApp(
            paths.final_v4_database,
            paths=paths,
            runtime_lock=lock,
            database_create_allowed=False,
            student_adapter=student_adapter,
            backup_restore_available=True,
            backup_restore_adapter=backup_restore_adapter,
            lesson_time_templates_adapter=lesson_time_templates_adapter,
        )
        window.configure_school_year_transition_activation(
            security_runtime.service
        )
        window.security_coordinator = SecurityUiCoordinator(
            app=app,
            shell=window,
            service=security_runtime.service,
            repository=security_runtime.repository,
            preferences_file=security_runtime.preferences,
            session=session,
            inactivity_minutes=preferences.inactivity_minutes,
            display_name=preferences.display_name,
            device_credentials=security_runtime.device_credentials,
            touch_id_preferred=preferences.touch_id_preferred,
            support_reset=security_runtime.support_reset,
            support_reset_backup_factory=support_reset_backup_factory,
        )
        window.configure_onboarding(
            preferences_file=security_runtime.preferences,
            preferences=preferences,
            automatic_open=True,
            packaged_smoke=packaged_smoke,
        )
    except RuntimeStorageError as error:
        if packaged_smoke:
            print("Runtime-Pakettest blockiert.", file=sys.stderr)
            runtime_stack.close()
            lock.release()
            return 1
        QMessageBox.critical(
            None,
            "App-Daten nicht zugänglich",
            f"{error}\n\nDie App wurde nicht gestartet, damit keine Daten gefährdet werden.",
        )
        runtime_stack.close()
        lock.release()
        return 1
    except CipherProductRuntimeError as error:
        logging.getLogger("jenaplan.security").error(
            "cipher_product_startup_blocked code=%s operation=%s",
            error.code,
            error.operation.value,
        )
        if packaged_smoke:
            print(f"Cipher-Pakettest blockiert: {error.code}", file=sys.stderr)
            runtime_stack.close()
            lock.release()
            return 4
        QMessageBox.critical(
            None,
            "Verschlüsselter Datenbestand nicht verfügbar",
            "Die verschlüsselte lokale Datenablage konnte nicht sicher geöffnet "
            f"werden. Technischer Code: {error.code}",
        )
        runtime_stack.close()
        lock.release()
        return 4
    except Exception as error:  # pragma: no cover - startup/platform feedback
        logging.exception("Die App konnte nicht initialisiert werden.")
        if packaged_smoke:
            print("Pakettest-Initialisierung blockiert.", file=sys.stderr)
            runtime_stack.close()
            lock.release()
            return 1
        QMessageBox.critical(
            None,
            "App konnte nicht gestartet werden",
            "Die lokale Datenbank oder eine benötigte Ressource konnte nicht "
            f"geöffnet werden.\n\nDatenordner: {data_root}\nFehler: {error}",
        )
        runtime_stack.close()
        lock.release()
        return 1

    window.setWindowIcon(_app_icon())
    from src.security.startup import finalize_security_runtime
    if packaged_smoke:
        try:
            result = _run_packaged_smoke(
                app,
                window,
                paths,
                mode=str(packaged_smoke_mode),
                product_runtime=product_runtime,
                security_runtime=security_runtime,
                backup_application=encrypted_backup_application,
                restore_application=encrypted_restore_application,
                login_authenticated=session is not None,
            )
            if (not encrypted_restore_application.handoff_transferred
                    and packaged_smoke_mode != "restore-ready"):
                finalize_security_runtime(security_runtime, paths, lock)
            return result
        finally:
            runtime_stack.close()
            lock.release()
    window.showMaximized()
    try:
        result = app.exec()
        if not encrypted_restore_application.handoff_transferred:
            finalize_security_runtime(security_runtime, paths, lock)
        return result
    finally:
        runtime_stack.close()
        lock.release()


def _isolated_packaged_smoke_session(
    service,
    repository,
    decision,
    *,
    mode: str,
    data_root: Path,
) -> InMemorySession:
    """Automate auth only after the caller proved double smoke isolation."""
    from src.security.domain import AuthenticationStatus
    from src.security.session import InMemorySession
    from src.security.startup import SecurityStartState

    if mode == "initialize" and decision.state is not SecurityStartState.FIRST_RUN:
        raise RuntimeStorageError(
            "Der isolierte Pakettest erwartet eine neue temporaere Sicherheitsablage."
        )
    if mode != "initialize" and decision.state is not SecurityStartState.LOGIN_REQUIRED:
        raise RuntimeStorageError(
            "Der isolierte Pakettest erwartet eine bestehende Sicherheitsablage."
        )
    password = _packaged_smoke_password(data_root)
    if mode == "initialize":
        prepared = service.prepare_local_account_enrollment(password)
        if not service.confirm_local_account_enrollment(prepared.recovery_set_id):
            raise RuntimeStorageError("Der isolierte Pakettest konnte Auth nicht aktivieren.")
    result = service.authenticate_password(password)
    password = ""
    if result.status is not AuthenticationStatus.AUTHENTICATED:
        raise RuntimeStorageError("Der isolierte Pakettest konnte Auth nicht bestaetigen.")
    state = service.security_store_state()
    if state.user_id is None or state.installation_id is None:
        raise RuntimeStorageError("Der isolierte Pakettest hat keine Sitzungsbindung.")
    return InMemorySession(
        state.user_id,
        state.installation_id,
        repository.security_epoch(),
    )


def _packaged_smoke_password(data_root: Path) -> str:
    digest = hashlib.sha256(
        f"packaged-final-v4:{Path(data_root).name}".encode("utf-8")
    ).hexdigest()
    return f"synthetic-only-{digest}"


def _run_packaged_smoke(
    app: QApplication,
    window: JenaplanDesktopApp,
    paths: RuntimePaths,
    *,
    mode: str,
    product_runtime,
    security_runtime,
    backup_application,
    restore_application,
    login_authenticated: bool,
) -> int:
    """Exercise the frozen Final-V4 runtime without a broad UI automation."""
    from src.application.commands.backup import CreateBackupCommand
    from src.application.commands.restore import (
        CreateRestoreHandoffCommand,
        VerifyRestoreBackupQuery,
    )
    from src.core.restore_runtime import RestoreJournal, restore_transaction_paths
    from src.desktop_app.restore_worker import resolve_restore_worker_launch
    from src.security.final_v4_live_restore import recover_interrupted_final_v4_restore

    window.show()
    app.processEvents()
    build_info = load_build_info()
    current_school_year = window.adapter.current_school_year()
    student_count = (
        len(window.adapter.list_students())
        if current_school_year is not None
        else 0
    )
    competency_count = len(window.curriculum_adapter.list_entries())
    compatibility = product_runtime.runtime.final_v4.compatibility
    payload: dict[str, object] = {
        "app_version": APP_VERSION,
        "build_info": build_info,
        "cipher_provider": compatibility.cipher_provider,
        "cipher_version": compatibility.cipher_version,
        "competency_count": competency_count,
        "database_context_id": product_runtime.database_context_id,
        "database_key_fingerprint_sha256": product_runtime.database_key_fingerprint_sha256,
        "data_root": str(paths.root),
        "dmk_fingerprint_sha256": product_runtime.dmk_fingerprint_sha256,
        "final_v4": compatibility.sqlite_user_version,
        "schema_version": compatibility.sqlite_user_version,
        "lesson_time_templates_available": window.lesson_time_templates_adapter is not None,
        "first_run": product_runtime.first_run,
        "login_authenticated": login_authenticated,
        "mode": mode,
        "school_year_state": (
            "current" if current_school_year is not None else "missing"
        ),
        "school_year": (
            current_school_year.label if current_school_year is not None else ""
        ),
        "sqlite_version": compatibility.sqlite_version,
        "student_count": student_count,
        "window_title": window.windowTitle(),
    }
    if mode == "migration-source":
        from scripts.seed_test_data import seed_cipher_pilot_test_data
        if compatibility.sqlite_user_version != 4:
            raise RuntimeStorageError("migration_source_v4_required")
        seed_cipher_pilot_test_data(product_runtime, source_root=paths.root)
    elif mode == "v7-write":
        from datetime import date
        from src.desktop_app.adapters.timetable_desktop_adapter import TimetableDesktopAdapter
        if compatibility.sqlite_user_version != 7 or window.lesson_time_templates_adapter is None:
            raise RuntimeStorageError("migration_target_v7_required")
        timetable = TimetableDesktopAdapter(product_runtime.database)
        timetable.configure_week_cycle(date(2026, 10, 26), "A")
        timetable.set_week_override(date(2026, 11, 2), "A")
        product_runtime.runtime.lesson_time_templates.set_times(1, "08:00", "08:45")
        if not timetable.week_assignment(date(2026, 11, 2)).manual:
            raise RuntimeStorageError("migration_target_write_failed")
    if mode in {"migration-source", "migration-snapshot", "v7-write"}:
        from contextlib import closing
        from src.core.database_content_evidence import database_content_evidence
        with closing(product_runtime.database.connect()) as connection:
            payload["main_content"] = database_content_evidence(connection).tables
        documents = product_runtime.documents
        documents.validate_restart()
        payload["managed_document_hashes"] = {
            str(path.relative_to(paths.root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths.root.rglob("*.jkmedoc"))
        }
    if mode in {"restore-worker", "restore-ready", "restore-parent-exit"}:
        backup_result = backup_application.create(
            CreateBackupCommand(
                database_path=paths.final_v4_database,
                runtime_paths=paths,
                target_path=paths.backups,
                app_version=APP_VERSION,
                build_commit=str(build_info.get("git_commit", "unknown")),
                source_tree_state=(
                    str(build_info["source_tree_state"])
                    if build_info.get("source_tree_state") is not None
                    else None
                ),
            )
        )
        restore = restore_application.verify(
            VerifyRestoreBackupQuery(backup_result.path)
        )
        handoff = restore_application.create_handoff(
            CreateRestoreHandoffCommand(
                backup_result.path,
                restore.restore_id,
                paths,
                APP_VERSION,
                str(build_info.get("git_commit", "unknown")),
                str(build_info.get("source_tree_state", "dirty")),
            )
        )
        if mode == "restore-ready":
            restore_application._preparations[restore.restore_id].safety_backup.transfer_to_worker()
            payload["restore"] = {"ready_state": "RESTORE_READY", "restore_id": restore.restore_id}
            window.restore_handoff_started.emit()
            window.close()
            app.processEvents()
            print(json.dumps(payload, sort_keys=True), flush=True)
            return 0
        plan = resolve_restore_worker_launch(paths.root)
        started = restore_application.launch_prepared_restore(handoff)
        if mode == "restore-parent-exit":
            from src.core.restore_runtime import _process_start_identity
            payload["restore"] = {"worker_pid": started.process.pid, "restore_id": restore.restore_id,
                                  "worker_start_identity": _process_start_identity(started.process.pid),
                                  "parent_pid": os.getpid(),
                                  "ready_state": "RESTORE_READY", "command_prefix": list(plan.command_prefix)}
            print(json.dumps(payload, sort_keys=True), flush=True)
            # Real parent death releases the lifetime pipe. Worker owns the handoff.
            os._exit(0)
        try:
            state = RestoreJournal(
                restore_transaction_paths(paths.root, restore.restore_id)
            ).read()
            if state.get("phase") != "worker_started":
                raise RuntimeError("cipher_restore_worker_not_started")
            payload["restore"] = {
                "backup_suffix": backup_result.path.suffix,
                "command_prefix": list(plan.command_prefix),
                "ready_state": "RESTORE_READY",
                "worker_phase": state.get("phase"),
            }
        finally:
            if started.process.poll() is None:
                started.process.terminate()
            started.process.wait(timeout=5)
            os.close(started.parent_lifetime_fd)
        if compatibility.sqlite_user_version in (6, 7):
            from src.desktop_app.synthetic_v6_runtime_adapters import recover_internal_test_v6_restore
            if compatibility.sqlite_user_version == 7:
                from src.desktop_app.synthetic_v7_runtime_adapters import recover_internal_test_v7_restore as recover_internal_test_v6_restore
            from src.core.macos_test_package_profile import test_identity
            if compatibility.sqlite_user_version == 7 and test_identity() is None:
                from src.desktop_app.product_v7_runtime_adapters import recover_product_v7_runtime_restore
                recovery = recover_product_v7_runtime_restore(paths.root)
            else:
                recovery = recover_internal_test_v6_restore(paths.root)
        else:
            recovery = recover_interrupted_final_v4_restore(
                runtime_root=paths.root,
                product_paths=paths,
            )
        payload["restore"]["recovery"] = recovery.status
    elif mode == "cleanup":
        from src.security.data_keys import DataMasterKeyService
        from src.security.infrastructure.data_keyset_repository import (
            SQLiteDataKeysetRepository,
        )
        from src.security.infrastructure.data_master_key_store import (
            build_platform_data_master_key_store,
        )
        from src.security.infrastructure.system import (
            PlatformFilePermissionManager,
            SystemRandomSource,
        )

        repository = SQLiteDataKeysetRepository(
            paths.keyset_metadata,
            PlatformFilePermissionManager(),
        )
        repository.initialize()
        deleted = DataMasterKeyService(
            repository=repository,
            key_store=build_platform_data_master_key_store(),
            random_source=SystemRandomSource(),
            account_loader=security_runtime.repository.load_account,
        ).delete()
        if not deleted or repository.active_data_keyset() is not None:
            raise RuntimeStorageError("Final-V4-Pakettest-Keychain-Cleanup fehlgeschlagen.")
        payload["keychain_cleanup"] = "ok"
    elif mode not in {"initialize", "restart", "migration-source", "migration-snapshot", "v7-write"}:
        raise RuntimeStorageError("Unbekannter Final-V4-Pakettestmodus.")
    window.close()
    app.processEvents()
    payload["regular_exit_completed"] = not window.isVisible()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


def _run_packaged_runtime_audit() -> int:
    """Report exact native database versions from the frozen bundle only."""
    from importlib import metadata

    from src.core.database_engine import (
        SQLCIPHER_4_17_BINDING_VERSION,
        SQLCIPHER_4_17_ENGINE_VERSION,
        SQLCIPHER_4_17_SQLITE_VERSION,
    )

    if not getattr(sys, "frozen", False):
        print("Packaged-Runtime-Audit benötigt ein App-Bundle.", file=sys.stderr)
        return 2
    import sqlcipher3

    with tempfile.TemporaryDirectory(prefix="jkm-packaged-runtime-audit-") as temp:
        database = Path(temp) / "audit.sqlcipher"
        connection = sqlcipher3.connect(database)
        try:
            connection.execute("PRAGMA key = \"x'" + ("00" * 32) + "'\"")
            connection.execute("CREATE TABLE audit(value TEXT NOT NULL)")
            connection.execute("INSERT INTO audit VALUES ('synthetic')")
            connection.commit()
            payload = {
                "binding": metadata.version("sqlcipher3"),
                "cipher_provider": str(
                    connection.execute("PRAGMA cipher_provider").fetchone()[0]
                ),
                "cipher_version": str(
                    connection.execute("PRAGMA cipher_version").fetchone()[0]
                ),
                "integrity": connection.execute(
                    "PRAGMA cipher_integrity_check"
                ).fetchall(),
                "sqlite_version": str(
                    connection.execute("SELECT sqlite_version()").fetchone()[0]
                ),
            }
        finally:
            connection.close()
    if payload != {
        "binding": SQLCIPHER_4_17_BINDING_VERSION,
        "cipher_provider": "commoncrypto",
        "cipher_version": SQLCIPHER_4_17_ENGINE_VERSION,
        "integrity": [],
        "sqlite_version": SQLCIPHER_4_17_SQLITE_VERSION,
    }:
        print("Packaged-Runtime-Audit meldet eine unerwartete Runtime.", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
