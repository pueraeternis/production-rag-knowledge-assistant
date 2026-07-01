# Progress

Chronological record of completed milestones for Production RAG Knowledge Assistant.

---

## Current Status (2026-07-01)

**Latest completed plan:** [Plan 21 — Audit Portfolio Polish and Claim Precision](plans/active/21-audit-portfolio-polish.md) (Phase 1).

**Current phase:** Plan 21 Phase 1 complete. Phase 2 and Phase 3 remain deferred within Plan 21.

**Authorized implementation scope:** none (no active plan beyond deferred Plan 21 phases).

**Deferred from Plan 12:** query rewriting and retrieval retry (proposed Plan 12b), MCP SDK transport (proposed Plan 12c).

---

## 2026-07-01 — Audit Portfolio Polish (Phase 1)

**Plan:** [21-audit-portfolio-polish.md](plans/active/21-audit-portfolio-polish.md)

Portfolio credibility and open-source readiness improvements from the 2026-07-01 engineering audit:

* added `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`, and GitHub issue/PR templates;
* added README portfolio summary, implementation-status table, MCP/production claim precision, stub-first smoke demo with expected outputs, benchmark limitations, and reproduction workflow;
* added ADR index and current key decisions summary to `docs/DECISIONS.md`;
* added short corpus excerpts under `docs/examples/` for GitHub inspection;
* documented operational non-goals and session-local memory in README;
* validation suite passed: ruff format, ruff check, basedpyright, pytest.

**Deferred within Plan 21:** optional model dependency extra, GitHub Actions CI, troubleshooting guide (Phase 2); Makefile/justfile wrappers (Phase 3).

---

## 2026-06-23 — Chat Banner Omits LLM Endpoint URL

* `rag chat` startup banner prints `LLM model: <name>` only; `LLM_BASE_URL` is no longer shown (avoids exposing internal IPs/hostnames in terminal output).
* Documented in README behavior notes and ADR-077.

---

## 2026-06-22 — Agent Tool-Loop and Off-Topic Search Fix

Operator validation found empty answers and irrelevant Sources for general-knowledge questions (for example "What is the capital of France?").

* preserved assistant `tool_calls` on `ChatMessage` and in OpenAI request payloads so the tool loop does not repeat `search_documents` after tool results are already in context;
* tightened `SYSTEM_PROMPT` and `search_documents` tool description to scope search to the internal corpus only;
* documented expected off-topic behavior in README.

---

## 2026-06-22 — Chat CLI UX and Non-Streaming Turn Fix

Operator validation surfaced two chat issues:

* REPL assistant output could run into the next `You:` prompt when streaming omitted a trailing newline — fixed in `cli/chat.py` with explicit turn finalization.
* `--no-stream` could fail against some OpenAI-compatible gateways when LangGraph issued a final `chat()` call still carrying tools and large tool payloads — `run_turn` now mirrors streaming's two-phase pattern (tool loop, then final `chat()` without tools).

Also documented `set -a && source .env && set +a` in README and suppressed third-party tokenizer/hub progress noise during `rag chat`.

---

## 2026-06-22 — Real Sparse Embeddings Integration

**Plan:** [20-real-sparse-embeddings-integration.md](plans/completed/20-real-sparse-embeddings-integration.md)

Replaced ADR-010 sparse placeholders and stub-only query sparse paths with real BGE-M3 lexical vectors:

* added `embeddings/sparse_conversion.py` with `lexical_weights_to_sparse_payload` and `SparseVectorPayload`;
* extended `BgeM3FlagEmbeddingRuntime` with `embed_passages_sparse`, `embed_query_sparse`, and `embed_passages_dual`;
* added `SparseEmbeddingProvider`, `StubSparseEmbeddingProvider`, and `BgeM3SparseEmbeddingProvider` in indexing;
* added `BgeM3SparseQueryEmbeddingProvider` in retrieval;
* `IndexingPipeline` accepts `sparse_embedding_provider` and upserts per-chunk sparse vectors;
* bootstrap wires sparse providers from `RAG_EMBEDDING_MODE` (stub/real) for indexing and retrieval;
* `build_retrieval_stack` accepts injected `sparse_query_embedding_provider`; pipeline label reports `sparse (bge-m3)` in real mode;
* unit and integration tests with mocked FlagEmbedding; optional `@pytest.mark.embedding_model` sparse smoke test;
* recorded ADR-081 through ADR-086 in `docs/DECISIONS.md`;
* documented sparse write/read paths in `docs/ARCHITECTURE.md` and `README.md`;
* validation suite passed: ruff format, ruff check, basedpyright, pytest (587 tests, 4 deselected model markers).

---

## 2026-06-22 — Interactive Chat Demo

**Plan:** [19-interactive-chat-demo.md](plans/completed/19-interactive-chat-demo.md)

Delivered the lecture interactive chat path:

* added `StreamingLLMClient` capability and SSE streaming to `OpenAICompatibleLLMClient` without changing Plan 11 `LLMClient.chat()`;
* added `TurnSource`, `TurnResult`, `TurnStream`, and streaming turn execution strategy (no LangGraph topology changes);
* added `bootstrap/chat.py` with `ChatSession`, `build_chat_session()`, and turn facades;
* added `rag chat` CLI with streaming REPL, `--message`, `--no-stream`, `--no-sources`, configuration banner, and precondition checks (no startup LLM probe);
* CLI consumes `TurnStream` and renders sources from `TurnResult.sources` only;
* recorded ADR-042 through ADR-046 (Plan 12 carryover) and ADR-071 through ADR-080 in `docs/DECISIONS.md`;
* documented chat workflow in `docs/ARCHITECTURE.md` and `README.md`;
* unit and integration tests for streaming, chat session, CLI parsing, preconditions, and end-to-end stub chat;
* validation suite passed: ruff format, ruff check, basedpyright, pytest (566 tests, 3 deselected model markers).

---

## 2026-06-22 — Retrieval Strategy Evaluation

**Plan:** [18-retrieval-strategy-evaluation.md](plans/completed/18-retrieval-strategy-evaluation.md)

Exposed end-to-end retrieval strategy evaluation through bootstrap and CLI:

* added `bootstrap/retrievers.py` with `RetrievalStrategy`, shared `RetrievalStack`, and `build_retriever_for_strategy()`;
* refactored `build_demo_environment()` to use shared retrieval stack builder (canonical `retriever` remains full rerank stack);
* added `rag evaluate run` and `rag evaluate compare` CLI commands with precondition checks, configuration banner, and Plan 13 report formatters;
* evaluate inherits `RAG_EMBEDDING_MODE` and `RAG_RERANKER_MODE` from bootstrap (ADR-070 stub-mode notice);
* unit tests for strategy assembly, CLI parsing, preconditions, and import boundaries;
* integration tests for evaluate run/compare against indexed fixture corpus;
* recorded ADR-067 through ADR-070 in `docs/DECISIONS.md`;
* documented evaluation execution workflow in `docs/ARCHITECTURE.md` and `README.md`;
* validation suite passed: ruff format, ruff check, basedpyright, pytest (542 tests, 3 deselected model markers).

---


## 2026-06-22 — Real Reranker Integration

**Plan:** [17-real-reranker.md](plans/completed/17-real-reranker.md)

Integrated the production BGE reranker runtime behind the existing retrieval protocol:

* added `BgeRerankerSettings` and `BgeReranker` for `BAAI/bge-reranker-v2-m3`;
* used lazy `FlagEmbedding` backend loading with injectable fake backends for tests;
* preserved the Plan 09 candidate contract: `N` candidates in, `N` candidates out;
* replaced reranked `SearchResult.score` values with BGE relevance scores and deterministic score/`chunk_id` ordering;
* kept `StubReranker` as the default for CI and fallback demo mode;
* added `RAG_RERANKER_*` environment configuration and real-mode bootstrap selection;
* updated `rag demo info` pipeline reporting without triggering model load;
* added mocked reranker unit tests, bootstrap mode tests, and an optional skipped real-model smoke test;
* recorded ADR-061 through ADR-066 in `docs/DECISIONS.md`;
* documented real reranker setup in `README.md`, `.env.example`, and `docs/ARCHITECTURE.md`.

---

## 2026-06-22 — Real Dense Embeddings Integration

**Plan:** [16-real-dense-embeddings-integration.md](plans/completed/16-real-dense-embeddings-integration.md)

Replaced stub dense embedding providers with real BGE-M3 runtime while preserving ADR-013 layer boundaries:

* added `knowledge_assistant.embeddings` package with `DenseEmbeddingRuntime`, `BgeM3FlagEmbeddingRuntime`, `EmbeddingRuntimeSettings`, and factory;
* added `BgeM3EmbeddingProvider` (indexing) and `BgeM3QueryEmbeddingProvider` (retrieval) adapters;
* bootstrap selects stub (default) vs real dense providers via `RAG_EMBEDDING_MODE`; one shared runtime per `DemoEnvironment` in real mode;
* `rag demo info` pipeline label reports embedding mode;
* L2 normalization and dimension validation at runtime boundary;
* device fail-fast for unavailable `cuda`/`mps` (no silent CPU fallback);
* `FlagEmbedding` runtime dependency; stub providers retained for CI;
* import-boundary tests and optional `@pytest.mark.embedding_model` smoke tests;
* recorded ADR-055 through ADR-060 in `docs/DECISIONS.md`;
* documented embeddings layer in `docs/ARCHITECTURE.md` and `README.md`;
* validation suite passed: ruff format, ruff check, basedpyright, pytest (522 tests, 3 deselected model markers).

---

## 2026-06-22 — Demo Bootstrap Workflow

**Plan:** [15-demo-bootstrap-workflow.md](plans/completed/15-demo-bootstrap-workflow.md)

Wired existing components into a runnable demo bootstrap path:

* added `knowledge_assistant.bootstrap` composition root with `BootstrapSettings`, `DemoEnvironment`, and `build_demo_environment()`;
* canonical demo retrieval stack: dense + sparse → fusion (RRF) → rerank (stub providers);
* `rag` CLI entrypoint with `demo info`, `demo load`, and `demo reset` subcommands;
* extended `VectorStore` protocol with `count_points()` for collection cardinality reporting;
* human-in-the-loop approval gates for destructive `demo load --rebuild` and `demo reset`;
* AST-based import-boundary tests for CLI and bootstrap packages;
* CLI integration tests exercise `main()` entry points for demo commands;
* corpus document counting aligned with indexing discovery (includes `README.md`);
* `BootstrapSettings.dense_vector_size` delegates to `storage_settings.dense_vector_size`;
* bootstrap imports retrieval orchestrators from public `knowledge_assistant.retrieval` API;
* recorded ADR-051 through ADR-054 in `docs/DECISIONS.md`;
* documented bootstrap layer and CLI demo workflow in `docs/ARCHITECTURE.md` and `README.md`;
* validation suite passed: ruff format, ruff check, basedpyright, pytest (457 tests).

---

## 2026-06-22 — Tracked Corpus Generator

**Plan:** [14-synthetic-knowledge-base.md](plans/completed/14-synthetic-knowledge-base.md)

Revised corpus generation for reproducibility:

* tracked generator assets under `tools/knowledge_generator/`;
* `tools/knowledge_generator/manifests/corpus.v1.yaml` is the single source of truth for the 96-document inventory, paths, types, owners, related systems, related documents, required facts, and benchmark alignment metadata;
* document-type prompt templates live under `tools/knowledge_generator/templates/`;
* quality gates live under `tools/knowledge_generator/quality/`;
* regeneration command is `python3 tools/knowledge_generator/generator.py`;
* generated corpus remains local under gitignored `knowledge/`; fresh clones can regenerate it from tracked assets.

Latest generator run produced 97 markdown files (96 documents plus `knowledge/README.md`) and passed quality gates: duplicate paragraphs 0, duplicate sentences 205, average repeated sentence ratio 3.91%, average section title diversity 100.00%, known filler phrase hits 0, distinct section structures 96.

---

## 2026-06-21 — Repository Governance Bootstrap

**Plan:** [01-project-bootstrap.md](plans/completed/01-project-bootstrap.md)

Established repository governance and documentation skeleton:

* aligned documentation precedence and read-first order across governance files;
* standardized terminology (Retrieval Layer);
* created `docs/` structure with architecture, decisions, and progress documents;
* documented bootstrap validation exception for pre-Python repository state.

---

## 2026-06-21 — Python Bootstrap

**Plan:** [02-python-bootstrap.md](plans/completed/02-python-bootstrap.md)

Established the Python project foundation:

* created `pyproject.toml` with `src` layout, `uv` configuration, and development dependency groups;
* generated `uv.lock` with tooling-only dependencies (`ruff`, `basedpyright`, `pytest`);
* created `src/knowledge_assistant/` package skeleton aligned with `docs/ARCHITECTURE.md`;
* configured ruff, basedpyright, and pytest;
* added `tests/unit/`, `tests/integration/`, and `tests/smoke/` layout with package import smoke tests;
* documented setup and validation workflow in `README.md`.

Bootstrap validation exception is superseded. All commits must pass the standard quality commands.

---

## 2026-06-21 — Domain Models

**Plan:** [03-domain-models.md](plans/completed/03-domain-models.md)

Established the shared domain model foundation in `knowledge_assistant.core`:

* implemented frozen dataclass domain types for documents, chunks, source attribution, retrieval, and indexing;
* defined `DocumentId` and `ChunkId` as `NewType` identifiers;
* implemented `IndexingSourceKind` and `ApprovalStatus` as stdlib enums;
* added `__post_init__` validation for all domain invariants;
* exported public API from `core/__init__.py`;
* added unit tests in `tests/unit/core/` covering construction, validation, and immutability;
* recorded ADR-001 in `docs/DECISIONS.md`;
* documented core domain layer in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — Storage Layer

**Plan:** [04-storage-layer.md](plans/completed/04-storage-layer.md)

Established the Qdrant storage boundary in `knowledge_assistant.storage`:

* defined `VectorStore` protocol with five methods (`create_collection`, `delete_collection`, `collection_exists`, `upsert_chunks`, `search_dense`; `search_sparse` added in Plan 07);
* implemented `QdrantVectorStore` with named `dense` and `sparse` vectors;
* added `ChunkUpsertItem`, `SparseVector`, and payload mapping for nine-field chunk payloads;
* added `StorageSettings` and `create_qdrant_vector_store` factory;
* added storage-specific exception types;
* added `qdrant-client` runtime dependency;
* added unit tests in `tests/unit/storage/` and integration tests with in-memory Qdrant;
* recorded ADR-002 through ADR-006 in `docs/DECISIONS.md`;
* documented storage layer boundary in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — Indexing Pipeline

**Plan:** [05-indexing-pipeline.md](plans/completed/05-indexing-pipeline.md)

Established the indexing layer in `knowledge_assistant.indexing`:

* implemented local file discovery for `.md` and `.txt` sources;
* added LlamaIndex adapter confined to `llamaindex_adapter.py` with line attribution from original text;
* implemented deterministic UUID5 `DocumentId` and `ChunkId` generation;
* defined `EmbeddingProvider` protocol with `StubEmbeddingProvider` development stub;
* added constant sparse vector placeholder for storage schema compliance;
* implemented `IndexingPipeline` with `preview_indexing` and `index_documents` (including rebuild flow);
* added `llama-index-core` and `llama-index-readers-file` runtime dependencies;
* added unit tests in `tests/unit/indexing/` and integration tests in `tests/integration/indexing/`;
* recorded ADR-007 through ADR-013 in `docs/DECISIONS.md`;
* documented indexing layer boundary in `docs/ARCHITECTURE.md`.

**Revision (post-review):** overlap-aware line attribution; `ChunkingError` for splitter failures; empty-directory `index_documents` storage no-op; LlamaIndex `SimpleDirectoryReader` owns loading with raw on-disk text as attribution mirror only.

---

## 2026-06-21 — Dense Retrieval

**Plan:** [06-dense-retrieval.md](plans/completed/06-dense-retrieval.md)

Established the dense retrieval path in `knowledge_assistant.retrieval`:

* implemented `DenseRetriever` orchestrating query embedding and `VectorStore.search_dense`;
* defined retrieval-local `QueryEmbeddingProvider` protocol separate from indexing `EmbeddingProvider`;
* added `StubQueryEmbeddingProvider` (hash-based, deterministic, L2-normalized, default dimension 1024);
* added `DenseRetrievalSettings` with `dense_vector_size` validation;
* added retrieval-specific exception types;
* added unit tests in `tests/unit/retrieval/` and integration tests with fake `VectorStore` in `tests/integration/retrieval/`;
* recorded ADR-014 through ADR-016 in `docs/DECISIONS.md`;
* documented retrieval layer dense path in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — Sparse Retrieval

**Plan:** [07-sparse-retrieval.md](plans/completed/07-sparse-retrieval.md)

Established the sparse retrieval path in `knowledge_assistant.retrieval`:

* extended `VectorStore` protocol with `search_sparse` (sixth method);
* implemented `QdrantVectorStore.search_sparse` querying the `sparse` named vector;
* added storage structural validation for sparse search inputs;
* implemented `SparseRetriever` orchestrating query sparse embedding and sparse search;
* defined retrieval-local `SparseQueryVector` and `SparseQueryEmbeddingProvider` protocol;
* added `StubSparseQueryEmbeddingProvider` (hash-based, deterministic, no model runtime);
* added unit tests in `tests/unit/retrieval/` and `tests/unit/storage/`;
* added integration tests with fake `VectorStore` and in-memory Qdrant;
* recorded ADR-017 through ADR-020 in `docs/DECISIONS.md`;
* documented sparse retrieval path and future placeholder constraint in `docs/ARCHITECTURE.md`.

Indexing sparse generation and reindex migration remain deferred to a future plan per ADR-020.

---

## 2026-06-21 — Fusion Retrieval

**Plan:** [08-fusion-retrieval.md](plans/completed/08-fusion-retrieval.md)

Established hybrid rank-based fusion in `knowledge_assistant.retrieval`:

* defined retrieval-local `Retriever` protocol for leaf-retriever composition;
* added `FusionRetrievalSettings` with `rrf_k` and `leaf_top_k_multiplier`;
* implemented `reciprocal_rank_fusion` pure function with RRF, deduplication, and deterministic tie-breaking;
* implemented `FusionRetriever` orchestrating dense and sparse leaf retrievers with expanded candidate pools;
* added unit tests in `tests/unit/retrieval/` and integration tests with `FakeRetriever` in `tests/integration/retrieval/`;
* recorded ADR-021 through ADR-023 in `docs/DECISIONS.md`;
* documented fusion retrieval path and fused score semantics in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — Reranking

**Plan:** [09-reranking.md](plans/completed/09-reranking.md)

Established deterministic reranking orchestration in `knowledge_assistant.retrieval`:

* defined retrieval-local `Reranker` protocol with candidate preservation contract (`N` in → `N` out);
* added `RerankRetrievalSettings` with `candidate_top_k_multiplier` for candidate pool expansion;
* implemented `StubReranker` (deterministic Jaccard token overlap, no model runtime);
* implemented `RerankRetriever` wrapping any `Retriever` with contract enforcement via `ValueError`;
* added unit tests in `tests/unit/retrieval/` and integration tests with `FakeRetriever` in `tests/integration/retrieval/`;
* recorded ADR-024 through ADR-027 in `docs/DECISIONS.md`;
* documented reranking retrieval path and reranked score semantics in `docs/ARCHITECTURE.md`.

Real `BAAI/bge-reranker-v2-m3` cross-encoder runtime remains deferred to a future plan per ADR-027.

---

## 2026-06-21 — Knowledge MCP Server

**Plan:** [10-knowledge-mcp-server.md](plans/completed/10-knowledge-mcp-server.md)

Established the knowledge-access MCP handler boundary in `knowledge_assistant.mcp_server`:

* implemented Tier 1 handlers — `search_documents`, `index_documents_preview`, `index_documents_apply` — with Pydantic schemas confined to `schemas.py`;
* added `McpServerSettings`, `ApprovalRequiredError`, and core → Pydantic formatting helpers;
* enforced human approval gate (`approval_confirmed=True`) before index mutation;
* added `SearchResult.source: SourceReference` populated by storage at search time; reranking and fusion preserve `source`;
* added stubs for deferred MCP SDK registration (`server.py`) and Tier 2 resources (`resources.py`);
* added `pydantic` runtime dependency for MCP schemas only;
* added unit tests in `tests/unit/mcp_server/` and integration tests in `tests/integration/mcp_server/`;
* added cross-layer tests for `SearchResult.source` in storage and reranking;
* recorded ADR-028 through ADR-034 in `docs/DECISIONS.md`;
* documented MCP handler layer and source attribution path in `docs/ARCHITECTURE.md`.

MCP SDK runtime, Tier 2 browse tools (`get_document`, `get_statistics`), and MCP resources remain deferred per ADR-034.

---

## 2026-06-21 — LLM Boundary

**Plan:** [11-llm-boundary.md](plans/completed/11-llm-boundary.md)

Established the OpenAI-compatible model invocation layer in `knowledge_assistant.llm`:

* implemented chat-oriented `LLMClient` protocol with sync, non-streaming `chat(...)` entry point;
* added frozen dataclass DTOs: `ChatMessage`, `ChatRole`, `ToolDefinition`, `ToolCall`, `GenerationSettings`, `GenerationResult`, `TokenUsage`;
* added `LlmSettings.from_env()` and committed `.env.example` with six `LLM_*` variables;
* implemented `OpenAICompatibleLLMClient` with httpx transport confined to `openai_client.py`;
* implemented `StubLLMClient` for deterministic scripted responses in tests;
* added typed exception hierarchy: `LLMError`, `LLMTimeoutError`, `LLMAuthenticationError`, `LLMResponseError`, `LLMTransportError`;
* added unit tests in `tests/unit/llm/` and integration tests in `tests/integration/llm/` with mocked HTTP;
* added import-boundary tests enforcing layer isolation;
* added `httpx` runtime dependency;
* recorded ADR-035 through ADR-041 in `docs/DECISIONS.md`;
* documented LLM boundary in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — LangGraph Agent

**Plan:** [12-langgraph-agent.md](plans/completed/12-langgraph-agent.md)

Established the LangGraph conversational agent in `knowledge_assistant.agent`:

* implemented `StateGraph` with `agent_node`, `tool_node`, `max_iterations`, and conditional `should_continue` routing;
* added in-memory `AgentState` with message history and tool-iteration guard (`AgentSettings.max_tool_iterations`, default 5);
* integrated `LLMClient.chat()` using Plan 11 DTOs from `agent_node` only;
* added `ToolRegistry`, `AgentTool` protocol, and Tier 1 MCP handler adapters in `agent/wiring.py`;
* added RAG system prompt with grounding and citation contract in `agent/prompts.py`;
* added `run_turn` public API and `build_agent_graph` factory;
* added `langgraph` runtime dependency;
* added unit tests in `tests/unit/agent/` and integration tests in `tests/integration/agent/`;
* added import-boundary tests for agent core modules.

Plan 12 uses in-process MCP handler adapters (ADR-043 design) rather than MCP SDK transport. Query rewriting, retrieval retry, durable memory, and CLI chat remain deferred per plan non-scope.

**Documentation follow-up (outstanding):** none — ADR-042 through ADR-046 accepted in Plan 19 (`docs/DECISIONS.md`).

---

## 2026-06-21 — Evaluation Framework

**Plan:** [13-evaluation-framework.md](plans/completed/13-evaluation-framework.md)

Established the retrieval evaluation layer in `knowledge_assistant.evaluation`:

* implemented frozen dataclass models for benchmark cases, document registry, settings, per-case results, single-strategy reports, and multi-strategy comparison reports;
* added pure metric functions — Hit Rate@K, Recall@K, and MRR — matching via normalized `SearchResult.source.document_path`;
* implemented `EvaluationRunner` accepting any `Retriever` with fail-fast error handling;
* added `compare_evaluation_reports`, `format_evaluation_report`, and `format_comparison_report` for side-by-side dense/sparse/fusion/rerank comparison;
* committed retrieval benchmark under `data/evaluation/retrieval_benchmark_v1.json` (70 curated cases targeting the synthetic knowledge-base corpus);
* added unit tests in `tests/unit/evaluation/` with minimal JSON fixtures and import-boundary tests;
* recorded ADR-047 through ADR-050 in `docs/DECISIONS.md`;
* documented evaluation layer boundary in `docs/ARCHITECTURE.md`.

CLI wiring for evaluation output and optional full-benchmark integration tests remain deferred per plan non-scope.
