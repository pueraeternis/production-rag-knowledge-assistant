"""Shared fixtures for agent integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.prompts import SYSTEM_PROMPT
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.agent.wiring import build_default_tool_registry
from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.identifiers import ChunkId, DocumentId
from knowledge_assistant.core.indexing import (
    IndexingPreview,
    IndexingSource,
    IndexingSourceKind,
)
from knowledge_assistant.core.retrieval import (
    RetrievalResult,
    SearchQuery,
    SearchResult,
)
from knowledge_assistant.core.source import LineRange, SourceReference
from knowledge_assistant.indexing.pipeline import IndexingResult
from knowledge_assistant.llm.messages import ChatMessage, ChatRole


@pytest.fixture
def fake_retriever() -> MagicMock:
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        query=SearchQuery(text="remote work policy", top_k=3),
        results=(
            SearchResult(
                chunk=Chunk(
                    chunk_id=ChunkId("chunk-1"),
                    metadata=ChunkMetadata(
                        document_id=DocumentId("doc-1"),
                        section_title="Policy",
                        line_range=LineRange(start_line=10, end_line=20),
                        chunk_index=0,
                    ),
                    text="Employees may work remotely two days per week.",
                ),
                score=0.95,
                source=SourceReference(
                    document_title="Employee Handbook",
                    document_path="docs/handbook.md",
                    section_title="Remote Work",
                    line_range=LineRange(start_line=10, end_line=20),
                ),
            ),
        ),
    )
    return retriever


@pytest.fixture
def fake_indexing_pipeline() -> MagicMock:
    pipeline = MagicMock()
    source = IndexingSource(
        kind=IndexingSourceKind.FILE,
        location="docs/handbook.md",
        recursive=False,
    )
    pipeline.preview_indexing.return_value = IndexingPreview(
        sources=(source,),
        document_count=1,
        chunk_count=4,
        replaces_existing=False,
    )
    pipeline.index_documents.return_value = IndexingResult(
        sources=(source,),
        document_count=1,
        chunk_count=4,
        upserted_count=4,
        rebuilt=False,
    )
    return pipeline


@pytest.fixture
def tool_registry(fake_retriever: MagicMock, fake_indexing_pipeline: MagicMock):
    return build_default_tool_registry(
        retriever=fake_retriever,
        pipeline=fake_indexing_pipeline,
    )


@pytest.fixture
def initial_state() -> AgentState:
    return AgentState(
        messages=(ChatMessage(role=ChatRole.SYSTEM, content=SYSTEM_PROMPT),),
    )


@pytest.fixture
def agent_settings() -> AgentSettings:
    return AgentSettings(max_tool_iterations=5)
