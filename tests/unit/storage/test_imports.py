"""Import guard tests for storage package boundaries."""

from pathlib import Path


def test_qdrant_client_import_is_confined_to_qdrant_store_module() -> None:
    storage_dir = Path("src/knowledge_assistant/storage")

    for path in storage_dir.glob("*.py"):
        if path.name == "qdrant_store.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert "qdrant_client" not in content, (
            f"{path.name} must not import qdrant_client outside qdrant_store.py"
        )


def test_storage_modules_do_not_import_forbidden_dependencies() -> None:
    storage_dir = Path("src/knowledge_assistant/storage")
    forbidden_patterns = (
        "knowledge_assistant.indexing",
        "knowledge_assistant.retrieval",
        "knowledge_assistant.mcp_server",
        "knowledge_assistant.llm",
        "knowledge_assistant.agent",
        "knowledge_assistant.cli",
        "llama_index",
        "llama-index",
        "langgraph",
        "from mcp",
        "import mcp",
        "openai",
        "httpx",
    )

    for path in storage_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference forbidden dependency {pattern!r}"
            )


def test_storage_modules_only_import_core_and_internal_storage_packages() -> None:
    storage_dir = Path("src/knowledge_assistant/storage")
    allowed_patterns = (
        "knowledge_assistant.core",
        "knowledge_assistant.storage",
    )

    for path in storage_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(
                ("from knowledge_assistant", "import knowledge_assistant"),
            ):
                continue
            assert any(pattern in stripped for pattern in allowed_patterns), (
                f"{path.name} has unauthorized import line: {stripped}"
            )
