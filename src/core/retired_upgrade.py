"""Terminal rejection of the superseded file-exchange upgrade mechanism."""
from src.core.schema_upgrade import UpgradeError


class RetiredUpgradeAPI:
    def __init__(self, *args, **kwargs):
        self._deny()

    @staticmethod
    def _deny(*args, **kwargs):
        raise UpgradeError("upgrade_file_exchange_retired")

    # Also reject unbound invocation with an old/deserialized object.
    __enter__ = __exit__ = require_owner = execute = _deny
    create = save = load = load_with_digest = exists = _deny
    delete_completed = peek_context = verify = _deny
    validate_context = verify_source = create_backup = verify_backup = _deny
    create_staging = verify_staging = _deny
