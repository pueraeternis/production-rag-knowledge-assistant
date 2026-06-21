"""Import guard tests for agent package boundaries."""

from pathlib import Path


def test_agent_core_modules_do_not_import_forbidden_dependencies() -> None:
    agent_dir = Path("src/knowledge_assistant/agent")
    forbidden_patterns = (
        "knowledge_assistant.storage",
        "knowledge_assistant.retrieval",
        "knowledge_assistant.indexing",
        "qdrant_client",
        "llama_index",
        "from openai",
        "import openai",
        "import httpx",
        "from httpx",
        "from langchain",
        "import langchain",
        "from mcp",
        "import mcp",
        "sentence_transformers",
        "transformers",
        "torch",
    )

    for path in agent_dir.glob("*.py"):
        if path.name == "wiring.py":
            continue
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference forbidden dependency {pattern!r}"
            )


def test_openai_client_is_not_imported_in_agent_core() -> None:
    agent_dir = Path("src/knowledge_assistant/agent")

    for path in agent_dir.glob("*.py"):
        if path.name == "wiring.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert "openai_client" not in content
        assert "OpenAICompatibleLLMClient" not in content
