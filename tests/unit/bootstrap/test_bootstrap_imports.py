"""Import guard tests for bootstrap package boundaries."""

from pathlib import Path

from import_ast import collect_import_modules, module_matches_prefix

BOOTSTRAP_DIR = Path("src/knowledge_assistant/bootstrap")
GLOBAL_FORBIDDEN_PREFIXES = (
    "knowledge_assistant.cli",
    "knowledge_assistant.evaluation",
    "qdrant_client",
    "langgraph",
    "mcp",
    "openai",
)
CHAT_FORBIDDEN_PREFIXES = (
    "knowledge_assistant.cli",
    "knowledge_assistant.evaluation",
    "knowledge_assistant.storage",
    "knowledge_assistant.indexing",
    "knowledge_assistant.retrieval",
    "qdrant_client",
    "langgraph",
    "mcp",
    "openai",
)
AUTHORIZED_PREFIXES = (
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.core",
    "knowledge_assistant.embeddings",
    "knowledge_assistant.storage",
    "knowledge_assistant.indexing",
    "knowledge_assistant.retrieval",
)
CHAT_AUTHORIZED_PREFIXES = (
    "knowledge_assistant.bootstrap",
    "knowledge_assistant.agent",
    "knowledge_assistant.llm",
    "knowledge_assistant.mcp_server.config",
    "knowledge_assistant.core",
)
FORBIDDEN_RUNTIME_PREFIXES = (
    "torch",
    "FlagEmbedding",
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
        forbidden_prefixes = (
            CHAT_FORBIDDEN_PREFIXES
            if path.name == "chat.py"
            else GLOBAL_FORBIDDEN_PREFIXES
        )
        for prefix in forbidden_prefixes:
            if path.name == "chat.py" and prefix in {
                "knowledge_assistant.agent",
                "knowledge_assistant.llm",
                "knowledge_assistant.mcp_server",
            }:
                continue
            forbidden = {
                module for module in modules if module_matches_prefix(module, prefix)
            }
            assert not forbidden, (
                f"{path.name} must not import forbidden module {prefix!r}; "
                f"found {sorted(forbidden)}"
            )
        if path.name != "chat.py":
            for prefix in (
                "knowledge_assistant.agent",
                "knowledge_assistant.mcp_server",
                "knowledge_assistant.llm",
            ):
                forbidden = {
                    module
                    for module in modules
                    if module_matches_prefix(module, prefix)
                }
                assert not forbidden, (
                    f"{path.name} must not import forbidden module {prefix!r}; "
                    f"found {sorted(forbidden)}"
                )


def test_bootstrap_modules_do_not_import_model_runtimes() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_RUNTIME_PREFIXES:
            assert pattern not in content, (
                f"{path.name} must not import model runtime {pattern!r}"
            )


def test_bootstrap_modules_import_only_authorized_packages() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        modules = collect_import_modules(path)
        knowledge_assistant_modules = {
            module
            for module in modules
            if module_matches_prefix(module, "knowledge_assistant")
        }
        authorized_prefixes = (
            CHAT_AUTHORIZED_PREFIXES if path.name == "chat.py" else AUTHORIZED_PREFIXES
        )
        unauthorized = {
            module
            for module in knowledge_assistant_modules
            if not any(
                module_matches_prefix(module, prefix) for prefix in authorized_prefixes
            )
        }
        assert not unauthorized, (
            f"{path.name} has unauthorized knowledge_assistant imports: "
            f"{sorted(unauthorized)}"
        )


def test_bootstrap_modules_use_retrieval_public_api() -> None:
    for path in BOOTSTRAP_DIR.glob("*.py"):
        if path.name == "chat.py":
            continue
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
