"""Shared port for encrypted managed-document storage."""

from __future__ import annotations

from typing import Protocol


class ManagedDocumentStore(Protocol):
    """Qt-free lifecycle boundary implemented by the encrypted runtime."""

    def plan_prepare(self, *, document_id: str) -> object: ...

    def prepare(self, **kwargs: object) -> object: ...

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
