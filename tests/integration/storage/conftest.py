"""Integration test fixtures for storage layer."""

import uuid

import pytest
from qdrant_client import QdrantClient

from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import QdrantVectorStore


@pytest.fixture
def qdrant_client() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture
def vector_store(qdrant_client: QdrantClient) -> QdrantVectorStore:
    settings = StorageSettings(
        collection_name=f"integration-{uuid.uuid4()}",
        dense_vector_size=4,
    )
    return QdrantVectorStore(client=qdrant_client, settings=settings)
