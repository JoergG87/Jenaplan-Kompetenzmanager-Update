"""Pure schema admissions; no database opening, migration or runtime wiring."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from collections.abc import Iterable, Mapping

from .database_compatibility import FINAL_SCHEMA_FINGERPRINT, FINAL_SCHEMA_VERSION

# Names the existing compatibility algorithm; does not implement or alter it.
SCHEMA_FINGERPRINT_ALGORITHM = "sqlite-schema-canonical-json-sha256-v1"


class SchemaRegistryError(ValueError):
    """Controlled failure without database contents, paths or keys."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class RegisteredSchemaIdentity:
    schema_version: int
    fingerprint: str
    fingerprint_algorithm: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise SchemaRegistryError("schema_version_invalid")
        if not isinstance(self.fingerprint, str) or re.fullmatch(
            r"[0-9a-f]{64}", self.fingerprint
        ) is None:
            raise SchemaRegistryError("schema_fingerprint_invalid")
        if self.fingerprint_algorithm != SCHEMA_FINGERPRINT_ALGORITHM:
            raise SchemaRegistryError("schema_fingerprint_algorithm_unsupported")


class SchemaAdmission(str, Enum):
    RUNTIME = "runtime"
    HISTORICAL_INSPECTION = "historical_inspection"


@dataclass(frozen=True)
class SchemaRegistration:
    schema_id: str
    identity: RegisteredSchemaIdentity
    admissions: frozenset[SchemaAdmission]

    def __post_init__(self) -> None:
        if not isinstance(self.schema_id, str) or re.fullmatch(
            r"[a-z][a-z0-9_-]{0,79}", self.schema_id
        ) is None:
            raise SchemaRegistryError("schema_id_invalid")
        if not isinstance(self.identity, RegisteredSchemaIdentity):
            raise SchemaRegistryError("schema_identity_invalid")
        admissions = frozenset(self.admissions)
        if any(not isinstance(item, SchemaAdmission) for item in admissions):
            raise SchemaRegistryError("schema_admission_invalid")
        object.__setattr__(self, "admissions", admissions)


@dataclass(frozen=True)
class SchemaUpgradeRelation:
    source: RegisteredSchemaIdentity
    target: RegisteredSchemaIdentity

    def __post_init__(self) -> None:
        if not all(isinstance(item, RegisteredSchemaIdentity)
                   for item in (self.source, self.target)):
            raise SchemaRegistryError("schema_upgrade_identity_invalid")
        if self.source == self.target:
            raise SchemaRegistryError("schema_upgrade_self_relation")


@dataclass(frozen=True, init=False)
class DatabaseSchemaRegistry:
    """Immutable exact allowlist. Admissions never imply an upgrade relation.

    An admission is metadata only: callers must separately enforce isolation,
    integrity, keys and lifecycle gates. This class performs no I/O.
    """

    _schemas: Mapping[RegisteredSchemaIdentity, SchemaRegistration]
    _upgrades: frozenset[SchemaUpgradeRelation]

    def __init__(
        self,
        schemas: Iterable[SchemaRegistration],
        upgrades: Iterable[SchemaUpgradeRelation] = (),
    ) -> None:
        by_identity = {}
        names = set()
        fingerprints = set()
        for schema in schemas:
            if not isinstance(schema, SchemaRegistration):
                raise SchemaRegistryError("schema_registration_invalid")
            if schema.schema_id in names or schema.identity in by_identity:
                raise SchemaRegistryError("schema_registration_duplicate")
            fingerprint_key = (schema.identity.fingerprint_algorithm,
                               schema.identity.fingerprint)
            if fingerprint_key in fingerprints:
                raise SchemaRegistryError("schema_registration_conflicting")
            names.add(schema.schema_id)
            fingerprints.add(fingerprint_key)
            by_identity[schema.identity] = schema
        relations = set()
        for relation in upgrades:
            if not isinstance(relation, SchemaUpgradeRelation):
                raise SchemaRegistryError("schema_upgrade_relation_invalid")
            if relation.source not in by_identity or relation.target not in by_identity:
                raise SchemaRegistryError("schema_upgrade_endpoint_unknown")
            if relation in relations:
                raise SchemaRegistryError("schema_upgrade_relation_duplicate")
            relations.add(relation)
        object.__setattr__(self, "_schemas", MappingProxyType(by_identity))
        object.__setattr__(self, "_upgrades", frozenset(relations))

    @property
    def schemas(self) -> tuple[SchemaRegistration, ...]:
        return tuple(self._schemas.values())

    @property
    def upgrades(self) -> frozenset[SchemaUpgradeRelation]:
        return self._upgrades

    def identify(self, identity: RegisteredSchemaIdentity) -> SchemaRegistration:
        if not isinstance(identity, RegisteredSchemaIdentity):
            raise SchemaRegistryError("schema_identity_invalid")
        registration = self._schemas.get(identity)
        if registration is None:
            raise SchemaRegistryError("schema_unknown")
        return registration

    def require_admission(
        self, identity: RegisteredSchemaIdentity, admission: SchemaAdmission
    ) -> SchemaRegistration:
        if not isinstance(admission, SchemaAdmission):
            raise SchemaRegistryError("schema_admission_invalid")
        registration = self.identify(identity)
        if admission not in registration.admissions:
            raise SchemaRegistryError("schema_admission_denied")
        return registration

    def require_upgrade(
        self, source: RegisteredSchemaIdentity, target: RegisteredSchemaIdentity
    ) -> SchemaUpgradeRelation:
        self.identify(source)
        self.identify(target)
        relation = SchemaUpgradeRelation(source, target)
        if relation not in self._upgrades:
            raise SchemaRegistryError("schema_upgrade_denied")
        return relation


FINAL_V4_SCHEMA_REGISTRATION = SchemaRegistration(
    schema_id="final_v4",
    identity=RegisteredSchemaIdentity(
        FINAL_SCHEMA_VERSION, FINAL_SCHEMA_FINGERPRINT, SCHEMA_FINGERPRINT_ALGORITHM
    ),
    admissions=frozenset({SchemaAdmission.RUNTIME, SchemaAdmission.HISTORICAL_INSPECTION}),
)
PRODUCT_SCHEMA_REGISTRY = DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION,))
