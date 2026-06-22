"""Bootstrap configuration for demo environment assembly."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self, cast

from knowledge_assistant.embeddings import EmbeddingRuntimeSettings
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.retrieval import (
    BgeRerankerSettings,
    DenseRetrievalSettings,
    RerankerMode,
    parse_reranker_mode,
)
from knowledge_assistant.storage.collection import DEFAULT_COLLECTION_NAME
from knowledge_assistant.storage.config import StorageSettings

EmbeddingMode = Literal["stub", "real"]

STUB_PIPELINE_LABEL = "dense + sparse → fusion (RRF) → rerank (stub embeddings)"
REAL_PIPELINE_LABEL = (
    "dense (bge-m3) + sparse → fusion (RRF) → rerank (stub embeddings)"
)


def retrieval_pipeline_label(
    *,
    embedding_mode: EmbeddingMode,
    reranker_mode: RerankerMode = "stub",
    reranker_model_name: str = "",
) -> str:
    """Return the demo retrieval pipeline label for the configured provider modes."""
    if reranker_mode == "stub":
        if embedding_mode == "real":
            return REAL_PIPELINE_LABEL
        return STUB_PIPELINE_LABEL

    dense_part = "dense (bge-m3)" if embedding_mode == "real" else "dense"
    rerank_part = reranker_model_name or "bge-reranker"
    return f"{dense_part} + sparse → fusion (RRF) → rerank ({rerank_part})"


@dataclass(frozen=True, slots=True)
class BootstrapSettings:
    """Resolved paths and collection configuration for the demo stack."""

    corpus_root: Path
    storage_settings: StorageSettings
    reranker_mode: RerankerMode = "stub"
    bge_reranker_settings: BgeRerankerSettings = BgeRerankerSettings()
    embedding_mode: EmbeddingMode = "stub"
    embedding_runtime_settings: EmbeddingRuntimeSettings | None = None

    def __post_init__(self) -> None:
        parse_reranker_mode(self.reranker_mode)
        if self.embedding_mode == "real" and self.embedding_runtime_settings is None:
            msg = "embedding_runtime_settings is required when embedding_mode is 'real'"
            raise ValueError(msg)

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

    @property
    def pipeline_label(self) -> str:
        return retrieval_pipeline_label(
            embedding_mode=self.embedding_mode,
            reranker_mode=self.reranker_mode,
            reranker_model_name=self.bge_reranker_settings.model_name,
        )

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

        reranker_mode = parse_reranker_mode(
            str(
                overrides.pop(
                    "reranker_mode",
                    os.environ.get("RAG_RERANKER_MODE", "stub"),
                ),
            ),
        )
        bge_reranker_overrides: dict[str, object] = {}
        for key in ("model_name", "device", "batch_size", "max_length", "use_fp16"):
            if key in overrides:
                bge_reranker_overrides[key] = overrides.pop(key)
        bge_reranker_settings = BgeRerankerSettings.from_env(
            **bge_reranker_overrides,
        )

        embedding_mode_raw = str(
            overrides.pop(
                "embedding_mode",
                os.environ.get("RAG_EMBEDDING_MODE", "stub"),
            ),
        )
        if embedding_mode_raw not in ("stub", "real"):
            msg = (
                "RAG_EMBEDDING_MODE must be 'stub' or 'real'; "
                f"got {embedding_mode_raw!r}"
            )
            raise ValueError(msg)
        embedding_mode: EmbeddingMode = embedding_mode_raw  # type: ignore[assignment]

        embedding_runtime_settings: EmbeddingRuntimeSettings | None = None
        if "embedding_runtime_settings" in overrides:
            embedding_runtime_settings = cast(
                "EmbeddingRuntimeSettings",
                overrides.pop("embedding_runtime_settings"),
            )
        elif embedding_mode == "real":
            embedding_runtime_settings = EmbeddingRuntimeSettings.from_env(
                dense_vector_size=storage_settings.dense_vector_size,
            )

        if overrides:
            unexpected = ", ".join(sorted(overrides))
            msg = f"unexpected bootstrap settings overrides: {unexpected}"
            raise TypeError(msg)

        return cls(
            corpus_root=corpus_root,
            storage_settings=storage_settings,
            reranker_mode=reranker_mode,
            bge_reranker_settings=bge_reranker_settings,
            embedding_mode=embedding_mode,
            embedding_runtime_settings=embedding_runtime_settings,
        )

    @property
    def collection_name(self) -> str:
        return self.storage_settings.collection_name or DEFAULT_COLLECTION_NAME

    @property
    def qdrant_url(self) -> str:
        return self.storage_settings.qdrant_url
