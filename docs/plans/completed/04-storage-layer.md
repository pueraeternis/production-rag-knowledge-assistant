# Plan 04 — Storage Layer

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 3 — Storage and Indexing

**Depends on:** [Plan 03 — Domain Models](../completed/03-domain-models.md)

---

## Objective

Establish the storage boundary between the domain layer (`knowledge_assistant.core`) and Qdrant.

This plan introduces a `VectorStore` protocol abstraction with a Qdrant-backed implementation. Indexing and retrieval layers will depend on `VectorStore`, not on Qdrant APIs directly. Qdrant remains an implementation detail hidden inside `knowledge_assistant.storage`.

After this plan is complete, the storage layer exposes collection lifecycle and chunk persistence primitives:

```python
store.create_collection()
store.upsert_chunks(...)
store.search_dense(...)
store.delete_collection()
```

All operations consume or return domain models where appropriate. Storage never generates embeddings.

---

## Scope

This plan authorizes storage-layer implementation only within `src/knowledge_assistant/storage/` and associated tests.

### In Scope

* `VectorStore` protocol definition;
* storage boundary types for upsert inputs and sparse vectors;
* domain ↔ Qdrant payload mapping (pure translation functions);
* Qdrant collection schema for `knowledge_chunks` with named `dense` and `sparse` vectors;
* `QdrantVectorStore` concrete implementation;
* storage configuration (Qdrant URL, collection name, dense vector size);
* storage-specific exception types;
* unit tests for mapping and validation logic;
* integration tests using in-memory Qdrant (`QdrantClient(":memory:")`);
* runtime dependency on `qdrant-client`;
* ADR entries for storage architecture decisions;
* brief `docs/ARCHITECTURE.md` update for the storage layer.

---

## Non-Scope

This plan does **not** authorize:

* indexing implementation (loading, parsing, chunking, embedding generation);
* retrieval implementation (dense orchestration beyond storage primitive, sparse search, fusion, reranking);
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* LlamaIndex integration;
* embedding model loading or inference (BAAI/bge-m3);
* reranking (BAAI/bge-reranker-v2-m3);
* CLI behavior;
* human-in-the-loop approval workflows (indexing plan owns orchestration; storage exposes destructive primitives only);
* separate document repository or document-level storage;
* Qdrant fusion, query prefetch, or reciprocal rank fusion at the database layer;
* `search_sparse` protocol method or sparse search implementation (deferred completely to Plan 07);
* scroll, count, or get-by-id APIs (deferred to MCP/statistics plans);
* Docker Compose or production Qdrant deployment;
* smoke tests against a live Qdrant instance;
* changes to `knowledge_assistant.core` domain models;
* exception hierarchy rooted at `AppError` (deferred to a future plan).

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-002 — VectorStore Protocol Abstraction

**Status:** Accepted (established by this plan)

#### Context

Indexing and retrieval layers need vector persistence and search without coupling to Qdrant client APIs. A stable internal contract allows testing with fakes and keeps Qdrant as a replaceable backend.

#### Decision

* Define `VectorStore` as a `typing.Protocol` in `storage/protocol.py`.
* Provide `QdrantVectorStore` as the concrete implementation in `storage/qdrant_store.py`.
* Indexing and retrieval layers depend on `VectorStore`, never on `qdrant_client` imports.
* Storage may import from `knowledge_assistant.core` for domain types.
* `knowledge_assistant.core` must not import from `knowledge_assistant.storage`.

#### Consequences

* Qdrant API changes are localized to the storage package.
* Retrieval and indexing tests can inject in-memory or fake vector stores.
* Static type checkers verify protocol conformance structurally.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Abstract base class (`abc.ABC`) | Protocol enables structural subtyping without inheritance; aligns with project typing style |
| Direct `qdrant_client` usage in retrieval/indexing | Violates component boundaries in `docs/ARCHITECTURE.md` |
| Repository pattern with separate document store | Out of scope; single collection with denormalized payloads is sufficient |

---

### ADR-003 — Single Collection Strategy

**Status:** Accepted (established by this plan)

#### Context

The project uses one synthetic knowledge base. Multi-tenant and multi-collection designs add complexity without educational value.

#### Decision

* Use exactly one Qdrant collection: `knowledge_chunks`.
* Collection name defaults to `knowledge_chunks` and is overridable via `StorageSettings` for tests.
* Point ID is derived from the `ChunkId` string value. `ChunkId` values must be convertible to Qdrant point identifiers. The concrete ID generation strategy is outside the scope of this plan and will be decided by the indexing plan.
* Index rebuild flow uses `delete_collection()` followed by `create_collection()` and `upsert_chunks()`; human approval is enforced by higher layers, not storage.

#### Consequences

* Simple mental model for the lecture demo.
* No cross-collection routing logic.
* Full index replacement is a storage primitive; partial document deletion is deferred.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Collection per document | Operational overhead; out of project scope |
| Collection per tenant | Multi-tenant is a non-goal per `PROJECT.md` |
| Auto-generated Qdrant point IDs separate from `ChunkId` | Requires extra ID mapping layer without benefit at this scale |

---

### ADR-004 — Named Vectors for Hybrid Retrieval

**Status:** Accepted (established by this plan)

#### Context

Future hybrid retrieval requires both dense semantic vectors and sparse lexical vectors on the same points. The collection schema must be designed now to avoid a breaking migration when sparse retrieval is implemented.

#### Decision

* Configure the collection with two named vector slots:

| Name | Type | Purpose |
| ---- | ---- | ------- |
| `dense` | dense `VectorParams` | Semantic embeddings (BAAI/bge-m3) |
| `sparse` | `SparseVectorParams` | Lexical sparse embeddings (BAAI/bge-m3) |

* Dense vector configuration:
  * `size`: `settings.dense_vector_size` (default `1024`, matching planned BAAI/bge-m3 output dimension)
  * `distance`: `COSINE`
* Sparse vector configuration:
  * default `SparseVectorParams()` (no IDF modifier in Plan 04; tuning deferred to Plan 07)
* `upsert_chunks` accepts both dense and sparse vectors as caller-provided inputs.
* `search_dense` queries only the `dense` named vector.
* Sparse search is **not** part of the Plan 04 protocol. `search_sparse` will be added to `VectorStore` in Plan 07 when sparse retrieval is implemented.

#### Consequences

* Plan 05 indexing can store both vector types in one upsert.
* Plan 06 dense retrieval can query the `dense` vector via `search_dense`.
* Plan 07 will extend the protocol with sparse search.
* Fusion remains outside Qdrant.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Dense-only collection, migrate later | Requires collection rebuild and reindex |
| Qdrant native hybrid fusion (`FusionQuery`) | Fusion must live in retrieval layer per project architecture |
| Separate collections for dense and sparse | Complicates point alignment and payload duplication |
| Declare `search_sparse` on protocol before implementation | Creates a misleading public contract for an unsupported operation |

---

### ADR-005 — Chunk Payload Schema

**Status:** Accepted (established by this plan)

#### Context

Retrieved chunks must reconstruct domain objects (`Chunk`, `ChunkMetadata`, and enough data to build `SourceReference`) without a separate document repository. Payload fields must support source attribution per `PROJECT.md`.

#### Decision

Store the following flat payload fields on every point:

| Payload key | Type | Maps to |
| ----------- | ---- | ------- |
| `document_id` | `str` | `ChunkMetadata.document_id` |
| `document_title` | `str` | `DocumentMetadata.title` / `SourceReference.document_title` |
| `document_path` | `str` | `DocumentMetadata.path` / `SourceReference.document_path` |
| `source_uri` | `str \| null` | `DocumentMetadata.source_uri` |
| `section_title` | `str` | `ChunkMetadata.section_title` / `SourceReference.section_title` |
| `start_line` | `int` | `ChunkMetadata.line_range.start_line` |
| `end_line` | `int` | `ChunkMetadata.line_range.end_line` |
| `chunk_index` | `int` | `ChunkMetadata.chunk_index` |
| `text` | `str` | `Chunk.text` |

* Document metadata is **denormalized** into each chunk payload at write time from `ChunkUpsertItem.document_metadata`.
* Do **not** introduce a separate document repository or document collection.
* Pure mapping functions in `storage/mapping.py` translate between Qdrant payloads and domain models.
* `SourceReference` is not stored as a nested object; it is reconstructible from payload fields via a dedicated mapper for callers that need citations.

#### Consequences

* Slightly larger payloads due to duplicated document fields across chunks.
* Retrieval can rebuild `Chunk` and `SourceReference` from a single point payload.
* Document title/path updates require re-upserting affected chunks (acceptable for this project).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate `documents` collection | Out of scope; adds join logic and consistency concerns |
| Store only `document_id`, resolve metadata elsewhere | Requires document repository not authorized by this plan |
| Embed `SourceReference` JSON blob | Duplicates domain model structure; harder to query and validate |

---

### ADR-006 — Storage Does Not Generate Embeddings

**Status:** Accepted (established by this plan)

#### Context

Embedding generation belongs to the indexing layer (write path) and retrieval layer (query path). Storage must remain a passive persistence and search primitive.

#### Decision

* Storage receives pre-computed `dense_vector` and `sparse_vector` on upsert.
* `search_dense` receives a pre-computed query vector and `top_k`; it does not accept query text.
* Storage must not import embedding libraries or call models.

#### Consequences

* Clear separation of concerns.
* Storage tests use synthetic vectors.
* Retrieval layer owns query embedding before calling storage.

---

## Design Evaluations

### VectorStore Protocol Surface

The protocol defines the minimum storage contract for indexing and dense retrieval primitives.

**Protocol:**

```python
class VectorStore(Protocol):
    def create_collection(self) -> None:
        """Create the knowledge_chunks collection with dense and sparse vector schema."""
        ...

    def delete_collection(self) -> None:
        """Delete the collection if it exists. Idempotent."""
        ...

    def collection_exists(self) -> bool:
        """Return whether the collection currently exists."""
        ...

    def upsert_chunks(self, items: tuple[ChunkUpsertItem, ...]) -> None:
        """Insert or update chunk points with vectors and payloads."""
        ...

    def search_dense(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
    ) -> tuple[SearchResult, ...]:
        """Search the dense named vector. Returns domain chunks with similarity scores."""
        ...
```

**Justification for each method:**

| Method | Rationale |
| ------ | --------- |
| `create_collection` | Required for index initialization and rebuild after `delete_collection` |
| `delete_collection` | Required for full index replacement; primitive used by indexing orchestration |
| `collection_exists` | Diagnostic helper for indexing and tests; avoids guessing from exceptions |
| `upsert_chunks` | Primary write path for indexing layer |
| `search_dense` | Primary read primitive for Plan 06 dense retrieval |

**Deliberately excluded from Plan 04:**

| Method | Deferred to |
| ------ | ----------- |
| `search_sparse` | Plan 07 — Sparse Retrieval (protocol extension and implementation) |
| `scroll` / `get_chunk_by_id` | Plan 10 — MCP `get_document` |
| `count_chunks` / `collection_info` | Plan 10 — MCP `get_statistics` |
| `delete_chunks_by_document_id` | Future indexing partial-update plan |

**`search_dense` does not accept `SearchQuery`:** `SearchQuery.text` is natural-language input. Embedding that text is retrieval-layer responsibility. Storage accepts `vector` and `top_k` only. This keeps storage free of embedding dependencies and makes unit testing trivial.

**`search_dense` returns `SearchResult`:** Each hit includes a reconstructed `Chunk` and a `float` score from Qdrant similarity. Scores are raw dense similarity, not fused or reranked values. Higher layers apply fusion and reranking.

---

### Qdrant Mapping Layer

**Module:** `storage/qdrant_store.py`

`QdrantVectorStore` owns all `qdrant_client` interaction:

| Responsibility | Detail |
| -------------- | ------ |
| Client lifecycle | Accept `QdrantClient` via constructor (dependency injection for tests) |
| Collection creation | `create_collection` with `vectors_config` and `sparse_vectors_config` |
| Point upsert | Batch `PointStruct` with named vectors and mapped payload |
| Dense search | `query_points` / `search` on `"dense"` vector only; no fusion |
| Collection deletion | `delete_collection`; swallow not-found for idempotency |
| Error translation | Map Qdrant client errors to storage exceptions |

**Constants module:** `storage/collection.py`

```python
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
DEFAULT_COLLECTION_NAME = "knowledge_chunks"
DEFAULT_DENSE_VECTOR_SIZE = 1024
```

Vector names are stable contracts referenced by future retrieval plans. Collection name and dense vector size are configuration values supplied via `StorageSettings`, not hardcoded at use sites.

---

### Collection Schema

Qdrant collection configured via `StorageSettings.collection_name` (default `knowledge_chunks`):

```python
client.create_collection(
    collection_name=settings.collection_name,
    vectors_config={
        DENSE_VECTOR_NAME: models.VectorParams(
            size=settings.dense_vector_size,
            distance=models.Distance.COSINE,
        ),
    },
    sparse_vectors_config={
        SPARSE_VECTOR_NAME: models.SparseVectorParams(),
    },
)
```

**`create_collection` behavior:**

* Succeeds when the collection does not exist.
* Raises `CollectionAlreadyExistsError` when the collection already exists.
* Does not silently recreate or modify an existing collection.

**`delete_collection` behavior:**

* Deletes the collection if present.
* Succeeds silently when the collection does not exist (idempotent).

---

### Payload Mapping

**Module:** `storage/mapping.py`

Pure functions with no I/O:

```python
def chunk_upsert_item_to_payload(item: ChunkUpsertItem) -> dict[str, object]: ...
def payload_to_chunk(payload: Mapping[str, object]) -> Chunk: ...
def payload_to_source_reference(payload: Mapping[str, object]) -> SourceReference: ...
```

**`chunk_upsert_item_to_payload`:**

* Reads `item.chunk` for chunk fields (`document_id`, `section_title`, line range, `chunk_index`, `text`).
* Reads `item.document_metadata` for `document_title`, `document_path`, and `source_uri`.
* Emits flat payload dict with the nine keys defined in ADR-005.
* `source_uri` is stored as JSON `null` when `None`.

**`payload_to_chunk`:**

* Validates required keys are present and types are correct.
* Reconstructs `LineRange`, `ChunkMetadata`, and `Chunk`.
* Uses `chunk_id` from the Qdrant point ID (passed separately), not from payload.
* Raises `PayloadMappingError` on missing or invalid fields.

**`payload_to_source_reference`:**

* Builds `SourceReference` from payload citation fields.
* Used by future MCP/retrieval layers; tested in Plan 04 for round-trip correctness.

**Round-trip invariant:** For any valid `ChunkUpsertItem`, mapping payload → `Chunk` (with original `chunk_id`) reproduces `item.chunk`, and payload citation fields match `item.document_metadata`.

---

### Domain ↔ Storage Translation Strategy

**Boundary type:** `ChunkUpsertItem` in `storage/models.py`

```python
@dataclass(frozen=True, slots=True)
class SparseVector:
    indices: tuple[int, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        # len(indices) == len(values); indices unique; all indices >= 0

@dataclass(frozen=True, slots=True)
class ChunkUpsertItem:
    chunk: Chunk
    document_metadata: DocumentMetadata
    dense_vector: tuple[float, ...]
    sparse_vector: SparseVector
```

**Why `ChunkUpsertItem` is not in `core`:** It couples domain `Chunk` and `DocumentMetadata` with infrastructure vectors required for Qdrant persistence. It is a storage write-model, not a domain entity.

**Write path (indexing → storage):**

```text
Indexing layer produces Chunk + DocumentMetadata + vectors
        ↓
ChunkUpsertItem(chunk, document_metadata, dense_vector, sparse_vector)
        ↓
QdrantVectorStore.upsert_chunks
        ↓
mapping.chunk_upsert_item_to_payload + Qdrant PointStruct
```

**Read path (storage → retrieval):**

```text
QdrantVectorStore.search_dense(vector, top_k)
        ↓
Qdrant scored points
        ↓
mapping.payload_to_chunk(point.payload) + point.score
        ↓
tuple[SearchResult, ...]
```

**Configuration:** `StorageSettings` in `storage/config.py`

```python
@dataclass(frozen=True, slots=True)
class StorageSettings:
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = DEFAULT_COLLECTION_NAME
    dense_vector_size: int = DEFAULT_DENSE_VECTOR_SIZE
```

| Field | Default | Source |
| ----- | ------- | ------ |
| `qdrant_url` | `http://localhost:6333` | `QDRANT_URL` env var |
| `collection_name` | `knowledge_chunks` | `DEFAULT_COLLECTION_NAME`; overridable in tests |
| `dense_vector_size` | `1024` | `DEFAULT_DENSE_VECTOR_SIZE`; matches planned BAAI/bge-m3 dimension |

Collection creation and vector dimension validation use `settings.dense_vector_size`, not a hardcoded constant.

Factory function:

```python
def create_qdrant_vector_store(
    settings: StorageSettings,
    *,
    client: QdrantClient | None = None,
) -> QdrantVectorStore: ...
```

---

### Testing Strategy

| Level | Location | What is tested | Qdrant usage |
| ----- | -------- | -------------- | ------------ |
| Unit | `tests/unit/storage/` | `SparseVector` validation; payload mapping from `ChunkUpsertItem` with `DocumentMetadata`; round-trip invariants; error cases for malformed payloads | None |
| Integration | `tests/integration/storage/` | Full lifecycle: create → upsert → search_dense → delete; collection_exists; error paths | `QdrantClient(":memory:")` per test |

**Unit tests (fast, no I/O):**

* `SparseVector` rejects mismatched indices/values lengths and negative indices.
* `chunk_upsert_item_to_payload` produces expected keys and values from `document_metadata`.
* `payload_to_chunk` reconstructs valid `Chunk` from payload dict.
* `payload_to_source_reference` reconstructs valid `SourceReference` from payload fields derived from `DocumentMetadata`.
* Malformed payloads raise `PayloadMappingError`.
* `dense_vector` length validation raises `VectorDimensionError` when length does not match `settings.dense_vector_size`.

**Integration tests (in-memory Qdrant):**

* `create_collection` creates retrievable schema.
* `create_collection` raises when collection already exists.
* `delete_collection` is idempotent.
* `upsert_chunks` + `search_dense` returns expected `SearchResult` ordered by score.
* `search_dense` returns empty tuple when collection is empty.
* `search_dense` raises when collection does not exist.
* Upserted sparse vectors are stored (verify via client-level retrieve or upsert round-trip); sparse search is not tested in Plan 04.

**Test helpers:** `tests/integration/storage/conftest.py` provides a `vector_store` fixture wrapping in-memory `QdrantVectorStore` with test `StorageSettings`.

**Not in scope:** smoke tests against Docker Qdrant; embedding model tests; retrieval pipeline tests; sparse search tests.

---

## Module Layout

```text
src/knowledge_assistant/storage/
    __init__.py           # public exports: VectorStore, QdrantVectorStore, ChunkUpsertItem, ...
    protocol.py           # VectorStore Protocol
    models.py             # ChunkUpsertItem, SparseVector
    mapping.py            # payload ↔ domain translation (pure)
    collection.py         # vector names, DEFAULT_COLLECTION_NAME, DEFAULT_DENSE_VECTOR_SIZE
    config.py             # StorageSettings, create_qdrant_vector_store factory
    exceptions.py         # StorageError and subclasses
    qdrant_store.py       # QdrantVectorStore implementation
```

Do not create `storage/utils/` or deep `qdrant/` subpackages unless a future plan requires it.

### Public API (`storage/__init__.py`)

Export intentionally:

* `VectorStore`
* `QdrantVectorStore`
* `ChunkUpsertItem`
* `SparseVector`
* `StorageSettings`
* `create_qdrant_vector_store`
* Storage exceptions used by callers

Do not re-export `qdrant_client` types from the package public API.

### Exception Hierarchy (storage-local)

```python
class StorageError(Exception): ...
class CollectionAlreadyExistsError(StorageError): ...
class CollectionNotFoundError(StorageError): ...
class VectorDimensionError(StorageError): ...
class PayloadMappingError(StorageError): ...
```

Root `AppError` integration is deferred.

---

## Dependencies

Add runtime dependency:

```toml
dependencies = [
    "qdrant-client>=1.12",
]
```

Pin compatible version in `uv.lock` during implementation.

Do **not** add: `llama-index`, `sentence-transformers`, `torch`, `langgraph`, `mcp`, or embedding libraries.

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-002 through ADR-006 from this plan;
* `docs/ARCHITECTURE.md` — expand Qdrant Storage section with `VectorStore` protocol, module layout, and dependency rule (indexing/retrieval → `VectorStore`, not Qdrant);
* `docs/PROGRESS.md` — record plan completion.

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Acceptance Criteria

- [x] `VectorStore` protocol is defined in `storage/protocol.py` with exactly five methods: `create_collection`, `delete_collection`, `collection_exists`, `upsert_chunks`, `search_dense`
- [x] `QdrantVectorStore` implements all five protocol methods
- [x] `search_sparse` is not declared on the Plan 04 protocol
- [x] Collection defaults to `knowledge_chunks` with named vectors `dense` (configurable size, default 1024, cosine) and `sparse`
- [x] Chunk payloads contain all nine fields defined in ADR-005
- [x] `ChunkUpsertItem` uses `document_metadata: DocumentMetadata` (not separate title/path/uri fields)
- [x] `upsert_chunks` accepts `tuple[ChunkUpsertItem, ...]` with caller-provided dense and sparse vectors
- [x] `search_dense` returns `tuple[SearchResult, ...]` with reconstructed `Chunk` domain objects
- [x] Collection creation and vector validation use `settings.dense_vector_size`
- [x] Storage does not generate embeddings or import embedding libraries
- [x] No separate document repository is introduced
- [x] Qdrant fusion is not used; `search_dense` performs single-vector similarity search only
- [x] `knowledge_assistant.core` has no imports from `knowledge_assistant.storage`
- [x] `qdrant-client` is the only new runtime dependency
- [x] Unit tests exist in `tests/unit/storage/`
- [x] Integration tests exist in `tests/integration/storage/` using in-memory Qdrant
- [x] ADR-002 through ADR-006 are transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents the storage layer boundary
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes with zero errors on `src/knowledge_assistant/storage/`
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into indexing or retrieval | Explicit non-scope; storage exposes primitives only |
| `ChunkId` incompatible with Qdrant point IDs | Document convertibility requirement; indexing plan decides concrete ID generation |
| Sparse vector schema mismatch with BGE-M3 output | Accept generic `SparseVector` boundary type; indexing plan validates model output format |
| Integration tests require Docker Qdrant | Use `QdrantClient(":memory:")` per Qdrant client docs and testing standards |
| Payload field drift from domain models | Round-trip unit tests; single mapping module; `DocumentMetadata` as upsert input |
| Vector dimension mismatch at runtime | Validate `len(dense_vector) == settings.dense_vector_size` before upsert/search |
| Denormalized document metadata stale after title change | Acceptable for demo; full reindex is the recovery path |
| Qdrant client API changes | Pin `qdrant-client` version; isolate usage in `qdrant_store.py` |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-002 through ADR-006 from this plan in `docs/DECISIONS.md`.
2. **Add dependency** — add `qdrant-client` to `pyproject.toml`; run `uv lock`.
3. **Create `collection.py`** — define vector names, `DEFAULT_COLLECTION_NAME`, and `DEFAULT_DENSE_VECTOR_SIZE`.
4. **Create `exceptions.py`** — define storage exception types.
5. **Create `models.py`** — implement `SparseVector` and `ChunkUpsertItem` with `document_metadata: DocumentMetadata`.
6. **Create `mapping.py`** — implement payload mapping functions; read document fields from `document_metadata`.
7. **Create `protocol.py`** — define `VectorStore` protocol (five methods only).
8. **Create `config.py`** — implement `StorageSettings` and `create_qdrant_vector_store` factory.
9. **Create `qdrant_store.py`** — implement `QdrantVectorStore` using `settings.dense_vector_size` for collection schema and validation.
10. **Update `storage/__init__.py`** — export public API.
11. **Add unit tests** — create `tests/unit/storage/` for models and mapping.
12. **Add integration tests** — create `tests/integration/storage/` with in-memory Qdrant fixtures.
13. **Update `docs/ARCHITECTURE.md`** — document storage layer boundary and module responsibilities.
14. **Run validation suite** — execute all four quality commands; fix issues until all pass.
15. **Update progress** — record completion in `docs/PROGRESS.md`.
16. **Verify non-scope compliance** — confirm no indexing, retrieval, MCP, embedding, LlamaIndex, or `search_sparse` code was introduced.

---

## Checklist

### Architectural Decisions (ADR-002 – ADR-006)

- [x] Transcribe ADR-002 (VectorStore Protocol) into `docs/DECISIONS.md`
- [x] Transcribe ADR-003 (Single Collection) into `docs/DECISIONS.md`
- [x] Transcribe ADR-004 (Named Vectors) into `docs/DECISIONS.md`
- [x] Transcribe ADR-005 (Chunk Payload Schema) into `docs/DECISIONS.md`
- [x] Transcribe ADR-006 (No Embedding Generation) into `docs/DECISIONS.md`

### Dependencies

- [x] Add `qdrant-client` to `pyproject.toml` dependencies
- [x] Update `uv.lock`
- [x] Confirm no unauthorized runtime dependencies added

### Collection Schema

- [x] Create `storage/collection.py` with `DEFAULT_COLLECTION_NAME`, `dense`, `sparse`, `DEFAULT_DENSE_VECTOR_SIZE`
- [x] `create_collection` configures cosine dense vector using `settings.dense_vector_size`
- [x] `create_collection` configures sparse vector params
- [x] `create_collection` raises `CollectionAlreadyExistsError` when collection exists
- [x] `delete_collection` is idempotent

### Boundary Types

- [x] Create `storage/models.py`
- [x] Implement `SparseVector` with indices/values validation
- [x] Implement `ChunkUpsertItem` with `chunk`, `document_metadata: DocumentMetadata`, and both vectors

### Payload Mapping

- [x] Create `storage/mapping.py`
- [x] Implement `chunk_upsert_item_to_payload` reading from `document_metadata`
- [x] Implement `payload_to_chunk`
- [x] Implement `payload_to_source_reference`
- [x] Payload includes all nine ADR-005 fields

### Protocol and Implementation

- [x] Create `storage/protocol.py` with `VectorStore` (five methods; no `search_sparse`)
- [x] Create `storage/config.py` with `StorageSettings` and factory
- [x] Create `storage/qdrant_store.py` with `QdrantVectorStore`
- [x] Implement `collection_exists`
- [x] Implement `upsert_chunks` with named dense and sparse vectors
- [x] Implement `search_dense` returning `tuple[SearchResult, ...]`
- [x] Vector validation uses `settings.dense_vector_size`

### Public API

- [x] Update `storage/__init__.py` with intentional exports
- [x] No `qdrant_client` types in public exports

### Unit Tests

- [x] Create `tests/unit/storage/` package
- [x] Test `SparseVector` validation
- [x] Test payload mapping from `DocumentMetadata` and round-trip
- [x] Test malformed payload error handling
- [x] Test vector dimension validation against `settings.dense_vector_size`

### Integration Tests

- [x] Create `tests/integration/storage/` package
- [x] Fixture for in-memory `QdrantVectorStore`
- [x] Test create → upsert → search_dense lifecycle
- [x] Test delete_collection idempotency
- [x] Test collection_exists
- [x] Test search on missing collection error

### Validation Workflow

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes

### Documentation

- [x] Update `docs/ARCHITECTURE.md` with storage layer description
- [x] Update `docs/PROGRESS.md` with storage layer milestone

### Non-Scope Verification

- [x] No indexing implementation
- [x] No retrieval implementation (beyond storage search primitive)
- [x] No `search_sparse` on protocol or implementation
- [x] No MCP implementation
- [x] No LangGraph implementation
- [x] No LlamaIndex integration
- [x] No embedding or reranking code
- [x] No document repository
- [x] No Qdrant fusion queries
- [x] `core/` does not import `storage/`
