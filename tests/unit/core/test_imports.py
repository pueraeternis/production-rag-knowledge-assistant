"""Import guard tests for core package boundaries."""

from pathlib import Path


def test_core_modules_do_not_import_forbidden_dependencies() -> None:
    core_dir = Path("src/knowledge_assistant/core")
    forbidden_patterns = (
        "qdrant_client",
        "llama_index",
        "llama-index",
        "pydantic",
        "from mcp",
        "import mcp",
        "langgraph",
        "openai",
        "httpx",
        "knowledge_assistant.storage",
        "knowledge_assistant.indexing",
        "knowledge_assistant.retrieval",
        "knowledge_assistant.mcp_server",
        "knowledge_assistant.llm",
        "knowledge_assistant.agent",
        "knowledge_assistant.cli",
    )

    for path in core_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference forbidden dependency {pattern!r}"
            )


def test_core_modules_only_import_internal_knowledge_assistant_packages() -> None:
    core_dir = Path("src/knowledge_assistant/core")

    for path in core_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(
                ("from knowledge_assistant", "import knowledge_assistant"),
            ):
                continue
            assert "knowledge_assistant.core" in stripped, (
                f"{path.name} has unauthorized import line: {stripped}"
            )
