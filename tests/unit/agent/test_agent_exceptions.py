"""Unit tests for agent exceptions."""

from knowledge_assistant.agent.exceptions import (
    DuplicateToolError,
    MaxToolIterationsError,
    UnknownToolError,
)


class TestAgentExceptions:
    def test_unknown_tool_error_exposes_name(self) -> None:
        error = UnknownToolError("missing_tool")
        assert error.tool_name == "missing_tool"
        assert "missing_tool" in str(error)

    def test_duplicate_tool_error_exposes_name(self) -> None:
        error = DuplicateToolError("search_documents")
        assert error.tool_name == "search_documents"

    def test_max_tool_iterations_error_exposes_limit(self) -> None:
        error = MaxToolIterationsError(3)
        assert error.max_iterations == 3
        assert "3" in str(error)
