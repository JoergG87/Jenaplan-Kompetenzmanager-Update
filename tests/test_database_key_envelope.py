from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import logging
import os
from pathlib import Path
import secrets
import stat
import uuid

import pytest

from src.security.data_keys import LoadedDataMasterKey
from src.security.database_keys import (
    DATABASE_KEY_BYTES,
    DATABASE_KEY_ENVELOPE_VERSION,
    DATABASE_KEY_NONCE_BYTES,
    DATABASE_KEY_WRAP_ALGORITHM,
    DatabaseKeyEnvelopeError,
    DatabaseKeyEnvelopeService,
    DatabaseKeyEnvelopeStatus,
    derive_database_key_registry_auth_key,
    derive_database_wrapping_key,
    derive_domain_separated_key,
)
from src.security.infrastructure.database_key_envelope_repository import (
    DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
    FileDatabaseKeyEnvelopeRepository,
)
from src.security.infrastructure.system import (
    PlatformFilePermissionManager,
    SystemClock,
    SystemRandomSource,
)


def _dmk(*, key_id: str | None = None, generation: int = 1) -> LoadedDataMasterKey:
    return LoadedDataMasterKey(
        key_id or str(uuid.uuid4()), generation, secrets.token_bytes(32)
    )


def _environment(tmp_path: Path, *, random_source=None):
    repository = FileDatabaseKeyEnvelopeRepository(
        tmp_path / "envelopes" / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
        PlatformFilePermissionManager(),
    )
    service = DatabaseKeyEnvelopeService(
        repository=repository,
        random_source=random_source or SystemRandomSource(),
        clock=SystemClock(),
    )
    return repository, service


def _registry_auth(repository, dmk):
    return derive_database_key_registry_auth_key(
        dmk, database_context_id=repository.peek_context()
    )


def _load_registry(repository, dmk):
    return repository.load(_registry_auth(repository, dmk))


def _replace_registry(repository, dmk, expected, replacement) -> None:
    repository.replace(expected, replacement, _registry_auth(repository, dmk))


def test_domain_separated_wrapping_key_is_stable_and_context_bound() -> None:
    dmk = _dmk()
    context = str(uuid.uuid4())
    first = derive_database_wrapping_key(
        dmk, database_context_id=context, key_generation=1
    )
    repeated = derive_database_wrapping_key(
        dmk, database_context_id=context, key_generation=1
    )
    other_database = derive_database_wrapping_key(
        dmk, database_context_id=str(uuid.uuid4()), key_generation=1
    )
    other_generation = derive_database_wrapping_key(
        dmk, database_context_id=context, key_generation=2
    )
    other_rewrap_revision = derive_database_wrapping_key(
        dmk,
        database_context_id=context,
        key_generation=1,
        rewrap_revision=2,
    )
    other_purpose = derive_domain_separated_key(
        dmk,
        purpose="jenaplan-kompetenzmanager/test-independent-purpose/v1",
        derivation_version=1,
        context={"database_context_id": context, "database_key_generation": 1},
    )
    other_version = derive_database_wrapping_key(
        dmk,
        database_context_id=context,
        key_generation=1,
        derivation_version=2,
    )
    registry_auth = derive_database_key_registry_auth_key(
        dmk, database_context_id=context
    )

    assert first.key_material == repeated.key_material
    assert len(first.key_material) == DATABASE_KEY_BYTES
    assert len(
        {
            first.key_material,
            other_database.key_material,
            other_generation.key_material,
            other_rewrap_revision.key_material,
            other_purpose.key_material,
            other_version.key_material,
            registry_auth.key_material,
        }
    ) == 7
    assert "key_material" not in repr(first)


def test_create_activate_persist_load_and_restart(tmp_path: Path) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    context = str(uuid.uuid4())
    pending = service.create_pending(dmk, database_context_id=context, generation=1)
    assert len(pending.key_material) == DATABASE_KEY_BYTES
    assert _load_registry(repository, dmk)[0].lifecycle_status is DatabaseKeyEnvelopeStatus.PENDING

    active = service.activate(dmk, generation=1)
    assert active == pending
    assert service.activate(dmk, generation=1) == active
    restarted = DatabaseKeyEnvelopeService(
        repository=FileDatabaseKeyEnvelopeRepository(
            repository.path, PlatformFilePermissionManager()
        ),
        random_source=SystemRandomSource(),
        clock=SystemClock(),
    )
    assert restarted.load_active(dmk, expected_generation=1) == active
    assert restarted.load_active(dmk, expected_generation=1) == active
    assert pending.key_material not in repository.path.read_bytes()
    assert pending.key_material.hex().encode("ascii") not in repository.path.read_bytes()
    assert "key_material" not in repr(pending)


def test_authenticated_registry_load_returns_descriptor_bound_digest(
    tmp_path: Path,
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    service.activate(dmk, generation=1)
    auth_key = _registry_auth(repository, dmk)

    envelopes, digest = repository.load_with_digest(auth_key)

    assert envelopes == repository.load(auth_key)
    assert digest == hashlib.sha256(repository.path.read_bytes()).hexdigest()


def test_database_keys_and_nonces_are_fresh(tmp_path: Path) -> None:
    _repository, service = _environment(tmp_path)
    dmk = _dmk()
    context = str(uuid.uuid4())
    first = service.create_pending(
        dmk, database_context_id=context, generation=1
    )
    service.activate(dmk, generation=1)
    service.revoke(dmk, generation=1)
    second = service.create_pending(
        dmk, database_context_id=context, generation=2
    )
    assert first.key_material != second.key_material


def test_invalid_database_key_random_length_is_rejected(tmp_path: Path) -> None:
    class ShortKeyRandom:
        def bytes(self, length: int) -> bytes:
            return secrets.token_bytes(31 if length == DATABASE_KEY_BYTES else length)

        def uuid4(self) -> str:
            return str(uuid.uuid4())

    repository, service = _environment(tmp_path, random_source=ShortKeyRandom())
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.create_pending(
            _dmk(), database_context_id=str(uuid.uuid4()), generation=1
        )
    assert caught.value.code == "database_key_random_invalid"
    assert not repository.path.exists()


def test_wrong_dmk_and_wrong_binding_fail_closed(tmp_path: Path) -> None:
    _repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    service.activate(dmk, generation=1)
    same_binding_wrong_material = _dmk(key_id=dmk.key_id, generation=dmk.generation)
    with pytest.raises(DatabaseKeyEnvelopeError) as wrong_material:
        service.load_active(same_binding_wrong_material)
    assert wrong_material.value.code == "database_key_envelope_registry_authentication_failed"
    with pytest.raises(DatabaseKeyEnvelopeError) as wrong_binding:
        service.load_active(_dmk())
    assert wrong_binding.value.code == "database_key_envelope_registry_authentication_failed"


@pytest.mark.parametrize(
    ("field", "replacement_value", "expected_code"),
    [
        ("key_id", lambda: str(uuid.uuid4()), "database_key_envelope_authentication_failed"),
        ("key_generation", lambda: 2, "database_key_envelope_authentication_failed"),
        ("created_at", lambda: "2026-07-21T00:00:00Z", "database_key_envelope_authentication_failed"),
        ("lifecycle_status", lambda: "revoked", "database_key_envelope_authentication_failed"),
        ("rewrap_revision", lambda: 2, "database_key_envelope_authentication_failed"),
    ],
)
def test_every_mutable_metadata_field_is_aead_authenticated(
    tmp_path: Path, field: str, replacement_value, expected_code: str
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    envelope = _load_registry(repository, dmk)[0]
    replacement = replacement_value()
    if replacement == getattr(envelope, field):
        replacement = str(uuid.uuid4()) if "id" in field else "2026-07-22T00:00:00Z"
    tampered = replace(
        envelope,
        **{
            field: (
                DatabaseKeyEnvelopeStatus(replacement)
                if field == "lifecycle_status"
                else replacement
            )
        },
    )
    _replace_registry(repository, dmk, (envelope,), (tampered,))
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.activate(dmk, generation=1)
    assert caught.value.code == expected_code


@pytest.mark.parametrize("part", ["ciphertext", "nonce"])
def test_ciphertext_and_nonce_tampering_fails_closed(tmp_path: Path, part: str) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    envelope = _load_registry(repository, dmk)[0]
    value = bytearray(getattr(envelope, part))
    value[-1] ^= 1
    tampered = replace(envelope, **{part: bytes(value)})
    _replace_registry(repository, dmk, (envelope,), (tampered,))
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.activate(dmk, generation=1)
    assert caught.value.code == "database_key_envelope_authentication_failed"


def test_database_context_metadata_is_aead_authenticated(tmp_path: Path) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    payload = json.loads(repository.path.read_bytes())
    replacement_context = str(uuid.uuid4())
    payload["database_context_id"] = replacement_context
    payload["envelopes"][0]["database_context_id"] = replacement_context
    repository.path.write_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.activate(dmk, generation=1)
    assert caught.value.code == "database_key_envelope_registry_authentication_failed"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("envelope_version", 2, "database_key_envelope_version_unsupported"),
        ("envelope_version", True, "database_key_envelope_version_invalid"),
        ("wrapping_algorithm", "unknown", "database_key_algorithm_unsupported"),
        ("kdf_algorithm", "unknown", "database_key_kdf_unsupported"),
        ("kdf_version", 2, "database_key_kdf_version_unsupported"),
    ],
)
def test_unknown_versions_and_algorithms_are_rejected_before_decryption(
    tmp_path: Path, field: str, value, expected: str
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    payload = json.loads(repository.path.read_bytes())
    payload["envelopes"][0][field] = value
    with pytest.raises(DatabaseKeyEnvelopeError) as parsed:
        type(_load_registry(repository, dmk)[0]).from_payload(
            payload["envelopes"][0]
        )
    assert parsed.value.code == expected
    repository.path.write_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.activate(dmk, generation=1)
    assert caught.value.code == "database_key_envelope_registry_authentication_failed"


def test_missing_truncated_noncanonical_and_temp_registry_are_rejected(
    tmp_path: Path,
) -> None:
    repository, service = _environment(tmp_path)
    with pytest.raises(DatabaseKeyEnvelopeError) as missing:
        service.load_active(_dmk())
    assert missing.value.code == "database_key_envelope_missing"

    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    envelope = _load_registry(repository, dmk)[0]
    original = repository.path.read_bytes()
    repository.path.write_bytes(original[: len(original) // 2])
    with pytest.raises(DatabaseKeyEnvelopeError) as truncated:
        _load_registry(repository, dmk)
    assert truncated.value.code == "database_key_envelope_registry_invalid"
    repository.path.write_bytes(original + b"\n")
    with pytest.raises(DatabaseKeyEnvelopeError) as noncanonical:
        _load_registry(repository, dmk)
    assert noncanonical.value.code == "database_key_envelope_not_canonical"
    repository.path.write_bytes(original)
    leftover = repository.path.parent / ".database-key-envelope-registry-crash.tmp"
    leftover.write_bytes(b"partial")
    with pytest.raises(DatabaseKeyEnvelopeError) as temporary:
        _load_registry(repository, dmk)
    assert temporary.value.code == "database_key_envelope_temporary_present"
    assert repository.path.read_bytes() == original


def test_registry_file_and_parent_directory_symlinks_are_rejected(
    tmp_path: Path,
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    envelope = _load_registry(repository, dmk)[0]
    original = repository.path.read_bytes()
    real = tmp_path / "real-envelope.json"
    real.write_bytes(original)
    repository.path.unlink()
    repository.path.symlink_to(real)
    with pytest.raises(DatabaseKeyEnvelopeError):
        _load_registry(repository, dmk)

    actual_directory = tmp_path / "actual"
    actual_directory.mkdir()
    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(actual_directory, target_is_directory=True)
    linked_repository = FileDatabaseKeyEnvelopeRepository(
        linked_directory / DATABASE_KEY_ENVELOPE_REGISTRY_FILENAME,
        PlatformFilePermissionManager(),
    )
    with pytest.raises(DatabaseKeyEnvelopeError) as parent:
        linked_repository.create(
            (envelope,),
            derive_database_key_registry_auth_key(
                dmk, database_context_id=envelope.database_context_id
            ),
        )
    assert parent.value.code == "database_key_envelope_directory_invalid"


def test_generation_lifecycle_revocation_failure_and_metadata_delete(
    tmp_path: Path,
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    context = str(uuid.uuid4())
    with pytest.raises(DatabaseKeyEnvelopeError) as wrong_generation:
        service.create_pending(dmk, database_context_id=context, generation=2)
    assert wrong_generation.value.code == "database_key_generation_invalid"

    service.create_pending(dmk, database_context_id=context, generation=1)
    with pytest.raises(DatabaseKeyEnvelopeError) as unknown:
        service.activate(dmk, generation=2)
    assert unknown.value.code == "database_key_generation_unknown"
    service.activate(dmk, generation=1)
    revoked = service.revoke(dmk, generation=1)
    assert service.revoke(dmk, generation=1) == revoked
    with pytest.raises(DatabaseKeyEnvelopeError) as no_active:
        service.load_active(dmk)
    assert no_active.value.code == "active_database_key_missing"
    assert service.delete_terminal_metadata(dmk, generation=1)
    assert repository.path.exists()
    assert _load_registry(repository, dmk) == ()
    auth_key = _registry_auth(repository, dmk)
    assert repository.highest_generation(auth_key) == 1
    assert repository.database_context_id(auth_key) == context
    assert not service.delete_terminal_metadata(dmk, generation=1)

    service.create_pending(dmk, database_context_id=context, generation=2)
    failed = service.fail(dmk, generation=2)
    assert service.fail(dmk, generation=2) == failed
    assert service.delete_terminal_metadata(dmk, generation=2)
    assert repository.highest_generation(_registry_auth(repository, dmk)) == 2
    with pytest.raises(DatabaseKeyEnvelopeError) as reused:
        service.create_pending(dmk, database_context_id=context, generation=2)
    assert reused.value.code == "database_key_generation_invalid"


def test_multiple_active_envelopes_are_rejected(tmp_path: Path) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    context = str(uuid.uuid4())
    first = service.create_pending(dmk, database_context_id=context, generation=1)
    service.activate(dmk, generation=1)
    second = service.create_pending(dmk, database_context_id=context, generation=2)
    current = _load_registry(repository, dmk)
    second_active = service._seal(  # white-box corruption fixture
        dmk,
        key=second,
        database_context_id=context,
        status=DatabaseKeyEnvelopeStatus.ACTIVE,
        created_at=current[1].created_at,
    )
    _replace_registry(repository, dmk, current, (current[0], second_active))
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.load_active(dmk)
    assert caught.value.code == "multiple_active_database_keys"
    assert first.key_material not in repository.path.read_bytes()


@pytest.mark.parametrize("field", ["highest_generation", "database_context_id"])
def test_empty_registry_control_metadata_is_hmac_authenticated(
    tmp_path: Path, field: str
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    context = str(uuid.uuid4())
    service.create_pending(dmk, database_context_id=context, generation=1)
    service.fail(dmk, generation=1)
    service.delete_terminal_metadata(dmk, generation=1)
    service.create_pending(dmk, database_context_id=context, generation=2)
    service.fail(dmk, generation=2)
    service.delete_terminal_metadata(dmk, generation=2)
    payload = json.loads(repository.path.read_bytes())
    assert payload["envelopes"] == []
    payload[field] = 1 if field == "highest_generation" else str(uuid.uuid4())
    repository.path.write_bytes(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.create_pending(dmk, database_context_id=context, generation=3)
    assert caught.value.code == "database_key_envelope_registry_authentication_failed"


def test_nonce_reuse_during_status_rewrap_is_rejected(tmp_path: Path) -> None:
    class ControlledRandom:
        def __init__(self) -> None:
            self.database_key = secrets.token_bytes(DATABASE_KEY_BYTES)
            self.nonce = secrets.token_bytes(DATABASE_KEY_NONCE_BYTES)
            self.calls = 0

        def bytes(self, length: int) -> bytes:
            self.calls += 1
            if length == DATABASE_KEY_BYTES:
                return self.database_key
            assert length == DATABASE_KEY_NONCE_BYTES
            return self.nonce

        def uuid4(self) -> str:
            return str(uuid.uuid4())

    controlled = ControlledRandom()
    _repository, service = _environment(tmp_path, random_source=controlled)
    dmk = _dmk()
    service.create_pending(dmk, database_context_id=str(uuid.uuid4()), generation=1)
    with pytest.raises(DatabaseKeyEnvelopeError) as caught:
        service.activate(dmk, generation=1)
    assert caught.value.code == "database_key_nonce_reused"


def test_non_adjacent_nonce_repeat_uses_a_distinct_rewrap_key(tmp_path: Path) -> None:
    class ControlledRandom:
        def __init__(self) -> None:
            self.database_key = secrets.token_bytes(DATABASE_KEY_BYTES)
            self.nonces = [
                secrets.token_bytes(DATABASE_KEY_NONCE_BYTES),
                secrets.token_bytes(DATABASE_KEY_NONCE_BYTES),
            ]
            self.nonce_calls = 0

        def bytes(self, length: int) -> bytes:
            if length == DATABASE_KEY_BYTES:
                return self.database_key
            assert length == DATABASE_KEY_NONCE_BYTES
            nonce = self.nonces[self.nonce_calls % 2]
            self.nonce_calls += 1
            return nonce

        def uuid4(self) -> str:
            return str(uuid.uuid4())

    controlled = ControlledRandom()
    repository, service = _environment(tmp_path, random_source=controlled)
    dmk = _dmk()
    context = str(uuid.uuid4())
    service.create_pending(dmk, database_context_id=context, generation=1)
    service.activate(dmk, generation=1)
    failed = service.fail(dmk, generation=1)
    envelope = _load_registry(repository, dmk)[0]

    assert envelope.rewrap_revision == 3
    assert envelope.nonce == controlled.nonces[0]
    assert failed.key_material == controlled.database_key
    assert derive_database_wrapping_key(
        dmk,
        database_context_id=context,
        key_generation=1,
        rewrap_revision=1,
    ).key_material != derive_database_wrapping_key(
        dmk,
        database_context_id=context,
        key_generation=1,
        rewrap_revision=3,
    ).key_material


def test_secret_material_never_enters_repr_logs_or_plaintext_sidecar(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repository, service = _environment(tmp_path)
    dmk = _dmk()
    caplog.set_level(logging.DEBUG)
    key = service.create_pending(
        dmk, database_context_id=str(uuid.uuid4()), generation=1
    )
    service.activate(dmk, generation=1)
    raw = repository.path.read_bytes()
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (dmk.key_material, key.key_material):
        assert secret not in raw
        assert secret.hex() not in raw.decode("ascii")
        assert secret.hex() not in combined_logs
        assert secret.hex() not in repr(service)
    payload = json.loads(raw)
    envelope = payload["envelopes"][0]
    assert envelope["wrapping_algorithm"] == DATABASE_KEY_WRAP_ALGORITHM
    assert envelope["envelope_version"] == DATABASE_KEY_ENVELOPE_VERSION
    if os.name == "posix":
        assert stat.S_IMODE(repository.path.stat().st_mode) == 0o600
        assert stat.S_IMODE(repository.path.parent.stat().st_mode) == 0o700
