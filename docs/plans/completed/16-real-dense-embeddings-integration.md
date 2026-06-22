# Plan 16 — Real Dense Embeddings Integration

**Status:** Completed

**Created:** 2026-06-22

**Roadmap:** Phase 11 — Real Embeddings Integration

**Depends on:**

* [Plan 05 — Indexing Pipeline](../completed/05-indexing-pipeline.md)
* [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)
* [Plan 11 — LLM Boundary](../completed/11-llm-boundary.md)
* [Plan 13 — Evaluation Framework](../completed/13-evaluation-framework.md)
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md)

**Plan principle:** One plan introduces one architectural capability. Plan 16 introduces **real BGE-M3 dense embedding runtime** for indexing and retrieval query paths only. It does **not** change retrieval algorithms, sparse paths, reranking, MCP, agent, LLM, evaluation framework code, or CLI command surface beyond bootstrap provider selection.

---

## Authorization

**Active.** ADR-055 through ADR-060 recorded in `docs/DECISIONS.md` on implementation completion.

---

## Objective

Replace stub dense embedding providers with a real **BAAI/bge-m3** model runtime while preserving ADR-013 embedding boundary ownership and all existing retrieval orchestration.

```text
Indexing write path:
    Chunk texts
        ↓
EmbeddingProvider (BgeM3EmbeddingProvider)
        ↓
DenseEmbeddingRuntime.embed_passages(...)
        ↓
VectorStore.upsert_chunks

Retrieval query path:
    SearchQuery.text
        ↓
QueryEmbeddingProvider (BgeM3QueryEmbeddingProvider)
        ↓
DenseEmbeddingRuntime.embed_query(...)
        ↓
DenseRetriever → VectorStore.search_dense
```

After this plan is complete:

* indexing generates **real dense vectors** for document chunks via `EmbeddingProvider`;
* retrieval generates **real dense query vectors** via `QueryEmbeddingProvider`;
* a reusable **`knowledge_assistant.embeddings`** package owns BGE-M3 model loading and inference;
* bootstrap selects real providers for demo wiring when configured;
* operators can **reindex** the canonical corpus with human approval after switching from stub-indexed collections;
* Plan 13 evaluation can compare stub vs real embedding quality **without evaluation code changes** — by wiring different bootstrap environments and indexed corpora.

**Dependency rule:** model runtime dependencies (`FlagEmbedding`, `torch`) are confined to `knowledge_assistant.embeddings`. Indexing and retrieval depend on thin layer adapters and shared runtime interfaces — not on `torch` or `transformers` directly in production modules outside `embeddings/`.

**ADR-013 guardrail:** write-path and query-path **protocol ownership** remain in `indexing/` and `retrieval/` respectively. Shared model execution does not collapse those boundaries.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/embeddings/` | BGE-M3 runtime, settings, exceptions, factory |
| `src/knowledge_assistant/indexing/embeddings.py` | `BgeM3EmbeddingProvider` adapter implementing `EmbeddingProvider` |
| `src/knowledge_assistant/retrieval/embeddings.py` | `BgeM3QueryEmbeddingProvider` adapter implementing `QueryEmbeddingProvider` |
| `src/knowledge_assistant/bootstrap/` | Shared runtime construction; real vs stub provider selection |
| `tests/unit/embeddings/` | Runtime unit tests with mocked model backend |
| `tests/unit/indexing/` | Adapter tests for write-path provider |
| `tests/unit/retrieval/` | Adapter tests for query-path provider |
| `tests/unit/bootstrap/` | Bootstrap wiring tests for real provider mode |
| `tests/integration/embeddings/` | Optional real-model smoke tests (marked, not required in default CI) |
| `tests/integration/indexing/` | Real-embedding indexing integration (optional / marked) |
| `tests/integration/retrieval/` | Real-embedding dense retrieval integration (optional / marked) |
| `docs/ARCHITECTURE.md` | Embeddings layer section |
| `docs/DECISIONS.md` | ADR-055 through ADR-060 |
| `docs/PROGRESS.md` | Plan 16 completion entry |
| `README.md` | Real embedding setup notes (model download, device, reindex) |
| `.env.example` | Optional `RAG_EMBEDDING_*` variables |
| `pyproject.toml` | Approved model runtime dependencies |

### In Scope

* dedicated `embeddings/` package with `DenseEmbeddingRuntime` abstraction;
* `EmbeddingRuntimeSettings` (model name, device, batch size, normalization, max sequence length);
* `BgeM3EmbeddingProvider` in indexing implementing existing `EmbeddingProvider` protocol;
* `BgeM3QueryEmbeddingProvider` in retrieval implementing existing `QueryEmbeddingProvider` protocol;
* BGE-M3 **query vs passage** encoding modes (distinct inference paths);
* L2 normalization aligned with Qdrant `COSINE` distance (ADR-004);
* dimension validation: runtime output dimension must equal configured `dense_vector_size` (default `1024` for Plan 16 default model `BAAI/bge-m3`);
* bootstrap factory creates **one shared runtime instance** per `DemoEnvironment`;
* bootstrap provider mode: stub (default) vs real (opt-in via settings/env);
* `rag demo info` reports embedding provider mode in pipeline label;
* reindex workflow documentation and operator guidance (`demo load --rebuild --approve`);
* evaluation workflow documentation for stub vs real comparison using Plan 13 APIs unchanged;
* import-boundary tests for `embeddings/`, `indexing/`, `retrieval/`, and `bootstrap/`;
* `StubEmbeddingProvider` and `StubQueryEmbeddingProvider` remain available for tests and CI;
* ADR-055 through ADR-060.

---

## Non-Scope

Plan 16 does **not** authorize:

* BGE-M3 **sparse** vector generation (indexing write path);
* BGE-M3 **sparse query** embeddings (retrieval read path);
* replacement of `StubSparseQueryEmbeddingProvider` or sparse placeholder indexing (ADR-010);
* BM25 changes;
* `FusionRetriever`, `SparseRetriever`, `RerankRetriever`, fusion math, or reranker changes;
* `BAAI/bge-reranker-v2-m3` cross-encoder runtime (Plan 17);
* MCP handler, schema, or transport changes;
* LangGraph agent or `agent/wiring.py` changes;
* `llm/` changes;
* chat CLI (`rag chat`, Plan 19);
* evaluation framework redesign or benchmark changes (`data/evaluation/`);
* `rag evaluate` CLI subcommand (Plan 18);
* retrieval algorithm changes (`DenseRetriever` orchestration shape unchanged);
* `VectorStore` protocol or Qdrant collection schema changes;
* `core/` domain model changes;
* Docker Compose, GPU orchestration, or model serving infrastructure;
* async embedding APIs;
* embedding cache persistence (Redis, disk cache, Qdrant-side generation);
* changes to chunking, ID generation, or source attribution;
* automatic silent reindex on provider switch;
* `AppError`-rooted exception hierarchy (deferred).

---

## Architectural Decisions (Proposed ADRs)

### ADR-055 — Dedicated Embeddings Package for Shared BGE-M3 Runtime

**Status:** Proposed

#### Context

ADR-013 assigns write-path embedding ownership to indexing and query-path ownership to retrieval. ADR-015 forbids retrieval from importing indexing `EmbeddingProvider`. ADR-041 forbids `llm/` from owning embeddings. Plan 16 must load **one** BGE-M3 model used by both paths without violating layer boundaries or duplicating `torch` imports across indexing and retrieval.

#### Decision

* Introduce `knowledge_assistant.embeddings` as the **shared dense embedding runtime** package.
* The package owns:
  * `DenseEmbeddingRuntime` — stable protocol for dense embedding inference;
  * `BgeM3FlagEmbeddingRuntime` — Plan 16 default implementation (see ADR-056);
  * `EmbeddingRuntimeSettings` and environment loading;
  * embedding-specific exceptions.
* **Indexing** implements `BgeM3EmbeddingProvider(EmbeddingProvider)` in `indexing/embeddings.py` — a thin adapter delegating `embed_texts` → `runtime.embed_passages`.
* **Retrieval** implements `BgeM3QueryEmbeddingProvider(QueryEmbeddingProvider)` in `retrieval/embeddings.py` — a thin adapter delegating `embed_query` → `runtime.embed_query`.
* Layer protocols (`EmbeddingProvider`, `QueryEmbeddingProvider`) **remain** in their owning packages per ADR-013 and ADR-015.
* `embeddings/` must not import `indexing`, `retrieval`, `storage`, `mcp_server`, `agent`, `llm`, or `evaluation`.
* `llm/` must not implement or import embedding runtime code (reinforces ADR-041).

#### Consequences

* One model load path; no cross-layer protocol reuse violation.
* `torch` / `FlagEmbedding` imports are localized to `embeddings/`.
* Future sparse embedding runtime (separate plan) may extend `embeddings/` or add a sibling module without changing Plan 16 dense contracts.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Runtime only in `indexing/` | Violates ADR-013 query-path ownership; forces retrieval → indexing import |
| Runtime only in `retrieval/` | Violates ADR-013 write-path ownership; forces indexing → retrieval import (forbidden dependency direction) |
| Runtime in `llm/` | Violates ADR-013 and ADR-041; embeddings are not chat-completions inference |
| Duplicate model instances in indexing and retrieval with no shared package | Doubles memory; duplicates `torch` wiring; error-prone configuration drift |
| Shared `EmbeddingProvider` reused for queries | Violates ADR-015; blurs write/read path contracts |

---

### ADR-056 — BGE-M3 Default Runtime Implementation (FlagEmbedding)

**Status:** Proposed

#### Context

Plan 16 must introduce real `BAAI/bge-m3` dense vectors (1024-dim) with **distinct query vs passage encoding** for retrieval quality. The project technology stack names BGE-M3 explicitly in `PROJECT.md`. The stable project contract must not be locked to a single third-party library — indexing and retrieval depend on `DenseEmbeddingRuntime`, not on inference backends.

#### Decision

* **`DenseEmbeddingRuntime`** is the stable project abstraction (protocol). It defines `embed_passages(texts)` and `embed_query(text)` only. Indexing and retrieval adapters depend on this protocol — never on FlagEmbedding, `torch`, or other backends.
* **`BgeM3FlagEmbeddingRuntime`** is the Plan 16 default concrete implementation of `DenseEmbeddingRuntime`. It uses **FlagEmbedding** (`BGEM3FlagModel` or successor API) internally; FlagEmbedding is an implementation detail confined to `embeddings/runtime.py`.
* Architecture:

```text
DenseEmbeddingRuntime          ← stable contract (indexing/retrieval depend on this)
        ↑
BgeM3FlagEmbeddingRuntime      ← Plan 16 default implementation
        ↑
FlagEmbedding / torch          ← implementation detail; not a project contract
```

* Dense-only inference in `BgeM3FlagEmbeddingRuntime`:
  * passage / document chunks: `encode` (or equivalent) with **passage** mode → `dense_vecs`;
  * search queries: `encode_queries` (or equivalent) with **query** mode → `dense_vecs`.
* Do **not** request sparse vectors from the runtime in Plan 16.
* `create_dense_embedding_runtime(settings)` returns `DenseEmbeddingRuntime`. Plan 16 factory selects `BgeM3FlagEmbeddingRuntime` when real mode is enabled.
* **Future plans** may introduce alternative `DenseEmbeddingRuntime` implementations (e.g. ONNX, different BGE loader) without changing `EmbeddingProvider`, `QueryEmbeddingProvider`, indexing, or retrieval contracts.
* Plan 16 adds runtime dependencies to `pyproject.toml` for the default implementation only:
  * `FlagEmbedding` (pulls compatible `torch`);
  * pin minimum versions in implementation; document GPU vs CPU install notes in `README.md`.

#### Consequences

* Indexing and retrieval remain backend-agnostic; only `embeddings/` imports FlagEmbedding.
* Encoding behavior of the default implementation matches BAAI reference semantics for hybrid-ready BGE-M3.
* Heavier dependencies appear for the first time; CI default remains stub providers.
* Operators need one-time model download from Hugging Face on first real run.
* Backend swaps are localized to `embeddings/` factory and runtime module.

#### Alternatives Considered

| Alternative | Why rejected as architectural contract |
| ----------- | -------------------------------------- |
| FlagEmbedding as the project abstraction | Couples all layers to one library; blocks future backend swaps without contract churn |
| SentenceTransformers as default implementation | Viable alternative implementation, not selected for Plan 16 default — less precise BGE-M3 query/passage APIs |
| Raw Transformers as default implementation | High implementation cost; easy to get query/passage prefixes wrong |
| ONNX / external embedding server as Plan 16 default | Infrastructure scope expansion; deferred (see Design Evaluation 8) |
| LlamaIndex embedding wrappers | Violates ADR-007 containment; couples embedding runtime to ingestion library |

---

### ADR-057 — Bootstrap-Owned Shared Embedding Runtime

**Status:** Proposed

#### Context

Indexing and retrieval both require the same BGE-M3 weights. Plan 15 established `bootstrap` as the demo composition root (ADR-051). Without explicit shared-runtime ownership, CLI, tests, and future `rag evaluate` wiring could each construct independent model instances.

#### Decision

* **Bootstrap owns shared runtime construction** for demo and integration wiring.
* `build_demo_environment()` (or extracted helper `build_dense_embedding_runtime(...)`) creates **one** `DenseEmbeddingRuntime` per assembled `DemoEnvironment` when real embeddings are enabled.
* The same runtime instance is injected into:
  * `BgeM3EmbeddingProvider(runtime=...)` → `IndexingPipeline`;
  * `BgeM3QueryEmbeddingProvider(runtime=...)` → `DenseRetriever`.
* Default mode remains **stub providers** (ADR-053 compatibility for CI and fast tests).
* Real mode is opt-in via `BootstrapSettings` / environment (e.g. `RAG_EMBEDDING_MODE=real`).
* Process-local reuse: bootstrap may use `@functools.cache` on runtime factory keyed by `EmbeddingRuntimeSettings` fingerprint — optional optimization, not a global service.
* Bootstrap must not import `FlagEmbedding` or `torch` directly; it imports `knowledge_assistant.embeddings` factories only.

#### Consequences

* Single model load per demo environment assembly.
* Plans 17–18 change provider selection in one place.
* Unit tests continue injecting stub providers without loading models.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate model instance per layer | 2× memory; risk of inconsistent settings |
| Global module-level singleton without bootstrap | Hidden mutable state; harder to test; unclear ownership |
| Indexing owns runtime; retrieval borrows via indexing import | Violates indexing ↔ retrieval independence and ADR-013 |
| MCP server owns runtime | Violates ADR-032; MCP must not own embedding inference |
| Separate embedding microservice | Out of project scope per `PROJECT.md` non-goals |

---

### ADR-058 — Dense Embedding Migration Requires Full Reindex

**Status:** Proposed

#### Context

Existing collections may be indexed with `StubEmbeddingProvider` (hash-based vectors). Real BGE-M3 vectors occupy the same `dense` slot (ADR-004) but are semantically incompatible with stub vectors. Query vectors from real BGE-M3 will not align with stub-indexed passages.

#### Decision

* Switching dense embedding provider from **stub → real** (or real → stub) requires a **full collection rebuild and reindex** with caller approval.
* Recovery path: `rag demo load --rebuild --approve` (or equivalent `index_documents(..., rebuild=True)` with `approval_confirmed=True` at MCP layer).
* **No in-place dense vector migration** or partial chunk re-embedding in Plan 16.
* **Compatibility assumptions:**
  * configured `dense_vector_size` must match runtime output dimension across storage, indexing, and retrieval;
  * default `dense_vector_size` remains `1024` because Plan 16 default model is `BAAI/bge-m3`;
  * `BgeM3FlagEmbeddingRuntime` with default model is expected to produce 1024-dimensional dense vectors;
  * collection schema unchanged (named `dense` + `sparse` vectors);
  * sparse slot continues ADR-010 placeholder — unaffected by Plan 16;
  * chunk IDs and payloads may be identical after reindex if corpus and chunking settings unchanged (ADR-008), but **dense vectors must be regenerated**.
* `rag demo info` (or bootstrap status helper) should report current embedding mode so operators detect stub/real mismatch risk.
* Mixing stub-indexed dense vectors with real query embeddings (or vice versa) is **unsupported** — behavior is undefined; documentation must warn operators.

#### Consequences

* Operators must plan a reindex window when enabling real embeddings.
* Lecture demo flow: generate corpus → `demo load` with real mode → evaluate/chat on real-indexed collection.
* Plan 18 meaningful evaluation requires real-indexed corpus (Phase 13 note in ROADMAP).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Lazy re-embed on first query | Violates human-in-the-loop; unpredictable latency |
| Dual collections (stub + real) | Operational complexity; out of educational scope |
| Automatic rebuild on mode switch | Violates ADR-054 explicit approval |
| Store embedding provider version in Qdrant payload | Schema expansion; deferred — operator discipline sufficient for v1 |

---

### ADR-059 — Dense Vector Normalization and Dimension Contract

**Status:** Proposed

#### Context

Qdrant dense search uses `COSINE` distance (ADR-004). Stub providers L2-normalize vectors (ADR-009, ADR-016). Real model runtimes may return unnormalized vectors depending on API flags. Dimension mismatches must fail fast at layer boundaries. Plan 16 default model is `BAAI/bge-m3` (1024-dim dense output), but the architectural contract is compatibility with configured `dense_vector_size` — not a universal 1024 invariant.

#### Decision

* **Output dimension contract:** every `DenseEmbeddingRuntime` implementation must produce vectors whose length equals the configured `dense_vector_size`. The runtime validates `len(vector) == settings.dense_vector_size` before returning each vector.
* **Default expectation:** default `dense_vector_size` remains **1024** across `StorageSettings`, `IndexingSettings`, and `DenseRetrievalSettings` because Plan 16 default model is `BAAI/bge-m3`.
* **Plan 16 default implementation:** `BgeM3FlagEmbeddingRuntime` with default `model_name=BAAI/bge-m3` is **expected** to produce 1024-dimensional dense vectors. Dimension validation still applies — mismatch raises at runtime, not silently accepted.
* **Future implementations:** alternative `DenseEmbeddingRuntime` implementations may use different output dimensions only when `StorageSettings`, `IndexingSettings`, `DenseRetrievalSettings`, and collection schema are configured consistently for that dimension. Plan 16 does not authorize model swapping; this rule preserves long-term flexibility without adding swap support now.
* **Normalization:** runtime applies **L2 normalization** to all dense outputs when `EmbeddingRuntimeSettings.normalize_embeddings=True` (default `True`), regardless of model defaults — ensuring cosine compatibility and consistent behavior with stubs.
* **Validation chain:**
  * `DenseEmbeddingRuntime` validates `len(vector) == settings.dense_vector_size` before returning;
  * `BgeM3EmbeddingProvider` and `BgeM3QueryEmbeddingProvider` propagate runtime output unchanged;
  * existing `DenseRetriever` dimension check (`EmbeddingDimensionError`) remains the retrieval-side guard;
  * storage `VectorDimensionError` remains the persistence-side guard.
* **Configuration ownership:**
  * `EmbeddingRuntimeSettings` owns: `model_name`, `device`, `batch_size`, `max_length`, `normalize_embeddings`, and `dense_vector_size` (supplied from `StorageSettings` at bootstrap assembly — not an independent runtime override);
  * `batch_size` applies **only** to passage/document embedding via `embed_passages`; query embedding via `embed_query` always processes a **single query** — no configurable query batching in Plan 16;
  * `BootstrapSettings` aggregates embedding mode + delegates `dense_vector_size` from `StorageSettings` (unchanged single source per Plan 15);
  * indexing/retrieval settings do **not** duplicate model name, device, or batch size — they receive ready providers from bootstrap.

#### Consequences

* Predictable cosine behavior in Qdrant when all layers share one `dense_vector_size`.
* Misconfigured model/runtime dimension pairing fails at runtime construction or first embed, not silently at search time.
* Tests can use small `dense_vector_size` with stub providers; real `BgeM3FlagEmbeddingRuntime` smoke tests use configured `dense_vector_size` (default 1024).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Trust model-native normalization only | Provider/version drift risk; stub vs real behavioral mismatch |
| Normalize in storage | Violates ADR-006 passive storage boundary |
| Normalize separately in indexing and retrieval | Duplicated logic; inconsistent if one path omits it |
| Hard-code `dense_vector_size == 1024` for all real-mode runtimes | Too rigid; blocks future `DenseEmbeddingRuntime` implementations with different dimensions |
| Omit runtime dimension validation | Allows silent vector/schema mismatch; weakens fail-fast guarantees |

---

### ADR-060 — Stub Providers Remain Default for CI and Fast Tests

**Status:** Proposed

#### Context

Real BGE-M3 introduces `torch`, large downloads, and variable runtime. CI and unit tests must remain fast and deterministic. Plan 15 mandated stub providers until Plan 16 (ADR-053).

#### Decision

* `StubEmbeddingProvider` and `StubQueryEmbeddingProvider` **remain** in the codebase.
* Default `build_demo_environment()` uses **stub** providers unless explicitly configured for real embeddings.
* Default `pytest` invocation must pass **without** downloading models or requiring GPU.
* Real-model tests are opt-in via pytest marker (e.g. `@pytest.mark.embedding_model`) excluded from default CI.
* `rag demo info` pipeline label distinguishes modes, e.g.:
  * stub: `dense + sparse → fusion (RRF) → rerank (stub embeddings)`
  * real: `dense (bge-m3) + sparse → fusion (RRF) → rerank (stub embeddings)`

#### Consequences

* CI validation suite stays lightweight.
* Operators opt into real embeddings deliberately.
* Plan 18 documents that meaningful benchmark numbers require real mode + reindexed corpus.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Real embeddings as default everywhere | Breaks CI; forces model download on every dev machine |
| Remove stub providers after Plan 16 | Loses fast deterministic tests; violates incremental migration |
| Mock only; no real smoke test | Insufficient confidence in default `BgeM3FlagEmbeddingRuntime` integration |

---

## Design Evaluations

This section records Plan 16 answers to required design questions. These are **decided** for this plan; implementation must not reopen them without a plan revision.

### 1. Embedding Runtime Location

| Location | Assessment |
| -------- | ---------- |
| `indexing/` only | **Rejected** — violates query-path ownership (ADR-013, ADR-015) |
| `retrieval/` only | **Rejected** — violates write-path ownership; wrong dependency direction |
| `llm/` | **Rejected** — violates ADR-013, ADR-036, ADR-041 |
| **`embeddings/` dedicated package** | **Selected** — shared runtime with layer-local protocol adapters |

**Package layout (justified):**

```text
src/knowledge_assistant/embeddings/
    __init__.py          # minimal public exports
    config.py            # EmbeddingRuntimeSettings
    runtime.py           # DenseEmbeddingRuntime protocol + BgeM3FlagEmbeddingRuntime
    factory.py           # create_dense_embedding_runtime(...)
    exceptions.py        # EmbeddingRuntimeError, EmbeddingDimensionMismatchError
```

Layer adapters stay in owning packages:

```text
indexing/embeddings.py     → BgeM3EmbeddingProvider
retrieval/embeddings.py    → BgeM3QueryEmbeddingProvider
```

**ADR-013 consistency:** indexing still **owns** the write-path contract; retrieval still **owns** the query-path contract. `embeddings/` owns **model execution**, not retrieval or indexing orchestration.

---

### 2. Shared Runtime

| Approach | Assessment |
| -------- | ---------- |
| Separate model instances per layer | **Rejected** — 2× memory, config drift |
| Shared runtime service (external) | **Rejected** — infrastructure scope |
| Global singleton without injection | **Rejected** — hurts testability |
| **Bootstrap-owned shared runtime, injected into both adapters** | **Selected** |

**Selected wiring:**

```text
BootstrapSettings (embedding_mode=stub|real)
        ↓
create_dense_embedding_runtime(settings)   # one instance
        ↓
┌──────────────────────────┬───────────────────────────┐
│ BgeM3EmbeddingProvider   │ BgeM3QueryEmbeddingProvider │
│ → IndexingPipeline       │ → DenseRetriever            │
└──────────────────────────┴───────────────────────────┘
```

* One `DenseEmbeddingRuntime` per `DemoEnvironment` assembly.
* Optional `@cache` on factory for repeated calls within a process.
* Tests pass `StubEmbeddingProvider` / `StubQueryEmbeddingProvider` directly — no runtime required.

---

### 3. Model Execution Strategy

The **stable contract** is `DenseEmbeddingRuntime`. Plan 16 selects a **default implementation** — not a permanent backend lock-in.

| Strategy | Assessment |
| -------- | ---------- |
| **`DenseEmbeddingRuntime` protocol** | **Selected** — stable project abstraction; indexing and retrieval depend only on this |
| **`BgeM3FlagEmbeddingRuntime` (FlagEmbedding)** | **Selected as Plan 16 default implementation** — official BGE-M3 library; native query/passage APIs; dense-only extraction straightforward |
| SentenceTransformers implementation | **Rejected for Plan 16 default** — viable future alternative `DenseEmbeddingRuntime`; less precise BGE-M3 query/passage split |
| Raw Transformers implementation | **Rejected for Plan 16 default** — high implementation risk for marginal benefit |

**Inference contract (dense only — `DenseEmbeddingRuntime`):**

```python
# Passages (indexing) — batch_size from EmbeddingRuntimeSettings applies here
runtime.embed_passages(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]

# Queries (retrieval) — always single query; no batch_size setting
runtime.embed_query(text: str) -> tuple[float, ...]
```

**Plan 16 default implementation (`BgeM3FlagEmbeddingRuntime`) maps to FlagEmbedding internally:**

* `embed_passages` → batch `encode` returning `dense_vecs` only; batches texts according to `settings.batch_size`;
* `embed_query` → `encode_queries` for one query string returning `dense_vecs` only; does not use `batch_size`;
* `return_sparse` / lexical weights disabled in Plan 16.

Indexing and retrieval must not import or reference FlagEmbedding.

---

### 4. Configuration Ownership

| Setting | Owner | Default | Notes |
| ------- | ----- | ------- | ----- |
| `model_name` | `EmbeddingRuntimeSettings` | `BAAI/bge-m3` | Hugging Face model id |
| `device` | `EmbeddingRuntimeSettings` | `cpu` | `cpu` / `cuda` / `mps` (validate at runtime) |
| `batch_size` | `EmbeddingRuntimeSettings` | `32` | **Passage path only** — `embed_passages` batching; `embed_query` always processes one query (no query batching in Plan 16) |
| `max_length` | `EmbeddingRuntimeSettings` | `8192` | BGE-M3 supports long context; tune if needed |
| `normalize_embeddings` | `EmbeddingRuntimeSettings` | `True` | L2 normalize all outputs (ADR-059) |
| `dense_vector_size` | `StorageSettings` → bootstrap → `EmbeddingRuntimeSettings` | `1024` | Default because Plan 16 default model is `BAAI/bge-m3`; runtime output must equal this value; future runtimes may use other dimensions only when all layers and collection schema are configured consistently |
| `embedding_mode` | `BootstrapSettings` | `stub` | `stub` \| `real` |

**Dimension compatibility rule:** `DenseEmbeddingRuntime` output length must equal configured `dense_vector_size`. Default is 1024. `BgeM3FlagEmbeddingRuntime` with default model is expected to satisfy this with the default setting. Plan 16 does not add model swapping — only documents that the contract is configuration-driven, not hard-coded to 1024.

**Environment variables (proposed):**

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `RAG_EMBEDDING_MODE` | `stub` | `stub` or `real` provider selection |
| `RAG_EMBEDDING_MODEL` | `BAAI/bge-m3` | Model identifier |
| `RAG_EMBEDDING_DEVICE` | `cpu` | Inference device |
| `RAG_EMBEDDING_BATCH_SIZE` | `32` | Passage batch size for `embed_passages` only (not used by query path) |
| `RAG_EMBEDDING_MAX_LENGTH` | `8192` | Tokenization limit |
| `RAG_EMBEDDING_NORMALIZE` | `true` | L2 normalization flag |

Existing `QDRANT_URL`, `RAG_CORPUS_ROOT` unchanged.

**Layer settings unchanged:** `IndexingSettings` and `DenseRetrievalSettings` keep only `dense_vector_size` — not model hyperparameters.

---

### 5. Reindex Requirements

| Scenario | Reindex required? | Approval required? |
| -------- | ----------------- | ------------------ |
| First index with real embeddings (empty collection) | No (initial load) | No |
| Replace stub-indexed collection with real embeddings | **Yes** — full rebuild | **Yes** — `--rebuild --approve` |
| Replace real-indexed collection after model/version change | **Yes** | **Yes** |
| Change `embedding_mode` without reindex | **Forbidden** — unsupported mixed state |
| Change chunking settings only | **Yes** (existing ADR-008 behavior) | **Yes** when `rebuild=True` |

**Operator workflow (real embeddings):**

```text
# 1. Enable real embeddings
export RAG_EMBEDDING_MODE=real

# 2. Inspect state
rag demo info

# 3. Reindex canonical corpus (destructive if collection exists)
rag demo load --rebuild --approve

# 4. Verify
rag demo info
```

**Migration expectations:**

* Document IDs and chunk IDs stable across reindex when corpus unchanged (ADR-008).
* Dense vectors always regenerated on index.
* Sparse placeholder unchanged (ADR-010).
* No automatic detection of stub vs real indexed vectors in Qdrant — **operator responsibility** via `RAG_EMBEDDING_MODE` and documented workflow.

---

### 6. Evaluation Workflow (Plan 13 compatibility)

Plan 16 does **not** modify `knowledge_assistant.evaluation`. Comparison uses existing APIs:

```text
# Corpus A: stub-indexed (legacy / CI baseline)
build_demo_environment(settings=stub_settings)
→ demo load --rebuild --approve
→ EvaluationRunner.run(retriever, dataset, settings, label="fusion+stub_embed")

# Corpus B: real-indexed (meaningful quality)
build_demo_environment(settings=real_settings)
→ demo load --rebuild --approve
→ EvaluationRunner.run(retriever, dataset, settings, label="fusion+bge-m3_dense")

compare_evaluation_reports(report_a, report_b)
→ ComparisonReport
```

**Rules:**

* Same `data/evaluation/retrieval_benchmark_v1.json` for both runs.
* Same retriever stack shape (ADR-053); only dense embedding provider and indexed dense vectors differ.
* Sparse path remains stub/placeholder in Plan 16 — fusion and rerank scores still reflect hybrid stack, but sparse leg remains non-meaningful until future sparse indexing plan.
* For **dense-only** embedding comparison, wire `DenseRetriever` directly in test/script assembly (outside `evaluation/` production code) with labels `"dense+stub"` vs `"dense+bge-m3"`.
* Full four-strategy Plan 18 comparison deferred — Plan 16 documents manual/script workflow in `README.md` only.

**What changes vs what does not:**

| Component | Changes in Plan 16? |
| --------- | ------------------- |
| `EvaluationRunner` | No |
| `EvaluationDataset` / benchmark JSON | No |
| Metrics (Hit Rate@K, Recall@K, MRR) | No |
| `Retriever` protocol | No |
| Bootstrap / indexed corpus | Yes — operator must reindex |
| Dense embedding provider | Yes |

---

### 7. Runtime device validation

Plan 16 must define behavior when the configured device is unavailable at runtime initialization.

| Behavior | Assessment |
| -------- | ---------- |
| Silent fallback to CPU | **Rejected** — hides misconfiguration; produces surprising performance on lecture machines |
| Defer validation until first `embed_*` call | **Rejected** — delays failure; harder to diagnose in bootstrap |
| **Fail fast at runtime initialization** | **Selected** |

**Selected behavior:**

* When `device="cuda"` is configured but CUDA is unavailable, runtime initialization **raises** a clear configuration/runtime exception (e.g. `EmbeddingRuntimeError` or `EmbeddingDeviceError`) — **do not** silently fall back to CPU.
* When `device="mps"` is configured but MPS is unavailable, same fail-fast behavior applies.
* When `device="cpu"`, no accelerator check is required.
* Factory (`create_dense_embedding_runtime`) performs device validation during construction, before returning the runtime to bootstrap.
* Error messages must state the requested device and that fallback is not automatic.

**Rationale:** explicit configuration errors are preferable to silent degradation in an educational project where operators set `RAG_EMBEDDING_DEVICE=cuda` expecting GPU inference.

---

### 8. Local embedding runtime vs remote embedding service

| Approach | Assessment |
| -------- | ---------- |
| **Local in-process inference** | **Selected for Plan 16** — `DenseEmbeddingRuntime` loads model weights in-process via `BgeM3FlagEmbeddingRuntime` |
| OpenAI-compatible embedding endpoint | **Deferred** — would require a separate `DenseEmbeddingRuntime` HTTP implementation; out of Plan 16 scope |
| Dedicated embedding service (TEI, Infinity, vLLM embeddings, etc.) | **Deferred** — adds deployment and network boundaries; contradicts local educational project goals |

**Rationale for local in-process selection:**

* Aligns with `PROJECT.md` local demo goals and Plan 15 bootstrap composition root.
* Avoids new infrastructure, authentication, and network failure modes in Plan 16.
* `DenseEmbeddingRuntime` abstraction still allows a future remote implementation without changing indexing or retrieval contracts.

**Why remote services are deferred:**

* Requires service discovery, health checks, and API versioning not authorized by Plan 16.
* Lecture workflow should run on a laptop with `uv sync` and optional GPU — not a separate embedding server.
* OpenAI-compatible **chat** endpoints belong to `llm/` (ADR-036); embedding endpoints are a separate future concern.

No Plan 16 implementation changes beyond documenting this decision.

---

### 9. DenseEmbeddingRuntime concurrency expectations

Plan 16 documents concurrency expectations for `DenseEmbeddingRuntime` — contract clarification only; no implementation work required.

* **Thread safety is not guaranteed** by Plan 16. Callers must not assume safe concurrent `embed_passages` / `embed_query` from multiple threads on the same runtime instance.
* Runtime instances are intended for **normal single-process usage** — bootstrap demo wiring, indexing batches, and sequential retrieval queries in one process.
* Concurrent inference behavior (locking, per-thread runtimes, async batch queues) is **deferred** to a future plan if production-scale concurrency becomes a requirement.
* Unit and integration tests run sequentially; no parallel embedding stress tests in Plan 16.

Document these expectations in `embeddings/runtime.py` protocol docstring and `docs/ARCHITECTURE.md` Embeddings Layer section on completion.

---

## Public APIs

### `embeddings/` package

Export intentionally from `knowledge_assistant.embeddings`:

* `EmbeddingRuntimeSettings`
* `DenseEmbeddingRuntime` (protocol — stable contract)
* `BgeM3FlagEmbeddingRuntime` (Plan 16 default concrete implementation)
* `create_dense_embedding_runtime(settings) -> DenseEmbeddingRuntime`
* `EmbeddingRuntimeError`, `EmbeddingDimensionMismatchError`

Do **not** export FlagEmbedding types from `embeddings/__init__.py`. Callers outside `embeddings/` depend on `DenseEmbeddingRuntime`, not on `BgeM3FlagEmbeddingRuntime` directly (factory returns the protocol type).

**`DenseEmbeddingRuntime` contract notes (documentation):**

* `embed_passages` — batches input texts using `EmbeddingRuntimeSettings.batch_size`;
* `embed_query` — processes exactly one query; `batch_size` does not apply;
* thread safety not guaranteed (see Design Evaluation 9).

### Indexing additions (`indexing/embeddings.py`)

* `BgeM3EmbeddingProvider` — `@dataclass(frozen=True)` implementing `EmbeddingProvider`:

```python
@dataclass(frozen=True, slots=True)
class BgeM3EmbeddingProvider:
    runtime: DenseEmbeddingRuntime

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        ...
```

Export from `indexing/__init__.py` alongside existing `StubEmbeddingProvider`.

### Retrieval additions (`retrieval/embeddings.py`)

* `BgeM3QueryEmbeddingProvider` — `@dataclass(frozen=True)` implementing `QueryEmbeddingProvider`:

```python
@dataclass(frozen=True, slots=True)
class BgeM3QueryEmbeddingProvider:
    runtime: DenseEmbeddingRuntime

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        ...
```

Export from `retrieval/__init__.py` alongside existing `StubQueryEmbeddingProvider`.

### Bootstrap changes

* Extend `BootstrapSettings` with `embedding_mode: Literal["stub", "real"]` and `embedding_runtime_settings: EmbeddingRuntimeSettings`.
* Update `build_demo_environment()`:
  * `stub` mode — current behavior (unchanged defaults);
  * `real` mode — shared runtime + BGE adapters for dense paths; sparse/rerank remain stub.
* Update `DEMO_RETRIEVAL_PIPELINE_LABEL` to reflect embedding mode.

### Unchanged public APIs

* `DenseRetriever.retrieve` — no signature change;
* `IndexingPipeline.preview_indexing` / `index_documents` — no signature change;
* `VectorStore` protocol — no change;
* MCP handlers — no change;
* `EvaluationRunner.run` — no change.

---

## Dependency Rules

### Allowed dependency flow

```text
bootstrap
  ↓
embeddings (DenseEmbeddingRuntime via factory)
  ↓
BgeM3FlagEmbeddingRuntime   ← Plan 16 default
  ↓
FlagEmbedding / torch       ← implementation detail

bootstrap
  ↓
indexing (BgeM3EmbeddingProvider adapter → DenseEmbeddingRuntime)
  ↓
embeddings

bootstrap
  ↓
retrieval (BgeM3QueryEmbeddingProvider adapter → DenseEmbeddingRuntime)
  ↓
embeddings

indexing (pipeline)
  ↓
VectorStore

retrieval (DenseRetriever)
  ↓
VectorStore
```

### Forbidden dependencies

| From | Must not import |
| ---- | ---------------- |
| `embeddings/` | `indexing`, `retrieval`, `storage`, `mcp_server`, `agent`, `llm`, `evaluation`, `cli`, `bootstrap` |
| `indexing/` (production) | `FlagEmbedding`, `torch`, `transformers`, `retrieval` |
| `retrieval/` (production) | `FlagEmbedding`, `torch`, `transformers`, `indexing` |
| `storage/` | `embeddings`, `torch`, `FlagEmbedding` |
| `mcp_server/` | `embeddings`, `torch` |
| `agent/` | `embeddings`, `torch` |
| `llm/` | `embeddings`, `torch`, `FlagEmbedding` |
| `evaluation/` | `embeddings`, `indexing`, `storage` |
| `cli/` | `embeddings`, `torch`, `indexing`, `retrieval`, `storage` |

### Import-boundary tests (required)

| Package | Test module | Forbidden patterns |
| ------- | ----------- | ------------------ |
| `embeddings/` | `tests/unit/embeddings/test_embeddings_imports.py` | `indexing`, `retrieval`, `storage`, `llm`, `agent` |
| `indexing/` | extend `tests/unit/indexing/test_imports.py` | `torch`, `FlagEmbedding`, `retrieval` |
| `retrieval/` | extend `tests/unit/retrieval/test_imports.py` | `torch`, `FlagEmbedding`, `indexing` |
| `bootstrap/` | extend `tests/unit/bootstrap/test_bootstrap_imports.py` | `torch`, `FlagEmbedding`, `cli` |

Use AST-based import analysis consistent with existing `tests/unit/import_ast.py` patterns.

---

## Testing Strategy

### Unit tests (required — default CI)

| Location | Focus |
| -------- | ----- |
| `tests/unit/embeddings/` | settings validation; `BgeM3FlagEmbeddingRuntime` delegates to mocked FlagEmbedding backend; L2 normalization; dimension validation; batch ordering preserved; device fail-fast when cuda/mps unavailable; `embed_query` ignores batch_size |
| `tests/unit/indexing/` | `BgeM3EmbeddingProvider.embed_texts` delegates to `runtime.embed_passages`; preserves text order; empty input |
| `tests/unit/retrieval/` | `BgeM3QueryEmbeddingProvider.embed_query` delegates to `runtime.embed_query` |
| `tests/unit/bootstrap/` | stub mode unchanged; real mode wires shared runtime to both providers; same runtime object identity |
| `tests/unit/embeddings/test_embeddings_imports.py` | forbidden imports |

**Mock strategy:** patch FlagEmbedding model class at `embeddings/runtime.py` boundary — no model download in default CI.

### Integration tests (required — stub mode, default CI)

| Location | Focus |
| -------- | ----- |
| `tests/integration/indexing/` | existing flows continue with `StubEmbeddingProvider` |
| `tests/integration/retrieval/` | existing `DenseRetriever` flows with `StubQueryEmbeddingProvider` |
| `tests/integration/cli/` | demo commands remain stub-based by default |

### Integration tests (optional — real model, excluded from default CI)

| Location | Focus | Marker |
| -------- | ----- | ------ |
| `tests/integration/embeddings/test_bge_m3_runtime_smoke.py` | load model; embed one query + one passage; output dim equals configured `dense_vector_size` (default 1024); unit norm | `@pytest.mark.embedding_model` |
| `tests/integration/retrieval/test_dense_bge_m3_integration.py` | index fixture corpus with real provider; dense retrieve returns results | `@pytest.mark.embedding_model` |

Configure `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "embedding_model: requires BAAI/bge-m3 download and significant runtime",
]
```

Default CI: `pytest -m "not embedding_model"`.

### Evaluation compatibility test (required)

| Location | Focus |
| -------- | ----- |
| `tests/integration/evaluation/test_evaluation_embedding_mode_compat.py` | construct `EvaluationRunner`; run against `FakeRetriever` or stub-indexed fixture; assert no `evaluation/` imports from `embeddings/`; document pattern for real-mode script (comment/docstring reference only) |

This test proves Plan 13 API compatibility — not full benchmark execution.

---

## Documentation Updates

On completion, update:

* `docs/DECISIONS.md` — ADR-055 through ADR-060;
* `docs/ARCHITECTURE.md` — new Embeddings Layer section; update Indexing, Retrieval, Bootstrap sections for real provider wiring;
* `docs/PROGRESS.md` — Plan 16 completion entry;
* `README.md` — real embedding setup, reindex workflow, optional evaluation comparison commands;
* `.env.example` — `RAG_EMBEDDING_*` variables.

Do not update `data/evaluation/` benchmark.

---

## Acceptance Criteria

### Embedding runtime

- [ ] `knowledge_assistant.embeddings` package exists with `config.py`, `runtime.py`, `factory.py`, `exceptions.py`
- [ ] `EmbeddingRuntimeSettings` validates `model_name`, `device`, `batch_size > 0`, `max_length > 0`, `dense_vector_size > 0`
- [ ] `DenseEmbeddingRuntime` protocol defines stable `embed_passages` / `embed_query` contract
- [ ] `BgeM3FlagEmbeddingRuntime` implements `DenseEmbeddingRuntime` using FlagEmbedding dense-only APIs internally
- [ ] `BgeM3FlagEmbeddingRuntime` with default `BAAI/bge-m3` model produces vectors of length `dense_vector_size` (default 1024)
- [ ] `embed_passages` and `embed_query` use distinct BGE-M3 encoding modes in default implementation
- [ ] `batch_size` applies to `embed_passages` only; `embed_query` processes one query without configurable batching
- [ ] Runtime L2-normalizes outputs when `normalize_embeddings=True`
- [ ] Runtime validates `len(vector) == settings.dense_vector_size` before returning vectors
- [ ] Runtime initialization fails fast when `device=cuda` but CUDA is unavailable (no silent CPU fallback)
- [ ] Runtime initialization fails fast when `device=mps` but MPS is unavailable (no silent CPU fallback)
- [ ] `create_dense_embedding_runtime` is the single factory entry point; returns `DenseEmbeddingRuntime`
- [ ] `DenseEmbeddingRuntime` contract documents single-process usage; thread safety not guaranteed

### Layer adapters

- [ ] `BgeM3EmbeddingProvider` implements `EmbeddingProvider` without importing FlagEmbedding
- [ ] `BgeM3QueryEmbeddingProvider` implements `QueryEmbeddingProvider` without importing FlagEmbedding
- [ ] `StubEmbeddingProvider` and `StubQueryEmbeddingProvider` remain available and unchanged in behavior
- [ ] Indexing does not import retrieval; retrieval does not import indexing

### Dimension validation

- [ ] Runtime raises when `len(vector) != settings.dense_vector_size`
- [ ] `DenseRetriever` still raises `EmbeddingDimensionError` on provider mismatch (existing behavior)
- [ ] Storage still raises `VectorDimensionError` on upsert mismatch (existing behavior)

### Normalization behavior

- [ ] Unit tests verify L2 unit length within tolerance for runtime outputs
- [ ] Normalization applied consistently on query and passage paths

### Bootstrap integration

- [ ] `BootstrapSettings` supports `embedding_mode` stub/real (default stub)
- [ ] `build_demo_environment()` creates one shared runtime in real mode
- [ ] Same runtime instance injected into indexing and dense retrieval adapters
- [ ] `DEMO_RETRIEVAL_PIPELINE_LABEL` reflects embedding mode
- [ ] Default CI/bootstrap path uses stubs without model download

### Import-boundary tests

- [ ] AST tests for `embeddings/`, updated `indexing/`, `retrieval/`, `bootstrap/`
- [ ] No `torch` / `FlagEmbedding` in `indexing/`, `retrieval/`, `cli/`, `mcp_server/`, `llm/`, `evaluation/` production code

### Evaluation compatibility

- [ ] No changes to `knowledge_assistant.evaluation` production modules
- [ ] Integration test demonstrates `EvaluationRunner` works with retriever wired through bootstrap (stub mode)
- [ ] README documents manual stub vs real comparison workflow using `compare_evaluation_reports`

### Integration tests

- [ ] Existing stub-based integration tests pass unchanged
- [ ] Optional `@pytest.mark.embedding_model` smoke tests exist and are excluded from default pytest invocation
- [ ] `tests/integration/cli/` demo tests pass with stub default

### Dependencies and validation

- [ ] `FlagEmbedding` (and transitive `torch`) added to `pyproject.toml` runtime dependencies
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run ruff check .` passes
- [ ] `uv run basedpyright` passes
- [ ] `uv run pytest` passes (default marker selection)
- [ ] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Model download failures in dev/lecture | Document HF cache setup; optional smoke test; stub fallback default |
| GPU unavailable on student laptops | Default `device=cpu`; document expected latency; fail fast if `cuda`/`mps` configured but unavailable (no silent fallback) |
| CI slowdown from accidental model tests | `@pytest.mark.embedding_model`; excluded by default |
| Stub/real vector mismatch undetected | ADR-058 reindex requirement; `demo info` reports mode; README warning |
| FlagEmbedding API changes | Pin minimum version; isolate in `embeddings/runtime.py` |
| Memory pressure loading BGE-M3 | Bootstrap single shared instance (ADR-057) |
| Query/passage encoding confusion | ADR-056 explicit methods; unit tests assert correct backend call in `BgeM3FlagEmbeddingRuntime` |
| Accidental coupling to FlagEmbedding outside `embeddings/` | ADR-056 abstraction layering; import-boundary tests; factory returns protocol type |
| Scope creep into sparse embeddings | Explicit non-scope; dense-only FlagEmbedding flags |
| Violating ADR-013 via shared `EmbeddingProvider` | Separate adapters; protocols stay layer-local |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-055 through ADR-060 in `docs/DECISIONS.md` on plan activation.
2. **Add dependencies** — `FlagEmbedding` to `pyproject.toml`; run `uv lock`.
3. **Create `embeddings/` package** — settings, exceptions, runtime, factory.
4. **Implement `BgeM3FlagEmbeddingRuntime`** — default `DenseEmbeddingRuntime` using FlagEmbedding internally; device validation at init.
5. **Add indexing adapter** — `BgeM3EmbeddingProvider` in `indexing/embeddings.py`.
6. **Add retrieval adapter** — `BgeM3QueryEmbeddingProvider` in `retrieval/embeddings.py`.
7. **Extend bootstrap** — `embedding_mode`, shared runtime wiring, pipeline label.
8. **Update `.env.example` and README** — configuration and reindex workflow.
9. **Unit tests** — runtime (mocked), adapters, bootstrap wiring, import guards.
10. **Optional integration smoke tests** — `@pytest.mark.embedding_model`.
11. **Evaluation compat test** — stub-mode `EvaluationRunner` through bootstrap retriever.
12. **Update `docs/ARCHITECTURE.md`** — embeddings layer and bootstrap changes.
13. **Run validation suite** — all four quality commands; default pytest without `embedding_model`.
14. **Update `docs/PROGRESS.md`** — record completion; move plan to `docs/plans/completed/`.

---

## Checklist

### Architectural decisions

- [ ] ADR-055 — Dedicated embeddings package
- [ ] ADR-056 — BGE-M3 default runtime implementation (FlagEmbedding)
- [ ] ADR-057 — Bootstrap-owned shared runtime
- [ ] ADR-058 — Full reindex on dense provider migration
- [ ] ADR-059 — Normalization and dimension contract
- [ ] ADR-060 — Stub default for CI

### Embeddings package

- [ ] `EmbeddingRuntimeSettings`
- [ ] `DenseEmbeddingRuntime` / `BgeM3FlagEmbeddingRuntime`
- [ ] `create_dense_embedding_runtime`
- [ ] Embedding exceptions
- [ ] Import-boundary tests

### Layer adapters

- [ ] `BgeM3EmbeddingProvider`
- [ ] `BgeM3QueryEmbeddingProvider`
- [ ] Public exports updated

### Bootstrap

- [ ] `embedding_mode` setting
- [ ] Shared runtime injection
- [ ] Pipeline label update
- [ ] Bootstrap unit tests

### Documentation

- [ ] `docs/ARCHITECTURE.md`
- [ ] `docs/DECISIONS.md`
- [ ] `README.md`
- [ ] `.env.example`

### Validation

- [ ] ruff format / check
- [ ] basedpyright
- [ ] pytest (default)
- [ ] `docs/PROGRESS.md`
