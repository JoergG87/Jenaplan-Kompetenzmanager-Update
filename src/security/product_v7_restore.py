"""Exact product V7 strategy, using the existing cipher restore state machine."""
from src.security.product_v7 import ProductV7BackupService, require_product_v7_scope
from src.security.synthetic_v7_live_restore import (
    SyntheticV7EncryptedRestoreHandoffService, SyntheticV7EncryptedLiveRestoreService,
    prepare_synthetic_v7_live_restore as _prepare,
    confirm_synthetic_v7_restore_startup as _confirm,
    recover_interrupted_synthetic_v7_restore as _recover,
)

PRODUCT_V7_RESTORE_KIND = "product_v7_encrypted_same_installation"


class ProductV7RestoreHandoffService(SyntheticV7EncryptedRestoreHandoffService):
    expected_backup_service_type = ProductV7BackupService
    restore_kind = PRODUCT_V7_RESTORE_KIND
    authentication_purpose = "jenaplan-kompetenzmanager/product-v7-live-restore-handoff/v1"
    require_root = staticmethod(require_product_v7_scope)


def _require_product_service(service):
    if type(service) is not ProductV7BackupService:
        from src.core.restore_runtime import RestorePreflightError
        raise RestorePreflightError("Der Produkt-V7-Backupvertrag fehlt.")
    service.require_synthetic()


class ProductV7LiveRestoreService(SyntheticV7EncryptedLiveRestoreService):
    def __init__(self, backup_service, **kwargs):
        _require_product_service(backup_service)
        super().__init__(backup_service, **kwargs)


def prepare_product_v7_restore(*, backup_service, **kwargs):
    _require_product_service(backup_service)
    return _prepare(backup_service=backup_service, **kwargs)


def confirm_product_v7_restore(*, backup_service, **kwargs):
    _require_product_service(backup_service)
    return _confirm(backup_service=backup_service, **kwargs)


def recover_product_v7_restore(*, backup_service, **kwargs):
    _require_product_service(backup_service)
    return _recover(backup_service=backup_service, **kwargs)
