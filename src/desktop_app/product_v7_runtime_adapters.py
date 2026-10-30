"""Product V7 adapters for existing restore worker and authenticated restart."""
from src.desktop_app.final_v4_runtime_adapters import DesktopFinalV4RestartLauncher
from src.desktop_app.restore_worker import launch_restore_worker
from src.security.product_v7 import build_product_v7_service, require_product_v7_scope
from src.security.product_v7_restore import (
    ProductV7LiveRestoreService, ProductV7RestoreHandoffService,
    PRODUCT_V7_RESTORE_KIND, recover_product_v7_restore, confirm_product_v7_restore,
)


class DesktopProductV7RestoreWorkerLauncher:
    def launch(self, *, handoff, nonce, lock):
        require_product_v7_scope(lock.runtime_root)
        return launch_restore_worker(handoff=handoff, nonce=nonce, lock=lock,
            restore_mode="final_v7_encrypted")


class DesktopProductV7RestartLauncher(DesktopFinalV4RestartLauncher):
    confirm_argument = "--final-v7-restore-confirm"


def build_product_v7_restore_verifier(root):
    from src.desktop_app.synthetic_v7_runtime_adapters import _build_v7_restore_verifier
    return _build_v7_restore_verifier(root,
        require_context=require_product_v7_scope,
        service_builder=build_product_v7_service,
        restore_kind=PRODUCT_V7_RESTORE_KIND,
        handoff_type=ProductV7RestoreHandoffService)


def build_product_v7_restore_worker_service(root, *, lock):
    if lock.runtime_root != root:
        raise RuntimeError("product_v7_worker_root_mismatch")
    from src.security.upgrade_startup import ProductUpgradeStartupGuard
    ProductUpgradeStartupGuard(lock)._require_lock()
    return ProductV7LiveRestoreService(build_product_v7_service(root),
        restart_launcher=DesktopProductV7RestartLauncher())


def recover_product_v7_runtime_restore(root, *, on_verified_rollback=None):
    service = build_product_v7_restore_verifier(root)
    result = recover_product_v7_restore(backup_service=service, runtime_root=root)
    if result.status == "rolled_back" and on_verified_rollback is not None:
        on_verified_rollback(service)
    return result


def confirm_product_v7_runtime_restore(root, restore_id, token):
    return confirm_product_v7_restore(backup_service=build_product_v7_service(root),
        runtime_root=root, restore_id=restore_id, token=token)
