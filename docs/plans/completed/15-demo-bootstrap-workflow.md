# Plan 15 — Demo Bootstrap Workflow

**Status:** Completed

**Completed:** 2026-06-22

**Created:** 2026-06-22

**Roadmap:** Phase 10 — Demo Bootstrap Workflow

**Depends on:**

* [Plan 10 — Knowledge MCP Server](../completed/10-knowledge-mcp-server.md)
* [Plan 11 — LLM Boundary](../completed/11-llm-boundary.md)
* [Plan 12 — LangGraph Agent](../completed/12-langgraph-agent.md)
* [Plan 13 — Evaluation Framework](../completed/13-evaluation-framework.md)
* [Plan 14 — Synthetic Corporate Knowledge Base](../completed/14-synthetic-knowledge-base.md)

**Plan principle:** One plan introduces one capability. Plan 15 introduces **bootstrap and wiring of the complete demo environment** only — connecting existing components into a runnable demo workflow. It does **not** introduce retrieval algorithms, MCP capabilities, agent capabilities, real model runtimes, evaluation execution, or interactive chat.

---

## Authorization

**Active.** ADR-051 through ADR-054 recorded in `docs/DECISIONS.md`.

---

## Objective

Wire existing storage, indexing, and retrieval layers into a **demo composition root** and expose **CLI demo commands** that let a developer go from a locally generated Plan 14 corpus to an indexed Qdrant collection ready for future evaluation and chat workflows.

```text
python3 tools/knowledge_generator/generator.py   ← Plan 14 (corpus generation)
        ↓
rag demo info                                    ← Plan 15 (read-only status)
        ↓
rag demo load                                    ← Plan 15 (index canonical corpus)
        ↓
(index ready)
        ↓
future: rag evaluate                             ← Plan 18
future: rag chat                                 ← Plan 19
```

After this plan is complete:

* a developer can inspect demo readiness with `rag demo info`;
* a developer can index the canonical `knowledge/` corpus into Qdrant with `rag demo load`;
* a developer can remove the demo collection with `rag demo reset`;
* all dependency assembly lives in `knowledge_assistant.bootstrap` — not duplicated in CLI modules;
* the canonical demo retrieval stack uses stub embeddings and stub reranker until Plans 16–17;
* human-in-the-loop approval gates protect destructive operations.

**Ownership boundaries (explicit):**

| Concern | Owner |
| ------- | ----- |
| Corpus generation (`python3 tools/knowledge_generator/generator.py`) | Plan 14 |
| Retrieval strategy evaluation CLI (`rag evaluate`) | Plan 18 |
| Interactive chat CLI (`rag chat`) | Plan 19 |

Plan 15 must not implement, stub, or partially deliver evaluation execution or chat UX.

---

## Required User Workflow

The lecture and README demo path after Plan 15:

```text
# 1. Generate canonical corpus (Plan 14 — not implemented by Plan 15)
python3 tools/knowledge_generator/generator.py

# 2. Inspect demo state (no mutations)
rag demo info

# 3. Index corpus into Qdrant (first load — collection absent)
rag demo load

# 4. Confirm index ready
rag demo info

# To replace an existing collection (both flags required):
# rag demo load --rebuild --approve

# Future plans (out of scope for Plan 15):
# rag evaluate
# rag chat
```

Prerequisites assumed by the workflow:

* Python 3.12+ and `uv sync` completed;
* Qdrant reachable at configured URL (default `http://localhost:6333` via `QDRANT_URL`);
* Plan 14 corpus generated locally under `knowledge/` (gitignored).

Plan 15 does **not** add Docker Compose, corpus generation, LLM setup, or MCP SDK transport.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/bootstrap/` | Demo composition root — assemble storage, indexing, retrieval |
| `src/knowledge_assistant/cli/` | `rag` entrypoint and `demo` subcommands |
| `tests/unit/cli/` | CLI parsing, approval gates, formatting |
| `tests/integration/cli/` | End-to-end demo load/info/reset against Qdrant |
| `README.md` | Demo bootstrap quickstart |
| `docs/ARCHITECTURE.md` | Bootstrap layer and CLI demo workflow |
| `docs/DECISIONS.md` | ADR-051 through ADR-054 |
| `docs/PROGRESS.md` | Plan 15 completion entry |

### Minimal authorized storage extension

`rag demo info` must report **collection chunk count**. The existing `VectorStore` protocol exposes `collection_exists()` but not point counts. Plan 15 authorizes one administrative primitive:

* add `count_points() -> int` to `VectorStore` protocol and `QdrantVectorStore` implementation;
* return `0` when the collection does not exist;
* implement using Qdrant collection metadata (`points_count`) — not a new retrieval capability.

No other storage protocol changes are authorized.

### In Scope

* `bootstrap/` package with pure dependency assembly (no business logic, no CLI logic);
* `DemoEnvironment` (or equivalent frozen dataclass) exposing assembled `vector_store`, `indexing_pipeline`, and `retriever`;
* `BootstrapSettings` (or equivalent) for corpus root path, Qdrant URL, collection name, and vector dimensions — aligned with `StorageSettings` / `IndexingSettings` defaults;
* `build_demo_environment()` factory using stub providers only;
* `rag` CLI entrypoint registered in `pyproject.toml` (`[project.scripts]`);
* `rag demo info`, `rag demo load`, `rag demo reset` subcommands;
* explicit `--approve` / `--yes` flag for destructive `demo load` (when `rebuild=True`) and `demo reset`;
* corpus discovery against canonical `knowledge/` directory from Plan 14;
* `demo load` flow: `knowledge/` → `IndexingPipeline.index_documents` → Qdrant;
* `demo load` refuses to modify an existing collection unless both `--rebuild` and `--approve` are supplied; when permitted, runs `rebuild=True` (delete → create → upsert via existing pipeline);
* `demo reset` calls `VectorStore.delete_collection()` via bootstrap-assembled store;
* import-boundary tests: CLI imports `bootstrap` only; no `qdrant_client` in CLI production modules;
* unit and integration tests per [Testing Strategy](#testing-strategy);
* ADR-051 through ADR-054;
* documentation updates listed above.

### Non-Scope

Plan 15 does **not** authorize:

* **corpus generation** — remains `tools/knowledge_generator/` (Plan 14);
* **evaluation execution** — `rag evaluate`, `EvaluationRunner` CLI wiring (Plan 18);
* **interactive chat** — `rag chat`, agent loop, LLM calls (Plan 19);
* new retrieval algorithms or changes to `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `RerankRetriever`, or fusion/rerank math;
* new MCP handlers, MCP SDK transport, or agent graph changes;
* real **BAAI/bge-m3** embeddings or **BAAI/bge-reranker-v2-m3** reranker (Plans 16–17);
* query rewriting, memory systems, or LangGraph changes;
* Docker Compose or infrastructure orchestration;
* committing generated `knowledge/` files;
* changes to `data/evaluation/` benchmark;
* changes to `tools/knowledge_generator/`;
* duplicate indexing implementation outside `IndexingPipeline`;
* CLI direct imports of `agent`, `mcp_server`, `llm`, `qdrant_client`, concrete retrieval modules, or indexing internals.

---

## Design Evaluation

### Should `count_points()` be added to `VectorStore`?

#### Context

`rag demo info` must report collection chunk count. The existing `VectorStore` protocol exposes `collection_exists()` but not point counts. Operators need a read-only cardinality signal without running a search query.

#### Decision

* Add `count_points() -> int` to the existing `VectorStore` protocol and `QdrantVectorStore` implementation.
* Return `0` when the collection does not exist.
* Implement using Qdrant collection metadata (`points_count`).
* Do **not** introduce a separate admin protocol or admin-only interface.

This is an informational storage primitive — not a retrieval capability. Primary consumer is demo bootstrap status reporting (`demo info`).

#### Consequences

* `demo info` can report chunk count through the same `VectorStore` abstraction indexing and retrieval already use.
* Test fakes (`FakeVectorStore`) must implement `count_points()` for integration tests.
* The operation stays localized to storage; bootstrap and CLI do not call `qdrant_client` directly for counts.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate `AdminVectorStore` protocol | Adds a parallel interface for one read-only method; increases project complexity without meaningful benefit at this scale |
| Count via `search_dense` / scroll in bootstrap | Bypasses storage boundary; couples bootstrap to Qdrant query semantics |
| Omit chunk count from `demo info` | Fails plan requirement; operators cannot confirm indexing outcome |
| CLI calls `qdrant_client` for `get_collection` | Violates CLI import boundaries; duplicates storage knowledge |

---

## Bootstrap Composition Root

### Location

```text
src/knowledge_assistant/bootstrap/
    __init__.py          # public exports
    config.py            # BootstrapSettings
    environment.py       # DemoEnvironment + build_demo_environment()
```

### Responsibilities

Assemble and return ready-to-use objects. **No business logic. No CLI logic. Pure dependency assembly.**

```text
BootstrapSettings.from_env()
        ↓
create_qdrant_vector_store(StorageSettings)
        ↓
StubEmbeddingProvider + IndexingSettings  →  IndexingPipeline
        ↓
StubQueryEmbeddingProvider + StubSparseQueryEmbeddingProvider
        ↓
DenseRetriever + SparseRetriever
        ↓
FusionRetriever
        ↓
StubReranker + RerankRetriever
        ↓
DemoEnvironment(vector_store, indexing_pipeline, retriever, settings)
```

### `DemoEnvironment` fields (minimum)

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `settings` | `BootstrapSettings` | Resolved paths and collection configuration |
| `vector_store` | `VectorStore` | Qdrant-backed store |
| `indexing_pipeline` | `IndexingPipeline` | Canonical corpus indexing |
| `retriever` | `RerankRetriever` | Canonical demo retrieval entry point |

Optional read-only helpers (bootstrap-owned, not CLI-duplicated):

* `corpus_exists() -> bool`
* `corpus_document_count() -> int` — count supported `.md`/`.txt` files under corpus root using the same discovery rules as `IndexingPipeline` (includes `README.md`)
* `collection_exists() -> bool` — delegate to `vector_store.collection_exists()`
* `collection_chunk_count() -> int` — delegate to `vector_store.count_points()`

### Assembly rules

* Use `create_qdrant_vector_store` factory from `storage` — bootstrap is the only production module outside `storage/` that may construct `QdrantVectorStore` directly for demo wiring (CLI must not).
* `IndexingSettings.dense_vector_size` and `StorageSettings.dense_vector_size` must match via `BootstrapSettings.dense_vector_size` (read-only view of `storage_settings.dense_vector_size`; default `1024`).
* `DenseRetrievalSettings`, `FusionRetrievalSettings`, and `RerankRetrievalSettings` use library defaults unless `BootstrapSettings` overrides documented fields.
* Stub providers only: `StubEmbeddingProvider`, `StubQueryEmbeddingProvider`, `StubSparseQueryEmbeddingProvider`, `StubReranker`.
* Retriever wiring must mirror the integration pattern in `tests/integration/mcp_server/test_search_composed_retrieval_integration.py` — no novel composition shape.

### Future Evolution (Informational)

Plan 15 intentionally uses a single `build_demo_environment()` entrypoint that assembles the full demo stack.

Future plans may split assembly into:

* `build_demo_retriever()`
* `build_demo_indexing_pipeline()`
* `build_demo_environment()`

if composition complexity grows (for example, when Plans 16–17 introduce swappable real model providers with independent configuration).

**No such split is authorized in Plan 15.** This note is documentation only — no additional modules or public APIs are introduced by this plan.

### Dependency rules

**Bootstrap may import:**

| Package | Symbols |
| ------- | ------- |
| `storage` | `VectorStore`, `StorageSettings`, `create_qdrant_vector_store` |
| `indexing` | `IndexingPipeline`, `IndexingSettings`, `StubEmbeddingProvider`; `indexing.documents.discover_files` for corpus counting |
| `retrieval` (public package API) | `DenseRetriever`, `SparseRetriever`, `FusionRetriever`, `RerankRetriever`, `StubReranker`, `StubQueryEmbeddingProvider`, `StubSparseQueryEmbeddingProvider`, `DenseRetrievalSettings`, `FusionRetrievalSettings`, `RerankRetrievalSettings` |
| `core` | `IndexingSource`, `IndexingSourceKind` |
| `bootstrap.config` | `BootstrapSettings` (internal) |

Bootstrap must import retrieval orchestrators from `knowledge_assistant.retrieval` (public `__init__` exports), not internal retrieval submodules. `indexing.documents.discover_files` is required for corpus counting because it is not re-exported from `indexing.__init__`.

Bootstrap must **not** import other `retrieval` modules (for example `retrieval.protocol`, `retrieval.fusion.reciprocal_rank_fusion`, exception types, or future BGE provider modules). If a symbol is not listed above, it is not authorized in Plan 15 bootstrap production code.

**Bootstrap must not import:**

`cli`, `agent`, `mcp_server`, `llm`, `evaluation`, LangGraph, MCP SDK, OpenAI SDK.

---

## Canonical Demo Retrieval Pipeline

This is the **canonical demo retrieval configuration** until Plans 16–17 replace stub providers with real model runtimes.

```text
DenseRetriever
      +
SparseRetriever
      ↓
FusionRetriever
      ↓
StubReranker
      ↓
RerankRetriever          ← inject into future MCP/agent/evaluation wiring
```

| Stage | Implementation | Notes |
| ----- | -------------- | ----- |
| Dense | `DenseRetriever` + `StubQueryEmbeddingProvider` | Hash-based stub per ADR-016 |
| Sparse | `SparseRetriever` + `StubSparseQueryEmbeddingProvider` | Placeholder-indexed corpus per ADR-020 |
| Fusion | `FusionRetriever` | RRF per ADR-023 |
| Rerank | `RerankRetriever` + `StubReranker` | Deterministic stub per ADR-027 |

`rag demo info` must report this pipeline as a human-readable label, for example:

```text
Retrieval pipeline: dense + sparse → fusion (RRF) → rerank (stub)
```

Future Plans 16–17 swap stub providers without changing CLI command names or bootstrap factory signature (constructor injection only).

---

## CLI Commands

Register entrypoint in `pyproject.toml`:

```toml
[project.scripts]
rag = "knowledge_assistant.cli.main:main"
```

Suggested module layout:

```text
src/knowledge_assistant/cli/
    __init__.py
    main.py              # argparse root: rag demo {info,load,reset}
    demo.py              # command handlers (delegate to bootstrap)
```

### `rag demo info`

**Purpose:** Show current demo state. **No indexing. No mutations.**

**Output must include:**

| Field | Source |
| ----- | ------ |
| Corpus exists (yes/no) | `knowledge/` directory present |
| Corpus document count | bootstrap corpus discovery |
| Collection exists (yes/no) | `vector_store.collection_exists()` |
| Collection chunk count | `vector_store.count_points()` |
| Configured retrieval pipeline | fixed demo label (see above) |
| Qdrant URL | `BootstrapSettings` / `StorageSettings` |
| Collection name | `StorageSettings.collection_name` (default `knowledge_chunks`) |
| Corpus path | `BootstrapSettings.corpus_root` (default `knowledge/`) |

**Exit codes:**

* `0` — command succeeded;
* non-zero — unexpected assembly or connectivity failure (e.g. Qdrant unreachable when probing collection metadata).

**Flags:** none required. No `--approve`.

### `rag demo load`

**Purpose:** Index the canonical Plan 14 corpus into Qdrant.

**Flow (collection absent):**

```text
knowledge/  (IndexingSourceKind.DIRECTORY)
    ↓
IndexingPipeline.index_documents(rebuild=False)
    ↓
create collection (if needed) + upsert
    ↓
Qdrant collection populated
```

**Flow (collection present — rebuild):**

```text
knowledge/
    ↓
--rebuild --approve validation
    ↓
IndexingPipeline.index_documents(rebuild=True)
    ↓
delete collection → create collection → upsert
```

#### Existing Collection Behavior

Behavior is **mandatory** — no alternative implementations.

**Collection missing:**

```text
collection missing
    ↓
rag demo load
    ↓
create collection
    ↓
index corpus
```

* No `--rebuild` or `--approve` required.
* Calls `IndexingPipeline.index_documents(rebuild=False)`.

**Collection exists:**

```text
collection exists
    ↓
rag demo load
    ↓
error (non-zero exit)
```

* `rag demo load` **must refuse** to modify the existing collection.
* Exit with a clear message directing the operator to:

```text
rag demo load --rebuild --approve
```

* Rebuild is permitted **only** when **both** `--rebuild` and `--approve` (or `--yes`) are supplied.
* That path calls `IndexingPipeline.index_documents(rebuild=True)` per ADR-012.

**Requirements:**

* default corpus source: repository-relative `knowledge/` directory;
* reuse `IndexingPipeline` — no duplicate indexing implementation in CLI;
* print summary on success: documents indexed, chunks upserted, collection name;
* fail with clear message if corpus directory missing or empty.

### `rag demo reset`

**Purpose:** Delete the demo Qdrant collection.

**Requirements:**

* destructive operation;
* **`--approve` / `--yes` always required** — even when collection does not exist (no-op delete is still an explicit destructive intent);
* uses `vector_store.delete_collection()` via bootstrap-assembled store;
* no corpus file deletion;
* print confirmation of collection name removed or absent.

---

## Dependency Rules

### CLI layer

**CLI may import:**

| Module | Usage |
| ------ | ----- |
| `knowledge_assistant.bootstrap` | environment factory and status helpers |
| Python stdlib | `argparse`, `sys`, `pathlib` |

**CLI must not import:**

| Module | Reason |
| ------ | ------ |
| `qdrant_client` | Storage boundary per ADR-002 |
| `knowledge_assistant.storage` (direct) | Assembly belongs in bootstrap |
| `knowledge_assistant.indexing` (direct) | Assembly belongs in bootstrap |
| `knowledge_assistant.retrieval.*` (concrete) | No duplicated retriever wiring |
| `knowledge_assistant.agent` | Out of scope |
| `knowledge_assistant.mcp_server` | Out of scope |
| `knowledge_assistant.llm` | Out of scope |
| `knowledge_assistant.evaluation` | Plan 18 |

Enforce with AST-based import-boundary tests in `tests/unit/cli/test_cli_imports.py` (mirroring the `tests/unit/import_ast.py` helper pattern).

### Design Note — Corpus Document Count (2026-06-22 review)

`corpus_document_count()` and `rag demo load` both use `discover_files()` over the corpus directory. `README.md` is included in both counting and indexing so `demo info` document counts match indexed document counts.

### Design Note — BootstrapSettings Vector Dimension (2026-06-22 review)

`BootstrapSettings.dense_vector_size` is a read-only property delegating to `storage_settings.dense_vector_size`. Indexing and retrieval settings derive from that single field — no duplicate constructor parameter.

### Who may import `bootstrap/`

| Consumer | Allowed |
| -------- | ------- |
| `cli` | yes |
| tests | yes |
| `agent`, `mcp_server`, `evaluation` (future) | yes for wiring — bootstrap is the shared composition root |
| `retrieval`, `indexing`, `storage` | **no** (no upward imports) |

---

## Architectural Decisions (Proposed ADRs)

Record in `docs/DECISIONS.md` during implementation.

### ADR-051 — Demo Bootstrap Composition Root

**Status:** Proposed

#### Context

Plans 04–09 delivered storage, indexing, and composable retrieval. Plans 10–13 delivered MCP handlers, agent, and evaluation — each requiring externally injected `Retriever` and `IndexingPipeline` instances. Without a single composition root, CLI, tests, and future demo scripts would duplicate retriever wiring (violating ADR-032 assembly rule).

#### Decision

* Introduce `knowledge_assistant.bootstrap` as the **demo composition root**.
* `build_demo_environment()` assembles `VectorStore`, `IndexingPipeline`, and canonical `RerankRetriever` stack using stub providers.
* Bootstrap contains **dependency assembly only** — no CLI parsing, no MCP handlers, no agent logic, no evaluation metrics.
* Bootstrap is the preferred wiring location for demo, CLI, and future `rag evaluate` / `rag chat` commands until a production configuration layer is needed.

#### Consequences

* CLI stays thin; retriever wiring exists in one place.
* Agent and MCP plans continue to receive injected dependencies — bootstrap does not replace `agent/wiring.py` MCP adapters.
* Real embedding/reranker swaps (Plans 16–17) change bootstrap provider selection only.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Wire retrievers directly in CLI | Duplicates assembly; violates import boundaries |
| Wire in `mcp_server` | Violates ADR-032 |
| Wire only in tests | Production demo path remains unwired |

---

### ADR-052 — CLI Owns Demo Orchestration

**Status:** Proposed

#### Context

ADR-012 and ADR-030 assign human approval enforcement to callers. Plan 14 owns corpus generation tooling outside `src/`. Demo workflows need a user-facing orchestration layer for status, indexing, and reset — without growing MCP or agent responsibilities.

#### Decision

* `knowledge_assistant.cli` owns **demo command orchestration**: argument parsing, stdout formatting, exit codes, and approval flag validation.
* CLI delegates all dependency construction to `bootstrap`.
* CLI does not implement indexing, retrieval, or storage logic.
* Corpus generation remains outside CLI (`tools/knowledge_generator/generator.py`).
* Evaluation and chat CLIs remain deferred to Plans 18 and 19.

#### Consequences

* Demo UX is testable independently of retrieval algorithms.
* MCP and agent layers remain free of argparse and stdin concerns.
* Future `rag evaluate` and `rag chat` extend the same CLI package under separate plans.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP tools for demo bootstrap | Demo setup is operator workflow, not agent knowledge access |
| Makefile-only orchestration | Not cross-platform; hides approval semantics |
| Agent-driven indexing | Violates human-in-the-loop and scope boundaries |

---

### ADR-053 — Canonical Demo Retrieval Pipeline

**Status:** Proposed

#### Context

Multiple valid retriever stacks exist (dense-only, fusion without rerank, etc.). Demo, evaluation comparison, and future MCP wiring must use one documented default so lecture results are reproducible.

#### Decision

* The canonical demo retrieval stack is:

```text
RerankRetriever(
    base_retriever=FusionRetriever(
        dense_retriever=DenseRetriever(...),
        sparse_retriever=SparseRetriever(...),
    ),
    reranker=StubReranker(),
)
```

* Stub embedding and stub reranker providers are mandatory until Plans 16–17.
* `bootstrap.build_demo_environment().retriever` is the default `Retriever` for demo indexing verification and future CLI evaluation/chat wiring.
* `rag demo info` reports this pipeline configuration to operators.

#### Consequences

* Plan 18 strategy comparison can document dense/sparse/fusion/rerank relative to the same indexed corpus and bootstrap defaults.
* Plans 16–17 replace providers without changing orchestrator shape.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Dense-only demo default | Under-represents hybrid retrieval lecture goals |
| Real models in Plan 15 | Explicitly deferred; heavy dependencies |
| Per-command retriever wiring | Non-reproducible demo state |

---

### ADR-054 — Demo Commands Require Explicit Approval for Destructive Operations

**Status:** Proposed

#### Context

`PROJECT.md` and ADR-012 require user confirmation before index replacement. Deleting a collection is similarly destructive. CLI must not silently rebuild or drop demo indexes.

#### Decision

* `rag demo load` requires `--approve` when `rebuild=True` executes (collection delete → create → upsert).
* `rag demo load` refuses to replace an existing collection without explicit `--rebuild --approve`.
* `rag demo reset` requires `--approve` for every invocation.
* `rag demo info` never mutates storage or corpus.
* CLI must not call `input()` — non-interactive flags only (CI-friendly).

#### Consequences

* Operators must deliberately opt in to data loss scenarios.
* Scripts and CI integration tests pass `--approve` explicitly.
* Consistent with MCP `approval_confirmed=True` pattern (ADR-030) at CLI layer.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Interactive `input()` prompts | Untestable in CI; ADR-012 rejects library prompts |
| Silent rebuild on `demo load` | Violates human-in-the-loop |
| Reset without approval | Destructive operation requires explicit consent |

---

## Configuration

### Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP endpoint (existing `StorageSettings.from_env()`) |
| `RAG_CORPUS_ROOT` | `knowledge` | Repository-relative corpus directory (optional; implement in `BootstrapSettings`) |

Collection name remains `knowledge_chunks` per ADR-003 unless overridden in test settings.

### Corpus path contract

* Canonical corpus root: `knowledge/` at repository root (Plan 14).
* `demo load` indexes the full directory tree via `IndexingSource(kind=IndexingSourceKind.DIRECTORY, path=corpus_root)`.
* Do not create a separate `demo/` corpus or sample subset.

---

## Testing Strategy

### Unit tests — `tests/unit/cli/`

| Module | Focus |
| ------ | ----- |
| `test_cli_imports.py` | AST-based import analysis: CLI production modules import only `bootstrap` + stdlib; forbid `qdrant_client`, `retrieval`, `indexing`, `storage`, `agent`, `mcp_server`, `llm` |
| `test_demo_parsing.py` | argparse subcommands, flag validation |
| `test_demo_approval.py` | `demo load` errors when collection exists without `--rebuild --approve`; `demo load` rejects `--rebuild` without `--approve`; `demo reset` rejects without `--approve` |
| `test_demo_info_format.py` | stable status output fields |

### Unit tests — `tests/unit/bootstrap/` (if not covered by CLI tests)

| Module | Focus |
| ------ | ----- |
| `test_bootstrap_imports.py` | AST-based import analysis: bootstrap does not import `cli`, `agent`, `mcp_server`, `llm`; bootstrap uses public `retrieval` package API only |
| `test_build_demo_environment.py` | returns wired `DemoEnvironment`; retriever is `RerankRetriever` over `FusionRetriever` |

### Integration tests — `tests/integration/cli/`

| Module | Focus |
| ------ | ----- |
| `test_demo_load_integration.py` | `main(["demo", "load"])` indexes fixture corpus into Qdrant (`:memory:`); verify collection exists and chunk count > 0 |
| `test_demo_info_integration.py` | `main(["demo", "info"])` reports corpus and collection state after CLI load |
| `test_demo_reset_integration.py` | `main(["demo", "reset", "--approve"])` deletes collection; chunk count == 0 |
| `test_demo_retrieval_smoke.py` | after `demo load` on fixture corpus, `build_demo_environment().retriever.retrieve(...)` returns `>= 1` result — wiring smoke only, not retrieval quality |

**Fixture strategy:**

* Use a temporary directory with 2–3 minimal `.md` files — **not** the full Plan 14 corpus (keeps CI fast).
* Use `QdrantClient(":memory:")` injected via `StorageSettings` override in test bootstrap factory helper.
* Optional smoke test (not required for acceptance): manual run against Docker Qdrant with real `knowledge/` corpus.

### Storage extension tests

* Add unit test for `QdrantVectorStore.count_points()` — `0` when missing, correct count after upsert.
* Update `FakeVectorStore` in retrieval integration fixtures if shared tests require `count_points`.

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-051 through ADR-054 in `docs/DECISIONS.md`.
2. **Extend storage protocol** — add `count_points() -> int` to `VectorStore` and `QdrantVectorStore`; update fakes; add unit tests.
3. **Create `bootstrap/config.py`** — `BootstrapSettings` with corpus root, env loading, aligned vector dimensions.
4. **Create `bootstrap/environment.py`** — `DemoEnvironment`, `build_demo_environment()`, status helper methods.
5. **Create `bootstrap/__init__.py`** — minimal public exports.
6. **Create `cli/main.py` and `cli/demo.py`** — argparse tree and command handlers.
7. **Register `[project.scripts]`** — `rag` entrypoint in `pyproject.toml`.
8. **Add unit tests** — CLI imports, approval gates, parsing, bootstrap assembly.
9. **Add integration tests** — demo load/info/reset and retrieval smoke (`test_demo_retrieval_smoke.py`) against in-memory Qdrant.
10. **Update `docs/ARCHITECTURE.md`** — bootstrap layer section, CLI demo workflow, dependency diagram.
11. **Update `README.md`** — demo quickstart (`generator.py` → `rag demo info` → `rag demo load`).
12. **Run validation suite** — all four quality commands; fix until pass.
13. **Update `docs/PROGRESS.md`** — Plan 15 completion entry; move this plan to `docs/plans/completed/`.
14. **Verify non-scope compliance** — no BGE models, evaluation runner CLI, chat, MCP/agent changes, or corpus generator changes.

---

## Acceptance Criteria

### Commands

- [x] `rag demo info` implemented — read-only status with corpus exists, corpus document count, collection exists, collection chunk count, retrieval pipeline label
- [x] `rag demo load` implemented — indexes Plan 14 `knowledge/` corpus via `IndexingPipeline`
- [x] `rag demo reset` implemented — deletes demo collection with `--approve`

### Bootstrap

- [x] `bootstrap/` package assembles full demo stack (`VectorStore`, `IndexingPipeline`, canonical `RerankRetriever`)
- [x] No duplicated retrieval wiring in CLI production modules
- [x] Stub providers only (`StubEmbeddingProvider`, stub query embeddings, `StubReranker`)

### Boundaries

- [x] CLI production code imports `bootstrap` only (plus stdlib)
- [x] No `qdrant_client` imports in `cli/` production modules
- [x] Import-boundary tests added and passing
- [x] Bootstrap does not import `cli`, `agent`, `mcp_server`, or `llm`

### Integration

- [x] `demo load` indexes a fixture corpus end-to-end into Qdrant
- [x] `demo info` reports collection state after load
- [x] `demo reset` removes collection when approved
- [x] `test_demo_retrieval_smoke.py` passes — fixture corpus → `demo load` → `build_demo_environment()` → `retriever.retrieve(...)` returns `>= 1` result (wiring smoke only)

### Approval gates

- [x] `demo load` refuses to modify an existing collection unless both `--rebuild` and `--approve` are supplied
- [x] `demo load` requires `--approve` when `--rebuild` is used
- [x] `demo reset` requires `--approve` always
- [x] `demo info` performs no mutations

### Validation

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes

#### Validation Report (2026-06-22)

```text
$ uv run ruff format --check .
171 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run basedpyright
0 errors, 0 warnings, 0 notes

$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 457 items
...
============================= 457 passed in 3.13s ==============================
```

### Documentation

- [x] ADR-051 through ADR-054 recorded in `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents bootstrap layer and CLI demo commands
- [x] `README.md` documents demo workflow
- [x] `docs/PROGRESS.md` updated on completion

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into `rag evaluate` or `rag chat` | Explicit ownership table; non-scope list; no `evaluation` or `agent` imports in CLI |
| Duplicated retriever wiring in CLI | ADR-051; import-boundary tests; single `build_demo_environment()` |
| CLI imports `qdrant_client` for convenience | Forbidden list; `test_cli_imports.py` |
| Missing corpus on fresh clone | `demo info` reports corpus missing; README documents `generator.py` first |
| Qdrant not running | clear connectivity error from `demo info` / `demo load` |
| Rebuild without approval or existing-collection load without flags | ADR-054; mandatory [Existing Collection Behavior](#existing-collection-behavior); `test_demo_approval.py` |
| `count_points` protocol change breaks fakes | update `FakeVectorStore` in test fixtures |
| Full 96-document corpus slows CI | integration tests use minimal temp fixture only |
| Vector dimension mismatch across settings | single `BootstrapSettings` source of truth for `dense_vector_size` |

---

## Follow-Up Work (Not Plan 15)

| Item | Plan |
| ---- | ---- |
| Real BGE-M3 embeddings (index + query) | Plan 16 |
| Real BGE cross-encoder reranker | Plan 17 |
| `rag evaluate` — four-strategy benchmark run | Plan 18 |
| `rag chat` — interactive agent CLI | Plan 19 |
| MCP SDK transport | Plan 12c (backlog) |
| Docker Compose for Qdrant | informational / operator docs only |

---

## Checklist (Plan Meta)

- [x] Plan authored and placed in `docs/plans/active/`
- [x] Implementation complete per acceptance criteria
- [x] Plan moved to `docs/plans/completed/` on completion
