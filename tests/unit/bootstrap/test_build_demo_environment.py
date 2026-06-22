"""Unit tests for demo environment assembly."""

import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.retrieval import BgeReranker, RerankRetriever, StubReranker
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store


def test_build_demo_environment_returns_wired_stack() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    assert isinstance(environment, DemoEnvironment)
    assert environment.vector_store is store
    assert environment.indexing_pipeline is not None
    assert isinstance(environment.retriever, RerankRetriever)


def test_build_demo_environment_defaults_to_stub_reranker() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    assert settings.reranker_mode == "stub"
    assert isinstance(environment.retriever._reranker, StubReranker)  # pyright: ignore[reportPrivateUsage]
    assert environment.pipeline_label.endswith("rerank (stub embeddings)")


def test_build_demo_environment_real_mode_selects_bge_without_loading_model() -> None:
    settings = BootstrapSettings(
        corpus_root=Path("knowledge"),
        storage_settings=StorageSettings(
            collection_name=f"bootstrap-unit-{uuid.uuid4()}",
            dense_vector_size=8,
        ),
        reranker_mode="real",
    )
    store = create_qdrant_vector_store(
        settings.storage_settings,
        client=QdrantClient(":memory:"),
    )

    environment = build_demo_environment(settings=settings, vector_store=store)

    assert isinstance(environment.retriever._reranker, BgeReranker)  # pyright: ignore[reportPrivateUsage]
    assert environment.retriever._reranker._backend is None  # pyright: ignore[reportPrivateUsage]
    assert "BAAI/bge-reranker-v2-m3" in environment.pipeline_label


def test_bootstrap_settings_from_env_reads_real_reranker_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RAG_CORPUS_ROOT", str(tmp_path))
    monkeypatch.setenv("RAG_RERANKER_MODE", "real")
    monkeypatch.setenv("RAG_RERANKER_MODEL", "custom/reranker")
    monkeypatch.setenv("RAG_RERANKER_BATCH_SIZE", "3")

    settings = BootstrapSettings.from_env(
        collection_name=f"bootstrap-unit-{uuid.uuid4()}",
        dense_vector_size=8,
    )

    assert settings.reranker_mode == "real"
    assert settings.bge_reranker_settings.model_name == "custom/reranker"
    assert settings.bge_reranker_settings.batch_size == 3


def test_bootstrap_settings_from_env_rejects_invalid_reranker_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_RERANKER_MODE", "auto")

    with pytest.raises(ValueError, match="reranker mode must be"):
        BootstrapSettings.from_env()
