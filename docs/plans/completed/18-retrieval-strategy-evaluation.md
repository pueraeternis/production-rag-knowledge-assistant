# Plan 18 — Retrieval Strategy Evaluation

**Status:** Completed (amended 2026-06-22 — optional JSON export authorized)

**Completed:** 2026-06-22

**Amendment (2026-06-22):** Optional `--output PATH` JSON report export added to plan scope. Stdout remains the primary interface. Export is CLI-owned, operator-driven, and local-only. No changes to evaluation ownership, bootstrap ownership, strategy selection, `EvaluationRunner` responsibilities, `ComparisonReport` assembly, or default CLI behavior when `--output` is omitted.

**Roadmap:** Phase 13 — End-to-End Evaluation

**Depends on:**

* [Plan 13 — Evaluation Framework](../completed/13-evaluation-framework.md)
* [Plan 14 — Synthetic Corporate Knowledge Base](../completed/14-synthetic-knowledge-base.md)
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md)
* [Plan 16 — Real Dense Embeddings Integration](../completed/16-real-dense-embeddings-integration.md)
* [Plan 17 — Real Reranker Integration](../completed/17-real-reranker.md)

**Plan principle:** One plan introduces one architectural capability. Plan 18 introduces **retrieval evaluation execution and CLI exposure** only — wiring the existing evaluation framework to bootstrap-assembled retrievers and the canonical benchmark. It does **not** introduce retrieval algorithms, agent/MCP changes, chat UX, new metrics, or evaluation framework redesign.

---

## Authorization

**Active.** ADR-067 through ADR-070 recorded in `docs/DECISIONS.md`.

---

## Amendment — Optional Report Persistence (2026-06-22)

This amendment authorizes an **optional** JSON export capability. It does **not** change Plan 18 primary scope, architecture, or core acceptance criteria.

### What is unchanged

| Concern | Owner | Change |
| ------- | ----- | ------ |
| Evaluation report generation | `knowledge_assistant.evaluation` | none |
| Bootstrap strategy assembly | `knowledge_assistant.bootstrap` | none |
| `EvaluationRunner` responsibilities | Plan 13 | none |
| `ComparisonReport` assembly | Plan 13 `compare_evaluation_reports` | none |
| Default stdout rendering | CLI formatters | none |
| CLI default behavior (no `--output`) | CLI | none |

### What is added

| Command | Flag | Output |
| ------- | ---- | ------ |
| `rag evaluate run` | `--output PATH` | `PATH/evaluation_<strategy>.json` |
| `rag evaluate compare` | `--output PATH` | `PATH/evaluation_{dense,sparse,fusion,rerank}.json` + `PATH/comparison.json` |

### Serialization rules

* **JSON only** — no HTML, CSV, or database persistence.
* **Reuse existing dataclasses** — serialize `EvaluationReport` and `ComparisonReport` as-is; no new report models.
* **CLI ownership** — `cli/evaluate.py` may serialize reports (e.g. `dataclasses.asdict` + `json.dump`); do not move export logic into `evaluation/` unless serialization helpers already exist there.
* **Filesystem optional** — commands work identically when `--output` is omitted.
* **Operator-driven** — no automatic history, report registry, experiment tracking, MLFlow, or Weights & Biases.

---

## Objective

Expose end-to-end retrieval strategy evaluation on the committed benchmark by connecting:

```text
BootstrapSettings.from_env()
        ↓
build_demo_environment()                    ← Plan 15/16/17 (vector store + providers)
        ↓
build_retriever_for_strategy(env, ...)    ← Plan 18 (strategy selection)
        ↓
load_evaluation_dataset(...)                ← Plan 13 (read-only benchmark)
        ↓
EvaluationRunner.run(retriever, ...)        ← Plan 13 (per strategy)
        ↓
EvaluationReport                            ← one per strategy
        ↓
compare_evaluation_reports(...)             ← Plan 13 (compare command)
        ↓
ComparisonReport
        ↓
CLI stdout (format_evaluation_report / format_comparison_report)
```

After this plan is complete:

* a developer can index the canonical corpus with existing `rag demo load` and run benchmark evaluation through **`rag evaluate run`** and **`rag evaluate compare`**;
* four canonical strategies — **dense**, **sparse**, **fusion**, **rerank** — are selectable and documented with explicit retrieval-stack mappings;
* retriever assembly for evaluation reuses **`knowledge_assistant.bootstrap`** — no duplicated composition logic in CLI or evaluation production modules;
* **`EvaluationReport`** and **`ComparisonReport`** render through existing Plan 13 formatters;
* operators may optionally export the same reports as JSON via `--output PATH` for portfolio/demo reuse (stdout remains primary);
* stub and real model modes inherit bootstrap provider selection (`RAG_EMBEDDING_MODE`, `RAG_RERANKER_MODE`) with documented expectations for meaningful benchmark results;
* default CI remains stub-based; real model benchmark execution stays optional.

**Ownership boundaries (explicit):**

| Concern | Owner |
| ------- | ----- |
| Benchmark dataset, metrics, runner, reports, comparison | Plan 13 — `knowledge_assistant.evaluation` |
| Vector store, indexing pipeline, provider selection, strategy retriever assembly | Plan 15–17 — `knowledge_assistant.bootstrap` |
| Evaluation CLI orchestration, exit codes, stdout rendering, optional JSON export | Plan 18 — `knowledge_assistant.cli` |
| Corpus indexing (`rag demo load`) | Plan 15 — prerequisite, not reimplemented |
| Interactive chat (`rag chat`) | Plan 19 |

Plan 18 must not implement, stub, or partially deliver chat, agent loops, or MCP evaluation.

---

## Required User Workflow

The lecture and README evaluation path after Plan 18:

```text
# 1. Generate canonical corpus (Plan 14)
python3 tools/knowledge_generator/generator.py

# 2. Start Qdrant (operator responsibility)
# default: http://localhost:6333

# 3. Index corpus (Plan 15)
rag demo info
rag demo load

# 4. (Recommended for meaningful results) enable real models and reindex
export RAG_EMBEDDING_MODE=real
export RAG_RERANKER_MODE=real
rag demo load --rebuild --approve

# 5. Run single-strategy evaluation (Plan 18)
rag evaluate run --strategy dense
rag evaluate run --strategy sparse
rag evaluate run --strategy fusion
rag evaluate run --strategy rerank

# 6. Run four-strategy comparison (Plan 18)
rag evaluate compare

# 7. (Optional) Export JSON reports for portfolio/demo reuse
rag evaluate run --strategy rerank --output reports/
rag evaluate compare --output reports/
```

Prerequisites assumed by the workflow:

* Python 3.12+ and `uv sync` completed;
* Qdrant reachable at configured URL;
* Plan 14 corpus generated locally under `knowledge/` (gitignored);
* demo collection populated (`rag demo load`) before any `rag evaluate` command;
* meaningful absolute benchmark quality requires real embeddings and an index built with those embeddings (ADR-058).

Plan 18 does **not** add corpus generation, Docker Compose, automatic indexing inside evaluate commands, or LLM setup.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/bootstrap/` | Strategy retriever assembly; shared retrieval stack extraction |
| `src/knowledge_assistant/cli/` | `evaluate` subcommands (`run`, `compare`) |
| `tests/unit/bootstrap/` | Strategy retriever wiring tests |
| `tests/unit/cli/` | Evaluate parsing, preconditions, import boundaries |
| `tests/integration/evaluation/` | End-to-end evaluate CLI against indexed fixture corpus |
| `docs/ARCHITECTURE.md` | Evaluation execution workflow, CLI evaluate commands, bootstrap strategy assembly |
| `docs/DECISIONS.md` | ADR-067 through ADR-070 |
| `docs/PROGRESS.md` | Plan 18 completion entry |
| `docs/plans/backlog/ROADMAP.md` | Phase 13 status update on completion |
| `README.md` | Evaluation quickstart and real-model guidance |

### In Scope

* `RetrievalStrategy` type and canonical strategy constants (`dense`, `sparse`, `fusion`, `rerank`);
* `build_retriever_for_strategy(environment, strategy)` in bootstrap;
* internal retrieval-stack builder shared by `build_demo_environment()` and strategy selection (no duplicate wiring);
* `rag evaluate run --strategy {dense,sparse,fusion,rerank}` CLI command;
* `rag evaluate compare` CLI command running all four canonical strategies;
* precondition validation: dataset file exists, collection exists, `collection_chunk_count > 0`;
* stdout rendering via existing `format_evaluation_report` and `format_comparison_report`;
* optional `--dataset`, `--eval-top-k`, `--metrics-k` CLI overrides for `EvaluationSettings`;
* bootstrap-mode banner in CLI output (embedding mode, reranker mode, pipeline label);
* unit tests for strategy assembly and CLI behavior;
* integration tests using a minimal indexed fixture corpus and test-local benchmark JSON;
* optional marked integration test for full `retrieval_benchmark_v1.json` with real models (skipped by default);
* optional JSON export of `EvaluationReport` and `ComparisonReport` when `--output PATH` is supplied (stdout remains primary; export is operator-driven and local-only);
* ADR-067 through ADR-070;
* documentation updates listed above.

### Non-Scope

Plan 18 does **not** authorize:

* changes to `EvaluationRunner`, metric functions, dataset schema, or `ComparisonReport` assembly logic beyond using existing APIs;
* new retrieval metrics (NDCG, MAP, latency, etc.);
* new retrieval algorithms or changes to `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `RerankRetriever`, fusion math, or reranker contracts;
* changes to `data/evaluation/retrieval_benchmark_v1.json` content or benchmark curation;
* automatic indexing or rebuild inside `rag evaluate` (indexing remains `rag demo load`);
* `rag chat`, LangGraph agent changes, MCP handler/transport changes;
* query rewriting, memory systems, or conversational evaluation;
* LLM answer evaluation, LLM-as-a-Judge, or hallucination detection;
* observability platforms, dashboards, web UI, or report persistence databases;
* automatic history storage, report registries, experiment tracking, MLFlow, Weights & Biases, or benchmark dashboards (optional `--output` JSON export is in scope; broader persistence systems are not);
* Docker Compose or infrastructure orchestration;
* real model downloads or GPU requirements in default CI;
* sparse BGE-M3 vector generation (remains stub sparse per ADR-010/ADR-020);
* evaluation production modules importing bootstrap, storage, indexing, or concrete retrievers.

---

## Architectural Decisions (Proposed ADRs)

Record in `docs/DECISIONS.md` during implementation.

### ADR-067 — Retrieval Evaluation Execution Ownership

**Status:** Accepted

#### Context

Plan 13 owns retrieval-quality measurement (`EvaluationRunner`, metrics, reports) but deliberately excludes retriever construction and CLI exposure (ADR-047, ADR-050). Plan 15 established `knowledge_assistant.bootstrap` as the demo composition root (ADR-051). Without explicit execution ownership, evaluate workflow logic could land in `evaluation/` (violating import boundaries), `mcp_server`, or ad hoc scripts — duplicating wiring and blurring component responsibilities.

#### Decision

* **Evaluation execution** is the offline workflow that loads a benchmark, selects a retriever, runs `EvaluationRunner`, and renders reports. It is **not** a new package and does **not** move into `evaluation/` production modules.
* **CLI (`knowledge_assistant.cli.evaluate`)** owns evaluation **command orchestration**:
  * argument parsing and validation;
  * prerequisite checks (dataset path, indexed collection);
  * calling bootstrap strategy assembly;
  * invoking Plan 13 evaluation APIs;
  * stdout rendering and exit codes;
  * optional JSON export of reports when `--output PATH` is supplied (CLI-owned serialization; no changes to evaluation report models).
* **Bootstrap (`knowledge_assistant.bootstrap`)** owns **strategy retriever assembly** from a shared `DemoEnvironment` / retrieval stack — the only production location that constructs concrete `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, and `RerankRetriever` instances for evaluation.
* **`knowledge_assistant.evaluation`** remains unchanged in responsibility: dataset, runner, metrics, reports, comparison — no bootstrap/storage/indexing imports.
* MCP, agent, and LLM layers do not participate in retrieval evaluation execution.

#### Consequences

* Plan 13 import-boundary tests remain valid.
* `rag evaluate` extends CLI ownership (ADR-052) without growing MCP or agent scope.
* Tests can orchestrate the same workflow by calling bootstrap + evaluation APIs directly (integration tests) or CLI `main([...])` (CLI integration tests).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `evaluation/execution.py` importing bootstrap | Violates Plan 13 evaluation import rules; couples measurement to wiring |
| MCP tool `evaluate_retrieval` | Offline batch analysis is operator workflow, not agent knowledge access |
| Evaluation runner owns retriever factory | Breaks ADR-050; forces evaluation → retrieval concrete imports |
| Standalone `scripts/evaluate.py` outside `cli/` | Hides capability from `rag` entrypoint; duplicates CLI patterns |

---

### ADR-068 — Bootstrap-Owned Strategy Retriever Assembly

**Status:** Accepted

#### Context

Plan 15 wires one canonical `RerankRetriever` stack in `build_demo_environment()`. Plan 18 must evaluate four distinct strategies against the same indexed corpus and provider configuration. Duplicating retriever construction in CLI modules violates ADR-051 and ADR-032 assembly rules.

#### Decision

* Add bootstrap-level **strategy retriever assembly** — e.g. `build_retriever_for_strategy(environment, strategy) -> Retriever`.
* Extract a shared internal retrieval stack builder used by both `build_demo_environment()` and strategy selection so dense/sparse/fusion/rerank instances share:
  * the same `VectorStore`;
  * the same dense query embedding provider (stub or real per `RAG_EMBEDDING_MODE`);
  * the same sparse query embedding provider (`StubSparseQueryEmbeddingProvider` per ADR-020);
  * the same reranker instance (`StubReranker` or `BgeReranker` per `RAG_RERANKER_MODE`).
* Canonical strategy identifiers and stacks:

| `strategy` | `retriever_label` | Retrieval stack evaluated |
| ---------- | ----------------- | ------------------------- |
| `dense` | `"dense"` | `DenseRetriever` only |
| `sparse` | `"sparse"` | `SparseRetriever` only |
| `fusion` | `"fusion"` | `FusionRetriever(dense_retriever, sparse_retriever)` |
| `rerank` | `"rerank"` | `RerankRetriever(base_retriever=fusion_retriever, reranker=...)` |

* `build_demo_environment().retriever` must remain the canonical **`rerank`** stack (unchanged default demo entry point per ADR-053).
* Bootstrap may import the public `knowledge_assistant.retrieval` package API only — same rule as Plan 15/16/17.
* Bootstrap must **not** import `knowledge_assistant.evaluation`.

#### Consequences

* Strategy comparison uses identical infrastructure except the selected orchestrator boundary.
* Plans 16–17 provider toggles automatically apply to all four strategies without evaluation code changes.
* Refactoring `environment.py` is authorized when it eliminates duplicate wiring.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| CLI constructs retrievers directly | Duplicates bootstrap; violates CLI import boundaries |
| Four separate `build_*_environment()` factories | Configuration drift across strategies |
| Evaluation selects strategies by string inside `EvaluationRunner` | Violates ADR-050; couples runner to concrete classes |
| Strategy assembly in tests only | No production path for lecture demo |

---

### ADR-069 — Strategy Comparison Contract

**Status:** Accepted

#### Context

Plan 13 defines `compare_evaluation_reports(...)` validation: shared `dataset_id`, `eval_top_k`, `metrics_k`, and `case_count` across reports (ADR-049, Design Evaluation 6). Plan 18 must define how CLI `rag evaluate compare` produces a valid `ComparisonReport` for the four canonical strategies.

#### Decision

* **`rag evaluate compare`** runs evaluation for all four canonical strategies in fixed order: **dense → sparse → fusion → rerank**.
* Each run uses:
  * the same `EvaluationDataset` instance (or equivalent loaded dataset);
  * the same `EvaluationSettings` (`eval_top_k`, `metrics_k`);
  * the same bootstrap environment / indexed collection state;
  * canonical `retriever_label` values: `"dense"`, `"sparse"`, `"fusion"`, `"rerank"`.
* Comparison assembly calls existing `compare_evaluation_reports(tuple_of_four_reports)` — **no fork** of comparison logic.
* `compare_evaluation_reports` mismatch failures propagate as command failure (fail-fast).
* Single-strategy `rag evaluate run` may be invoked independently for debugging; compare does **not** require prior `run` invocations.
* Comparison requires **identical benchmark inputs** across strategies. Mixing datasets, `eval_top_k`, or `metrics_k` between runs is forbidden; CLI enforces shared settings within one `compare` invocation.
* Benchmark JSON is **read-only** during evaluation; execution must not mutate `data/evaluation/` files.

#### Consequences

* Lecture demo output is reproducible: one command prints a stable four-column comparison table.
* Plan 13 comparison unit tests remain authoritative for validation rules.
* Partial strategy runs are not combined into a comparison report.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Compare cached reports from prior `run` commands | Adds persistence contract and stale-index risk; deferred |
| Arbitrary strategy subset in v1 compare | Complicates lecture narrative; four canonical strategies are the Phase 13 goal |
| Different `eval_top_k` per strategy | Invalidates `compare_evaluation_reports` validation |
| Silent skip when a strategy fails | Hides infrastructure failures; fail-fast is clearer |

---

### ADR-070 — Real-Model Benchmark Expectations

**Status:** Accepted

#### Context

Bootstrap defaults to stub dense embeddings (ADR-060) and stub reranker (ADR-065). Plan 16 requires full reindex after switching to real embeddings (ADR-058). Plan 18 exposes benchmark execution to operators who may run evaluate without real models or without reindexing. Absolute metric values and lecture claims must not be ambiguous.

#### Decision

* **`rag evaluate` uses bootstrap provider modes by default** — no separate evaluation-specific model toggle. Environment variables:
  * `RAG_EMBEDDING_MODE` (`stub` default, `real` opt-in);
  * `RAG_RERANKER_MODE` (`stub` default, `real` opt-in).
* **Stub mode behavior:**
  * commands run successfully against any non-empty indexed collection;
  * metrics are **valid numerically** and strategy **relative ordering** may still differ;
  * absolute Hit@K / MRR values are **not** meaningful for production-quality or lecture claims about BGE-M3 / BGE reranker effectiveness;
  * sparse strategy continues to reflect placeholder sparse vectors (ADR-020) — expect weak sparse-only metrics.
* **Meaningful benchmark mode (operator expectation):**
  * `RAG_EMBEDDING_MODE=real`;
  * corpus indexed with real dense embeddings (`rag demo load` or `rag demo load --rebuild --approve` after mode switch per ADR-058);
  * for rerank strategy quality: `RAG_RERANKER_MODE=real` (rerank strategy uses configured reranker; other strategies unaffected).
* CLI must print a **configuration banner** before results including: dataset id, case count, `eval_top_k`, embedding mode, reranker mode, collection chunk count, and pipeline label. When either mode is `stub`, banner includes an explicit note that results are wiring/determinism checks, not authoritative model-quality benchmarks.
* Default CI and unit/integration tests use **stub providers** and **must not** download or execute real models.
* Optional pytest marker (e.g. `real_model` or reuse `RAG_EMBEDDING_ENABLE_REAL_TESTS` / `RAG_RERANKER_ENABLE_REAL_TESTS`) may gate a manual full-benchmark smoke test — not required for plan acceptance.

#### Consequences

* Operators can verify evaluation wiring in lightweight environments.
* Lecture documentation can state clear prerequisites for publishing benchmark numbers.
* Plan 13 evaluation APIs remain mode-agnostic.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Force real models for `rag evaluate` | Breaks CI and lightweight dev workflows |
| Separate `RAG_EVAL_*` model overrides | Duplicates bootstrap configuration; risks index/provider mismatch |
| Hide stub mode from output | Misleading benchmark interpretation |
| Auto-reindex on evaluate when mode changes | Violates human-in-the-loop indexing rules (ADR-012, ADR-054) |

---

## Design Evaluations

This section records Plan 18 answers to explicit design questions. Implementation must not reopen them without a plan revision.

### 1. Where does evaluation execution live?

| Layer | Responsibility |
| ----- | -------------- |
| `evaluation/` | Dataset loading, `EvaluationRunner`, metrics, `EvaluationReport`, `ComparisonReport`, text formatters — **unchanged** |
| `bootstrap/` | `build_demo_environment()`, `build_retriever_for_strategy()`, shared retrieval stack |
| `cli/evaluate.py` | Command handlers: validate prerequisites → assemble retriever → run evaluation → print report; optionally serialize reports to JSON when `--output` is supplied |
| `cli/main.py` | Argparse tree for `rag evaluate {run,compare}` |

No `evaluation/execution.py` production module. No MCP or agent participation.

---

### 2. Does evaluation own retriever construction?

**No.** Retriever construction remains outside `evaluation/` production modules per ADR-050. Plan 18 assigns construction to **bootstrap** (ADR-068). `EvaluationRunner` continues to accept any `Retriever` with a caller-supplied `retriever_label`.

---

### 3. Can benchmark data mutate?

**No.** `load_evaluation_dataset` is read-only. Evaluation commands must not write to `data/evaluation/`. Optional operator-supplied report export via `--output PATH` writes JSON outside the benchmark tree only; it is not required for acceptance.

---

### 4. How does strategy selection work?

CLI parses `--strategy` for `run` and maps to bootstrap `RetrievalStrategy`. Bootstrap returns the orchestrator for that strategy from the shared stack. Invalid strategy names fail argparse or explicit validation before any retrieval call.

**Canonical stacks (repeated for implementers):**

```text
dense:   DenseRetriever
sparse:  SparseRetriever
fusion:  FusionRetriever(DenseRetriever, SparseRetriever)
rerank:  RerankRetriever(FusionRetriever(...), Reranker)
```

Fusion and rerank strategies always use the **same** dense and sparse leaf retrievers built from the current bootstrap environment.

---

### 5. Does comparison require identical benchmark inputs?

**Yes.** Within one `rag evaluate compare` invocation, all four strategies share the same dataset file, `EvaluationSettings`, and indexed collection. `compare_evaluation_reports` enforces compatible `EvaluationReport` metadata.

---

### 6. Real vs stub evaluation expectations

See ADR-070. Summary:

| Mode | Runs? | Meaningful for lecture benchmark claims? |
| ---- | ----- | ---------------------------------------- |
| stub embeddings + stub reranker | yes | no — wiring and relative strategy behavior only |
| real embeddings + stub reranker | yes | partial — dense/fusion improve; rerank strategy still stub-scored |
| real embeddings + real reranker | yes | yes — intended lecture benchmark configuration (with reindexed corpus) |

---

### 7. CLI ownership boundaries

| Module | May import |
| ------ | ---------- |
| `cli/demo.py` | `bootstrap`, stdlib |
| `cli/evaluate.py` | `bootstrap`, `evaluation`, stdlib |
| `cli/main.py` | `cli.demo`, `cli.evaluate`, stdlib |

`cli/evaluate.py` must not import `storage`, `indexing`, `retrieval` (concrete), `agent`, `mcp_server`, `llm`, or `qdrant_client`. Strategy access goes through bootstrap only.

Update `tests/unit/cli/test_cli_imports.py` to enforce per-module boundaries (demo vs evaluate).

---

### 8. Should evaluate auto-index the corpus?

**No.** Indexing is a separate human-gated operator step (`rag demo load`). Evaluate fails fast when the collection is missing or empty, directing the operator to run `rag demo load` first. Evaluate does not accept `--rebuild` or `--approve`.

---

### 9. Default dataset and settings

| Setting | Default | Override |
| ------- | ------- | -------- |
| Dataset path | `data/evaluation/retrieval_benchmark_v1.json` (repo-relative) | `--dataset PATH` |
| `eval_top_k` | `5` (`EvaluationSettings` default) | `--eval-top-k INT` |
| `metrics_k` | `(1, 3, 5)` | `--metrics-k` comma-separated (e.g. `1,3,5`) |

Validation follows existing `EvaluationSettings.__post_init__` rules.

---

## Module Layout

### Bootstrap (extend)

```text
src/knowledge_assistant/bootstrap/
    __init__.py          # export build_retriever_for_strategy, RetrievalStrategy (if public)
    config.py            # UNCHANGED (provider modes already present)
    environment.py       # refactor: use shared retrieval stack builder
    retrievers.py        # NEW: RetrievalStrategy, build_retrieval_stack, build_retriever_for_strategy
```

### CLI (extend)

```text
src/knowledge_assistant/cli/
    main.py              # add evaluate subparser
    evaluate.py          # NEW: run_evaluate_run, run_evaluate_compare
    demo.py              # UNCHANGED
```

### Unchanged packages

```text
evaluation/       # UNCHANGED production modules (use existing APIs only)
retrieval/        # UNCHANGED
storage/          # UNCHANGED
indexing/         # UNCHANGED
mcp_server/       # UNCHANGED
agent/            # UNCHANGED
llm/              # UNCHANGED
data/evaluation/  # UNCHANGED benchmark content
```

---

## API Design

### `RetrievalStrategy`

**Module:** `bootstrap/retrievers.py`

```python
RetrievalStrategy = Literal["dense", "sparse", "fusion", "rerank"]

CANONICAL_STRATEGIES: tuple[RetrievalStrategy, ...] = (
    "dense",
    "sparse",
    "fusion",
    "rerank",
)
```

### `build_retrieval_stack`

**Module:** `bootstrap/retrievers.py`

Internal or public frozen dataclass holding shared `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `RerankRetriever`, and reranker reference. Built from `BootstrapSettings` + `VectorStore` using the same rules as current `build_demo_environment()`.

### `build_retriever_for_strategy`

**Module:** `bootstrap/retrievers.py`

```python
def build_retriever_for_strategy(
    environment: DemoEnvironment,
    strategy: RetrievalStrategy,
) -> Retriever: ...
```

Behavior:

1. Reuse retrieval stack components from `environment` (preferred: build stack once per `DemoEnvironment` or memoize on environment).
2. Return the orchestrator for `strategy`:
   * `dense` → dense retriever;
   * `sparse` → sparse retriever;
   * `fusion` → fusion retriever;
   * `rerank` → rerank retriever.
3. Do not mutate vector store or index.
4. Raise `ValueError` for invalid strategy (defensive; CLI should pre-validate).

### `strategy_stack_description`

**Module:** `bootstrap/retrievers.py` (optional helper)

Returns human-readable stack description for CLI banner (may delegate to existing `pipeline_label` for `rerank`).

### Public bootstrap exports

Add to `bootstrap/__init__.py`:

```python
__all__ = (
    # ... existing ...
    "CANONICAL_STRATEGIES",
    "RetrievalStrategy",
    "build_retriever_for_strategy",
)
```

---

## CLI Commands

Extend `rag` argparse tree:

```text
rag evaluate run --strategy <dense|sparse|fusion|rerank> [options]
rag evaluate compare [options]
```

### Shared options (`run` and `compare`)

| Flag | Default | Purpose |
| ---- | ------- | ------- |
| `--dataset PATH` | `data/evaluation/retrieval_benchmark_v1.json` | Benchmark JSON path |
| `--eval-top-k INT` | `5` | `EvaluationSettings.eval_top_k` |
| `--metrics-k LIST` | `1,3,5` | Comma-separated K values for Hit Rate@K and Recall@K |
| `--output PATH` | *(omitted)* | Optional directory for JSON report export; stdout rendering is unchanged |

### `rag evaluate run`

**Purpose:** Evaluate one retrieval strategy against the benchmark.

**Example:**

```bash
rag evaluate run --strategy dense
rag evaluate run --strategy rerank --eval-top-k 10 --metrics-k 1,5,10
rag evaluate run --strategy rerank --output reports/
```

**Flow:**

```text
parse args
    ↓
build_demo_environment()
    ↓
validate dataset path exists → load_evaluation_dataset
    ↓
validate collection_chunk_count > 0
    ↓
build_retriever_for_strategy(env, strategy)
    ↓
EvaluationRunner(settings).run(retriever, dataset, retriever_label=strategy)
    ↓
print configuration banner
    ↓
print format_evaluation_report(report)
    ↓
if --output PATH supplied:
    write evaluation_<strategy>.json (serialized EvaluationReport)
```

**Optional JSON export (`--output PATH`):**

When `--output` is supplied, CLI creates the directory if needed and writes:

```text
<PATH>/
└── evaluation_<strategy>.json
```

Example: `rag evaluate run --strategy rerank --output reports/` → `reports/evaluation_rerank.json`.

* Contents: JSON serialization of the existing `EvaluationReport` dataclass — no new report schema.
* Serialization is owned by `cli/evaluate.py` (e.g. `dataclasses.asdict` + `json.dump`); do not add export logic to `evaluation/` production modules unless serialization helpers already exist there.
* Stdout behavior is unchanged: configuration banner and `format_evaluation_report` still print when `--output` is supplied.

**Exit codes:**

| Code | Condition |
| ---- | --------- |
| `0` | evaluation completed successfully |
| `1` | unexpected operational failure (Qdrant connectivity, retriever exception, dataset load error after validation) |
| `2` | argparse usage error (unknown strategy, invalid flags) |
| `3` | precondition failure: missing dataset file, missing/empty collection |

**Stdout:** configuration banner + `format_evaluation_report(report)` (stable Plan 13 plain text).

**Stderr:** actionable error messages (e.g. "collection is empty; run `rag demo load` first").

### `rag evaluate compare`

**Purpose:** Run all four canonical strategies and print a side-by-side comparison.

**Example:**

```bash
rag evaluate compare
rag evaluate compare --dataset data/evaluation/retrieval_benchmark_v1.json
rag evaluate compare --output reports/
```

**Flow:**

```text
parse args
    ↓
build_demo_environment()
    ↓
validate dataset + non-empty collection (once)
    ↓
load_evaluation_dataset
    ↓
for strategy in CANONICAL_STRATEGIES:
    retriever = build_retriever_for_strategy(env, strategy)
    report = runner.run(retriever, dataset, retriever_label=strategy)
    ↓
compare_evaluation_reports(tuple(reports))
    ↓
print configuration banner
    ↓
print format_comparison_report(comparison)
    ↓
if --output PATH supplied:
    write evaluation_<strategy>.json for each strategy
    write comparison.json (serialized ComparisonReport)
```

**Optional JSON export (`--output PATH`):**

When `--output` is supplied, CLI creates the directory if needed and writes:

```text
<PATH>/
├── evaluation_dense.json
├── evaluation_sparse.json
├── evaluation_fusion.json
├── evaluation_rerank.json
└── comparison.json
```

* Per-strategy files: serialized `EvaluationReport` for each canonical strategy run.
* `comparison.json`: serialized `ComparisonReport` from `compare_evaluation_reports` — no alternate format (no HTML, CSV, or database persistence).
* Serialization is owned by `cli/evaluate.py`; evaluation remains responsible for report generation only.
* Stdout behavior is unchanged: configuration banner and `format_comparison_report` still print when `--output` is supplied.

**Exit codes:** same table as `run`. Any strategy failure aborts the command (fail-fast).

**Stdout:** configuration banner + `format_comparison_report(comparison)` with columns `dense`, `sparse`, `fusion`, `rerank`.

**Performance note:** compare executes the full benchmark four times. This is acceptable for Phase 13 lecture scale (~70 cases). Document expected runtime; do not add parallelism in Plan 18.

---

## Bootstrap Integration

Plan 18 extends bootstrap without changing provider selection semantics from Plans 16–17.

```text
BootstrapSettings.from_env()
    ↓
build_demo_environment()
    ├── vector_store        ← Qdrant via storage factory
    ├── indexing_pipeline   ← stub or real embeddings
    └── retriever           ← canonical rerank stack (unchanged)
    ↓
build_retriever_for_strategy(environment, strategy)
    └── uses shared dense/sparse/fusion/rerank instances
```

**Requirements:**

* `build_demo_environment()` signature remains stable unless a minimal refactor requires no caller changes;
* evaluate commands obtain settings exclusively through `BootstrapSettings.from_env()` / `build_demo_environment()` — no parallel settings types;
* evaluate does not call `IndexingPipeline.index_documents`;
* `rag demo info` remains the status command for corpus/index/provider configuration; evaluate banner may echo the same pipeline label.

**Indexed corpus contract:** evaluation assumes the collection indexed via `rag demo load` against `BootstrapSettings.corpus_root` (default `knowledge/`). Evaluate does not verify corpus file hashes against `corpus_version` in benchmark JSON in v1 — path-level qrels only (ADR-048). Mismatch between indexed paths and benchmark registry surfaces as low metrics, not as a silent pass.

---

## Evaluation Outputs

### `EvaluationReport` (single strategy)

Produced by existing `EvaluationRunner.run(...)`. Required fields used by CLI and tests:

* `retriever_label` — canonical strategy name;
* `dataset_id`, `eval_top_k`, `metrics_k`, `case_count`;
* `hit_rate_at_k`, `recall_at_k`, `mrr`;
* per-case breakdown in `cases` (for tests; CLI prints formatted aggregate report by default).

### `ComparisonReport` (four strategies)

Produced by existing `compare_evaluation_reports(...)`. CLI prints `format_comparison_report(comparison)`:

* rows: Hit Rate@K, Recall@K, MRR per ADR-049;
* columns: `dense`, `sparse`, `fusion`, `rerank` in canonical order.

No new metrics. No changes to formatter column semantics.

### CLI rendering

* Use existing `format_evaluation_report` and `format_comparison_report` — do not duplicate table formatting in CLI.
* Configuration banner is CLI-owned plain text (not part of `EvaluationReport`).
* Banner minimum fields: dataset id, case count, eval top_k, metrics_k, embedding mode, reranker mode, collection name, chunk count, pipeline label, stub-mode notice when applicable.

### Optional JSON export (CLI-owned)

When `--output PATH` is supplied:

| Command | Files written | Source object |
| ------- | ------------- | ------------- |
| `evaluate run` | `evaluation_<strategy>.json` | `EvaluationReport` |
| `evaluate compare` | `evaluation_dense.json`, `evaluation_sparse.json`, `evaluation_fusion.json`, `evaluation_rerank.json`, `comparison.json` | per-strategy `EvaluationReport` + `ComparisonReport` |

Design constraints:

* **JSON only** — no HTML, CSV, or database persistence.
* **Reuse existing dataclasses** — serialize `EvaluationReport` and `ComparisonReport` as-is; no new report models or schema redesign.
* **CLI ownership** — `cli/evaluate.py` may serialize reports; `evaluation/` remains responsible for report generation and text formatters only.
* **Filesystem optional** — commands work identically when `--output` is omitted; export is operator-driven and local-only.
* **No tracking systems** — no automatic history, report registry, experiment tracking, MLFlow, or Weights & Biases.

---

## Dependency Rules

### Allowed

| Consumer | May import |
| -------- | ---------- |
| `bootstrap/retrievers.py` | `bootstrap.config`, `bootstrap.environment` types, `storage.VectorStore`, public `retrieval` API, `core`, `embeddings` (if already used by `environment.py`) |
| `cli/evaluate.py` | `bootstrap`, `evaluation`, stdlib |
| `cli/main.py` | `cli.demo`, `cli.evaluate`, stdlib |
| tests | `bootstrap`, `evaluation`, `cli`, fixtures |

### Forbidden

| Consumer | Must not import |
| -------- | --------------- |
| `evaluation/` production modules | `bootstrap`, `storage`, `indexing`, concrete `retrieval.*`, `cli` |
| `bootstrap/` | `evaluation`, `cli`, `agent`, `mcp_server`, `llm` |
| `cli/evaluate.py` | `storage`, `indexing`, concrete `retrieval`, `qdrant_client`, `agent`, `mcp_server`, `llm` |
| `cli/demo.py` | `evaluation` (demo commands remain independent) |
| `retrieval/`, `mcp_server/`, `agent/` | `evaluation` |

### Import-boundary tests

* Extend `tests/unit/cli/test_cli_imports.py` — evaluate modules may import `bootstrap` + `evaluation`; demo modules remain `bootstrap` only.
* Extend `tests/unit/bootstrap/test_bootstrap_imports.py` — bootstrap still must not import `evaluation`.
* Existing `tests/unit/evaluation/test_evaluation_imports.py` — unchanged pass criteria.

---

## Configuration

No new required environment variables for Plan 18. Evaluation inherits bootstrap configuration:

| Variable | Effect on evaluation |
| -------- | -------------------- |
| `QDRANT_URL` | vector store endpoint |
| `RAG_CORPUS_ROOT` | corpus path context (indexing prerequisite via demo load) |
| `RAG_EMBEDDING_MODE` | stub vs real dense embeddings for dense/fusion/rerank strategies |
| `RAG_RERANKER_MODE` | stub vs real reranker for **rerank** strategy only |
| `RAG_RERANKER_MODEL`, `RAG_RERANKER_DEVICE`, ... | reranker runtime when real mode |

CLI flags override `EvaluationSettings` only — not bootstrap provider modes.

---

## Testing Strategy

### Unit tests — `tests/unit/bootstrap/`

| Module | Focus |
| ------ | ----- |
| `test_strategy_retrievers.py` | `build_retriever_for_strategy` returns expected orchestrator types; four strategies share vector store; canonical labels; invalid strategy raises |

Use in-memory or fake vector store where needed; no Qdrant required for type/wiring tests.

### Unit tests — `tests/unit/cli/`

| Module | Focus |
| ------ | ----- |
| `test_evaluate_parsing.py` | `evaluate run` / `evaluate compare` argparse; strategy choices; metrics-k parsing; `--output` parsing |
| `test_evaluate_preconditions.py` | empty collection → exit `3`; missing dataset → exit `3`; mocked successful run prints formatter output |
| `test_evaluate_export.py` | optional `--output` writes expected JSON filenames; stdout unchanged; omitted `--output` writes no files |
| `test_evaluate_imports.py` | `evaluate.py` imports only `bootstrap`, `evaluation`, stdlib |

Mock `build_demo_environment` and evaluation runner for precondition and parsing tests.

### Integration tests — `tests/integration/evaluation/`

| Module | Focus |
| ------ | ----- |
| `test_evaluate_run_integration.py` | fixture corpus indexed into `:memory:` Qdrant; `main(["evaluate","run","--strategy","dense", "--dataset", fixture])` exits `0`; stdout contains Hit Rate / MRR |
| `test_evaluate_compare_integration.py` | same setup; `evaluate compare` with minimal benchmark fixture (3–5 cases in `tests/unit/evaluation/fixtures/` or dedicated integration fixture); builds four reports; stdout contains all strategy column headers |

**Fixture strategy:**

* temporary corpus directory with 2–3 `.md` files whose paths align with a **minimal** benchmark JSON used only in integration tests;
* `BootstrapSettings` override with in-memory Qdrant;
* index via `IndexingPipeline` or `rag demo load` code path;
* stub embedding/reranker modes only in default CI.

**Optional (not required for acceptance):**

* marked test running full `retrieval_benchmark_v1.json` against Docker Qdrant with real models when env flags set.

Real model execution remains optional in all default test runs.

---

## Runtime Dependencies

Plan 18 adds **no new runtime dependencies** to `pyproject.toml`. Execution composes existing bootstrap and evaluation packages.

---

## Documentation Updates (on implementation)

* `docs/DECISIONS.md` — accept ADR-067 through ADR-070;
* `docs/ARCHITECTURE.md` — evaluation execution workflow, bootstrap strategy assembly, CLI `rag evaluate` commands, updated CLI import rule for evaluate modules;
* `docs/PROGRESS.md` — Plan 18 completion entry;
* `README.md` — evaluation quickstart (`demo load` → `evaluate run` / `evaluate compare`), stub vs real benchmark prerequisites, optional `--output` JSON export;
* `docs/plans/backlog/ROADMAP.md` — mark Plan 18 active/completed under Phase 13;
* move this plan to `docs/plans/completed/` on completion.

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-067 through ADR-070 in `docs/DECISIONS.md`.
2. **Create `bootstrap/retrievers.py`** — `RetrievalStrategy`, `CANONICAL_STRATEGIES`, shared stack builder, `build_retriever_for_strategy`.
3. **Refactor `bootstrap/environment.py`** — use shared stack builder; preserve `DemoEnvironment` public fields and `build_demo_environment()` behavior.
4. **Update `bootstrap/__init__.py`** — export strategy assembly symbols.
5. **Create `cli/evaluate.py`** — `run_evaluate_run`, `run_evaluate_compare`, banner helper, precondition validation, optional `--output` JSON serialization.
6. **Extend `cli/main.py`** — `evaluate` subparser with `run` and `compare`.
7. **Add unit tests** — bootstrap strategy retrievers, CLI parsing, preconditions, import boundaries.
8. **Add integration tests** — evaluate run/compare against indexed fixture corpus and minimal benchmark JSON.
9. **Update `docs/ARCHITECTURE.md`** — evaluation execution and CLI sections.
10. **Update `README.md`** — evaluation workflow and real-model prerequisites.
11. **Update `docs/plans/backlog/ROADMAP.md`** — Phase 13 status.
12. **Run validation suite** — all four quality commands; fix until pass.
13. **Update `docs/PROGRESS.md`** — Plan 18 completion entry.
14. **Verify non-scope compliance** — no agent/MCP/retrieval algorithm/chat changes; evaluation production import boundaries intact.
15. **Move plan** to `docs/plans/completed/` when acceptance criteria satisfied.
16. **(Optional amendment)** Implement `--output PATH` JSON export in `cli/evaluate.py` and `test_evaluate_export.py` when portfolio/demo reuse is needed.

---

## Acceptance Criteria

### Bootstrap strategy assembly

- [x] `RetrievalStrategy` and `CANONICAL_STRATEGIES` defined with values `dense`, `sparse`, `fusion`, `rerank`
- [x] `build_retriever_for_strategy(environment, strategy)` returns correct orchestrator per ADR-068 stack table
- [x] Four strategies share the same `VectorStore` and bootstrap-selected embedding/reranker providers
- [x] `build_demo_environment()` behavior unchanged for existing demo/MCP/agent consumers (canonical `retriever` remains full rerank stack)
- [x] Bootstrap does not import `evaluation`

### CLI — `rag evaluate run`

- [x] `rag evaluate run --strategy dense|sparse|fusion|rerank` implemented
- [x] Loads benchmark dataset (default `data/evaluation/retrieval_benchmark_v1.json`, overridable via `--dataset`)
- [x] Fails with exit code `3` when collection missing or empty; message directs operator to `rag demo load`
- [x] Prints configuration banner and `format_evaluation_report` on success
- [x] Uses canonical `retriever_label` matching strategy name
- [x] Exit codes `0` / `1` / `2` / `3` behave per CLI specification

### CLI — `rag evaluate compare`

- [x] `rag evaluate compare` runs all four canonical strategies in order
- [x] Produces `ComparisonReport` via `compare_evaluation_reports`
- [x] Prints `format_comparison_report` with columns `dense`, `sparse`, `fusion`, `rerank`
- [x] Fail-fast on any strategy retriever or comparison validation error

### Evaluation framework integration

- [x] Uses existing `EvaluationRunner`, `EvaluationSettings`, `load_evaluation_dataset`, `compare_evaluation_reports`, and formatters without contract changes
- [x] Metrics reported: Hit Rate@K, Recall@K, MRR only (ADR-049)
- [x] Benchmark JSON is not mutated by evaluate commands

### Real vs stub behavior

- [x] Evaluate inherits `RAG_EMBEDDING_MODE` and `RAG_RERANKER_MODE` from bootstrap
- [x] Stub mode runs successfully with explicit non-authoritative benchmark notice in banner
- [x] README documents meaningful benchmark prerequisites (real embeddings, reindex, optional real reranker)

### Boundaries

- [x] `evaluation/` production modules still import only `core`, `retrieval.protocol.Retriever`, and stdlib
- [x] `cli/evaluate.py` imports `bootstrap` and `evaluation` only (plus stdlib); no direct storage/indexing/retrieval imports
- [x] `cli/demo.py` unchanged import boundary (`bootstrap` only)
- [x] Import-boundary tests updated and passing

### Tests and validation

- [x] Unit tests for strategy retriever assembly
- [x] Unit tests for CLI parsing, preconditions, and imports
- [x] Integration tests for `evaluate run` and `evaluate compare` with indexed fixture corpus
- [x] Default CI does not execute real models or require full 70-case benchmark
- [x] `uv run ruff format --check .`, `ruff check .`, `basedpyright`, `pytest` pass

### Optional JSON export

*Optional — not required for core Plan 18 completion. Commands must work identically when `--output` is omitted.*

- [ ] `rag evaluate run --output PATH` writes `evaluation_<strategy>.json` (serialized `EvaluationReport`; no new report schema)
- [ ] `rag evaluate compare --output PATH` writes `evaluation_dense.json`, `evaluation_sparse.json`, `evaluation_fusion.json`, `evaluation_rerank.json`, and `comparison.json` (serialized `ComparisonReport`)
- [ ] JSON export is owned by `cli/evaluate.py`; `evaluation/` remains responsible for report generation only
- [ ] Stdout behavior unchanged when `--output` is supplied (configuration banner and formatters still print)
- [ ] Unit tests in `test_evaluate_export.py` cover filenames, JSON contents, and no-file behavior when flag omitted

### Documentation

- [x] ADR-067 through ADR-070 recorded in `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents evaluation execution workflow
- [x] `README.md` documents `rag evaluate` commands
- [x] `docs/PROGRESS.md` updated on completion
- [x] `docs/plans/backlog/ROADMAP.md` updated for Phase 13

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Duplicated retriever wiring in CLI | ADR-068; shared stack builder; import-boundary tests |
| Evaluation import boundary violation | ADR-067; no execution module inside `evaluation/` |
| Operators run benchmark on stub-indexed collection | ADR-070 banner; README reindex guidance (ADR-058) |
| `compare` runtime on 70×4 cases feels slow | Document expected cost; no parallelism scope creep |
| Empty collection causes confusing zero metrics | Precondition check with exit `3` and explicit message |
| Strategy label drift breaks comparison table | Canonical labels enforced in CLI and bootstrap |
| Full benchmark integration test slows CI | Use minimal fixture benchmark in default integration tests |
| Refactoring `build_demo_environment` breaks demo tests | Preserve public `DemoEnvironment` contract; run existing demo integration tests |
| Sparse metrics disappoint in lecture | Document ADR-020 placeholder sparse behavior; fusion/rerank still demonstrate hybrid value |

---

## Follow-Up Work (Not Plan 18)

| Item | Target |
| ---- | ------ |
| `rag chat` interactive demo | Plan 19 |
| Optional `--output` JSON export (`EvaluationReport`, `ComparisonReport`) | Plan 18 amendment (authorized; see acceptance criteria) |
| Experiment tracking, report registries, benchmark dashboards | future evaluate enhancement |
| NDCG and graded metrics | future evaluation plan |
| Real BGE-M3 sparse vectors | future indexing/retrieval plan |
| Query rewriting impact evaluation | backlog (Plan 12b) |
| MCP SDK transport | Plan 12c (backlog) |
| Parallel strategy evaluation | future performance plan |
| Benchmark `corpus_version` hash verification against index | future hardening |

---

## Open Questions

1. **Memoization:** should `DemoEnvironment` cache the retrieval stack on first access, or rebuild per `build_retriever_for_strategy` call? Default: cache on environment for compare efficiency — decide during implementation without API churn.
2. **Full-benchmark CI job:** confirm whether a marked slow job running all 70 cases × 4 strategies belongs in repository CI or manual lecture prep only.
3. **Compare progress output:** should CLI print per-strategy progress lines during long compares? Recommended yes for operator feedback; not a contract requirement.

---

## Readiness Assessment

**Ready for activation?** **Yes.**

Plans 13–17 delivered the evaluation framework, canonical benchmark (70 cases), demo bootstrap, real dense embeddings, and real reranker. Bootstrap already assembles the full retrieval stack in `environment.py`. Plan 18 adds the missing execution path and CLI surface without retrieval algorithm or evaluation framework changes.

Before implementation:

1. Review proposed ADRs (especially stub vs real benchmark expectations).
2. Confirm CLI import-boundary test split (demo vs evaluate modules).
3. Confirm integration fixture benchmark aligns with minimal indexed corpus paths.

No architectural blockers identified relative to completed plans.

---

## Checklist

- [x] Plan reviewed and active in `docs/plans/active/`
- [x] ADR-067 through ADR-070 accepted in `docs/DECISIONS.md`
- [x] `bootstrap/retrievers.py` implemented; `environment.py` refactored
- [x] `cli/evaluate.py` and `cli/main.py` evaluate subcommands implemented
- [x] Unit and integration tests complete
- [x] `docs/ARCHITECTURE.md` and `README.md` updated
- [x] `docs/plans/backlog/ROADMAP.md` updated
- [x] Full validation suite passes
- [x] `docs/PROGRESS.md` updated
- [x] Plan moved to `docs/plans/completed/` on completion
- [ ] Optional `--output` JSON export implemented and tested (amendment; deferred from initial completion)
