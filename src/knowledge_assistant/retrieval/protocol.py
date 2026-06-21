"""Retrieval composition protocols."""

from typing import Protocol

from knowledge_assistant.core.retrieval import RetrievalResult, SearchQuery


class Retriever(Protocol):
    """Minimal leaf-retriever contract for retrieval orchestration."""

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Run one retrieval strategy for a search query."""
        ...
