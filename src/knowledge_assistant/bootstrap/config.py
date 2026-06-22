"""Bootstrap configuration for demo environment assembly."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.retrieval import DenseRetrievalSettings
from knowledge_assistant.storage.collection import DEFAULT_COLLECTION_NAME
from knowledge_assistant.storage.config import StorageSettings


@dataclass(frozen=True, slots=True)
class BootstrapSettings:
    """Resolved paths and collection configuration for the demo stack."""

    corpus_root: Path
    storage_settings: StorageSettings

    @property
    def dense_vector_size(self) -> int:
        """Vector dimension shared by indexing, retrieval, and storage."""
        return self.storage_settings.dense_vector_size

    @property
    def indexing_settings(self) -> IndexingSettings:
        return IndexingSettings(dense_vector_size=self.dense_vector_size)

    @property
    def dense_retrieval_settings(self) -> DenseRetrievalSettings:
        return DenseRetrievalSettings(dense_vector_size=self.dense_vector_size)

    @classmethod
    def from_env(cls, **overrides: object) -> Self:
        """Load bootstrap settings from environment variables and overrides."""
        corpus_root = Path(
            str(
                overrides.pop(
                    "corpus_root",
                    os.environ.get("RAG_CORPUS_ROOT", "knowledge"),
                ),
            ),
        )

        storage_overrides: dict[str, object] = {}
        for key in ("qdrant_url", "collection_name", "dense_vector_size"):
            if key in overrides:
                storage_overrides[key] = overrides.pop(key)

        storage_settings = StorageSettings.from_env(**storage_overrides)

        if overrides:
            unexpected = ", ".join(sorted(overrides))
            msg = f"unexpected bootstrap settings overrides: {unexpected}"
            raise TypeError(msg)

        return cls(
            corpus_root=corpus_root,
            storage_settings=storage_settings,
        )

    @property
    def collection_name(self) -> str:
        return self.storage_settings.collection_name or DEFAULT_COLLECTION_NAME

    @property
    def qdrant_url(self) -> str:
        return self.storage_settings.qdrant_url
