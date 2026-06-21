# Plan 09 — Reranking

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 4 — Retrieval

**Depends on:**

* [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)
* [Plan 07 — Sparse Retrieval](../completed/07-sparse-retrieval.md)
* [Plan 08 — Hybrid Retrieval / Fusion](../completed/08-fusion-retrieval.md)

**Plan principle:** One plan introduces one architectural capability. Plan 09 introduces **reranking** only.

---

## Objective

Design and implement deterministic reranking of already-retrieved search candidates on top of the existing `Retriever` composition model.

```text
SearchQuery
    ↓
RerankRetriever.retrieve()
    ↓
base Retriever.retrieve(candidate_query)  → RetrievalResult
    ↓
extract SearchResult candidates
    ↓
Reranker.rerank(query, candidates)   ← N candidates in, N candidates out
    ↓
validate len(reranked) == len(candidates)  ← ValueError on violation
    ↓
truncate to query.top_k                ← only candidate reduction in Plan 09
    ↓
RetrievalResult (reranked, top_k)
```

After this plan is complete:

* callers can run reranked retrieval via `RerankRetriever.retrieve(SearchQuery)`;
* any `Retriever` implementation (typically `FusionRetriever` in production wiring) remains a composable base retriever;
* reranking is deterministic with `StubReranker` and lives entirely in the retrieval layer;
* the Plan 09 `Reranker` contract preserves candidate count (`N` in → `N` out); only `RerankRetriever` truncates to `query.top_k`;
* `RerankRetriever` raises `ValueError` when a reranker violates the candidate-count contract;
* no storage, indexing, MCP, agent, or LLM changes are required;
* real `BAAI/bge-reranker-v2-m3` integration is documented for a future plan only.

**Dependency rule:** reranking production code in `rerank.py` depends on `knowledge_assistant.core`, `knowledge_assistant.retrieval.protocol`, `knowledge_assistant.retrieval.config`, and the Python standard library only. Base retrievers and rerankers are injected at runtime — reranking modules must not import `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `VectorStore`, `qdrant_client`, indexing, MCP, agent, LLM, LlamaIndex, or model runtimes.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/retrieval/` — reranking orchestration, reranker protocol, rerank settings, stub reranker;
* associated unit and integration tests;
* ADR entries and documentation updates.

### In Scope

* `Reranker` protocol — retrieval-local reranking contract with candidate preservation invariant (`N` in → `N` out);
* `RerankRetriever` wrapping any `Retriever` instance (fusion retriever by convention in production);
* `RerankRetrievalSettings` (`candidate_top_k_multiplier` for candidate pool sizing);
* `StubReranker` — deterministic, hash/lexical-based, no model runtime;
* unit tests: settings validation, stub determinism, orchestration, candidate expansion, import boundaries;
* integration tests: `RerankRetriever` with fake base retriever (no Qdrant);
* ADR entries ADR-024 through ADR-027;
* `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/PROGRESS.md` updates.

---

## Non-Scope

This plan does **not** authorize:

* real `BAAI/bge-reranker-v2-m3` model runtime (`torch`, `sentence-transformers`, `transformers`);
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* CLI behavior;
* query rewriting or LLM calls;
* source attribution formatting (`SourceReference` construction or display);
* changes to `knowledge_assistant.core` domain models (`SearchQuery`, `SearchResult`, `RetrievalResult`);
* changes to `VectorStore` protocol or Qdrant storage implementation;
* indexing changes;
* modifications to `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, embedding providers, or their settings;
* preservation of original dense/sparse/RRF scores in reranked output (no core model extension);
* cross-layer end-to-end hybrid+rerank test requiring real indexed corpora;
* Docker Compose or smoke tests against live Qdrant from reranking tests;
* exception hierarchy rooted at `AppError` (deferred);
* multi-query batch reranking APIs;
* score-threshold filtering, candidate dropping, or confidence cutoffs inside `Reranker` (deferred to a separate future plan that must revise the reranker contract explicitly).

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-024 — Reranking Boundary

**Status:** Accepted (established by this plan)

#### Context

Plans 06–08 deliver dense retrieval, sparse retrieval, and RRF fusion. `PROJECT.md` and `docs/ARCHITECTURE.md` position reranking as the next retrieval-layer stage before MCP exposure. Reranking must refine candidate ordering without LLM calls, storage changes, or modifications to leaf/fusion retriever APIs.

#### Decision

* Reranking is implemented in `knowledge_assistant.retrieval`.
* `RerankRetriever` is the public orchestration entry point for reranked search.
* Responsibilities:
  * accept caller `SearchQuery` (text + final `top_k`);
  * invoke one injected `Retriever` with an expanded candidate `SearchQuery` (see ADR-026);
  * extract ranked `SearchResult` tuples from the base `RetrievalResult`;
  * call `Reranker.rerank(query, candidates)` — reranker must return `len(candidates)` results (candidate preservation);
  * validate `len(reranked) == len(candidates)` when candidates are non-empty; raise `ValueError` on violation;
  * truncate reranked output to at most `query.top_k` — the **only** candidate reduction in Plan 09;
  * return one `RetrievalResult` with caller `query` echoed.
* `RerankRetriever` must **not** call `VectorStore`, embed queries, call LLMs, or import dense/sparse/fusion concrete retrievers.
* `RerankRetriever` must **not** modify `DenseRetriever`, `SparseRetriever`, or `FusionRetriever`.
* Reranked `SearchResult.score` values are **reranker relevance scores**, not dense, sparse, or RRF scores.
* Base retrievers remain **unchanged composable units** with unchanged public APIs.

#### Consequences

* MCP and agent plans (future) depend on `RerankRetriever.retrieve`, not on reranking internals.
* Reranking tests use fake base retrievers and `StubReranker` without Qdrant or model runtimes.
* Production wiring typically nests `FusionRetriever` as the base retriever; tests may use any `Retriever` fake.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Reranking inside `FusionRetriever` | Violates single-capability plans; couples fusion and reranking |
| MCP calls cross-encoder directly | Violates component boundaries; reranking belongs in retrieval |
| Rerank only inside MCP operations layer | Skips reusable retrieval orchestration; harder to test in isolation |
| Modify `RetrievalResult` to carry pre-rerank scores | Requires core model changes; out of scope |

---

### ADR-025 — Reranker Protocol

**Status:** Accepted (established by this plan)

#### Context

Plan 08 introduced `Retriever` for composable orchestration. Reranking is a separate concern from candidate retrieval: it scores and reorders already-retrieved `SearchResult` tuples. A dedicated protocol enables stub and future real cross-encoder implementations without coupling `RerankRetriever` to model runtimes.

#### Decision

* Define retrieval-local `Reranker` protocol in `retrieval/rerank.py`:

```python
class Reranker(Protocol):
    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]:
        """Score and reorder retrieval candidates for one search query."""
        ...
```

* `RerankRetriever.__init__` accepts one `Retriever` and one `Reranker`:

```python
def __init__(
    self,
    *,
    base_retriever: Retriever,
    reranker: Reranker,
    settings: RerankRetrievalSettings,
) -> None: ...
```

* Parameter name `base_retriever` documents conventional wiring (typically `FusionRetriever`); the protocol does **not** encode retriever kind — any `Retriever` implementation is valid.
* `RerankRetriever` depends on `Retriever` and `Reranker`, not on `VectorStore` or embedding providers.
* Plan 09 provides `StubReranker` as the deterministic development/test implementation.
* **Protocol shape note:** rerankers conceptually score existing candidates and reorder them. The protocol returns `tuple[SearchResult, ...]` rather than a bare score sequence for simplicity and consistency with existing retrieval contracts (`Retriever` returns `RetrievalResult`; fusion and leaf retrievers work in `SearchResult` tuples). No API change is required for Plan 09.
* **Candidate preservation (Plan 09 contract):** every `Reranker` implementation must return exactly `len(candidates)` results — rerankers do not add or remove candidates; they only rescale scores and reorder. See ADR-026.
* **Contract enforcement:** `RerankRetriever` validates `len(reranked) == len(candidates)` when candidates are non-empty. Violations raise `ValueError` (no new exception types; no `assert` in production code). Future reranker implementations, including BGE-based rerankers, must not silently violate the contract.

#### Consequences

* Unit and integration tests inject `FakeRetriever` and `StubReranker` without subclassing production retrievers.
* Future real cross-encoder implements `Reranker` in the same module without changing `RerankRetriever`.
* `Reranker.rerank` accepts the **caller** `SearchQuery`, not the expanded candidate query.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Hard dependency on `FusionRetriever` only | Couples reranking to hybrid fusion; blocks reranking dense-only paths in tests |
| Callable protocol `(SearchQuery, tuple) -> tuple` | Less discoverable; inconsistent with `Retriever` / embedding provider patterns |
| Reranker accepts raw `str` query text only | Loses typed retrieval contract; `SearchQuery` is the established caller input |
| Reranking as a method on `FusionRetriever` | Violates composability; fusion and reranking remain separate orchestrators |
| Rely on reranker contract without orchestrator validation | Silent violations possible; fail-fast `ValueError` in `RerankRetriever` is required |
| Use `assert` for candidate-count validation in production | Assertions may be disabled; explicit `ValueError` is deterministic and testable |

---

### ADR-026 — Reranked Score Semantics and Candidate Pool

**Status:** Accepted (established by this plan)

#### Context

Retrieval passes through multiple score spaces: dense cosine, sparse dot-product, RRF fusion. Reranking introduces a fourth score space. Callers need predictable semantics. Reranking quality improves when the base retriever returns more candidates than the final `top_k`, mirroring Plan 08 leaf candidate expansion.

#### Decision

**Candidate pool:**

* Base retriever receives `SearchQuery(text=query.text, top_k=candidate_top_k)` where `candidate_top_k >= query.top_k`.
* Default: `candidate_top_k = query.top_k * candidate_top_k_multiplier` with `candidate_top_k_multiplier = 2` (see `RerankRetrievalSettings`).
* Final reranked output is truncated to `query.top_k`.

**Score semantics after reranking:**

* `SearchResult.score` = reranker relevance score returned by `Reranker.rerank`.
* Higher is better.
* Reranked scores are **not comparable** to dense, sparse, or RRF scores.
* Original retrieval scores are **not preserved** in Plan 09 output.

**Ordering:**

1. `Reranker.rerank` returns candidates sorted by reranker score descending.
2. Tie-break equal reranker scores by `chunk_id` ascending (lexicographic string order) for deterministic ordering.

**Candidate preservation contract (Plan 09 invariant):**

```text
Reranker does not add candidates.
Reranker does not remove candidates.
Reranker only rescales scores and reorders existing candidates.

Input:  N candidates
Output: N candidates
```

* Every `Reranker` implementation (including `StubReranker` and the future BGE cross-encoder) must satisfy `len(output) == len(candidates)` for Plan 09.
* The **only** candidate reduction permitted in Plan 09 is `RerankRetriever` final truncation to `query.top_k` after `Reranker.rerank` returns.
* Score-threshold filtering, confidence cutoffs, and reranker-side candidate dropping are **not** part of the Plan 09 contract. A separate future plan must explicitly authorize contract changes before any `Reranker` may return fewer than `len(candidates)` results.

**Contract enforcement:**

* `RerankRetriever` validates `len(reranked) == len(candidates)` when `len(candidates) > 0`.
* Violations raise `ValueError`. Do not use `assert` for production correctness.
* Do not introduce new exception types for this check.
* Rationale: candidate preservation is a core Plan 09 invariant; violations must fail fast so future reranker implementations (including BGE-based rerankers) cannot silently break the contract.

**Fewer candidates than requested from base retriever:**

* When the base retriever returns fewer than `candidate_top_k` results, rerank **all returned candidates**; do not error or pad.
* `RerankRetriever` returns `len(results) <= query.top_k` and `len(results) <= len(base candidates)`.

**Deterministic ordering guarantee:**

For identical `query` and `candidates` inputs, reranking output must be **fully deterministic**:

* identical inputs produce identical ordering;
* identical inputs produce identical scores;
* tie-breaking is deterministic via `chunk_id` ascending order when reranker scores are equal.

Production reranking code (stub and orchestration) must not introduce randomness. This guarantee applies to all Plan 09 `Reranker` implementations.

**Fusion candidate pool independence (documentation only):**

* Fusion candidate expansion (`FusionRetrievalSettings.leaf_top_k_multiplier`) and reranking candidate expansion (`RerankRetrievalSettings.candidate_top_k_multiplier`) are **independent**.
* `RerankRetriever` controls only the `top_k` it forwards to its injected `base_retriever`; it does not know whether that retriever is dense, sparse, fusion, or another `Retriever` implementation.
* There is **no coupling** between `FusionRetrievalSettings` and `RerankRetrievalSettings`. When `base_retriever` is `FusionRetriever`, fusion applies its own internal leaf expansion; `RerankRetriever` separately requests `candidate_top_k` fused results from the fusion orchestrator.

**Batch shape:**

* `Reranker.rerank` processes **one query and its full candidate tuple** in a single call (single-query batch).
* Multi-query batch APIs are out of scope.

#### Consequences

* Reranking behavior is fully testable with hand-computed score expectations for `StubReranker`.
* Expanding the candidate pool improves reranker recall when fusion ranks a relevant chunk outside the final `top_k`.
* Operators can tune `candidate_top_k_multiplier` without code changes.
* Contract violations surface immediately as `ValueError` from `RerankRetriever`, keeping behavior deterministic and testable.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Rerank with `query.top_k` unchanged on base retriever | Reduces reranker benefit when fusion ordering places good chunks at the tail |
| Preserve RRF score alongside reranker score | Requires core model extension; deferred |
| Per-candidate `rerank_one` API | More round trips; harder to swap in batch cross-encoders later |
| Non-deterministic tie-breaking | Breaks reproducible tests and lecture demo expectations |
| Trust reranker contract without `RerankRetriever` validation | Silent contract violations; rejected in favor of fail-fast `ValueError` |

---

### ADR-027 — Future BGE Cross-Encoder Reranker Integration

**Status:** Accepted (documentation only — no Plan 09 implementation)

#### Context

`PROJECT.md` specifies `BAAI/bge-reranker-v2-m3` as the production reranker model. Plan 09 delivers orchestration and a deterministic stub only. Real model integration requires `torch` / `transformers` dependencies and is a separate deliverable.

#### Decision

* A **future plan** (backlog: BGE cross-encoder reranker runtime) will implement `BGECrossEncoderReranker` (exact class name may vary) in `retrieval/rerank.py` implementing the `Reranker` protocol.
* That plan will:
  * add approved model runtime dependencies (`torch`, `transformers`, or `sentence-transformers` as chosen in that plan);
  * score `(query.text, chunk.text)` pairs via `BAAI/bge-reranker-v2-m3`;
  * remain inside `knowledge_assistant.retrieval` — not MCP, agent, or `llm/`;
  * plug into existing `RerankRetriever` via constructor injection without API changes;
  * obey the Plan 09 candidate preservation contract (`len(output) == len(candidates)`) unless a **separate** future plan explicitly revises the `Reranker` contract to allow filtering.
* Plan 09 must **not** add `torch`, `transformers`, or `sentence-transformers` to `pyproject.toml`.
* `StubReranker` remains the default for tests, CI, and development without GPU.

#### Consequences

* Plan 09 completes the retrieval pipeline shape: dense → sparse → fusion → rerank (stub).
* Lecture demo can show reranking orchestration before model runtime is integrated.
* MCP plans can depend on `RerankRetriever` interface stability.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Bundle real BGE reranker into Plan 09 | Violates one-capability scope; adds heavy dependencies |
| Place cross-encoder in `llm/` | Violates retrieval ownership; reranking is not LLM inference |
| MCP-owned reranking | Violates component boundaries in `docs/ARCHITECTURE.md` |
| Skip stub; mock only in tests | Loses deterministic dev path and import-boundary clarity |

---

## Design Evaluations

This section records Plan 09 answers to the explicit design questions. These are **decided**; implementation must not reopen them without a plan revision.

### 1. Should reranking wrap `Retriever` or only `FusionRetriever`?

| Approach | Assessment |
| -------- | ---------- |
| **A — Wrap any `Retriever` (ADR-024, ADR-025)** | **Selected.** `RerankRetriever` accepts `base_retriever: Retriever`. Production wiring passes `FusionRetriever`; unit tests may pass `FakeRetriever` or even `DenseRetriever`. |
| B — Hard-code `FusionRetriever` only | Couples reranking to hybrid fusion; blocks isolated reranking tests and dense-only experiments. |

**Rationale:** Plan 08 established `Retriever` for composable orchestration. Reranking is the next orchestrator layer, not a fusion special case.

---

### 2. How many candidates should the wrapped retriever request?

**Yes — request more candidates than final `top_k`.** Default multiplier `2` via `RerankRetrievalSettings.candidate_top_k_multiplier`. `RerankRetriever` forwards `candidate_top_k = query.top_k * multiplier` to the base retriever, then truncates reranked output to caller `query.top_k`.

Example: caller `top_k=5`, multiplier `2` → base retriever queried with `top_k=10` → rerank → return top 5.

When `candidate_top_k_multiplier=1`, reranking still works but with a narrower candidate pool (acceptable for minimal tests).

**Fusion interaction:** `candidate_top_k_multiplier` applies only to the `top_k` `RerankRetriever` forwards to its `base_retriever`. It does not modify, read, or couple to `FusionRetrievalSettings`. When the base retriever is `FusionRetriever`, each orchestration layer expands its own candidate pool independently (fusion expands leaf `top_k` internally; reranking expands the fused-result `top_k` it requests from fusion).

---

### 3. What does `SearchResult.score` mean after reranking?

Reranked `score` is the **reranker relevance score** (ADR-026). Higher is better. It is not a similarity probability and is not comparable to dense, sparse, or RRF values from earlier stages.

---

### 4. Should original retrieval scores be preserved?

**Out of scope.** Core `SearchResult` exposes one `score` field. Plan 09 overwrites it with the reranker score. Preserving per-stage scores would require core model changes or parallel metadata — deferred to a future observability plan if needed.

---

### 5. How should ties be broken deterministically?

When reranker scores tie:

1. Sort by reranker score descending.
2. Tie-break equal scores by `chunk_id` ascending (lexicographic string order).

`StubReranker` and all Plan 09 `Reranker` implementations rely on this rule. Dedicated unit tests must assert tie ordering.

**Broader determinism requirement (ADR-026):** for identical `query` and `candidates` inputs, reranking must produce identical scores and identical ordering on every invocation. Unit tests must call `rerank()` twice with the same inputs and assert byte-for-byte equal output tuples (scores and order).

---

### 6. What should happen when the base retriever returns fewer candidates than requested?

Rerank **all candidates returned** by the base retriever. Do not raise an error. Do not pad with synthetic results. Final output length is `min(len(base candidates), query.top_k)` after reranking and truncation.

---

### 7. Should reranking be allowed to drop candidates?

**Plan 09 contract:** `Reranker` does not drop candidates. Input `N` candidates → output `N` candidates. Rerankers only rescale scores and reorder.

| Mechanism | Plan 09 behavior |
| --------- | ---------------- |
| `Reranker.rerank` | **No dropping** — `len(output) == len(candidates)` always |
| `RerankRetriever` truncation to `query.top_k` | **Yes** — the **only** candidate reduction in Plan 09 |
| Score-threshold filtering or confidence cutoffs | **Out of scope** — requires a separate future plan and explicit contract revision |

**Enforcement:** `RerankRetriever` raises `ValueError` when `len(reranked) != len(candidates)` for non-empty input. Rerankers cannot silently violate the contract.

---

### 8. Should `Reranker` accept `SearchQuery` or raw query text?

**`SearchQuery` (ADR-025).** `Reranker.rerank(query: SearchQuery, candidates: ...)` uses `query.text` for scoring. Accepting the full domain type keeps reranking aligned with `Retriever.retrieve` and avoids parallel string-only contracts. `Reranker` does **not** use `query.top_k` for scoring — truncation remains `RerankRetriever` responsibility.

---

### 9. Should reranking be batch-oriented?

**Single-query batch only (ADR-026).** One `rerank()` call receives the full candidate tuple for one `SearchQuery` and returns the reranked tuple. This matches cross-encoder batch scoring shape for the future BGE plan. Multi-query batch APIs are out of scope.

---

### 10. Where will real BGE reranker integration live in a future plan?

**`retrieval/rerank.py`** — new `Reranker` implementation (e.g. `BGECrossEncoderReranker`) in a future backlog plan authorized separately. Injected into `RerankRetriever` at assembly time. No MCP, agent, storage, or `llm/` changes. See ADR-027.

---

## Module Layout

### Retrieval (new and modified files)

```text
src/knowledge_assistant/retrieval/
    __init__.py           # add reranking exports; update module docstring
    protocol.py           # UNCHANGED (Retriever protocol from Plan 08)
    config.py             # add RerankRetrievalSettings (existing settings unchanged)
    rerank.py             # NEW: Reranker, StubReranker, RerankRetriever
    fusion.py             # UNCHANGED
    dense.py              # UNCHANGED
    sparse.py             # UNCHANGED
    embeddings.py         # UNCHANGED
    sparse_vectors.py     # UNCHANGED
    exceptions.py         # UNCHANGED (no new exception types required)
```

Do not create `retrieval/utils/` or `retrieval/rerank/` subpackages.

### Storage, Indexing, Core

**No modifications.**

---

## API Design

### Reranker Protocol

**Module:** `retrieval/rerank.py`

```python
class Reranker(Protocol):
    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]:
        """Score and reorder retrieval candidates for one search query."""
        ...
```

Structural conformance: `StubReranker`, future `BGECrossEncoderReranker`, test fakes.

**Contract (Plan 09):**

* Input: `N` candidates → output: `N` candidates.
* Rerankers do not add candidates, do not remove candidates, and do not filter by score threshold.
* Rerankers rescale `SearchResult.score` and reorder candidates only.
* The protocol returns `SearchResult` objects (not bare score tuples) for consistency with leaf retriever and fusion contracts; rerankers conceptually score existing candidates.
* `RerankRetriever` enforces the contract: if `len(reranked) != len(candidates)` when candidates are non-empty, raise `ValueError`.

---

### RerankRetrievalSettings

**Module:** `retrieval/config.py`

```python
@dataclass(frozen=True, slots=True)
class RerankRetrievalSettings:
    candidate_top_k_multiplier: int = 2
```

Validation in `__post_init__`:

* `candidate_top_k_multiplier >= 1`

```python
def resolve_candidate_top_k(self, query_top_k: int) -> int:
    """Candidate pool size forwarded to the base retriever."""
    return query_top_k * self.candidate_top_k_multiplier
```

`resolve_candidate_top_k` relies on the existing `SearchQuery.top_k >= 1` invariant (enforced in `core`). It does not require separate defensive validation of `query_top_k` unless the implementation chooses to keep the helper trivially simple.

`DenseRetrievalSettings` and `FusionRetrievalSettings` remain unchanged in the same module.

---

### StubReranker

**Module:** `retrieval/rerank.py`

Deterministic reranker stub (no model runtime):

1. If `candidates` is empty, return `()`.
2. For each candidate, compute a deterministic relevance score from `query.text` and `candidate.chunk.text` (e.g. normalized token overlap or hash-derived float in `[0.0, 1.0]`).
3. Build new `SearchResult` entries with `score` set to the computed reranker score; preserve `chunk` payloads unchanged.
4. Sort by score descending; tie-break by `chunk_id` ascending.
5. Return the sorted tuple with `len(output) == len(candidates)`.

Requirements:

* `len(output) == len(candidates)` for every non-empty input (candidate preservation contract);
* fully deterministic for identical inputs (identical scores and ordering on repeated calls);
* no `torch`, `transformers`, or `sentence-transformers`;
* no LLM calls;
* no threshold filtering or candidate dropping.

**Visibility:** scoring helper functions may be module-public in `rerank.py` for unit tests if needed; they are internal retrieval-layer helpers, not package `__init__` exports.

---

### RerankRetriever

**Module:** `retrieval/rerank.py`

```python
class RerankRetriever:
    def __init__(
        self,
        *,
        base_retriever: Retriever,
        reranker: Reranker,
        settings: RerankRetrievalSettings,
    ) -> None: ...

    def retrieve(self, query: SearchQuery) -> RetrievalResult:
        ...
```

**`retrieve` behavior:**

1. Compute `candidate_top_k = settings.resolve_candidate_top_k(query.top_k)`.
2. Build `candidate_query = SearchQuery(text=query.text, top_k=candidate_top_k)`.
3. Call `base_retriever.retrieve(candidate_query)`.
4. Extract `candidates` from `RetrievalResult.results`.
5. Call `reranker.rerank(query=query, candidates=candidates)`.
6. When `len(candidates) > 0`, validate `len(reranked) == len(candidates)`; raise `ValueError` if the reranker returns a different candidate count (candidate preservation contract enforcement).
7. Truncate reranked tuple to `query.top_k` — the **only** candidate reduction in Plan 09.
8. Return `RetrievalResult(query=query, results=reranked[:query.top_k])`.

**Query echo semantics:** `RerankRetriever` returns `RetrievalResult` with the **original caller** `query`. The base retriever receives `candidate_query` and may echo that query in its own `RetrievalResult` — `RerankRetriever` does not validate or reuse the base result's `query` field.

**Forbidden public APIs:**

* vector-accepting methods;
* direct `VectorStore` access;
* exposure of base retriever or reranker internals.

**Error propagation:** exceptions from the base retriever or reranker propagate unchanged. `RerankRetriever` does not catch and translate those failures. Additionally, `RerankRetriever` raises `ValueError` when a non-empty candidate list produces a reranker output with a mismatched length — this is orchestrator-side contract enforcement, not reranker exception translation.

**Empty results:** if the base retriever returns `()`, return `RetrievalResult(query=query, results=())` without calling the reranker (no candidate-count validation required for empty input).

---

### Public API Exports

**`retrieval/__init__.py`:**

* `RerankRetriever`
* `RerankRetrievalSettings`
* `Reranker` (protocol)
* `StubReranker`

Do **not** re-export internal scoring helpers from `retrieval/__init__.py`.

Update module docstring to reflect reranking capability.

---

## Reranking Flow

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
sort by reranker score + tie-break by chunk_id
    ↓
truncate to query.top_k
    ↓
RetrievalResult(query=caller_query, results=reranked)
```

### Production wiring (documentation only)

```text
RerankRetriever(
    base_retriever=FusionRetriever(
        dense_retriever=DenseRetriever(...),
        sparse_retriever=SparseRetriever(...),
        settings=FusionRetrievalSettings(),
    ),
    reranker=StubReranker(),
    settings=RerankRetrievalSettings(),
)
```

### Boundary Responsibilities

| Layer | Input | Output | Vectors / storage |
| ----- | ----- | ------ | ----------------- |
| Caller (future MCP/agent) | `SearchQuery` | `RetrievalResult` | none |
| `RerankRetriever` | `SearchQuery` | `RetrievalResult` | orchestrates base retriever + reranker only |
| Base `Retriever` (e.g. `FusionRetriever`) | `SearchQuery` | `RetrievalResult` | delegates to leaf retrievers (unchanged) |
| `Reranker` | `SearchQuery`, `N` candidates | `N` reranked candidates (reordered, rescaled scores) | none |

No LLM calls. No storage changes. No modifications to fusion or leaf retrievers.

**Fusion + rerank candidate pools:** when `base_retriever` is `FusionRetriever`, fusion leaf expansion (`leaf_top_k_multiplier`) and reranking expansion (`candidate_top_k_multiplier`) are independent settings with no cross-layer coupling.

---

## Score Semantics

| Stage | `SearchResult.score` meaning |
| ----- | ---------------------------- |
| `DenseRetriever` output | Raw dense similarity (unchanged, ADR-014) |
| `SparseRetriever` output | Raw sparse similarity (unchanged, ADR-017) |
| `FusionRetriever` output | RRF fusion score (ADR-023) |
| `RerankRetriever` output | **Reranker relevance score** (ADR-026) |

Callers of `RerankRetriever` must treat reranked scores as **ordinal ranking keys**, not calibrated relevance probabilities.

---

## Dependency Rules

### Allowed Dependencies (Reranking Production Code)

Reranking modules (`rerank.py`) may import only:

* `knowledge_assistant.core` (domain types);
* `knowledge_assistant.retrieval.protocol`;
* `knowledge_assistant.retrieval.config`;
* Python standard library.

Base retrievers and rerankers are supplied by callers via constructor injection. Reranking production code must **not** import `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, or other concrete retriever implementations.

`RerankRetriever` must **not** import `storage.protocol.VectorStore` — it delegates to injected `Retriever` instances.

### Forbidden Dependencies

Reranking production code must **not** import:

* `qdrant_client`;
* `knowledge_assistant.storage` (any submodule);
* `knowledge_assistant.indexing` (any submodule);
* `knowledge_assistant.agent`;
* `knowledge_assistant.mcp_server`;
* `knowledge_assistant.llm`;
* `llama_index` / `llama-index`;
* `torch`, `sentence_transformers`, `transformers`.

`DenseRetriever`, `SparseRetriever`, `FusionRetriever`, and leaf retriever production modules remain unchanged; their existing dependency rules stand.

### Import-Boundary Tests

Extend `tests/unit/retrieval/test_retrieval_imports.py`:

* `rerank.py` follows the same forbidden-import rules as `fusion.py` and `protocol.py`;
* `rerank.py` must not import `storage`;
* `rerank.py` must not import `torch`, `transformers`, or `sentence_transformers`.

---

## Testing Strategy

| Level | Location | What is tested | Dependencies |
| ----- | -------- | -------------- | ------------ |
| Unit | `tests/unit/retrieval/test_rerank.py` | `RerankRetrievalSettings`, `StubReranker` determinism and tie-breaking | None |
| Unit | `tests/unit/retrieval/test_rerank_retriever.py` | orchestration, candidate_top_k forwarding, empty results, errors | `FakeRetriever`, `StubReranker` |
| Integration | `tests/integration/retrieval/test_rerank_retriever_integration.py` | end-to-end `RerankRetriever` with fake base retriever | No Qdrant |

**No Qdrant-specific behavior in reranking tests.** Storage and leaf retriever Qdrant tests remain in their respective packages.

### Unit Tests — RerankRetrievalSettings (required)

* default `candidate_top_k_multiplier == 2`;
* `resolve_candidate_top_k(5)` returns `10` with default multiplier;
* `candidate_top_k_multiplier < 1` raises `ValueError`.

### Unit Tests — StubReranker (required)

* empty candidates → `()`;
* `len(output) == len(candidates)` for non-empty inputs (candidate preservation);
* deterministic scores for same `query` and `candidates`;
* repeated `rerank()` with identical inputs returns identical output tuples (scores and order);
* higher-scoring candidate sorts before lower-scoring candidate;
* reranked `SearchResult.score` replaces input score (not equal to prior RRF/dense score in fixture);
* tie on reranker score → `chunk_id` ascending order;
* every input `chunk_id` appears exactly once in output (no additions, no removals);
* `chunk` payloads unchanged.

### Unit Tests — RerankRetriever (required)

* calls base retriever exactly once per `retrieve`;
* forwards `SearchQuery(text=..., top_k=candidate_top_k)` with `candidate_top_k = query.top_k * multiplier`;
* passes **caller** `query` to `reranker.rerank`, not `candidate_query`;
* returns `RetrievalResult` with caller `query` echoed;
* truncates to caller `query.top_k` (only candidate reduction in Plan 09);
* reranker returns `len(candidates)` results before truncation;
* raises `ValueError` when a test double reranker returns fewer or more candidates than received (contract violation);
* reranker scores replace previous scores in output;
* propagates base retriever exceptions unchanged;
* propagates reranker exceptions unchanged;
* empty base results handled;
* fewer base candidates than `candidate_top_k` handled without error;
* existing dense, sparse, and fusion retriever behavior unchanged; existing tests continue to pass without semantic updates.

### Integration Tests (required)

Using `FakeRetriever` in `tests/integration/retrieval/conftest.py`:

* `RerankRetriever` with fake base retriever returning predetermined candidates;
* verify reranked ordering differs from base order when stub scores dictate;
* verify base `top_k` argument recorded on fake (`candidate_top_k`);
* verify final result length `<= query.top_k`;
* verify scores in final output match `StubReranker` expectations.

**Not in scope:** Docker Qdrant; real BGE reranker; MCP; agent; fusion or leaf retriever modifications.

---

## Dependencies

Do **not** add new runtime dependencies for Plan 09.

Do **not** add `torch`, `sentence-transformers`, `transformers`, `langgraph`, `mcp`, or `openai`.

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-024 through ADR-027 from this plan;
* `docs/ARCHITECTURE.md`:
  * reranking retrieval path diagram after fusion;
  * module table entries for `rerank.py`, `RerankRetrievalSettings`;
  * document reranking orchestration, candidate preservation contract, candidate expansion, fusion pool independence, and reranked score semantics;
  * replace "Reranking is deferred" with reranking implemented, BGE runtime deferred;
* `docs/PROGRESS.md` — record Plan 09 completion when done.

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Acceptance Criteria

### Protocol and Settings

- [x] `Reranker` protocol defined in `retrieval/rerank.py` with `rerank(query: SearchQuery, candidates: tuple[SearchResult, ...]) -> tuple[SearchResult, ...]`
- [x] `Reranker` contract: `len(output) == len(candidates)`; no add/remove/filter inside reranker
- [x] `RerankRetrievalSettings` defined with `candidate_top_k_multiplier: int = 2`
- [x] Settings validation: `candidate_top_k_multiplier >= 1`
- [x] `resolve_candidate_top_k(query_top_k)` returns `query_top_k * candidate_top_k_multiplier`
- [x] `resolve_candidate_top_k` relies on `SearchQuery.top_k >= 1`; no separate defensive validation required unless implementation keeps the helper trivially simple

### Reranker Contract and Stub Reranker

- [x] `Reranker` preserves candidate count: `len(output) == len(candidates)` for non-empty inputs
- [x] `Reranker` does not add, remove, or filter candidates — only rescales scores and reorders
- [x] `StubReranker` implemented in `retrieval/rerank.py`
- [x] Fully deterministic: identical inputs produce identical scores and ordering
- [x] Deterministic scoring without model runtime
- [x] Tie-break on equal reranker score by `chunk_id` ascending
- [x] Empty input returns `()`

### RerankRetriever

- [x] `RerankRetriever` implements `retrieve(query: SearchQuery) -> RetrievalResult`
- [x] Accepts `base_retriever: Retriever`, `reranker: Reranker`, `settings: RerankRetrievalSettings`
- [x] Does not import or call `VectorStore` directly
- [x] Does not import dense, sparse, or fusion concrete retrievers
- [x] Invokes base retriever with expanded `candidate_top_k`
- [x] Passes caller `query` to `reranker.rerank`
- [x] Returns `RetrievalResult` with caller `query` and at most `query.top_k` results
- [x] Candidate reduction occurs only via final truncation to `query.top_k` (not inside `Reranker`)
- [x] Validates `len(reranked) == len(candidates)` when candidates are non-empty
- [x] Raises `ValueError` on candidate-count contract violation (no `assert`; no new exception types)
- [x] Reranked `SearchResult.score` holds reranker value
- [x] Base retriever and reranker exceptions propagate unchanged
- [x] Empty base results produce valid reranked output
- [x] Fewer base candidates than requested handled without error

### Leaf, Fusion, and Boundaries

- [x] Do not modify `DenseRetriever`, `SparseRetriever`, or `FusionRetriever` production code
- [x] Existing dense, sparse, and fusion retriever behavior unchanged; existing tests pass without semantic updates
- [x] `SearchQuery`, `SearchResult`, `RetrievalResult` unchanged in `core`
- [x] No `VectorStore` protocol changes
- [x] No indexing changes
- [x] Production reranking code (`rerank.py`) imports only `core`, `retrieval.protocol`, `retrieval.config`, and stdlib
- [x] Production reranking code does not import `VectorStore`, `qdrant_client`, `storage`, `indexing`, `mcp_server`, `agent`, `llm`, LlamaIndex, or model runtimes

### Tests

- [x] Unit tests in `tests/unit/retrieval/test_rerank.py` for settings, candidate preservation, and full determinism
- [x] Unit tests in `tests/unit/retrieval/test_rerank_retriever.py` for orchestration and `ValueError` on contract violation
- [x] Integration tests in `tests/integration/retrieval/test_rerank_retriever_integration.py` with `FakeRetriever`
- [x] Import-boundary tests extended for `rerank.py`
- [x] Existing dense, sparse, and fusion tests continue to pass without semantic updates

### Validation and Documentation

- [x] ADR-024 through ADR-027 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents reranking path and score semantics
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes on modified packages
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into BGE runtime or MCP | Explicit non-scope; stub-only deliverable; ADR-027 defers model |
| Accidental modification of fusion or leaf retrievers | Acceptance criterion: do not modify production leaf/fusion code |
| `RerankRetriever` imports `VectorStore` or concrete retrievers | ADR-024; depends on `Retriever` protocol only |
| Non-deterministic ordering on reranker ties | ADR-026 tie-break by `chunk_id`; dedicated unit tests |
| Base `top_k` equals caller `top_k` reduces rerank quality | Default `candidate_top_k_multiplier=2`; tests verify forwarding |
| Score semantics confusion across pipeline stages | Document per-stage score table in architecture and ADR-026 |
| Empty-candidate reranker call inconsistency | Specify skip-or-empty behavior; test empty base results |
| Stub reranker unlike real cross-encoder | Contract shape only; BGE plan replaces stub via injection |
| Ambiguity about reranker-side candidate filtering | ADR-026 candidate preservation contract; filtering deferred to separate plan |
| Silent reranker contract violations | `RerankRetriever` validates candidate count and raises `ValueError` on mismatch |
| Double candidate expansion with fusion base retriever | Document independent settings; no `FusionRetrievalSettings` coupling |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-024 through ADR-027 in `docs/DECISIONS.md`.
2. **Extend `retrieval/config.py`** — add `RerankRetrievalSettings` with validation and `resolve_candidate_top_k`.
3. **Create `retrieval/rerank.py`** — define `Reranker` protocol and implement `StubReranker`.
4. **Implement `RerankRetriever`** — orchestrate base retriever, reranker, candidate-count validation (`ValueError`), and truncation.
5. **Update `retrieval/__init__.py`** — export reranking public API; update module docstring.
6. **Add unit tests** — `test_rerank.py` for settings and stub; `test_rerank_retriever.py` for orchestration.
7. **Extend import guard tests** — `rerank.py` in `test_retrieval_imports.py`.
8. **Add integration tests** — `test_rerank_retriever_integration.py` with `FakeRetriever`.
9. **Update `docs/ARCHITECTURE.md`** — reranking path, modules, score semantics.
10. **Run validation suite** — all four quality commands; fix until pass.
11. **Update progress** — record completion in `docs/PROGRESS.md`.
12. **Verify non-scope compliance** — no BGE runtime, no storage/indexing/core changes; do not modify leaf or fusion production code.

---

## Checklist

### Architectural Decisions

- [x] Transcribe ADR-024 (Reranking Boundary) into `docs/DECISIONS.md`
- [x] Transcribe ADR-025 (Reranker Protocol) into `docs/DECISIONS.md`
- [x] Transcribe ADR-026 (Reranked Score Semantics and Candidate Pool) into `docs/DECISIONS.md`
- [x] Transcribe ADR-027 (Future BGE Cross-Encoder Reranker) into `docs/DECISIONS.md`

### Configuration

- [x] Add `RerankRetrievalSettings` to `retrieval/config.py`
- [x] Validate `candidate_top_k_multiplier >= 1`
- [x] Implement `resolve_candidate_top_k`

### Reranking Implementation

- [x] Create `retrieval/rerank.py` with `Reranker` protocol
- [x] Implement `StubReranker` (deterministic, candidate-preserving, no model runtime)
- [x] Implement `RerankRetriever` with `Retriever` + `Reranker` dependencies
- [x] Validate `len(reranked) == len(candidates)` and raise `ValueError` on violation
- [x] Forward expanded `candidate_top_k` to base retriever (independent of fusion leaf expansion)
- [x] Truncate reranked output to caller `query.top_k` (only candidate reduction in Plan 09)

### Public API

- [x] Update `retrieval/__init__.py` exports
- [x] Confirm `fusion.py`, `dense.py`, `sparse.py`, `embeddings.py` unchanged

### Unit Tests

- [x] `tests/unit/retrieval/test_rerank.py` — settings, stub determinism, tie-breaking
- [x] `tests/unit/retrieval/test_rerank_retriever.py` — orchestration, candidate_top_k, errors, `ValueError` on contract violation
- [x] Extend `tests/unit/retrieval/test_retrieval_imports.py`

### Integration Tests

- [x] `tests/integration/retrieval/test_rerank_retriever_integration.py` with `FakeRetriever`

### Validation and Documentation

- [x] All quality commands pass
- [x] `docs/ARCHITECTURE.md` updated
- [x] `docs/PROGRESS.md` updated on completion

### Non-Scope Verification

- [x] No real BGE reranker or `torch` / `transformers` / `sentence-transformers`
- [x] No MCP, agent, or LLM integration
- [x] No `core` model changes
- [x] No storage or indexing changes
- [x] Do not modify `DenseRetriever`, `SparseRetriever`, or `FusionRetriever` production code
