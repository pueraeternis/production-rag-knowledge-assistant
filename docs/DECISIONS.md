# Architectural Decisions

This document records meaningful architectural decisions for Production RAG Knowledge Assistant.

For project vision and scope, see [PROJECT.md](../PROJECT.md).

---

## ADR Template

Use the following template for new decision records.

```markdown
## ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded | Deprecated

**Date:** YYYY-MM-DD

### Context

What problem or architectural question prompted this decision?

### Decision

What was decided?

### Consequences

What are the positive and negative outcomes of this decision?

### Alternatives Considered

What other options were evaluated and why were they rejected?
```

---

## Decision Log

### ADR-001: Domain Model Technology

**Status:** Accepted

**Date:** 2026-06-21

#### Context

The system needs shared domain types exchanged by indexing, retrieval, MCP, agent, and storage layers. These types must remain implementation-agnostic — independent from Qdrant, LlamaIndex, MCP, LangGraph, and OpenAI APIs.

#### Decision

* Core domain entities and value objects use `@dataclass(frozen=True, slots=True)`.
* Typed identifiers use `typing.NewType` for `DocumentId` and `ChunkId`.
* Pydantic, TypedDict, ORM models, and infrastructure-specific schemas are excluded from `knowledge_assistant.core`.
* Closed enumerations (`IndexingSourceKind`, `ApprovalStatus`) use stdlib `enum.Enum`.
* Domain models contain data and validation only; no business workflows or I/O.
* Core modules depend only on the Python standard library and other modules inside `knowledge_assistant.core`.

#### Consequences

* All layers can exchange typed, immutable domain objects without coupling to infrastructure.
* Static type checkers distinguish `DocumentId` from `ChunkId` and from arbitrary `str` fields.
* Pydantic remains available for future boundary layers (configuration, MCP contracts, LLM structured outputs) without polluting the core domain.
* Validation is limited to domain invariants in `__post_init__`; format validation for IDs is deferred to generating layers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Plain `str` for identifiers | No compile-time distinction between identifier types |
| Frozen dataclass wrapper for IDs | Unnecessary allocation for a single string field |
| `uuid.UUID` for identifiers | Couples identifier format to UUID; indexing may use content-derived IDs |
| Pydantic constrained types | Out of scope for core domain layer |
| TypedDict | No runtime validation; less suitable for immutable value objects with invariants |

---

### ADR-002: VectorStore Protocol Abstraction

**Status:** Accepted

**Date:** 2026-06-21

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

### ADR-003: Single Collection Strategy

**Status:** Accepted

**Date:** 2026-06-21

#### Context

The project uses one synthetic knowledge base. Multi-tenant and multi-collection designs add complexity without educational value.

#### Decision

* Use exactly one Qdrant collection: `knowledge_chunks`.
* Collection name defaults to `knowledge_chunks` and is overridable via `StorageSettings` for tests.
* Point ID is derived from the `ChunkId` string value. `ChunkId` values must be convertible to Qdrant point identifiers. The concrete ID generation strategy is outside the scope of Plan 04 and will be decided by the indexing plan.
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

### ADR-004: Named Vectors for Hybrid Retrieval

**Status:** Accepted

**Date:** 2026-06-21

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

### ADR-005: Chunk Payload Schema

**Status:** Accepted

**Date:** 2026-06-21

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

### ADR-006: Storage Does Not Generate Embeddings

**Status:** Accepted

**Date:** 2026-06-21

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

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Embedding generation inside storage | Violates component boundaries; couples persistence to model inference |
| Query text accepted by `search_dense` | Would require embedding dependencies in storage |
