# Architecture

Production RAG Knowledge Assistant is a documentation-driven educational project demonstrating modern enterprise knowledge assistant architecture.

For project vision and scope, see [PROJECT.md](../PROJECT.md).

---

## System Overview

```text
User
  ↓
CLI Chat
  ↓
LangGraph Agent
  ↓
MCP Client
  ↓
Knowledge MCP Server
  ↓
Retrieval Layer
  ↓
Qdrant
```

The agent never interacts with Qdrant directly.

All knowledge access happens through MCP tools and resources.

---

## Component Boundaries

| Component        | Owns                                                   | Must not own                            |
| ---------------- | ------------------------------------------------------ | --------------------------------------- |
| LangGraph Agent  | Conversation handling, routing, tool selection, memory | Retrieval implementation, Qdrant access |
| MCP Server       | Knowledge tools and resources                          | Agent behavior, conversation management |
| Retrieval Layer  | Dense retrieval, sparse retrieval, fusion, reranking   | LLM interaction                         |
| Indexing Layer   | Loading, parsing, chunking, indexing                   | Retrieval decisions                     |
| Qdrant Storage   | Vector storage and metadata                            | Business logic                          |
| LLM Boundary     | All model calls                                        | Retrieval implementation                |

---

## Retrieval Layer

The retrieval layer is deterministic and must not call LLMs. Plan 06 implements dense retrieval; Plan 07 implements sparse retrieval; Plan 08 implements rank-based fusion; Plan 09 implements reranking orchestration with a deterministic stub. Plan 17 adds an opt-in real `BAAI/bge-reranker-v2-m3` runtime behind the same `Reranker` protocol.

### Dense retrieval path

```text
SearchQuery (text, top_k)
    ↓
DenseRetriever.retrieve()
    ↓
QueryEmbeddingProvider.embed_query(query.text)
    ↓
validate len(vector) == DenseRetrievalSettings.dense_vector_size
    ↓
VectorStore.search_dense(vector=vector, top_k=query.top_k)
    ↓
RetrievalResult(query=query, results=...)
```

### Sparse retrieval path

```text
SearchQuery (text, top_k)
    ↓
SparseRetriever.retrieve()
    ↓
SparseQueryEmbeddingProvider.embed_query(query.text)
    ↓
SparseQueryVector (retrieval-local validation, non-empty enforced)
    ↓
VectorStore.search_sparse(indices=..., values=..., top_k=query.top_k)
    ↓
RetrievalResult(query=query, results=...)
```

### Fusion retrieval path

```text
SearchQuery (text, top_k)          ← caller input
    ↓
FusionRetriever.retrieve()
    ↓
leaf_top_k = top_k * leaf_top_k_multiplier
leaf_query = SearchQuery(text, top_k=leaf_top_k)
    ↓
DenseRetriever.retrieve(leaf_query)  → RetrievalResult.results (dense ranks)
SparseRetriever.retrieve(leaf_query) → RetrievalResult.results (sparse ranks)
    ↓
reciprocal_rank_fusion(dense, sparse, rrf_k)
    ↓
dedupe by ChunkId + RRF score + tie-break by chunk_id
    ↓
truncate to query.top_k
    ↓
RetrievalResult(query=caller_query, results=fused)
```

### Reranking retrieval path

```text
SearchQuery (text, top_k)          ← caller input
    ↓
RerankRetriever.retrieve()
    ↓
candidate_top_k = top_k * candidate_top_k_multiplier
candidate_query = SearchQuery(text, top_k=candidate_top_k)
    ↓
base Retriever.retrieve(candidate_query)  → RetrievalResult.results
    ↓
Reranker.rerank(query=caller_query, candidates=...)
    ↓
validate len(reranked) == len(candidates)  ← ValueError on violation
    ↓
sort by reranker score + tie-break by chunk_id
    ↓
truncate to query.top_k
    ↓
RetrievalResult(query=caller_query, results=reranked)
```

Hybrid retrieval composes dense and sparse leaf retrievers behind `FusionRetriever`:

```text
Dense Search
      +
Sparse Search (BGE-M3 lexical vectors)
      ↓
Fusion (RRF)
      ↓
Reranker
      ↓
Top Context
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `DenseRetrievalSettings`, `FusionRetrievalSettings`, `RerankRetrievalSettings`, `BgeRerankerSettings` |
| `protocol.py` | `Retriever` composition protocol |
| `fusion.py` | `FusionRetriever`, `reciprocal_rank_fusion` (RRF) |
| `rerank.py` | `RerankRetriever`, `Reranker`, `StubReranker`, `BgeReranker` |
| `embeddings.py` | `QueryEmbeddingProvider`, `StubQueryEmbeddingProvider`, `BgeM3QueryEmbeddingProvider`, `SparseQueryEmbeddingProvider`, `StubSparseQueryEmbeddingProvider` |
| `exceptions.py` | Retrieval-specific error types |
| `dense.py` | `DenseRetriever` orchestration |
| `sparse_vectors.py` | `SparseQueryVector` (retrieval-local) |
| `sparse.py` | `SparseRetriever` orchestration |

**Fusion score semantics (ADR-023):** `FusionRetriever` output `SearchResult.score` values are RRF fusion scores — ordinal ranking keys, not raw dense/sparse similarity scores and not comparable to reranker scores.

**Reranked score semantics (ADR-026, ADR-064):** `RerankRetriever` output `SearchResult.score` values are reranker relevance scores — ordinal ranking keys, not comparable to dense, sparse, or RRF scores. `StubReranker` uses deterministic token overlap; `BgeReranker` replaces scores with model relevance scores from `BAAI/bge-reranker-v2-m3` or the configured BGE model. Higher is better, and equal scores are ordered by `chunk_id` ascending. The `Reranker` contract preserves candidate count (`N` in → `N` out); only `RerankRetriever` truncates to `query.top_k`. Fusion leaf expansion (`FusionRetrievalSettings.leaf_top_k_multiplier`) and reranking candidate expansion (`RerankRetrievalSettings.candidate_top_k_multiplier`) are independent settings with no cross-layer coupling.

**Query embedding ownership (ADR-013, ADR-015, ADR-019):** retrieval generates query-path dense and sparse embeddings via retrieval-local providers; indexing generates write-path chunk embeddings; storage generates neither.

**Retrieval boundary:** leaf retriever production code depends on `core` and `storage.protocol.VectorStore` only. Fusion and reranking production code (`fusion.py`, `protocol.py`, `rerank.py`) depend on `core` and retrieval-local modules only — not on `VectorStore`, `storage.models`, `qdrant_client`, or indexing packages. Indexing may import `storage.models` for upsert boundary types.

**Public contract:** callers submit `SearchQuery` text and receive `RetrievalResult`. Vectors are internal to retrieval and must not leak to MCP, agent, or other higher layers.

**Sparse placeholder constraint (ADR-020):** indexing still stores a constant sparse placeholder per ADR-010 until a future sparse indexing plan replaces it. Meaningful sparse retrieval against production-indexed corpora requires that future plan and a full reindex with caller approval. Plan 07 delivers the read path only.

**BGE reranker runtime (ADR-061 through ADR-066):** `BgeReranker` lives in `knowledge_assistant.retrieval` and implements the existing `Reranker.rerank(query, candidates)` protocol. It loads the FlagEmbedding model lazily on the first non-empty rerank call, returns `()` for empty candidates without loading, reuses one backend per `BgeReranker` instance, and keeps CPU/GPU/runtime settings in `BgeRerankerSettings`. Default demo and CI wiring still use `StubReranker`; real mode is opt-in via bootstrap settings/environment.

**Dependency rule:** leaf retrievers depend on the `VectorStore` protocol only — not on `qdrant_client`, `StorageSettings`, or other storage modules. Fusion and reranking depend on the `Retriever` protocol (and reranking depends on the `Reranker` protocol) only. The real reranker may import its model runtime lazily inside retrieval, but storage, indexing, MCP, agent, evaluation, bootstrap, and LLM layers must not load reranker models. See [ADR-014](DECISIONS.md#adr-014-dense-retrieval-boundary) through [ADR-027](DECISIONS.md#adr-027-future-bge-cross-encoder-reranker-integration) and [ADR-061](DECISIONS.md#adr-061-real-reranker-stays-behind-the-existing-reranker-protocol) through [ADR-066](DECISIONS.md#adr-066-reranker-model-ownership).

---

## Dependency Flow

Preferred:

```text
agent
  ↓
mcp_server
  ↓
retrieval
  ↓
storage
```

```text
agent
  ↓
llm
```

```text
indexing
  ↓
storage
```

Forbidden:

```text
mcp_server → llm
retrieval → llm
storage → llm
storage → agent
retrieval → agent
```

---

## Core Domain Layer

The `core/` package defines shared domain types used across all layers. Types are immutable frozen dataclasses with `__post_init__` validation (see [ADR-001](DECISIONS.md#adr-001-domain-model-technology)).

| Module | Types |
| ------ | ----- |
| `identifiers.py` | `DocumentId`, `ChunkId` |
| `document.py` | `Document`, `DocumentMetadata`, `DocumentContent` |
| `chunk.py` | `Chunk`, `ChunkMetadata` |
| `source.py` | `LineRange`, `SourceReference` |
| `retrieval.py` | `SearchQuery`, `SearchResult` (with `source: SourceReference`), `RetrievalResult` |
| `indexing.py` | `IndexingSourceKind`, `IndexingSource`, `IndexingPreview`, `ApprovalStatus` |

Core models are implementation-agnostic. They must not import from `agent`, `retrieval`, `indexing`, `storage`, `mcp_server`, `llm`, `cli`, or third-party application libraries. Boundary layers translate between domain types and infrastructure-specific schemas.

`SourceReference` is the canonical citation model for user-visible source attribution. It is distinct from `DocumentMetadata` and `ChunkMetadata`, which serve indexing and storage concerns.

---

## Qdrant Storage Layer

The `storage/` package is the only component that imports `qdrant_client`. Indexing and retrieval depend on the `VectorStore` protocol, not on Qdrant APIs directly.

```text
indexing
  ↓
VectorStore (protocol)
  ↓
QdrantVectorStore
  ↓
Qdrant
```

```text
retrieval
  ↓
VectorStore (protocol)
  ↓
QdrantVectorStore
  ↓
Qdrant
```

| Module | Responsibility |
| ------ | -------------- |
| `protocol.py` | `VectorStore` protocol (seven methods: create, delete, exists, count_points, upsert, search_dense, search_sparse) |
| `models.py` | `ChunkUpsertItem`, `SparseVector` boundary types |
| `mapping.py` | Pure payload ↔ domain translation |
| `collection.py` | Vector names and collection defaults |
| `config.py` | `StorageSettings` |
| `qdrant_store.py` | `QdrantVectorStore` implementation, `search_sparse`, and `create_qdrant_vector_store` factory |
| `validation.py` | Structural validation for sparse search inputs |
| `exceptions.py` | Storage-specific error types |

Storage receives pre-computed vectors on write and pre-computed query vectors on read. It does not generate embeddings. See [ADR-002](DECISIONS.md#adr-002-vectorstore-protocol-abstraction) through [ADR-006](DECISIONS.md#adr-006-storage-does-not-generate-embeddings).

---

## Embeddings Layer

Plan 16 delivers the shared BGE-M3 dense embedding runtime in `knowledge_assistant.embeddings`. Indexing and retrieval keep layer-local provider protocols per ADR-013; bootstrap owns shared runtime construction per ADR-057.

```text
BootstrapSettings (embedding_mode=stub|real)
        ↓
create_shared_dense_embedding_runtime(...)
        ↓
┌──────────────────────────┬────────────────────────────┐
│ BgeM3EmbeddingProvider   │ BgeM3QueryEmbeddingProvider │
│ → IndexingPipeline       │ → DenseRetriever            │
└──────────────────────────┴────────────────────────────┘
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `EmbeddingRuntimeSettings` and `RAG_EMBEDDING_*` env loading |
| `runtime.py` | `DenseEmbeddingRuntime` protocol and `BgeM3FlagEmbeddingRuntime` |
| `factory.py` | `create_dense_embedding_runtime`, shared runtime cache |
| `exceptions.py` | `EmbeddingRuntimeError`, dimension and device errors |

**Stable contract:** indexing and retrieval depend on `DenseEmbeddingRuntime` only — not on FlagEmbedding or `torch`.

**Inference paths:** `embed_passages` batches document chunks; `embed_query` processes one query. Distinct BGE-M3 encoding modes apply in the default FlagEmbedding implementation.

**Normalization and dimensions (ADR-059):** runtime L2-normalizes outputs when configured; output length must equal configured `dense_vector_size` (default `1024`).

**Device validation:** configured `cuda` or `mps` fails fast at runtime initialization when unavailable — no silent CPU fallback.

**Concurrency:** thread safety is not guaranteed; one runtime instance per bootstrap assembly is intended for single-process demo usage.

**Migration (ADR-058):** switching stub ↔ real dense embeddings requires full collection rebuild and reindex with caller approval.

**Default mode (ADR-060):** stub providers remain the default for CI and fast tests; real mode is opt-in via `RAG_EMBEDDING_MODE=real`.

See [ADR-055](DECISIONS.md#adr-055-dedicated-embeddings-package-for-shared-bge-m3-runtime) through [ADR-060](DECISIONS.md#adr-060-stub-providers-remain-default-for-ci-and-fast-tests).

---

## Indexing Layer

The `indexing/` package turns local documents into stored chunks via the `VectorStore` protocol. It is the only component that imports LlamaIndex (confined to `llamaindex_adapter.py`). See [ADR-007](DECISIONS.md#adr-007-llamaindex-containment-in-indexing-layer) through [ADR-013](DECISIONS.md#adr-013-embedding-boundary-ownership).

```text
local file/directory
    ↓
LlamaIndex SimpleDirectoryReader (loading)
    ↓
loaded document text
    ↓
LlamaIndex SentenceSplitter (chunking)
    ↓
core domain models
    ↓
EmbeddingProvider (write path)
    ↓
VectorStore.upsert_chunks

parallel attribution mirror:
Path.read_text → raw source text → title, section_title, LineRange
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `IndexingSettings` |
| `documents.py` | Local file discovery (`.md`, `.txt`) |
| `embeddings.py` | `EmbeddingProvider`, `StubEmbeddingProvider`, `BgeM3EmbeddingProvider`, sparse placeholder |
| `exceptions.py` | Indexing-specific error types |
| `ids.py` | UUID5 `DocumentId` and `ChunkId` generation |
| `llamaindex_adapter.py` | LlamaIndex load/chunk + raw attribution mirror → domain models (sole LlamaIndex import site) |
| `pipeline.py` | `IndexingPipeline` with `preview_indexing` and `index_documents` |

**Loading and chunking:** LlamaIndex `SimpleDirectoryReader` owns loading; `SentenceSplitter` owns chunk boundaries. A separate raw file read mirrors on-disk text for source attribution only — it is not the primary loader and does not replace LlamaIndex ingestion.

**Reader contract:** one input file must yield exactly one LlamaIndex document; zero or multiple documents raise `DocumentLoadError`.

**Source attribution:** raw on-disk text is the source of truth for `LineRange`. Character offsets are resolved in indexing code (including overlap-aware lookup) and mapped to 1-based lines. LlamaIndex node metadata is not used for line numbers.

**Empty discovery:** `preview_indexing` may return zero document/chunk counts for empty directories. `index_documents` is a storage no-op when no files are discovered — it does not create, delete, or upsert collections.

**Chunking errors:** file read failures raise `DocumentLoadError`; LlamaIndex splitter failures and empty chunk results raise `ChunkingError`.

**Dependency rule:** indexing depends on the `VectorStore` protocol only — not on `qdrant_client` or `StorageSettings`.

**Embedding ownership (ADR-013):** indexing generates write-path chunk embeddings; retrieval generates query-path dense embeddings (Plan 06) and sparse query embeddings (Plan 07); storage generates neither.

**ID ownership (ADR-008):** indexing generates deterministic UUID5 document and chunk IDs; storage does not generate IDs.

**Human approval (ADR-012):** `preview_indexing` estimates impact without embeddings or storage writes; callers must obtain approval before `index_documents(..., rebuild=True)`.

**Sparse vectors (ADR-010, ADR-020):** indexing attaches a constant sparse placeholder until a future sparse indexing plan provides per-chunk BGE-M3 sparse vectors. A full reindex with caller approval will be required when that migration occurs.

---

## Knowledge MCP Handler Layer

Plan 10 delivers the knowledge-access boundary as typed handler functions and Pydantic schemas — not MCP SDK transport (deferred to a future plan per ADR-034). Plan 12 connects the agent to handlers via in-process tool adapters. Tier 2 repository-browse tools (`get_document`, `get_statistics`) are deferred to a follow-up plan.

```text
LangGraph Agent tool adapters     ← Plan 12
    ↓
Knowledge MCP handlers            ← Plan 10
    ↓
┌─────────────────────┬──────────────────────┐
│ Retriever.retrieve  │ IndexingPipeline     │
│ (RerankRetriever)   │ preview / index      │
└─────────┬───────────┴──────────┬───────────┘
          ↓                      ↓
   retrieval layer         indexing layer
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `McpServerSettings` (handler defaults such as `default_top_k`) |
| `schemas.py` | Pydantic request/response models only (ADR-033) |
| `exceptions.py` | `ApprovalRequiredError`, stable error codes |
| `formatting.py` | Core domain types → Pydantic DTOs |
| `tools.py` | Tier 1 handlers: `search_documents`, `index_documents_preview`, `index_documents_apply` |
| `resources.py` | Deferred MCP resource URI documentation |
| `server.py` | Deferred MCP SDK registration stub (future MCP SDK transport plan) |

**Tier 1 handlers:**

| Handler | Delegates to | Notes |
| ------- | ------------ | ----- |
| `search_documents` | `Retriever.retrieve(SearchQuery)` | Returns ranked evidence with citations; does not generate answers |
| `index_documents_preview` | `IndexingPipeline.preview_indexing` | Never mutates storage |
| `index_documents_apply` | `IndexingPipeline.index_documents` | Requires `approval_confirmed=True` (ADR-030) |

**Dependency rule (ADR-032):** `mcp_server` production code may depend on `core`, `retrieval.protocol.Retriever`, and `indexing.pipeline.IndexingPipeline` / `IndexingResult` only. It must not import `storage`, `qdrant_client`, concrete retrieval internals, LlamaIndex, LangGraph, OpenAI, `llm/`, or the MCP SDK.

**Production retriever wiring:** inject composed `RerankRetriever(FusionRetriever(...), StubReranker(), ...)` from outside `mcp_server` (CLI bootstrap, `agent/wiring.py`, test fixtures).

**Source attribution path (ADR-031):** storage populates `SearchResult.source` from Qdrant payloads at search time via `payload_to_source_reference`. Reranking preserves `source` when rescoring. MCP maps `SearchResult.source` → `SourceReferenceSchema` in `formatting.py` without importing `storage`.

**Score semantics:** `search_documents` passes through `SearchResult.score` unchanged. When production wiring uses `RerankRetriever`, scores are reranker relevance scores (ADR-026) — not comparable to dense, sparse, or RRF scores.

See [ADR-028](DECISIONS.md#adr-028-mcp-server-as-knowledge-boundary) through [ADR-034](DECISIONS.md#adr-034-mcp-handler-layer-without-sdk-runtime).

---

## LLM Boundary

Plan 11 delivers the OpenAI-compatible model invocation layer in `knowledge_assistant.llm`. The LangGraph agent (Plan 12) is the primary consumer; the layer does not assemble RAG prompts, execute tools, or call retrieval, indexing, MCP, or storage.

```text
LangGraph Agent (Plan 12 — completed)
    ↓
LLMClient.chat(messages, settings?, tools?)
    ↓
OpenAICompatibleLLMClient
    ↓
POST {base_url}/chat/completions
    ↓
vLLM / OpenAI / LiteLLM / Open WebUI / other gateway
```

| Module | Responsibility |
| ------ | -------------- |
| `protocol.py` | `LLMClient` chat protocol |
| `messages.py` | `ChatMessage`, `ChatRole`, `ToolDefinition`, `ToolCall`, `GenerationResult`, `TokenUsage` |
| `config.py` | `LlmSettings`, `GenerationSettings`, `from_env()` loader |
| `exceptions.py` | `LLMError` hierarchy |
| `openai_client.py` | `OpenAICompatibleLLMClient` (httpx transport) |
| `stub_client.py` | `StubLLMClient` for deterministic tests |

**Protocol:** sync, chat-first, non-streaming. Callers pass an immutable `messages` tuple; the client does not mutate conversation state. Optional `GenerationSettings` merge with `LlmSettings` defaults per call. `tools=()` omits the tools key from the provider request.

**Tool-call transport:** Plan 11 defines `ToolDefinition` and `ToolCall` DTOs only. Tool schema construction, MCP handler dispatch, and tool execution loops belong to the agent (`knowledge_assistant.agent`, Plan 12).

**Configuration:** copy `.env.example` → `.env` and set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and optional generation defaults. `LlmSettings.from_env()` reads `LLM_*` variables; tests construct settings explicitly.

**Embeddings and reranking (ADR-013, ADR-027, ADR-041):** `llm/` must not implement embeddings, sparse vectors, or reranking. Write-path embeddings belong to indexing; query-path embeddings and cross-encoder reranking belong to retrieval.

**Dependency rule:** only `agent` and `cli` may import `llm/` in the documented architecture. `mcp_server`, `retrieval`, `indexing`, and `storage` must not import `llm/`. Production code in `llm/` depends on the Python standard library, `httpx` (confined to `openai_client.py`), and internal `knowledge_assistant.llm` modules only.

See [ADR-035](DECISIONS.md#adr-035-openai-compatible-api-standard) through [ADR-041](DECISIONS.md#adr-041-embeddings-and-reranking-remain-outside-llm).

---

## Agent Layer

Plan 12 delivers LangGraph-based conversational orchestration in `knowledge_assistant.agent`. See [Plan 12](plans/completed/12-langgraph-agent.md) for graph topology, tool registry design, and dependency rules. ADR-042 through ADR-046 are documented in the completed plan pending acceptance into `docs/DECISIONS.md`.

```text
User message
    ↓
run_turn → LangGraph StateGraph
    ↓
agent_node → LLMClient.chat(..., tools=registry.definitions())
    ↓
should_continue → tool_node (MCP handler adapters) → agent_node → END
```

| Module | Responsibility |
| ------ | -------------- |
| `state.py` | `AgentState`, `GraphState`, reducers |
| `graph.py` | `build_agent_graph`, `run_turn`, node functions |
| `tools.py` | `ToolRegistry`, `AgentTool` protocol, dispatch |
| `wiring.py` | Tier 1 MCP tool adapters and `build_default_tool_registry` |
| `prompts.py` | RAG system prompt and citation contract |
| `config.py` | `AgentSettings` |
| `exceptions.py` | Agent error hierarchy |

**Dependency rule:** agent core must not import `storage`, concrete retrieval/indexing internals, OpenAI SDK, httpx, LlamaIndex, or MCP SDK. Knowledge access goes through MCP handler adapters in `wiring.py`.

---

## Evaluation Layer

Plan 13 delivers retrieval-quality evaluation in `knowledge_assistant.evaluation`. The layer measures ranked retrieval output against a committed benchmark — without evaluating LLM answers, agent behavior, or MCP integration. See [Plan 13](plans/completed/13-evaluation-framework.md) and ADR-047 through ADR-050.

```text
EvaluationDataset                          ← data/evaluation/
        ↓
EvaluationRunner.run(retriever, ...)       ← repeated per retrieval strategy
        ↓
Retriever.retrieve(SearchQuery)            ← any Retriever implementation
        ↓
RetrievalResult
        ↓
Metrics (Recall@K, Hit Rate@K, MRR)
        ↓
EvaluationReport                           ← one per strategy
        ↓
compare_evaluation_reports(...)            ← side-by-side strategy comparison
        ↓
ComparisonReport
```

| Module | Responsibility |
| ------ | -------------- |
| `dataset.py` | `EvaluationCase`, `DocumentRegistry`, `EvaluationDataset`, JSON loader, path normalization |
| `settings.py` | `EvaluationSettings` with metric `@K` cutoffs and `eval_top_k` |
| `metrics.py` | Pure functions: Hit Rate@K, Recall@K, MRR |
| `runner.py` | `EvaluationRunner` orchestrating `Retriever.retrieve` over benchmark cases |
| `report.py` | `EvaluationReport`, `ComparisonReport`, comparison assembly, text formatters |
| `exceptions.py` | `EvaluationError`, `EvaluationDatasetError` |

**Benchmark ownership (ADR-048):** committed retrieval benchmark JSON lives under `data/evaluation/`. Unit tests use minimal fixtures under `tests/unit/evaluation/fixtures/` only — not the production benchmark.

**Metric semantics (ADR-049):** relevance matching uses normalized `SearchResult.source.document_path` against registry-resolved expected paths. NDCG is deferred.

**Evaluation target (ADR-050):** `EvaluationRunner` accepts any structurally compatible `Retriever`; concrete retriever wiring lives outside `evaluation/` production modules (bootstrap strategy assembly per ADR-068; CLI orchestration per ADR-067).

**Execution workflow (Plan 18, ADR-067):** offline retrieval evaluation is orchestrated by `cli/evaluate.py` — not by `evaluation/` production modules, MCP, or the agent:

```text
BootstrapSettings.from_env()
        ↓
build_demo_environment()
        ↓
build_retriever_for_strategy(env, strategy)    ← bootstrap/retrievers.py
        ↓
load_evaluation_dataset(...)
        ↓
EvaluationRunner.run(retriever, ...)
        ↓
format_evaluation_report / compare_evaluation_reports
```

**Dependency rule:** evaluation production code may depend on `knowledge_assistant.core`, `knowledge_assistant.retrieval.protocol.Retriever`, and the Python standard library only. It must not import `storage`, `indexing`, `mcp_server`, `llm`, `agent`, LangGraph, LlamaIndex, or concrete retrieval orchestrators. `retrieval/` production code must not import `evaluation/`.

---

## Bootstrap Layer

Plan 15 delivers the demo composition root in `knowledge_assistant.bootstrap`. Bootstrap assembles storage, indexing, and the canonical retrieval stack for demo workflows. It contains dependency assembly only — no CLI parsing, MCP handlers, agent logic, or evaluation metrics.

```text
BootstrapSettings.from_env()
        ↓
create_qdrant_vector_store(StorageSettings)
        ↓
embedding_mode=stub → StubEmbeddingProvider + StubQueryEmbeddingProvider
embedding_mode=real → shared BgeM3 runtime → BgeM3* providers
        ↓
IndexingPipeline + DenseRetriever + SparseRetriever
        ↓
FusionRetriever
        ↓
StubReranker or BgeReranker + RerankRetriever
        ↓
DemoEnvironment (+ cached RetrievalStack)
        ↓
build_retriever_for_strategy(env, strategy)   ← Plan 18 (dense/sparse/fusion/rerank)
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `BootstrapSettings` — corpus root, Qdrant URL, collection name, vector dimensions, `embedding_mode`, reranker mode/settings |
| `environment.py` | `DemoEnvironment`, `build_demo_environment()`, corpus/collection status helpers, pipeline label |
| `retrievers.py` | `RetrievalStrategy`, `RetrievalStack`, `build_retrieval_stack()`, `build_retriever_for_strategy()` |

**Canonical demo retrieval pipeline (ADR-053, ADR-065):** `RerankRetriever(FusionRetriever(DenseRetriever, SparseRetriever), reranker)` where dense providers are stub or real BGE-M3 (Plan 16) and `reranker` is `StubReranker()` by default or `BgeReranker` when `RAG_RERANKER_MODE=real`. `rag demo info` reports embedding and reranker modes in the pipeline label without triggering model loading.

**Dense embedding migration (ADR-058):** switching `RAG_EMBEDDING_MODE` between stub and real requires `rag demo load --rebuild --approve`.

**`VectorStore.count_points()` (Plan 15):** read-only cardinality via Qdrant collection metadata (`points_count`); returns `0` when the collection does not exist. Primary consumer is `rag demo info`.

**Corpus discovery:** `DemoEnvironment.corpus_document_count()` uses the same file discovery rules as `IndexingPipeline` — all supported `.md`/`.txt` files under the corpus root, including `README.md`. Counting and indexing semantics are identical.

**`BootstrapSettings.dense_vector_size`:** read-only view of `storage_settings.dense_vector_size`; indexing and retrieval settings derive from this single source of truth.

**Dependency rule:** bootstrap may import `storage`, `indexing`, `embeddings`, the public `retrieval` package API, and `core`. It must not import `cli`, `agent`, `mcp_server`, `llm`, `evaluation`, `qdrant_client`, LangGraph, MCP SDK, `torch`, or FlagEmbedding directly. Retrieval orchestrators must be imported from `knowledge_assistant.retrieval`, not internal retrieval submodules.

**Consumers:** `cli` (demo and evaluate commands), tests, and future `rag chat` wiring. Bootstrap complements but does not replace `agent/wiring.py` MCP adapters.

See [ADR-051](DECISIONS.md#adr-051-demo-bootstrap-composition-root) through [ADR-070](DECISIONS.md#adr-070-real-model-benchmark-expectations).

---

## CLI Demo Commands

Plan 15 delivers operator-facing demo orchestration in `knowledge_assistant.cli`. The `rag` entrypoint exposes `demo info`, `demo load`, and `demo reset`. CLI owns argument parsing, stdout formatting, exit codes, and approval flag validation; all dependency construction delegates to `bootstrap`.

```text
python3 tools/knowledge_generator/generator.py   ← Plan 14 (corpus generation)
        ↓
rag demo info                                    ← read-only status
        ↓
rag demo load                                    ← index canonical knowledge/ corpus
        ↓
(index ready)
        ↓
rag evaluate run / compare                       ← Plan 18
rag chat                                         ← Plan 19
```

| Command | Purpose | Mutations |
| ------- | ------- | --------- |
| `rag demo info` | Corpus and collection status, retrieval pipeline label | None |
| `rag demo load` | Index `knowledge/` via `IndexingPipeline` | Creates or rebuilds Qdrant collection |
| `rag demo reset` | Delete demo Qdrant collection | Deletes collection (`--approve` required) |

**Approval gates (ADR-054):** `demo load` refuses to modify an existing collection unless both `--rebuild` and `--approve` are supplied. `demo reset` requires `--approve` on every invocation. CLI uses non-interactive flags only (no `input()` prompts).

**Dependency rule:** `cli/demo.py` may import `knowledge_assistant.bootstrap` and the Python standard library only. `cli/demo.py` must not import `evaluation`.

See [ADR-052](DECISIONS.md#adr-052-cli-owns-demo-orchestration).

---

## CLI Evaluate Commands

Plan 18 delivers retrieval strategy evaluation orchestration in `knowledge_assistant.cli.evaluate`. The `rag` entrypoint exposes `evaluate run` and `evaluate compare`. Evaluate commands validate prerequisites, assemble strategy retrievers via bootstrap, invoke Plan 13 evaluation APIs, and render reports to stdout.

```text
rag evaluate run --strategy {dense,sparse,fusion,rerank}
        ↓
build_demo_environment()
        ↓
validate dataset + non-empty collection
        ↓
build_retriever_for_strategy(env, strategy)
        ↓
EvaluationRunner.run(...)
        ↓
configuration banner + format_evaluation_report

rag evaluate compare
        ↓
(same prerequisites, once)
        ↓
for strategy in CANONICAL_STRATEGIES: EvaluationRunner.run(...)
        ↓
compare_evaluation_reports(...)
        ↓
configuration banner + format_comparison_report
```

| Command | Purpose | Mutations |
| ------- | ------- | --------- |
| `rag evaluate run` | Evaluate one canonical strategy against the benchmark | None (read-only on index and benchmark JSON) |
| `rag evaluate compare` | Evaluate all four strategies and print side-by-side comparison | None |

**Prerequisites:** corpus indexed via `rag demo load`; benchmark dataset exists (default `data/evaluation/retrieval_benchmark_v1.json`). Empty or missing collection fails with exit code `3` and directs the operator to `rag demo load`.

**Provider modes (ADR-070):** evaluate inherits `RAG_EMBEDDING_MODE` and `RAG_RERANKER_MODE` from bootstrap. Stub modes run successfully but are not authoritative for model-quality benchmark claims; meaningful results require real embeddings and a corpus reindexed with those embeddings.

**Exit codes:** `0` success; `1` operational failure; `2` usage/settings error; `3` precondition failure (missing dataset or empty collection).

**Dependency rule:** `cli/evaluate.py` may import `knowledge_assistant.bootstrap`, `knowledge_assistant.evaluation`, and the Python standard library only. `cli/main.py` imports `cli.demo` and `cli.evaluate` only. Evaluate must not import `storage`, `indexing`, concrete `retrieval`, `qdrant_client`, `agent`, `mcp_server`, or `llm`.

See [ADR-067](DECISIONS.md#adr-067-retrieval-evaluation-execution-ownership) through [ADR-070](DECISIONS.md#adr-070-real-model-benchmark-expectations).

---

## Source Layout

```text
src/knowledge_assistant/
    core/           # shared domain types, IDs, validation
    agent/          # LangGraph agent and graph definitions
    mcp_server/     # Knowledge MCP server
    retrieval/      # hybrid retrieval, fusion, reranking
    indexing/       # LlamaIndex ingestion and chunking
    llm/            # OpenAI-compatible LLM boundary
    storage/        # Qdrant integration
    evaluation/     # retrieval benchmark evaluation and strategy comparison
    bootstrap/      # demo composition root (storage + indexing + retrieval wiring)
    cli/            # CLI entrypoints (rag demo and evaluate commands)
```

---

## Human-in-the-Loop

Potentially destructive indexing operations require explicit user approval.

Examples:

* index rebuild;
* reindexing;
* index replacement.

---

## Source Attribution

All knowledge answers must be grounded in retrieved content.

The system exposes:

* document title;
* document path;
* section title;
* line range.

`SourceReference` is the canonical citation model. Storage populates `SearchResult.source` at search time (ADR-031). MCP maps `source` to `SourceReferenceSchema` for tool responses. `ChunkMetadata` intentionally holds structural fields only — bibliographic fields are not duplicated on chunk metadata.

---

## Documentation Precedence

When sources conflict:

1. PROJECT.md
2. docs/ARCHITECTURE.md
3. docs/DECISIONS.md
4. docs/plans/active/
5. docs/PROGRESS.md
6. Chat Context
