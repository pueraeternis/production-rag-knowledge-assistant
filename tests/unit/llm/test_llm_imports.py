"""Import guard tests for LLM package boundaries."""

from pathlib import Path


def test_llm_modules_do_not_import_forbidden_dependencies() -> None:
    llm_dir = Path("src/knowledge_assistant/llm")
    forbidden_patterns = (
        "knowledge_assistant.storage",
        "knowledge_assistant.indexing",
        "knowledge_assistant.retrieval",
        "knowledge_assistant.mcp_server",
        "knowledge_assistant.agent",
        "qdrant_client",
        "llama_index",
        "langgraph",
        "from mcp",
        "import mcp",
        "sentence_transformers",
        "transformers",
        "torch",
        "pydantic",
    )

    for path in llm_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference forbidden dependency {pattern!r}"
            )


def test_httpx_import_is_confined_to_openai_client_module() -> None:
    llm_dir = Path("src/knowledge_assistant/llm")

    for path in llm_dir.glob("*.py"):
        if path.name == "openai_client.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert "import httpx" not in content, (
            f"{path.name} must not import httpx outside openai_client.py"
        )
        assert "from httpx" not in content, (
            f"{path.name} must not import httpx outside openai_client.py"
        )


def test_llm_modules_only_import_internal_knowledge_assistant_packages() -> None:
    llm_dir = Path("src/knowledge_assistant/llm")

    for path in llm_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(
                ("from knowledge_assistant", "import knowledge_assistant")
            ):
                continue
            assert "knowledge_assistant.llm" in stripped, (
                f"{path.name} has unauthorized import line: {stripped}"
            )
