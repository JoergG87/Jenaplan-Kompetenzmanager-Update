"""Product V7 strategy for existing backup/restore application commands."""
from src.application.commands.final_v4_backup_restore import FinalV4EncryptedRestoreApplicationService
from src.security.product_v7 import ProductV7BackupService, TARGET
from src.security.product_v7_restore import prepare_product_v7_restore


class ProductV7RestoreApplicationService(FinalV4EncryptedRestoreApplicationService):
    schema_version = TARGET.schema_version
    schema_fingerprint = TARGET.fingerprint

    def __init__(self, service, **kwargs):
        if type(service) is not ProductV7BackupService:
            raise ValueError("product_v7_backup_service_required")
        service.require_synthetic()
        super().__init__(service, **kwargs)

    def prepare_restore(self, **kwargs):
        return prepare_product_v7_restore(**kwargs, before_handoff=self._before_handoff)
