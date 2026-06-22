"""Import guard tests for indexing package boundaries."""

from pathlib import Path


def test_indexing_modules_do_not_import_qdrant_client() -> None:
    indexing_dir = Path("src/knowledge_assistant/indexing")
    forbidden = "qdrant_client"

    for path in indexing_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import qdrant_client"


def test_indexing_modules_do_not_reference_storage_settings() -> None:
    indexing_dir = Path("src/knowledge_assistant/indexing")
    forbidden_patterns = ("StorageSettings", "storage.config")

    for path in indexing_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference storage configuration"
            )


def test_indexing_modules_do_not_import_model_runtimes() -> None:
    indexing_dir = Path("src/knowledge_assistant/indexing")
    forbidden_patterns = ("torch", "FlagEmbedding", "transformers")

    for path in indexing_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not import model runtime {pattern!r}"
            )


def test_indexing_modules_do_not_import_retrieval() -> None:
    indexing_dir = Path("src/knowledge_assistant/indexing")
    forbidden = "knowledge_assistant.retrieval"

    for path in indexing_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import retrieval"


def test_llamaindex_imports_are_confined_to_adapter() -> None:
    indexing_dir = Path("src/knowledge_assistant/indexing")
    adapter_name = "llamaindex_adapter.py"

    for path in indexing_dir.glob("*.py"):
        if path.name == adapter_name:
            continue
        content = path.read_text(encoding="utf-8")
        assert "llama_index" not in content, (
            f"{path.name} must not import LlamaIndex directly"
        )

    adapter_content = (indexing_dir / adapter_name).read_text(encoding="utf-8")
    assert "llama_index" in adapter_content
