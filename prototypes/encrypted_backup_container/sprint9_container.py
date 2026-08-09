"""Isolated writer, verifier, and restore for synthetic encrypted backups.

The service accepts only direct children of an injected private test root.
It has no product RuntimePaths, UI, startup, or product backup/restore imports.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import struct
from typing import Callable, Mapping, Protocol

import nacl.bindings
from nacl.exceptions import CryptoError

from src.core.database_engine import SQLCipherConnectionProvider
from src.security.backup_container import (
    BACKUP_KEY_BYTES,
    BACKUP_KEY_NONCE_BYTES,
    DEFAULT_BACKUP_CHUNK_SIZE,
    ENCRYPTED_BACKUP_MAGIC,
    MAX_BACKUP_HEADER_BYTES,
    MAX_BACKUP_MANIFEST_BYTES,
    BackupContainerContextV1,
    BackupContainerHeaderV1,
    BackupEntryRole,
    BackupManifestEntryV1,
    EncryptedBackupError,
    EncryptedBackupManifestV1,
    build_backup_key_envelope,
    canonical_json,
    entry_record_aad,
    expected_chunk_size,
    final_record_aad,
    format_utc,
    manifest_record_aad,
    manifest_sha256,
    open_backup_key_envelope,
    validate_backup_chunk_size,
)
from src.security.data_keys import LoadedDataMasterKey
from src.security.domain import validate_uuid4
from src.security.ports import RandomSource, UtcClock


ENCRYPTED_BACKUP_EXTENSION = ".jkmebackup"
RESTORE_COMPLETION_FILENAME = ".restore-complete.json"
SYNTHETIC_BACKUP_TEST_ROOT_MARKER = ".jkm-security-sprint9-test-root"
SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES = (
    b"jenaplan-security-sprint9-synthetic-root-v1\n"
)
SYNTHETIC_BACKUP_APPLICATION_ID = 0x4A4B4D39
SYNTHETIC_BACKUP_USER_VERSION = 9001
SYNTHETIC_BACKUP_GUARD_TABLE = "__jkm_security_sprint_9_synthetic_guard"
SYNTHETIC_BACKUP_GUARD_VALUE = "jkm-security-sprint9-synthetic-only-v1"
_UINT32 = struct.Struct(">I")
_SECRETSTREAM_OVERHEAD = (
    nacl.bindings.crypto_secretstream_xchacha20poly1305_ABYTES
)
_SECRETSTREAM_HEADER_BYTES = (
    nacl.bindings.crypto_secretstream_xchacha20poly1305_HEADERBYTES
)
_SECRETSTREAM_KEY_BYTES = (
    nacl.bindings.crypto_secretstream_xchacha20poly1305_KEYBYTES
)
_TAG_MESSAGE = nacl.bindings.crypto_secretstream_xchacha20poly1305_TAG_MESSAGE
_TAG_FINAL = nacl.bindings.crypto_secretstream_xchacha20poly1305_TAG_FINAL


class EntryConsumer(Protocol):
    def start(self, entry: BackupManifestEntryV1) -> None: ...

    def write(self, entry: BackupManifestEntryV1, chunk: bytes) -> None: ...

    def finish(self, entry: BackupManifestEntryV1) -> None: ...


@dataclass(frozen=True)
class BackupSourceFile:
    path: Path
    entry_id: str
    role: BackupEntryRole


@dataclass(frozen=True)
class EncryptedBackupVerificationResult:
    header: BackupContainerHeaderV1
    manifest: EncryptedBackupManifestV1
    container_size: int
    container_sha256: str


@dataclass(frozen=True)
class EncryptedBackupRestoreResult:
    restore_root: Path
    database_path: Path
    document_paths: tuple[Path, ...]
    completion_path: Path
    verification: EncryptedBackupVerificationResult


@dataclass(frozen=True)
class EncryptedBackupExtractionResult:
    """Fully authenticated extraction without product completion state."""

    restore_root: Path
    entry_paths: Mapping[str, Path]
    verification: EncryptedBackupVerificationResult


@dataclass
class _BoundSource:
    source: BackupSourceFile
    fd: int
    device: int
    inode: int
    size: int
    mtime_ns: int
    sha256: str


class _FDReader:
    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.hasher = hashlib.sha256()
        self.bytes_read = 0

    def read_exact(self, size: int, code: str) -> bytes:
        if size < 0:
            raise EncryptedBackupError(code)
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            try:
                chunk = os.read(self.fd, min(remaining, 1024 * 1024))
            except OSError:
                raise EncryptedBackupError("backup_container_read_failed") from None
            if not chunk:
                raise EncryptedBackupError(code)
            chunks.append(chunk)
            self.hasher.update(chunk)
            self.bytes_read += len(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def read_one(self) -> bytes:
        try:
            value = os.read(self.fd, 1)
        except OSError:
            raise EncryptedBackupError("backup_container_read_failed") from None
        if value:
            self.hasher.update(value)
            self.bytes_read += 1
        return value


class _RestoreConsumer:
    def __init__(
        self,
        *,
        root_fd: int,
        fault: Callable[[str], None],
    ) -> None:
        self._root_fd = root_fd
        self._fault = fault
        self._current_fd: int | None = None
        self._current_entry: BackupManifestEntryV1 | None = None

    def start(self, entry: BackupManifestEntryV1) -> None:
        if self._current_fd is not None:
            raise EncryptedBackupError("backup_restore_state_invalid")
        self._fault(f"restore_before_entry:{entry.role.value}")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            self._current_fd = os.open(
                entry.restore_name,
                flags,
                0o600,
                dir_fd=self._root_fd,
            )
        except OSError:
            raise EncryptedBackupError(
                "backup_restore_target_create_failed"
            ) from None
        self._current_entry = entry

    def write(self, entry: BackupManifestEntryV1, chunk: bytes) -> None:
        if self._current_fd is None or self._current_entry is not entry:
            raise EncryptedBackupError("backup_restore_state_invalid")
        self._fault(f"restore_write:{entry.role.value}")
        _write_all(self._current_fd, chunk, "backup_restore_write_failed")

    def finish(self, entry: BackupManifestEntryV1) -> None:
        if self._current_fd is None or self._current_entry is not entry:
            raise EncryptedBackupError("backup_restore_state_invalid")
        try:
            self._fault(f"restore_before_fsync:{entry.role.value}")
            os.fsync(self._current_fd)
        except OSError:
            raise EncryptedBackupError("backup_restore_fsync_failed") from None
        finally:
            os.close(self._current_fd)
            self._current_fd = None
            self._current_entry = None
        self._fault(f"restore_after_entry:{entry.role.value}")

    def close(self) -> None:
        if self._current_fd is not None:
            os.close(self._current_fd)
            self._current_fd = None
            self._current_entry = None


class SyntheticEncryptedBackupServiceV1:
    """Smallest complete synthetic container path for Security Sprint 9."""

    def __init__(
        self,
        *,
        random_source: RandomSource,
        clock: UtcClock,
        sqlcipher_provider: SQLCipherConnectionProvider,
        fault_injector: Callable[[str], None] | None = None,
        chunk_size: int = DEFAULT_BACKUP_CHUNK_SIZE,
        sqlcipher_guard_validator: (
            Callable[[object, BackupContainerContextV1], None] | None
        ) = None,
    ) -> None:
        self._random = random_source
        self._clock = clock
        self._provider = sqlcipher_provider
        self._fault = fault_injector or (lambda _phase: None)
        self._sqlcipher_guard_validator = sqlcipher_guard_validator
        validate_backup_chunk_size(chunk_size)
        self._chunk_size = chunk_size

    def create(
        self,
        *,
        test_root: Path,
        target: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
        database_source: BackupSourceFile,
        document_sources: tuple[BackupSourceFile, ...],
        database_key: bytes,
    ) -> EncryptedBackupVerificationResult:
        root = _validated_test_root(test_root)
        destination = _validated_direct_child(
            root, target, required_suffix=ENCRYPTED_BACKUP_EXTENSION
        )
        _require_absent(destination, "backup_target_exists")
        _validate_database_key(database_key)
        sources = _validated_sources(
            root,
            database_source=database_source,
            document_sources=document_sources,
        )
        bound: list[_BoundSource] = []
        try:
            bound.append(_bind_source(root, sources[0], self._chunk_size))
            self._verify_bound_sqlcipher(
                bound[0],
                database_key=database_key,
                expected_context=context,
            )
            bound.extend(
                _bind_source(root, source, self._chunk_size)
                for source in sources[1:]
            )
            manifest = _build_manifest(
                context=context,
                container_id=self._new_uuid("backup_container_id_invalid"),
                created_at=format_utc(self._clock.utc_now()),
                chunk_size=self._chunk_size,
                bound=tuple(bound),
            )
            backup_key_buffer = bytearray(self._random.bytes(BACKUP_KEY_BYTES))
            try:
                if len(backup_key_buffer) != BACKUP_KEY_BYTES:
                    raise EncryptedBackupError("backup_key_random_invalid")
                backup_key = bytes(backup_key_buffer)
                if len(backup_key) != _SECRETSTREAM_KEY_BYTES:
                    raise EncryptedBackupError("backup_key_length_invalid")
                push_state = (
                    nacl.bindings.crypto_secretstream_xchacha20poly1305_state()
                )
                try:
                    stream_header = (
                        nacl.bindings.crypto_secretstream_xchacha20poly1305_init_push(
                            push_state, backup_key
                        )
                    )
                except Exception:
                    raise EncryptedBackupError(
                        "backup_secretstream_init_failed"
                    ) from None
                if len(stream_header) != _SECRETSTREAM_HEADER_BYTES:
                    raise EncryptedBackupError("backup_stream_header_invalid")
                backup_key_id = self._new_uuid("backup_key_id_invalid")
                nonce = self._random.bytes(BACKUP_KEY_NONCE_BYTES)
                envelope = build_backup_key_envelope(
                    dmk,
                    context=context,
                    container_id=manifest.container_id,
                    backup_key_id=backup_key_id,
                    stream_header=stream_header,
                    chunk_size=self._chunk_size,
                    backup_key=backup_key,
                    nonce=nonce,
                )
                header = BackupContainerHeaderV1(
                    container_id=manifest.container_id,
                    chunk_size=self._chunk_size,
                    stream_header=stream_header,
                    envelope=envelope,
                )
                header_bytes = header.to_bytes()
                run_id = self._new_uuid("backup_run_id_invalid")
                retained = root / f".{destination.name}.{run_id}.retained"
                _require_absent(retained, "backup_temp_exists")
                self._write_container(
                    retained,
                    header_bytes=header_bytes,
                    manifest=manifest,
                    push_state=push_state,
                    bound=tuple(bound),
                )
            finally:
                _erase(backup_key_buffer)

            _fsync_directory(root, "backup_directory_fsync_failed")
            self._fault("writer_after_retained_fsync")
            prepublish = self.verify(
                test_root=root,
                container=retained,
                dmk=dmk,
                context=context,
            )
            if prepublish.manifest != manifest:
                raise EncryptedBackupError("backup_self_verification_failed")
            self._fault("writer_after_preverify")
            _require_absent(destination, "backup_target_exists")
            try:
                os.link(retained, destination, follow_symlinks=False)
            except FileExistsError:
                raise EncryptedBackupError("backup_target_exists") from None
            except OSError:
                raise EncryptedBackupError("backup_publish_failed") from None
            _fsync_directory(root, "backup_directory_fsync_failed")
            self._fault("writer_after_publish")
            result = self.verify(
                test_root=root,
                container=destination,
                dmk=dmk,
                context=context,
            )
            if result.manifest != manifest:
                raise EncryptedBackupError("backup_self_verification_failed")
            return result
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_writer_failed") from None
        finally:
            for source in bound:
                os.close(source.fd)

    def verify(
        self,
        *,
        test_root: Path,
        container: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
    ) -> EncryptedBackupVerificationResult:
        root = _validated_test_root(test_root)
        path = _validated_direct_child(
            root, container, required_suffix=None, allow_hidden=True
        )
        return self._consume(
            container=path,
            dmk=dmk,
            context=context,
            consumer=None,
        )

    def verify_path(
        self,
        *,
        container: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
    ) -> EncryptedBackupVerificationResult:
        """Verify one absolute regular container outside the synthetic root.

        The caller owns destination policy. Descriptor binding, final-tag and
        physical-EOF checks remain identical to :meth:`verify`.
        """

        path = Path(container)
        if not path.is_absolute():
            raise EncryptedBackupError("backup_container_path_invalid")
        return self._consume(
            container=path,
            dmk=dmk,
            context=context,
            consumer=None,
        )

    def extract_to_new_root(
        self,
        *,
        container: Path,
        restore_root: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
    ) -> EncryptedBackupExtractionResult:
        """Authenticate twice and extract only into a new private root.

        This primitive intentionally writes no completion marker. A higher
        layer must validate database keys, schemas and crossbindings before it
        can publish its own staging-ready state.
        """

        container_path = Path(container)
        destination = Path(restore_root)
        if not container_path.is_absolute() or not destination.is_absolute():
            raise EncryptedBackupError("backup_restore_path_invalid")
        if destination.name in {"", ".", ".."}:
            raise EncryptedBackupError("backup_restore_path_invalid")
        _require_absent(destination, "backup_restore_root_exists")
        verification = self.verify_path(
            container=container_path,
            dmk=dmk,
            context=context,
        )
        restored_bound: list[_BoundSource] = []
        root_fd: int | None = None
        consumer: _RestoreConsumer | None = None
        try:
            try:
                os.mkdir(destination, mode=0o700)
                os.chmod(destination, 0o700)
            except OSError:
                raise EncryptedBackupError(
                    "backup_restore_root_create_failed"
                ) from None
            root_status = os.stat(destination, follow_symlinks=False)
            if (
                not stat.S_ISDIR(root_status.st_mode)
                or stat.S_IMODE(root_status.st_mode) & 0o077
                or (hasattr(os, "getuid") and root_status.st_uid != os.getuid())
            ):
                raise EncryptedBackupError("backup_restore_root_changed")
            root_identity = (root_status.st_dev, root_status.st_ino)
            self._fault("restore_before_root_open")
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                root_fd = os.open(destination, flags)
            except OSError:
                raise EncryptedBackupError("backup_restore_root_changed") from None
            opened_root = os.fstat(root_fd)
            if (
                not stat.S_ISDIR(opened_root.st_mode)
                or (opened_root.st_dev, opened_root.st_ino) != root_identity
            ):
                raise EncryptedBackupError("backup_restore_root_changed")
            consumer = _RestoreConsumer(root_fd=root_fd, fault=self._fault)
            self._fault("restore_after_root_created")
            second = self._consume(
                container=container_path,
                dmk=dmk,
                context=context,
                consumer=consumer,
            )
            if second != verification:
                raise EncryptedBackupError("backup_restore_reverify_mismatch")
            _require_directory_identity(destination, root_identity)
            _fsync_fd(root_fd, "backup_restore_directory_fsync_failed")
            entry_paths: dict[str, Path] = {}
            for entry in verification.manifest.entries:
                restored = destination / entry.restore_name
                restored_item = _bind_source_path(
                    BackupSourceFile(restored, entry.entry_id, entry.role),
                    verification.manifest.chunk_size,
                )
                restored_bound.append(restored_item)
                if (
                    restored_item.size != entry.plaintext_size
                    or restored_item.sha256 != entry.sha256
                ):
                    raise EncryptedBackupError(
                        "backup_restore_entry_verification_failed"
                    )
                entry_paths[entry.entry_id] = restored
            self._fault("restore_after_extraction_before_reopen")
            _require_directory_identity(destination, root_identity)
            for source in restored_bound:
                _require_bound_source_unchanged(source)
            return EncryptedBackupExtractionResult(
                restore_root=destination,
                entry_paths=entry_paths,
                verification=verification,
            )
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_restore_failed") from None
        finally:
            if consumer is not None:
                consumer.close()
            if root_fd is not None:
                os.close(root_fd)
            for source in restored_bound:
                os.close(source.fd)

    def restore(
        self,
        *,
        test_root: Path,
        container: Path,
        restore_root: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
        database_key: bytes,
        expected_sources: Mapping[str, Path],
    ) -> EncryptedBackupRestoreResult:
        root = _validated_test_root(test_root)
        container_path = _validated_direct_child(
            root, container, required_suffix=ENCRYPTED_BACKUP_EXTENSION
        )
        destination = _validated_direct_child(
            root, restore_root, required_suffix=None
        )
        _require_absent(destination, "backup_restore_root_exists")
        _validate_database_key(database_key)

        verification = self._consume(
            container=container_path,
            dmk=dmk,
            context=context,
            consumer=None,
        )
        expected_bound = _bind_expected_sources(
            root, verification.manifest, expected_sources
        )
        restored_bound: list[_BoundSource] = []
        root_fd: int | None = None
        consumer: _RestoreConsumer | None = None
        try:
            try:
                os.mkdir(destination, mode=0o700)
            except OSError:
                raise EncryptedBackupError(
                    "backup_restore_root_create_failed"
                ) from None
            root_status = os.stat(destination, follow_symlinks=False)
            if not stat.S_ISDIR(root_status.st_mode):
                raise EncryptedBackupError("backup_restore_root_changed")
            root_identity = (root_status.st_dev, root_status.st_ino)
            self._fault("restore_before_root_open")
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                root_fd = os.open(destination, flags)
            except OSError:
                raise EncryptedBackupError("backup_restore_root_changed") from None
            opened_root = os.fstat(root_fd)
            if (
                not stat.S_ISDIR(opened_root.st_mode)
                or (opened_root.st_dev, opened_root.st_ino) != root_identity
            ):
                raise EncryptedBackupError("backup_restore_root_changed")
            consumer = _RestoreConsumer(root_fd=root_fd, fault=self._fault)
            self._fault("restore_after_root_created")
            second = self._consume(
                container=container_path,
                dmk=dmk,
                context=context,
                consumer=consumer,
            )
            if second != verification:
                raise EncryptedBackupError("backup_restore_reverify_mismatch")
            _require_directory_identity(destination, root_identity)
            _fsync_fd(root_fd, "backup_restore_directory_fsync_failed")
            database_entry = verification.manifest.entries[0]
            database_path = destination / database_entry.restore_name
            document_paths = tuple(
                destination / entry.restore_name
                for entry in verification.manifest.entries[1:]
            )
            for entry in verification.manifest.entries:
                restored = destination / entry.restore_name
                restored_item = _bind_source_path(
                    BackupSourceFile(
                        restored,
                        entry.entry_id,
                        entry.role,
                    ),
                    verification.manifest.chunk_size,
                )
                restored_bound.append(restored_item)
                expected = expected_bound[entry.entry_id]
                if (
                    restored_item.size != entry.plaintext_size
                    or restored_item.sha256 != entry.sha256
                    or not _bound_files_equal(
                        restored_item,
                        expected,
                        verification.manifest.chunk_size,
                    )
                ):
                    raise EncryptedBackupError(
                        "backup_restore_source_comparison_failed"
                    )
            self._verify_bound_sqlcipher(
                restored_bound[0],
                database_key=database_key,
                expected_context=context,
            )
            self._fault("restore_before_completion")
            _require_directory_identity(destination, root_identity)
            for source in (*restored_bound, *expected_bound.values()):
                _require_bound_source_unchanged(source)
            completion_payload = canonical_json(
                {
                    "container_sha256": verification.container_sha256,
                    "entry_count": len(verification.manifest.entries),
                    "manifest_sha256": manifest_sha256(
                        verification.manifest.to_bytes()
                    ),
                    "restore_format_version": 1,
                }
            )
            completion_retained_name = (
                f".{RESTORE_COMPLETION_FILENAME}."
                f"{self._new_uuid('backup_restore_run_id_invalid')}.retained"
            )
            completion_fd = _open_exclusive_at(
                root_fd, completion_retained_name
            )
            try:
                _write_all(
                    completion_fd,
                    completion_payload,
                    "backup_restore_completion_write_failed",
                )
                _fsync_fd(
                    completion_fd, "backup_restore_completion_fsync_failed"
                )
            finally:
                os.close(completion_fd)
            self._fault("restore_after_completion_file_fsync")
            try:
                os.link(
                    completion_retained_name,
                    RESTORE_COMPLETION_FILENAME,
                    src_dir_fd=root_fd,
                    dst_dir_fd=root_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                raise EncryptedBackupError(
                    "backup_restore_completion_exists"
                ) from None
            except OSError:
                raise EncryptedBackupError(
                    "backup_restore_completion_publish_failed"
                ) from None
            self._fault("restore_after_completion_publish")
            _fsync_fd(root_fd, "backup_restore_directory_fsync_failed")
            self._fault("restore_after_completion")
            return EncryptedBackupRestoreResult(
                restore_root=destination,
                database_path=database_path,
                document_paths=document_paths,
                completion_path=destination / RESTORE_COMPLETION_FILENAME,
                verification=verification,
            )
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_restore_failed") from None
        finally:
            if consumer is not None:
                consumer.close()
            if root_fd is not None:
                os.close(root_fd)
            for source in restored_bound:
                os.close(source.fd)
            for source in expected_bound.values():
                os.close(source.fd)

    def _write_container(
        self,
        path: Path,
        *,
        header_bytes: bytes,
        manifest: EncryptedBackupManifestV1,
        push_state,
        bound: tuple[_BoundSource, ...],
    ) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
        except OSError:
            raise EncryptedBackupError("backup_temp_create_failed") from None
        try:
            _write_all(fd, ENCRYPTED_BACKUP_MAGIC, "backup_header_write_failed")
            _write_all(
                fd,
                _UINT32.pack(len(header_bytes)),
                "backup_header_write_failed",
            )
            _write_all(fd, header_bytes, "backup_header_write_failed")
            self._fault("writer_after_header")

            manifest_bytes = manifest.to_bytes()
            manifest_ciphertext = _secretstream_push(
                push_state,
                manifest_bytes,
                manifest_record_aad(header_bytes, len(manifest_bytes)),
                _TAG_MESSAGE,
            )
            _write_frame(fd, manifest_ciphertext, "backup_manifest_write_failed")
            self._fault("writer_after_manifest")
            manifest_digest = manifest_sha256(manifest_bytes)

            ordinal = 1
            for source, entry in zip(bound, manifest.entries, strict=True):
                os.lseek(source.fd, 0, os.SEEK_SET)
                streamed_hash = hashlib.sha256()
                streamed_size = 0
                for chunk_index in range(entry.chunk_count):
                    expected_size = expected_chunk_size(
                        entry,
                        chunk_size=manifest.chunk_size,
                        chunk_index=chunk_index,
                    )
                    chunk = _read_source_exact(source.fd, expected_size)
                    streamed_hash.update(chunk)
                    streamed_size += len(chunk)
                    ciphertext = _secretstream_push(
                        push_state,
                        chunk,
                        entry_record_aad(
                            header_bytes,
                            manifest_sha256=manifest_digest,
                            record_ordinal=ordinal,
                            entry=entry,
                            chunk_index=chunk_index,
                            plaintext_size=len(chunk),
                        ),
                        _TAG_MESSAGE,
                    )
                    _write_frame(fd, ciphertext, "backup_entry_write_failed")
                    self._fault(f"writer_after_chunk:{entry.role.value}")
                    ordinal += 1
                _require_bound_source_unchanged(source)
                if (
                    streamed_size != entry.plaintext_size
                    or streamed_hash.hexdigest() != entry.sha256
                ):
                    raise EncryptedBackupError("backup_source_changed")
                self._fault(f"writer_after_entry:{entry.role.value}")

            final_ciphertext = _secretstream_push(
                push_state,
                b"",
                final_record_aad(
                    header_bytes,
                    manifest_sha256=manifest_digest,
                    record_ordinal=ordinal,
                    entry_count=len(manifest.entries),
                    total_plaintext_size=manifest.total_plaintext_size,
                ),
                _TAG_FINAL,
            )
            self._fault("writer_before_final")
            _write_frame(fd, final_ciphertext, "backup_final_write_failed")
            self._fault("writer_after_final")
            _fsync_fd(fd, "backup_file_fsync_failed")
            self._fault("writer_after_file_fsync")
        except EncryptedBackupError:
            raise
        except OSError:
            raise EncryptedBackupError("backup_writer_io_failed") from None
        finally:
            os.close(fd)

    def _consume(
        self,
        *,
        container: Path,
        dmk: LoadedDataMasterKey,
        context: BackupContainerContextV1,
        consumer: EntryConsumer | None,
    ) -> EncryptedBackupVerificationResult:
        fd, initial = _open_bound_regular(container)
        reader = _FDReader(fd)
        try:
            if (
                reader.read_exact(
                    len(ENCRYPTED_BACKUP_MAGIC), "backup_container_truncated"
                )
                != ENCRYPTED_BACKUP_MAGIC
            ):
                raise EncryptedBackupError("backup_container_magic_invalid")
            header_size = _UINT32.unpack(
                reader.read_exact(_UINT32.size, "backup_container_truncated")
            )[0]
            if header_size < 1 or header_size > MAX_BACKUP_HEADER_BYTES:
                raise EncryptedBackupError("backup_header_size_invalid")
            header_bytes = reader.read_exact(
                header_size, "backup_container_truncated"
            )
            header = BackupContainerHeaderV1.from_bytes(header_bytes)
            backup_key = open_backup_key_envelope(
                dmk, context=context, header=header
            )
            pull_state = (
                nacl.bindings.crypto_secretstream_xchacha20poly1305_state()
            )
            try:
                nacl.bindings.crypto_secretstream_xchacha20poly1305_init_pull(
                    pull_state, header.stream_header, backup_key
                )
            except Exception:
                raise EncryptedBackupError(
                    "backup_secretstream_init_failed"
                ) from None

            manifest_ciphertext = _read_frame(
                reader,
                minimum=_SECRETSTREAM_OVERHEAD,
                maximum=MAX_BACKUP_MANIFEST_BYTES + _SECRETSTREAM_OVERHEAD,
            )
            manifest_plaintext_size = (
                len(manifest_ciphertext) - _SECRETSTREAM_OVERHEAD
            )
            manifest_bytes, tag = _secretstream_pull(
                pull_state,
                manifest_ciphertext,
                manifest_record_aad(header_bytes, manifest_plaintext_size),
            )
            if tag != _TAG_MESSAGE:
                raise EncryptedBackupError("backup_manifest_tag_invalid")
            manifest = EncryptedBackupManifestV1.from_bytes(manifest_bytes)
            if (
                manifest.container_id != header.container_id
                or manifest.chunk_size != header.chunk_size
                or manifest.context.binding_payload()
                != context.binding_payload()
            ):
                raise EncryptedBackupError("backup_container_context_mismatch")
            manifest_digest = manifest_sha256(manifest_bytes)

            ordinal = 1
            for entry in manifest.entries:
                if consumer is not None:
                    consumer.start(entry)
                entry_hasher = hashlib.sha256()
                entry_size = 0
                for chunk_index in range(entry.chunk_count):
                    expected_size = expected_chunk_size(
                        entry,
                        chunk_size=manifest.chunk_size,
                        chunk_index=chunk_index,
                    )
                    ciphertext = _read_frame(
                        reader,
                        minimum=expected_size + _SECRETSTREAM_OVERHEAD,
                        maximum=expected_size + _SECRETSTREAM_OVERHEAD,
                    )
                    plaintext, tag = _secretstream_pull(
                        pull_state,
                        ciphertext,
                        entry_record_aad(
                            header_bytes,
                            manifest_sha256=manifest_digest,
                            record_ordinal=ordinal,
                            entry=entry,
                            chunk_index=chunk_index,
                            plaintext_size=expected_size,
                        ),
                    )
                    if tag != _TAG_MESSAGE or len(plaintext) != expected_size:
                        raise EncryptedBackupError("backup_entry_tag_invalid")
                    entry_hasher.update(plaintext)
                    entry_size += len(plaintext)
                    if consumer is not None:
                        consumer.write(entry, plaintext)
                    ordinal += 1
                if (
                    entry_size != entry.plaintext_size
                    or entry_hasher.hexdigest() != entry.sha256
                ):
                    raise EncryptedBackupError("backup_entry_integrity_failed")
                if consumer is not None:
                    consumer.finish(entry)

            final_ciphertext = _read_frame(
                reader,
                minimum=_SECRETSTREAM_OVERHEAD,
                maximum=_SECRETSTREAM_OVERHEAD,
            )
            final_plaintext, final_tag = _secretstream_pull(
                pull_state,
                final_ciphertext,
                final_record_aad(
                    header_bytes,
                    manifest_sha256=manifest_digest,
                    record_ordinal=ordinal,
                    entry_count=len(manifest.entries),
                    total_plaintext_size=manifest.total_plaintext_size,
                ),
            )
            if final_tag != _TAG_FINAL or final_plaintext:
                raise EncryptedBackupError("backup_final_tag_invalid")
            if reader.read_one():
                raise EncryptedBackupError("backup_trailing_data")
            final_status = os.fstat(fd)
            if _file_identity(final_status) != _file_identity(initial):
                raise EncryptedBackupError("backup_container_changed")
            try:
                path_status = os.stat(container, follow_symlinks=False)
            except OSError:
                raise EncryptedBackupError("backup_container_changed") from None
            if (
                not stat.S_ISREG(path_status.st_mode)
                or _file_identity(path_status) != _file_identity(initial)
            ):
                raise EncryptedBackupError("backup_container_changed")
            return EncryptedBackupVerificationResult(
                header=header,
                manifest=manifest,
                container_size=reader.bytes_read,
                container_sha256=reader.hasher.hexdigest(),
            )
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_verification_failed") from None
        finally:
            os.close(fd)

    def _verify_bound_sqlcipher(
        self,
        source: _BoundSource,
        *,
        database_key: bytes,
        expected_context: BackupContainerContextV1,
    ) -> None:
        connection = None
        key_buffer = bytearray(database_key)
        try:
            _require_bound_source_unchanged(source)
            driver = self._provider._load_driver()
            self._provider._probe_engine_version(driver)
            uri = f"{source.source.path.resolve().as_uri()}?mode=ro&immutable=1"
            connection = driver.connect(
                uri,
                uri=True,
                cached_statements=0,
            )
            self._provider._apply_key(connection, key_buffer)
            self._provider._verify_engine_version(connection)
            self._provider._configure_cipher_before_authentication(connection)
            self._provider._authenticate_schema(connection)
            connection.execute("PRAGMA query_only = ON")
            self._provider.verify_integrity(connection)
            sqlite_row = connection.execute("SELECT sqlite_version()").fetchone()
            cipher_row = connection.execute("PRAGMA cipher_version").fetchone()
            application_row = connection.execute("PRAGMA application_id").fetchone()
            user_row = connection.execute("PRAGMA user_version").fetchone()
            if (
                sqlite_row is None
                or str(sqlite_row[0]) != expected_context.sqlite_version
                or cipher_row is None
                or str(cipher_row[0]) != expected_context.sqlcipher_version
            ):
                raise EncryptedBackupError(
                    "backup_sqlcipher_synthetic_guard_invalid"
                )
            if self._sqlcipher_guard_validator is None:
                guard_rows = connection.execute(
                    f'SELECT marker FROM "{SYNTHETIC_BACKUP_GUARD_TABLE}"'
                ).fetchall()
                if (
                    application_row is None
                    or int(application_row[0])
                    != SYNTHETIC_BACKUP_APPLICATION_ID
                    or user_row is None
                    or int(user_row[0]) != SYNTHETIC_BACKUP_USER_VERSION
                    or guard_rows != [(SYNTHETIC_BACKUP_GUARD_VALUE,)]
                ):
                    raise EncryptedBackupError(
                        "backup_sqlcipher_synthetic_guard_invalid"
                    )
            else:
                self._sqlcipher_guard_validator(
                    connection,
                    expected_context,
                )
            _require_bound_source_unchanged(source)
        except EncryptedBackupError:
            raise
        except Exception:
            raise EncryptedBackupError("backup_sqlcipher_verification_failed") from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            _erase(key_buffer)

    def _new_uuid(self, code: str) -> str:
        value = self._random.uuid4()
        try:
            validate_uuid4(value)
        except Exception:
            raise EncryptedBackupError(code) from None
        return value


def _validated_test_root(value: Path) -> Path:
    root = Path(value)
    if not root.is_absolute():
        raise EncryptedBackupError("backup_test_root_invalid")
    try:
        status = os.lstat(root)
    except OSError:
        raise EncryptedBackupError("backup_test_root_invalid") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise EncryptedBackupError("backup_test_root_invalid")
    if stat.S_IMODE(status.st_mode) & 0o077:
        raise EncryptedBackupError("backup_test_root_not_private")
    if hasattr(os, "getuid") and status.st_uid != os.getuid():
        raise EncryptedBackupError("backup_test_root_owner_invalid")
    marker = root / SYNTHETIC_BACKUP_TEST_ROOT_MARKER
    try:
        marker_fd, marker_status = _open_bound_regular(marker)
    except EncryptedBackupError:
        raise EncryptedBackupError("backup_test_root_marker_invalid") from None
    try:
        if (
            marker_status.st_size != len(SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES)
            or os.read(
                marker_fd, len(SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES) + 1
            )
            != SYNTHETIC_BACKUP_TEST_ROOT_MARKER_BYTES
        ):
            raise EncryptedBackupError("backup_test_root_marker_invalid")
    finally:
        os.close(marker_fd)
    return root


def _validated_direct_child(
    root: Path,
    value: Path,
    *,
    required_suffix: str | None,
    allow_hidden: bool = False,
) -> Path:
    path = Path(value)
    if (
        not path.is_absolute()
        or path.parent != root
        or path.name in {"", ".", ".."}
        or (not allow_hidden and path.name.startswith("."))
        or "/" in path.name
        or "\\" in path.name
    ):
        raise EncryptedBackupError("backup_path_outside_test_root")
    if required_suffix is not None and path.suffix != required_suffix:
        raise EncryptedBackupError("backup_path_extension_invalid")
    return path


def _validated_sources(
    root: Path,
    *,
    database_source: BackupSourceFile,
    document_sources: tuple[BackupSourceFile, ...],
) -> tuple[BackupSourceFile, ...]:
    if (
        not isinstance(database_source, BackupSourceFile)
        or database_source.role is not BackupEntryRole.SQLCIPHER_DATABASE
        or not isinstance(document_sources, tuple)
        or not document_sources
    ):
        raise EncryptedBackupError("backup_source_roles_invalid")
    documents = tuple(sorted(document_sources, key=lambda item: item.entry_id))
    if any(
        not isinstance(source, BackupSourceFile)
        or source.role is not BackupEntryRole.MANAGED_DOCUMENT
        for source in documents
    ):
        raise EncryptedBackupError("backup_source_roles_invalid")
    sources = (database_source, *documents)
    ids: list[str] = []
    paths: list[Path] = []
    for source in sources:
        try:
            validate_uuid4(source.entry_id)
        except Exception:
            raise EncryptedBackupError("backup_entry_id_invalid") from None
        source_path = _validated_direct_child(
            root, source.path, required_suffix=None
        )
        ids.append(source.entry_id)
        paths.append(source_path)
    if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
        raise EncryptedBackupError("backup_source_duplicate")
    return sources


def _bind_source(
    root: Path, source: BackupSourceFile, chunk_size: int
) -> _BoundSource:
    _validated_direct_child(root, source.path, required_suffix=None)
    return _bind_source_path(source, chunk_size)


def _bind_source_path(
    source: BackupSourceFile, chunk_size: int
) -> _BoundSource:
    path = Path(source.path)
    fd, status = _open_bound_regular(path)
    try:
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        if size != status.st_size:
            raise EncryptedBackupError("backup_source_changed")
        final = os.fstat(fd)
        if _file_identity(final) != _file_identity(status):
            raise EncryptedBackupError("backup_source_changed")
        os.lseek(fd, 0, os.SEEK_SET)
        return _BoundSource(
            source=source,
            fd=fd,
            device=status.st_dev,
            inode=status.st_ino,
            size=size,
            mtime_ns=status.st_mtime_ns,
            sha256=digest.hexdigest(),
        )
    except Exception:
        os.close(fd)
        raise


def _build_manifest(
    *,
    context: BackupContainerContextV1,
    container_id: str,
    created_at: str,
    chunk_size: int,
    bound: tuple[_BoundSource, ...],
) -> EncryptedBackupManifestV1:
    entries: list[BackupManifestEntryV1] = []
    for item in bound:
        restore_name = (
            "database.sqlcipher"
            if item.source.role is BackupEntryRole.SQLCIPHER_DATABASE
            else f"document-{item.source.entry_id}.bin"
        )
        entries.append(
            BackupManifestEntryV1(
                entry_id=item.source.entry_id,
                role=item.source.role,
                restore_name=restore_name,
                plaintext_size=item.size,
                sha256=item.sha256,
                chunk_count=max(1, (item.size + chunk_size - 1) // chunk_size),
            )
        )
    manifest = EncryptedBackupManifestV1(
        container_id=container_id,
        created_at=created_at,
        context=context,
        entries=tuple(entries),
        total_plaintext_size=sum(item.size for item in bound),
        chunk_size=chunk_size,
    )
    manifest.to_bytes()
    return manifest


def _open_bound_regular(path: Path) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        raise EncryptedBackupError("backup_regular_file_required") from None
    try:
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise EncryptedBackupError("backup_regular_file_required")
        path_status = os.stat(path, follow_symlinks=False)
        if _file_identity(status)[:2] != _file_identity(path_status)[:2]:
            raise EncryptedBackupError("backup_file_identity_mismatch")
        return fd, status
    except Exception:
        os.close(fd)
        raise


def _require_bound_source_unchanged(source: _BoundSource) -> None:
    status = os.fstat(source.fd)
    try:
        path_status = os.stat(source.source.path, follow_symlinks=False)
    except OSError:
        raise EncryptedBackupError("backup_source_changed") from None
    if (
        status.st_dev != source.device
        or status.st_ino != source.inode
        or status.st_size != source.size
        or status.st_mtime_ns != source.mtime_ns
        or not stat.S_ISREG(path_status.st_mode)
        or path_status.st_dev != source.device
        or path_status.st_ino != source.inode
        or path_status.st_size != source.size
        or path_status.st_mtime_ns != source.mtime_ns
    ):
        raise EncryptedBackupError("backup_source_changed")


def _file_identity(status: os.stat_result) -> tuple[int, int, int, int]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
    )


def _read_source_exact(fd: int, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        try:
            chunk = os.read(fd, remaining)
        except OSError:
            raise EncryptedBackupError("backup_source_read_failed") from None
        if not chunk:
            raise EncryptedBackupError("backup_source_changed")
        chunks.append(chunk)
        remaining -= len(chunk)
    if size == 0:
        return b""
    return b"".join(chunks)


def _write_frame(fd: int, ciphertext: bytes, code: str) -> None:
    if len(ciphertext) > 0xFFFFFFFF:
        raise EncryptedBackupError("backup_record_size_invalid")
    _write_all(fd, _UINT32.pack(len(ciphertext)), code)
    _write_all(fd, ciphertext, code)


def _read_frame(
    reader: _FDReader, *, minimum: int, maximum: int
) -> bytes:
    length = _UINT32.unpack(
        reader.read_exact(_UINT32.size, "backup_container_truncated")
    )[0]
    if length < minimum or length > maximum:
        raise EncryptedBackupError("backup_record_size_invalid")
    return reader.read_exact(length, "backup_container_truncated")


def _secretstream_push(state, plaintext: bytes, aad: bytes, tag: int) -> bytes:
    try:
        return nacl.bindings.crypto_secretstream_xchacha20poly1305_push(
            state, plaintext, ad=aad, tag=tag
        )
    except Exception:
        raise EncryptedBackupError("backup_stream_encrypt_failed") from None


def _secretstream_pull(state, ciphertext: bytes, aad: bytes) -> tuple[bytes, int]:
    try:
        return nacl.bindings.crypto_secretstream_xchacha20poly1305_pull(
            state, ciphertext, ad=aad
        )
    except CryptoError:
        raise EncryptedBackupError("backup_stream_authentication_failed") from None
    except Exception:
        raise EncryptedBackupError("backup_stream_decrypt_failed") from None


def _write_all(fd: int, value: bytes, code: str) -> None:
    view = memoryview(value)
    written = 0
    while written < len(view):
        try:
            count = os.write(fd, view[written:])
        except OSError:
            raise EncryptedBackupError(code) from None
        if count <= 0:
            raise EncryptedBackupError(code)
        written += count


def _fsync_fd(fd: int, code: str) -> None:
    try:
        os.fsync(fd)
    except OSError:
        raise EncryptedBackupError(code) from None


def _fsync_directory(path: Path, code: str) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise EncryptedBackupError(code) from None
    try:
        _fsync_fd(fd, code)
    finally:
        os.close(fd)


def _require_absent(path: Path, code: str) -> None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    except OSError:
        raise EncryptedBackupError(code) from None
    raise EncryptedBackupError(code)


def _erase(value: bytearray) -> None:
    for index in range(len(value)):
        value[index] = 0


def _validate_database_key(value: bytes) -> None:
    if not isinstance(value, bytes) or len(value) != 32:
        raise EncryptedBackupError("backup_database_key_invalid")


def _bind_expected_sources(
    root: Path,
    manifest: EncryptedBackupManifestV1,
    sources: Mapping[str, Path],
) -> dict[str, _BoundSource]:
    if not isinstance(sources, Mapping) or set(sources) != {
        entry.entry_id for entry in manifest.entries
    }:
        raise EncryptedBackupError("backup_restore_sources_invalid")
    bound: dict[str, _BoundSource] = {}
    try:
        for entry in manifest.entries:
            source = BackupSourceFile(
                Path(sources[entry.entry_id]),
                entry.entry_id,
                entry.role,
            )
            bound[entry.entry_id] = _bind_source(
                root, source, manifest.chunk_size
            )
        return bound
    except Exception:
        for item in bound.values():
            os.close(item.fd)
        raise


def _bound_files_equal(
    first: _BoundSource, second: _BoundSource, chunk_size: int
) -> bool:
    if first.size != second.size or first.sha256 != second.sha256:
        return False
    os.lseek(first.fd, 0, os.SEEK_SET)
    os.lseek(second.fd, 0, os.SEEK_SET)
    while True:
        left = os.read(first.fd, chunk_size)
        right = os.read(second.fd, chunk_size)
        if left != right:
            return False
        if not left:
            _require_bound_source_unchanged(first)
            _require_bound_source_unchanged(second)
            return True


def _require_directory_identity(
    path: Path, identity: tuple[int, int]
) -> None:
    try:
        status = os.stat(path, follow_symlinks=False)
    except OSError:
        raise EncryptedBackupError("backup_restore_root_changed") from None
    if (
        not stat.S_ISDIR(status.st_mode)
        or (status.st_dev, status.st_ino) != identity
    ):
        raise EncryptedBackupError("backup_restore_root_changed")


def _open_exclusive_at(root_fd: int, name: str) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, 0o600, dir_fd=root_fd)
    except OSError:
        raise EncryptedBackupError(
            "backup_restore_completion_create_failed"
        ) from None
