"""Explicit synthetic target. Does not extend PRODUCT_SCHEMA_REGISTRY."""
from .schema_registry import (
    DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION, RegisteredSchemaIdentity,
    SCHEMA_FINGERPRINT_ALGORITHM, SchemaRegistration, SchemaUpgradeRelation,
)

LESSON_TIME_TEMPLATE_STATEMENT = """CREATE TABLE lesson_time_templates (
    lesson_number INTEGER PRIMARY KEY CHECK (lesson_number > 0),
    start_time TEXT NOT NULL CHECK (
        length(start_time) = 5 AND start_time GLOB '[0-2][0-9]:[0-5][0-9]'
        AND start_time < '24:00'),
    end_time TEXT NOT NULL CHECK (
        length(end_time) = 5 AND end_time GLOB '[0-2][0-9]:[0-5][0-9]'
        AND end_time < '24:00' AND start_time < end_time)
)"""

# Exact fingerprint measured using the audited SQLCipher 4.17 schema source.
SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION = SchemaRegistration(
    "synthetic_v5_lesson_times",
    RegisteredSchemaIdentity(5, "21f9af621c54a31e476161a6ee8c916bfd248acbd8d443bed979d27d67f9d1af",
                             SCHEMA_FINGERPRINT_ALGORITHM),
    frozenset(),
)
SYNTHETIC_LESSON_TIMES_REGISTRY = DatabaseSchemaRegistry(
    (FINAL_V4_SCHEMA_REGISTRATION, SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION),
    (SchemaUpgradeRelation(FINAL_V4_SCHEMA_REGISTRATION.identity,
                          SYNTHETIC_LESSON_TIMES_SCHEMA_REGISTRATION.identity),),
)
