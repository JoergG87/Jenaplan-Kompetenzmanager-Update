"""Isolated writer, verifier, reader, export, and rotation for documents.

All operations are confined to a marker-bound synthetic test root. Product
RuntimePaths, document repositories, UI, backup/restore, and startup are not
dependencies of this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import platform
import re
import stat
import struct
import sys
from typing import Callable, Protocol

import nacl.bindings
from nacl.exceptions import CryptoError

from src.security.data_keys import LoadedDataMasterKey
from src.security.document_container import (
    DEFAULT_DOCUMENT_CHUNK_SIZE,
    DOCUMENT_KEY_BYTES,
    DOCUMENT_KEY_NONCE_BYTES,
    ENCRYPTED_DOCUMENT_MAGIC,
    MAX_DOCUMENT_HEADER_BYTES,
    MAX_DOCUMENT_MANIFEST_BYTES,
    DocumentContainerContextV1,
    DocumentContainerHeaderV1,
    DocumentKeyEnvelopeV1,
    EncryptedDocumentError,
    EncryptedDocumentManifestV1,
    build_document_key_envelope,
    chunk_record_aad,
    expected_chunk_size,
    final_record_aad,
    format_utc,
    manifest_record_aad,
    open_document_key_envelope,
    validate_document_chunk_size,
)
from src.security.domain import validate_uuid4
from src.security.ports import RandomSource, UtcClock


DOCUMENT_CONTAINER_EXTENSION = ".jkmedoc"
SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER = ".jkm-security-sprint10-test-root"
SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES = (
    b"jenaplan-security-sprint10-synthetic-root-v1\n"
)
SYNTHETIC_DOCUMENT_STORAGE_MARKER = ".jkm-security-sprint10-storage-root"
SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES = (
    b"jenaplan-security-sprint10-storage-root-v1\n"
)
SYNTHETIC_DOCUMENT_EXPORT_MARKER = ".jkm-security-sprint10-export-root"
SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES = (
    b"jenaplan-security-sprint10-export-root-v1\n"
)
SYNTHETIC_DOCUMENT_SOURCE_PREFIX = (
    b"JKM-SECURITY-SPRINT10-SYNTHETIC-DOCUMENT-V1\n"
)
SOURCES_DIRECTORY = "sources"
STORAGE_DIRECTORY = "storage"
EXPORTS_DIRECTORY = "exports"
_UINT32 = struct.Struct(">I")
_FILENAME_PATTERN = re.compile(
    r"\A([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})(?:\.w([1-9][0-9]*))?\.jkmedoc\Z"
)
_RETAINED_PATTERN = re.compile(
    r"\A\.([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12})(?:\.w([1-9][0-9]*))?\.jkmedoc\."
    r"([0-9a-f-]{36})\.retained\Z"
)
_SECRETSTREAM_OVERHEAD = nacl.bindings.crypto_secretstream_xchacha20poly1305_ABYTES
_SECRETSTREAM_HEADER_BYTES = (
    nacl.bindings.crypto_secretstream_xchacha20poly1305_HEADERBYTES
)
_SECRETSTREAM_KEY_BYTES = nacl.bindings.crypto_secretstream_xchacha20poly1305_KEYBYTES
_TAG_MESSAGE = nacl.bindings.crypto_secretstream_xchacha20poly1305_TAG_MESSAGE
_TAG_FINAL = nacl.bindings.crypto_secretstream_xchacha20poly1305_TAG_FINAL


class DocumentChunkConsumer(Protocol):
    def start(self, manifest: EncryptedDocumentManifestV1) -> None: ...
    def write(self, chunk: bytes) -> None: ...
    def finish(self, result: "EncryptedDocumentVerificationResult") -> None: ...
    def abort(self, code: str) -> None: ...


class DocumentStorageState(str, Enum):
    ACTIVE = "ACTIVE"
    PREPARED = "PREPARED"
    RETAINED = "RETAINED"
    QUARANTINED = "QUARANTINED"
    GC_ELIGIBLE = "GC_ELIGIBLE"


@dataclass(frozen=True)
class DocumentSource:
    source_name: str
    original_filename: str
    mime_type: str


@dataclass(frozen=True)
class EncryptedDocumentVerificationResult:
    container_path: Path
    retained_path: Path | None
    header: DocumentContainerHeaderV1
    manifest: EncryptedDocumentManifestV1
    container_size: int
    container_sha256: str
    container_device: int
    container_inode: int
    container_mtime_ns: int


@dataclass(frozen=True)
class EncryptedDocumentExportResult:
    export_path: Path
    plaintext_size: int
    plaintext_sha256: str
    warning: str
    verification: EncryptedDocumentVerificationResult


@dataclass(frozen=True)
class DocumentGenerationExchangeResult:
    previous: EncryptedDocumentVerificationResult
    prepared: EncryptedDocumentVerificationResult
    pointer_switched: bool
    retained_previous_path: Path | None


@dataclass(frozen=True)
class DocumentStorageInventoryItem:
    name: str
    state: DocumentStorageState
    reason: str


@dataclass
class _BoundSource:
    fd: int
    directory: Path
    name: str
    device: int
    inode: int
    file_size: int
    size: int
    mtime_ns: int
    sha256: str
    payload: bytes | None = None


class _FDReader:
    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.hasher = hashlib.sha256()
        self.bytes_read = 0

    def exact(self, size: int, code: str) -> bytes:
        if size < 0:
            raise EncryptedDocumentError(code)
        parts: list[bytes] = []
        remaining = size
        while remaining:
            try:
                chunk = os.read(self.fd, min(remaining, 1024 * 1024))
            except OSError:
                raise EncryptedDocumentError("document_container_read_failed") from None
            if not chunk:
                raise EncryptedDocumentError(code)
            parts.append(chunk)
            self.hasher.update(chunk)
            self.bytes_read += len(chunk)
            remaining -= len(chunk)
        return b"".join(parts)

    def one(self) -> bytes:
        try:
            value = os.read(self.fd, 1)
        except OSError:
            raise EncryptedDocumentError("document_container_read_failed") from None
        if value:
            self.hasher.update(value)
            self.bytes_read += 1
        return value


class _ExportConsumer:
    def __init__(self, fd: int, fault: Callable[[str], None]) -> None:
        self.fd = fd
        self.fault = fault
        self.hasher = hashlib.sha256()
        self.size = 0

    def start(self, manifest: EncryptedDocumentManifestV1) -> None:
        self.fault("export_after_start")

    def write(self, chunk: bytes) -> None:
        _write_all(self.fd, chunk, "document_export_write_failed")
        self.hasher.update(chunk)
        self.size += len(chunk)
        self.fault("export_after_chunk")

    def finish(self, result: EncryptedDocumentVerificationResult) -> None:
        self.fault("export_before_fsync")
        _fsync_fd(self.fd, "document_export_fsync_failed")
        self.fault("export_after_fsync")

    def abort(self, code: str) -> None:
        return None


class SyntheticEncryptedDocumentServiceV1:
    """Smallest complete synthetic document-container path for Sprint 10."""

    def __init__(
        self,
        *,
        random_source: RandomSource,
        clock: UtcClock,
        fault_injector: Callable[[str], None] | None = None,
        chunk_size: int = DEFAULT_DOCUMENT_CHUNK_SIZE,
        required_source_prefix: bytes | None = (
            SYNTHETIC_DOCUMENT_SOURCE_PREFIX
        ),
        plain_storage_names: bool = False,
        retain_published_hardlink_evidence: bool = True,
        source_root_override: Path | None = None,
        direct_visible_write: bool = False,
        require_export_layout: bool = True,
    ) -> None:
        self._random = random_source
        self._clock = clock
        self._fault = fault_injector or (lambda _phase: None)
        validate_document_chunk_size(chunk_size)
        self._chunk_size = chunk_size
        if required_source_prefix is not None and (
            not isinstance(required_source_prefix, bytes)
            or not required_source_prefix
        ):
            raise EncryptedDocumentError(
                "document_source_prefix_invalid"
            )
        self._required_source_prefix = required_source_prefix
        self._plain_storage_names = bool(plain_storage_names)
        self._retain_published_hardlink_evidence = bool(
            retain_published_hardlink_evidence
        )
        self._source_root_override = (
            None if source_root_override is None else Path(source_root_override)
        )
        self._direct_visible_write = bool(direct_visible_write)
        self._require_export_layout = bool(require_export_layout)

    def create(
        self,
        *,
        test_root: Path,
        source: DocumentSource,
        storage_id: str,
        dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        document_key_generation: int = 1,
        source_bytes: bytes | None = None,
    ) -> EncryptedDocumentVerificationResult:
        root, source_root, storage_root, _export_root = self._layout(
            test_root, require_source=True
        )
        identity_paths = [root, source_root, storage_root]
        if self._require_export_layout:
            identity_paths.append(_export_root)
        layout_identity = _capture_layout_identity(*identity_paths)
        _validate_uuid(storage_id, "document_storage_id_invalid")
        _positive(document_key_generation, "document_key_generation_invalid")
        source_name = _safe_leaf(source.source_name, "document_source_name_invalid")
        storage_name = _container_filename(
            storage_id,
            1,
            include_rewrap_revision=not self._plain_storage_names,
        )
        _require_absent(storage_root / storage_name, "document_target_exists")
        if source_bytes is None:
            bound = _bind_source(
                source_root,
                source_name,
                self._chunk_size,
                required_prefix=self._required_source_prefix,
            )
        else:
            if not isinstance(source_bytes, bytes):
                raise EncryptedDocumentError("document_source_bytes_invalid")
            bound = _BoundSource(
                fd=-1,
                directory=source_root,
                name=source_name,
                device=0,
                inode=0,
                file_size=len(source_bytes),
                size=len(source_bytes),
                mtime_ns=0,
                sha256=hashlib.sha256(source_bytes).hexdigest(),
                payload=source_bytes,
            )
        try:
            self._fault("writer_after_source_bound")
            _require_layout_identity(layout_identity)
            manifest_base = {
                "storage_id": storage_id,
                "original_filename": source.original_filename,
                "mime_type": source.mime_type,
                "plaintext_size": bound.size,
                "plaintext_sha256": bound.sha256,
                "chunk_size": self._chunk_size,
                "chunk_count": max(1, (bound.size + self._chunk_size - 1) // self._chunk_size),
                "created_at": format_utc(self._clock.utc_now()),
            }
            document_key_buffer = bytearray(self._random.bytes(DOCUMENT_KEY_BYTES))
            if len(document_key_buffer) != DOCUMENT_KEY_BYTES:
                raise EncryptedDocumentError("document_key_random_invalid")
            try:
                document_key = bytes(document_key_buffer)
                if len(document_key) != _SECRETSTREAM_KEY_BYTES:
                    raise EncryptedDocumentError("document_key_length_invalid")
                push_state = nacl.bindings.crypto_secretstream_xchacha20poly1305_state()
                try:
                    stream_header = (
                        nacl.bindings.crypto_secretstream_xchacha20poly1305_init_push(
                            push_state, document_key
                        )
                    )
                except Exception:
                    raise EncryptedDocumentError("document_stream_init_failed") from None
                if len(stream_header) != _SECRETSTREAM_HEADER_BYTES:
                    raise EncryptedDocumentError("document_stream_header_invalid")
                container_id = self._uuid("document_container_id_invalid")
                document_key_id = self._uuid("document_key_id_invalid")
                placeholder = DocumentKeyEnvelopeV1(
                    document_key_id=document_key_id,
                    document_key_generation=document_key_generation,
                    rewrap_revision=1,
                    wrapping_dmk_key_id=dmk.key_id,
                    wrapping_dmk_generation=dmk.generation,
                    nonce=self._random.bytes(DOCUMENT_KEY_NONCE_BYTES),
                    ciphertext=b"",
                )
                bare_header = DocumentContainerHeaderV1(
                    container_id=container_id,
                    chunk_size=self._chunk_size,
                    stream_header=stream_header,
                    document_key_id=document_key_id,
                    document_key_generation=document_key_generation,
                    envelope=placeholder,
                )
                envelope = build_document_key_envelope(
                    dmk,
                    context=context,
                    header_without_envelope=bare_header,
                    document_key=document_key,
                    nonce=placeholder.nonce,
                    rewrap_revision=1,
                )
                header = DocumentContainerHeaderV1(
                    container_id=container_id,
                    chunk_size=self._chunk_size,
                    stream_header=stream_header,
                    document_key_id=document_key_id,
                    document_key_generation=document_key_generation,
                    envelope=envelope,
                )
                manifest = EncryptedDocumentManifestV1(
                    context=context,
                    container_id=container_id,
                    document_key_id=document_key_id,
                    document_key_generation=document_key_generation,
                    **manifest_base,
                )
                # Validate every source-derived metadata value before creating
                # even the hidden retained container.
                manifest.to_bytes()
                retained_name = storage_name
                if not self._direct_visible_write:
                    retained_name = (
                        f".{storage_name}."
                        f"{self._uuid('document_run_id_invalid')}.retained"
                    )
                retained_path = storage_root / retained_name
                self._write_container(
                    storage_root=storage_root,
                    retained_name=retained_name,
                    header=header,
                    manifest=manifest,
                    push_state=push_state,
                    source=bound,
                )
            finally:
                _erase(document_key_buffer)

            _require_layout_identity(layout_identity)
            _fsync_directory(storage_root, "document_directory_fsync_failed")
            self._fault("writer_after_retained_directory_fsync")
            prepublish = self.verify(
                test_root=root,
                container=retained_path,
                dmk=dmk,
                context=context,
                expected_storage_id=storage_id,
            )
            if prepublish.manifest != manifest:
                raise EncryptedDocumentError("document_self_verification_failed")
            self._fault("writer_after_preverify")
            _require_layout_identity(layout_identity)
            if not self._direct_visible_write:
                _publish_hardlink(storage_root, retained_name, storage_name)
                _fsync_directory(storage_root, "document_directory_fsync_failed")
                self._fault("writer_after_publish")
            result = self.verify(
                test_root=root,
                container=storage_root / storage_name,
                dmk=dmk,
                context=context,
                expected_storage_id=storage_id,
            )
            if result.manifest != manifest:
                raise EncryptedDocumentError("document_self_verification_failed")
            self._fault("writer_after_published_verify")
            if (
                not self._direct_visible_write
                and not self._retain_published_hardlink_evidence
            ):
                try:
                    os.unlink(retained_path)
                except OSError:
                    raise EncryptedDocumentError(
                        "document_retained_cleanup_failed"
                    ) from None
                _fsync_directory(
                    storage_root, "document_directory_fsync_failed"
                )
                retained_path = None
            return EncryptedDocumentVerificationResult(
                container_path=result.container_path,
                retained_path=(
                    None if self._direct_visible_write else retained_path
                ),
                header=result.header,
                manifest=result.manifest,
                container_size=result.container_size,
                container_sha256=result.container_sha256,
                container_device=result.container_device,
                container_inode=result.container_inode,
                container_mtime_ns=result.container_mtime_ns,
            )
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError("document_writer_failed") from None
        finally:
            if bound.fd >= 0:
                os.close(bound.fd)

    def inspect_header(
        self, *, test_root: Path, container: Path
    ) -> DocumentContainerHeaderV1:
        _root, _source_root, storage_root, _export_root = self._layout(test_root)
        storage_identity = _directory_identity(storage_root)
        name = _validated_storage_child(storage_root, container, allow_hidden=True)
        fd, _identity = _open_regular_at(storage_root, name)
        try:
            reader = _FDReader(fd)
            if reader.exact(len(ENCRYPTED_DOCUMENT_MAGIC), "document_container_truncated") != ENCRYPTED_DOCUMENT_MAGIC:
                raise EncryptedDocumentError("document_container_magic_invalid")
            header_size = _UINT32.unpack(
                reader.exact(_UINT32.size, "document_container_truncated")
            )[0]
            if header_size < 1 or header_size > MAX_DOCUMENT_HEADER_BYTES:
                raise EncryptedDocumentError("document_header_size_invalid")
            header = DocumentContainerHeaderV1.from_bytes(
                reader.exact(header_size, "document_container_truncated")
            )
            _require_path_identity(
                storage_root, name, _identity, "document_container_changed"
            )
            _require_directory_identity(
                storage_root, storage_identity, "document_storage_root_changed"
            )
            return header
        finally:
            os.close(fd)

    def verify(
        self,
        *,
        test_root: Path,
        container: Path,
        dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        expected_storage_id: str,
    ) -> EncryptedDocumentVerificationResult:
        root, _source_root, storage_root, _export_root = self._layout(test_root)
        name = _validated_storage_child(storage_root, container, allow_hidden=True)
        return self._consume(
            root=root,
            storage_root=storage_root,
            name=name,
            dmk=dmk,
            context=context,
            expected_storage_id=expected_storage_id,
            consumer=None,
        )

    def stream_verified(
        self,
        *,
        test_root: Path,
        container: Path,
        dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        expected_storage_id: str,
        consumer: DocumentChunkConsumer,
    ) -> EncryptedDocumentVerificationResult:
        first = self.verify(
            test_root=test_root,
            container=container,
            dmk=dmk,
            context=context,
            expected_storage_id=expected_storage_id,
        )
        root, _source_root, storage_root, _export_root = self._layout(test_root)
        name = _validated_storage_child(storage_root, container, allow_hidden=True)
        try:
            consumer.start(first.manifest)
            second = self._consume(
                root=root,
                storage_root=storage_root,
                name=name,
                dmk=dmk,
                context=context,
                expected_storage_id=expected_storage_id,
                consumer=consumer,
            )
            if second != first:
                raise EncryptedDocumentError("document_reader_reverify_mismatch")
            consumer.finish(second)
            return second
        except EncryptedDocumentError as error:
            consumer.abort(error.code)
            raise
        except Exception:
            consumer.abort("document_reader_consumer_failed")
            raise EncryptedDocumentError("document_reader_consumer_failed") from None

    def export(
        self,
        *,
        test_root: Path,
        container: Path,
        export_name: str,
        dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        expected_storage_id: str,
    ) -> EncryptedDocumentExportResult:
        if not self._require_export_layout:
            raise EncryptedDocumentError("document_export_disabled")
        root, _source_root, _storage_root, export_root = self._layout(test_root)
        layout_identity = _capture_layout_identity(
            root, _source_root, _storage_root, export_root
        )
        target_name = _safe_leaf(export_name, "document_export_name_invalid")
        target = export_root / target_name
        _require_absent(target, "document_export_target_exists")
        verification = self.verify(
            test_root=root,
            container=container,
            dmk=dmk,
            context=context,
            expected_storage_id=expected_storage_id,
        )
        _require_layout_identity(layout_identity)
        temp_name = f".{target_name}.{self._uuid('document_export_run_id_invalid')}.retained"
        fd, identity = _open_exclusive_at(export_root, temp_name)
        consumer = _ExportConsumer(fd, self._fault)
        published = False
        try:
            second = self.stream_verified(
                test_root=root,
                container=container,
                dmk=dmk,
                context=context,
                expected_storage_id=expected_storage_id,
                consumer=consumer,
            )
            if second != verification:
                raise EncryptedDocumentError("document_export_reverify_mismatch")
            if (
                consumer.size != verification.manifest.plaintext_size
                or consumer.hasher.hexdigest()
                != verification.manifest.plaintext_sha256
            ):
                raise EncryptedDocumentError("document_export_hash_mismatch")
            _require_layout_identity(layout_identity)
            self._fault("export_before_publish")
            _require_fd_identity(fd, identity, "document_export_temp_changed")
            identity = _fd_identity(fd, "document_export_temp_changed")
            _require_path_identity(
                export_root, temp_name, identity, "document_export_temp_changed"
            )
            _publish_rename_exclusive(export_root, temp_name, target_name)
            published = True
            os.close(fd)
            fd = -1
            _fsync_directory(export_root, "document_export_directory_fsync_failed")
            self._fault("export_after_publish")
            final_size, final_hash = _hash_regular_at(export_root, target_name)
            if (
                final_size != verification.manifest.plaintext_size
                or final_hash != verification.manifest.plaintext_sha256
            ):
                raise EncryptedDocumentError("document_export_hash_mismatch")
            return EncryptedDocumentExportResult(
                export_path=target,
                plaintext_size=final_size,
                plaintext_sha256=final_hash,
                warning=(
                    "Die exportierte Datei liegt außerhalb des verwalteten "
                    "Speichers unverschlüsselt vor."
                ),
                verification=verification,
            )
        except EncryptedDocumentError:
            if fd >= 0:
                if not published:
                    _clear_owned_fd_best_effort(fd, identity)
                os.close(fd)
                fd = -1
            raise
        finally:
            if fd >= 0:
                os.close(fd)

    def rewrap(
        self,
        *,
        test_root: Path,
        container: Path,
        old_dmk: LoadedDataMasterKey,
        new_dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        expected_storage_id: str,
    ) -> EncryptedDocumentVerificationResult:
        root, _source_root, storage_root, _export_root = self._layout(test_root)
        layout_identity = _capture_layout_identity(
            root, _source_root, storage_root, _export_root
        )
        old = self.verify(
            test_root=root,
            container=container,
            dmk=old_dmk,
            context=context,
            expected_storage_id=expected_storage_id,
        )
        old_revision = old.header.envelope.rewrap_revision
        new_revision = old_revision + 1
        new_name = _container_filename(expected_storage_id, new_revision)
        _require_absent(storage_root / new_name, "document_target_exists")
        document_key_buffer = bytearray(
            open_document_key_envelope(old_dmk, context=context, header=old.header)
        )
        try:
            placeholder = DocumentKeyEnvelopeV1(
                document_key_id=old.header.document_key_id,
                document_key_generation=old.header.document_key_generation,
                rewrap_revision=new_revision,
                wrapping_dmk_key_id=new_dmk.key_id,
                wrapping_dmk_generation=new_dmk.generation,
                nonce=self._random.bytes(DOCUMENT_KEY_NONCE_BYTES),
                ciphertext=b"",
            )
            bare = DocumentContainerHeaderV1(
                container_id=old.header.container_id,
                chunk_size=old.header.chunk_size,
                stream_header=old.header.stream_header,
                document_key_id=old.header.document_key_id,
                document_key_generation=old.header.document_key_generation,
                envelope=placeholder,
            )
            envelope = build_document_key_envelope(
                new_dmk,
                context=context,
                header_without_envelope=bare,
                document_key=bytes(document_key_buffer),
                nonce=placeholder.nonce,
                rewrap_revision=new_revision,
            )
            new_header = DocumentContainerHeaderV1(
                container_id=bare.container_id,
                chunk_size=bare.chunk_size,
                stream_header=bare.stream_header,
                document_key_id=bare.document_key_id,
                document_key_generation=bare.document_key_generation,
                envelope=envelope,
            )
            retained_name = (
                f".{new_name}.{self._uuid('document_run_id_invalid')}.retained"
            )
            self._copy_rewrapped_container(
                storage_root=storage_root,
                old_name=_validated_storage_child(storage_root, container, allow_hidden=False),
                retained_name=retained_name,
                new_header=new_header,
                expected=old,
            )
        finally:
            _erase(document_key_buffer)
        _fsync_directory(storage_root, "document_directory_fsync_failed")
        prepublish = self.verify(
            test_root=root,
            container=storage_root / retained_name,
            dmk=new_dmk,
            context=context,
            expected_storage_id=expected_storage_id,
        )
        if prepublish.manifest != old.manifest:
            raise EncryptedDocumentError("document_rewrap_manifest_changed")
        self._fault("rewrap_after_preverify")
        _require_layout_identity(layout_identity)
        _publish_hardlink(storage_root, retained_name, new_name)
        _fsync_directory(storage_root, "document_directory_fsync_failed")
        self._fault("rewrap_after_publish")
        result = self.verify(
            test_root=root,
            container=storage_root / new_name,
            dmk=new_dmk,
            context=context,
            expected_storage_id=expected_storage_id,
        )
        if (
            result.manifest != old.manifest
            or result.header.payload_binding_bytes()
            != old.header.payload_binding_bytes()
        ):
            raise EncryptedDocumentError("document_rewrap_verification_failed")
        return EncryptedDocumentVerificationResult(
            container_path=result.container_path,
            retained_path=storage_root / retained_name,
            header=result.header,
            manifest=result.manifest,
            container_size=result.container_size,
            container_sha256=result.container_sha256,
            container_device=result.container_device,
            container_inode=result.container_inode,
            container_mtime_ns=result.container_mtime_ns,
        )

    def exchange_generation(
        self,
        *,
        test_root: Path,
        previous_container: Path,
        previous_dmk: LoadedDataMasterKey,
        previous_context: DocumentContainerContextV1,
        previous_storage_id: str,
        new_source: DocumentSource,
        new_storage_id: str,
        new_dmk: LoadedDataMasterKey,
        new_context: DocumentContainerContextV1,
        pointer_switch: Callable[[EncryptedDocumentVerificationResult], bool],
    ) -> DocumentGenerationExchangeResult:
        if new_context.document_id != previous_context.document_id or (
            new_context.document_generation
            != previous_context.document_generation + 1
        ):
            raise EncryptedDocumentError("document_exchange_generation_invalid")
        previous = self.verify(
            test_root=test_root,
            container=previous_container,
            dmk=previous_dmk,
            context=previous_context,
            expected_storage_id=previous_storage_id,
        )
        prepared = self.create(
            test_root=test_root,
            source=new_source,
            storage_id=new_storage_id,
            dmk=new_dmk,
            context=new_context,
            document_key_generation=1,
        )
        self._fault("exchange_after_new_generation_verified")
        confirmed_prepared = self.verify(
            test_root=test_root,
            container=prepared.container_path,
            dmk=new_dmk,
            context=new_context,
            expected_storage_id=new_storage_id,
        )
        if confirmed_prepared != replace(prepared, retained_path=None):
            raise EncryptedDocumentError("document_exchange_prepared_changed")
        retained_candidate = _find_retained_hardlink(
            previous.container_path.parent, previous
        )
        try:
            switched = bool(pointer_switch(prepared))
        except Exception:
            raise EncryptedDocumentError(
                "document_pointer_switch_state_unknown"
            ) from None
        self._fault("exchange_after_pointer_switch")
        retained_previous_path: Path | None = None
        if switched:
            retained_previous_path = retained_candidate
            self._fault("exchange_after_retained_mark")
        return DocumentGenerationExchangeResult(
            previous,
            prepared,
            switched,
            retained_previous_path,
        )

    def inventory(
        self,
        *,
        test_root: Path,
        active_names: frozenset[str] = frozenset(),
        verifications: tuple[EncryptedDocumentVerificationResult, ...] = (),
        gc_candidates: frozenset[str] = frozenset(),
    ) -> tuple[DocumentStorageInventoryItem, ...]:
        _root, _source_root, storage_root, _export_root = self._layout(test_root)
        evidence: dict[str, EncryptedDocumentVerificationResult] = {}
        for verification in verifications:
            evidence[verification.container_path.name] = verification
            if verification.retained_path is not None:
                evidence[verification.retained_path.name] = verification
        items: list[DocumentStorageInventoryItem] = []
        for entry in sorted(os.scandir(storage_root), key=lambda item: item.name):
            if entry.name == SYNTHETIC_DOCUMENT_STORAGE_MARKER:
                continue
            try:
                status = entry.stat(follow_symlinks=False)
            except OSError:
                items.append(
                    DocumentStorageInventoryItem(
                        entry.name, DocumentStorageState.QUARANTINED, "stat_failed"
                    )
                )
                continue
            if not stat.S_ISREG(status.st_mode):
                state = DocumentStorageState.QUARANTINED
                reason = "unknown_or_nonregular"
            elif _FILENAME_PATTERN.fullmatch(entry.name):
                verified = _matches_verification_evidence(
                    storage_root, entry.name, evidence.get(entry.name)
                )
                if entry.name in active_names and verified:
                    state, reason = DocumentStorageState.ACTIVE, "verified_active"
                elif verified:
                    state, reason = DocumentStorageState.PREPARED, "verified_unreferenced"
                else:
                    state, reason = DocumentStorageState.QUARANTINED, "not_fully_verified"
            elif _RETAINED_PATTERN.fullmatch(entry.name):
                verified = _matches_verification_evidence(
                    storage_root, entry.name, evidence.get(entry.name)
                )
                if entry.name in gc_candidates and verified:
                    state, reason = DocumentStorageState.GC_ELIGIBLE, "verified_allowlisted_retained"
                elif verified:
                    state, reason = DocumentStorageState.RETAINED, "verified_retained"
                else:
                    state, reason = DocumentStorageState.QUARANTINED, "retained_not_fully_verified"
            else:
                state, reason = DocumentStorageState.QUARANTINED, "unknown_name"
            items.append(DocumentStorageInventoryItem(entry.name, state, reason))
        return tuple(items)

    def _write_container(
        self,
        *,
        storage_root: Path,
        retained_name: str,
        header: DocumentContainerHeaderV1,
        manifest: EncryptedDocumentManifestV1,
        push_state,
        source: _BoundSource,
    ) -> None:
        fd, _identity = _open_exclusive_at(storage_root, retained_name)
        try:
            header_bytes = header.to_bytes()
            _write_all(fd, ENCRYPTED_DOCUMENT_MAGIC, "document_header_write_failed")
            _write_all(fd, _UINT32.pack(len(header_bytes)), "document_header_write_failed")
            self._fault("writer_after_header_prefix")
            _write_all(fd, header_bytes, "document_header_write_failed")
            self._fault("writer_after_envelope")
            manifest_bytes = manifest.to_bytes()
            manifest_ciphertext = _push(
                push_state,
                manifest_bytes,
                manifest_record_aad(header, manifest.context, len(manifest_bytes)),
                _TAG_MESSAGE,
            )
            _write_frame(fd, manifest_ciphertext, "document_manifest_write_failed")
            self._fault("writer_after_manifest")
            manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
            if source.payload is None:
                os.lseek(
                    source.fd,
                    len(self._required_source_prefix or b""),
                    os.SEEK_SET,
                )
            streamed_hash = hashlib.sha256()
            streamed_size = 0
            for chunk_index in range(manifest.chunk_count):
                size = expected_chunk_size(manifest, chunk_index)
                if source.payload is None:
                    chunk = _read_exact_source(source.fd, size)
                else:
                    chunk = source.payload[streamed_size : streamed_size + size]
                    if len(chunk) != size:
                        raise EncryptedDocumentError("document_source_changed")
                streamed_hash.update(chunk)
                streamed_size += len(chunk)
                ciphertext = _push(
                    push_state,
                    chunk,
                    chunk_record_aad(
                        header,
                        manifest.context,
                        manifest_sha256=manifest_hash,
                        record_ordinal=chunk_index + 1,
                        chunk_index=chunk_index,
                        plaintext_size=len(chunk),
                    ),
                    _TAG_MESSAGE,
                )
                _write_frame(fd, ciphertext, "document_chunk_write_failed")
                if chunk_index == 0:
                    self._fault("writer_after_first_chunk")
                if chunk_index == manifest.chunk_count // 2:
                    self._fault("writer_after_middle_chunk")
            _require_bound_source_unchanged(source)
            if (
                streamed_size != manifest.plaintext_size
                or streamed_hash.hexdigest() != manifest.plaintext_sha256
            ):
                raise EncryptedDocumentError("document_source_changed")
            final_ciphertext = _push(
                push_state,
                b"",
                final_record_aad(
                    header,
                    manifest.context,
                    manifest_sha256=manifest_hash,
                    record_ordinal=manifest.chunk_count + 1,
                    chunk_count=manifest.chunk_count,
                    plaintext_size=manifest.plaintext_size,
                ),
                _TAG_FINAL,
            )
            self._fault("writer_before_final")
            _write_frame(fd, final_ciphertext, "document_final_write_failed")
            self._fault("writer_after_final")
            _fsync_fd(fd, "document_file_fsync_failed")
            self._fault("writer_after_file_fsync")
        except EncryptedDocumentError:
            raise
        except OSError:
            raise EncryptedDocumentError("document_writer_io_failed") from None
        finally:
            os.close(fd)

    def _consume(
        self,
        *,
        root: Path,
        storage_root: Path,
        name: str,
        dmk: LoadedDataMasterKey,
        context: DocumentContainerContextV1,
        expected_storage_id: str,
        consumer: DocumentChunkConsumer | _ExportConsumer | None,
    ) -> EncryptedDocumentVerificationResult:
        _validate_uuid(expected_storage_id, "document_storage_id_invalid")
        fd, initial = _open_regular_at(storage_root, name)
        storage_identity = _directory_identity(storage_root)
        reader = _FDReader(fd)
        try:
            if reader.exact(len(ENCRYPTED_DOCUMENT_MAGIC), "document_container_truncated") != ENCRYPTED_DOCUMENT_MAGIC:
                raise EncryptedDocumentError("document_container_magic_invalid")
            header_size = _UINT32.unpack(
                reader.exact(_UINT32.size, "document_container_truncated")
            )[0]
            if header_size < 1 or header_size > MAX_DOCUMENT_HEADER_BYTES:
                raise EncryptedDocumentError("document_header_size_invalid")
            header = DocumentContainerHeaderV1.from_bytes(
                reader.exact(header_size, "document_container_truncated")
            )
            document_key_buffer = bytearray(
                open_document_key_envelope(dmk, context=context, header=header)
            )
            try:
                pull_state = nacl.bindings.crypto_secretstream_xchacha20poly1305_state()
                try:
                    nacl.bindings.crypto_secretstream_xchacha20poly1305_init_pull(
                        pull_state, header.stream_header, bytes(document_key_buffer)
                    )
                except Exception:
                    raise EncryptedDocumentError("document_stream_init_failed") from None
                manifest_ciphertext = _read_frame(
                    reader,
                    minimum=_SECRETSTREAM_OVERHEAD,
                    maximum=MAX_DOCUMENT_MANIFEST_BYTES + _SECRETSTREAM_OVERHEAD,
                )
                manifest_size = len(manifest_ciphertext) - _SECRETSTREAM_OVERHEAD
                manifest_bytes, tag = _pull(
                    pull_state,
                    manifest_ciphertext,
                    manifest_record_aad(header, context, manifest_size),
                )
                if tag != _TAG_MESSAGE:
                    raise EncryptedDocumentError("document_manifest_tag_invalid")
                manifest = EncryptedDocumentManifestV1.from_bytes(manifest_bytes)
                if (
                    manifest.context != context
                    or manifest.storage_id != expected_storage_id
                    or manifest.container_id != header.container_id
                    or manifest.document_key_id != header.document_key_id
                    or manifest.document_key_generation
                    != header.document_key_generation
                    or manifest.chunk_size != header.chunk_size
                ):
                    raise EncryptedDocumentError("document_container_context_mismatch")
                self._fault("verifier_after_manifest")
                manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
                plaintext_hash = hashlib.sha256()
                plaintext_size = 0
                for chunk_index in range(manifest.chunk_count):
                    expected_size = expected_chunk_size(manifest, chunk_index)
                    ciphertext = _read_frame(
                        reader,
                        minimum=expected_size + _SECRETSTREAM_OVERHEAD,
                        maximum=expected_size + _SECRETSTREAM_OVERHEAD,
                    )
                    plaintext, tag = _pull(
                        pull_state,
                        ciphertext,
                        chunk_record_aad(
                            header,
                            context,
                            manifest_sha256=manifest_hash,
                            record_ordinal=chunk_index + 1,
                            chunk_index=chunk_index,
                            plaintext_size=expected_size,
                        ),
                    )
                    if tag != _TAG_MESSAGE or len(plaintext) != expected_size:
                        raise EncryptedDocumentError("document_chunk_tag_invalid")
                    plaintext_hash.update(plaintext)
                    plaintext_size += len(plaintext)
                    if consumer is not None:
                        consumer.write(plaintext)
                final_ciphertext = _read_frame(
                    reader,
                    minimum=_SECRETSTREAM_OVERHEAD,
                    maximum=_SECRETSTREAM_OVERHEAD,
                )
                final_plaintext, final_tag = _pull(
                    pull_state,
                    final_ciphertext,
                    final_record_aad(
                        header,
                        context,
                        manifest_sha256=manifest_hash,
                        record_ordinal=manifest.chunk_count + 1,
                        chunk_count=manifest.chunk_count,
                        plaintext_size=manifest.plaintext_size,
                    ),
                )
                if final_tag != _TAG_FINAL or final_plaintext:
                    raise EncryptedDocumentError("document_final_tag_invalid")
                if reader.one():
                    raise EncryptedDocumentError("document_container_trailing_data")
                if (
                    plaintext_size != manifest.plaintext_size
                    or plaintext_hash.hexdigest() != manifest.plaintext_sha256
                ):
                    raise EncryptedDocumentError("document_plaintext_hash_mismatch")
            finally:
                _erase(document_key_buffer)
            final_status = os.fstat(fd)
            if (
                not stat.S_ISREG(final_status.st_mode)
                or (final_status.st_dev, final_status.st_ino) != initial[:2]
                or final_status.st_size != initial[2]
                or final_status.st_mtime_ns != initial[3]
                or reader.bytes_read != initial[2]
            ):
                raise EncryptedDocumentError("document_container_changed")
            _require_path_identity(
                storage_root, name, initial, "document_container_changed"
            )
            result = EncryptedDocumentVerificationResult(
                container_path=storage_root / name,
                retained_path=None,
                header=header,
                manifest=manifest,
                container_size=reader.bytes_read,
                container_sha256=reader.hasher.hexdigest(),
                container_device=initial[0],
                container_inode=initial[1],
                container_mtime_ns=initial[3],
            )
            _require_directory_identity(
                storage_root,
                storage_identity,
                "document_storage_root_changed",
            )
            return result
        except EncryptedDocumentError:
            raise
        except Exception:
            raise EncryptedDocumentError("document_verifier_failed") from None
        finally:
            os.close(fd)

    def _copy_rewrapped_container(
        self,
        *,
        storage_root: Path,
        old_name: str,
        retained_name: str,
        new_header: DocumentContainerHeaderV1,
        expected: EncryptedDocumentVerificationResult,
    ) -> None:
        source_fd, source_identity = _open_regular_at(storage_root, old_name)
        target_fd, _target_identity = _open_exclusive_at(storage_root, retained_name)
        try:
            reader = _FDReader(source_fd)
            if reader.exact(len(ENCRYPTED_DOCUMENT_MAGIC), "document_container_truncated") != ENCRYPTED_DOCUMENT_MAGIC:
                raise EncryptedDocumentError("document_container_magic_invalid")
            old_header_size = _UINT32.unpack(
                reader.exact(_UINT32.size, "document_container_truncated")
            )[0]
            if old_header_size < 1 or old_header_size > MAX_DOCUMENT_HEADER_BYTES:
                raise EncryptedDocumentError("document_header_size_invalid")
            if (
                source_identity[0] != expected.container_device
                or source_identity[1] != expected.container_inode
                or source_identity[2] != expected.container_size
                or source_identity[3] != expected.container_mtime_ns
            ):
                raise EncryptedDocumentError("document_container_changed")
            reader.exact(old_header_size, "document_container_truncated")
            new_header_bytes = new_header.to_bytes()
            _write_all(target_fd, ENCRYPTED_DOCUMENT_MAGIC, "document_rewrap_write_failed")
            _write_all(target_fd, _UINT32.pack(len(new_header_bytes)), "document_rewrap_write_failed")
            _write_all(target_fd, new_header_bytes, "document_rewrap_write_failed")
            copied_hasher = hashlib.sha256()
            copied_hasher.update(ENCRYPTED_DOCUMENT_MAGIC)
            copied_hasher.update(_UINT32.pack(old_header_size))
            os.lseek(source_fd, len(ENCRYPTED_DOCUMENT_MAGIC) + _UINT32.size, os.SEEK_SET)
            copied_hasher.update(reader.exact(old_header_size, "document_container_truncated"))
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                copied_hasher.update(chunk)
                _write_all(target_fd, chunk, "document_rewrap_write_failed")
            if copied_hasher.hexdigest() != expected.container_sha256:
                raise EncryptedDocumentError("document_container_changed")
            _require_fd_identity(source_fd, source_identity, "document_container_changed")
            _require_path_identity(
                storage_root,
                old_name,
                source_identity,
                "document_container_changed",
            )
            _fsync_fd(target_fd, "document_file_fsync_failed")
            self._fault("rewrap_after_file_fsync")
        finally:
            os.close(source_fd)
            os.close(target_fd)

    def _uuid(self, code: str) -> str:
        raw = self._random.bytes(16)
        if len(raw) != 16:
            raise EncryptedDocumentError(code)
        value = bytearray(raw)
        value[6] = (value[6] & 0x0F) | 0x40
        value[8] = (value[8] & 0x3F) | 0x80
        text = (
            f"{bytes(value[0:4]).hex()}-{bytes(value[4:6]).hex()}-"
            f"{bytes(value[6:8]).hex()}-{bytes(value[8:10]).hex()}-"
            f"{bytes(value[10:16]).hex()}"
        )
        _validate_uuid(text, code)
        return text

    def _layout(
        self, test_root: Path, *, require_source: bool = False
    ) -> tuple[Path, Path, Path, Path]:
        root, source_root, storage_root, export_root = _validated_layout(
            test_root,
            require_export_layout=self._require_export_layout,
        )
        if require_source and self._source_root_override is not None:
            source_root = self._source_root_override
            if not source_root.is_absolute():
                raise EncryptedDocumentError("document_source_root_invalid")
            _validate_private_directory(
                source_root, "document_source_root_invalid"
            )
        return root, source_root, storage_root, export_root


def _validated_layout(
    test_root: Path, *, require_export_layout: bool = True
) -> tuple[Path, Path, Path, Path]:
    root = Path(test_root)
    if not root.is_absolute():
        raise EncryptedDocumentError("document_test_root_invalid")
    _validate_private_directory(root, "document_test_root_invalid")
    _validate_marker(
        root / SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER,
        SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER_BYTES,
        "document_test_root_marker_invalid",
    )
    source_root = root / SOURCES_DIRECTORY
    storage_root = root / STORAGE_DIRECTORY
    export_root = root / EXPORTS_DIRECTORY
    required_directories = [source_root, storage_root]
    if require_export_layout:
        required_directories.append(export_root)
    for path in required_directories:
        _validate_private_directory(path, "document_test_layout_invalid")
    _validate_marker(
        storage_root / SYNTHETIC_DOCUMENT_STORAGE_MARKER,
        SYNTHETIC_DOCUMENT_STORAGE_MARKER_BYTES,
        "document_storage_marker_invalid",
    )
    if require_export_layout:
        _validate_marker(
            export_root / SYNTHETIC_DOCUMENT_EXPORT_MARKER,
            SYNTHETIC_DOCUMENT_EXPORT_MARKER_BYTES,
            "document_export_marker_invalid",
        )
    return root, source_root, storage_root, export_root


def _validate_private_directory(path: Path, code: str) -> None:
    try:
        status = os.stat(path, follow_symlinks=False)
    except OSError:
        raise EncryptedDocumentError(code) from None
    if (
        not stat.S_ISDIR(status.st_mode)
        or status.st_uid != os.getuid()
        or stat.S_IMODE(status.st_mode) & 0o077
    ):
        raise EncryptedDocumentError(code)


def _directory_identity(path: Path) -> tuple[Path, int, int]:
    try:
        status = os.stat(path, follow_symlinks=False)
    except OSError:
        raise EncryptedDocumentError("document_directory_identity_invalid") from None
    if not stat.S_ISDIR(status.st_mode):
        raise EncryptedDocumentError("document_directory_identity_invalid")
    return path, status.st_dev, status.st_ino


def _capture_layout_identity(
    *paths: Path,
) -> tuple[tuple[Path, int, int], ...]:
    return tuple(
        _directory_identity(path)
        for path in paths
    )


def _require_directory_identity(
    path: Path,
    expected: tuple[Path, int, int],
    code: str,
) -> None:
    observed = _directory_identity(path)
    if observed != expected:
        raise EncryptedDocumentError(code)


def _require_layout_identity(
    expected: tuple[tuple[Path, int, int], ...]
) -> None:
    for item in expected:
        _require_directory_identity(item[0], item, "document_test_root_changed")


def _validate_marker(path: Path, expected: bytes, code: str) -> None:
    try:
        status = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
            raise EncryptedDocumentError(code)
        with path.open("rb") as handle:
            value = handle.read(len(expected) + 1)
    except EncryptedDocumentError:
        raise
    except OSError:
        raise EncryptedDocumentError(code) from None
    if value != expected:
        raise EncryptedDocumentError(code)


def _bind_source(
    source_root: Path,
    name: str,
    chunk_size: int,
    *,
    required_prefix: bytes | None,
) -> _BoundSource:
    fd, identity = _open_regular_at(source_root, name, require_single_link=True)
    try:
        prefix_size = 0
        if required_prefix is not None:
            prefix = os.read(fd, len(required_prefix))
            if prefix != required_prefix:
                raise EncryptedDocumentError("document_source_not_synthetic")
            prefix_size = len(required_prefix)
        hasher = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, min(chunk_size, 1024 * 1024))
            if not chunk:
                break
            hasher.update(chunk)
            total += len(chunk)
        if total != identity[2] - prefix_size:
            raise EncryptedDocumentError("document_source_changed")
        bound = _BoundSource(
            fd=fd,
            directory=source_root,
            name=name,
            device=identity[0],
            inode=identity[1],
            file_size=identity[2],
            size=total,
            mtime_ns=identity[3],
            sha256=hasher.hexdigest(),
        )
        _require_bound_source_unchanged(bound)
        return bound
    except Exception:
        os.close(fd)
        raise


def _open_regular_at(
    directory: Path, name: str, *, require_single_link: bool = False
) -> tuple[int, tuple[int, int, int, int]]:
    dir_fd = _open_directory(directory)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except OSError:
        os.close(dir_fd)
        raise EncryptedDocumentError("document_file_open_failed") from None
    finally:
        if "fd" in locals():
            os.close(dir_fd)
    status = os.fstat(fd)
    if (
        not stat.S_ISREG(status.st_mode)
        or (require_single_link and status.st_nlink != 1)
    ):
        os.close(fd)
        raise EncryptedDocumentError("document_file_type_invalid")
    return fd, (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(path, flags)
    except OSError:
        raise EncryptedDocumentError("document_directory_open_failed") from None


def _open_exclusive_at(directory: Path, name: str) -> tuple[int, tuple[int, int, int, int]]:
    dir_fd = _open_directory(directory)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    except FileExistsError:
        raise EncryptedDocumentError("document_target_exists") from None
    except OSError:
        raise EncryptedDocumentError("document_target_create_failed") from None
    finally:
        os.close(dir_fd)
    status = os.fstat(fd)
    return fd, (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)


def _validated_storage_child(
    storage_root: Path, value: Path, *, allow_hidden: bool
) -> str:
    path = Path(value)
    if not path.is_absolute() or path.parent != storage_root:
        raise EncryptedDocumentError("document_container_path_invalid")
    name = _safe_leaf(path.name, "document_container_path_invalid")
    if _FILENAME_PATTERN.fullmatch(name):
        return name
    if allow_hidden and _RETAINED_PATTERN.fullmatch(name):
        return name
    raise EncryptedDocumentError("document_container_path_invalid")


def _safe_leaf(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or len(value) > 255
    ):
        raise EncryptedDocumentError(code)
    return value


def _container_filename(
    storage_id: str,
    rewrap_revision: int,
    *,
    include_rewrap_revision: bool = True,
) -> str:
    _validate_uuid(storage_id, "document_storage_id_invalid")
    _positive(rewrap_revision, "document_rewrap_revision_invalid")
    if include_rewrap_revision:
        return f"{storage_id}.w{rewrap_revision}{DOCUMENT_CONTAINER_EXTENSION}"
    return f"{storage_id}{DOCUMENT_CONTAINER_EXTENSION}"


def _find_retained_hardlink(
    storage_root: Path,
    verification: EncryptedDocumentVerificationResult,
) -> Path:
    matches: list[Path] = []
    for entry in os.scandir(storage_root):
        if not _RETAINED_PATTERN.fullmatch(entry.name):
            continue
        try:
            status = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if (
            stat.S_ISREG(status.st_mode)
            and status.st_dev == verification.container_device
            and status.st_ino == verification.container_inode
            and status.st_size == verification.container_size
            and status.st_mtime_ns == verification.container_mtime_ns
        ):
            matches.append(storage_root / entry.name)
    if len(matches) != 1:
        raise EncryptedDocumentError("document_retained_evidence_invalid")
    return matches[0]


def _matches_verification_evidence(
    storage_root: Path,
    name: str,
    verification: EncryptedDocumentVerificationResult | None,
) -> bool:
    if verification is None:
        return False
    try:
        size, digest = _hash_regular_at(storage_root, name)
        fd, identity = _open_regular_at(storage_root, name)
        os.close(fd)
    except EncryptedDocumentError:
        return False
    return (
        size == verification.container_size
        and digest == verification.container_sha256
        and identity[0] == verification.container_device
        and identity[1] == verification.container_inode
        and identity[3] == verification.container_mtime_ns
    )


def _publish_hardlink(directory: Path, source_name: str, target_name: str) -> None:
    dir_fd = _open_directory(directory)
    try:
        os.link(
            source_name,
            target_name,
            src_dir_fd=dir_fd,
            dst_dir_fd=dir_fd,
            follow_symlinks=False,
        )
    except FileExistsError:
        raise EncryptedDocumentError("document_target_exists") from None
    except OSError:
        raise EncryptedDocumentError("document_publish_failed") from None
    finally:
        os.close(dir_fd)


def _publish_rename_exclusive(
    directory: Path, source_name: str, target_name: str
) -> None:
    """Atomically publish without replacing an existing target.

    Python does not expose the no-replace rename variants uniformly. Sprint 10
    is an isolated foundation, so unsupported platforms fail closed instead of
    falling back to a check-then-rename sequence.
    """

    dir_fd = _open_directory(directory)
    try:
        if sys.platform == "darwin":
            libc = ctypes.CDLL(None, use_errno=True)
            renameatx_np = libc.renameatx_np
            renameatx_np.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            renameatx_np.restype = ctypes.c_int
            result = renameatx_np(
                dir_fd,
                os.fsencode(source_name),
                dir_fd,
                os.fsencode(target_name),
                0x00000004,  # RENAME_EXCL
            )
        elif sys.platform.startswith("linux"):
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = getattr(libc, "renameat2", None)
            if renameat2 is None:
                syscall_number = {
                    "x86_64": 316,
                    "amd64": 316,
                    "aarch64": 276,
                    "arm64": 276,
                }.get(platform.machine().lower())
                if syscall_number is None:
                    raise EncryptedDocumentError(
                        "document_publish_platform_unsupported"
                    )
                syscall = libc.syscall
                syscall.argtypes = (
                    ctypes.c_long,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_uint,
                )
                syscall.restype = ctypes.c_long
                result = syscall(
                    syscall_number,
                    dir_fd,
                    os.fsencode(source_name),
                    dir_fd,
                    os.fsencode(target_name),
                    0x00000001,  # RENAME_NOREPLACE
                )
            else:
                renameat2.argtypes = (
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_uint,
                )
                renameat2.restype = ctypes.c_int
                result = renameat2(
                    dir_fd,
                    os.fsencode(source_name),
                    dir_fd,
                    os.fsencode(target_name),
                    0x00000001,  # RENAME_NOREPLACE
                )
        elif os.name == "nt":
            # Windows rename is no-clobber when the destination exists. The
            # marker-bound layout is revalidated immediately before this call.
            os.rename(directory / source_name, directory / target_name)
            return
        else:
            raise EncryptedDocumentError("document_publish_platform_unsupported")
        if result == 0:
            return
        observed_errno = ctypes.get_errno()
        if observed_errno in {errno.EEXIST, errno.ENOTEMPTY}:
            raise EncryptedDocumentError("document_target_exists")
        raise EncryptedDocumentError("document_publish_failed")
    except EncryptedDocumentError:
        raise
    except FileExistsError:
        raise EncryptedDocumentError("document_target_exists") from None
    except OSError:
        raise EncryptedDocumentError("document_publish_failed") from None
    finally:
        os.close(dir_fd)


def _write_frame(fd: int, value: bytes, code: str) -> None:
    _write_all(fd, _UINT32.pack(len(value)), code)
    _write_all(fd, value, code)


def _read_frame(reader: _FDReader, *, minimum: int, maximum: int) -> bytes:
    size = _UINT32.unpack(
        reader.exact(_UINT32.size, "document_container_truncated")
    )[0]
    if size < minimum or size > maximum:
        raise EncryptedDocumentError("document_frame_size_invalid")
    return reader.exact(size, "document_container_truncated")


def _push(state, plaintext: bytes, aad: bytes, tag: int) -> bytes:
    try:
        return nacl.bindings.crypto_secretstream_xchacha20poly1305_push(
            state, plaintext, aad, tag
        )
    except Exception:
        raise EncryptedDocumentError("document_stream_encrypt_failed") from None


def _pull(state, ciphertext: bytes, aad: bytes) -> tuple[bytes, int]:
    try:
        return nacl.bindings.crypto_secretstream_xchacha20poly1305_pull(
            state, ciphertext, aad
        )
    except CryptoError:
        raise EncryptedDocumentError("document_stream_authentication_failed") from None
    except Exception:
        raise EncryptedDocumentError("document_stream_decrypt_failed") from None


def _write_all(fd: int, value: bytes, code: str) -> None:
    view = memoryview(value)
    offset = 0
    while offset < len(view):
        try:
            written = os.write(fd, view[offset:])
        except OSError:
            raise EncryptedDocumentError(code) from None
        if written <= 0:
            raise EncryptedDocumentError(code)
        offset += written


def _read_exact_source(fd: int, size: int) -> bytes:
    parts: list[bytes] = []
    remaining = size
    while remaining:
        chunk = os.read(fd, min(remaining, 1024 * 1024))
        if not chunk:
            raise EncryptedDocumentError("document_source_changed")
        parts.append(chunk)
        remaining -= len(chunk)
    return b"".join(parts)


def _require_bound_source_unchanged(value: _BoundSource) -> None:
    if value.payload is not None:
        if (
            len(value.payload) != value.size
            or hashlib.sha256(value.payload).hexdigest() != value.sha256
        ):
            raise EncryptedDocumentError("document_source_changed")
        return
    status = os.fstat(value.fd)
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_nlink != 1
        or status.st_dev != value.device
        or status.st_ino != value.inode
        or status.st_size != value.file_size
        or status.st_mtime_ns != value.mtime_ns
    ):
        raise EncryptedDocumentError("document_source_changed")
    _require_path_identity(
        value.directory,
        value.name,
        (value.device, value.inode, value.file_size, value.mtime_ns),
        "document_source_changed",
    )


def _require_fd_identity(
    fd: int, identity: tuple[int, int, int, int], code: str
) -> None:
    status = os.fstat(fd)
    if (
        not stat.S_ISREG(status.st_mode)
        or (status.st_dev, status.st_ino) != identity[:2]
    ):
        raise EncryptedDocumentError(code)


def _fd_identity(fd: int, code: str) -> tuple[int, int, int, int]:
    try:
        status = os.fstat(fd)
    except OSError:
        raise EncryptedDocumentError(code) from None
    if not stat.S_ISREG(status.st_mode):
        raise EncryptedDocumentError(code)
    return (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)


def _require_path_identity(
    directory: Path,
    name: str,
    identity: tuple[int, int, int, int],
    code: str,
) -> None:
    dir_fd = _open_directory(directory)
    try:
        status = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError:
        raise EncryptedDocumentError(code) from None
    finally:
        os.close(dir_fd)
    if (
        not stat.S_ISREG(status.st_mode)
        or (status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns)
        != identity
    ):
        raise EncryptedDocumentError(code)


def _require_absent(path: Path, code: str) -> None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    except OSError:
        raise EncryptedDocumentError(code) from None
    raise EncryptedDocumentError(code)


def _fsync_fd(fd: int, code: str) -> None:
    try:
        os.fsync(fd)
    except OSError:
        raise EncryptedDocumentError(code) from None


def _fsync_directory(path: Path, code: str) -> None:
    fd = _open_directory(path)
    try:
        _fsync_fd(fd, code)
    finally:
        os.close(fd)


def _hash_regular_at(directory: Path, name: str) -> tuple[int, str]:
    fd, identity = _open_regular_at(directory, name)
    try:
        hasher = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            total += len(chunk)
        _require_fd_identity(fd, identity, "document_export_changed")
        _require_path_identity(
            directory, name, identity, "document_export_changed"
        )
        return total, hasher.hexdigest()
    finally:
        os.close(fd)


def _clear_owned_fd_best_effort(
    fd: int, identity: tuple[int, int, int, int]
) -> None:
    try:
        _require_fd_identity(fd, identity, "document_export_temp_changed")
        os.ftruncate(fd, 0)
        os.fsync(fd)
    except OSError:
        pass
    except EncryptedDocumentError:
        pass


def _erase(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


def _validate_uuid(value: object, code: str) -> None:
    try:
        validate_uuid4(value)
    except Exception:
        raise EncryptedDocumentError(code) from None


def _positive(value: object, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EncryptedDocumentError(code)
