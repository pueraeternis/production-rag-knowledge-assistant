# Plan 20 — Real Sparse Embeddings Integration

**Status:** Completed

**Created:** 2026-06-22

**Completed:** 2026-06-22

**Roadmap:** Phase 15 — Real Sparse Embeddings Integration

**Depends on:**

* [Plan 05 — Indexing Pipeline](../completed/05-indexing-pipeline.md)
* [Plan 07 — Sparse Retrieval](../completed/07-sparse-retrieval.md)
* [Plan 08 — Fusion Retrieval](../completed/08-fusion-retrieval.md)
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md)
* [Plan 16 — Real Dense Embeddings Integration](../completed/16-real-dense-embeddings-integration.md)
* [Plan 18 — Retrieval Strategy Evaluation](../completed/18-retrieval-strategy-evaluation.md)

**Plan principle:** One plan introduces one architectural capability. Plan 20 introduces **real BGE-M3 sparse (lexical) embedding runtime** for indexing write path and retrieval query path only. It does **not** redesign `DenseRetriever`, `FusionRetriever`, `RerankRetriever`, fusion math, reranking, MCP, agent, LLM, evaluation framework code, or CLI command surface beyond bootstrap provider selection and pipeline labels.

---

## Authorization

**Completed.** ADR-081 through ADR-086 recorded in `docs/DECISIONS.md`.

---

## Objective

Replace ADR-010 sparse placeholder indexing and hash-based stub sparse query embeddings with **real BGE-M3 lexical sparse vectors**, completing the hybrid retrieval data path:

```text
Indexing write path:
    Chunk texts
        ↓
SparseEmbeddingProvider (BgeM3SparseEmbeddingProvider)
        ↓
BgeM3FlagEmbeddingRuntime.embed_passages_sparse(...)
        ↓
lexical_weights → SparseVector (indices + values)
        ↓
VectorStore.upsert_chunks (named vector: sparse)

Retrieval query path:
    SearchQuery.text
        ↓
SparseQueryEmbeddingProvider (BgeM3SparseQueryEmbeddingProvider)
        ↓
BgeM3FlagEmbeddingRuntime.embed_query_sparse(...)
        ↓
lexical_weights → SparseQueryVector (indices + values)
        ↓
SparseRetriever → VectorStore.search_sparse
```

End-to-end hybrid flow after Plan 20 + approved reindex:

```text
Document
    ↓
BGE-M3
    ↓
Dense vector + Sparse vector
    ↓
Qdrant

Query
    ↓
BGE-M3
    ↓
Dense vector + Sparse vector
    ↓
Dense Retrieval + Sparse Retrieval
    ↓
Fusion (RRF)
    ↓
Rerank
```

After this plan is complete:

* indexing generates **real per-chunk sparse vectors** aligned with BGE-M3 passage encoding;
* retrieval generates **real sparse query vectors** aligned with BGE-M3 query encoding;
* the existing **`knowledge_assistant.embeddings`** package extends BGE-M3 runtime with sparse inference and lexical-weight conversion — no second model load;
* bootstrap selects real sparse providers when `RAG_EMBEDDING_MODE=real` (same mode gate as Plan 16 dense);
* operators **reindex** after switching from placeholder-indexed collections;
* Plan 18 evaluation can measure meaningful sparse and fusion lift **without evaluation code changes** — by reindexing with real sparse vectors and re-running `rag evaluate`.

**Observed baseline (first successful end-to-end run, real dense + real rerank, placeholder sparse):**

| Strategy | Hit@1 | Hit@3 | Hit@5 |
| -------- | ----- | ----- | ----- |
| dense | 0.743 | 0.871 | 0.914 |
| sparse | 0.000 | 0.000 | 0.000 |
| fusion | ≈ dense | ≈ dense | ≈ dense |
| rerank | slight improvement over dense | | |

Root cause: every indexed chunk stores `SparseVector(indices=(0,), values=(1.0,))` (ADR-010); sparse query uses hash-based `StubSparseQueryEmbeddingProvider`. Sparse retrieval contributes no lexical signal; fusion collapses to dense ordering.

**Dependency rule:** sparse model runtime (`FlagEmbedding`, `torch`) remains confined to `knowledge_assistant.embeddings`. Indexing and retrieval depend on thin layer adapters — not on `torch` or `FlagEmbedding` directly.

**ADR-019 guardrail:** write-path sparse contract remains in `indexing/`; query-path sparse contract remains in `retrieval/`. Shared model execution does not collapse those boundaries.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/embeddings/` | Sparse inference methods, lexical-weight conversion, settings extension, exceptions |
| `src/knowledge_assistant/indexing/embeddings.py` | `SparseEmbeddingProvider`, `StubSparseEmbeddingProvider`, `BgeM3SparseEmbeddingProvider` |
| `src/knowledge_assistant/indexing/pipeline.py` | Wire sparse provider; remove hardcoded `sparse_placeholder_vector()` in real mode |
| `src/knowledge_assistant/retrieval/embeddings.py` | `BgeM3SparseQueryEmbeddingProvider` |
| `src/knowledge_assistant/bootstrap/` | Real vs stub sparse provider selection; shared runtime injection; pipeline label |
| `src/knowledge_assistant/bootstrap/retrievers.py` | Inject configured sparse query provider (today hardcoded stub) |
| `tests/unit/embeddings/` | Sparse conversion, runtime sparse methods (mocked backend) |
| `tests/unit/indexing/` | Sparse write-path provider and pipeline wiring |
| `tests/unit/retrieval/` | Sparse query-path provider |
| `tests/unit/bootstrap/` | Bootstrap sparse mode wiring |
| `tests/integration/embeddings/` | Optional real-model sparse smoke tests (marked) |
| `tests/integration/indexing/` | Real sparse indexing integration (optional / marked) |
| `tests/integration/retrieval/` | Real sparse retrieval integration (optional / marked) |
| `docs/ARCHITECTURE.md` | Sparse embedding runtime, indexing write path, bootstrap wiring |
| `docs/DECISIONS.md` | ADR-081 through ADR-086 |
| `docs/PROGRESS.md` | Plan 20 completion entry |
| `docs/plans/backlog/ROADMAP.md` | Phase 15 entry |
| `README.md` | Real sparse setup, reindex workflow, evaluation expectations |
| `.env.example` | Document sparse behavior under existing `RAG_EMBEDDING_*` (no new mode variable required) |

### In Scope

* extend `BgeM3FlagEmbeddingRuntime` (or sibling sparse-capable runtime on same model instance) with:
  * `embed_passages_sparse(texts) -> tuple[SparseVectorPayload, ...]`
  * `embed_query_sparse(text) -> SparseVectorPayload`
  where `SparseVectorPayload` is an embeddings-local `(indices, values)` tuple validated before crossing layer boundaries;
* **single FlagEmbedding encode call** per batch with `return_dense=True, return_sparse=True` on indexing path when both dense and sparse are real — avoid duplicate model forward passes;
* lexical weight conversion: `dict[token_id, weight]` → sorted unique `indices: tuple[int, ...]`, `values: tuple[float, ...]`;
* drop zero-weight entries; validate finite non-negative weights;
* `SparseEmbeddingProvider` protocol in `indexing/embeddings.py`;
* `StubSparseEmbeddingProvider` — deterministic hash-based sparse vectors aligned with `StubSparseQueryEmbeddingProvider` philosophy;
* `BgeM3SparseEmbeddingProvider` adapter implementing `SparseEmbeddingProvider`;
* `BgeM3SparseQueryEmbeddingProvider` adapter implementing `SparseQueryEmbeddingProvider`;
* `IndexingPipeline` accepts `sparse_embedding_provider: SparseEmbeddingProvider`; generates **per-chunk** sparse vectors;
* bootstrap: when `embedding_mode=real`, inject shared runtime into dense **and** sparse adapters for indexing and retrieval;
* bootstrap: when `embedding_mode=stub`, use `StubSparseEmbeddingProvider` + `StubSparseQueryEmbeddingProvider`;
* `sparse_placeholder_vector()` retained for backward-compatible tests but **not** used in production pipeline paths after Plan 20;
* `DEMO_RETRIEVAL_PIPELINE_LABEL` / `retrieval_pipeline_label` reflects real sparse, e.g. `dense (bge-m3) + sparse (bge-m3) → fusion (RRF) → rerank (...)`;
* reindex workflow documentation (`rag demo load --rebuild --approve`);
* evaluation workflow documentation: expect sparse Hit@K > 0 and fusion ≠ dense after reindex;
* import-boundary tests;
* ADR-081 through ADR-086.

---

## Non-Scope

Plan 20 does **not** authorize:

* ColBERT / multi-vector retrieval (`return_colbert_vecs=True`);
* BM25, Elasticsearch, Whoosh, Tantivy, or separate lexical indexes;
* `FusionRetriever`, `SparseRetriever`, `DenseRetriever`, `RerankRetriever` orchestration changes;
* fusion algorithm (RRF) or `FusionRetrievalSettings` changes;
* reranker changes (`BgeReranker`, `StubReranker`, Plan 17 runtime);
* `VectorStore` protocol changes;
* Qdrant collection schema changes (ADR-004 already provisioned `sparse` named vector);
* `SparseVectorParams` tuning (IDF modifier, on-disk index) — defer unless search quality requires it;
* MCP handler, schema, or transport changes;
* LangGraph agent or `agent/wiring.py` changes;
* `llm/` changes;
* chat CLI (`rag chat`, Plan 19);
* `EvaluationRunner`, metrics, benchmark JSON, or `rag evaluate` command changes;
* automatic silent reindex on provider switch;
* sparse-only mode with stub dense (real hybrid requires aligned dense + sparse from same indexing generation);
* embedding cache persistence;
* async embedding APIs;
* `AppError`-rooted exception hierarchy (deferred).

---

## Research Summary

### BGE-M3 sparse capabilities

| Topic | Finding |
| ----- | ------- |
| Mechanism | Linear layer + ReLU on per-token hidden states → lexical importance weights |
| API — passages | `BGEM3FlagModel.encode(texts, return_dense=True, return_sparse=True, return_colbert_vecs=False)` |
| API — queries | `BGEM3FlagModel.encode_queries(queries, return_dense=True, return_sparse=True, return_colbert_vecs=False)` |
| Output key | `lexical_weights`: `list[dict[token_id, float]]`, one dict per input text |
| Token mapping | Keys are **tokenizer token IDs** (vocabulary indices), not arbitrary hash buckets; `model.convert_id_to_token()` for debugging |
| Typical sparsity | ~20–200 non-zero entries per text (variable length, not fixed dimension) |
| Weight semantics | Non-negative ReLU weights; similarity = dot product over **co-occurring token indices** (lexical matching) |
| Dense interaction | Same `encode` / `encode_queries` call can return `dense_vecs` and `lexical_weights` — Plan 20 should exploit this on indexing |
| ColBERT | Available but explicitly out of scope |

**Encoding path distinction (required):**

* document chunks → `encode` (passage mode);
* search queries → `encode_queries` (query mode).

Plan 16 already enforces this split for dense vectors. Plan 20 must mirror it for sparse vectors. Using `encode` for queries (or vice versa) is a quality bug, not a supported configuration.

### Qdrant sparse-vector support (current storage layer)

| Topic | Finding |
| ----- | ------- |
| Schema | ADR-004: named vector `sparse` with `SparseVectorParams()` — **already created** in `QdrantVectorStore.create_collection` |
| Upsert | `models.SparseVector(indices=..., values=...)` on named vector `sparse` — **already implemented** |
| Search | `query_points(..., query=SparseVector(...), using=SPARSE_VECTOR_NAME)` — **already implemented** |
| Metric | Dot product on matching indices (Qdrant sparse default) — aligns with BGE-M3 lexical matching |
| Index requirements | Inverted index built by Qdrant on upsert; no application-side sparse index |
| Validation | `storage/validation.py` — unique indices, matching lengths, finite values; `SparseQueryVector` adds non-empty requirement on query path |
| Conversion requirement | BGE `lexical_weights` dict keys → `int` indices, **sorted ascending**, unique |
| Storage changes | **None required** for Plan 20 |

### Retrieval impact

| Component | Plan 20 change |
| --------- | -------------- |
| `DenseRetriever` | **Unchanged** |
| `SparseRetriever` | **Unchanged** orchestration; receives real provider via injection |
| `FusionRetriever` | **Unchanged**; benefits automatically when sparse leaf returns meaningful ranks |
| `RerankRetriever` / `Reranker` | **Unchanged** |
| Bootstrap `build_retrieval_stack` | **Change provider injection only** — replace hardcoded `StubSparseQueryEmbeddingProvider()` |
| Evaluation | **Unchanged** code; meaningful sparse/fusion metrics require reindex |

---

## Architectural Decisions (Proposed ADRs)

### ADR-081 — Real Sparse Embedding Ownership

**Status:** Accepted

#### Context

ADR-019 assigns sparse write-path ownership to indexing (deferred) and query-path ownership to retrieval (Plan 07). ADR-010 placeholder and stub query embeddings block meaningful hybrid retrieval. Plan 16 added shared dense runtime without addressing sparse. Without explicit ownership for real sparse generation, implementation could blur `embeddings/`, `indexing/`, and `retrieval/` boundaries.

#### Decision

* **Indexing** owns write-path sparse embedding via `SparseEmbeddingProvider.embed_sparse_texts` in `indexing/embeddings.py`.
* **Retrieval** owns query-path sparse embedding via `SparseQueryEmbeddingProvider.embed_query` in `retrieval/embeddings.py` (protocol exists since Plan 07).
* **`knowledge_assistant.embeddings`** owns BGE-M3 sparse **model execution** and lexical-weight conversion — same package as dense runtime (ADR-055).
* **Storage** receives pre-computed `SparseVector` on upsert and `(indices, values)` on search — unchanged (ADR-006, ADR-019).
* `llm/` must not implement or import sparse embedding runtime code.
* Layer protocols remain in owning packages; adapters delegate to shared runtime.

#### Consequences

* Plan 20 completes the ownership model ADR-019 deferred to a future plan.
* `SparseRetriever` and `IndexingPipeline` remain orchestrators — they do not call FlagEmbedding directly.
* Future ColBERT or alternate sparse models would extend `embeddings/` without changing leaf retriever APIs.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Single `HybridEmbeddingProvider` returning dense+sparse tuples | Collapses ADR-013 write/read contracts; harder to test layers independently |
| Sparse runtime in `retrieval/` only | Violates ADR-019 write-path indexing ownership |
| Sparse runtime in `indexing/` only | Violates ADR-019 query-path retrieval ownership |
| Storage-side sparse generation | Violates ADR-006 |

---

### ADR-082 — BGE-M3 Dual Dense+Sparse Encoding in Shared Runtime

**Status:** Accepted

#### Context

Plan 16 introduced `BgeM3FlagEmbeddingRuntime` with dense-only FlagEmbedding calls (`return_sparse=False`). Real hybrid retrieval requires passage and query sparse vectors from the **same** `BAAI/bge-m3` weights already loaded for dense paths (ADR-057). A second model instance would double memory and risk configuration drift.

#### Decision

* Extend `BgeM3FlagEmbeddingRuntime` (same class, same loaded model) with sparse inference methods.
* **Passage sparse:** internal call to `encode(..., return_dense=False, return_sparse=True, return_colbert_vecs=False)` or combined `return_dense=True, return_sparse=True` when caller needs both.
* **Query sparse:** internal call to `encode_queries(..., return_sparse=True, return_colbert_vecs=False)`.
* Stable sparse contract at embeddings layer:

```python
# embeddings-local payload before mapping to storage/retrieval types
SparseVectorPayload = tuple[tuple[int, ...], tuple[float, ...]]  # (indices, values)

runtime.embed_passages_sparse(texts) -> tuple[SparseVectorPayload, ...]
runtime.embed_query_sparse(text) -> SparseVectorPayload
```

* Optional combined method for indexing efficiency:

```python
runtime.embed_passages_dual(texts) -> tuple[
    tuple[tuple[float, ...], ...],      # dense
    tuple[SparseVectorPayload, ...],     # sparse
]
```

  Implementation may use one FlagEmbedding call with `return_dense=True, return_sparse=True`. Public adapter split (`BgeM3EmbeddingProvider` + `BgeM3SparseEmbeddingProvider`) remains for ADR-013/ADR-081 boundaries.

* `return_colbert_vecs` remains **disabled** in Plan 20.
* Indexing and retrieval adapters depend on runtime protocol methods — not on `lexical_weights` dict shape.

#### Consequences

* One model load serves dense and sparse for both indexing and retrieval.
* Plan 16 dense behavior unchanged when sparse methods are not called.
* Indexing can halve forward passes by using dual-output encode.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate `SparseEmbeddingRuntime` with second model load | 2× memory; config drift risk |
| Dense-only runtime; sparse via separate library | Duplicates BGE-M3 weights |
| Reuse `encode` for queries | Violates BGE-M3 query/passage semantics; hurts retrieval quality |

---

### ADR-083 — Lexical Weight to Qdrant SparseVector Conversion Contract

**Status:** Accepted

#### Context

FlagEmbedding returns `lexical_weights` as `dict[token_id, weight]` per text. Qdrant expects `SparseVector(indices: list[int], values: list[float])` with unique indices. `storage.models.SparseVector` and `retrieval.sparse_vectors.SparseQueryVector` enforce additional invariants. Conversion must be deterministic and shared across write and read paths.

#### Decision

* Implement `lexical_weights_to_sparse_payload(weights: dict) -> SparseVectorPayload` in `embeddings/` (e.g. `embeddings/sparse_conversion.py`).
* Conversion rules:
  1. Parse each key as `int` token ID (accept `int` or `str` keys from FlagEmbedding).
  2. Include only entries with **weight > 0** and finite values.
  3. If duplicate token IDs appear after parsing, **sum** weights (defensive; FlagEmbedding should not duplicate).
  4. Sort by index ascending.
  5. Emit `values` aligned with sorted `indices`.
* **Query path:** after conversion, wrap in `SparseQueryVector`; if zero non-zero weights remain, raise `EmbeddingRuntimeError` (or `SparseVectorValidationError` at adapter) — empty sparse queries are invalid for search.
* **Write path:** after conversion, wrap in `storage.models.SparseVector`; if zero non-zero weights remain, raise at runtime — empty sparse document vectors must not be upserted silently.
* **No IDF modifier** applied in application layer; Qdrant stores raw weights. Tuning deferred.
* **No schema change** — existing ADR-004 `sparse` slot and Plan 04 validation rules apply.
* Token IDs are stored **as-is** in Qdrant indices; vocabulary is defined by the BGE-M3 tokenizer bundled with the model. Reindex required if model/tokenizer changes.

#### Consequences

* Identical conversion logic for indexing and retrieval eliminates index misalignment.
* Stub providers continue using hash-modulo indices (`StubSparseQueryEmbeddingProvider`) independent of tokenizer IDs — stub sparse remains non-meaningful for hybrid quality, as today.
* Real sparse vectors are **not** L2-normalized unless FlagEmbedding weights already imply it; dot product in Qdrant matches BGE lexical matching semantics.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Convert in indexing and retrieval separately | Duplication risk; alignment bugs |
| Map tokens to hash buckets | Breaks BGE-M3 lexical matching; reintroduces stub-like behavior |
| Store string tokens in Qdrant | Qdrant sparse indices are numeric; violates storage contract |
| Apply IDF in application layer | Undocumented divergence from BGE reference scoring; defer |

---

### ADR-084 — Sparse Embedding Migration Requires Full Reindex

**Status:** Accepted

#### Context

ADR-020 documents that replacing ADR-010 placeholders requires full reindex. Collections indexed with real dense vectors (Plan 16) may still carry `indices=(0,), values=(1.0,)` sparse placeholders. Real sparse query vectors will not align with placeholder-indexed passages. Mixing stub sparse query with real sparse index (or vice versa) is undefined.

#### Decision

* Enabling real sparse embeddings for production retrieval requires **per-chunk BGE-M3 sparse vectors** in Qdrant.
* Switching sparse generation **placeholder → real** (or real → stub) requires **full collection rebuild and reindex** with caller approval — same workflow as ADR-058 dense migration.
* Recovery path: `rag demo load --rebuild --approve`.
* **No in-place sparse vector migration** or partial chunk updates in Plan 20.
* **Coupling rule:** when `RAG_EMBEDDING_MODE=real`, bootstrap enables real dense **and** real sparse together from one shared runtime. Operators must not manually combine real dense-indexed corpus with placeholder sparse vectors expecting meaningful hybrid results.
* `rag demo info` pipeline label must indicate sparse mode (`sparse` vs `sparse (bge-m3)`) so operators detect incomplete migration.
* ADR-020 remains valid; Plan 20 **implements** the migration ADR-020 anticipated.

#### Consequences

* Operators who completed Plan 16 reindex must reindex again after Plan 20 for sparse/fusion lift.
* Evaluation baseline: sparse Hit@K = 0 and fusion ≈ dense until reindex — expected, not a framework bug.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Lazy sparse backfill on read | Violates human-in-the-loop; unpredictable latency |
| Sparse-only reindex without dense regeneration | Risks dense/sparse chunk misalignment; simpler to full rebuild |
| Automatic rebuild on mode switch | Violates ADR-054 explicit approval |

---

### ADR-085 — Bootstrap Sparse Provider Selection Follows Embedding Mode

**Status:** Accepted

#### Context

Plan 16 introduced `RAG_EMBEDDING_MODE=stub|real` for dense providers. `build_retrieval_stack` currently **always** injects `StubSparseQueryEmbeddingProvider()` regardless of mode. `IndexingPipeline` always calls `sparse_placeholder_vector()`. Bootstrap must become the single composition point for sparse provider selection (ADR-051, ADR-057).

#### Decision

* **No separate `RAG_SPARSE_MODE`** in Plan 20 — sparse follows `BootstrapSettings.embedding_mode`:
  * `stub` → `StubSparseEmbeddingProvider` + `StubSparseQueryEmbeddingProvider`;
  * `real` → `BgeM3SparseEmbeddingProvider(runtime=...)` + `BgeM3SparseQueryEmbeddingProvider(runtime=...)` using the **same** shared runtime instance as dense adapters.
* Extend `build_demo_environment()`:
  * pass `sparse_embedding_provider` into `IndexingPipeline`;
  * pass `sparse_query_embedding_provider` into `build_retrieval_stack`.
* Extend `build_retrieval_stack(..., sparse_query_embedding_provider: SparseQueryEmbeddingProvider)` — remove hardcoded stub.
* Update `retrieval_pipeline_label()`:
  * stub: `dense + sparse → fusion (RRF) → rerank (...)`
  * real: `dense (bge-m3) + sparse (bge-m3) → fusion (RRF) → rerank (...)`
* Default remains **stub** for CI (ADR-060 pattern extended to sparse).

#### Consequences

* One environment variable controls real vs stub for both embedding legs — operator-simple.
* Plan 18 `rag evaluate` automatically picks up sparse provider from bootstrap without CLI changes.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Independent `RAG_SPARSE_MODE` | Allows misaligned dense-real + sparse-stub states that defeat hybrid evaluation |
| Sparse wiring only in CLI | Violates ADR-051 composition root |
| Always real sparse when dense is real but skip indexing | Query/index vocabulary misalignment |

---

### ADR-086 — Stub Sparse Providers Remain Default for CI

**Status:** Accepted

#### Context

Real BGE-M3 sparse inference shares Plan 16 costs (torch, model download). CI and unit tests must remain fast. `StubSparseQueryEmbeddingProvider` and hash-based dense stubs are established patterns (ADR-016, Plan 07).

#### Decision

* `StubSparseEmbeddingProvider` and `StubSparseQueryEmbeddingProvider` **remain** in the codebase.
* Default `build_demo_environment()` uses stub sparse providers unless `RAG_EMBEDDING_MODE=real`.
* Default `pytest` invocation passes without sparse model inference.
* Real sparse smoke tests opt-in via existing `@pytest.mark.embedding_model` and `RAG_EMBEDDING_ENABLE_REAL_TESTS=true`.
* `sparse_placeholder_vector()` may remain exported for legacy unit tests but is **not** used by `IndexingPipeline` after Plan 20.

#### Consequences

* CI validation unchanged in weight.
* Meaningful sparse/fusion benchmark numbers require `RAG_EMBEDDING_MODE=real` + approved reindex — document in README (extends ADR-070).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Remove stub sparse providers | Loses fast deterministic tests |
| Real sparse as default | Breaks CI; forces model download |
| Skip sparse tests in CI entirely | Regresses Plan 07 coverage |

---

## Design Evaluations

### 1. Runtime extension vs new package

| Approach | Assessment |
| -------- | ---------- |
| New `sparse_embeddings/` package | **Rejected** — splits one model across packages |
| Sparse in `retrieval/` only | **Rejected** — violates ADR-081 |
| **Extend `embeddings/` + `BgeM3FlagEmbeddingRuntime`** | **Selected** — same model, same factory cache |

**Package layout (proposed):**

```text
src/knowledge_assistant/embeddings/
    runtime.py              # add sparse methods to BgeM3FlagEmbeddingRuntime
    sparse_conversion.py    # lexical_weights → (indices, values)
    exceptions.py           # extend with sparse-specific errors if needed
```

### 2. Indexing pipeline integration

| Approach | Assessment |
| -------- | ---------- |
| Keep `sparse_placeholder_vector()` in pipeline | **Rejected** — perpetuates ADR-010 in real mode |
| **`sparse_embedding_provider` injected into `IndexingPipeline`** | **Selected** |

**Selected wiring:**

```text
chunk_texts
    ↓
embedding_provider.embed_texts(chunk_texts)           → dense_vectors
sparse_embedding_provider.embed_sparse_texts(chunk_texts) → sparse_vectors
    ↓
per-chunk ChunkUpsertItem(dense_vector=..., sparse_vector=...)
```

Optional optimization: `BgeM3SparseEmbeddingProvider` and `BgeM3EmbeddingProvider` share runtime; pipeline may call a single `embed_passages_dual` through a package-internal helper to avoid double forward pass — implementation detail confined to `embeddings/`.

### 3. Query vs passage sparse encoding

| Path | FlagEmbedding API | Plan 20 runtime method |
| ---- | ----------------- | ------------------------ |
| Chunks (write) | `encode` | `embed_passages_sparse` / dual encode |
| Queries (read) | `encode_queries` | `embed_query_sparse` |

Unit tests must assert correct backend method per path (mirror Plan 16 dense tests).

### 4. Lexical weight structure

| Field | Value |
| ----- | ----- |
| Source key | `output["lexical_weights"][i]` |
| Key type | Token ID (`int` or `str` of int) |
| Value type | `float`, non-negative |
| Typical nnz | ~20–200 per text (variable) |
| Vocabulary | BGE-M3 tokenizer vocab (~250k); indices stored directly in Qdrant |
| Similarity | Dot product on intersection of query/passage indices |

### 5. Qdrant compatibility checklist

| Requirement | Current state |
| ----------- | ------------- |
| Named `sparse` vector | ✅ ADR-004 / `collection.py` |
| `SparseVector` upsert | ✅ `qdrant_store.upsert_chunks` |
| `search_sparse` | ✅ `qdrant_store.search_sparse` |
| Unique sorted indices | ⚠️ Plan 20 conversion must enforce |
| Non-empty query vector | ✅ `SparseQueryVector` validation |
| Storage code changes | **None** |

### 6. Fusion and rerank impact

| Component | Change |
| --------- | ------ |
| `FusionRetriever` | **None** — RRF over leaf lists unchanged |
| `reciprocal_rank_fusion` | **None** |
| `RerankRetriever` | **None** |
| Expected behavior | Sparse leaf returns lexical hits; fusion diversifies beyond dense; rerank reorders fused pool |

Fusion ≈ dense today because sparse leaf returns arbitrary constant-scored results. After Plan 20 + reindex, fusion should diverge when queries benefit from lexical overlap.

### 7. Configuration ownership

| Setting | Owner | Default | Notes |
| ------- | ----- | ------- | ----- |
| `embedding_mode` | `BootstrapSettings` / `RAG_EMBEDDING_MODE` | `stub` | Controls **both** dense and sparse real vs stub |
| `model_name` | `EmbeddingRuntimeSettings` | `BAAI/bge-m3` | Shared for dense + sparse |
| `device`, `batch_size`, `max_length` | `EmbeddingRuntimeSettings` | Plan 16 defaults | `batch_size` applies to passage paths only |
| `normalize_embeddings` | `EmbeddingRuntimeSettings` | `True` | Dense only; sparse weights unnormalized |

**No new required environment variables** for Plan 20. Document in README that `RAG_EMBEDDING_MODE=real` now enables real sparse paths and requires reindex for sparse/fusion evaluation.

### 8. Reindex requirements

| Scenario | Reindex | Approval |
| -------- | ------- | -------- |
| First index with real dense + sparse (empty collection) | No (initial load) | No |
| Plan 16 real dense index → Plan 20 real sparse | **Yes** | **Yes** |
| Placeholder sparse → real sparse | **Yes** | **Yes** |
| Model/tokenizer change | **Yes** | **Yes** |
| `embedding_mode=real` without reindex after placeholder index | **Unsupported** — sparse/fusion metrics meaningless |

**Operator workflow:**

```text
export RAG_EMBEDDING_MODE=real
rag demo info
rag demo load --rebuild --approve
rag evaluate compare    # expect sparse > 0, fusion ≠ dense
```

### 9. Evaluation workflow (Plan 18 compatibility)

| Component | Changes in Plan 20? |
| --------- | ------------------- |
| `EvaluationRunner` | No |
| `rag evaluate` CLI | No |
| Benchmark JSON | No |
| Bootstrap providers | Yes |
| Indexed sparse vectors | Yes — operator reindex |

**Expected post-reindex shifts (qualitative, not acceptance thresholds):**

* `sparse` strategy: Hit@K > 0 on `retrieval_benchmark_v1.json`
* `fusion` strategy: metrics diverge from `dense` on lexical-friendly queries
* `rerank` strategy: may improve further over fusion

---

## Public APIs

### `embeddings/` additions

Export from `knowledge_assistant.embeddings`:

* `SparseVectorPayload` (type alias or small NamedTuple)
* `lexical_weights_to_sparse_payload(...)`
* Extended `BgeM3FlagEmbeddingRuntime` sparse methods (via existing class)
* Sparse-related exceptions if needed

Do **not** export FlagEmbedding types from `__init__.py`.

### Indexing additions (`indexing/embeddings.py`)

```python
class SparseEmbeddingProvider(Protocol):
    def embed_sparse_texts(self, texts: tuple[str, ...]) -> tuple[SparseVector, ...]: ...

@dataclass(frozen=True, slots=True)
class StubSparseEmbeddingProvider: ...

@dataclass(frozen=True, slots=True)
class BgeM3SparseEmbeddingProvider:
    runtime: DenseEmbeddingRuntime  # or sparse-capable protocol
    def embed_sparse_texts(self, texts: tuple[str, ...]) -> tuple[SparseVector, ...]: ...
```

### Retrieval additions (`retrieval/embeddings.py`)

```python
@dataclass(frozen=True, slots=True)
class BgeM3SparseQueryEmbeddingProvider:
    runtime: DenseEmbeddingRuntime  # or sparse-capable protocol
    def embed_query(self, text: str) -> SparseQueryVector: ...
```

### `IndexingPipeline` change

Add constructor parameter:

```python
sparse_embedding_provider: SparseEmbeddingProvider
```

Replace `sparse_placeholder_vector()` loop with `embed_sparse_texts(chunk_texts)` aligned per chunk.

### Bootstrap changes

* `build_demo_environment()` — construct sparse providers from `embedding_mode`
* `build_retrieval_stack(..., sparse_query_embedding_provider=...)` — required parameter
* `retrieval_pipeline_label()` — sparse mode segment

### Unchanged public APIs

* `SparseRetriever.retrieve` — no signature change
* `FusionRetriever.retrieve` — no signature change
* `RerankRetriever.retrieve` — no signature change
* `VectorStore` protocol — no change
* MCP handlers — no change
* `EvaluationRunner.run` — no change

---

## Dependency Rules

### Allowed dependency flow

```text
bootstrap
  ↓
embeddings (BgeM3FlagEmbeddingRuntime — dense + sparse methods)
  ↓
FlagEmbedding / torch

bootstrap → indexing (BgeM3SparseEmbeddingProvider) → embeddings
bootstrap → retrieval (BgeM3SparseQueryEmbeddingProvider) → embeddings

indexing (pipeline) → VectorStore
retrieval (SparseRetriever) → VectorStore
```

### Forbidden dependencies

| From | Must not import |
| ---- | ---------------- |
| `indexing/` (production) | `FlagEmbedding`, `torch`, `retrieval` |
| `retrieval/` (production) | `FlagEmbedding`, `torch`, `indexing` |
| `storage/` | `embeddings`, `torch`, `FlagEmbedding` |
| `embeddings/` | `indexing`, `retrieval`, `storage`, `mcp_server`, `agent`, `llm`, `evaluation` |
| `evaluation/` | `embeddings`, `indexing`, `storage` |

---

## Testing Strategy

### Unit tests (required — default CI)

| Location | Focus |
| -------- | ----- |
| `tests/unit/embeddings/` | `lexical_weights_to_sparse_payload`: sort, dedupe, drop zeros, int keys; mocked `lexical_weights` from backend; passage vs query method dispatch; empty weights error |
| `tests/unit/indexing/` | `StubSparseEmbeddingProvider` determinism; `BgeM3SparseEmbeddingProvider` delegates; pipeline uses provider output per chunk (mocked) |
| `tests/unit/retrieval/` | `BgeM3SparseQueryEmbeddingProvider` delegates; produces valid `SparseQueryVector` |
| `tests/unit/bootstrap/` | stub mode → stub sparse providers; real mode → shared runtime injected into sparse adapters; `build_retrieval_stack` receives sparse provider |
| Import-boundary tests | extend existing AST guards |

**Mock strategy:** patch FlagEmbedding at `embeddings/runtime.py` boundary; return synthetic `lexical_weights` dicts.

### Integration tests (required — stub mode, default CI)

| Location | Focus |
| -------- | ----- |
| `tests/integration/indexing/` | pipeline with `StubSparseEmbeddingProvider` produces non-constant sparse per chunk |
| `tests/integration/retrieval/` | existing `SparseRetriever` + stub providers unchanged behavior |
| `tests/integration/retrieval/test_fusion_retriever.py` | continues to pass — fusion wiring unchanged |

### Integration tests (optional — real model, excluded from default CI)

| Location | Focus | Marker |
| -------- | ----- | ------ |
| `tests/integration/embeddings/test_bge_m3_sparse_smoke.py` | real encode returns non-empty sparse; indices sorted; query vs passage both work | `@pytest.mark.embedding_model` |
| `tests/integration/retrieval/test_sparse_bge_m3_integration.py` | index fixture with real sparse; sparse search returns results | `@pytest.mark.embedding_model` |

### Evaluation compatibility (required)

| Location | Focus |
| -------- | ----- |
| `tests/unit/bootstrap/test_strategy_retrievers.py` | real mode wires non-stub sparse provider into `SparseRetriever` |
| Document in README | post-Plan-20 reindex required for meaningful `rag evaluate compare` sparse/fusion columns |

---

## Documentation Updates

On completion, update:

* `docs/DECISIONS.md` — ADR-081 through ADR-086;
* `docs/ARCHITECTURE.md` — remove "future sparse indexing" language; document real sparse write/read paths;
* `docs/PROGRESS.md` — Plan 20 completion entry;
* `docs/plans/backlog/ROADMAP.md` — Phase 15;
* `README.md` — reindex after Plan 20, evaluation expectations, `RAG_EMBEDDING_MODE=real` now covers sparse;
* `.env.example` — clarify sparse behavior under `RAG_EMBEDDING_MODE`.

Do not update `data/evaluation/retrieval_benchmark_v1.json`.

---

## Acceptance Criteria

### Embedding runtime (sparse)

- [x] `lexical_weights_to_sparse_payload` converts FlagEmbedding dicts to sorted unique indices + aligned values
- [x] Zero-weight entries excluded; empty result raises clear error
- [x] `BgeM3FlagEmbeddingRuntime.embed_passages_sparse` uses `encode` with `return_sparse=True`
- [x] `BgeM3FlagEmbeddingRuntime.embed_query_sparse` uses `encode_queries` with `return_sparse=True`
- [x] `return_colbert_vecs=False` on all sparse calls
- [x] Optional dual encode avoids duplicate forward pass for indexing (implementation may use `embed_passages_dual`)
- [x] Sparse methods use same `EmbeddingRuntimeSettings` and shared model instance as dense methods

### Layer adapters

- [x] `SparseEmbeddingProvider` protocol defined in `indexing/embeddings.py`
- [x] `StubSparseEmbeddingProvider` and `BgeM3SparseEmbeddingProvider` implemented
- [x] `BgeM3SparseQueryEmbeddingProvider` implemented in `retrieval/embeddings.py`
- [x] Adapters do not import FlagEmbedding or torch
- [x] `sparse_placeholder_vector()` not used in `IndexingPipeline` production path

### Indexing pipeline

- [x] `IndexingPipeline` accepts `sparse_embedding_provider`
- [x] Each chunk receives distinct sparse vector from `embed_sparse_texts`
- [x] Dense validation behavior unchanged

### Bootstrap integration

- [x] `embedding_mode=stub` → stub sparse providers for indexing and retrieval
- [x] `embedding_mode=real` → shared runtime injected into dense and sparse adapters
- [x] `build_retrieval_stack` no longer hardcodes `StubSparseQueryEmbeddingProvider()`
- [x] Pipeline label reflects `sparse (bge-m3)` in real mode
- [x] Default CI/bootstrap uses stubs without model download

### Retrieval stack (unchanged orchestration)

- [x] `SparseRetriever` signature and behavior unchanged (except provider injection)
- [x] `FusionRetriever` unchanged
- [x] `RerankRetriever` unchanged

### Storage (unchanged)

- [x] No `VectorStore` protocol changes
- [x] Existing `search_sparse` and upsert tests pass

### Evaluation compatibility

- [x] No changes to `knowledge_assistant.evaluation` production modules
- [x] README documents reindex + `rag evaluate compare` expectation for sparse/fusion lift
- [x] Manual verification checklist: after reindex with `RAG_EMBEDDING_MODE=real`, sparse Hit@K > 0

### Import-boundary tests

- [x] AST tests extended for new modules
- [x] No `torch` / `FlagEmbedding` in `indexing/`, `retrieval/`, `cli/`, `mcp_server/`, `llm/`, `evaluation/` production code

### Validation

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes (default marker selection)
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Operators skip reindex after Plan 20 | ADR-084; `demo info` label; README; evaluation doc |
| FlagEmbedding `lexical_weights` shape changes | Pin version; isolate conversion in `sparse_conversion.py` |
| Empty sparse vector for short/noisy chunks | Fail fast at conversion; unit tests for edge cases |
| Double model forward pass on indexing | `embed_passages_dual` optimization |
| Stub/real sparse index mismatch | Couple sparse to `embedding_mode`; document unsupported mixed state |
| Fusion still ≈ dense if sparse signal weak | Accept as data/model outcome; evaluation compares strategies |
| Memory pressure from larger upsert payloads | Variable nnz ~20–200; monitor; same single model instance |
| Scope creep into ColBERT | Explicit non-scope |
| Accidental `FusionRetriever` changes | Code review against non-scope; leaf retriever tests unchanged |

---

## Implementation Steps

1. **Activate plan** — record ADR-081 through ADR-086 in `docs/DECISIONS.md`.
2. **Add sparse conversion** — `embeddings/sparse_conversion.py` + unit tests.
3. **Extend `BgeM3FlagEmbeddingRuntime`** — sparse methods; mocked unit tests.
4. **Add indexing sparse provider** — `SparseEmbeddingProvider`, stub + BGE adapters.
5. **Update `IndexingPipeline`** — inject sparse provider; per-chunk sparse vectors.
6. **Add `BgeM3SparseQueryEmbeddingProvider`** — retrieval adapter + unit tests.
7. **Update bootstrap** — sparse provider selection; `build_retrieval_stack` parameter; pipeline label.
8. **Update README / `.env.example` / ARCHITECTURE** — reindex workflow and evaluation expectations.
9. **Integration tests** — stub path pipeline; optional `@pytest.mark.embedding_model` smoke tests.
10. **Manual evaluation verification** — `RAG_EMBEDDING_MODE=real`, reindex, `rag evaluate compare`; confirm sparse > 0 and fusion ≠ dense on benchmark.
11. **Run validation suite** — all four quality commands.
12. **Update `docs/PROGRESS.md`** — record completion; move plan to `docs/plans/completed/`.

---

## Checklist

### Architectural decisions

- [x] ADR-081 — Real sparse embedding ownership
- [x] ADR-082 — BGE-M3 dual dense+sparse encoding in shared runtime
- [x] ADR-083 — Lexical weight to Qdrant sparse vector conversion
- [x] ADR-084 — Sparse migration requires full reindex
- [x] ADR-085 — Bootstrap sparse provider selection follows embedding mode
- [x] ADR-086 — Stub sparse providers remain default for CI

### Embeddings package

- [x] `sparse_conversion.py`
- [x] Runtime sparse methods on `BgeM3FlagEmbeddingRuntime`
- [x] Unit tests with mocked FlagEmbedding backend

### Indexing

- [x] `SparseEmbeddingProvider` / stub / BGE adapters
- [x] `IndexingPipeline` sparse provider injection
- [x] Pipeline unit/integration tests

### Retrieval

- [x] `BgeM3SparseQueryEmbeddingProvider`
- [x] Adapter unit tests

### Bootstrap

- [x] Sparse provider wiring in `build_demo_environment`
- [x] `build_retrieval_stack` sparse parameter
- [x] Pipeline label update
- [x] Bootstrap unit tests

### Documentation

- [x] `docs/ARCHITECTURE.md`
- [x] `docs/DECISIONS.md`
- [x] `docs/plans/backlog/ROADMAP.md`
- [x] `README.md`
- [x] `.env.example`

### Validation

- [x] ruff format / check
- [x] basedpyright
- [x] pytest (default)
- [x] Manual `rag evaluate compare` after reindex (operator checklist)
- [x] `docs/PROGRESS.md`
