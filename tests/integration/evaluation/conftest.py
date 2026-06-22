"""Integration fixtures for evaluation CLI workflow tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store

_DEMO_VECTOR_SIZE = 8


@pytest.fixture
def fixture_corpus_root(tmp_path: Path) -> Path:
    corpus = tmp_path / "knowledge"
    corpus.mkdir()
    (corpus / "doc-a.md").write_text("# Policy A\n\nRemote work policy details.\n")
    (corpus / "doc-b.md").write_text("# Policy B\n\nTravel expense guidelines.\n")
    (corpus / "README.md").write_text("# Corpus metadata\n")
    return corpus


@pytest.fixture
def demo_settings(fixture_corpus_root: Path) -> BootstrapSettings:
    return BootstrapSettings(
        corpus_root=fixture_corpus_root,
        storage_settings=StorageSettings(
            collection_name=f"eval-cli-{uuid.uuid4()}",
            dense_vector_size=_DEMO_VECTOR_SIZE,
        ),
    )


@pytest.fixture
def demo_environment(demo_settings: BootstrapSettings) -> DemoEnvironment:
    store = create_qdrant_vector_store(
        demo_settings.storage_settings,
        client=QdrantClient(":memory:"),
    )
    return build_demo_environment(settings=demo_settings, vector_store=store)
