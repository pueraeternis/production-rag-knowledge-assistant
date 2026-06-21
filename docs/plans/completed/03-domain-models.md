# Plan 03 — Domain Models

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 2 — Core Domain

**Depends on:** [Plan 02 — Python Bootstrap](../completed/02-python-bootstrap.md)

---

## Objective

Define the shared domain model foundation for the entire system.

This plan establishes the core types that will be used by indexing, retrieval, MCP, agent, and storage layers. Domain models live in `knowledge_assistant.core` and must remain implementation-agnostic — independent from Qdrant, LlamaIndex, MCP, LangGraph, and OpenAI APIs.

After this plan is complete, all subsequent implementation plans can exchange data through typed, immutable domain objects instead of primitive collections or infrastructure-specific schemas.

---

## Scope

This plan authorizes domain model definition only within `src/knowledge_assistant/core/`.

### Technology Decision

All domain entities and value objects must use:

```python
@dataclass(frozen=True, slots=True)
```

**Do not use** in the core domain layer:

* Pydantic
* TypedDict
* ORM models
* Qdrant payload schemas
* MCP schemas
* API request/response schemas

Pydantic may appear in future boundary layers (configuration, MCP contracts, LLM structured outputs) but is explicitly out of scope for this plan.

### ADR-001 — Domain Model Technology (Accepted)

**Status:** Accepted (established by this plan)

This plan is the authoritative source for **ADR-001**. Implementation must follow this decision; it is not a separate design task.

**Decision:**

* Core domain entities and value objects use `@dataclass(frozen=True, slots=True)`.
* Typed identifiers use `typing.NewType` for `DocumentId` and `ChunkId`.
* Pydantic, TypedDict, ORM models, and infrastructure-specific schemas are excluded from `knowledge_assistant.core`.
* Closed enumerations (`IndexingSourceKind`, `ApprovalStatus`) use stdlib `enum.Enum`.

During implementation, record ADR-001 in `docs/DECISIONS.md` by transcribing this plan's technology decision and identifier strategy. Do not reinterpret or extend the decision during implementation.

### Core Design Rules

Domain models must satisfy all of the following:

| Rule | Requirement |
| ---- | ----------- |
| Immutability | All models are frozen dataclasses; no in-place mutation |
| Strong typing | Every field has an explicit type annotation; no `Any` |
| Value objects | Prefer dedicated types over primitive tuples (e.g. `LineRange`, not `tuple[int, int]`) |
| Validation | Use `__post_init__` for invariant checks; raise `ValueError` for invalid values |
| Domain dependencies | Core models may depend only on the Python standard library and other modules inside `knowledge_assistant.core` |
| No infrastructure | Must not import from `agent`, `retrieval`, `indexing`, `storage`, `mcp_server`, `llm`, `cli`, or third-party application libraries (Qdrant, LlamaIndex, MCP, LangGraph, OpenAI) |
| No services | Models contain data and validation only; no business workflows or I/O |
| Collections | Prefer `tuple` over `list` for sequence fields in frozen models |
| Paths | Store filesystem paths as `str`; do not use `pathlib.Path` in domain models |

### Identifier Strategy

Evaluate and adopt **typed identifiers** for `DocumentId` and `ChunkId`.

**Recommendation:** use `typing.NewType`.

```python
from typing import NewType

DocumentId = NewType("DocumentId", str)
ChunkId = NewType("ChunkId", str)
```

**Rationale:**

* Identifiers are opaque strings at runtime (UUIDs, content hashes, or stable slugs decided by later plans).
* `NewType` provides static type safety without runtime overhead or extra object allocation.
* Prevents accidental interchange of `DocumentId` and `ChunkId` at type-check time.
* Keeps identifiers distinct from arbitrary `str` fields such as titles or paths.

**Rejected alternatives:**

| Alternative | Why rejected |
| ----------- | ------------ |
| Plain `str` | No compile-time distinction between identifier types |
| Frozen dataclass wrapper | Unnecessary allocation for a single string field |
| `uuid.UUID` | Couples identifier format to UUID; indexing may use content-derived IDs |
| Pydantic constrained types | Out of scope for core domain layer |

Place identifier definitions in `core/identifiers.py`.

Validation in `__post_init__` for IDs (if any) is limited to non-empty string checks. Format validation (UUID, hash length) is deferred to the layer that generates IDs (indexing/storage plans).

### Module Layout

Organize domain models by concern:

```text
src/knowledge_assistant/core/
    __init__.py          # intentional public exports only
    identifiers.py       # DocumentId, ChunkId
    document.py          # Document, DocumentMetadata, DocumentContent
    chunk.py             # Chunk, ChunkMetadata
    source.py            # LineRange, SourceReference
    retrieval.py         # SearchQuery, SearchResult, RetrievalResult
    indexing.py          # IndexingSourceKind, IndexingSource, IndexingPreview, ApprovalStatus
```

Do not create catch-all modules (`utils`, `common`, `models.py`).

### Domain Types

#### Identifiers (`identifiers.py`)

| Type | Description |
| ---- | ----------- |
| `DocumentId` | Stable identifier for a knowledge-base document |
| `ChunkId` | Stable identifier for an indexed chunk |

#### Document Models (`document.py`)

**`DocumentMetadata`** — descriptive metadata for a document.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `title` | `str` | yes | Human-readable document title |
| `path` | `str` | yes | Source path relative to knowledge base or absolute path as indexed |
| `source_uri` | `str \| None` | no | Original URI when document was fetched from a URL |

Validation:

* `title` must be non-empty after stripping whitespace
* `path` must be non-empty after stripping whitespace

**`Document`** — document entity and metadata without loaded content.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `document_id` | `DocumentId` | yes | Stable document identifier |
| `metadata` | `DocumentMetadata` | yes | Document descriptive metadata |

`Document` represents the document entity. It does not carry document text. This keeps identity and metadata independent from whether content has been loaded, indexed, or retrieved.

**`DocumentContent`** — document text payload, separate from entity metadata.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `document_id` | `DocumentId` | yes | Identifier of the document this content belongs to |
| `content` | `str` | yes | Full document text |

Validation:

* `content` may be empty (edge case for placeholder documents); no minimum length enforced at domain layer

**Rationale for separation:** coupling `Document` with `content` ties document identity and metadata to loaded payload state. Separating `DocumentContent` keeps the model extensible for future storage and retrieval scenarios where metadata is known before content is fetched, or content is loaded on demand.

#### Chunk Models (`chunk.py`)

**`ChunkMetadata`** — positional and structural metadata for a chunk.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `document_id` | `DocumentId` | yes | Parent document |
| `section_title` | `str` | yes | Heading or section name; use empty string if no section |
| `line_range` | `LineRange` | yes | Line span within source document |
| `chunk_index` | `int` | yes | Zero-based position of chunk within document |

Validation:

* `chunk_index` must be `>= 0`

**`Chunk`** — an indexed fragment of a document.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `chunk_id` | `ChunkId` | yes | Stable chunk identifier |
| `metadata` | `ChunkMetadata` | yes | Chunk structural metadata |
| `text` | `str` | yes | Chunk text content |

Validation:

* `text` must be non-empty after stripping whitespace

#### Source Models (`source.py`)

**`LineRange`** — value object for source line attribution.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `start_line` | `int` | yes | First line (1-based, inclusive) |
| `end_line` | `int` | yes | Last line (1-based, inclusive) |

Validation:

* `start_line` must be `>= 1`
* `end_line` must be `>= start_line`

**`SourceReference`** — canonical citation and display model per [PROJECT.md](../../../PROJECT.md).

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `document_title` | `str` | yes | Display title |
| `document_path` | `str` | yes | File path for user inspection |
| `section_title` | `str` | yes | Section heading; empty string if none |
| `line_range` | `LineRange` | yes | Lines cited |

Validation:

* `document_title` and `document_path` must be non-empty after stripping whitespace

**Architectural note — `SourceReference` purpose:**

`SourceReference` is the canonical citation/display model used for answer grounding and user-visible source attribution.

It is intentionally distinct from:

* `DocumentMetadata` — indexing and document identity context
* `ChunkMetadata` — chunk structure and positional context within a document

Even though some fields overlap (titles, paths, section names, line ranges), the types serve different concerns:

| Type | Concern |
| ---- | ------- |
| `DocumentMetadata` | What a document is in the knowledge base |
| `ChunkMetadata` | Where a chunk sits within a document |
| `SourceReference` | What the user sees when inspecting an answer's sources |

`SourceReference` exists for presentation and explainability, not for indexing or storage. Later layers map `Chunk` / `ChunkMetadata` (and document metadata) to `SourceReference` at boundaries; mapping logic is not part of this plan.

#### Retrieval Models (`retrieval.py`)

**`SearchQuery`** — input to the retrieval layer.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `text` | `str` | yes | Query text |
| `top_k` | `int` | yes | Maximum results to return |

Validation:

* `text` must be non-empty after stripping whitespace
* `top_k` must be `>= 1`

Default `top_k` values are chosen by calling layers (agent, MCP); the domain model does not embed defaults.

**`SearchResult`** — a single retrieved chunk with ranking score.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `chunk` | `Chunk` | yes | Retrieved domain chunk |
| `score` | `float` | yes | Relevance score after fusion/reranking |

Retrieval returns retrieved domain objects plus ranking information. Source attribution is a separate concern and is not embedded in `SearchResult`. Callers that need user-facing citations derive `SourceReference` from the returned `Chunk` (and related document metadata) at a higher layer.

**`RetrievalResult`** — aggregate output of a retrieval operation.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `query` | `SearchQuery` | yes | Query that produced these results |
| `results` | `tuple[SearchResult, ...]` | yes | Ordered results (highest relevance first) |

Validation:

* `results` length must be `<= query.top_k`

Empty `results` is valid (no matches).

#### Indexing Models (`indexing.py`)

**`IndexingSourceKind`** — explicit category of an indexing source per [docs/plans/backlog/ROADMAP.md](../backlog/ROADMAP.md).

Use `enum.Enum` (stdlib) for this closed set of values:

| Member | Meaning |
| ------ | ------- |
| `FILE` | Single file on the local filesystem |
| `DIRECTORY` | Local directory; may be walked recursively |
| `DOCUMENT_URL` | URL pointing to a single document |
| `DIRECTORY_URL` | URL pointing to a directory listing or prefix |

The domain model represents source category explicitly rather than relying on string inspection in later layers.

**`IndexingSource`** — describes where documents originate for indexing.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `kind` | `IndexingSourceKind` | yes | Source category |
| `location` | `str` | yes | File path, directory path, or URL |
| `recursive` | `bool` | yes | Whether directory sources are walked recursively |

Validation:

* `location` must be non-empty after stripping whitespace

`recursive` is meaningful for `DIRECTORY` and `DIRECTORY_URL` kinds; for `FILE` and `DOCUMENT_URL` it should be `False`.

**`IndexingPreview`** — summary shown before human approval of index changes.

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `sources` | `tuple[IndexingSource, ...]` | yes | Sources proposed for indexing |
| `document_count` | `int` | yes | Number of documents that would be indexed |
| `chunk_count` | `int` | yes | Number of chunks that would be created |
| `replaces_existing` | `bool` | yes | Whether operation replaces the current index |

Validation:

* `document_count` must be `>= 0`
* `chunk_count` must be `>= 0`
* `sources` must be non-empty

**`ApprovalStatus`** — human-in-the-loop decision for destructive indexing operations.

Use `enum.Enum` (stdlib) for this closed set of values:

| Member | Meaning |
| ------ | ------- |
| `PENDING` | Awaiting user decision |
| `APPROVED` | User approved the operation |
| `REJECTED` | User rejected the operation |

`IndexingSourceKind` and `ApprovalStatus` use stdlib `Enum` because they represent fixed enumerations with no associated data. All other domain types in this plan use frozen dataclasses.

### Public API Surface

`core/__init__.py` exports the domain types listed above as the stable public API.

Other packages import from `knowledge_assistant.core` (or submodules) — not by reaching into internal module paths from outside `core`.

Keep exports intentional and minimal; do not re-export stdlib types.

### Unit Tests

Add unit tests under `tests/unit/core/` covering:

* valid construction of every domain type;
* `__post_init__` validation failures (invalid line ranges, empty required strings, `top_k < 1`, etc.);
* immutability (attempted mutation raises `FrozenInstanceError`);
* `IndexingSourceKind` and `ApprovalStatus` enum membership.

Tests validate domain invariants only — no Qdrant, LlamaIndex, MCP, or LLM dependencies.

### Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-001 from this plan (domain model technology and identifier strategy);
* `docs/PROGRESS.md` — record plan completion;
* `docs/ARCHITECTURE.md` — add brief `core/` domain layer description if not already present (types only, no new components).

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Non-Scope

This plan does **not** authorize:

* retrieval implementation (dense, sparse, fusion, reranking);
* indexing implementation (loading, parsing, chunking, embedding);
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* Qdrant integration or storage logic;
* LlamaIndex integration;
* embedding generation;
* reranking;
* CLI behavior;
* API or MCP request/response schemas;
* persistence models or Qdrant payload mapping;
* repositories or data access objects;
* services, factories, or business workflows;
* ID generation algorithms;
* mapping functions between domain and infrastructure types;
* configuration loading;
* exception hierarchy (`AppError` and subclasses — future plan);
* application runtime dependencies beyond existing dev tooling.

Boundary-layer Pydantic schemas that translate to/from these domain types are deferred to the plans that own those boundaries (MCP, LLM, configuration).

---

## Acceptance Criteria

- [x] `DocumentId` and `ChunkId` are defined using `NewType` in `core/identifiers.py`
- [x] All dataclass domain types use `@dataclass(frozen=True, slots=True)`
- [x] All domain types listed in Scope are implemented with fields and validation as specified
- [x] `Document` and `DocumentContent` are separate types (entity/metadata vs payload)
- [x] `SearchResult` contains `chunk: Chunk` and `score: float` only (no embedded source attribution)
- [x] `IndexingSourceKind` is implemented as a stdlib `Enum` with `FILE`, `DIRECTORY`, `DOCUMENT_URL`, `DIRECTORY_URL`
- [x] `IndexingSource` includes `kind: IndexingSourceKind` in addition to `location`
- [x] `ApprovalStatus` is implemented as a stdlib `Enum` with `PENDING`, `APPROVED`, `REJECTED`
- [x] Core domain modules depend only on stdlib and other `knowledge_assistant.core` modules
- [x] `core/__init__.py` exports the public domain API
- [x] Unit tests exist in `tests/unit/core/` and cover validation and immutability
- [x] ADR-001 is transcribed into `docs/DECISIONS.md` per the accepted decision in this plan
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes with zero errors on `src/knowledge_assistant/core/`
- [x] `uv run pytest` passes
- [x] No application runtime dependencies added to `pyproject.toml`
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into retrieval or indexing logic | Explicit non-scope; models are data-only |
| Pydantic introduced in core for convenience | Technology decision and ADR-001 forbid Pydantic in core |
| Python standards rule suggests Pydantic for retrieval models | ADR-001 clarifies domain vs boundary layer; update `.cursor/rules/01-python-standards.mdc` in a follow-up if needed |
| Over-engineered model hierarchy | Flat module layout; only types required by roadmap and PROJECT.md |
| Identifier format locked in too early | IDs are opaque strings; format left to indexing/storage plans |
| `SourceReference` overlaps `DocumentMetadata` / `ChunkMetadata` fields | Intentional separation: presentation/explainability vs indexing/storage; mapping deferred to boundary layers |
| `SearchResult` creates dependency from `retrieval` to `chunk` module | Allowed under domain dependency rule; both modules live in `core/` |
| Frozen dataclasses with mutable defaults | Use tuples; no mutable default fields |
| Missing validation allows invalid state downstream | Unit tests for every `__post_init__` invariant |

---

## Implementation Steps

1. **Transcribe ADR-001** — record the accepted domain model technology decision from this plan in `docs/DECISIONS.md`.
2. **Create `identifiers.py`** — define `DocumentId` and `ChunkId` with `NewType`.
3. **Create `source.py`** — implement `LineRange` and `SourceReference` with validation (foundation for other models).
4. **Create `document.py`** — implement `DocumentMetadata`, `Document`, and `DocumentContent`.
5. **Create `chunk.py`** — implement `ChunkMetadata` and `Chunk`.
6. **Create `retrieval.py`** — implement `SearchQuery`, `SearchResult` (`chunk` + `score`), and `RetrievalResult`.
7. **Create `indexing.py`** — implement `IndexingSourceKind`, `IndexingSource`, `IndexingPreview`, and `ApprovalStatus`.
8. **Update `core/__init__.py`** — export public domain API.
9. **Add unit tests** — create `tests/unit/core/` with validation and immutability tests for each type.
10. **Run validation suite** — execute all four quality commands; fix issues until all pass.
11. **Update architecture documentation** — brief `core/` description in `docs/ARCHITECTURE.md` if needed.
12. **Update progress** — record completion in `docs/PROGRESS.md`.
13. **Verify non-scope compliance** — confirm no infrastructure code, services, or runtime dependencies were introduced.

---

## Checklist

### Architectural Decision (ADR-001)

- [x] Transcribe ADR-001 from this plan into `docs/DECISIONS.md`
- [x] Confirm implementation follows accepted ADR-001 (frozen dataclasses, `NewType` identifiers, no Pydantic in core)

### Identifiers

- [x] Create `core/identifiers.py`
- [x] Define `DocumentId = NewType("DocumentId", str)`
- [x] Define `ChunkId = NewType("ChunkId", str)`

### Source Models

- [x] Create `core/source.py`
- [x] Implement `LineRange` with 1-based line validation
- [x] Implement `SourceReference` with required field validation

### Document Models

- [x] Create `core/document.py`
- [x] Implement `DocumentMetadata`
- [x] Implement `Document` (entity + metadata only)
- [x] Implement `DocumentContent` (document_id + content payload)

### Chunk Models

- [x] Create `core/chunk.py`
- [x] Implement `ChunkMetadata`
- [x] Implement `Chunk`

### Retrieval Models

- [x] Create `core/retrieval.py`
- [x] Implement `SearchQuery`
- [x] Implement `SearchResult` with `chunk: Chunk` and `score: float`
- [x] Implement `RetrievalResult`

### Indexing Models

- [x] Create `core/indexing.py`
- [x] Implement `IndexingSourceKind` enum (`FILE`, `DIRECTORY`, `DOCUMENT_URL`, `DIRECTORY_URL`)
- [x] Implement `IndexingSource` with `kind`, `location`, and `recursive`
- [x] Implement `IndexingPreview`
- [x] Implement `ApprovalStatus` enum

### Public API

- [x] Update `core/__init__.py` with intentional exports
- [x] Verify no business logic or side effects in `__init__.py`

### Unit Tests

- [x] Create `tests/unit/core/` package
- [x] Test valid construction for each domain type
- [x] Test validation failures for each `__post_init__` rule
- [x] Test frozen dataclass immutability
- [x] Test `IndexingSourceKind` enum values
- [x] Test `ApprovalStatus` enum values

### Validation Workflow

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes

### Documentation

- [x] Update `docs/ARCHITECTURE.md` with core domain layer description (if needed)
- [x] Update `docs/PROGRESS.md` with domain models milestone

### Non-Scope Verification

- [x] No imports from `agent`, `retrieval`, `indexing`, `storage`, `mcp_server`, `llm`, or `cli` in `core/`
- [x] No indexing implementation
- [x] No MCP implementation
- [x] No LangGraph implementation
- [x] No Qdrant integration
- [x] No LlamaIndex integration
- [x] No embedding or reranking code
- [x] No CLI behavior
- [x] No API/MCP schemas
- [x] No persistence or repository code
- [x] No services or workflows
- [x] No new runtime dependencies in `pyproject.toml`
