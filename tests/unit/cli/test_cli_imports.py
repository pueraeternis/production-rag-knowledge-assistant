"""Import guard tests for CLI package boundaries."""

from pathlib import Path

from import_ast import collect_import_modules, module_matches_prefix

CLI_DIR = Path("src/knowledge_assistant/cli")
FORBIDDEN_PREFIXES = (
    "qdrant_client",
    "knowledge_assistant.storage",
    "knowledge_assistant.indexing",
    "knowledge_assistant.retrieval",
    "knowledge_assistant.agent",
    "knowledge_assistant.mcp_server",
    "knowledge_assistant.llm",
    "knowledge_assistant.evaluation",
)
ALLOWED_PREFIXES = (
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.cli",
)


def test_cli_production_modules_respect_import_boundaries() -> None:
    for path in CLI_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue

        modules = collect_import_modules(path)
        knowledge_assistant_modules = {
            module
            for module in modules
            if module_matches_prefix(module, "knowledge_assistant")
        }

        for prefix in FORBIDDEN_PREFIXES:
            forbidden = {
                module for module in modules if module_matches_prefix(module, prefix)
            }
            assert not forbidden, (
                f"{path.name} must not import forbidden module {prefix!r}; "
                f"found {sorted(forbidden)}"
            )

        if path.name == "demo.py":
            assert any(
                module_matches_prefix(module, "knowledge_assistant.bootstrap")
                for module in knowledge_assistant_modules
            ), f"{path.name} must import knowledge_assistant.bootstrap"
            assert not any(
                module_matches_prefix(module, "knowledge_assistant.cli")
                for module in knowledge_assistant_modules
            ), f"{path.name} must not import knowledge_assistant.cli"

        if path.name == "main.py":
            assert any(
                module_matches_prefix(module, "knowledge_assistant.cli")
                for module in knowledge_assistant_modules
            ), f"{path.name} must import knowledge_assistant.cli"
            assert not any(
                module_matches_prefix(module, "knowledge_assistant.bootstrap")
                for module in knowledge_assistant_modules
            ), f"{path.name} must not import knowledge_assistant.bootstrap"

        unexpected = {
            module
            for module in knowledge_assistant_modules
            if not any(
                module_matches_prefix(module, prefix) for prefix in ALLOWED_PREFIXES
            )
        }
        assert not unexpected, (
            f"{path.name} has unauthorized knowledge_assistant imports: "
            f"{sorted(unexpected)}"
        )
