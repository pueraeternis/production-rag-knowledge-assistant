"""Shared fixtures for chat integration tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_chat_session
from knowledge_assistant.bootstrap.chat import ChatSession
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.llm.config import LlmSettings
from knowledge_assistant.llm.messages import GenerationResult
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store

_DEMO_VECTOR_SIZE = 8


@pytest.fixture
def fixture_corpus_root(tmp_path: Path) -> Path:
    corpus = tmp_path / "knowledge"
    corpus.mkdir()
    (corpus / "policy.md").write_text("# Policy\n\nRemote work is allowed.\n")
    (corpus / "README.md").write_text("# Corpus metadata\n")
    return corpus


@pytest.fixture
def demo_settings(fixture_corpus_root: Path) -> BootstrapSettings:
    return BootstrapSettings(
        corpus_root=fixture_corpus_root,
        storage_settings=StorageSettings(
            collection_name=f"chat-int-{uuid.uuid4()}",
            dense_vector_size=_DEMO_VECTOR_SIZE,
        ),
    )


@pytest.fixture
def demo_environment(demo_settings: BootstrapSettings) -> DemoEnvironment:
    store = create_qdrant_vector_store(
        demo_settings.storage_settings,
        client=QdrantClient(":memory:"),
    )
    from knowledge_assistant.bootstrap import build_demo_environment

    return build_demo_environment(settings=demo_settings, vector_store=store)


@pytest.fixture
def indexed_environment(demo_environment: DemoEnvironment) -> DemoEnvironment:
    demo_environment.indexing_pipeline.index_documents(
        (demo_environment.corpus_indexing_source(),),
        rebuild=False,
    )
    return demo_environment


@pytest.fixture
def streaming_chat_session(indexed_environment: DemoEnvironment) -> ChatSession:
    return build_chat_session(
        bootstrap_settings=indexed_environment.settings,
        vector_store=indexed_environment.vector_store,
        llm_settings=LlmSettings(
            base_url="http://localhost:8000/v1",
            api_key="test",
            default_model="test-model",
        ),
        llm_client=StreamingStubLLMClient(
            responses=(GenerationResult(content="unused"),),
            stream_deltas=("Hello from chat",),
        ),
    )
