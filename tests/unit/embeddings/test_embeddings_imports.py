"""Import guard tests for embeddings package boundaries."""

from pathlib import Path

from import_ast import collect_import_modules, module_matches_prefix

EMBEDDINGS_DIR = Path("src/knowledge_assistant/embeddings")
FORBIDDEN_PREFIXES = (
    "knowledge_assistant.indexing",
    "knowledge_assistant.retrieval",
    "knowledge_assistant.storage",
    "knowledge_assistant.mcp_server",
    "knowledge_assistant.agent",
    "knowledge_assistant.llm",
    "knowledge_assistant.evaluation",
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.cli",
)


def test_embeddings_modules_do_not_import_forbidden_packages() -> None:
    for path in EMBEDDINGS_DIR.glob("*.py"):
        modules = collect_import_modules(path)
        for prefix in FORBIDDEN_PREFIXES:
            forbidden = {
                module for module in modules if module_matches_prefix(module, prefix)
            }
            assert not forbidden, (
                f"{path.name} must not import forbidden module {prefix!r}; "
                f"found {sorted(forbidden)}"
            )
