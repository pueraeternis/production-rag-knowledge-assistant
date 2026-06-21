# Plan 06 — Dense Retrieval

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 4 — Retrieval

**Depends on:** [Plan 05 — Indexing Pipeline](../completed/05-indexing-pipeline.md)

---

## Post-Completion Note (2026-06-21)

Unit test modules use unique basenames (`test_retrieval_config.py`, `test_query_embeddings.py`, `test_retrieval_imports.py`) to avoid pytest module-name collisions with `tests/unit/indexing/` counterparts.

---

## Objective

Design and implement the first retrieval-layer capability: production-style dense retrieval over domain models.

```text
SearchQuery
    ↓
DenseRetriever
    ↓
QueryEmbeddingProvider
    ↓
VectorStore.search_dense()
    ↓
RetrievalResult
```

After this plan is complete, callers can submit natural-language `SearchQuery` values and receive typed `RetrievalResult` objects without handling vectors, Qdrant APIs, or embedding libraries.

The retrieval layer owns query embeddings. Storage remains embedding-agnostic (ADR-006, ADR-013). Callers work only with text queries; vectors are an internal retrieval concern and must not leak to MCP, agent, or other higher layers.

**Dependency rule:** `retrieval → VectorStore` protocol only — not `StorageSettings`, not `storage.models`, not `qdrant_client`.

---

## Scope

This plan authorizes retrieval-layer implementation only within `src/knowledge_assistant/retrieval/` and associated tests.

### In Scope

* `DenseRetriever` orchestrating query embedding and dense vector search;
* `QueryEmbeddingProvider` protocol (retrieval-local, separate from indexing `EmbeddingProvider`);
* `StubQueryEmbeddingProvider` — deterministic, hash-based, no model runtime;
* `DenseRetrievalSettings` with `dense_vector_size` validation;
* retrieval-specific exception types;
* unit tests for embedding generation, dimension validation, result assembly, and import boundaries;
* integration tests using a fake `VectorStore` (no Qdrant-specific behavior in retrieval tests);
* ADR entries for dense retrieval architecture decisions;
* brief `docs/ARCHITECTURE.md` update for the retrieval layer (dense path only).

---

## Non-Scope

This plan does **not** authorize:

* BM25 or sparse retrieval;
* `VectorStore.search_sparse` usage or protocol extension;
* result fusion (RRF, weighted merge, or Qdrant fusion);
* reranking (BAAI/bge-reranker-v2-m3 or any cross-encoder);
* real BAAI/bge-m3 query embedding integration;
* `torch`, `sentence-transformers`, `transformers`, or other model runtime dependencies;
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* CLI behavior;
* query rewriting or LLM calls;
* source attribution formatting (`SourceReference` construction or display);
* hybrid retrieval pipeline orchestration;
* changes to `knowledge_assistant.core` domain models;
* changes to `VectorStore` protocol or storage payload schema;
* direct `qdrant_client` imports in `knowledge_assistant.retrieval`;
* `StorageSettings` or other storage configuration types in `knowledge_assistant.retrieval`;
* reuse of indexing `EmbeddingProvider` or `StubEmbeddingProvider`;
* Docker Compose or smoke tests against live Qdrant from retrieval tests;
* exception hierarchy rooted at `AppError` (deferred to a future plan).

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-014 — Dense Retrieval Boundary

**Status:** Accepted (established by this plan)

#### Context

Plan 04 exposes `VectorStore.search_dense(vector, top_k)` as a storage primitive that accepts pre-computed vectors. ADR-013 assigns query-path embedding ownership to retrieval. Higher layers (MCP, agent) must not embed queries or call storage search primitives directly.

#### Decision

* Dense retrieval is implemented in `knowledge_assistant.retrieval`.
* `DenseRetriever` is the public orchestration entry point for dense search.
* Responsibilities:
  * accept `SearchQuery` (text + `top_k`);
  * generate query embeddings via `QueryEmbeddingProvider`;
  * validate embedding dimension against `DenseRetrievalSettings.dense_vector_size`;
  * call `VectorStore.search_dense(vector=..., top_k=query.top_k)`;
  * wrap `tuple[SearchResult, ...]` in `RetrievalResult`.
* The retrieval layer must **not** expose vectors to callers.
* Callers work only with text queries via `SearchQuery`.
* `DenseRetriever` must **not** expose:
  * `retrieve(vector)` or any vector-accepting public API;
  * passthrough wrappers around `search_dense`.
* Raw dense similarity scores from storage are returned unchanged in `SearchResult.score` (no fusion, no reranking).

**Architectural note — leaf retriever:**

`DenseRetriever` is a **leaf retriever** implementation. Future plans may introduce higher-level retrieval orchestrators (e.g. `FusionRetriever`) that compose `DenseRetriever` and other retrieval strategies without changing the `DenseRetriever` public API. This note is documentation only; Plan 06 does not add orchestrator types.

#### Consequences

* MCP and agent plans depend on `DenseRetriever.retrieve`, not on storage or embedding internals.
* Retrieval tests inject fake `VectorStore` and stub embedding providers without Qdrant.
* Future hybrid retrieval (Plan 08) composes `DenseRetriever` alongside other leaf retrievers behind a higher orchestrator without modifying `DenseRetriever.retrieve`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP calls `VectorStore.search_dense` directly | Violates component boundaries; pushes embedding into MCP |
| Storage accepts query text | Violates ADR-006; couples persistence to embedding models |
| Shared retriever returning raw vectors | Leaks infrastructure concerns to callers |
| Reuse indexing `EmbeddingProvider.embed_texts` for queries | Different ownership and call shape; blurs ADR-013 boundaries |

---

### ADR-015 — QueryEmbeddingProvider

**Status:** Accepted (established by this plan)

#### Context

ADR-013 separates write-path embeddings (indexing) from query-path embeddings (retrieval). Indexing defines `EmbeddingProvider.embed_texts` for batch chunk embedding. Retrieval needs a query-focused contract with a single-text entry point.

#### Decision

* Define a retrieval-local `QueryEmbeddingProvider` protocol in `retrieval/embeddings.py`:

```python
QueryEmbeddingVector = tuple[float, ...]

class QueryEmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> QueryEmbeddingVector:
        """Return one dense embedding for a search query."""
        ...
```

* Do **not** reuse indexing `EmbeddingProvider` or import from `knowledge_assistant.indexing.embeddings`.
* Real BAAI/bge-m3 query-path implementation is deferred to a future plan; it will implement this protocol.
* `DenseRetriever` depends on `QueryEmbeddingProvider`, not on indexing types.
* `llm/` is not the embedding owner for the query path (reinforces ADR-013).

#### Consequences

* Indexing and retrieval embedding contracts evolve independently.
* Retrieval unit tests mock `embed_query` without indexing package imports.
* Future BGE-M3 integration replaces `StubQueryEmbeddingProvider` within retrieval only.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Reuse indexing `EmbeddingProvider` | Different method (`embed_texts` vs `embed_query`); couples read/write paths |
| Shared embedding module in `core/` | Pollutes domain layer per ADR-001 |
| `EmbeddingProvider` in retrieval with alias import from indexing | Violates layer ownership per ADR-013 |

---

### ADR-016 — Stub Query Embeddings

**Status:** Accepted (established by this plan)

#### Context

Real BGE-M3 integration is deferred. Retrieval still needs a deterministic, testable query embedding implementation aligned with indexing stub philosophy (ADR-009) and default vector dimension (1024).

#### Decision

* Provide `StubQueryEmbeddingProvider` in `retrieval/embeddings.py`.
* Requirements:
  * deterministic;
  * hash-based (SHA-256 expansion);
  * no model runtime;
  * default dimension `1024` (matches `DEFAULT_DENSE_VECTOR_SIZE`, indexing stub, and storage schema).
* Algorithm mirrors `StubEmbeddingProvider` philosophy from Plan 05:
  1. Compute SHA-256 digest of query text (UTF-8).
  2. Expand digest bytes deterministically to `dimension` float components in `[-1.0, 1.0]`.
  3. L2-normalize the vector for cosine distance compatibility.
  4. Return `tuple[float, ...]` with length exactly `dimension`.
* `StubQueryEmbeddingProvider` is a development/testing stub, not a production embedding model.
* No real BGE-M3, `sentence-transformers`, `torch`, or `transformers` in this plan.

#### Consequences

* Retrieval tests run without GPU or model downloads.
* End-to-end dense retrieval against stub-indexed content is possible when indexing and retrieval use matching dimensions and compatible stub algorithms (same text → same vector on both paths only when the underlying hash algorithm matches; cross-layer semantic retrieval quality is not a Plan 06 goal).
* Plan 07+ sparse retrieval and Plan 08 fusion are unaffected.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Import `StubEmbeddingProvider` from indexing | Couples retrieval to indexing; violates ADR-015 |
| Random vectors per query | Non-deterministic; breaks reproducible tests |
| Zero vector placeholder | Poor cosine behavior; less representative of real embeddings |
| Real BGE-M3 in Plan 06 | Explicitly deferred; adds model runtime dependencies |

---

## Module Layout

Flat package structure under `src/knowledge_assistant/retrieval/`:

```text
src/knowledge_assistant/retrieval/
    __init__.py          # public exports only
    config.py            # DenseRetrievalSettings
    embeddings.py        # QueryEmbeddingProvider, StubQueryEmbeddingProvider
    exceptions.py        # retrieval-specific errors
    dense.py             # DenseRetriever orchestration
```

Do not create deep subpackages (`retrieval/providers/`, `retrieval/utils/`).

### Public API (`retrieval/__init__.py`)

Export intentionally:

* `DenseRetriever`
* `DenseRetrievalSettings`
* `QueryEmbeddingProvider`
* `StubQueryEmbeddingProvider`
* Retrieval exceptions used by callers

Do **not** export:

* internal helper functions;
* `QueryEmbeddingVector` type alias unless needed for typing re-exports (prefer keeping it module-local).

---

## API Design

### DenseRetrievalSettings

**Module:** `retrieval/config.py`

```python
@dataclass(frozen=True, slots=True)
class DenseRetrievalSettings:
    dense_vector_size: int = 1024
```

Validation in `__post_init__`:

* `dense_vector_size` must be `> 0`.

Default `1024` matches `DEFAULT_DENSE_VECTOR_SIZE` in `storage/collection.py` and `IndexingSettings.dense_vector_size`.

**Vector dimension ownership:**

Retrieval, indexing, and storage each own their own configuration (`DenseRetrievalSettings`, `IndexingSettings`, `StorageSettings` respectively). All three layers must be configured with the same `dense_vector_size` value. This duplication is **intentional** — it preserves layer independence per ADR-006 and ADR-013; no layer reads another layer's settings. Dimension mismatches are expected to **fail fast** via validation (`EmbeddingDimensionError` in retrieval before `search_dense`; `VectorDimensionError` in storage at upsert/search).

---

### QueryEmbeddingProvider and StubQueryEmbeddingProvider

**Module:** `retrieval/embeddings.py`

```python
QueryEmbeddingVector = tuple[float, ...]

class QueryEmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> QueryEmbeddingVector:
        ...

@dataclass(frozen=True, slots=True)
class StubQueryEmbeddingProvider:
    dimension: int = 1024

    def embed_query(self, text: str) -> QueryEmbeddingVector:
        ...
```

**`StubQueryEmbeddingProvider` algorithm:** identical expansion and L2-normalization steps as `StubEmbeddingProvider._embed_text` in indexing (see ADR-016). Implementation may extract shared logic only within `retrieval/embeddings.py` — do not import from indexing.

---

### DenseRetriever

**Module:** `retrieval/dense.py`

```python
class DenseRetriever:
    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: QueryEmbeddingProvider,
        settings: DenseRetrievalSettings,
    ) -> None: ...

    def retrieve(
        self,
        query: SearchQuery,
    ) -> RetrievalResult:
        ...
```

**Preferred public API:** `retrieve(query: SearchQuery) -> RetrievalResult` only.

**Forbidden public APIs:**

```python
def retrieve(self, vector: Sequence[float], ...) -> ...: ...  # NO
def search_dense(self, ...) -> ...: ...                         # NO
```

Storage-level `search_dense` remains internal to `DenseRetriever.retrieve`.

**`retrieve` behavior:**

1. Call `embedding_provider.embed_query(query.text)`.
2. Validate `len(vector) == settings.dense_vector_size`; raise `EmbeddingDimensionError` on mismatch.
3. Call `vector_store.search_dense(vector=vector, top_k=query.top_k)`.
4. Return `RetrievalResult(query=query, results=search_results)`.

**Score semantics:** `SearchResult.score` values are raw dense similarity scores from storage (cosine similarity from Qdrant in production). No score normalization or fusion in Plan 06.

**Empty results:** When storage returns `()`, return `RetrievalResult(query=query, results=())`. Empty results are valid.

**`top_k` forwarding:** Pass `query.top_k` unchanged to `search_dense`. Do not clamp or override unless storage returns more than `top_k` results (defensive slice allowed only if needed to satisfy `RetrievalResult` invariant `len(results) <= query.top_k`; storage is expected to respect `top_k`).

**Error propagation:** Storage exceptions (`CollectionNotFoundError`, `VectorDimensionError`, etc.) may propagate unchanged. Retrieval raises `EmbeddingDimensionError` before storage when the embedding provider returns wrong dimension.

---

### Exception Hierarchy (retrieval-local)

**Module:** `retrieval/exceptions.py`

```python
class RetrievalError(Exception): ...
class RetrievalConfigurationError(RetrievalError): ...
class EmbeddingDimensionError(RetrievalError): ...
```

`RetrievalConfigurationError` is reserved for invalid retrieval settings (e.g. future configuration validation beyond `dense_vector_size`). Plan 06 does not require raising it; establishing the hierarchy prepares later plans. `EmbeddingDimensionError` is raised when the embedding provider returns a vector whose length does not match `settings.dense_vector_size`.

Root `AppError` integration is deferred.

---

## Retrieval Flow

### Dense Retrieval Flow

```text
SearchQuery (text, top_k)
    ↓
DenseRetriever.retrieve()
    ↓
QueryEmbeddingProvider.embed_query(query.text)
    ↓
validate len(vector) == settings.dense_vector_size
    ↓
VectorStore.search_dense(vector=vector, top_k=query.top_k)
    ↓
tuple[SearchResult, ...]   # each SearchResult: chunk + raw dense score
    ↓
RetrievalResult(query=query, results=...)
```

### Boundary Responsibilities

| Layer | Input | Output | Embedding |
| ----- | ----- | ------ | --------- |
| Caller (future MCP/agent) | `SearchQuery` | `RetrievalResult` | none |
| `DenseRetriever` | `SearchQuery` | `RetrievalResult` | orchestrates |
| `QueryEmbeddingProvider` | `str` | `tuple[float, ...]` | generates |
| `VectorStore` | `vector`, `top_k` | `tuple[SearchResult, ...]` | none |

No fusion. No reranking. No sparse retrieval. No BM25. No LLM calls.

---

## Dependency Rules

### Allowed Dependencies (Production Code)

Production retrieval code may depend only on:

* `knowledge_assistant.core` (domain types: `SearchQuery`, `SearchResult`, `RetrievalResult`, `Chunk`, etc.);
* `knowledge_assistant.storage.protocol.VectorStore`;
* Python standard library.

Retrieval must **not** import any other `knowledge_assistant.storage` modules (`models`, `config`, `mapping`, `qdrant_store`, etc.). This aligns with Plan 04 storage boundaries: indexing and retrieval depend on the `VectorStore` protocol, not on Qdrant APIs or storage configuration types.

**Test code** (`tests/unit/retrieval/`, `tests/integration/retrieval/`) may import additional packages to build fakes and fixtures; import-boundary tests apply to `src/knowledge_assistant/retrieval/` only.

### Forbidden Dependencies

Retrieval production code must **not** import:

* `qdrant_client`;
* `knowledge_assistant.storage.config` / `StorageSettings`;
* `knowledge_assistant.storage.models` (e.g. `ChunkUpsertItem`, `SparseVector`);
* `knowledge_assistant.storage.mapping`;
* `knowledge_assistant.storage.qdrant_store`;
* `knowledge_assistant.indexing` (any submodule);
* `knowledge_assistant.agent`;
* `knowledge_assistant.mcp_server`;
* `knowledge_assistant.llm`;
* `llama_index` / `llama-index`;
* `torch`, `sentence_transformers`, `transformers`.

### Import-Boundary Tests

Add `tests/unit/retrieval/test_imports.py` mirroring indexing import guards:

* no `qdrant_client` references in `src/knowledge_assistant/retrieval/*.py`;
* no `StorageSettings`, `storage.config`, or other `knowledge_assistant.storage` imports except `storage.protocol`;
* no `knowledge_assistant.indexing` imports;
* no `llama_index` imports;
* no `langgraph`, `mcp`, or `openai` imports.

---

## Testing Strategy

| Level | Location | What is tested | VectorStore usage |
| ----- | -------- | -------------- | ----------------- |
| Unit | `tests/unit/retrieval/` | embedding stub, dimension validation, `RetrievalResult` assembly, import guards | None (mock `VectorStore` and `QueryEmbeddingProvider`) |
| Integration | `tests/integration/retrieval/` | `DenseRetriever` with fake `VectorStore` recording calls | `FakeVectorStore` protocol fake — no Qdrant |

**No Qdrant-specific behavior in retrieval tests.** Storage integration with Qdrant remains in `tests/integration/storage/`. Retrieval integration tests use a fake implementing `VectorStore`.

### Unit Tests (required)

* `StubQueryEmbeddingProvider.embed_query` returns vector of expected `dimension`;
* same query text → same vector (deterministic);
* L2-normalized stub vector has unit length (within float tolerance);
* `DenseRetriever.retrieve` calls `embed_query` with `query.text`;
* `DenseRetriever.retrieve` calls `search_dense` with embedded vector and `top_k=query.top_k`;
* dimension mismatch from provider raises `EmbeddingDimensionError` before `search_dense`;
* `retrieve` returns `RetrievalResult` with `query` echoed back;
* empty `search_dense` result yields `RetrievalResult` with `results=()`;
* non-empty results are propagated unchanged in order;
* `top_k` from `SearchQuery` is forwarded to `search_dense`;
* import-boundary validation (forbidden modules absent).

### Integration Tests (required)

Using `FakeVectorStore` in `tests/integration/retrieval/conftest.py`:

* `retrieve` invokes `embed_query` exactly once per call;
* `retrieve` invokes `search_dense` with vector length matching settings;
* `retrieve` forwards `query.top_k` to `search_dense`;
* results from fake store are propagated into `RetrievalResult.results`;
* empty fake results handled correctly (`results=()`);
* fake store records `search_dense` call arguments for assertion.

**`FakeVectorStore` design:**

* Implement `VectorStore` protocol methods (minimal stubs for unused methods);
* `search_dense` returns configurable `tuple[SearchResult, ...]`;
* record last `vector` and `top_k` passed to `search_dense`;
* optionally reuse patterns from `tests/integration/indexing/conftest.py` for `FakeVectorStore` structure, but place the retrieval fixture in `tests/integration/retrieval/conftest.py` to avoid cross-test coupling; test fixtures may import `storage.models` for protocol fakes — production retrieval code may not.

### Test Helpers

* Build minimal valid `SearchResult` / `Chunk` fixtures using core domain factories or inline construction (mirror patterns from `tests/unit/core/`).
* Use small `dense_vector_size` (e.g. `8` or `16`) in tests for readability.

**Not in scope:** Docker Qdrant; real BGE-M3; MCP tests; agent tests; fusion/reranking tests.

---

## Dependencies

Do **not** add new runtime dependencies for Plan 06.

Existing dependencies (`qdrant-client`, `llama-index-core`, etc.) remain unchanged. Retrieval production code uses only stdlib plus `core` and `storage.protocol` imports.

Do **not** add:

* `torch`
* `sentence-transformers`
* `transformers`
* `langgraph`
* `mcp`
* `openai`

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-014 through ADR-016 from this plan;
* `docs/ARCHITECTURE.md` — add Retrieval Layer section documenting dense retrieval boundary, module layout, query embedding ownership (ADR-013/ADR-015), and dependency flow (`retrieval → VectorStore`);
* `docs/PROGRESS.md` — record Plan 06 completion.

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Acceptance Criteria

- [x] `DenseRetriever` implements `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] `DenseRetriever` does not expose vector-accepting or `search_dense` public methods
- [x] `QueryEmbeddingProvider` protocol defined in `retrieval/embeddings.py` with `embed_query(text: str)`
- [x] `StubQueryEmbeddingProvider` implemented (hash-based, deterministic, default dimension 1024, L2-normalized)
- [x] Indexing `EmbeddingProvider` is not imported or reused in retrieval
- [x] `DenseRetrievalSettings` defined with `dense_vector_size: int = 1024` and validation
- [x] `DenseRetriever` validates embedding dimension before calling `search_dense`
- [x] `retrieve` forwards `query.top_k` to `search_dense`
- [x] `retrieve` returns `RetrievalResult` including echoed `SearchQuery`
- [x] Empty storage results return valid `RetrievalResult` with `results=()`
- [x] Raw dense scores from storage propagate unchanged in `SearchResult.score`
- [x] Production retrieval code depends only on `core`, `storage.protocol.VectorStore`, and stdlib
- [x] No other `knowledge_assistant.storage` module imports in `knowledge_assistant.retrieval`
- [x] No `qdrant_client` imports in `knowledge_assistant.retrieval`
- [x] `RetrievalError`, `RetrievalConfigurationError`, and `EmbeddingDimensionError` defined in `retrieval/exceptions.py`
- [x] No imports from `indexing`, `agent`, `mcp_server`, or `llm` in retrieval package
- [x] Unit tests exist in `tests/unit/retrieval/`
- [x] Integration tests exist in `tests/integration/retrieval/` using fake `VectorStore` only
- [x] Import-boundary tests exist in `tests/unit/retrieval/test_imports.py`
- [x] ADR-014 through ADR-016 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents retrieval layer dense path
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes with zero errors on `src/knowledge_assistant/retrieval/`
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Accidental reuse of indexing `EmbeddingProvider` | ADR-015 forbids it; import-boundary tests; separate protocol module |
| Vector dimension mismatch across layers | Retrieval (`DenseRetrievalSettings`), indexing (`IndexingSettings`), and storage (`StorageSettings`) each own their own `dense_vector_size`; callers must configure all three consistently; duplication is intentional for layer independence; fail fast via `EmbeddingDimensionError` (retrieval) and `VectorDimensionError` (storage) |
| Vector dimension mismatch at runtime | `DenseRetriever` validates before storage; `DenseRetrievalSettings.dense_vector_size`; tests for `EmbeddingDimensionError` |
| Vectors leak to MCP/agent APIs | ADR-014: text-only public contract; no `retrieve(vector)` |
| Retrieval tests coupled to Qdrant | Fake `VectorStore` only in retrieval integration tests |
| Stub query vs stub index embedding divergence | Document as acceptable for Plan 06; real BGE-M3 deferred; same algorithm family for determinism |
| Scope creep into sparse/fusion/reranking | Explicit non-scope; single `DenseRetriever` only |
| `RetrievalResult` invariant violated when storage over-fetches | Forward `top_k`; defensive slice only if storage returns excess (document if used) |
| Storage `CollectionNotFoundError` surfaces to callers | Acceptable; MCP layer will handle in Plan 10 |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-014 through ADR-016 from this plan in `docs/DECISIONS.md`.
2. **Create `exceptions.py`** — define `RetrievalError`, `RetrievalConfigurationError`, and `EmbeddingDimensionError`.
3. **Create `config.py`** — implement `DenseRetrievalSettings` with validation.
4. **Create `embeddings.py`** — implement `QueryEmbeddingProvider` protocol and `StubQueryEmbeddingProvider`.
5. **Create `dense.py`** — implement `DenseRetriever` with `retrieve` orchestration.
6. **Update `retrieval/__init__.py`** — export public API only.
7. **Add unit tests** — create `tests/unit/retrieval/` for embeddings, dimension validation, and retriever behavior with mocks.
8. **Add import guard tests** — create `tests/unit/retrieval/test_imports.py`.
9. **Add integration tests** — create `tests/integration/retrieval/` with `FakeVectorStore` fixture and end-to-end `DenseRetriever` tests.
10. **Update `docs/ARCHITECTURE.md`** — document retrieval layer boundary and dense flow.
11. **Run validation suite** — execute all four quality commands; fix issues until all pass.
12. **Update progress** — record completion in `docs/PROGRESS.md`.
13. **Verify non-scope compliance** — confirm no sparse, fusion, reranking, BGE-M3, MCP, agent, or indexing imports.

---

## Checklist

### Architectural Decisions (ADR-014 – ADR-016)

- [x] Transcribe ADR-014 (Dense Retrieval Boundary) into `docs/DECISIONS.md`
- [x] Transcribe ADR-015 (QueryEmbeddingProvider) into `docs/DECISIONS.md`
- [x] Transcribe ADR-016 (Stub Query Embeddings) into `docs/DECISIONS.md`

### Configuration and Exceptions

- [x] Create `retrieval/config.py` with `DenseRetrievalSettings`
- [x] Validate `dense_vector_size > 0`
- [x] Create `retrieval/exceptions.py` with `RetrievalError`, `RetrievalConfigurationError`, and `EmbeddingDimensionError`

### Query Embeddings

- [x] Create `retrieval/embeddings.py`
- [x] Define `QueryEmbeddingProvider` protocol with `embed_query`
- [x] Implement `StubQueryEmbeddingProvider` (hash-based, L2-normalized, default 1024)
- [x] Do not import indexing `EmbeddingProvider`

### Dense Retriever

- [x] Create `retrieval/dense.py`
- [x] Implement `DenseRetriever.__init__` with `vector_store`, `embedding_provider`, `settings`
- [x] Implement `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] Validate embedding dimension before `search_dense`
- [x] Forward `query.top_k` to storage
- [x] No public `retrieve(vector)` or `search_dense` methods

### Public API

- [x] Update `retrieval/__init__.py` with intentional exports
- [x] No vector or storage primitive leakage in exports

### Unit Tests

- [x] Create `tests/unit/retrieval/` package
- [x] Test `StubQueryEmbeddingProvider` dimension and determinism
- [x] Test L2 normalization of stub vectors
- [x] Test dimension validation raises `EmbeddingDimensionError`
- [x] Test `retrieve` returns `RetrievalResult`
- [x] Test empty result handling
- [x] Test `top_k` forwarding (mock/fake)
- [x] Create `tests/unit/retrieval/test_imports.py` for import boundaries

### Integration Tests

- [x] Create `tests/integration/retrieval/` package
- [x] Implement `FakeVectorStore` in `conftest.py`
- [x] Test `retrieve` invokes `embed_query`
- [x] Test `retrieve` invokes `search_dense` with correct arguments
- [x] Test result propagation
- [x] Test empty results from fake store
- [x] No Qdrant client usage in retrieval tests

### Validation Workflow

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes

### Documentation

- [x] Update `docs/ARCHITECTURE.md` with retrieval layer description
- [x] Update `docs/PROGRESS.md` with dense retrieval milestone

### Non-Scope Verification

- [x] No BM25 or sparse retrieval
- [x] No fusion or reranking
- [x] No BGE-M3 or model runtime dependencies
- [x] No MCP implementation
- [x] No LangGraph/agent implementation
- [x] No query rewriting or LLM calls
- [x] No source attribution formatting
- [x] No `qdrant_client`, `StorageSettings`, or other `storage` modules (except `storage.protocol`) in retrieval production code
- [x] No indexing package imports in retrieval
- [x] No changes to `VectorStore` protocol or core domain models
