# Plan 07 — Sparse Retrieval

**Status:** Completed

**Created:** 2026-06-21

**Revised:** 2026-06-21 — narrowed to sparse retrieval only; indexing and migration work deferred

**Roadmap:** Phase 4 — Retrieval

**Depends on:** [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)

**Architecture audit:** Incorporates findings from the pre-Plan-07 architecture audit (2026-06-21). No architectural blockers were identified.

**Plan principle:** One plan introduces one architectural capability. Plan 07 introduces **sparse retrieval** only.

---

## Objective

Design and implement the sparse retrieval path over lexical sparse vectors stored in Qdrant, extending the existing retrieval architecture without changing established boundaries.

```text
SearchQuery
    ↓
SparseRetriever
    ↓
SparseQueryEmbeddingProvider
    ↓
VectorStore.search_sparse()
    ↓
RetrievalResult
```

After this plan is complete:

* callers can run sparse (lexical) retrieval via `SparseRetriever.retrieve(SearchQuery)`;
* `VectorStore` exposes a localized `search_sparse` protocol extension;
* `QdrantVectorStore` implements sparse vector search;
* `DenseRetriever` remains unchanged as a composable leaf retriever.

Plan 07 does **not** modify indexing behavior, sparse document embedding generation, or reindex workflows.

**Dependency rule:** `retrieval → VectorStore` protocol only — not `StorageSettings`, not `storage.models`, not `qdrant_client`.

**Technology direction:** BGE-M3 sparse vectors via Qdrant named `sparse` slot (ADR-004). Not BM25, Elasticsearch, Whoosh, Tantivy, or separate lexical databases.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/retrieval/` — sparse retrieval orchestration and query sparse embeddings;
* `src/knowledge_assistant/storage/` — `search_sparse` protocol extension and Qdrant implementation;
* associated unit and integration tests;
* ADR entries and documentation updates.

### In Scope

* `VectorStore.search_sparse(...)` protocol extension (sixth protocol method);
* `QdrantVectorStore.search_sparse` implementation querying the `sparse` named vector;
* storage structural validation for sparse search inputs (`search_sparse` path only);
* `SparseRetriever` orchestration mirroring `DenseRetriever`;
* retrieval-local `SparseQueryVector` type and `SparseQueryEmbeddingProvider` protocol;
* `StubSparseQueryEmbeddingProvider` — deterministic, hash-based, no model runtime;
* unit tests: sparse query provider, `SparseQueryVector` validation, `SparseRetriever`, import boundaries;
* integration tests: `SparseRetriever` + fake `VectorStore`; Qdrant sparse search;
* ADR entries ADR-017 through ADR-019;
* documentation note for future sparse indexing and reindex constraint (ADR-020, documentation only);
* `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` updates.

---

## Non-Scope

This plan does **not** authorize:

* **indexing changes** of any kind (`indexing/embeddings.py`, `indexing/pipeline.py`, constructor changes, sparse placeholder removal);
* **`SparseEmbeddingProvider`** or **`StubSparseEmbeddingProvider`** (indexing write path);
* **reindex migration implementation** or rebuild workflow changes;
* **sparse document embedding generation** (write path);
* fusion (RRF, weighted merge, Qdrant native fusion);
* `FusionRetriever` or any hybrid orchestrator;
* reranking (BAAI/bge-reranker-v2-m3 or any cross-encoder);
* real BAAI/bge-m3 model runtime (`torch`, `sentence-transformers`, `transformers`);
* BM25 index, Elasticsearch, Whoosh, Tantivy, or separate lexical databases;
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* CLI behavior;
* query rewriting or LLM calls;
* source attribution formatting;
* changes to `knowledge_assistant.core` domain models (`SearchQuery`, `SearchResult`, `RetrievalResult`);
* modifications to `DenseRetriever`, `QueryEmbeddingProvider`, or `DenseRetrievalSettings`;
* modifications to `SparseVector` upsert validation in `storage/models.py` (unchanged from Plan 04);
* shared `Retriever` protocol (deferred to Plan 08);
* cross-layer index→retrieve end-to-end integration test;
* Docker Compose or smoke tests against live Qdrant from retrieval tests;
* exception hierarchy rooted at `AppError` (deferred).

---

## Future Constraint (Documentation Only)

The following is recorded for future plans. Plan 07 does **not** implement it.

* ADR-010 stores a constant sparse placeholder `SparseVector(indices=(0,), values=(1.0,))` on every indexed chunk today.
* Meaningful sparse retrieval requires per-chunk sparse embeddings aligned with query sparse embeddings.
* A **future plan** (sparse indexing / embedding generation) must replace the placeholder and will require a **full reindex** with caller approval per ADR-012.
* Until that future plan completes, `SparseRetriever` can be tested against handcrafted or integration-test sparse vectors; production sparse retrieval quality against placeholder-indexed corpora is not meaningful.

This constraint is documented in ADR-020 and `docs/ARCHITECTURE.md`. No migration code is a Plan 07 deliverable.

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-017 — Sparse Retrieval Boundary

**Status:** Accepted (established by this plan)

#### Context

Plan 04 defers `search_sparse` to Plan 07 (ADR-004). ADR-013 assigns query-path embedding ownership to retrieval. ADR-014 establishes the dense leaf-retriever pattern. Sparse retrieval must mirror dense retrieval without coupling retrieval to `storage.models` (architecture audit Finding 3).

#### Decision

* Sparse retrieval is implemented in `knowledge_assistant.retrieval`.
* `SparseRetriever` is the public orchestration entry point for sparse search.
* Responsibilities:
  * accept `SearchQuery` (text + `top_k`);
  * generate query sparse embeddings via `SparseQueryEmbeddingProvider`;
  * validate sparse query representation via retrieval-local rules;
  * call `VectorStore.search_sparse(indices=..., values=..., top_k=query.top_k)`;
  * wrap `tuple[SearchResult, ...]` in `RetrievalResult`.
* The retrieval layer must **not** expose sparse vectors to callers.
* Callers work only with text queries via `SearchQuery`.
* `SparseRetriever` must **not** expose:
  * `retrieve(indices, values)` or any vector-accepting public API;
  * passthrough wrappers around `search_sparse`.
* Raw sparse similarity scores from storage are returned unchanged in `SearchResult.score` (no fusion, no reranking).
* `SparseRetriever` is a **leaf retriever**; Plan 08 may compose it alongside `DenseRetriever` without changing its public API.
* `DenseRetriever` must remain **unchanged** by this plan.

#### Consequences

* MCP and agent plans can depend on `SparseRetriever.retrieve`, not on storage or sparse embedding internals.
* Retrieval tests inject fake `VectorStore` and stub sparse providers without Qdrant.
* Plan 08 composes `DenseRetriever` and `SparseRetriever` as peer leaf retrievers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP calls `VectorStore.search_sparse` directly | Violates component boundaries; pushes embedding into MCP |
| Storage accepts query text | Violates ADR-006; couples persistence to embedding models |
| `SparseRetriever` imports `storage.models.SparseVector` | Violates retrieval boundary per Plan 06 and audit Finding 3 |
| Single `HybridRetriever` replacing leaf retrievers | Premature; fusion belongs in Plan 08 |

---

### ADR-018 — SparseQueryEmbeddingProvider

**Status:** Accepted (established by this plan)

#### Context

ADR-015 defines `QueryEmbeddingProvider` for dense query embeddings. Sparse query embeddings require a separate contract with different output shape (indices + values, not fixed-dimension dense vectors). Indexing embedding providers must not be reused for the query path (ADR-013).

#### Decision

* Define retrieval-local types and protocol in `retrieval/sparse_vectors.py` and `retrieval/embeddings.py`:

```python
@dataclass(frozen=True, slots=True)
class SparseQueryVector:
    indices: tuple[int, ...]
    values: tuple[float, ...]
    # __post_init__: structural validation + non-empty (retrieval-owned)

class SparseQueryEmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> SparseQueryVector:
        """Return one sparse embedding for a search query."""
        ...
```

* Do **not** import `storage.models.SparseVector` in retrieval production code.
* Do **not** import from `knowledge_assistant.indexing.embeddings`.
* Real BAAI/bge-m3 sparse query-path implementation is deferred; it will implement this protocol.
* `SparseRetriever` depends on `SparseQueryEmbeddingProvider`, not on indexing types.
* `llm/` is not the embedding owner for the sparse query path (reinforces ADR-013).

#### Consequences

* Indexing and retrieval sparse contracts evolve independently.
* Retrieval unit tests mock `embed_query` without indexing package imports.
* Future BGE-M3 integration replaces `StubSparseQueryEmbeddingProvider` within retrieval only.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Reuse indexing write-path sparse provider | Different ownership; couples read/write paths; indexing provider does not exist yet |
| Return `storage.models.SparseVector` from provider | Couples retrieval to storage write boundary types |
| Shared sparse module in `core/` | Pollutes domain layer per ADR-001 |
| Primitives only, no `SparseQueryVector` | Loses retrieval-local validation; error-prone at orchestration boundary |

---

### ADR-019 — Sparse Embedding Ownership

**Status:** Accepted (established by this plan)

#### Context

ADR-013 establishes dense embedding ownership. Sparse vectors have parallel write-path (indexing) and query-path (retrieval) responsibilities. Without explicit sparse ownership documentation, future plans could blur boundaries.

#### Decision

```text
Indexing owns write-path sparse embeddings (document chunks).  [future plan]
Retrieval owns query-path sparse embeddings (search queries).   [Plan 07]
Storage owns neither.
```

* **Retrieval (Plan 07)** generates sparse embeddings for user queries before `VectorStore.search_sparse`, via `SparseQueryEmbeddingProvider.embed_query`, using retrieval-local `SparseQueryVector` only.
* **Indexing (future plan)** will generate sparse embeddings for document chunks before `VectorStore.upsert_chunks`. Plan 07 does not implement indexing sparse generation. ADR-010 placeholder remains in place.
* **Storage** receives pre-computed sparse `indices` and `values` on search; receives `SparseVector` on upsert from indexing (unchanged). Storage does not generate sparse embeddings.
* The `llm/` package is not the sparse embedding owner for either path.

#### Consequences

* Plan 07 delivers query-path sparse retrieval without coupling to indexing implementation.
* Storage remains a passive vector store for sparse search primitives.
* A future sparse indexing plan can implement write-path generation independently.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Implement write-path sparse in Plan 07 | Violates one-capability-per-plan principle |
| Single shared `SparseEmbeddingProvider` in `core/` | Pollutes domain layer per ADR-001 |
| Storage generates query sparse vectors | Violates ADR-006 |

---

### ADR-020 — Reindex Requirement for Future Sparse Migration

**Status:** Accepted (documentation only — no Plan 07 implementation)

#### Context

ADR-010 stores a constant sparse placeholder on every chunk. Meaningful sparse retrieval requires per-chunk sparse vectors aligned with query sparse encoding. This migration is a future concern, not a Plan 07 deliverable.

#### Decision

* When a future plan replaces ADR-010 placeholders with real per-chunk sparse encoding, a **full reindex** will be required.
* Recovery path (future): caller-approved `index_documents(..., rebuild=True)`.
* Partial sparse vector updates or in-place migration are **not** planned.
* Sparse retrieval against placeholder-indexed corpora produces meaningless sparse rankings until that future migration completes.
* Dense retrieval is unaffected (sparse slot ignored by `search_dense`).

#### Consequences

* Plan 07 can ship sparse retrieval infrastructure without blocking on indexing changes.
* Operators will need a future reindex window before production sparse retrieval against real corpora.
* Plan 08 fusion requires meaningful sparse data from a future indexing plan for useful hybrid results.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Bundle migration into Plan 07 | Scope expansion; mixes retrieval with indexing |
| In-place sparse vector patch | Out of scope; adds complexity |
| Lazy reindex on first sparse query | Violates human-in-the-loop |

---

## Design Evaluations

### Sparse Query Representation (Protocol vs Retrieval-Local)

#### Option A — Primitive sequences in `search_sparse`

```python
def search_sparse(
    self,
    *,
    indices: Sequence[int],
    values: Sequence[float],
    top_k: int,
) -> tuple[SearchResult, ...]: ...
```

#### Option B — Retrieval-local object in protocol

```python
def search_sparse(
    self,
    *,
    sparse_vector: SparseQueryVector,
    top_k: int,
) -> tuple[SearchResult, ...]: ...
```

#### Decision

**Option A for the `VectorStore` protocol.** `search_sparse` accepts primitive `indices` and `values` sequences.

**Option B internally in retrieval only.** `SparseQueryEmbeddingProvider.embed_query` returns retrieval-local `SparseQueryVector`. `SparseRetriever` unpacks to primitives for `search_sparse`.

Retrieval never imports `storage.models`.

---

### Empty Sparse Vector Handling

#### Questions

| Question | Answer |
| -------- | ------ |
| Is an empty sparse query always invalid? | **For retrieval, yes.** `SearchQuery` requires non-empty text; a well-formed query sparse embedding must have at least one non-zero term. An empty sparse vector carries no lexical signal. |
| Should retrieval own this decision? | **Yes.** Non-empty is a retrieval contract enforced by `SparseQueryVector.__post_init__`, raising `SparseVectorValidationError`. |
| Should storage reject empty sparse vectors? | **No, not in Plan 07.** Storage `search_sparse` is a passive primitive. An empty sparse query can validly return `()` without calling Qdrant with malformed intent. Retrieval never sends empty vectors in normal operation. |
| Would allowing empty at storage make future implementations easier? | **Yes.** Storage stays embedding-agnostic and does not encode retrieval semantics. Future callers (tests, diagnostics) can probe empty-input behavior without new storage exceptions. |

#### Decision

| Layer | Empty sparse handling | Owner |
| ----- | --------------------- | ----- |
| `SparseQueryVector` (retrieval) | **Reject** non-empty invariant: `len(indices) >= 1` | Retrieval |
| `StubSparseQueryEmbeddingProvider` | Always produces non-empty output for non-empty query text | Retrieval |
| `search_sparse` (storage) | **Allow**; structural validation only; empty input returns `()` without error | Storage |
| `SparseVector` upsert (storage) | **Unchanged** from Plan 04; no new non-empty rule in Plan 07 | Storage (existing) |

**Do not introduce `EmptySparseVectorError`.** Retrieval uses `SparseVectorValidationError` for empty query sparse vectors. Storage uses existing `ValueError` for structural violations (length mismatch, duplicate indices, negative indices) on the `search_sparse` path only.

**Rationale:** Non-empty is a **semantic** rule about query quality, not a storage invariant. Dense retrieval does not add storage-level rejection of zero vectors; sparse follows the same split. Keeping storage passive preserves ADR-006 and avoids coupling persistence to retrieval policy.

---

### SparseRetrievalSettings

#### Options

| Option | Assessment |
| ------ | ---------- |
| **A — Remove entirely** | `DenseRetriever` needs `DenseRetrievalSettings` for `dense_vector_size` validation before `search_dense`. Sparse retrieval has **no analogous configuration** in Plan 07 — no fixed dimension, no tunable parameter required for stub or protocol implementation. |
| **B — Keep empty settings object for symmetry** | Adds a type with no fields and no behavior; violates YAGNI; forces meaningless constructor parameter. |

#### Decision

**Option A — Remove `SparseRetrievalSettings`.**

`SparseRetriever.__init__` accepts only `vector_store` and `embedding_provider`, mirroring the meaningful dependencies of `DenseRetriever` without a vacuous settings object. If a future BGE-M3 plan introduces sparse tuning knobs (e.g. `max_query_terms`), a settings type can be added then.

---

### Storage Validation Rules (`search_sparse` path only)

Plan 07 extends validation **only** for sparse search inputs. Upsert validation in `storage/models.py` is **unchanged**.

| Rule | `search_sparse` primitives | Owner |
| ---- | -------------------------- | ----- |
| `len(indices) == len(values)` | ✅ enforce | Storage |
| Indices unique | ✅ enforce | Storage |
| Indices `>= 0` | ✅ enforce | Storage |
| Non-empty | ❌ not enforced | Retrieval owns semantic rule |
| Values finite (no NaN/Inf) | ✅ enforce | Storage |
| Lexical correctness | ❌ not validated | Embedding providers |

Implementation: shared helper `validate_sparse_search_input(indices, values)` in `storage/` (e.g. `qdrant_store.py` module-local or `storage/validation.py` if preferred). Raises `ValueError` on structural violation.

`SparseRetriever` validates via `SparseQueryVector` before calling storage (fail fast with `SparseVectorValidationError`).

---

### Retrieval Result Semantics

**No changes** to core domain models:

| Type | Plan 07 impact |
| ---- | -------------- |
| `SearchQuery` | Unchanged |
| `SearchResult` | Unchanged — raw sparse scores from Qdrant |
| `RetrievalResult` | Unchanged — invariant `len(results) <= query.top_k` preserved |

Plan 08 fusion composes leaf `RetrievalResult` values without core model changes.

---

## Module Layout

### Retrieval (new and modified files)

```text
src/knowledge_assistant/retrieval/
    __init__.py           # add sparse exports; update module docstring
    embeddings.py         # add SparseQueryEmbeddingProvider, StubSparseQueryEmbeddingProvider
    sparse_vectors.py     # NEW: SparseQueryVector
    sparse.py             # NEW: SparseRetriever orchestration
    exceptions.py         # add SparseVectorValidationError
    config.py             # UNCHANGED (no SparseRetrievalSettings)
    dense.py              # UNCHANGED
```

Do not create `retrieval/utils/` or `retrieval/providers/` subpackages.

### Storage (modified files)

```text
src/knowledge_assistant/storage/
    protocol.py           # add search_sparse (sixth method)
    qdrant_store.py       # implement search_sparse + structural validation helper
```

`storage/models.py`, `storage/exceptions.py` — **unchanged** in Plan 07.

### Indexing

**No modifications.** `sparse_placeholder_vector()` remains until a future plan.

`FakeVectorStore` in `tests/integration/indexing/conftest.py` may receive a minimal `search_sparse` stub **only** for `VectorStore` protocol conformance when the protocol extends — this is test infrastructure, not indexing feature work.

---

## API Design

### VectorStore Protocol Extension

**Module:** `storage/protocol.py`

After Plan 07, the protocol defines **six** methods:

```python
class VectorStore(Protocol):
    def create_collection(self) -> None: ...
    def delete_collection(self) -> None: ...
    def collection_exists(self) -> bool: ...
    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None: ...
    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]: ...
    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        """Search the sparse named vector. Returns domain chunks with similarity scores."""
        ...
```

**`search_sparse` does not accept `SearchQuery`.** Storage accepts `indices`, `values`, and `top_k` only (ADR-006).

**`search_sparse` returns `SearchResult`:** same shape as `search_dense`. Scores are raw sparse similarity from Qdrant.

---

### QdrantVectorStore.search_sparse

**Module:** `storage/qdrant_store.py`

Behavior:

1. Raise `CollectionNotFoundError` if collection does not exist.
2. Raise `ValueError` if `top_k < 1`.
3. If `len(indices) == 0`: return `()` immediately (no Qdrant call).
4. Validate structural invariants via helper (length match, unique indices, non-negative indices, finite values).
5. Call `self._client.query_points` with `using=SPARSE_VECTOR_NAME` and `query=models.SparseVector(indices=list(indices), values=list(values))`.
6. Map scored points to `SearchResult` using existing `payload_to_chunk` path.
7. Return `tuple[SearchResult, ...]` ordered by Qdrant score descending.

No Qdrant fusion. Single sparse vector search only.

---

### SparseQueryVector

**Module:** `retrieval/sparse_vectors.py`

```python
@dataclass(frozen=True, slots=True)
class SparseQueryVector:
    indices: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        # len(indices) == len(values)
        # indices unique
        # all indices >= 0
        # len(indices) >= 1  (non-empty — retrieval-owned semantic rule)
        # all values finite
```

Violations raise `SparseVectorValidationError` (retrieval) when constructed from provider output in `SparseRetriever`, or `ValueError` from `__post_init__` if used directly in tests.

---

### StubSparseQueryEmbeddingProvider

**Module:** `retrieval/embeddings.py`

Deterministic hash-based sparse query embedding stub (no model runtime):

1. Normalize query text (strip; UTF-8).
2. Tokenize on whitespace.
3. For each term (up to a fixed cap, e.g. 32), derive stable index via hashed term modulo a large constant.
4. Accumulate term weights; deduplicate colliding indices by summing weights.
5. Normalize values for stable dot-product behavior.
6. Return `SparseQueryVector(indices=..., values=...)`.

Requirements: deterministic; non-empty for non-empty query text; no model runtime dependencies.

---

### SparseRetriever

**Module:** `retrieval/sparse.py`

```python
class SparseRetriever:
    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: SparseQueryEmbeddingProvider,
    ) -> None: ...

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        ...
```

No `SparseRetrievalSettings` parameter. See design evaluation above.

**`retrieve` behavior:**

1. Call `embedding_provider.embed_query(query.text)` → `SparseQueryVector`.
2. Validate via `SparseQueryVector` construction (`SparseVectorValidationError` on invalid output).
3. Call `vector_store.search_sparse(indices=..., values=..., top_k=query.top_k)`.
4. Defensive slice if `len(search_results) > query.top_k` (mirror `DenseRetriever`).
5. Return `RetrievalResult(query=query, results=search_results)`.

**Forbidden public APIs:** vector-accepting `retrieve`, public `search_sparse` passthrough.

---

### Exception Hierarchy

**Retrieval (`retrieval/exceptions.py`):**

```python
class SparseVectorValidationError(RetrievalError): ...
```

Raised when `SparseQueryVector` validation fails, including empty sparse query vectors.

**Storage:** no new exception types in Plan 07. Structural violations on `search_sparse` raise `ValueError`.

---

### Public API Exports

**`retrieval/__init__.py`:**

* `SparseRetriever`
* `SparseQueryEmbeddingProvider`
* `StubSparseQueryEmbeddingProvider`
* `SparseVectorValidationError`

Do **not** export `SparseQueryVector` unless needed for typing re-exports (prefer module-local).

Update module docstring to reflect sparse retrieval capability (architecture audit Finding 10).

---

## Retrieval Flow

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
tuple[SearchResult, ...]
    ↓
RetrievalResult(query=query, results=...)
```

### Leaf Retriever Composition (Plan 08 — documentation only)

```text
DenseRetriever.retrieve(query)   ─┐
                                  ├─→ FusionRetriever (Plan 08)
SparseRetriever.retrieve(query)  ─┘
```

### Boundary Responsibilities

| Layer | Input | Output | Sparse embedding |
| ----- | ----- | ------ | ---------------- |
| Caller | `SearchQuery` | `RetrievalResult` | none |
| `SparseRetriever` | `SearchQuery` | `RetrievalResult` | orchestrates |
| `SparseQueryEmbeddingProvider` | `str` | `SparseQueryVector` | generates |
| `VectorStore.search_sparse` | `indices`, `values`, `top_k` | `tuple[SearchResult, ...]` | none |

No fusion. No reranking. No LLM calls. No indexing changes.

---

## Dependency Rules

### Allowed Dependencies (Retrieval Production Code)

* `knowledge_assistant.core`;
* `knowledge_assistant.storage.protocol.VectorStore`;
* Python standard library.

### Forbidden Dependencies (Retrieval)

* `qdrant_client`;
* `knowledge_assistant.storage.config` / `StorageSettings`;
* `knowledge_assistant.storage.models`;
* `knowledge_assistant.storage.mapping`;
* `knowledge_assistant.storage.qdrant_store`;
* `knowledge_assistant.indexing` (any submodule);
* `knowledge_assistant.agent`;
* `knowledge_assistant.mcp_server`;
* `knowledge_assistant.llm`;
* `llama_index` / `llama-index`;
* `torch`, `sentence_transformers`, `transformers`.

### Import-Boundary Tests

Extend `tests/unit/retrieval/test_retrieval_imports.py` to assert `storage.models` is not referenced in retrieval production code.

---

## Testing Strategy

| Level | Location | What is tested |
| ----- | -------- | -------------- |
| Unit | `tests/unit/retrieval/` | sparse query provider, `SparseQueryVector`, `SparseRetriever`, import guards |
| Unit | `tests/unit/storage/` | `search_sparse` structural validation; empty-input returns `()` |
| Integration | `tests/integration/retrieval/` | `SparseRetriever` + `FakeVectorStore` |
| Integration | `tests/integration/storage/` | Qdrant sparse search lifecycle |

**No indexing sparse tests.** No reindex migration tests.

### Unit Tests — Retrieval (required)

* `StubSparseQueryEmbeddingProvider` returns valid non-empty `SparseQueryVector`;
* deterministic embedding for same text;
* `SparseQueryVector` rejects empty, mismatched, duplicate, and negative indices;
* `SparseRetriever.retrieve` calls `embed_query` and `search_sparse` with correct arguments;
* `SparseVectorValidationError` raised for invalid provider output before `search_sparse`;
* `retrieve` returns `RetrievalResult`; empty storage results → `results=()`;
* `DenseRetriever` tests unchanged;
* import-boundary guards pass.

Use unique test module basenames (e.g. `test_sparse_embeddings.py`, `test_sparse_retriever.py`).

### Unit Tests — Storage (required)

* `search_sparse` structural validation rejects length mismatch, duplicate indices, negative indices;
* `search_sparse` with `indices=()` returns `()` without error;
* `search_sparse` raises `CollectionNotFoundError` when collection missing (integration-level also).

### Integration Tests — Retrieval (required)

* `FakeVectorStore` in `tests/integration/retrieval/conftest.py` implements `search_sparse`;
* `retrieve` invokes `embed_query` once and forwards `indices`, `values`, `top_k`;
* results propagated correctly; empty fake results handled.

### Integration Tests — Storage (required)

* create → upsert with distinct handcrafted sparse vectors → `search_sparse` returns ordered `SearchResult`;
* sparse search ranking differs from dense when vectors differ;
* empty sparse query returns `()`;
* `CollectionNotFoundError` on missing collection.

**`FakeVectorStore` protocol conformance:** add minimal `search_sparse` stub to `tests/integration/indexing/conftest.py` only so existing indexing integration tests continue to satisfy the extended protocol. No new indexing sparse behavior tests.

**Not in scope:** indexing sparse generation tests; reindex migration tests; Docker Qdrant; real BGE-M3; MCP; fusion.

---

## Dependencies

Do **not** add new runtime dependencies for Plan 07.

Do **not** add `torch`, `sentence-transformers`, `transformers`, `langgraph`, `mcp`, or `openai`.

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-017 through ADR-020;
* `docs/ARCHITECTURE.md`:
  * sparse retrieval path diagram and module table;
  * `SparseRetriever` leaf alongside `DenseRetriever`;
  * `search_sparse` protocol extension (six methods);
  * retrieval must not import `storage.models`; indexing may (unchanged note);
  * replace "BM25 Search" with "Sparse Search (BGE-M3 lexical vectors)" in hybrid diagram;
  * document future constraint: placeholder sparse vectors until future indexing plan; reindex required for migration (ADR-020);
* `docs/PROGRESS.md` — record Plan 07 completion.

Do not update `docs/plans/backlog/ROADMAP.md`.

---

## Acceptance Criteria

### Protocol and Storage

- [x] `VectorStore` protocol defines **six** methods including `search_sparse`
- [x] `search_sparse` accepts primitive `indices` and `values` — not `storage.models.SparseVector`
- [x] `search_sparse` does not accept query text
- [x] `QdrantVectorStore.search_sparse` queries the `sparse` named vector via `query_points`
- [x] `search_sparse` returns `tuple[SearchResult, ...]` with reconstructed `Chunk` objects
- [x] `search_sparse` enforces structural validation (length match, unique indices, non-negative indices, finite values)
- [x] `search_sparse` returns `()` for empty `indices` without error
- [x] `storage/models.py` and upsert validation unchanged
- [x] No `EmptySparseVectorError` introduced
- [x] Storage does not generate sparse embeddings
- [x] No Qdrant fusion in sparse search

### Sparse Retrieval

- [x] `SparseRetriever` implements `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] `SparseRetriever` accepts `vector_store` and `embedding_provider` only — no settings object
- [x] `SparseRetriever` does not expose vector-accepting or `search_sparse` public methods
- [x] `SparseQueryEmbeddingProvider` protocol with `embed_query(text: str) -> SparseQueryVector`
- [x] `SparseQueryVector` defined in retrieval package only
- [x] `SparseQueryVector` rejects empty sparse vectors (`SparseVectorValidationError`)
- [x] `StubSparseQueryEmbeddingProvider` implemented (deterministic, non-empty for non-empty text, no model runtime)
- [x] `SparseVectorValidationError` defined in `retrieval/exceptions.py`
- [x] Raw sparse scores propagate unchanged in `SearchResult.score`
- [x] `DenseRetriever` and its tests remain unchanged

### Domain Models and Boundaries

- [x] `SearchQuery`, `SearchResult`, `RetrievalResult` unchanged in `core`
- [x] Production retrieval code depends only on `core`, `storage.protocol.VectorStore`, and stdlib
- [x] No `storage.models` imports in `knowledge_assistant.retrieval`
- [x] No `qdrant_client` imports in `knowledge_assistant.retrieval`
- [x] No imports from `indexing`, `agent`, `mcp_server`, or `llm` in retrieval package
- [x] No modifications to `knowledge_assistant.indexing` production code

### Tests

- [x] Unit tests in `tests/unit/retrieval/` for sparse provider, validation, and `SparseRetriever`
- [x] Unit tests in `tests/unit/storage/` for `search_sparse` validation and empty-input behavior
- [x] Integration tests in `tests/integration/retrieval/` with `FakeVectorStore` implementing `search_sparse`
- [x] Integration tests in `tests/integration/storage/` for Qdrant sparse search
- [x] Import-boundary tests extended for retrieval `storage.models` prohibition
- [x] `FakeVectorStore` in retrieval conftest updated; indexing conftest updated for protocol conformance only

### Validation and Documentation

- [x] ADR-017 through ADR-020 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents sparse retrieval path and future placeholder constraint
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes on modified packages
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Retrieval imports `storage.models` | ADR-017/018; import-boundary tests; primitive protocol signature |
| Placeholder-indexed corpora yield meaningless sparse results | Document future constraint (ADR-020); defer to future indexing plan |
| `FakeVectorStore` protocol drift | Update retrieval conftest; minimal stub in indexing conftest for conformance |
| Stub sparse unlike real BGE-M3 | Contract shape only; real model is future plan |
| Scope creep into indexing or migration | Explicit non-scope; one capability per plan |
| `DenseRetriever` accidental modification | Acceptance criterion: dense tests unchanged |
| Empty sparse at storage vs retrieval | Documented split: retrieval rejects; storage allows and returns `()` |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-017 through ADR-020 in `docs/DECISIONS.md`.
2. **Extend protocol** — add `search_sparse` to `storage/protocol.py`.
3. **Implement Qdrant sparse search** — add `search_sparse` and structural validation helper to `qdrant_store.py`.
4. **Add storage unit tests** — `search_sparse` validation and empty-input behavior.
5. **Add storage integration tests** — Qdrant sparse search lifecycle in `tests/integration/storage/`.
6. **Create `retrieval/sparse_vectors.py`** — implement `SparseQueryVector` with non-empty rule.
7. **Extend `retrieval/exceptions.py`** — add `SparseVectorValidationError`.
8. **Extend `retrieval/embeddings.py`** — add `SparseQueryEmbeddingProvider` and `StubSparseQueryEmbeddingProvider`.
9. **Create `retrieval/sparse.py`** — implement `SparseRetriever` (no settings parameter).
10. **Update `retrieval/__init__.py`** — export sparse public API; update module docstring.
11. **Add retrieval unit tests** — provider, validation, retriever, import guards.
12. **Add retrieval integration tests** — `FakeVectorStore` with `search_sparse` in retrieval conftest.
13. **Update indexing `FakeVectorStore`** — minimal `search_sparse` stub in indexing conftest for protocol conformance only.
14. **Update `docs/ARCHITECTURE.md`** — sparse path, protocol, future placeholder constraint, BM25 label fix.
15. **Run validation suite** — all four quality commands; fix until pass.
16. **Update progress** — record completion in `docs/PROGRESS.md`.
17. **Verify non-scope compliance** — no indexing changes, no migration, no fusion, no `DenseRetriever` changes.

---

## Checklist

### Architectural Decisions

- [x] Transcribe ADR-017 (Sparse Retrieval Boundary) into `docs/DECISIONS.md`
- [x] Transcribe ADR-018 (SparseQueryEmbeddingProvider) into `docs/DECISIONS.md`
- [x] Transcribe ADR-019 (Sparse Embedding Ownership) into `docs/DECISIONS.md`
- [x] Transcribe ADR-020 (Future Reindex Constraint, documentation only) into `docs/DECISIONS.md`

### Storage

- [x] Add `search_sparse` to `storage/protocol.py`
- [x] Implement `QdrantVectorStore.search_sparse`
- [x] Structural validation helper for search inputs
- [x] Empty `indices` returns `()` at storage
- [x] Confirm `storage/models.py` unchanged

### Retrieval

- [x] Create `retrieval/sparse_vectors.py` with `SparseQueryVector`
- [x] Add `SparseVectorValidationError` to `retrieval/exceptions.py`
- [x] Add `SparseQueryEmbeddingProvider` and `StubSparseQueryEmbeddingProvider`
- [x] Create `retrieval/sparse.py` with `SparseRetriever` (no settings)
- [x] Update `retrieval/__init__.py`
- [x] Confirm `dense.py` and `config.py` unchanged

### Tests

- [x] `tests/unit/storage/` — `search_sparse` validation
- [x] `tests/unit/retrieval/test_sparse_embeddings.py`
- [x] `tests/unit/retrieval/test_sparse_retriever.py`
- [x] Extend `tests/unit/retrieval/test_retrieval_imports.py`
- [x] `tests/integration/storage/` — Qdrant sparse search
- [x] `tests/integration/retrieval/` — `SparseRetriever` with fake store
- [x] Indexing `FakeVectorStore` protocol stub only

### Validation and Documentation

- [x] All quality commands pass
- [x] `docs/ARCHITECTURE.md` updated
- [x] `docs/PROGRESS.md` updated

### Non-Scope Verification

- [x] No indexing production code changes
- [x] No `sparse_placeholder_vector()` removal
- [x] No reindex migration implementation
- [x] No fusion, reranking, or BGE-M3 runtime
- [x] `DenseRetriever` unchanged
- [x] No `storage.models` imports in retrieval

---

## Revision Summary (2026-06-21)

### 1. What was removed

* All indexing implementation work: `SparseEmbeddingProvider`, `StubSparseEmbeddingProvider`, pipeline constructor changes, `sparse_placeholder_vector()` removal, indexing unit/integration sparse tests.
* Reindex migration implementation: rebuild workflows, migration tests, indexing integration reindex path.
* `SparseRetrievalSettings` empty settings object.
* `EmptySparseVectorError` and storage-level non-empty rejection on upsert.
* Modifications to `storage/models.py` upsert validation.

### 2. Why it was removed

Plans 04–06 follow **one plan, one architectural capability**. The original Plan 07 mixed sparse retrieval, sparse indexing, and migration into a single deliverable. That expanded scope beyond what a retrieval plan should own and would have forced indexing constructor breaking changes alongside retrieval work. Sparse retrieval can be implemented and tested independently using handcrafted sparse vectors in storage integration tests. Indexing placeholder replacement and reindex are separate concerns with their own ownership boundary (ADR-013 write path).

### 3. Future plan required

**Yes.** A future plan (e.g. **Plan 07b — Sparse Indexing** or renumbered per roadmap) is required for:

* `SparseEmbeddingProvider` and `StubSparseEmbeddingProvider` on the indexing write path;
* replacing `sparse_placeholder_vector()` with per-chunk sparse generation;
* `IndexingPipeline` integration;
* full reindex migration per ADR-020.

Until that plan completes, ADR-010 placeholders remain in production indexing behavior. Plan 07 delivers the read path; the write path is documented but deferred.
