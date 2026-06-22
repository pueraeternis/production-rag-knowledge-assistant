"""Import guard tests for evaluation package embedding isolation."""

from pathlib import Path

from import_ast import collect_import_modules, module_matches_prefix


def test_evaluation_package_does_not_import_embeddings() -> None:
    evaluation_dir = Path("src/knowledge_assistant/evaluation")
    forbidden = "knowledge_assistant.embeddings"

    for path in evaluation_dir.glob("*.py"):
        modules = collect_import_modules(path)
        matches = {
            module for module in modules if module_matches_prefix(module, forbidden)
        }
        assert not matches, (
            f"{path.name} must not import embeddings; found {sorted(matches)}"
        )
