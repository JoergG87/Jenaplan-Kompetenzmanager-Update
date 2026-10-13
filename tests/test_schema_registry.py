"""Exact schema admissions; all alternate registrations are test-local."""
from dataclasses import FrozenInstanceError, replace
import pytest

from src.core.database_compatibility import (
    DatabaseCompatibilityInspector, DatabaseCompatibilityPolicy,
    DatabaseCompatibilityStatus, FINAL_SCHEMA_FINGERPRINT, FINAL_SCHEMA_VERSION,
)
from src.core.final_v4_schema import FinalV4SchemaInitializer
from src.core.schema_registry import (
    DatabaseSchemaRegistry, FINAL_V4_SCHEMA_REGISTRATION, PRODUCT_SCHEMA_REGISTRY,
    RegisteredSchemaIdentity, SCHEMA_FINGERPRINT_ALGORITHM, SchemaAdmission,
    SchemaRegistration, SchemaRegistryError, SchemaUpgradeRelation,
)


def synthetic(version=5, fingerprint="b" * 64, admissions=()):
    return SchemaRegistration(
        f"synthetic_{version}",
        RegisteredSchemaIdentity(version, fingerprint, SCHEMA_FINGERPRINT_ALGORITHM),
        frozenset(admissions),
    )


def test_real_final_v4_matches_unchanged_fingerprint_and_policy(tmp_path):
    path = tmp_path / "final.sqlite"
    FinalV4SchemaInitializer().initialize(path)
    before = path.read_bytes()
    result = DatabaseCompatibilityInspector().inspect(path)
    identity = RegisteredSchemaIdentity(
        result.version.sqlite_user_version, result.schema_identity.fingerprint,
        SCHEMA_FINGERPRINT_ALGORITHM,
    )
    assert identity == FINAL_V4_SCHEMA_REGISTRATION.identity
    assert identity.schema_version == FINAL_SCHEMA_VERSION == 4
    assert identity.fingerprint == FINAL_SCHEMA_FINGERPRINT == (
        "a3a4ec7694daf60fe90a547036f5d7573f4875800a411f923485e76582ea3516"
    )
    assert result.status is DatabaseCompatibilityStatus.EXACT
    assert DatabaseCompatibilityPolicy.require_backup_compatible(result) is result
    assert PRODUCT_SCHEMA_REGISTRY.require_admission(
        identity, SchemaAdmission.RUNTIME
    ) is FINAL_V4_SCHEMA_REGISTRATION
    assert path.read_bytes() == before


@pytest.mark.parametrize("version,fingerprint", [(3, FINAL_SCHEMA_FINGERPRINT),
    (5, FINAL_SCHEMA_FINGERPRINT), (4, "f" * 64), (6, "c" * 64)])
def test_unknown_identity_never_admitted(version, fingerprint):
    identity = RegisteredSchemaIdentity(version, fingerprint, SCHEMA_FINGERPRINT_ALGORITHM)
    for admission in SchemaAdmission:
        with pytest.raises(SchemaRegistryError, match="schema_unknown"):
            PRODUCT_SCHEMA_REGISTRY.require_admission(identity, admission)


def test_unknown_algorithm_never_admitted():
    with pytest.raises(SchemaRegistryError, match="algorithm_unsupported"):
        replace(FINAL_V4_SCHEMA_REGISTRATION.identity, fingerprint_algorithm="other")


@pytest.mark.parametrize("changes", [{"schema_version": True}, {"schema_version": 0},
    {"fingerprint": "A" * 64}, {"fingerprint": "bad"}])
def test_malformed_identity_rejected(changes):
    with pytest.raises(SchemaRegistryError):
        replace(FINAL_V4_SCHEMA_REGISTRATION.identity, **changes)


@pytest.mark.parametrize("duplicate", [
    FINAL_V4_SCHEMA_REGISTRATION,
    replace(FINAL_V4_SCHEMA_REGISTRATION, admissions=frozenset()),
    replace(FINAL_V4_SCHEMA_REGISTRATION, schema_id="alias"),
    replace(FINAL_V4_SCHEMA_REGISTRATION, identity=RegisteredSchemaIdentity(
        5, "d" * 64, SCHEMA_FINGERPRINT_ALGORITHM)),
    replace(FINAL_V4_SCHEMA_REGISTRATION, schema_id="other", identity=RegisteredSchemaIdentity(
        5, FINAL_SCHEMA_FINGERPRINT, SCHEMA_FINGERPRINT_ALGORITHM)),
])
def test_duplicate_or_conflicting_registrations_rejected(duplicate):
    with pytest.raises(SchemaRegistryError):
        DatabaseSchemaRegistry((FINAL_V4_SCHEMA_REGISTRATION, duplicate))


def test_admission_categories_and_upgrade_are_independent():
    historical = synthetic(3, "a" * 64, (SchemaAdmission.HISTORICAL_INSPECTION,))
    runtime = synthetic(5, "b" * 64, (SchemaAdmission.RUNTIME,))
    registry = DatabaseSchemaRegistry((historical, runtime))
    assert registry.require_admission(historical.identity, SchemaAdmission.HISTORICAL_INSPECTION) == historical
    assert registry.require_admission(runtime.identity, SchemaAdmission.RUNTIME) == runtime
    with pytest.raises(SchemaRegistryError, match="admission_denied"):
        registry.require_admission(historical.identity, SchemaAdmission.RUNTIME)
    with pytest.raises(SchemaRegistryError, match="admission_denied"):
        registry.require_admission(runtime.identity, SchemaAdmission.HISTORICAL_INSPECTION)
    with pytest.raises(SchemaRegistryError, match="upgrade_denied"):
        registry.require_upgrade(historical.identity, runtime.identity)
    edge = SchemaUpgradeRelation(historical.identity, runtime.identity)
    explicit = DatabaseSchemaRegistry((historical, runtime), (edge,))
    assert explicit.require_upgrade(historical.identity, runtime.identity) == edge
    with pytest.raises(SchemaRegistryError, match="upgrade_denied"):
        explicit.require_upgrade(runtime.identity, historical.identity)
    with pytest.raises(SchemaRegistryError, match="admission_denied"):
        explicit.require_admission(historical.identity, SchemaAdmission.RUNTIME)


def test_no_transitive_upgrade_authorization():
    a, b, c = synthetic(3, "a" * 64), synthetic(5), synthetic(6, "c" * 64)
    registry = DatabaseSchemaRegistry((a, b, c), (
        SchemaUpgradeRelation(a.identity, b.identity), SchemaUpgradeRelation(b.identity, c.identity)))
    with pytest.raises(SchemaRegistryError, match="upgrade_denied"):
        registry.require_upgrade(a.identity, c.identity)


def test_unknown_duplicate_and_self_upgrade_rejected():
    v4, other = FINAL_V4_SCHEMA_REGISTRATION, synthetic()
    edge = SchemaUpgradeRelation(v4.identity, other.identity)
    with pytest.raises(SchemaRegistryError, match="endpoint_unknown"):
        DatabaseSchemaRegistry((v4,), (edge,))
    with pytest.raises(SchemaRegistryError, match="relation_duplicate"):
        DatabaseSchemaRegistry((v4, other), (edge, edge))
    with pytest.raises(SchemaRegistryError, match="self_relation"):
        SchemaUpgradeRelation(v4.identity, v4.identity)
    with pytest.raises(SchemaRegistryError, match="schema_unknown"):
        PRODUCT_SCHEMA_REGISTRY.require_upgrade(v4.identity, other.identity)


def test_registry_immutable_and_test_registry_cannot_expand_product_gates():
    v4 = FINAL_V4_SCHEMA_REGISTRATION
    alternate = synthetic(admissions=(SchemaAdmission.RUNTIME,))
    registry = DatabaseSchemaRegistry([v4, alternate])
    with pytest.raises(FrozenInstanceError):
        registry._upgrades = frozenset()
    with pytest.raises(FrozenInstanceError):
        alternate.schema_id = "mutated"
    assert PRODUCT_SCHEMA_REGISTRY.schemas == (v4,)
    assert PRODUCT_SCHEMA_REGISTRY.upgrades == frozenset()
    with pytest.raises(SchemaRegistryError):
        PRODUCT_SCHEMA_REGISTRY.require_admission(alternate.identity, SchemaAdmission.RUNTIME)
    from src.core.database_compatibility import DatabaseSchemaIdentity
    assert DatabaseCompatibilityPolicy().evaluate(
        sqlite_user_version=alternate.identity.schema_version,
        schema_identity=DatabaseSchemaIdentity(alternate.identity.fingerprint, 1),
    ).status is DatabaseCompatibilityStatus.INCOMPATIBLE


def test_raw_admission_string_is_not_an_explicit_category():
    with pytest.raises(SchemaRegistryError, match="admission_invalid"):
        PRODUCT_SCHEMA_REGISTRY.require_admission(FINAL_V4_SCHEMA_REGISTRATION.identity, "runtime")
    with pytest.raises(SchemaRegistryError, match="admission_invalid"):
        replace(FINAL_V4_SCHEMA_REGISTRATION, admissions=frozenset({"runtime"}))
