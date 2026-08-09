"""Shared port for encrypted managed-document storage."""

from __future__ import annotations

from typing import Callable, Protocol, TypeVar


ArtifactT = TypeVar("ArtifactT")


class ManagedPdfArtifactError(RuntimeError):
    """Sanitized fail-closed error for the encrypted PDF lifecycle."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ManagedDocumentStore(Protocol):
    """Qt-free lifecycle boundary implemented by the encrypted runtime."""

    def plan_prepare(self, *, document_id: str) -> object: ...

    def prepare(self, **kwargs: object) -> object: ...

    def prepare_bytes(self, **kwargs: object) -> object: ...

    def verify_prepared(self, *, plan: object) -> object: ...

    def activate(
        self, *, document_id: str, document_generation: int | None = None
    ) -> object: ...

    def deactivate(self, *, document_id: str) -> object: ...

    def apply_journaled_changes(
        self,
        *,
        prepared_plans: tuple[object, ...],
        deactivated_document_ids: tuple[str, ...],
    ) -> tuple[object, ...]: ...

    def read(
        self,
        *,
        document_id: str,
        consumer: object,
        document_generation: int | None = None,
    ) -> object: ...


class ManagedPdfArtifactLifecyclePort(Protocol[ArtifactT]):
    """Core-facing port for journaled encrypted final-PDF persistence."""

    def generate(
        self,
        *,
        revision_id: str,
        snapshot_sha256: str,
        created_at: str,
        render_pdf: Callable[[], bytes],
    ) -> ArtifactT: ...

    def verify_existing(self, artifact: ArtifactT) -> bytes: ...
