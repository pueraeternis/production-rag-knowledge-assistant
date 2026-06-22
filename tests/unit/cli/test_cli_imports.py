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
)
DEMO_FORBIDDEN_PREFIXES = (
    *FORBIDDEN_PREFIXES,
    "knowledge_assistant.evaluation",
)
EVALUATE_FORBIDDEN_PREFIXES = FORBIDDEN_PREFIXES
MAIN_FORBIDDEN_PREFIXES = (
    *FORBIDDEN_PREFIXES,
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.evaluation",
)
ALLOWED_PREFIXES = (
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.cli",
    "knowledge_assistant.evaluation",
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

        if path.name == "demo.py":
            forbidden_prefixes = DEMO_FORBIDDEN_PREFIXES
            allowed_prefixes = ("knowledge_assistant.bootstrap",)
        elif path.name == "evaluate.py":
            forbidden_prefixes = EVALUATE_FORBIDDEN_PREFIXES
            allowed_prefixes = (
                "knowledge_assistant.bootstrap",
                "knowledge_assistant.evaluation",
            )
        elif path.name == "main.py":
            forbidden_prefixes = MAIN_FORBIDDEN_PREFIXES
            allowed_prefixes = ("knowledge_assistant.cli",)
        else:
            forbidden_prefixes = DEMO_FORBIDDEN_PREFIXES
            allowed_prefixes = ALLOWED_PREFIXES

        for prefix in forbidden_prefixes:
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

        if path.name == "evaluate.py":
            assert any(
                module_matches_prefix(module, "knowledge_assistant.bootstrap")
                for module in knowledge_assistant_modules
            ), f"{path.name} must import knowledge_assistant.bootstrap"
            assert any(
                module_matches_prefix(module, "knowledge_assistant.evaluation")
                for module in knowledge_assistant_modules
            ), f"{path.name} must import knowledge_assistant.evaluation"

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
                module_matches_prefix(module, prefix) for prefix in allowed_prefixes
            )
        }
        assert not unexpected, (
            f"{path.name} has unauthorized knowledge_assistant imports: "
            f"{sorted(unexpected)}"
        )
