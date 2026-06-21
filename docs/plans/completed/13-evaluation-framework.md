# Plan 13 — Evaluation Framework

**Status:** Completed

**Completed:** 2026-06-21

**Roadmap:** Phase 8 — Evaluation

**Depends on:**

* [Plan 03 — Domain Models](../completed/03-domain-models.md)
* [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)
* [Plan 07 — Sparse Retrieval](../completed/07-sparse-retrieval.md)
* [Plan 08 — Fusion Retrieval](../completed/08-fusion-retrieval.md)
* [Plan 09 — Reranking](../completed/09-reranking.md)

**Plan principle:** One plan introduces one architectural capability. Plan 13 introduces a **retrieval-only evaluation layer** that measures ranked retrieval quality against a shared benchmark dataset — without evaluating LLM answers, agent behavior, or MCP integration.

---

## Authorization

**Authorized and completed.** ADR-047 through ADR-050 are recorded in `docs/DECISIONS.md`.

---

## Objective

Design and implement a dedicated **evaluation layer** that measures retrieval quality across retrieval strategies using a shared benchmark dataset and common retrieval metrics.

```text
EvaluationDataset                          ← first-class asset under data/evaluation/
        ↓
EvaluationRunner.run(retriever, ...)       ← repeated per retrieval strategy
        ↓
Retriever.retrieve(SearchQuery)          ← any Retriever implementation
        ↓
RetrievalResult
        ↓
Metrics (Recall@K, Hit Rate@K, MRR)
        ↓
EvaluationReport                           ← one per strategy (dense, sparse, fusion, rerank)
        ↓
compare_evaluation_reports(...)            ← side-by-side strategy comparison
        ↓
ComparisonReport
```

After this plan is complete:

* **`knowledge_assistant.evaluation`** exposes dataset loading, metric computation, an evaluation runner, single-strategy reports, and **multi-strategy comparison reports**;
* any `Retriever` implementation (`DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `RerankRetriever`, or test fakes) can be evaluated with the same API;
* evaluation is **retrieval-quality only** — no LLM, agent, MCP, storage, or indexing imports in production evaluation code;
* a committed **retrieval benchmark** under `data/evaluation/` targets the project's **synthetic corporate knowledge base** (see `PROJECT.md`) — a first-class project asset owned by the evaluation layer, not derived from `tests/` fixtures;
* **`ComparisonReport`** makes side-by-side comparison of dense, sparse, fusion, and rerank strategies an explicit Phase 8 capability;
* reports are suitable for unit tests, strategy comparison, and future CLI output.

**Dependency rule:** evaluation production code may depend on `knowledge_assistant.core`, `knowledge_assistant.retrieval.protocol.Retriever`, and the Python standard library only. It must **not** import `storage`, `qdrant_client`, `indexing`, `mcp_server`, `llm`, `agent`, `langgraph`, `llama_index`, concrete retrieval orchestrators, embedding providers, or model runtimes.

**Wiring rule:** tests, CLI bootstrap (future), and demo scripts may construct concrete retrievers and pass them into `EvaluationRunner`. That assembly lives **outside** `knowledge_assistant.evaluation` production modules.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/evaluation/` — dataset models, metrics, runner, report, comparison, settings, optional text formatting;
* `data/evaluation/` — committed retrieval benchmark dataset and document registry (first-class project assets);
* associated unit tests under `tests/unit/evaluation/` using **minimal test-only JSON snippets** in `tests/unit/evaluation/fixtures/` (not the production benchmark);
* optional integration tests under `tests/integration/evaluation/` that wire real retriever stacks against an **indexed synthetic knowledge-base corpus** (assembly in test conftest only);
* ADR entries and documentation updates on completion.

### In Scope

* `EvaluationCase`, `EvaluationDataset`, `DocumentRegistry`, and JSON dataset loader;
* document-level relevance judgments via **benchmark-local document keys** (see Design Evaluation 2);
* `EvaluationSettings` with configurable metric `@K` cutoffs and evaluation `top_k`;
* pure metric functions: **Recall@K**, **Hit Rate@K**, **MRR**;
* `EvaluationRunner` accepting any `Retriever` plus `retriever_label` for reports;
* `EvaluationReport` and per-case result records (macro-averaged metrics + case breakdown);
* **`ComparisonReport`**, `compare_evaluation_reports(...)`, and `format_comparison_report(...)` for side-by-side retrieval-strategy comparison;
* human-readable report formatters for single-strategy and comparison output (stdlib string formatting only);
* committed retrieval benchmark under `data/evaluation/` targeting the synthetic knowledge-base corpus described in `PROJECT.md` (target **50–100** curated questions; see Design Evaluation 5);
* import-boundary tests for `evaluation/` production modules;
* ADR-047 through ADR-050 (proposed below);
* updates to `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/PROGRESS.md` on completion.

---

## Non-Scope

This plan does **not** authorize:

* LLM answer quality, hallucination detection, or LLM-as-a-Judge evaluation;
* prompt quality or RAG prompt evaluation;
* agent behavior, tool-calling quality, or LangGraph routing evaluation;
* MCP handler or transport evaluation;
* end-to-end question-answering evaluation;
* query rewriting or retrieval retry evaluation;
* changes to `Retriever` protocol, retrieval orchestrators, or retrieval algorithms;
* changes to `knowledge_assistant.core` domain models (`SearchQuery`, `SearchResult`, `RetrievalResult`, `Chunk`, etc.);
* storage, indexing, MCP, agent, or LLM implementation changes;
* real BGE-M3 / BGE reranker model runtime (evaluation may run against stub retrievers only in CI);
* NDCG or other graded-relevance metrics (deferred — see Design Evaluations);
* chunk-level expected relevance labels (deferred — see Design Evaluations);
* automated LLM-generated benchmark expansion;
* evaluation report persistence to database or external observability platforms;
* Langfuse, tracing, or production monitoring;
* CLI subcommand wiring (deferred to Plan 15 or a dedicated CLI plan);
* Docker Compose, live Qdrant smoke requirements for unit tests;
* Pydantic in evaluation production code (frozen dataclasses per ADR-001 style).

---

## Architectural Decisions (Proposed ADRs)

The following decisions are **proposed** for Plan 13. Implementation must follow them; reopen only via plan revision. Record in `docs/DECISIONS.md` on implementation.

### ADR-047 — Evaluation Layer Ownership

**Status:** Proposed

#### Context

`PROJECT.md` lists retrieval evaluation as a project goal. Plans 06–09 deliver composable retrievers behind `Retriever`. Higher layers (MCP, agent, LLM) must not own retrieval-quality measurement. Without an explicit evaluation boundary, metrics logic risks appearing in retrieval tests, CLI scripts, or agent workflows — violating component ownership and making strategy comparison inconsistent.

#### Decision

* Implement retrieval evaluation in a dedicated package: `knowledge_assistant.evaluation`.
* The evaluation layer owns:
  * benchmark dataset models, document registry, and loading;
  * retrieval metric definitions and aggregation;
  * `EvaluationRunner` orchestration over `Retriever.retrieve`;
  * structured `EvaluationReport` output;
  * **`ComparisonReport` assembly and formatting** for multi-strategy retrieval comparison.
* The evaluation layer owns the **retrieval benchmark** as a first-class asset under `data/evaluation/`. Benchmark questions target the synthetic corporate knowledge base; benchmark data is **not** owned by or derived from `tests/` fixtures.
* The evaluation layer does **not** own:
  * retrieval algorithms;
  * indexing or storage;
  * MCP handlers;
  * agent orchestration;
  * LLM inference;
  * answer generation or citation rendering.
* Evaluation measures **ranked retrieval output only** — inputs are `SearchQuery`; outputs are analyzed `RetrievalResult` tuples.
* Production code in `evaluation/` depends on `knowledge_assistant.core` and `knowledge_assistant.retrieval.protocol.Retriever` only, plus the Python standard library.
* Concrete retriever construction (`DenseRetriever`, `FusionRetriever`, etc.) belongs in tests, future CLI wiring, or demo scripts — not in `evaluation/` production modules.

#### Consequences

* Retrieval strategies are comparable on equal footing using one runner and one dataset.
* Evaluation runs without Qdrant, MCP, LangGraph, or LLM when tests inject fake retrievers.
* Phase 8 lecture flow runs four wired retrievers against one benchmark and prints a **`ComparisonReport`** table (dense vs sparse vs fusion vs rerank).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Metrics inside `retrieval/` | Couples measurement to the subsystem under test; violates single-responsibility |
| MCP tool `evaluate_retrieval` | Evaluation is offline/batch analysis, not agent knowledge access |
| Agent-side evaluation loop | Conflates orchestration quality with retrieval quality |
| pytest-only helpers without a package | Not reusable for CLI comparison or lecture demos |

---

### ADR-048 — Evaluation Dataset Format

**Status:** Proposed

#### Context

Retrieval evaluation requires stable ground-truth labels independent of any one retriever. The project knowledge base consists of **synthetic corporate documents** (remote work policy, onboarding, travel, security, etc.) per `PROJECT.md`. Plan 14 will expand the committed demo corpus; Plan 13 must define a **first-class benchmark** that targets that corpus — not indexing unit-test fixtures under `tests/`.

The benchmark is a project asset owned by the evaluation layer. Test fixtures remain test fixtures: they may reuse similar *shapes* for loader validation but must not define benchmark validity or long-term label provenance.

#### Decision

* Store benchmark data as **committed JSON files** under `data/evaluation/`.
* Top-level schema:

```json
{
  "dataset_id": "string",
  "description": "string",
  "corpus_version": "string",
  "documents": {
    "remote-work-policy": {
      "path": "knowledge/policies/remote_work_policy.md"
    }
  },
  "cases": [
    {
      "case_id": "string",
      "question": "string",
      "expected_document_key": "remote-work-policy"
    }
  ]
}
```

* **`DocumentRegistry`** (evaluation-local): maps benchmark-local **`document_key`** strings to canonical **`path`** strings (relative paths within the synthetic knowledge-base tree). Keys are **stable benchmark identifiers** owned by the evaluation dataset — not derived from ADR-008 UUID generation.
* **`EvaluationCase`** fields:
  * `case_id: str` — stable identifier for reports;
  * `question: str` — natural-language query passed to `SearchQuery.text`;
  * `expected_document_key: str` — key into the dataset `documents` registry (single relevant document for Plan 13 v1).
* **`EvaluationDataset`** aggregates `dataset_id`, optional `description`, optional `corpus_version`, `documents` registry, and `cases`.
* Loader: `load_evaluation_dataset(path: Path) -> EvaluationDataset` using stdlib `json` only.
* Validation at load time:
  * non-empty `dataset_id`;
  * non-empty `documents` registry;
  * at least one case;
  * non-empty `case_id`, `question`, `expected_document_key` per case;
  * every `expected_document_key` references a key present in `documents`;
  * unique `case_id` values within a dataset;
  * each registry entry has non-empty `path`.
* **Plan 13 v1 uses document-level labels only.** Optional chunk-level labels are **not** part of the v1 schema.
* **Manual curation.** Maintainers author questions against the synthetic knowledge-base corpus. Paths in the registry align with the planned corpus layout (`PROJECT.md` policy document themes).
* **Target scale:** **50–100** evaluation questions for meaningful strategy comparison (see Design Evaluation 5). Plan 13 may land the framework before all cases are authored; acceptance requires the format, loader, and comparison tooling — full benchmark population may complete incrementally before Plan 15 demo, but **50–100** is the design target, not a minimal smoke subset.
* **No dependency on `tests/` fixtures.** Unit tests validate loaders and metrics using tiny JSON files in `tests/unit/evaluation/fixtures/` only. The production benchmark lives exclusively under `data/evaluation/`.
* Plan 14 may add corpus files under a knowledge-base directory; Plan 13 benchmark registry paths must remain consistent with that layout. Plan 14 does not own the benchmark — it owns corpus content; evaluation owns benchmark labels.

#### Consequences

* Benchmark labels survive indexing-internal ID changes (ADR-008) as long as indexed `SourceReference.document_path` matches registry paths.
* Datasets are version-controlled, diffable, and agent-legible.
* No runtime dependency on indexing code to parse dataset files.
* Corpus path changes require a **benchmark dataset version bump** (update registry paths and `corpus_version`), not silent relabeling.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| YAML dataset | Requires non-stdlib dependency or custom parser |
| Dataset embedded only in Python test modules | Harder to reuse for CLI and lecture comparison; conflates tests with benchmark |
| Benchmark derived from `tests/unit/indexing/fixtures/` | Couples long-term evaluation validity to test fixtures; rejected per review |
| `expected_document_id` (UUID5) as primary label | Tightly couples benchmark to ADR-008 path normalization and indexing internals; see Design Evaluation 2 |
| LLM-automated question generation in Plan 13 | Non-deterministic; expands scope |
| Chunk-level labels in v1 | Higher maintenance; defer |

---

### ADR-049 — Retrieval Metric Selection

**Status:** Proposed

#### Context

Plan 13 must quantify retrieval quality with standard, interpretable metrics comparable across `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, and `RerankRetriever`. The v1 dataset uses **one relevant document per question** (binary relevance at document granularity). Metric choice must match label granularity without implying answer correctness.

#### Decision

**Include in Plan 13:**

| Metric | Definition (per case) | Aggregation |
| ------ | ---------------------- | ------------- |
| **Hit Rate@K** | `1.0` if any result in top `K` matches the expected document (via normalized path from registry key), else `0.0` | Macro mean across cases |
| **Recall@K** | Same as Hit Rate@K when exactly one relevant document exists per case | Macro mean across cases |
| **MRR** | `1 / rank` of the first matching document in the full evaluated ranking (`rank` is 1-based); `0.0` if no match within evaluated `top_k` | Mean across cases |

**Configuration:**

* `EvaluationSettings.metrics_k: tuple[int, ...]` — default `(1, 3, 5)` for Hit Rate@K and Recall@K reporting.
* `EvaluationSettings.eval_top_k: int` — passed to `SearchQuery.top_k` for every case; must be `>= max(metrics_k)`.
* Metrics inspect **`RetrievalResult.results` order** as returned by the retriever — no re-sorting in the evaluation layer.
* **Relevance matching (Plan 13 v1):** resolve `expected_document_key` → registry `path`, normalize path strings, compare against **`SearchResult.source.document_path`** (normalized). Do not import indexing or recompute ADR-008 `DocumentId` values inside the evaluation layer.
* **`SearchResult.chunk.metadata.document_id`** is not the primary benchmark label. It may appear in debug fields on case results but is not the qrel matching key.

**Defer NDCG** to a future evaluation plan. Rationale:

* NDCG requires graded relevance judgments (multiple levels per document/chunk).
* Plan 13 v1 labels are binary and document-level with one gold document per case.
* With single relevant documents, NDCG@K collapses toward Hit Rate@K / MRR behavior while adding ranking-formula complexity and lecture distraction.
* Chunk-level or multi-document benchmarks can justify NDCG in a follow-up plan with an extended dataset schema.

**Explicitly exclude from Plan 13 metrics:**

* answer correctness;
* citation formatting quality;
* LLM judge scores;
* latency (optional future plan);
* nDCG, MAP (multi-relevant variants deferred with richer labels).

#### Consequences

* Reports are easy to explain in the Production RAG lecture.
* Same metrics apply uniformly to all `Retriever` implementations.
* When Plan 13 later adds multi-document relevance, Recall@K and Hit Rate@K definitions must diverge — document that in a plan revision.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Include NDCG now | Graded labels absent; redundant with simpler metrics for v1 |
| Chunk-level precision only | Misaligned with document-scoped synthetic policies in PROJECT.md |
| Score-threshold metrics | Scores are incomparable across retriever types (ADR-023, ADR-026) |
| Mean average precision (MAP) | Requires multi-relevant qrels; out of v1 schema |

---

### ADR-050 — Retriever Protocol as Evaluation Target

**Status:** Proposed

#### Context

Plan 08 introduced `Retriever` as the composable retrieval contract (ADR-022). Plan 13 must evaluate dense, sparse, fusion, and rerank strategies without importing their concrete classes. The evaluation runner must remain stable as new orchestrators appear.

#### Decision

* `EvaluationRunner.run(...)` accepts **`retriever: Retriever`** (structural protocol from `retrieval.protocol`).
* The runner calls **`retriever.retrieve(SearchQuery(text=case.question, top_k=settings.eval_top_k))`** for each case.
* The runner does **not** call `VectorStore`, embedding providers, fusion math, or rerankers directly.
* **`retriever_label: str`** is a caller-supplied report field (e.g. `"dense"`, `"fusion+stub_rerank"`). The protocol has no name property; labels are assigned at wiring time.
* Evaluation code imports **`Retriever` from `knowledge_assistant.retrieval.protocol` only** — not from `retrieval/__init__.py` re-exports, not from `dense.py`, `fusion.py`, or `rerank.py`.
* Retriever exceptions propagate unless `EvaluationSettings` explicitly documents fail-fast behavior (default: **fail-fast** — abort report on first retriever error).

#### Consequences

* Unit tests use `FakeRetriever` without storage.
* Integration tests construct real retriever stacks in `conftest.py` while keeping `evaluation/` modules import-clean.
* Lecture demo runs **`EvaluationRunner`** four times (dense, sparse, fusion, rerank) and assembles a **`ComparisonReport`** from the four `EvaluationReport` instances.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Evaluate `VectorStore.search_*` directly | Bypasses retrieval orchestration under test |
| Hard-code four concrete retriever classes in runner | Breaks composability; couples evaluation to Plans 06–09 internals |
| Callable `(SearchQuery) -> RetrievalResult` instead of protocol | Less consistent with ADR-022 and static checking |
| Swallow retriever errors and score as miss | Hides infrastructure failures; fail-fast is clearer for CI |

---

## Design Evaluations

This section records Plan 13 answers to explicit design questions. These are **decided** for this draft; implementation must not reopen them without a plan revision.

### 1. Document-level vs chunk-level expectations

| Approach | Assessment |
| -------- | ---------- |
| **A — Document-level labels only (v1)** | **Selected.** Matches policy-document retrieval use case; resilient to chunk boundary changes; simpler curator workflow. |
| B — Chunk-level `expected_chunk_id` required | Higher maintenance; reindex/chunking config changes invalidate labels; defer until benchmark maturity. |

**Matching rule (v1):** a case is a hit at rank `r` when the normalized `SearchResult.source.document_path` at rank `r` equals the normalized registry path for `case.expected_document_key`.

**Future extension:** add optional `expected_chunk_ids: tuple[str, ...]` in a later plan revision without breaking v1 JSON (unknown fields ignored by v1 loader).

---

### 2. Benchmark labeling strategy

Plan 13 must choose how evaluation cases reference ground-truth documents. Labels must remain stable across retrieval strategy comparisons and should not break when indexing internals evolve.

| Option | Description | Pros | Cons |
| ------ | ----------- | ---- | ---- |
| **A — `expected_document_id` (`DocumentId` / UUID5)** | Store ADR-008 UUID strings in each case | Direct match to `chunk.metadata.document_id`; no path normalization | **Tight coupling to indexing ID generation**; path normalization changes invalidate labels; opaque in JSON; curators must precompute UUIDs offline |
| B — `expected_document_path` only | Store canonical relative path per case | Human-readable; matches `SourceReference.document_path` at scoring time | Path string duplicated in every case; corpus layout changes require bulk case edits |
| C — **`expected_document_key` + document registry (selected)** | Stable benchmark-local keys; registry maps key → canonical path | **Benchmark owns identifier namespace**; path updates localized to registry; readable keys in cases; matches via `SourceReference.document_path` without indexing imports | Requires registry maintenance; path normalization rules must be documented |
| D — Benchmark-local IDs unrelated to corpus | Opaque benchmark IDs with external mapping file | Maximum decoupling | Extra indirection; harder for lecture/demo traceability |

**Decision:** Option **C — `expected_document_key` + document registry**.

**Rationale:**

* The evaluation layer should measure retrieval against **corpus documents as users cite them** (`SourceReference.document_path` per ADR-031), not against indexing-internal UUID derivation rules.
* ADR-008 `DocumentId` values change when source path normalization or content-derived inputs change — an unsuitable primary label for a long-lived benchmark.
* Centralizing paths in a `documents` registry keeps **50–100** cases maintainable: corpus layout revisions update one registry block plus `corpus_version`, not every case row.
* Matching on normalized paths uses fields already populated at retrieval time — no `indexing` import, no UUID precomputation tooling.

**Path normalization (evaluation-local, stdlib only):**

* Resolve forward slashes;
* strip leading `./` if present;
* case-sensitive comparison (corpus paths are authoritative as authored).

**Why not primary `DocumentId`?** Acceptable only when labels are ephemeral test doubles. For a committed Phase 8 benchmark tied to a synthetic knowledge base, **DocumentId coupling is rejected** — the benchmark must remain valid when indexing implementation details change, as long as indexed paths remain consistent with the registry.

---

### 3. Metric set and NDCG deferral

| Metric | Plan 13 | Rationale |
| ------ | ------- | --------- |
| Hit Rate@K | **In scope** | Standard binary retrieval success metric; intuitive for lectures |
| Recall@K | **In scope** | Reports under single-relevant-doc assumption; prepares for multi-relevant datasets |
| MRR | **In scope** | Rewards early placement of the correct document |
| NDCG@K | **Deferred** | Needs graded qrels; redundant for binary single-doc labels in v1 |

**Note:** With exactly one relevant document per case, Hit Rate@K and Recall@K are numerically identical. Plan 13 reports **both** names so future multi-document benchmarks can extend Recall@K without renaming Hit Rate@K.

---

### 4. Evaluation runner behavior

| Decision | Choice |
| -------- | ------ |
| Input | `Retriever`, `EvaluationDataset`, `EvaluationSettings`, optional `retriever_label` |
| Query construction | `SearchQuery(text=case.question, top_k=settings.eval_top_k)` |
| Per-case output | ranks, hit flags, reciprocal rank, optional matched rank |
| Aggregation | macro averages over all cases |
| Error handling | fail-fast on retriever exceptions (default) |
| Side effects | none — runner does not mutate index or call MCP/LLM |

---

### 5. Single-strategy report model

**`EvaluationCaseResult`** (per case):

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `case_id` | `str` | Benchmark case identifier |
| `question` | `str` | Echo for report readability |
| `expected_document_key` | `str` | Ground-truth registry key |
| `expected_document_path` | `str` | Resolved normalized path (from registry) |
| `hit_at_k` | `dict[int, bool]` | Hit flags per configured K |
| `reciprocal_rank` | `float` | MRR contribution |
| `first_hit_rank` | `int \| None` | 1-based rank if hit within `eval_top_k` |
| `retrieved_document_paths` | `tuple[str, ...]` | Ordered normalized paths in top results (debugging) |

**`EvaluationReport`** (one retriever strategy):

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `retriever_label` | `str` | Caller-supplied strategy name (e.g. `"dense"`, `"sparse"`, `"fusion"`, `"rerank"`) |
| `dataset_id` | `str` | Benchmark identifier |
| `eval_top_k` | `int` | Query cutoff used |
| `metrics_k` | `tuple[int, ...]` | K values reported |
| `case_count` | `int` | Number of evaluated cases |
| `hit_rate_at_k` | `dict[int, float]` | Macro Hit Rate@K |
| `recall_at_k` | `dict[int, float]` | Macro Recall@K |
| `mrr` | `float` | Mean reciprocal rank |
| `cases` | `tuple[EvaluationCaseResult, ...]` | Full breakdown for tests and diffing |

**Formatting:** `format_evaluation_report(report: EvaluationReport) -> str` — stable, column-aligned plain text for one strategy.

---

### 6. Multi-strategy comparison (Phase 8 primary use case)

Phase 8 exists to **compare retrieval strategies** on equal footing. Comparing dense, sparse, fusion, and rerank is not an optional downstream concern — it is a **first-class Plan 13 deliverable**.

**Typical workflow:**

```text
dataset = load_evaluation_dataset("data/evaluation/retrieval_benchmark_v1.json")
runner = EvaluationRunner(settings)

reports = (
    runner.run(dense_retriever, dataset, retriever_label="dense"),
    runner.run(sparse_retriever, dataset, retriever_label="sparse"),
    runner.run(fusion_retriever, dataset, retriever_label="fusion"),
    runner.run(rerank_retriever, dataset, retriever_label="rerank"),
)

comparison = compare_evaluation_reports(reports)
print(format_comparison_report(comparison))
```

**`ComparisonReport`** (lightweight — no separate runner class):

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `dataset_id` | `str` | Shared benchmark identifier (must match across reports) |
| `eval_top_k` | `int` | Shared eval top_k (must match) |
| `metrics_k` | `tuple[int, ...]` | Shared K values (must match) |
| `strategies` | `tuple[str, ...]` | Ordered `retriever_label` values |
| `hit_rate_at_k` | `dict[int, tuple[float, ...]]` | For each K, macro Hit Rate@K per strategy (same order as `strategies`) |
| `recall_at_k` | `dict[int, tuple[float, ...]]` | For each K, macro Recall@K per strategy |
| `mrr` | `tuple[float, ...]` | MRR per strategy |
| `reports` | `tuple[EvaluationReport, ...]` | Underlying single-strategy reports for drill-down |

**`compare_evaluation_reports(reports: tuple[EvaluationReport, ...]) -> ComparisonReport`:**

* Requires at least two reports.
* Validates all reports share the same `dataset_id`, `eval_top_k`, `metrics_k`, and `case_count`.
* Raises `EvaluationError` on mismatch (fail-fast).
* Does **not** re-run retrieval — pure assembly over existing reports.

**`format_comparison_report(comparison: ComparisonReport) -> str`:**

* Plain-text table: rows = metrics (`Hit@1`, `Hit@3`, `Hit@5`, `Recall@*`, `MRR`); columns = strategy labels.
* Stable column order follows input report order.
* Suitable for lecture demo output and test assertions.

**Design constraint:** no `ComparisonRunner` orchestrating retriever wiring — retriever construction stays in CLI/demo/test wiring; comparison is a pure report transform.

---

### 7. Retrieval benchmark creation, ownership, and scale

| Question | Decision |
| -------- | -------- |
| **Ownership** | Evaluation layer owns benchmark JSON under `data/evaluation/`; corpus *files* may arrive in Plan 14, but **questions and qrels belong to evaluation** |
| **Corpus target** | Synthetic corporate knowledge base per `PROJECT.md` (policies, onboarding, travel, security, equipment, expense, incident response, etc.) |
| **How created?** | **Manual curation** — subject-matter-style questions authored against planned corpus documents |
| **Automated generation?** | **No** in Plan 13 |
| **Stored in repository?** | **Yes** — `data/evaluation/retrieval_benchmark_v1.json` (name may adjust at implementation) |
| **Relationship to Plan 14** | Plan 14 commits corpus *content*; Plan 13 benchmark references corpus paths via registry. Plans are coordinated but **benchmark ≠ test fixtures ≠ Plan 14 implementation artifact** |
| **Relationship to tests** | Unit tests use **minimal** JSON in `tests/unit/evaluation/fixtures/` (2–5 cases) for loader/metric tests only. CI does **not** require executing the full 50–100 case benchmark on every test run unless explicitly added as a slow/integration job |
| **Scale guidance** | Target **50–100** evaluation questions for stable macro metrics and meaningful dense/sparse/fusion/rerank comparison. Fewer than ~30 cases produces high-variance Hit@K estimates unsuitable for lecture comparison |

**CI strategy:**

* **Fast path (required):** unit tests with tiny fixtures + `FakeRetriever` — no Qdrant, no full benchmark, no dependency on `tests/unit/indexing/fixtures/`.
* **Optional slow path:** integration job indexes synthetic KB corpus paths referenced by the benchmark registry, runs four retriever strategies, asserts `ComparisonReport` builds and metrics are finite — assembly in test conftest only.

---

### 8. Pydantic vs dataclass for evaluation models

**Decision:** frozen `@dataclass(frozen=True, slots=True)` models in `evaluation/`, consistent with ADR-001 domain style. Evaluation types are evaluation-local — they do not live in `core` and do not use Pydantic.

---

### 9. Package naming

**Decision:** `knowledge_assistant.evaluation` — parallel to `retrieval`, `indexing`, `storage`. Do not nest under `retrieval/eval/` or create `utils/`.

---

## Module Layout

### Evaluation (new package)

```text
src/knowledge_assistant/evaluation/
    __init__.py           # minimal public exports
    dataset.py            # EvaluationCase, DocumentRegistry, EvaluationDataset, JSON loader, path normalization
    settings.py           # EvaluationSettings
    metrics.py            # hit_rate_at_k, recall_at_k, mrr helpers (pure functions)
    runner.py             # EvaluationRunner
    report.py             # EvaluationCaseResult, EvaluationReport, ComparisonReport,
                          # compare_evaluation_reports, format_evaluation_report, format_comparison_report
    exceptions.py         # EvaluationError hierarchy (optional, minimal)
```

Do not create `evaluation/utils/` or `evaluation/cli.py` in Plan 13.

### Benchmark data (new)

```text
data/evaluation/
    retrieval_benchmark_v1.json    # committed retrieval benchmark (50–100 cases target)
```

Benchmark JSON includes `documents` registry and `cases`. Document provenance, corpus version, and curation notes belong in the JSON `description` and `corpus_version` fields — not in `tests/` fixtures.

### Unchanged packages

```text
core/           # UNCHANGED
retrieval/      # UNCHANGED (EvaluationRunner uses protocol only)
storage/        # UNCHANGED
indexing/       # UNCHANGED
mcp_server/     # UNCHANGED
llm/            # UNCHANGED
agent/          # UNCHANGED
cli/            # UNCHANGED (no CLI wiring in Plan 13)
```

---

## API Design

### EvaluationSettings

**Module:** `evaluation/settings.py`

```python
@dataclass(frozen=True, slots=True)
class EvaluationSettings:
    eval_top_k: int = 5
    metrics_k: tuple[int, ...] = (1, 3, 5)
```

Validation in `__post_init__`:

* `eval_top_k >= 1`
* every `k` in `metrics_k` satisfies `1 <= k <= eval_top_k`
* `metrics_k` non-empty

---

### Metric functions

**Module:** `evaluation/metrics.py`

Pure functions operating on ordered `tuple[SearchResult, ...]` and a normalized expected document path:

```python
def normalize_document_path(path: str) -> str: ...

def hit_at_k(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
    k: int,
) -> bool: ...

def recall_at_k(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
    k: int,
) -> float: ...  # 0.0 or 1.0 for v1 single-relevant-doc cases

def reciprocal_rank(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
) -> float: ...
```

**Path extraction helper** (evaluation-local):

```python
def document_path_from_result(result: SearchResult) -> str:
    return normalize_document_path(result.source.document_path)
```

Match using normalized `SourceReference.document_path` — not chunk text similarity, not score thresholds, not ADR-008 `DocumentId`.

---

### EvaluationRunner

**Module:** `evaluation/runner.py`

```python
@dataclass(frozen=True, slots=True)
class EvaluationRunner:
    settings: EvaluationSettings

    def run(
        self,
        retriever: Retriever,
        dataset: EvaluationDataset,
        *,
        retriever_label: str,
    ) -> EvaluationReport: ...
```

Behavior:

1. Validate `retriever_label` non-empty.
2. For each case in dataset order:
   * resolve `expected_document_path` from registry via `case.expected_document_key`;
   * call `retriever.retrieve(SearchQuery(text=case.question, top_k=self.settings.eval_top_k))`;
   * compute per-K hit flags, reciprocal rank, and first hit rank using normalized path matching;
   * append `EvaluationCaseResult`.
3. Aggregate macro Hit Rate@K, Recall@K, and MRR.
4. Return `EvaluationReport`.

---

### Comparison assembly

**Module:** `evaluation/report.py`

```python
def compare_evaluation_reports(
    reports: tuple[EvaluationReport, ...],
) -> ComparisonReport: ...

def format_comparison_report(comparison: ComparisonReport) -> str: ...
```

Validates compatible reports, extracts per-strategy metric vectors, preserves underlying reports for drill-down. Pure function — no I/O, no retriever calls.

---

### Dataset loader

**Module:** `evaluation/dataset.py`

```python
def load_evaluation_dataset(path: Path) -> EvaluationDataset: ...
```

* Uses stdlib `json.load`.
* Builds `DocumentRegistry` and validates key references.
* Raises `EvaluationDatasetError` (subclass of `EvaluationError`) on schema/validation failures.

---

### Public exports (`evaluation/__init__.py`)

Keep minimal:

```python
__all__ = [
    "EvaluationCase",
    "EvaluationDataset",
    "DocumentRegistry",
    "EvaluationSettings",
    "EvaluationRunner",
    "EvaluationReport",
    "EvaluationCaseResult",
    "ComparisonReport",
    "compare_evaluation_reports",
    "load_evaluation_dataset",
    "format_evaluation_report",
    "format_comparison_report",
]
```

Metric functions may remain module-level exports for unit tests without re-export from `__init__.py`.

---

## Dependency Rules

### Allowed in evaluation production code

| Dependency | Usage |
| ---------- | ----- |
| Python standard library | `json`, `pathlib`, `dataclasses`, `typing` |
| `knowledge_assistant.core` | `SearchQuery`, `SearchResult`, `RetrievalResult`, `SourceReference` (via `SearchResult.source`) |
| `knowledge_assistant.retrieval.protocol` | `Retriever` protocol only |

### Forbidden in evaluation production code

| Dependency | Reason |
| ---------- | ------ |
| `knowledge_assistant.storage`, `qdrant_client` | Evaluation must not depend on storage internals |
| `knowledge_assistant.indexing` | Benchmark resolves paths without indexing; no ingestion in evaluation layer |
| `knowledge_assistant.retrieval.dense`, `.sparse`, `.fusion`, `.rerank` | Concrete strategies wired outside evaluation |
| `knowledge_assistant.mcp_server`, `agent`, `llm` | Out of retrieval-quality scope |
| `langgraph`, `llama_index`, `pydantic` | Wrong layer / ADR-001 boundary |
| Model runtimes (`torch`, `transformers`, etc.) | Not required for metric computation |

### Who may import `evaluation/`

| Consumer | Allowed |
| -------- | ------- |
| `cli` | yes (future Plan 15) |
| tests | yes |
| `retrieval`, `storage`, `indexing`, `mcp_server`, `agent`, `llm` | **no** (retrieval must not depend on evaluation) |

---

## Testing Strategy

### Unit tests — `tests/unit/evaluation/`

| Module | Focus |
| ------ | ----- |
| `test_metrics.py` | hit@K, recall@K, MRR, edge cases (empty results, hit at rank 1, miss) |
| `test_dataset.py` | JSON loader validation, duplicate case_id rejection, malformed files |
| `test_runner.py` | `EvaluationRunner` with `FakeRetriever`; aggregated metrics match hand computation |
| `test_report.py` | `EvaluationReport` and `ComparisonReport` construction; `format_evaluation_report` and `format_comparison_report` stable output |
| `test_comparison.py` | `compare_evaluation_reports` validation, mismatch errors, metric table assembly |
| `test_evaluation_imports.py` | forbidden imports in `evaluation/*.py` production modules |

### FakeRetriever pattern

Reuse the integration-retrieval pattern: a test-local `FakeRetriever` implementing `Retriever` that returns scripted `RetrievalResult` per query text or call index. Lives in `tests/integration/evaluation/conftest.py` or shared test helper — **not** in `src/`.

### Mandatory metric scenarios

| Scenario | Expected behavior |
| -------- | ----------------- |
| Expected document at rank 1 | Hit@K true for all K ≥ 1; MRR = 1.0 |
| Expected document at rank 3 | Hit@1 false, Hit@3 true; MRR = 1/3 |
| Expected document absent | all Hit@K false; MRR = 0.0 |
| Empty results | all Hit@K false; MRR = 0.0 |
| Multiple chunks same document in top K | still one hit; first matching rank drives MRR |

### Integration tests — `tests/integration/evaluation/` (optional)

| Module | Focus |
| ------ | ----- |
| `test_evaluation_strategy_comparison.py` | Index synthetic KB corpus paths referenced by benchmark registry; wire dense/sparse/fusion/rerank retrievers; run runner four times; build and format `ComparisonReport` |

Assembly and corpus indexing live in test `conftest.py` only. Tests must not import or depend on `tests/unit/indexing/fixtures/` as the benchmark source of truth.

**Not required for Plan 13 acceptance:** live Qdrant Docker, real BGE models, MCP, agent, LLM.

### Determinism rules

* Metric unit tests use fixed `SearchResult` fixtures with known `source.document_path` values — no randomness.
* Dataset loader tests use **minimal** JSON snippets in `tests/unit/evaluation/fixtures/` (2–5 cases) — **not** the production benchmark file.
* Comparison tests assemble 2–4 synthetic `EvaluationReport` instances with hand-computed metrics.
* Report formatter tests assert full expected text blocks for small single-strategy and comparison tables.

### Import boundary test pattern

Mirror `tests/unit/retrieval/test_retrieval_imports.py`:

* scan `evaluation/*.py`;
* forbid `storage`, `qdrant_client`, `indexing`, `mcp_server`, `agent`, `llm`, `langgraph`, `llama_index`, `retrieval.dense`, `retrieval.fusion`, etc.

---

## Runtime Dependencies

Plan 13 adds **no new runtime dependencies** to `pyproject.toml`. JSON loading and metrics use the Python standard library only.

---

## Documentation Updates (on implementation)

* `docs/DECISIONS.md` — accept ADR-047 through ADR-050;
* `docs/ARCHITECTURE.md` — new **Evaluation Layer** section (pipeline diagram, ownership, dependency rules);
* `docs/PROGRESS.md` — Plan 13 completion entry;
* `README.md` — brief note that retrieval evaluation exists (optional);
* Do **not** modify `docs/plans/backlog/ROADMAP.md` during this draft.

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-047 through ADR-050 in `docs/DECISIONS.md`.
2. **Create `evaluation/exceptions.py`** — minimal `EvaluationError`, `EvaluationDatasetError`.
3. **Create `evaluation/dataset.py`** — models + JSON loader.
4. **Create `evaluation/settings.py`** — `EvaluationSettings` with validation.
5. **Create `evaluation/metrics.py`** — pure metric functions.
6. **Create `evaluation/report.py`** — single-strategy and comparison report models + formatters + `compare_evaluation_reports`.
7. **Create `evaluation/runner.py`** — `EvaluationRunner`.
8. **Create `evaluation/__init__.py`** — public exports.
9. **Add `data/evaluation/retrieval_benchmark_v1.json`** — document registry + curated cases targeting synthetic KB corpus (**50–100** question target; may land incrementally).
10. **Add unit tests** — metrics, dataset, runner, report, comparison, import boundaries.
11. **Optional integration test** — four-strategy comparison against indexed synthetic KB corpus in test conftest only.
12. **Update `docs/ARCHITECTURE.md`** — evaluation layer section (include comparison workflow).
13. **Run validation suite** — all four quality commands; fix until pass.
14. **Update progress** — record completion in `docs/PROGRESS.md`.
15. **Verify non-scope compliance** — no LLM/agent/MCP evaluation; no retrieval algorithm changes; benchmark independent of test fixtures.

---

## Acceptance Criteria

### Evaluation models and dataset

- [x] `EvaluationCase`, `DocumentRegistry`, `EvaluationDataset`, `EvaluationSettings`, `EvaluationCaseResult`, `EvaluationReport`, and `ComparisonReport` implemented as frozen dataclasses
- [x] `load_evaluation_dataset` loads committed JSON from `data/evaluation/`
- [x] Dataset validation rejects empty cases, duplicate `case_id`, unknown `expected_document_key`, and invalid `metrics_k` configuration
- [x] v1 schema uses document-level `expected_document_key` with `documents` registry (not primary `DocumentId` labels)
- [x] Benchmark targets synthetic knowledge-base corpus; **not** derived from `tests/` fixtures

### Metrics

- [x] Hit Rate@K, Recall@K, and MRR implemented as pure functions
- [x] Metrics match via normalized `SearchResult.source.document_path` against registry-resolved expected path
- [x] NDCG not implemented (deferred per ADR-049)

### EvaluationRunner

- [x] Accepts any structurally compatible `Retriever`
- [x] Uses `SearchQuery(text=case.question, top_k=settings.eval_top_k)` for each case
- [x] Returns `EvaluationReport` with macro aggregates and per-case breakdown
- [x] Supports caller-supplied `retriever_label`
- [x] Fail-fast on retriever exceptions (default)

### Report, comparison, and formatting

- [x] `format_evaluation_report` produces stable plain-text suitable for test assertions
- [x] `compare_evaluation_reports` validates compatible reports and builds `ComparisonReport`
- [x] `format_comparison_report` produces side-by-side strategy table (dense / sparse / fusion / rerank labels)
- [x] Single-strategy report includes `hit_rate_at_k`, `recall_at_k`, and `mrr`

### Boundaries

- [x] Production `evaluation/` code imports only `core`, `retrieval.protocol.Retriever`, and stdlib
- [x] No imports of `storage`, `indexing`, `mcp_server`, `llm`, `agent`, `langgraph`, or `llama_index` in evaluation production modules
- [x] Import-boundary tests pass
- [x] `retrieval/` production code does not import `evaluation/`

### Tests and validation

- [x] Unit tests cover metric edge cases, runner aggregation, and comparison assembly with `FakeRetriever`
- [x] Dataset loader tests use minimal fixtures under `tests/unit/evaluation/fixtures/` only
- [x] `uv run ruff format --check .`, `ruff check .`, `basedpyright`, `pytest` pass

### Documentation

- [x] ADR-047 through ADR-050 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents evaluation layer
- [x] `docs/PROGRESS.md` updated on completion

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into LLM or agent evaluation | Explicit non-scope; ADR-047 ownership boundary |
| Evaluation imports concrete retrievers | ADR-050; import-boundary tests |
| Benchmark coupled to test fixtures | ADR-048; separate `data/evaluation/` from `tests/`; Design Evaluation 7 |
| Registry path mismatch after corpus changes | `corpus_version` field; coordinated Plan 14 path layout; fail-fast loader validation |
| Path normalization ambiguity | Document normalization rules; unit tests for edge paths |
| Hit Rate@K and Recall@K redundancy in v1 | Document identical values under single-relevant-doc assumption; keep both names for future qrels |
| Chunking changes invalidate future chunk labels | v1 is document-level only per ADR-048 |
| Sparse placeholder corpus yields poor sparse metrics | Expected for stub sparse vectors (ADR-020); comparison still shows relative strategy differences |
| Benchmark under-populated (<50 cases) | Design target 50–100 documented; incremental curation acceptable before Plan 15 demo |
| Plan 14 corpus not ready at Plan 13 start | Benchmark registry declares planned paths; framework + comparison ship first; questions added as corpus lands |

---

## Follow-Up Work (Not Plan 13)

| Item | Target |
| ---- | ------ |
| Plan 14 — Demo Dataset | Full synthetic corporate knowledge base |
| Plan 15 — End-to-End Demo | CLI commands printing `ComparisonReport` tables for lecture demo |
| NDCG / MAP / graded metrics | Future evaluation plan after multi-level or multi-document qrels |
| Chunk-level expected labels | Future dataset schema revision |
| LLM-as-a-Judge answer evaluation | Explicit non-goal per PROJECT.md |
| Agent / MCP / tool-calling evaluation | Future plans outside retrieval-quality scope |
| Latency and cost metrics | Future observability plan |
| Automated benchmark generation | Backlog only; manual curation remains default |
| Real BGE runtime retriever comparison | Depends on backlog BGE embedding/reranker plans |
| Query rewriting impact evaluation | Proposed Plan 12b |

---

## Open Questions

1. **Exact benchmark size at Plan 13 merge:** design target **50–100** cases — confirm whether full population is required for plan completion or incremental curation through Plan 14/15 is acceptable.
2. **Synthetic KB directory layout:** confirm canonical root path prefix for registry entries (e.g. `knowledge/policies/...`) relative to repository root — coordinate with Plan 14.
3. **Fail-fast vs continue-on-error:** draft default is fail-fast — confirm during activation.
4. **Optional full-benchmark CI job:** confirm whether running all 50–100 cases against four retrievers belongs in default CI or a marked slow integration job.
5. **Path normalization edge cases:** confirm whether corpus paths are always POSIX-style forward-slash in registry (recommended).

---

## Readiness Assessment

**Ready for review?** **Yes** (revised per review feedback).

The draft defines evaluation ownership, first-class benchmark under `data/evaluation/`, benchmark-local labeling via document keys, metric selection, retriever abstraction usage, **multi-strategy comparison reporting**, module layout, dependency rules, tests, and acceptance criteria aligned with Plans 03 and 06–09 and `docs/ARCHITECTURE.md`. Before activation:

1. Review proposed ADRs (especially document-key labeling and NDCG deferral).
2. Confirm synthetic KB path layout with Plan 14 scope.
3. Confirm benchmark curation timeline for **50–100** cases vs framework-first delivery.

No architectural blockers identified relative to completed plans.

---

## Checklist

- [x] Plan reviewed and activated in `docs/plans/active/`
- [x] ADR-047 through ADR-050 accepted in `docs/DECISIONS.md`
- [x] `evaluation/` package implemented per module layout
- [x] `ComparisonReport` and `compare_evaluation_reports` implemented
- [x] Committed benchmark JSON under `data/evaluation/` (synthetic KB target, 70 cases)
- [x] Unit tests complete; optional integration test deferred
- [x] `docs/ARCHITECTURE.md` Evaluation Layer section added
- [x] `docs/PROGRESS.md` updated
- [x] Full validation suite passes
- [x] Plan moved to `docs/plans/completed/` on completion
