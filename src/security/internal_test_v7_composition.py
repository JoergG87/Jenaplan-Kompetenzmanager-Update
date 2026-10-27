"""V7 strategy selectors for the existing sealed internal-test composition."""
from src.security.internal_test_v6_composition import (require_internal_test_v6_context as require_internal_test_v7_context,
    InternalTestStartupGuard, build_internal_test_v6_backup_service)
from src.core.timetable_weeks_schema import SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION


def build_internal_test_v7_backup_service(root, **kwargs):
    return build_internal_test_v6_backup_service(root,
        schema_identity=SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity, **kwargs)
