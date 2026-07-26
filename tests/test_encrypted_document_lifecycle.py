from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import uuid

import pytest

import prototypes.encrypted_document_container.sprint10_container as service_module
from prototypes.encrypted_document_container import DocumentStorageState
from prototypes.encrypted_document_container import SyntheticEncryptedDocumentServiceV1
from src.security.data_keys import LoadedDataMasterKey
from src.security.document_container import DocumentContainerContextV1, EncryptedDocumentError
from src.security.infrastructure.system import SystemClock, SystemRandomSource

from tests.test_encrypted_document_container import _create, _environment, _split


def test_explicit_export_is_verified_no_clobber_and_removes_hidden_plaintext(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    exported = env["service"].export(
        test_root=env["root"],
        container=result.container_path,
        export_name="bewusst-exportiert.pdf",
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    assert exported.export_path.read_bytes() == env["payload"]
    assert "unverschlüsselt" in exported.warning
    assert not any(
        path.name.startswith(".bewusst-exportiert.pdf")
        for path in env["exports"].iterdir()
    )
    with pytest.raises(EncryptedDocumentError):
        env["service"].export(
            test_root=env["root"],
            container=result.container_path,
            export_name="bewusst-exportiert.pdf",
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )


def test_export_symlink_target_is_not_followed_or_changed(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    outside = tmp_path.parent / f"export-outside-{uuid.uuid4()}.txt"
    outside.write_bytes(b"unchanged")
    link = env["exports"] / "target.pdf"
    link.symlink_to(outside)
    with pytest.raises(EncryptedDocumentError):
        env["service"].export(
            test_root=env["root"],
            container=result.container_path,
            export_name="target.pdf",
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    assert outside.read_bytes() == b"unchanged"


@pytest.mark.parametrize("phase", ["export_after_chunk", "export_after_fsync"])
def test_failed_export_cleans_its_hidden_plaintext(
    tmp_path: Path, phase: str
) -> None:
    env = _environment(tmp_path)
    result = _create(env)

    def fail(observed: str) -> None:
        if observed == phase:
            raise EncryptedDocumentError("synthetic_export_failure")

    service = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=fail,
        chunk_size=256,
    )
    with pytest.raises(EncryptedDocumentError, match="synthetic_export_failure"):
        service.export(
            test_root=env["root"],
            container=result.container_path,
            export_name="failed.pdf",
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    residues = tuple(
        path
        for path in env["exports"].iterdir()
        if path.name != service_module.SYNTHETIC_DOCUMENT_EXPORT_MARKER
    )
    assert len(residues) == 1
    assert residues[0].name.startswith(".failed.pdf.")
    assert residues[0].stat().st_size == 0


def test_export_publication_is_atomic_no_clobber_under_late_target_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    foreign = b"foreign-target-must-remain"
    original_publish = service_module._publish_rename_exclusive

    def late_target(directory: Path, source_name: str, target_name: str) -> None:
        (directory / target_name).write_bytes(foreign)
        original_publish(directory, source_name, target_name)

    monkeypatch.setattr(service_module, "_publish_rename_exclusive", late_target)
    with pytest.raises(EncryptedDocumentError, match="document_target_exists"):
        env["service"].export(
            test_root=env["root"],
            container=result.container_path,
            export_name="late-target.pdf",
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    assert (env["exports"] / "late-target.pdf").read_bytes() == foreign
    residues = tuple(
        path
        for path in env["exports"].iterdir()
        if path.name.startswith(".late-target.pdf.")
    )
    assert len(residues) == 1 and residues[0].stat().st_size == 0


def test_export_temp_path_exchange_before_publish_never_moves_foreign_file(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    foreign = env["exports"] / "foreign-source.bin"
    foreign.write_bytes(b"foreign-export-file")
    displaced = env["exports"] / "owned-displaced.bin"

    def exchange_temp(phase: str) -> None:
        if phase == "export_before_publish":
            temp = next(env["exports"].glob(".target.pdf.*.retained"))
            os.replace(temp, displaced)
            os.replace(foreign, temp)

    service = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=exchange_temp,
        chunk_size=256,
    )
    with pytest.raises(EncryptedDocumentError, match="document_export_temp_changed"):
        service.export(
            test_root=env["root"],
            container=result.container_path,
            export_name="target.pdf",
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )
    replacement = next(env["exports"].glob(".target.pdf.*.retained"))
    assert replacement.read_bytes() == b"foreign-export-file"
    assert displaced.stat().st_size == 0
    assert not (env["exports"] / "target.pdf").exists()


def test_integrated_envelope_rewrap_keeps_payload_and_old_generation_usable(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    new_dmk = LoadedDataMasterKey(str(uuid.uuid4()), 2, os.urandom(32))
    rewrapped = env["service"].rewrap(
        test_root=env["root"],
        container=old.container_path,
        old_dmk=env["dmk"],
        new_dmk=new_dmk,
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    assert rewrapped.header.envelope.rewrap_revision == 2
    assert rewrapped.manifest == old.manifest
    assert _split(rewrapped.container_path)[1] == _split(old.container_path)[1]
    env["service"].verify(
        test_root=env["root"],
        container=old.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    with pytest.raises(EncryptedDocumentError):
        env["service"].verify(
            test_root=env["root"],
            container=rewrapped.container_path,
            dmk=env["dmk"],
            context=env["context"],
            expected_storage_id=env["storage_id"],
        )


def test_full_data_rotation_uses_fresh_key_nonce_and_stream(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    new_storage_id = str(uuid.uuid4())
    rotated = env["service"].create(
        test_root=env["root"],
        source=env["source"],
        storage_id=new_storage_id,
        dmk=env["dmk"],
        context=env["context"],
        document_key_generation=2,
    )
    assert rotated.manifest.plaintext_sha256 == old.manifest.plaintext_sha256
    assert rotated.header.document_key_generation == 2
    assert rotated.header.document_key_id != old.header.document_key_id
    assert rotated.header.envelope.nonce != old.header.envelope.nonce
    assert rotated.header.stream_header != old.header.stream_header
    assert _split(rotated.container_path)[1] != _split(old.container_path)[1]
    env["service"].verify(
        test_root=env["root"],
        container=old.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )
    env["service"].verify(
        test_root=env["root"],
        container=rotated.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=new_storage_id,
    )


@pytest.mark.parametrize("switch_result", [True, False])
def test_generation_exchange_never_loses_old_generation(
    tmp_path: Path, switch_result: bool
) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    env["source_path"].write_bytes(
        __import__(
            "prototypes.encrypted_document_container.sprint10_container",
            fromlist=["SYNTHETIC_DOCUMENT_SOURCE_PREFIX"],
        ).SYNTHETIC_DOCUMENT_SOURCE_PREFIX
        + b"replacement"
    )
    new_context = replace(env["context"], document_generation=2)
    exchange = env["service"].exchange_generation(
        test_root=env["root"],
        previous_container=old.container_path,
        previous_dmk=env["dmk"],
        previous_context=env["context"],
        previous_storage_id=env["storage_id"],
        new_source=env["source"],
        new_storage_id=str(uuid.uuid4()),
        new_dmk=env["dmk"],
        new_context=new_context,
        pointer_switch=lambda _prepared: switch_result,
    )
    assert exchange.pointer_switched is switch_result
    assert exchange.retained_previous_path == (
        old.retained_path if switch_result else None
    )
    assert exchange.previous.container_path.read_bytes() == old.container_path.read_bytes()
    env["service"].verify(
        test_root=env["root"],
        container=old.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )


def test_pointer_callback_exception_reports_unknown_state_and_keeps_old(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    env["source_path"].write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + b"new"
    )
    new_storage_id = str(uuid.uuid4())
    switched = False

    def switch_then_fail(_prepared) -> bool:
        nonlocal switched
        switched = True
        raise RuntimeError("synthetic callback ambiguity")

    with pytest.raises(
        EncryptedDocumentError, match="document_pointer_switch_state_unknown"
    ):
        env["service"].exchange_generation(
            test_root=env["root"],
            previous_container=old.container_path,
            previous_dmk=env["dmk"],
            previous_context=env["context"],
            previous_storage_id=env["storage_id"],
            new_source=env["source"],
            new_storage_id=new_storage_id,
            new_dmk=env["dmk"],
            new_context=replace(env["context"], document_generation=2),
            pointer_switch=switch_then_fail,
        )
    assert switched
    env["service"].verify(
        test_root=env["root"],
        container=old.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )


def test_damaged_prepared_generation_blocks_pointer_switch(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    env["source_path"].write_bytes(
        service_module.SYNTHETIC_DOCUMENT_SOURCE_PREFIX + b"new"
    )
    new_storage_id = str(uuid.uuid4())
    callback_called = False

    def damage_after_verification(phase: str) -> None:
        if phase == "exchange_after_new_generation_verified":
            path = env["storage"] / f"{new_storage_id}.w1.jkmedoc"
            value = bytearray(path.read_bytes())
            value[-1] ^= 0x80
            path.write_bytes(value)

    service = SyntheticEncryptedDocumentServiceV1(
        random_source=SystemRandomSource(),
        clock=SystemClock(),
        fault_injector=damage_after_verification,
        chunk_size=256,
    )

    def pointer_switch(_prepared) -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(EncryptedDocumentError):
        service.exchange_generation(
            test_root=env["root"],
            previous_container=old.container_path,
            previous_dmk=env["dmk"],
            previous_context=env["context"],
            previous_storage_id=env["storage_id"],
            new_source=env["source"],
            new_storage_id=new_storage_id,
            new_dmk=env["dmk"],
            new_context=replace(env["context"], document_generation=2),
            pointer_switch=pointer_switch,
        )
    assert not callback_called
    env["service"].verify(
        test_root=env["root"],
        container=old.container_path,
        dmk=env["dmk"],
        context=env["context"],
        expected_storage_id=env["storage_id"],
    )


def test_inventory_is_read_only_and_gc_requires_verified_explicit_allowlist(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    unknown = env["storage"] / "unknown.bin"
    unknown.write_bytes(b"foreign")
    inventory = env["service"].inventory(
        test_root=env["root"],
        active_names=frozenset({result.container_path.name}),
        verifications=(result,),
        gc_candidates=frozenset({result.retained_path.name}),
    )
    by_name = {item.name: item.state for item in inventory}
    assert by_name[result.container_path.name] is DocumentStorageState.ACTIVE
    assert by_name[result.retained_path.name] is DocumentStorageState.GC_ELIGIBLE
    assert by_name["unknown.bin"] is DocumentStorageState.QUARANTINED
    assert unknown.read_bytes() == b"foreign"


def test_inventory_rejects_stale_evidence_after_container_tamper(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    result = _create(env)
    value = bytearray(result.container_path.read_bytes())
    value[-1] ^= 0x80
    result.container_path.write_bytes(value)
    states = {
        item.name: item.state
        for item in env["service"].inventory(
            test_root=env["root"],
            active_names=frozenset({result.container_path.name}),
            verifications=(result,),
            gc_candidates=frozenset({result.retained_path.name}),
        )
    }
    assert (
        states[result.container_path.name]
        is DocumentStorageState.QUARANTINED
    )
    assert (
        states[result.retained_path.name]
        is DocumentStorageState.QUARANTINED
    )


def test_failed_pointer_switch_leaves_new_generation_prepared(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    old = _create(env)
    env["source_path"].write_bytes(
        __import__(
            "prototypes.encrypted_document_container.sprint10_container",
            fromlist=["SYNTHETIC_DOCUMENT_SOURCE_PREFIX"],
        ).SYNTHETIC_DOCUMENT_SOURCE_PREFIX
        + b"new"
    )
    exchange = env["service"].exchange_generation(
        test_root=env["root"],
        previous_container=old.container_path,
        previous_dmk=env["dmk"],
        previous_context=env["context"],
        previous_storage_id=env["storage_id"],
        new_source=env["source"],
        new_storage_id=str(uuid.uuid4()),
        new_dmk=env["dmk"],
        new_context=replace(env["context"], document_generation=2),
        pointer_switch=lambda _prepared: False,
    )
    states = {
        item.name: item.state
        for item in env["service"].inventory(
            test_root=env["root"],
            active_names=frozenset({old.container_path.name}),
            verifications=(old, exchange.prepared),
        )
    }
    assert states[old.container_path.name] is DocumentStorageState.ACTIVE
    assert (
        states[exchange.prepared.container_path.name]
        is DocumentStorageState.PREPARED
    )
