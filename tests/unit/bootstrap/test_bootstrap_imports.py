"""Import guard tests for bootstrap package boundaries."""

from pathlib import Path

from import_ast import collect_import_modules, module_matches_prefix

BOOTSTRAP_DIR = Path("src/knowledge_assistant/bootstrap")
FORBIDDEN_PREFIXES = (
    "knowledge_assistant.cli",
    "knowledge_assistant.agent",
    "knowledge_assistant.mcp_server",
    "knowledge_assistant.llm",
    "knowledge_assistant.evaluation",
    "qdrant_client",
    "langgraph",
    "mcp",
    "openai",
)
AUTHORIZED_PREFIXES = (
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.core",
    "knowledge_assistant.storage",
    "knowledge_assistant.indexing",
    "knowledge_assistant.retrieval",
)
UNAUTHORIZED_RETRIEVAL_PREFIXES = (
    "knowledge_assistant.retrieval.protocol",
    "knowledge_assistant.retrieval.fusion.reciprocal_rank_fusion",
    "knowledge_assistant.retrieval.dense",
    "knowledge_assistant.retrieval.sparse",
    "knowledge_assistant.retrieval.fusion",
    "knowledge_assistant.retrieval.rerank",
    "knowledge_assistant.retrieval.embeddings",
    "knowledge_assistant.retrieval.config",
)


def test_bootstrap_modules_do_not_import_forbidden_packages() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        modules = collect_import_modules(path)
        for prefix in FORBIDDEN_PREFIXES:
            forbidden = {
                module for module in modules if module_matches_prefix(module, prefix)
            }
            assert not forbidden, (
                f"{path.name} must not import forbidden module {prefix!r}; "
                f"found {sorted(forbidden)}"
            )


def test_bootstrap_modules_import_only_authorized_packages() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        modules = collect_import_modules(path)
        knowledge_assistant_modules = {
            module
            for module in modules
            if module_matches_prefix(module, "knowledge_assistant")
        }
        unauthorized = {
            module
            for module in knowledge_assistant_modules
            if not any(
                module_matches_prefix(module, prefix) for prefix in AUTHORIZED_PREFIXES
            )
        }
        assert not unauthorized, (
            f"{path.name} has unauthorized knowledge_assistant imports: "
            f"{sorted(unauthorized)}"
        )


def test_bootstrap_modules_use_retrieval_public_api() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        modules = collect_import_modules(path)
        retrieval_modules = {
            module
            for module in modules
            if module_matches_prefix(module, "knowledge_assistant.retrieval")
        }
        internal_retrieval = {
            module
            for module in retrieval_modules
            if any(
                module_matches_prefix(module, prefix)
                for prefix in UNAUTHORIZED_RETRIEVAL_PREFIXES
            )
        }
        assert not internal_retrieval, (
            f"{path.name} must import retrieval symbols from the public package API; "
            f"found internal imports {sorted(internal_retrieval)}"
        )
