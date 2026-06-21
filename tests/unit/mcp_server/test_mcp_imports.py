"""Import guard tests for MCP package boundaries."""

from pathlib import Path


def test_mcp_modules_do_not_import_forbidden_dependencies() -> None:
    mcp_dir = Path("src/knowledge_assistant/mcp_server")
    forbidden_patterns = (
        "knowledge_assistant.storage",
        "qdrant_client",
        "from mcp",
        "import mcp",
        "langgraph",
        "openai",
        "llama_index",
        "knowledge_assistant.agent",
        "knowledge_assistant.llm",
        "knowledge_assistant.retrieval.dense",
        "knowledge_assistant.retrieval.sparse",
        "knowledge_assistant.retrieval.fusion",
        "knowledge_assistant.retrieval.rerank",
        "knowledge_assistant.retrieval.embeddings",
    )

    for path in mcp_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference forbidden dependency {pattern!r}"
            )


def test_pydantic_imports_are_confined_to_schemas_module() -> None:
    mcp_dir = Path("src/knowledge_assistant/mcp_server")

    for path in mcp_dir.glob("*.py"):
        if path.name == "schemas.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert "from pydantic" not in content, (
            f"{path.name} must not import pydantic outside schemas.py"
        )
        assert "import pydantic" not in content, (
            f"{path.name} must not import pydantic outside schemas.py"
        )


def test_mcp_allows_only_authorized_dependencies() -> None:
    allowed_patterns = (
        "knowledge_assistant.core",
        "knowledge_assistant.retrieval.protocol",
        "knowledge_assistant.indexing.pipeline",
        "knowledge_assistant.mcp_server",
    )
    mcp_dir = Path("src/knowledge_assistant/mcp_server")

    for path in mcp_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(
                ("from knowledge_assistant", "import knowledge_assistant")
            ):
                continue
            assert any(pattern in stripped for pattern in allowed_patterns), (
                f"{path.name} has unauthorized import line: {stripped}"
            )
