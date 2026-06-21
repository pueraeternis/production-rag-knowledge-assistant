"""Knowledge MCP handler layer."""

from knowledge_assistant.mcp_server.config import McpServerSettings
from knowledge_assistant.mcp_server.exceptions import (
    APPROVAL_REQUIRED,
    ApprovalRequiredError,
)
from knowledge_assistant.mcp_server.tools import (
    index_documents_apply,
    index_documents_preview,
    search_documents,
)

__all__ = [
    "APPROVAL_REQUIRED",
    "ApprovalRequiredError",
    "McpServerSettings",
    "index_documents_apply",
    "index_documents_preview",
    "search_documents",
]
