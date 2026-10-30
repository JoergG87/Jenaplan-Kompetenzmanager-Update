"""Separate additive synthetic V7 identity; V6 and product registry unchanged."""
from .schema_registry import DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION, RegisteredSchemaIdentity, SCHEMA_FINGERPRINT_ALGORITHM, SchemaRegistration, SchemaUpgradeRelation
from .timetable_schema import SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION

TIMETABLE_WEEKS_STATEMENTS = (
    "ALTER TABLE timetable_entries ADD COLUMN week_pattern TEXT NOT NULL DEFAULT 'all' CHECK (week_pattern IN ('all','A','B'))",
    "CREATE TABLE timetable_week_cycle (singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1), reference_monday TEXT NOT NULL, reference_kind TEXT NOT NULL CHECK (reference_kind IN ('A','B')))",
    "CREATE TABLE timetable_week_overrides (week_monday TEXT PRIMARY KEY NOT NULL, week_kind TEXT NOT NULL CHECK (week_kind IN ('A','B')))",
)
SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION = SchemaRegistration(
    "synthetic_v7_timetable_weeks", RegisteredSchemaIdentity(7, "909d9d366218a61df8f2107088d6653188d93faf7c8796e3cc9aff07ccba5c55", SCHEMA_FINGERPRINT_ALGORITHM), frozenset())
SYNTHETIC_TIMETABLE_WEEKS_REGISTRY = DatabaseSchemaRegistry(
    (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION, SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION),
    tuple(SchemaUpgradeRelation(source.identity, SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity)
        for source in (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_TIMETABLE_SCHEMA_REGISTRATION)))

# Current product composition uses this versioned registry. Historical A0/A2
# codecs deliberately retain their closed V4-only registry.
from .schema_registry import SchemaAdmission
PRODUCT_V7_SCHEMA_REGISTRATION = SchemaRegistration(
    "product_v7_timetable_weeks", SYNTHETIC_TIMETABLE_WEEKS_SCHEMA_REGISTRATION.identity,
    frozenset({SchemaAdmission.RUNTIME, SchemaAdmission.HISTORICAL_INSPECTION}))
PRODUCT_V7_SCHEMA_REGISTRY = DatabaseSchemaRegistry(
    (FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_V7_SCHEMA_REGISTRATION),
    (SchemaUpgradeRelation(FINAL_V4_SCHEMA_REGISTRATION.identity,
                          PRODUCT_V7_SCHEMA_REGISTRATION.identity),))
