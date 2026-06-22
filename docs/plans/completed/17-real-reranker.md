# Plan 17 — Real Reranker Integration

**Status:** Completed

**Created:** 2026-06-22

**Roadmap:** Phase 12 — Real Reranker Integration

**Depends on:**

* [Plan 09 — Reranking](../completed/09-reranking.md)
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md)

**Plan principle:** One plan introduces one architectural capability. Plan 17 introduces a **real BGE reranker runtime** behind the existing `Reranker` protocol only. It does **not** redesign retrieval, change retrieval contracts, introduce LLM calls, or move reranking outside the retrieval layer.

---

## Objective

Integrate a production `BAAI/bge-reranker-v2-m3` reranker implementation for the existing Plan 09 `Reranker` protocol while preserving the current retrieval architecture:

```text
SearchQuery
    ↓
RerankRetriever.retrieve()
    ↓
base Retriever.retrieve(candidate_query)
    ↓
Reranker.rerank(query, candidates)
    ↓
candidate preservation validation (N in → N out)
    ↓
truncate to query.top_k
    ↓
RetrievalResult
```

After this plan is complete:

* `knowledge_assistant.retrieval` contains a real `BgeReranker` (or similarly named) class implementing the existing `Reranker.rerank(query, candidates)` protocol;
* `StubReranker` remains available and remains the default for lightweight tests and fallback demo mode;
* bootstrap/demo wiring can opt into the real reranker via environment configuration;
* reranking uses `BAAI/bge-reranker-v2-m3` without changing `SearchQuery`, `SearchResult`, `RetrievalResult`, `Retriever`, or `Reranker`;
* real model execution is excluded from CI by default.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/retrieval/` | Real BGE reranker implementation, settings, exports |
| `src/knowledge_assistant/bootstrap/` | Stub vs real reranker selection for demo environment |
| `tests/unit/retrieval/` | Protocol, ordering, lazy-loading, and mocked backend tests |
| `tests/unit/bootstrap/` | Bootstrap reranker mode selection tests |
| `tests/integration/retrieval/` | Optional real-model smoke tests, marked and skipped by default |
| `docs/ARCHITECTURE.md` | Reranker runtime and score semantics documentation |
| `docs/DECISIONS.md` | ADR entries proposed below |
| `docs/PROGRESS.md` | Plan 17 completion entry |
| `README.md` and `.env.example` | Real reranker setup and environment variables |
| `pyproject.toml` / `uv.lock` | Approved runtime dependencies |

### In Scope

* concrete `Reranker` implementation using `BAAI/bge-reranker-v2-m3`;
* direct model integration inside `knowledge_assistant.retrieval`, preferably via `FlagEmbedding` or another minimal supported runtime;
* lazy model loading on first rerank call;
* CPU/GPU device selection through settings;
* batch scoring of `(query.text, candidate.chunk.text)` pairs for one query;
* deterministic ordering and tie-breaking after score assignment;
* candidate preservation invariant: `N` candidates in, `N` candidates out;
* bootstrap setting/env toggle for `stub` vs `real` reranker mode;
* fallback demo mode using `StubReranker`;
* unit tests with mocked model backend and no downloads;
* optional real-runtime tests excluded from default CI.

---

## Non-Scope

This plan does **not** authorize:

* changes to `SearchQuery`, `SearchResult`, `RetrievalResult`, `Retriever`, or `Reranker`;
* modifications to `DenseRetriever`, `SparseRetriever`, or `FusionRetriever`;
* new retrieval algorithms, alternate fusion strategies, score thresholding, or candidate filtering;
* changing the Plan 09 `Reranker` candidate preservation contract;
* moving reranking into MCP, agent, storage, Qdrant, evaluation, or LLM layers;
* LangChain reranker wrappers;
* LLM-as-a-Judge;
* LLM calls from retrieval;
* external observability/tracing systems;
* GPU requirement for tests or demo use;
* real model downloads in default CI;
* model serving infrastructure, microservices, Docker orchestration, or Kubernetes;
* sparse indexing changes or BGE-M3 sparse vector generation.

---

## Architectural Decisions / Proposed ADRs

Record these in `docs/DECISIONS.md` during implementation.

### ADR-061 — Real Reranker Stays Behind the Existing Reranker Protocol

**Status:** Proposed

#### Context

Plan 09 established `RerankRetriever` and the `Reranker` protocol. ADR-027 explicitly deferred real `BAAI/bge-reranker-v2-m3` integration while requiring future implementations to preserve the same contract.

#### Decision

* Implement the real reranker as a `knowledge_assistant.retrieval` class such as `BgeReranker`.
* The class implements `Reranker.rerank(query, candidates) -> tuple[SearchResult, ...]`.
* `RerankRetriever` remains unchanged except for dependency injection at bootstrap time.
* The real reranker must preserve candidate count exactly.
* The real reranker must not import MCP, agent, LLM, storage, indexing, Qdrant, or evaluation code.

#### Consequences

* Existing retrieval composition remains valid.
* MCP, agent, and evaluation code can keep depending on `Retriever` only.
* Tests can verify real reranker behavior with a mocked backend.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Rerank inside `FusionRetriever` | Couples fusion and reranking; violates Plan 09 architecture |
| MCP-owned reranking | Violates component boundaries |
| Agent or LLM-owned reranking | Introduces LLM behavior into retrieval scoring |
| Qdrant-side reranking | Moves model scoring into storage and bypasses `Reranker` |

### ADR-062 — Minimal Runtime for BGE Reranking

**Status:** Proposed

#### Context

The project names `BAAI/bge-reranker-v2-m3` as the required reranker. Implementation should be minimal, local, and aligned with BAAI-supported model APIs.

#### Decision

* Prefer direct integration through `FlagEmbedding` using its BGE reranker runtime API.
* Allow another minimal supported runtime if implementation proves it simpler, more stable, or better maintained for `BAAI/bge-reranker-v2-m3`.
* Add the required runtime dependency or dependency extras to `pyproject.toml` and lock them with `uv`.
* Do not use LangChain reranker wrappers.
* Do not use LlamaIndex reranker wrappers for production reranking.
* Do not hand-roll raw `transformers` inference unless preferred minimal runtimes prove unsuitable during implementation.
* Do not introduce ONNX or runtime optimization stacks in Plan 17.

#### Consequences

* Runtime code stays small and close to supported BGE reranker usage.
* First real run may download model weights from Hugging Face.
* CI remains stub/mock based unless optional model tests are explicitly enabled.
* Final runtime choice must be recorded in the implementation ADR if it differs from `FlagEmbedding`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| LangChain reranker wrapper | Adds an unnecessary framework layer and is explicitly out of scope |
| LlamaIndex postprocessor | Couples retrieval runtime to ingestion framework wrappers |
| Raw `transformers` cross-encoder | Higher maintenance cost; easier to mishandle model scoring; fallback only if minimal supported runtimes are unsuitable |
| ONNX / optimized inference runtime | Adds an optimization layer unnecessary for the educational project; may be reconsidered only in a future performance-focused plan |
| External reranker service | Infrastructure expansion; out of project scope |

### ADR-063 — Lazy Reranker Model Loading

**Status:** Proposed

#### Context

Bootstrap should remain cheap in stub mode and should not download or allocate a model unless real reranking is actually used.

#### Decision

* `BgeReranker` stores settings at construction time and loads the model lazily on first `rerank()`.
* Model lifetime is owned by the `BgeReranker` instance.
* A `BgeReranker` instance loads the model at most once.
* A `BgeReranker` instance reuses the already loaded model for all subsequent `rerank()` calls.
* A `BgeReranker` instance must not reload the model on every request.
* Cross-instance model sharing is implementation-defined and is not required by Plan 17.
* Plan 17 does not require process-wide singleton models, global caches, or shared model registries.
* Empty candidate input returns `()` without loading the model.
* Bootstrap can construct a real reranker without triggering model download.

#### Consequences

* `rag demo info` can report real reranker configuration without forcing model initialization.
* Unit tests can instantiate `BgeReranker` safely with mocked loaders.
* First real query pays model-load latency.
* Implementations may add cross-instance sharing later if justified, but Plan 17 keeps lifetime semantics instance-local.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Eager load during bootstrap | Makes status commands slow and may trigger downloads unexpectedly |
| Global singleton model | Hidden state complicates tests and configuration |
| Required global cache or model registry | Adds lifecycle complexity that Plan 17 does not need |
| Load per rerank call | Wastes time and memory |

### ADR-064 — Reranker Score Semantics Remain Reranker-Relevance Scores

**Status:** Proposed

#### Context

ADR-026 states that reranked `SearchResult.score` values are reranker relevance scores and are not comparable to dense, sparse, or RRF scores. The real model introduces numeric logits or relevance scores whose absolute calibration may vary by backend.

#### Decision

* `BgeReranker` replaces each candidate `SearchResult.score` with the model-produced relevance score.
* Higher score means more relevant.
* Scores are ordinal ranking keys, not probabilities.
* Original dense, sparse, or RRF scores are not preserved in Plan 17.
* Equal scores are tie-broken by `chunk_id` ascending.

#### Consequences

* Plan 09 score semantics remain intact.
* Evaluation and display code should treat scores as ranking values only.
* No core model extension is required.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Preserve previous scores in metadata | Requires core model or metadata contract changes |
| Normalize to probabilities | Backend-dependent and potentially misleading |
| Filter low-score candidates | Violates candidate preservation invariant |

### ADR-065 — Stub Default with Opt-In Real Reranker

**Status:** Proposed

#### Context

Plan 15 established a lightweight demo path using `StubReranker`. Real reranker dependencies are heavier and may require model downloads.

#### Decision

* Bootstrap defaults to `StubReranker`.
* Real reranker mode is opt-in via settings/environment.
* `StubReranker` remains the default for CI, unit tests, and fallback demo mode.
* `rag demo info` reports whether reranking is `stub` or `real`.

#### Consequences

* Existing tests remain fast and deterministic.
* Operators can enable the real reranker for the lecture demo after dependencies and model cache are available.
* Demo mode remains usable on CPU-only machines.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Make real reranker default | Breaks lightweight local and CI workflows |
| Remove `StubReranker` | Loses deterministic tests and fallback mode |
| Auto-detect real model availability | Hidden behavior makes demo state harder to explain |

### ADR-066 — Reranker Model Ownership

**Status:** Proposed

#### Context

The real reranker introduces the first retrieval-layer cross-encoder runtime. Without explicit ownership, model loading could drift into bootstrap, MCP handlers, evaluation, agent wiring, or LLM utilities.

#### Decision

* Retrieval owns reranker runtime models.
* Bootstrap selects the concrete implementation: `StubReranker` or real `Reranker`.
* Storage, indexing, MCP, agent, evaluation, and LLM layers must not load reranker models.
* Model loading stays behind the `Reranker` protocol.
* Higher layers interact only with a composed `Retriever`, typically `RerankRetriever`.

#### Consequences

* Model runtime dependencies remain localized to retrieval.
* Bootstrap remains a composition root rather than a model inference layer.
* MCP, agent, and evaluation code stay independent from reranker runtime details.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Bootstrap loads and owns the model directly | Turns dependency assembly into model runtime ownership |
| Evaluation owns the reranker for benchmark runs | Makes evaluation behavior diverge from production retrieval wiring |
| MCP or agent loads the reranker | Violates component boundaries and bypasses retrieval contracts |
| LLM layer owns cross-encoder models | Reranking is retrieval scoring, not chat-completion inference |

---

## Design Evaluation

### Should Plan 17 redesign retrieval?

No. Plan 09 already established the correct architecture:

```text
base Retriever → Reranker protocol → RerankRetriever truncation
```

Plan 17 adds a concrete `Reranker` implementation only. It must not change retrieval orchestration, contracts, or fusion behavior.

### Where should real reranking live?

In `knowledge_assistant.retrieval`, because reranking is retrieval-layer scoring over retrieved candidates. It should not be pushed into:

| Location | Reason rejected |
| -------- | --------------- |
| MCP | MCP exposes tools/resources; it does not own retrieval scoring |
| Agent | Agent handles conversation and tool use, not retrieval algorithms |
| LLM layer | Cross-encoder reranking is not chat-completion inference |
| Storage/Qdrant | Storage persists/searches vectors; it must not run model scoring |
| Evaluation | Evaluation measures retrieval; it must not own production scoring |


### Why BAAI/bge-reranker-v2-m3?

The project selects `BAAI/bge-reranker-v2-m3` because it is the current BGE reranker named in the repository technology constraints and best matches the project’s multilingual, modern-RAG teaching goals.

| Model | Assessment |
| ----- | ---------- |
| `BAAI/bge-reranker-base` | Smaller and lighter, but older and lower-capacity. Useful for constrained machines, but less representative of the stronger reranking quality expected in the lecture demo. |
| `BAAI/bge-reranker-large` | Stronger than `base`, but still from the earlier BGE reranker generation. It is a reasonable fallback for compatibility, but not the target model named by the project. |
| `BAAI/bge-reranker-v2-m3` | Selected. Modern BGE reranker aligned with the BGE-M3 family direction, suitable for multilingual retrieval scenarios, and explicitly required by `AGENTS.md` / project technology constraints. |

Plan 17 should implement `v2-m3` as the default model. Alternative BGE reranker models may be useful for local experimentation, but they must remain settings-level substitutions rather than a change to the project default.

### Which backend should be used?

The implementation should first evaluate `FlagEmbedding` BGE reranker APIs because they are close to the model family named by the project. Another minimal supported runtime is acceptable if it proves simpler or more stable for `BAAI/bge-reranker-v2-m3`. If the implementation uses a non-`FlagEmbedding` runtime, the final ADR must explain why.

ONNX and other runtime optimization stacks are out of scope for Plan 17 because they add an optimization layer that is unnecessary for the educational project. They may be reconsidered only in a future performance-focused plan.

### What happens to scores?

`SearchResult.score` after reranking is the BGE reranker score. It is an ordinal relevance score with higher values ranked first. It is not comparable to dense cosine, sparse scores, or RRF scores.

### How is determinism preserved?

The model score itself should be deterministic for identical inputs in evaluation mode. Ordering is enforced after scoring:

1. score descending;
2. `chunk_id` ascending for ties.

Do not preserve backend output order as the only ordering guarantee.

---

## Module/API Design

### Retrieval module layout

Preferred minimal change:

```text
src/knowledge_assistant/retrieval/
    __init__.py          # export BgeReranker and settings
    config.py            # add BgeRerankerSettings or RerankerRuntimeSettings
    rerank.py            # keep Reranker, StubReranker, RerankRetriever; add BgeReranker
```

If `rerank.py` becomes too large, implementation may introduce:

```text
src/knowledge_assistant/retrieval/bge_reranker.py
```

and re-export the public class from `retrieval/__init__.py`. Do not create a retrieval subpackage unless implementation complexity clearly requires it.

### Proposed settings

Use a frozen dataclass such as:

```python
@dataclass(frozen=True, slots=True)
class BgeRerankerSettings:
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "auto"
    batch_size: int = 16  # recommended initial default; implementation-defined
    max_length: int = 1024
    use_fp16: bool = False
```

Validation:

* `model_name` must be non-empty;
* `device` must be one of `auto`, `cpu`, `cuda`, or an implementation-supported device string such as `cuda:0`;
* `batch_size >= 1`;
* `max_length >= 1`;
* CPU mode must not require `use_fp16=True`.

`batch_size=16` is a recommended initial default, not a hard architectural decision. The actual default may be adjusted during implementation if the selected runtime has a safer convention. It must remain configurable via settings/environment, and operators may increase it for GPU machines.

### Proposed class

```python
class BgeReranker:
    def __init__(
        self,
        *,
        settings: BgeRerankerSettings,
        model_loader: BgeRerankerModelLoader | None = None,
    ) -> None: ...

    def rerank(
        self,
        query: SearchQuery,
        candidates: tuple[SearchResult, ...],
    ) -> tuple[SearchResult, ...]: ...
```

`model_loader` is an implementation detail that enables unit tests to inject a fake backend without importing or downloading the real model.

### Backend abstraction for tests

Define a small retrieval-local protocol or callable shape for the loaded model, for example:

```python
class BgeRerankerBackend(Protocol):
    def compute_scores(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int,
        max_length: int,
    ) -> list[float]: ...
```

This protocol is not a project-wide public API. It exists to keep model download and GPU use out of unit tests.

### Candidate preservation behavior

`BgeReranker.rerank()` must:

1. return `()` immediately for empty candidates;
2. build exactly one `(query.text, candidate.chunk.text)` pair per candidate;
3. request exactly `len(candidates)` scores from the backend;
4. raise `ValueError` or a retrieval-specific configuration/runtime error if backend score count differs;
5. construct new `SearchResult` values preserving `chunk` and `source`;
6. replace `score` with the BGE relevance score;
7. sort by `(-score, chunk_id)`;
8. return exactly `len(candidates)` results.

`RerankRetriever` remains the final enforcement point for `N` in → `N` out.

---

## Configuration Design

### Environment variables

Add settings under the `RAG_RERANKER_*` prefix:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `RAG_RERANKER_MODE` | `stub` | `stub` or `real` provider selection in bootstrap |
| `RAG_RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Hugging Face model identifier |
| `RAG_RERANKER_DEVICE` | `auto` | `auto`, `cpu`, `cuda`, or supported explicit device |
| `RAG_RERANKER_BATCH_SIZE` | implementation-defined, recommended initial `16` | Pair scoring batch size; operators may increase for GPU machines |
| `RAG_RERANKER_MAX_LENGTH` | `1024` | Max sequence length for pair scoring |
| `RAG_RERANKER_USE_FP16` | `false` | Optional half precision for supported GPU execution |
| `RAG_RERANKER_ENABLE_REAL_TESTS` | unset/false | Enables optional real-model smoke tests only |

### Device selection

* `cpu`: force CPU execution.
* `cuda`: require CUDA availability; fail clearly if unavailable.
* `cuda:0` or similar: use explicit backend-supported device.
* `auto`: prefer CUDA when available, otherwise CPU.

Implementation must not require GPU for tests or default demo mode.

### Dependency additions

Preferred dependency direction:

* evaluate `FlagEmbedding` first as the preferred BGE reranker runtime dependency;
* allow another minimal supported runtime if it is simpler or more stable for `BAAI/bge-reranker-v2-m3`;
* accept its required transitive dependencies such as `torch` and `transformers`;
* keep runtime imports localized to the real reranker module/path so stub-only imports remain cheap where practical;
* do not add ONNX or optimized inference runtime dependencies in Plan 17.

Document any platform-specific installation caveats in `README.md`.

---

## Bootstrap Integration

Plan 15 currently wires:

```text
FusionRetriever
      ↓
StubReranker
      ↓
RerankRetriever
```

Plan 17 updates bootstrap provider selection only:

```text
RAG_RERANKER_MODE=stub
    → StubReranker()

RAG_RERANKER_MODE=real
    → BgeReranker(settings=BgeRerankerSettings.from_env())
```

Requirements:

* `stub` remains the default;
* `build_demo_environment()` signature should remain stable unless implementation proves a small settings extension is necessary;
* `DemoEnvironment.retriever` remains `RerankRetriever`;
* `DEMO_RETRIEVAL_PIPELINE_LABEL` should reflect reranker mode, for example:
  * `dense + sparse → fusion (RRF) → rerank (stub)`;
  * `dense + sparse → fusion (RRF) → rerank (BAAI/bge-reranker-v2-m3)`;
* `rag demo info` must not trigger model loading;
* destructive index operations remain unchanged and still require approval.

---

## Testing Strategy

### Unit tests — retrieval

* `BgeRerankerSettings` validation and env parsing.
* Empty candidates return `()` without loading the model.
* Model is loaded lazily on first non-empty `rerank()`.
* One `BgeReranker` instance loads the model at most once and reuses it for subsequent `rerank()` calls.
* One `(query, chunk.text)` pair is passed per candidate.
* Backend score count mismatch raises a clear error.
* Candidate count is preserved for normal scoring.
* `chunk` and `source` are preserved while `score` is replaced.
* Ordering is score descending with `chunk_id` ascending tie-break.
* Repeated calls with the same fake backend output are deterministic.
* Import-boundary tests prevent retrieval reranker code from importing MCP, agent, LLM, storage, indexing, or Qdrant.

### Unit tests — bootstrap

* Default settings select `StubReranker`.
* `RAG_RERANKER_MODE=real` selects `BgeReranker` without loading the model.
* Invalid mode fails during settings parsing.
* Pipeline label includes reranker mode.
* Existing stub demo tests continue passing.

### Integration tests

Default CI:

* no real model download;
* no GPU requirement;
* use fake backend or mocked loader only.

Optional local smoke tests:

* marked with a pytest marker such as `real_model`;
* skipped unless `RAG_RERANKER_ENABLE_REAL_TESTS=true`;
* may require existing Hugging Face cache or network access;
* should run on CPU by default unless the operator configures CUDA;
* verify that `BgeReranker` returns the same number of candidates with numeric scores.

### Required validation commands

Run after implementation:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

---

## Documentation Updates

Implementation must update:

* `docs/ARCHITECTURE.md` — real reranker runtime, lazy loading, score semantics, bootstrap selection;
* `docs/DECISIONS.md` — ADR-061 through ADR-066 or final assigned ADR numbers;
* `docs/PROGRESS.md` — Plan 17 completion entry;
* `README.md` — how to enable real reranker, expected model download, CPU/GPU notes;
* `.env.example` — `RAG_RERANKER_*` variables;
* `docs/plans/backlog/ROADMAP.md` only if roadmap status references require adjustment when completing the plan.

Do not update documentation to imply reranking moved to MCP, agent, storage, Qdrant, or LLM layers.

---

## Acceptance Criteria

- [x] `BgeReranker` or equivalent implements the existing `Reranker` protocol.
- [x] `Reranker.rerank(query, candidates)` contract is unchanged.
- [x] `SearchQuery`, `SearchResult`, `RetrievalResult`, `Retriever`, and `Reranker` contracts are unchanged.
- [x] `DenseRetriever`, `SparseRetriever`, and `FusionRetriever` are unchanged.
- [x] Candidate preservation holds: `N` candidates in, `N` candidates out.
- [x] Scores after real reranking are BGE reranker relevance scores and higher is better.
- [x] Equal-score ties are ordered by `chunk_id` ascending.
- [x] Model loading is lazy, skipped for empty candidate input, and each `BgeReranker` instance loads at most once without requiring cross-instance sharing.
- [x] CPU and GPU device selection are configurable.
- [x] Stub reranker remains default for tests and fallback demo mode.
- [x] Bootstrap can opt into real reranker via environment/settings.
- [x] Default CI does not download or execute the real model.
- [x] Optional real-model smoke tests are marked/skipped by default.
- [x] No LangChain reranker wrappers are introduced.
- [x] Retrieval layer does not call LLMs.
- [x] Documentation and ADRs, including reranker model ownership, are updated.
- [x] Required validation commands pass.

---

## Implementation Checklist

1. Record proposed ADRs in `docs/DECISIONS.md`.
2. Add selected reranker runtime dependency in `pyproject.toml` and refresh `uv.lock`.
3. Add `BgeRerankerSettings` and env parsing.
4. Implement retrieval-local backend loader/protocol for test injection.
5. Implement `BgeReranker` with lazy loading.
6. Preserve candidate count and deterministic ordering.
7. Export public reranker class/settings from `knowledge_assistant.retrieval`.
8. Update bootstrap settings for `RAG_RERANKER_MODE` and real reranker settings.
9. Update `build_demo_environment()` reranker selection.
10. Update demo pipeline label/reporting.
11. Add retrieval unit tests with fake backend.
12. Add bootstrap unit tests for mode selection.
13. Add optional marked real-model smoke test.
14. Update README, `.env.example`, architecture, decisions, and progress docs.
15. Run required validation commands.
16. Move this plan to `docs/plans/completed/` when implementation is complete.

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Heavy dependencies slow CI | Keep `StubReranker` default; mock backend in unit tests |
| Model download during simple status command | Lazy load only on non-empty `rerank()` |
| GPU unavailable | Support CPU and make CPU the safe fallback for `auto` |
| Backend returns scores in unexpected shape | Validate score count and convert to plain `float` values |
| Scores are misread as probabilities | Document ordinal score semantics in architecture and README |
| Candidate filtering sneaks into reranker | Enforce `N` in → `N` out in `BgeReranker` and `RerankRetriever` |
| Framework wrappers blur boundaries | Use direct runtime integration; explicitly forbid LangChain wrappers |
| Real mode hides stub-indexed corpus quality issues | Document that meaningful end-to-end quality also depends on real embeddings and approved reindexing |
| Runtime optimization scope creep | Reject ONNX and optimization stacks in Plan 17; defer to a future performance-focused plan |
