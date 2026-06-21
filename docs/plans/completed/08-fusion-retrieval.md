# Plan 08 — Hybrid Retrieval / Fusion

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 4 — Retrieval

**Depends on:**

* [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)
* [Plan 07 — Sparse Retrieval](../completed/07-sparse-retrieval.md)

**Plan principle:** One plan introduces one architectural capability. Plan 08 introduces **result fusion** only.

---

## Objective

Design and implement deterministic rank-based fusion of dense and sparse leaf retrieval results.

```text
SearchQuery
    ↓
FusionRetriever.retrieve()
    ├─→ DenseRetriever.retrieve(leaf_query)  → RetrievalResult
    └─→ SparseRetriever.retrieve(leaf_query) → RetrievalResult
            ↓
    extract SearchResult tuples
            ↓
    deduplicate by ChunkId
            ↓
    Reciprocal Rank Fusion (RRF)
            ↓
RetrievalResult (fused, top_k)
```

After this plan is complete:

* callers can run hybrid retrieval via `FusionRetriever.retrieve(SearchQuery)`;
* dense and sparse leaf retrievers remain unchanged composable units;
* fusion is deterministic, rank-based (RRF), and lives entirely in the retrieval layer;
* no storage, indexing, MCP, agent, or LLM changes are required.

**Dependency rule:** fusion production code in `fusion.py` and `protocol.py` depends on `knowledge_assistant.core`, `knowledge_assistant.retrieval.protocol`, `knowledge_assistant.retrieval.config`, and the Python standard library only. Leaf retrievers are injected at runtime — fusion modules must not import `DenseRetriever`, `SparseRetriever`, `VectorStore`, `qdrant_client`, indexing, MCP, agent, LLM, LlamaIndex, or model runtimes.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/retrieval/` — fusion orchestration, RRF algorithm, retriever protocol, fusion settings;
* associated unit and integration tests;
* ADR entries and documentation updates.

### In Scope

* `Retriever` protocol — minimal leaf-retriever contract (`retrieve(SearchQuery) -> RetrievalResult`);
* `FusionRetriever` composing two `Retriever` instances (dense + sparse by convention);
* pure RRF fusion function operating on ranked `SearchResult` tuples;
* deduplication by `ChunkId` during fusion;
* `FusionRetrievalSettings` (`rrf_k`, leaf candidate pool sizing);
* unit tests: RRF math, deduplication, tie-breaking, orchestration, import boundaries;
* integration tests: `FusionRetriever` with fake leaf retrievers (no Qdrant);
* ADR entries ADR-021 through ADR-023;
* `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` updates.

---

## Non-Scope

This plan does **not** authorize:

* reranking (BAAI/bge-reranker-v2-m3 or any cross-encoder);
* real BGE-M3 model runtime (`torch`, `sentence-transformers`, `transformers`);
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* CLI behavior;
* query rewriting or LLM calls;
* source attribution formatting (`SourceReference` construction or display);
* changes to `knowledge_assistant.core` domain models (`SearchQuery`, `SearchResult`, `RetrievalResult`);
* changes to `VectorStore` protocol or Qdrant storage implementation;
* Qdrant native fusion (`FusionQuery`, prefetch fusion, or hybrid queries at storage layer);
* indexing changes (sparse placeholder, write-path sparse embeddings, reindex);
* modifications to `DenseRetriever`, `SparseRetriever`, embedding providers, or their settings;
* weighted score fusion (linear combination of raw dense/sparse similarity scores);
* preservation of original dense/sparse scores in fused output (no core model extension);
* cross-layer end-to-end hybrid test requiring real indexed corpora with meaningful sparse vectors;
* Docker Compose or smoke tests against live Qdrant from fusion tests;
* exception hierarchy rooted at `AppError` (deferred);
* `FusionRetriever` accepting more than two leaf retrievers (future extension only).

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-021 — Fusion Retrieval Boundary

**Status:** Accepted (established by this plan)

#### Context

Plans 06 and 07 deliver independent dense and sparse leaf retrievers. ADR-004 requires fusion outside Qdrant. The retrieval layer must compose leaf results deterministically without LLM calls, storage changes, or modifications to leaf retriever APIs.

#### Decision

* Hybrid fusion is implemented in `knowledge_assistant.retrieval`.
* `FusionRetriever` is the public orchestration entry point for fused search.
* Responsibilities:
  * accept caller `SearchQuery` (text + final `top_k`);
  * invoke two leaf `Retriever` instances with an expanded candidate `SearchQuery` (see ADR-023);
  * extract ranked `SearchResult` tuples from each `RetrievalResult`;
  * deduplicate by `ChunkId`;
  * apply Reciprocal Rank Fusion (RRF);
  * return one `RetrievalResult` with at most `query.top_k` fused hits.
* `FusionRetriever` must **not** call `VectorStore`, embed queries, or accept vectors.
* `FusionRetriever` must **not** modify `DenseRetriever` or `SparseRetriever`.
* Fused `SearchResult.score` values are **RRF fusion scores**, not raw dense or sparse similarity scores.
* `DenseRetriever` and `SparseRetriever` remain **leaf retrievers** with unchanged public APIs.

#### Consequences

* MCP and agent plans (future) depend on `FusionRetriever.retrieve`, not on fusion internals.
* Fusion tests use fake leaf retrievers without Qdrant or embedding stubs.
* Plan 09 reranking composes on top of fused results without changing Plan 08 contracts.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Qdrant `FusionQuery` at storage layer | Violates ADR-004; fusion must live in retrieval |
| Weighted sum of raw dense/sparse scores | Scores are incomparable across modalities; rank-based fusion is standard and deterministic |
| Modify `RetrievalResult` to carry per-modality scores | Requires core model changes; out of scope |
| Single `HybridRetriever` replacing leaf retrievers | Violates composability established in ADR-014 and ADR-017 |

---

### ADR-022 — Retriever Protocol for Composition

**Status:** Accepted (established by this plan)

#### Context

Plan 07 deferred a shared retriever protocol to Plan 08. `FusionRetriever` must compose leaf retrievers without hard-coding concrete `DenseRetriever` / `SparseRetriever` classes, enabling test fakes and future orchestrators (reranking) while keeping production wiring obvious.

#### Decision

* Define retrieval-local `Retriever` protocol in `retrieval/protocol.py`:

```python
class Retriever(Protocol):
    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Run one retrieval strategy for a search query."""
        ...
```

* `FusionRetriever.__init__` accepts two `Retriever` dependencies:

```python
def __init__(
    self,
    *,
    dense_retriever: Retriever,
    sparse_retriever: Retriever,
    settings: FusionRetrievalSettings,
) -> None: ...
```

* Parameter names document conventional wiring (`dense_retriever`, `sparse_retriever`); the protocol does **not** encode modality — any `Retriever` implementation is valid.
* `DenseRetriever` and `SparseRetriever` satisfy `Retriever` structurally; no inheritance or wrapper required.
* `FusionRetriever` depends on `Retriever`, not on `VectorStore` or embedding providers.

#### Consequences

* Unit and integration tests inject `FakeRetriever` without subclassing production leaf retrievers.
* Production assembly passes `DenseRetriever` and `SparseRetriever` instances.
* Future `RerankRetriever` (Plan 09) can wrap or compose `FusionRetriever` similarly.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Hard dependency on `DenseRetriever` / `SparseRetriever` concrete types | Couples fusion tests to leaf implementation details |
| Callable protocol `(SearchQuery) -> RetrievalResult` | Less discoverable; inconsistent with `VectorStore` / embedding provider patterns |
| Single `retrievers: tuple[Retriever, ...]` variadic constructor | Over-general for Plan 08; two-retriever API is clearer for hybrid demo |

---

### ADR-023 — Reciprocal Rank Fusion Algorithm

**Status:** Accepted (established by this plan)

#### Context

Dense cosine similarity and sparse dot-product scores are not directly comparable. Production hybrid systems commonly fuse **ranks** rather than raw scores. Fusion must remain deterministic with no model inference.

#### Decision

**Algorithm:** Reciprocal Rank Fusion (RRF).

For each `ChunkId` appearing in one or more leaf ranked lists:

```text
rrf_score(chunk_id) = Σ  1 / (rrf_k + rank_i)
```

where:

* the sum is over leaf lists in fixed order (**dense first, sparse second**);
* `rank_i` is the **1-based** rank of the chunk in list *i*;
* chunks absent from a list contribute **0** from that list (no imputation);
* `rrf_k` defaults to `60` (common RRF constant), configurable via `FusionRetrievalSettings`.

**Output ordering:**

1. Sort fused candidates by `rrf_score` descending.
2. Tie-break equal `rrf_score` by `chunk_id` ascending (lexicographic string order) for deterministic ordering.

**Deduplication:**

* Identity key: `SearchResult.chunk.chunk_id`.
* Duplicate `ChunkId` within the **same** leaf list: keep the **first (best) rank** only; ignore subsequent occurrences.
* Duplicate `ChunkId` across **dense and sparse** lists: one fused entry; RRF sums contributions from both ranks.
* `SearchResult.chunk` payload: use the `Chunk` from the **best-ranked occurrence** across all lists (lowest 1-based rank; dense list wins ties on equal rank because it is processed first).

**Candidate pool:**

* Leaf retrievers receive `SearchQuery(text=query.text, top_k=leaf_top_k)` where `leaf_top_k >= query.top_k`.
* Default: `leaf_top_k = query.top_k * leaf_top_k_multiplier` with `leaf_top_k_multiplier = 2` (see `FusionRetrievalSettings`).
* Final fused output is truncated to `query.top_k`.

**Score semantics after fusion:**

* `SearchResult.score` = computed `rrf_score`.
* Fused scores are **not comparable** to leaf retriever scores or to reranker scores (Plan 09).
* Original dense/sparse scores are **not preserved** in Plan 08 output.

#### Consequences

* Fusion behavior is fully testable with hand-computed RRF expectations.
* Expanding the leaf candidate pool improves recall for chunks ranked low in one modality but high in another.
* Operators can tune `rrf_k` and `leaf_top_k_multiplier` without code changes.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Weighted linear combination of raw scores | Requires score normalization; fragile across backends |
| CombSUM / CombMNZ on ranks | Less common in modern hybrid RAG; RRF is lecture-aligned |
| Preserve dense score when sparse rank missing | Requires core model extension; deferred |
| Use `query.top_k` unchanged for leaf retrievers | Reduces fusion benefit when modalities disagree on tail ranks |

---

## Design Evaluations

This section records Plan 08 answers to the explicit design questions. These are **decided**; implementation must not reopen them without a plan revision.

### Fusion input: `RetrievalResult` vs raw `SearchResult` tuples

| Approach | Assessment |
| -------- | ---------- |
| **A — Operate on `RetrievalResult` from leaf retrievers** | **Selected.** `FusionRetriever.retrieve` calls each leaf retriever, receives `RetrievalResult`, extracts `result.results` tuples, and passes them into the pure RRF function. |
| B — Leaf retrievers return bare tuples; fusion skips `RetrievalResult` | Rejects the established leaf retriever public API; forces orchestration duplication. |

**Rationale:** Leaf retrievers own the `SearchQuery → RetrievalResult` contract (ADR-014, ADR-017). Fusion is an orchestrator above them. The RRF pure function accepts `tuple[SearchResult, ...]` extracted from each `RetrievalResult.results` — fusion math operates on tuples; orchestration operates on `RetrievalResult`.

---

### Concrete leaf classes vs retrieval protocol

| Approach | Assessment |
| -------- | ---------- |
| **A — `Retriever` protocol (ADR-022)** | **Selected.** |
| B — Hard-coded `DenseRetriever` / `SparseRetriever` types | Couples tests and future orchestrators to concrete classes. |

---

### Duplicate `ChunkId` handling

| Scenario | Behavior |
| -------- | -------- |
| Same `ChunkId` in dense and sparse lists | Single fused entry; RRF score sums both rank contributions; chunk payload from best rank (dense wins rank ties). |
| Same `ChunkId` twice in one leaf list | Treat as data error; keep first occurrence rank only (defensive; storage should not produce this). |
| Same text, different `ChunkId` | **Not** deduplicated — identity is `ChunkId` only. |

---

### Fused `SearchResult.score` meaning

Fused `score` is the **RRF fusion score** (ADR-023). Higher is better. It is not a similarity probability and is not comparable to dense cosine or sparse dot-product values from leaf retrievers.

---

### Preserving original dense/sparse scores

**Out of scope.** Core `SearchResult` exposes one `score` field. Plan 08 overwrites it with the RRF score. Preserving per-modality scores would require core model changes or a parallel metadata type — deferred to a future plan if needed for observability or reranker features.

---

### Leaf candidate pool vs final `top_k`

**Yes — request more candidates from leaf retrievers than final `top_k`.** Default multiplier `2` via `FusionRetrievalSettings.leaf_top_k_multiplier`. Fusion truncates to caller `query.top_k` after RRF sorting.

Example: caller `top_k=5`, multiplier `2` → each leaf queried with `top_k=10` → fuse → return top 5.

When `leaf_top_k_multiplier=1`, fusion still works but with a narrower candidate pool (acceptable for minimal tests).

---

### `FusionRetrievalSettings`

**Yes — introduce `FusionRetrievalSettings`.** Unlike sparse retrieval (no tunable parameters in Plan 07), fusion has meaningful algorithm knobs:

* `rrf_k: int = 60`
* `leaf_top_k_multiplier: int = 2`

Validation:

* `rrf_k >= 1`
* `leaf_top_k_multiplier >= 1`

Helper (module-local on `FusionRetrievalSettings`):

```python
def resolve_leaf_top_k(self, query_top_k: int) -> int:
    return query_top_k * self.leaf_top_k_multiplier
```

`resolve_leaf_top_k` relies on the existing `SearchQuery.top_k >= 1` invariant (enforced in `core`). It does not require separate defensive validation of `query_top_k` unless the implementation chooses to keep the helper trivially simple.

No `VectorStore` or embedding settings in this type.

---

### Deterministic ranking in tests

Tests guarantee determinism by:

1. **Fixed inputs** — fake leaf retrievers return predetermined ordered `SearchResult` lists; no randomness.
2. **Hand-computed RRF expectations** — unit tests assert exact fused scores and order for known rank inputs.
3. **Explicit tie-break rule** — when RRF scores tie, expect `chunk_id` ascending order (ADR-023).
4. **Fixed list order** — dense list always processed before sparse list in RRF sum.
5. **No float tolerance ambiguity for RRF unit tests** — use rank inputs that produce unambiguous distinct scores where order matters; tie cases tested separately with explicit `chunk_id` ordering assertions.

Integration tests with `FakeRetriever` record leaf `SearchQuery` arguments to verify expanded `leaf_top_k` forwarding.

---

## Module Layout

### Retrieval (new and modified files)

```text
src/knowledge_assistant/retrieval/
    __init__.py           # add fusion exports; update module docstring
    protocol.py           # NEW: Retriever protocol
    config.py             # add FusionRetrievalSettings (DenseRetrievalSettings unchanged)
    fusion.py             # NEW: FusionRetriever + reciprocal_rank_fusion pure function
    dense.py              # UNCHANGED
    sparse.py             # UNCHANGED
    embeddings.py         # UNCHANGED
    sparse_vectors.py     # UNCHANGED
    exceptions.py         # UNCHANGED (no new exception types required)
```

Do not create `retrieval/utils/` or `retrieval/fusion/` subpackages.

### Storage, Indexing, Core

**No modifications.**

---

## API Design

### Retriever Protocol

**Module:** `retrieval/protocol.py`

```python
class Retriever(Protocol):
    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        """Run one retrieval strategy for a search query."""
        ...
```

Structural conformance: `DenseRetriever`, `SparseRetriever`, test fakes.

---

### FusionRetrievalSettings

**Module:** `retrieval/config.py`

```python
@dataclass(frozen=True, slots=True)
class FusionRetrievalSettings:
    rrf_k: int = 60
    leaf_top_k_multiplier: int = 2
```

Validation in `__post_init__`:

* `rrf_k >= 1`
* `leaf_top_k_multiplier >= 1`

```python
def resolve_leaf_top_k(self, query_top_k: int) -> int:
    """Candidate pool size forwarded to each leaf retriever."""
    return query_top_k * self.leaf_top_k_multiplier
```

`resolve_leaf_top_k` relies on the existing `SearchQuery.top_k >= 1` invariant (enforced in `core`). It does not require separate defensive validation of `query_top_k` unless the implementation chooses to keep the helper trivially simple.

`DenseRetrievalSettings` remains unchanged in the same module.

---

### reciprocal_rank_fusion (pure function)

**Module:** `retrieval/fusion.py`

```python
def reciprocal_rank_fusion(
    *,
    dense_results: tuple[SearchResult, ...],
    sparse_results: tuple[SearchResult, ...],
    rrf_k: int,
) -> tuple[SearchResult, ...]:
    """Fuse two ranked result lists with RRF. Returns all candidates sorted by fused score."""
    ...
```

Properties:

* deterministic;
* no I/O;
* deduplicates by `ChunkId` per ADR-023;
* returns `SearchResult` entries with `score` set to RRF value;
* does **not** truncate to `top_k` (orchestrator responsibility).

**Visibility:** `reciprocal_rank_fusion` is **module-public** inside `retrieval/fusion.py` (no leading underscore) so unit tests and direct algorithm validation can import it from that module. It is an internal retrieval-layer helper, not part of the package public API.

Module-local helpers (e.g. `_chunk_rank_map`, `_select_chunk_payload`) remain private.

---

### FusionRetriever

**Module:** `retrieval/fusion.py`

```python
class FusionRetriever:
    def __init__(
        self,
        *,
        dense_retriever: Retriever,
        sparse_retriever: Retriever,
        settings: FusionRetrievalSettings,
    ) -> None: ...

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        ...
```

**`retrieve` behavior:**

1. Compute `leaf_top_k = settings.resolve_leaf_top_k(query.top_k)`.
2. Build `leaf_query = SearchQuery(text=query.text, top_k=leaf_top_k)`.
3. Call `dense_retriever.retrieve(leaf_query)` and `sparse_retriever.retrieve(leaf_query)` sequentially (order documented; no parallelism required in Plan 08).
4. Extract `dense_results` and `sparse_results` tuples from each leaf `RetrievalResult.results`.
5. Call `reciprocal_rank_fusion(dense_results=..., sparse_results=..., rrf_k=settings.rrf_k)`.
6. Truncate fused tuple to `query.top_k`.
7. Return `RetrievalResult(query=query, results=fused[:query.top_k])`.

**Query echo semantics:** `FusionRetriever` does **not** perform defensive query echo validation. Leaf retrievers are responsible for returning `RetrievalResult` with their own input query (`leaf_query`). `FusionRetriever` returns `RetrievalResult` with the **original caller** `query`. Do not use `assert` in production code for query matching.

**Forbidden public APIs:**

* vector-accepting methods;
* direct `VectorStore` access;
* exposure of leaf retriever internals.

**Error propagation:** exceptions from leaf retrievers propagate unchanged. `FusionRetriever` does not catch and translate leaf failures.

**Empty results:** if both leaf lists are empty, return `RetrievalResult(query=query, results=())`. If one list is empty, RRF uses the non-empty list's ranks only.

---

### Public API Exports

**`retrieval/__init__.py`:**

* `FusionRetriever`
* `FusionRetrievalSettings`
* `Retriever` (protocol)

Do **not** re-export `reciprocal_rank_fusion` from `retrieval/__init__.py`. It remains module-public in `retrieval/fusion.py` for unit tests and direct algorithm validation; tests import it from `knowledge_assistant.retrieval.fusion`.

Update module docstring to reflect fusion capability.

---

## Fusion Flow

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

### Boundary Responsibilities

| Layer | Input | Output | Vectors / storage |
| ----- | ----- | ------ | ----------------- |
| Caller (future MCP/agent) | `SearchQuery` | `RetrievalResult` | none |
| `FusionRetriever` | `SearchQuery` | `RetrievalResult` | orchestrates leaf retrievers only |
| `DenseRetriever` / `SparseRetriever` | `SearchQuery` | `RetrievalResult` | embed + search (unchanged) |
| `reciprocal_rank_fusion` | two ranked tuples | ranked fused tuple | none |

No reranking. No LLM calls. No storage changes. No Qdrant fusion.

---

## Deduplication Strategy

| Step | Rule |
| ---- | ---- |
| Identity key | `ChunkId` from `SearchResult.chunk.chunk_id` |
| Within-list duplicates | Keep first (best) rank; ignore later occurrences |
| Cross-list duplicates | Merge into one entry; sum RRF contributions |
| Chunk payload selection | Use `Chunk` from occurrence with best (lowest) 1-based rank; dense list wins rank ties |
| Text-level deduplication | Not performed — different chunks with similar text remain distinct |

---

## Score Semantics

| Stage | `SearchResult.score` meaning |
| ----- | ---------------------------- |
| `DenseRetriever` output | Raw dense similarity (unchanged, ADR-014) |
| `SparseRetriever` output | Raw sparse similarity (unchanged, ADR-017) |
| `FusionRetriever` output | **RRF fusion score** (ADR-023) |
| Future reranker (Plan 09) | Cross-encoder score (separate plan) |

Callers of `FusionRetriever` must treat fused scores as **ordinal ranking keys**, not calibrated relevance probabilities.

---

## Dependency Rules

### Allowed Dependencies (Fusion Production Code)

Fusion modules (`fusion.py`, `protocol.py`) may import only:

* `knowledge_assistant.core` (domain types);
* `knowledge_assistant.retrieval.protocol`;
* `knowledge_assistant.retrieval.config`;
* Python standard library.

Leaf retrievers are supplied by callers via constructor injection. Fusion production code must **not** import `DenseRetriever`, `SparseRetriever`, or other leaf retriever implementations.

`FusionRetriever` must **not** import `storage.protocol.VectorStore` — it delegates to injected `Retriever` instances.

### Forbidden Dependencies

Fusion production code must **not** import:

* `qdrant_client`;
* `knowledge_assistant.storage` (any submodule);
* `knowledge_assistant.indexing` (any submodule);
* `knowledge_assistant.agent`;
* `knowledge_assistant.mcp_server`;
* `knowledge_assistant.llm`;
* `llama_index` / `llama-index`;
* `torch`, `sentence_transformers`, `transformers`.

`DenseRetriever` and `SparseRetriever` production modules remain unchanged; their existing dependency rules stand.

### Import-Boundary Tests

Extend `tests/unit/retrieval/test_retrieval_imports.py`:

* `fusion.py` and `protocol.py` follow the same forbidden-import rules as other retrieval modules;
* `fusion.py` must not import `storage`.

---

## Testing Strategy

| Level | Location | What is tested | Dependencies |
| ----- | -------- | -------------- | ------------ |
| Unit | `tests/unit/retrieval/test_fusion.py` | RRF math, deduplication, tie-breaking, truncation | None (pure function + mocked retrievers) |
| Unit | `tests/unit/retrieval/test_fusion_retriever.py` | orchestration, leaf_top_k forwarding, empty results | `FakeRetriever` |
| Integration | `tests/integration/retrieval/test_fusion_retriever.py` | end-to-end `FusionRetriever` with fake leaf retrievers | No Qdrant |

**No Qdrant-specific behavior in fusion tests.** Storage and leaf retriever Qdrant tests remain in their respective packages.

### Unit Tests — RRF Pure Function (required)

* empty both lists → `()`;
* empty one list → ranks from non-empty list only;
* single-list chunk receives `1/(rrf_k + rank)` score;
* chunk in both lists receives sum of two RRF terms;
* higher fused score when present in both lists at good ranks vs single-list presence;
* duplicate `ChunkId` within one list → first rank used;
* tie on RRF score → `chunk_id` ascending order;
* chunk payload taken from best-ranked occurrence;
* custom `rrf_k` changes scores predictably (hand-calculated);
* output sorted descending by fused score.

### Unit Tests — FusionRetriever (required)

* calls each leaf retriever exactly once per `retrieve`;
* forwards `SearchQuery(text=..., top_k=leaf_top_k)` to leaves with `leaf_top_k = query.top_k * multiplier`;
* returns `RetrievalResult` with caller `query` echoed (not leaf query);
* truncates to caller `query.top_k`;
* propagates leaf retriever exceptions;
* empty leaf results handled;
* existing dense and sparse retriever behavior remains unchanged; existing dense and sparse tests continue to pass without semantic updates.

### Integration Tests (required)

Using `FakeRetriever` in `tests/integration/retrieval/conftest.py`:

* `FusionRetriever` with two fakes returning overlapping and distinct `ChunkId` sets;
* verify fused ordering matches hand-computed RRF for fixture data;
* verify leaf `top_k` argument recorded on fakes;
* verify final result length `<= query.top_k`.

**`FakeRetriever` design:**

* implements `Retriever` protocol;
* configurable `RetrievalResult` return value;
* records last `SearchQuery` received.

**Not in scope:** Docker Qdrant; real BGE-M3; MCP; agent; reranking; indexing sparse migration.

---

## Dependencies

Do **not** add new runtime dependencies for Plan 08.

Do **not** add `torch`, `sentence-transformers`, `transformers`, `langgraph`, `mcp`, or `openai`.

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-021 through ADR-023 from this plan;
* `docs/ARCHITECTURE.md`:
  * fusion retrieval path diagram between sparse retrieval and future reranker;
  * module table entries for `protocol.py`, `fusion.py`, `FusionRetrievalSettings`;
  * document RRF fusion, deduplication, and fused score semantics;
  * replace "Fusion and reranking are deferred" with fusion implemented, reranking deferred;
* `docs/PROGRESS.md` — record Plan 08 completion when done.

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Acceptance Criteria

### Protocol and Settings

- [x] `Retriever` protocol defined in `retrieval/protocol.py` with `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] `FusionRetrievalSettings` defined with `rrf_k: int = 60` and `leaf_top_k_multiplier: int = 2`
- [x] Settings validation: `rrf_k >= 1`, `leaf_top_k_multiplier >= 1`
- [x] `resolve_leaf_top_k(query_top_k)` returns `query_top_k * leaf_top_k_multiplier`
- [x] `resolve_leaf_top_k` relies on `SearchQuery.top_k >= 1`; no separate defensive validation required unless implementation keeps the helper trivially simple

### Fusion Algorithm

- [x] `reciprocal_rank_fusion` implemented as pure deterministic function in `retrieval/fusion.py`
- [x] `reciprocal_rank_fusion` is module-public in `retrieval/fusion.py` (not private); must **not** be re-exported from `retrieval/__init__.py`
- [x] RRF uses 1-based ranks and configurable `rrf_k`
- [x] Dense list processed before sparse list in RRF sum
- [x] Deduplication by `ChunkId` per ADR-023
- [x] Tie-break on equal RRF score by `chunk_id` ascending
- [x] Fused `SearchResult.score` holds RRF value

### FusionRetriever

- [x] `FusionRetriever` implements `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] Accepts `dense_retriever: Retriever`, `sparse_retriever: Retriever`, `settings: FusionRetrievalSettings`
- [x] Does not import or call `VectorStore` directly
- [x] Invokes both leaf retrievers with expanded `leaf_top_k`
- [x] Returns `RetrievalResult` with caller `query` and at most `query.top_k` results
- [x] Does not perform defensive query echo validation; does not use `assert` for query matching
- [x] Leaf retriever exceptions propagate unchanged
- [x] Empty leaf results produce valid fused output

### Leaf Retrievers and Boundaries

- [x] Do not modify `DenseRetriever` or `SparseRetriever` production code
- [x] Existing dense and sparse retriever behavior unchanged; existing dense and sparse tests pass without semantic updates
- [x] `SearchQuery`, `SearchResult`, `RetrievalResult` unchanged in `core`
- [x] No `VectorStore` protocol changes
- [x] No indexing changes
- [x] No Qdrant fusion
- [x] Production fusion code (`fusion.py`, `protocol.py`) imports only `core`, `retrieval.protocol`, `retrieval.config`, and stdlib
- [x] Production fusion code does not import `VectorStore`, `qdrant_client`, `storage`, `indexing`, `mcp_server`, `agent`, `llm`, LlamaIndex, or model runtimes

### Tests

- [x] Unit tests in `tests/unit/retrieval/test_fusion.py` for RRF math and deduplication
- [x] Unit tests in `tests/unit/retrieval/test_fusion_retriever.py` for orchestration
- [x] Integration tests in `tests/integration/retrieval/test_fusion_retriever.py` with `FakeRetriever`
- [x] Import-boundary tests extended for fusion modules
- [x] Existing dense and sparse tests continue to pass without semantic updates

### Validation and Documentation

- [x] ADR-021 through ADR-023 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents fusion path and score semantics
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes on modified packages
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into reranking or MCP | Explicit non-scope; fusion-only deliverable |
| Accidental `DenseRetriever` / `SparseRetriever` modification | Acceptance criterion: do not modify leaf production code; existing dense/sparse tests pass without semantic updates |
| Fusion imports `VectorStore` directly | ADR-021; `FusionRetriever` depends on `Retriever` only |
| Non-deterministic ordering on RRF ties | ADR-023 tie-break by `chunk_id`; dedicated unit tests |
| Leaf `top_k` equals caller `top_k` reduces fusion quality | Default `leaf_top_k_multiplier=2`; tests verify forwarding |
| Placeholder sparse vectors yield poor hybrid quality in production | Document ADR-020 constraint; fusion logic testable with fake retrievers independent of corpus quality |
| Score semantics confusion for downstream reranker | Document fused scores as RRF-only in architecture and ADR-023 |
| Within-list duplicate `ChunkId` from storage bug | Defensive first-rank-only rule; unlikely in normal operation |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-021 through ADR-023 in `docs/DECISIONS.md`.
2. **Create `retrieval/protocol.py`** — define `Retriever` protocol.
3. **Extend `retrieval/config.py`** — add `FusionRetrievalSettings` with validation and `resolve_leaf_top_k`.
4. **Create `retrieval/fusion.py`** — implement `reciprocal_rank_fusion` pure function.
5. **Implement `FusionRetriever`** — orchestrate leaf retrievers and truncate output.
6. **Update `retrieval/__init__.py`** — export fusion public API; update module docstring.
7. **Add unit tests** — `test_fusion.py` for RRF math; `test_fusion_retriever.py` for orchestration.
8. **Extend import guard tests** — fusion modules in `test_retrieval_imports.py`.
9. **Add integration tests** — `FakeRetriever` in retrieval conftest; `test_fusion_retriever.py`.
10. **Update `docs/ARCHITECTURE.md`** — fusion path, modules, score semantics.
11. **Run validation suite** — all four quality commands; fix until pass.
12. **Update progress** — record completion in `docs/PROGRESS.md`.
13. **Verify non-scope compliance** — no reranking, no storage/indexing/core changes; do not modify `DenseRetriever` or `SparseRetriever` production code.

---

## Checklist

### Architectural Decisions

- [x] Transcribe ADR-021 (Fusion Retrieval Boundary) into `docs/DECISIONS.md`
- [x] Transcribe ADR-022 (Retriever Protocol) into `docs/DECISIONS.md`
- [x] Transcribe ADR-023 (Reciprocal Rank Fusion) into `docs/DECISIONS.md`

### Protocol and Configuration

- [x] Create `retrieval/protocol.py` with `Retriever` protocol
- [x] Add `FusionRetrievalSettings` to `retrieval/config.py`
- [x] Validate `rrf_k >= 1` and `leaf_top_k_multiplier >= 1`

### Fusion Implementation

- [x] Create `retrieval/fusion.py` with `reciprocal_rank_fusion`
- [x] Implement `FusionRetriever` with two `Retriever` dependencies
- [x] Forward expanded `leaf_top_k` to leaf retrievers
- [x] Truncate fused output to caller `query.top_k`

### Public API

- [x] Update `retrieval/__init__.py` exports
- [x] Confirm `dense.py`, `sparse.py`, `embeddings.py` unchanged

### Unit Tests

- [x] `tests/unit/retrieval/test_fusion.py` — RRF, deduplication, tie-breaking
- [x] `tests/unit/retrieval/test_fusion_retriever.py` — orchestration, leaf_top_k, errors
- [x] Extend `tests/unit/retrieval/test_retrieval_imports.py`

### Integration Tests

- [x] Add `FakeRetriever` to `tests/integration/retrieval/conftest.py`
- [x] `tests/integration/retrieval/test_fusion_retriever.py`

### Validation and Documentation

- [x] All quality commands pass
- [x] `docs/ARCHITECTURE.md` updated
- [x] `docs/PROGRESS.md` updated on completion

### Non-Scope Verification

- [x] No reranking or BGE reranker
- [x] No MCP, agent, or LLM integration
- [x] No `core` model changes
- [x] No storage or indexing changes
- [x] No Qdrant fusion
- [x] Do not modify `DenseRetriever` or `SparseRetriever` production code
