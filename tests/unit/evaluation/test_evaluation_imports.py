"""Import guard tests for evaluation package boundaries."""

from pathlib import Path


def test_evaluation_modules_do_not_import_forbidden_packages() -> None:
    evaluation_dir = Path("src/knowledge_assistant/evaluation")
    forbidden_patterns = (
        "knowledge_assistant.storage",
        "qdrant_client",
        "knowledge_assistant.indexing",
        "knowledge_assistant.mcp_server",
        "knowledge_assistant.llm",
        "knowledge_assistant.agent",
        "langgraph",
        "llama_index",
        "llama-index",
        "knowledge_assistant.retrieval.dense",
        "knowledge_assistant.retrieval.sparse",
        "knowledge_assistant.retrieval.fusion",
        "knowledge_assistant.retrieval.rerank",
    )

    for path in evaluation_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"{path.name} must not import or reference {pattern}"
            )


def test_evaluation_modules_only_import_retriever_from_protocol() -> None:
    runner_path = Path("src/knowledge_assistant/evaluation/runner.py")
    content = runner_path.read_text(encoding="utf-8")

    assert "knowledge_assistant.retrieval.protocol" in content
    assert "knowledge_assistant.retrieval.dense" not in content
    assert "from knowledge_assistant.retrieval import" not in content


def test_retrieval_modules_do_not_import_evaluation() -> None:
    retrieval_dir = Path("src/knowledge_assistant/retrieval")
    forbidden = "knowledge_assistant.evaluation"

    for path in retrieval_dir.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert forbidden not in content, f"{path.name} must not import evaluation"
