"""Import guard tests for retrieval package boundaries."""

from pathlib import Path


def test_retrieval_modules_do_not_import_qdrant_client() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden = "qdrant_client"

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import qdrant_client"


def test_retrieval_modules_do_not_reference_storage_settings() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden_patterns = ("StorageSettings", "storage.config")

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not reference storage configuration"
            )


def test_retrieval_modules_only_import_storage_protocol() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    allowed_storage_import = "knowledge_assistant.storage.protocol"

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        if "knowledge_assistant.storage" not in content:
            continue
        assert allowed_storage_import in content, (
            f"{path.name} must import only from knowledge_assistant.storage.protocol"
        )
        assert "knowledge_assistant.storage.models" not in content
        assert "knowledge_assistant.storage.qdrant_store" not in content
        assert "knowledge_assistant.storage.mapping" not in content


def test_retrieval_modules_do_not_import_indexing() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden = "knowledge_assistant.indexing"

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import indexing"


def test_retrieval_modules_do_not_import_llama_index() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden_patterns = ("llama_index", "llama-index")

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, f"{path.name} must not import LlamaIndex"


def test_retrieval_modules_do_not_import_agent_mcp_or_llm() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden_patterns = (
        "knowledge_assistant.agent",
        "knowledge_assistant.mcp_server",
        "knowledge_assistant.llm",
        "langgraph",
        "mcp",
        "openai",
    )

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, f"{path.name} must not import {pattern}"


def test_fusion_modules_do_not_import_storage() -> None:
    fusion_modules = (
        Path("src/knowledge_assistant/retrieval/fusion.py"),
        Path("src/knowledge_assistant/retrieval/protocol.py"),
        Path("src/knowledge_assistant/retrieval/rerank.py"),
    )
    forbidden = "knowledge_assistant.storage"

    for path in fusion_modules:
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import storage"


def test_retrieval_leaf_modules_do_not_import_model_runtimes() -> None:
    leaf_modules = (
        Path("src/knowledge_assistant/retrieval/embeddings.py"),
        Path("src/knowledge_assistant/retrieval/dense.py"),
        Path("src/knowledge_assistant/retrieval/sparse.py"),
    )
    forbidden_patterns = ("torch", "FlagEmbedding", "transformers")

    for path in leaf_modules:
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not import model runtime {pattern!r}"
            )


def test_rerank_modules_do_not_import_model_runtimes() -> None:
    rerank_path = Path("src/knowledge_assistant/retrieval/rerank.py")
    content = rerank_path.read_text(encoding="utf-8")
    forbidden_patterns = ("torch", "transformers", "sentence_transformers")

    for pattern in forbidden_patterns:
        assert pattern not in content, (
            f"rerank.py must not import model runtime {pattern}"
        )
