# Plan 10 — Knowledge MCP Server

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 5 — Knowledge Access

**Depends on:**

* [Plan 05 — Indexing Pipeline](../completed/05-indexing-pipeline.md)
* [Plan 06 — Dense Retrieval](../completed/06-dense-retrieval.md)
* [Plan 07 — Sparse Retrieval](../completed/07-sparse-retrieval.md)
* [Plan 08 — Fusion Retrieval](../completed/08-fusion-retrieval.md)
* [Plan 09 — Reranking](../completed/09-reranking.md)

**Plan principle:** One plan introduces one architectural capability. Plan 10 introduces the **knowledge-access MCP boundary** (tool handlers and contracts) only.

---

## Objective

Design and implement a thin MCP knowledge-access layer that exposes search and indexing operations to higher layers (future LangGraph agent, CLI) without implementing agent behavior, LLM calls, transport wiring, or direct Qdrant access.

```text
MCP Client (future — Plan 12)
    ↓
MCP transport (future — Plan 12)
    ↓
Knowledge MCP handlers          ← Plan 10 delivers this layer
    ↓
┌─────────────────────┬──────────────────────┐
│ Retriever.retrieve  │ IndexingPipeline     │
│ (RerankRetriever)   │ preview / index      │
└─────────┬───────────┴──────────┬───────────┘
          ↓                      ↓
   retrieval layer         indexing layer
          ↓                      ↓
                    VectorStore (protocol)
                              ↓
                           Qdrant
```

After this plan is complete:

* **mandatory** knowledge tools — `search_documents`, `index_documents_preview`, `index_documents_apply` — are implemented as typed, testable handler functions;
* MCP orchestrates injected `Retriever` and `IndexingPipeline` only — no retrieval or indexing algorithm logic in MCP;
* MCP does not call LLMs, LangGraph, or OpenAI APIs;
* MCP does not import `qdrant_client` or `storage` packages;
* production wiring uses `RerankRetriever` over `FusionRetriever`, injected from outside `mcp_server`;
* index mutation requires an explicit approval field on the apply handler;
* search results include source attribution via `SearchResult.source` (storage-populated — ADR-031);
* Pydantic models exist **only** in `mcp_server/schemas.py`;
* MCP SDK runtime and repository-browsing tools are **deferred** (ADR-034, Follow-Up).

**Dependency rule:** `mcp_server` production code may depend on `knowledge_assistant.core`, `knowledge_assistant.retrieval.protocol.Retriever`, and `knowledge_assistant.indexing.pipeline.IndexingPipeline` only. It must **not** depend on `storage`, `qdrant_client`, concrete retrieval internals, LlamaIndex, LangGraph, OpenAI, `llm/`, or the MCP SDK.

---

## Capability Tiers

Plan 10 separates knowledge-access capabilities from repository-browsing capabilities.

### Tier 1 — Mandatory (Plan 10)

Required for the knowledge-access boundary and the lecture RAG flow (retrieve → ground → answer):

| Handler | Purpose |
| ------- | ------- |
| `search_documents` | Ranked chunk retrieval for grounding |
| `index_documents_preview` | Impact preview; no mutation |
| `index_documents_apply` | Index mutation after explicit approval |

These three handlers define the MCP knowledge contract that Plan 12 (agent) will consume.

### Tier 2 — Optional / Deferred (future plan)

Repository inspection and admin diagnostics — **not** required for agents to search, index, or ground answers:

| Capability | Why deferred |
| ---------- | ------------ |
| `get_document` | Full-document fetch by path is browsing/inspection; search already returns chunk text and citations |
| `get_statistics` | Aggregate counts are operational diagnostics, not retrieval |
| Storage read primitives (`get_chunks_by_document_path`, `get_collection_statistics`) | Only needed to support Tier 2 tools |
| MCP SDK server bootstrap | Transport wiring belongs with agent integration (Plan 12) |
| MCP resources (`knowledge://…`) | No Tier 1 requirement |

**Follow-up:** document as backlog item **Plan 10b — Knowledge Repository Browse** (or equivalent backlog plan) — see [Follow-Up Work](#follow-up-work-not-plan-10).

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/mcp_server/` — handler layer and Pydantic schemas;
* minimal authorized extension to `knowledge_assistant.core.SearchResult` (source field — ADR-031);
* minimal authorized extension to `knowledge_assistant.storage` (populate `SearchResult.source` at search time — ADR-031);
* minimal authorized extension to `knowledge_assistant.retrieval` reranker path (preserve `source` when rescoring — ADR-031);
* associated unit and integration tests;
* ADR entries and documentation updates.

### In Scope

* MCP handler functions (`tools.py`) with Pydantic request/response schemas;
* `search_documents` over injected `Retriever.retrieve(SearchQuery)`;
* `index_documents_preview` over `IndexingPipeline.preview_indexing`;
* `index_documents_apply` over `IndexingPipeline.index_documents` with approval enforcement;
* source attribution formatting: `SearchResult.source` → `SourceReferenceSchema` (ADR-031);
* `McpServerSettings` (default `top_k`, handler defaults — no transport config);
* `server.py` stub documenting deferred MCP SDK registration;
* unit tests: schema validation, formatting, approval enforcement, import boundaries;
* integration tests: handlers with fake `Retriever` and fake `IndexingPipeline`;
* ADR entries ADR-028 through ADR-034;
* updates to `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/PROGRESS.md` on completion.

---

## Non-Scope

This plan does **not** authorize:

* LangGraph agent implementation (Plan 12);
* MCP client or MCP SDK server runtime (Plan 12);
* `get_document` or `get_statistics` handlers;
* `VectorStore` read primitive extensions;
* CLI chat or interactive approval UX;
* LLM answer generation, query rewriting, or intent classification;
* real BGE embedding or reranker runtime;
* authentication, authorization, or distributed deployment;
* direct `qdrant_client` or `storage` imports in `mcp_server`;
* Pydantic models outside `mcp_server/schemas.py`;
* retrieval algorithm changes beyond preserving `SearchResult.source` through reranking;
* indexing algorithm changes;
* `ChunkMetadata` changes;
* URL indexing (`DOCUMENT_URL`, `DIRECTORY_URL` remain rejected by indexing until a future plan);
* live MCP stdio/networking tests;
* exception hierarchy rooted at `AppError` (deferred);
* agent conversation memory or durable MCP-side state.

---

## Architectural Decisions

The following decisions are **proposed** for this plan. Implementation must follow them; reopen only via plan revision.

### ADR-028 — MCP Server as Knowledge Boundary

**Status:** Proposed (to be accepted on implementation)

#### Context

`PROJECT.md` and `docs/ARCHITECTURE.md` position the Knowledge MCP Server as the system boundary between the agent and the knowledge subsystem. Plans 04–09 delivered storage, indexing, and retrieval. Plan 10 must deliver the **handler layer** that higher layers call — not the full transport stack.

#### Decision

* Implement the knowledge boundary in `knowledge_assistant.mcp_server`.
* Plan 10 delivers **handler functions and schemas** — the stable knowledge-access contract.
* MCP owns:
  * tool handler functions for Tier 1 capabilities;
  * Pydantic request/response validation (ADR-033);
  * mapping between Pydantic DTOs and core domain types;
  * enforcing the human approval gate before index mutation;
  * mapping `SearchResult.source` to MCP citation DTOs.
* MCP does **not** own:
  * MCP SDK server process or stdio transport (ADR-034);
  * conversation state;
  * retrieval quality;
  * chunking, embedding, or storage logic;
  * answer generation.
* Handlers are thin: validate → map → delegate → map → return.

#### Consequences

* Plan 12 wraps handlers with MCP SDK client/server without changing handler contracts.
* Handler tests run without MCP SDK or network I/O.
* The knowledge boundary is testable before agent work begins.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Agent calls `Retriever` directly | Violates documented architecture |
| Full MCP SDK server in Plan 10 | Couples boundary to transport before agent exists (ADR-034) |
| REST API instead of MCP handlers | Contradicts project stack; handlers are MCP-ready without SDK |

---

### ADR-029 — MCP Tools vs Resources Split

**Status:** Proposed (to be accepted on implementation)

#### Context

MCP supports tools and resources. Plan 10 must scope what the handler layer defines.

#### Decision

**Plan 10 defines three tool handlers** (Tier 1):

| Capability | Handler | Rationale |
| ---------- | ------- | --------- |
| Search | `search_documents` | Primary RAG grounding path |
| Index preview | `index_documents_preview` | Human-in-the-loop preview |
| Index apply | `index_documents_apply` | Approved index mutation |

**Deferred** (Tier 2 / Plan 12+):

* `get_document`, `get_statistics` handlers;
* MCP resources (`knowledge://…` URIs);
* MCP SDK tool registration in `server.py`.

When MCP SDK registration is added (Plan 12), Tier 1 handler names and schemas remain stable.

#### Consequences

* Plan 10 scope stays focused on knowledge access.
* Repository browsing does not block Plan 10 completion.
* `resources.py` documents deferred URIs; no implementation required.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Five tools in Plan 10 per ROADMAP wording | Conflates knowledge access with repository browsing; ROADMAP is informational |
| Resources for reads | No Tier 1 requirement; adds surface without agent need |

---

### ADR-030 — Human Approval Boundary for Index Modification

**Status:** Proposed (to be accepted on implementation)

#### Context

ADR-012 assigns approval enforcement to callers. MCP is the first external-facing caller for indexing.

#### Decision

* Split indexing into two handlers:
  * `index_documents_preview` — `IndexingPipeline.preview_indexing`; never mutates storage;
  * `index_documents_apply` — `IndexingPipeline.index_documents`; may mutate storage.
* `index_documents_apply` requires:

```python
approval_confirmed: bool  # must be exactly True
```

* When `approval_confirmed is not True`, raise `ApprovalRequiredError` **before** calling `index_documents`.
* When `rebuild=True`, `approval_confirmed=True` is still required.
* MCP must not call `input()` or block on interactive stdin.
* Indexing layer behavior unchanged (ADR-012).

#### Consequences

* Agents must deliberately approve index mutation.
* CLI (future) wraps preview → user prompt → apply.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Single combined index handler | Violates preview/approve flow in PROJECT.md |
| MCP prompts interactively | Untestable; violates ADR-012 |

---

### ADR-031 — Source Attribution Contract

**Status:** Proposed (to be accepted on implementation)

#### Context

`PROJECT.md` requires citations with document title, document path, section title, and line range. `SourceReference` is the canonical model (ADR-005). Payload fields already store title and path (ADR-005); `storage.mapping.payload_to_source_reference` already reconstructs `SourceReference` from payloads. `SearchResult` today carries only `Chunk` + `score`; `ChunkMetadata` intentionally holds structural fields (`document_id`, `section_title`, `line_range`, `chunk_index`) — not bibliographic fields.

#### Investigation — alternatives to `ChunkMetadata` extension

| Option | Assessment |
| ------ | ---------- |
| **A — Extend `ChunkMetadata` with `document_title` / `document_path`** | **Rejected.** Bibliographic fields are document-level denormalizations already on the storage payload (ADR-005). Duplicating them on every chunk metadata object forces indexing, storage mapping, and all chunk construction sites to change for data that exists only at persistence boundary. Wrong ownership layer. |
| **B — MCP imports `storage.mapping.payload_to_source_reference`** | **Rejected.** Search results do not carry raw payloads at MCP; violates MCP → storage dependency rule. |
| **C — Partial MCP citation from `ChunkMetadata` only** | **Rejected.** Omits `document_title` and `document_path`; fails PROJECT.md citation requirements. |
| **D — Add `source: SourceReference` to `SearchResult`; populate in storage at search time** | **Selected.** Minimal, targeted core extension. Storage already has payload and `payload_to_source_reference`. Retrieval passes `SearchResult` through unchanged. MCP maps `SearchResult.source` to Pydantic DTO. No `ChunkMetadata` or indexing changes. |
| **E — Separate document repository** | **Rejected** (ADR-005). |

#### Decision

* **Do not modify `ChunkMetadata`.**
* Add to `SearchResult`:

```python
source: SourceReference
```

* Populate `source` in `storage` when constructing `SearchResult` from Qdrant points (`search_dense`, `search_sparse`) via existing `payload_to_source_reference`.
* `Reranker` / `StubReranker` implementations must preserve `source` when emitting rescored `SearchResult` tuples (copy from input candidate).
* MCP `formatting.py` maps `SearchResult.source` → `SourceReferenceSchema`; MCP does **not** import from `storage`.
* `search_documents` returns: `chunk_id`, `text`, `score`, `source`.
* Scores are reranker scores when production wiring uses `RerankRetriever` (ADR-026). Document in handler/tool description; MCP does not reinterpret scores.
* MCP does not generate natural-language answers.

#### Consequences

* Full PROJECT.md citations in search responses without indexing churn.
* One new required field on `SearchResult`; test fixtures across retrieval/storage updated.
* Tier 2 `get_document` (deferred) can reuse the same `source` field on returned chunks when implemented later.

#### Alternatives Considered

See investigation table above.

---

### ADR-032 — MCP Dependency Boundaries

**Status:** Proposed (to be accepted on implementation)

#### Context

Plan 10 must not violate dependency flow. Tier 1 handlers need only retrieval and indexing.

#### Decision

**Allowed imports in `mcp_server` production code:**

| Dependency | Usage |
| ---------- | ----- |
| `knowledge_assistant.core.*` | Domain types (`SearchQuery`, `IndexingSource`, `SourceReference`, …) |
| `knowledge_assistant.retrieval.protocol.Retriever` | Search delegation |
| `knowledge_assistant.indexing.pipeline.IndexingPipeline` | Preview and index |
| `pydantic` | MCP boundary schemas only (`schemas.py`) |

**Forbidden imports in `mcp_server` production code:**

* `knowledge_assistant.storage` (any submodule)
* `qdrant_client`
* `mcp` SDK
* `langgraph`, `langchain*`, `openai`, `llama_index*`
* `knowledge_assistant.retrieval.dense`, `.sparse`, `.fusion`, `.rerank`, `.embeddings`
* `knowledge_assistant.llm`, `knowledge_assistant.agent`

**Assembly rule:** `RerankRetriever(FusionRetriever(...), StubReranker(), ...)` construction lives outside `mcp_server` (CLI bootstrap, Plan 12 wiring, test fixtures).

#### Consequences

* Plan 10 MCP package has no storage or transport coupling.
* Import-boundary tests enforce rules mechanically.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP depends on `VectorStore` for Tier 2 tools | Tier 2 deferred; would violate focus |
| MCP imports concrete `RerankRetriever` | Couples boundary to retrieval internals |

---

### ADR-033 — Pydantic Boundary Ownership

**Status:** Proposed (to be accepted on implementation)

#### Context

ADR-001 excludes Pydantic from `core`. Project Python standards recommend Pydantic for MCP contracts. Plan 10 must prevent schema leakage into lower layers.

#### Decision

* **Pydantic is permitted only in `knowledge_assistant.mcp_server.schemas.py`** (and tests for that module).
* `core`, `retrieval`, `indexing`, and `storage` remain dataclass/protocol-only — no Pydantic imports.
* Handler flow:

```text
Pydantic request  →  core domain type  →  delegate  →  core/domain result  →  Pydantic response
```

* `formatting.py` maps core types to Pydantic response models; it does not define alternate domain models.
* `SourceReferenceSchema` mirrors `SourceReference` fields for JSON serialization; it is not a replacement for the core type inside handlers (handlers read `SearchResult.source: SourceReference`).
* If `pydantic` is not yet a runtime dependency, add it in Plan 10 implementation for `mcp_server` only.

#### Consequences

* Clear boundary: JSON/tool contracts live in MCP; domain logic stays Pydantic-free below.
* Plan 11 (LLM) may introduce separate Pydantic schemas in `llm/` without affecting MCP or core.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Pydantic in `core` | Violates ADR-001 |
| Shared `schemas/` package | Premature; MCP owns its transport contract |
| Dataclass MCP DTOs | Weaker validation; inconsistent with project MCP standards |

---

### ADR-034 — MCP Handler Layer Without SDK Runtime

**Status:** Proposed (to be accepted on implementation)

#### Context

Plan 10 could deliver either (a) handler functions only, or (b) handlers plus a runnable MCP SDK server. The agent (Plan 12) is the first consumer that needs MCP transport.

#### Evaluation

| Approach | Pros | Cons |
| -------- | ---- | ---- |
| **Handlers + schemas only (selected)** | Testable without SDK/network; no new runtime dep; boundary complete before agent; handlers are what Plan 12 wraps | No standalone `uv run mcp-server` demo until Plan 12 |
| Handlers + MCP SDK server in Plan 10 | Runnable stdio server early | Adds `mcp` dependency and transport code before a client exists; mixes boundary with integration; SDK API churn affects Plan 10 |

#### Decision

* **Plan 10 implements handler functions and Pydantic schemas only.**
* **Plan 10 does not add the `mcp` SDK runtime dependency.**
* `server.py` is a **stub** documenting deferred SDK registration (target: Plan 12 agent integration).
* Plan 12 will:
  * add `mcp` SDK dependency;
  * register Tier 1 handlers as MCP tools;
  * implement MCP client in the agent;
  * optionally add Tier 2 tools if Plan 10b is complete.

**Architectural justification:** The knowledge-access **boundary** is defined by handler contracts (inputs, outputs, approval rules, attribution mapping) — not by stdio transport. Transport is an integration concern between agent and handlers. Delivering handlers first lets Plan 10 complete with full test coverage and stable contracts before MCP SDK versioning and session lifecycle enter scope.

#### Consequences

* Plan 10 validation uses direct handler invocation, not MCP subprocess tests.
* Plan 12 owns end-to-end MCP connectivity.
* Tier 1 handler signatures are the stable API surface.

#### Alternatives Considered

See evaluation table above.

---

## Design Evaluations

### 1. Production retriever wiring

**Decision:** Inject composed `RerankRetriever` from outside `mcp_server` (ADR-032).

### 2. Schema technology

**Decision:** Pydantic in `mcp_server/schemas.py` only (ADR-033).

### 3. Repository browse tools in Phase 5

**Decision:** Defer `get_document` and `get_statistics` to follow-up plan. ROADMAP Phase 5 lists them informationally; they are not required for search → ground → answer. Search returns chunk text and full `SourceReference` via ADR-031.

### 4. Indexing source inputs

```python
class IndexingSourceSchema(BaseModel):
    kind: Literal["file", "directory"]
    location: str
    recursive: bool = False
```

Map to core `IndexingSource`. URL kinds fail via indexing exceptions wrapped as MCP errors.

### 5. Score semantics in `search_documents`

**Decision:** Pass through `SearchResult.score` unchanged. Document reranker score semantics in handler docstring / future tool description.

---

## Proposed MCP Capabilities (Tier 1)

### Handler: `search_documents`

**Purpose:** Retrieve ranked chunks for grounding. Does not generate answers.

**Request (`SearchDocumentsRequest`):**

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `query` | `str` | yes | Non-empty after strip |
| `top_k` | `int` | no | Default from `McpServerSettings.default_top_k`; `>= 1` |

**Flow:** validate → `SearchQuery` → `retriever.retrieve` → map hits via `formatting.py`.

**Response (`SearchDocumentsResponse`):**

| Field | Type |
| ----- | ---- |
| `query` | `str` |
| `top_k` | `int` |
| `hits` | `list[SearchHitSchema]` |

**`SearchHitSchema`:** `chunk_id`, `text`, `score`, `source: SourceReferenceSchema`

---

### Handler: `index_documents_preview`

**Request (`IndexDocumentsPreviewRequest`):** `sources: list[IndexingSourceSchema]` (non-empty)

**Response (`IndexDocumentsPreviewResponse`):** `sources`, `document_count`, `chunk_count`, `replaces_existing`

**Flow:** map sources → `IndexingPipeline.preview_indexing` → response.

---

### Handler: `index_documents_apply`

**Request (`IndexDocumentsApplyRequest`):**

| Field | Type | Required |
| ----- | ---- | -------- |
| `sources` | `list[IndexingSourceSchema]` | yes |
| `rebuild` | `bool` | no (default `False`) |
| `approval_confirmed` | `bool` | yes — must be `True` |

**Response (`IndexDocumentsApplyResponse`):** `sources`, `document_count`, `chunk_count`, `upserted_count`, `rebuilt`

**Flow:** validate approval → `IndexingPipeline.index_documents(sources, rebuild=rebuild)`.

---

## Deferred Capabilities (Tier 2 — not Plan 10)

Document for backlog plan; do not implement:

### `get_document`

Fetch all chunks for a document path. Requires storage read primitive `VectorStore.get_chunks_by_document_path`. Not needed when search returns sufficient evidence and citations.

### `get_statistics`

Collection chunk/document counts. Requires `VectorStore.get_collection_statistics`. Operational diagnostic only.

---

## Module Layout

```text
mcp_server/
    __init__.py          # minimal public exports (handlers, settings)
    config.py            # McpServerSettings
    schemas.py           # Pydantic only — all MCP request/response models
    exceptions.py        # ApprovalRequiredError, stable error codes
    formatting.py        # core SourceReference / SearchResult → Pydantic DTOs
    tools.py             # Tier 1 handler functions (Plan 10 deliverable)
    resources.py         # deferred URI documentation stub
    server.py            # deferred MCP SDK registration stub (Plan 12)
```

**Authorized changes outside `mcp_server` (ADR-031 only):**

```text
core/retrieval.py           # SearchResult.source: SourceReference
storage/qdrant_store.py     # populate source at search time
storage/mapping.py            # (unchanged — reuse payload_to_source_reference)
retrieval/rerank.py           # preserve source in StubReranker / Reranker contract
```

**Explicitly not authorized in Plan 10:**

```text
core/chunk.py                 # no ChunkMetadata changes
storage/protocol.py           # no Tier 2 read methods
```

---

## Testing Strategy

### Unit Tests — `tests/unit/mcp_server/`

| Module | Focus |
| ------ | ----- |
| `test_schemas.py` | Pydantic validation |
| `test_formatting.py` | `SearchResult` → `SearchHitSchema`; `SourceReference` → `SourceReferenceSchema` |
| `test_tools_search.py` | Fake `Retriever` |
| `test_tools_indexing.py` | Fake `IndexingPipeline`; approval gate |
| `test_mcp_imports.py` | No forbidden imports; no Pydantic outside `schemas.py`; no `storage`, `mcp` |

### Integration Tests — `tests/integration/mcp_server/`

| Module | Focus |
| ------ | ----- |
| `test_handlers_integration.py` | Handler flows with fakes |
| `conftest.py` | Fake `Retriever`, `IndexingPipeline` |

### Cross-Layer Tests (ADR-031)

| Location | Focus |
| -------- | ----- |
| `tests/unit/storage/` | `SearchResult.source` populated on search |
| `tests/unit/retrieval/` | Reranker preserves `source` |

**Not required:** MCP SDK; stdio subprocess; Qdrant in MCP tests; Tier 2 handlers.

### Validation Commands

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

---

## Dependencies

**Plan 10 adds:**

* `pydantic` — runtime dependency for `mcp_server/schemas.py` only (if not already present)

**Plan 10 does not add:**

* `mcp` SDK (deferred to Plan 12 — ADR-034)
* `langgraph`, `openai`, `torch`, `transformers`, `sentence-transformers`

---

## Documentation Updates

On implementation completion:

* `docs/DECISIONS.md` — ADR-028 through ADR-034;
* `docs/ARCHITECTURE.md`:
  * MCP handler layer (Tier 1 tools);
  * dependency diagram without storage in `mcp_server`;
  * `SearchResult.source` attribution path;
  * note Tier 2 / SDK deferred;
* `docs/PROGRESS.md` — Plan 10 completion.

Do not update `docs/plans/backlog/ROADMAP.md` (informational).

---

## Implementation Steps

1. **`SearchResult.source`** — extend core type; populate in storage search paths; preserve through reranker (ADR-031).
2. **MCP schemas** — Pydantic models in `schemas.py` only (ADR-033).
3. **Formatting** — map core → Pydantic DTOs.
4. **Exceptions** — `ApprovalRequiredError`, error codes.
5. **Handlers** — `tools.py` Tier 1 functions with injected dependencies.
6. **Config** — `McpServerSettings`.
7. **Stubs** — `server.py`, `resources.py` document deferred work.
8. **Unit and integration tests** — handlers, formatting, import boundaries, ADR-031 cross-layer tests.
9. **Documentation** — ARCHITECTURE, DECISIONS, PROGRESS.
10. **Validation** — full quality suite.

---

## Acceptance Criteria

### MCP Package and Boundaries

- [x] `mcp_server` package per module layout
- [x] No `qdrant_client`, `storage`, `mcp` SDK, LangGraph, OpenAI, LlamaIndex in `mcp_server` production code
- [x] No Pydantic outside `mcp_server/schemas.py`
- [x] MCP does not call LLMs
- [x] Retriever injected via protocol only

### Source Attribution (ADR-031)

- [x] `ChunkMetadata` unchanged
- [x] `SearchResult.source: SourceReference` populated by storage on search
- [x] Reranker preserves `source` on rescored results
- [x] MCP maps `source` to `SourceReferenceSchema` with all four citation fields

### Handler: `search_documents`

- [x] Accepts `query`, optional `top_k`
- [x] Calls `Retriever.retrieve(SearchQuery)`
- [x] Returns ranked hits with `chunk_id`, `text`, `score`, `source`
- [x] Does not generate answers

### Handlers: `index_documents_preview` / `index_documents_apply`

- [x] Preview never mutates storage
- [x] Apply requires `approval_confirmed=True`
- [x] Apply calls `IndexingPipeline.index_documents` with `rebuild`

### Deferred (must not block Plan 10)

- [x] No `get_document` or `get_statistics` handlers
- [x] No `VectorStore` read primitive extensions
- [x] No MCP SDK server runtime
- [x] `server.py` stub documents Plan 12 SDK registration

### Tests and Validation

- [x] Unit tests for schemas, formatting, handlers, import boundaries
- [x] Integration tests with fake dependencies
- [x] Storage/reranker tests for `SearchResult.source`
- [x] Full validation commands pass

### Documentation

- [x] ADR-028 through ADR-034 in `docs/DECISIONS.md`
- [x] MCP handler layer in `docs/ARCHITECTURE.md`
- [x] Plan 10 recorded in `docs/PROGRESS.md`

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| `SearchResult` field addition breaks fixtures | Update retrieval/storage test helpers in same change set |
| Plan 12 expects runnable MCP server | ADR-034 documents handler-first; Plan 12 adds SDK |
| ROADMAP lists Tier 2 tools in Phase 5 | ROADMAP is informational; Tier 2 scoped to follow-up plan |
| Agent conflates search with answer generation | Handler docstrings state "returns evidence, not answers" |

---

## Follow-Up Work (Not Plan 10)

| Item | Target |
| ---- | ------ |
| Plan 10b — Knowledge Repository Browse | `get_document`, `get_statistics`, storage read primitives |
| Plan 11 — LLM boundary | OpenAI-compatible client |
| Plan 12 — LangGraph agent | MCP SDK server + client wrapping Tier 1 handlers |
| URL indexing sources | Future indexing plan |
| MCP resources | After Tier 2 or Plan 12 |
| Real BGE runtimes | Backlog |

---

## Checklist

- [x] Read AGENTS.md, PROJECT.md, ARCHITECTURE.md, DECISIONS.md
- [x] Implement `SearchResult.source` (ADR-031) — not `ChunkMetadata`
- [x] Implement MCP schemas (Pydantic boundary only)
- [x] Implement Tier 1 handlers with approval gate
- [x] Add stubs for deferred SDK and Tier 2
- [x] Add unit and integration tests
- [x] Run full validation suite
- [x] Update DECISIONS.md, ARCHITECTURE.md, PROGRESS.md
- [x] Move plan to `completed/` when acceptance criteria satisfied
