"""Unit tests for RAG prompt templates."""

from knowledge_assistant.agent.prompts import SYSTEM_PROMPT


class TestPrompts:
    def test_system_prompt_requires_grounding_and_citations(self) -> None:
        assert "search_documents" in SYSTEM_PROMPT
        assert "Do NOT use search_documents for general knowledge" in SYSTEM_PROMPT
        assert "document_title" in SYSTEM_PROMPT
        assert "document_path" in SYSTEM_PROMPT
        assert "section_title" in SYSTEM_PROMPT
        assert "line_range" in SYSTEM_PROMPT
        assert "Ground corpus-related answers only in retrieved tool results" in (
            SYSTEM_PROMPT
        )

    def test_system_prompt_documents_indexing_approval(self) -> None:
        assert "index_documents_preview" in SYSTEM_PROMPT
        assert "index_documents_apply" in SYSTEM_PROMPT
        assert "approval_confirmed" in SYSTEM_PROMPT
