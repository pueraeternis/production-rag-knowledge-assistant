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

---

### ADR-007: LlamaIndex Containment in Indexing Layer

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Document loading and chunking require a mature ingestion library. The project stack includes LlamaIndex, but external layers must remain independent from LlamaIndex types and metadata schemas.

#### Decision

* Use LlamaIndex for document loading and chunking inside `knowledge_assistant.indexing` only.
* Load local `.md` and `.txt` files with LlamaIndex `SimpleDirectoryReader` (`input_files=[path]`); a single input file must produce exactly one LlamaIndex document (zero or multiple documents raise `DocumentLoadError`).
* Chunk loaded document text with LlamaIndex `SentenceSplitter`.
* Read raw on-disk file text separately as an attribution mirror only (title extraction, section headings, offset lookup, `LineRange`); raw text is authoritative for line numbers, not LlamaIndex node metadata.
* Confine all LlamaIndex imports to `llamaindex_adapter.py`.
* Translate LlamaIndex outputs into core domain models before they leave the indexing package.
* Do not export LlamaIndex types from `indexing/__init__.py`.
* `knowledge_assistant.core`, `storage`, `retrieval`, `mcp_server`, `agent`, and `llm` must not import LlamaIndex.

#### Consequences

* LlamaIndex API changes are localized to the adapter module.
* Higher layers work exclusively with project domain types.
* Tests can mock or bypass the adapter while still validating pipeline orchestration.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Custom loaders/parsers without LlamaIndex | Reinvents chunking; contradicts project technology stack |
| LlamaIndex types in core domain models | Violates implementation-agnostic core layer per ADR-001 |
| LlamaIndex types in MCP contracts | Couples knowledge access API to ingestion library |

---

### ADR-008: Deterministic UUID5 ID Generation

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 04 requires `ChunkId` values to be valid UUID strings for Qdrant point ID conversion. IDs must be stable across re-indexing runs so the same source content produces the same identifiers.

#### Decision

* The indexing layer owns ID generation; storage does not generate IDs.
* Use `uuid.uuid5` exclusively. Do not use `uuid.uuid4` for document or chunk IDs.
* Define namespace constant `INDEXING_ID_NAMESPACE` in `indexing/ids.py`.
* **DocumentId:** `UUID5(INDEXING_ID_NAMESPACE, normalized_source_path)` as a string.
* **ChunkId:** `UUID5(INDEXING_ID_NAMESPACE, f"{document_id}|{chunk_index}|{text_digest}")` where `text_digest` is the lowercase hex SHA-256 digest of stripped chunk text.
* **Path normalization:** resolve to absolute path, normalize separators to forward slashes.
* Validate generated IDs are non-empty UUID strings before use.

#### Consequences

* Re-indexing the same file produces identical document and chunk IDs when source text and chunking configuration are unchanged.
* Content or chunking configuration changes produce new chunk IDs; full reindex is the recovery path.
* IDs satisfy Plan 04 `InvalidChunkIdError` prevention at upsert time.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Random UUID4 per index run | Breaks idempotent re-indexing; complicates deduplication |
| Sequential integer IDs | Not UUID-compatible with Qdrant point ID mapping |
| Content-only hash without document scope | Collisions across different documents with identical chunk text |

---

### ADR-009: EmbeddingProvider Boundary in Indexing Layer

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Storage receives pre-computed vectors and must not generate embeddings (ADR-006). Real BGE-M3 integration is deferred, but the indexing layer needs a stable embedding contract for write-path vector generation.

#### Decision

* Define `EmbeddingProvider` as a `typing.Protocol` in `indexing/embeddings.py`.
* Provide `StubEmbeddingProvider` for tests and development: hash-based, fixed dimension, no model runtime.
* `IndexingSettings.dense_vector_size` defaults to `1024`. Callers must configure indexing and storage consistently.
* Real BAAI/bge-m3 write-path implementation is deferred; it will implement the same protocol.
* Write-path embedding ownership is further specified in ADR-013.

#### Consequences

* Indexing tests run without GPU or model downloads.
* Future BGE-M3 indexing integration is a drop-in provider replacement.
* Query-path embedding ownership belongs to retrieval (ADR-013).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Embedding generation in storage | Violates ADR-006 |
| Shared `llm/` embedding module | LLM boundary is for model inference calls; embeddings are retrieval/indexing concerns |
| Hardcoded vectors in pipeline | No reusable contract for future BGE-M3 integration |

---

### ADR-010: Sparse Vector Placeholder Until Sparse Retrieval

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 04 collection schema requires both dense and sparse named vectors on every upsert (ADR-004). Real BGE-M3 sparse vectors and BM25 retrieval are deferred to Plan 07.

#### Decision

* Plan 05 attaches a constant sparse vector placeholder to every chunk at indexing time: `SparseVector(indices=(0,), values=(1.0,))`.
* The placeholder is valid per storage validation rules, deterministic, and carries no pseudo-lexical representation.
* Plan 07 replaces the constant with real sparse vectors; full reindex will be required.

#### Consequences

* Upserts satisfy storage schema without model dependencies.
* Dense retrieval in Plan 06 is unaffected.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Digest-derived pseudo-sparse vectors | Implies lexical structure that does not exist |
| Empty sparse vectors | Zero-length edge cases; may not exercise storage sparse path |
| Random sparse vectors per run | Non-deterministic; breaks reproducibility |
| Defer sparse slot entirely | Would require storage schema change contradicting ADR-004 |

---

### ADR-011: Local File Indexing Scope

**Status:** Accepted

**Date:** 2026-06-21

#### Context

The domain model defines four `IndexingSourceKind` values (Plan 03). The roadmap defers URL indexing to MCP plans. Plan 05 must bound ingestion scope explicitly.

#### Decision

* Plan 05 supports only `IndexingSourceKind.FILE` and `IndexingSourceKind.DIRECTORY`.
* Supported file extensions: `.md`, `.txt` (case-insensitive).
* Reject URL source kinds with `UnsupportedSourceKindError`.
* Reject unsupported extensions with `UnsupportedFileTypeError` on explicit file sources; skip silently during directory walks.
* `DocumentMetadata.source_uri` remains `None` for local files in Plan 05.

#### Consequences

* MCP URL indexing (Plan 10) will extend discovery without changing core domain enums.
* Indexing pipeline has a clear, testable local-filesystem boundary.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Implement URL fetching now | Out of Phase 3 scope; MCP plan owns remote sources |
| Support all text-like extensions | Expands parsing scope without plan authorization |
| Store `file://` URI in `source_uri` | Unnecessary for local demo; deferred |

---

### ADR-012: Human Approval Enforced by Callers

**Status:** Accepted

**Date:** 2026-06-21

#### Context

`PROJECT.md` requires user confirmation before modifying the index. Plan 04 exposes destructive storage primitives; orchestration must not bypass the approval boundary.

#### Decision

* `IndexingPipeline` implements `preview_indexing(...)` and `index_documents(...)`.
* The indexing service must not prompt the user or read interactive input.
* `index_documents(..., rebuild=True)` performs `delete_collection` → `create_collection` → `upsert_chunks`; the caller must obtain approval before invoking rebuild.
* `preview_indexing` returns `IndexingPreview` with `replaces_existing` from `collection_exists()` only.
* `ApprovalStatus` remains a core domain type; indexing does not transition approval state.

#### Consequences

* Indexing layer is reusable in automated tests without stdin mocking.
* MCP and CLI plans own interactive approval UX.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Built-in `input()` approval prompt | Couples library to interactive CLI; untestable in CI |
| Silent rebuild without preview | Violates human-in-the-loop requirement |

---

### ADR-013: Embedding Boundary Ownership

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Embedding generation appears on both the indexing write path and the retrieval query path. Without explicit ownership, layers could duplicate contracts or blur boundaries.

#### Decision

```text
Indexing owns write-path embeddings.
Retrieval owns query-path embeddings.
Storage owns neither.
```

* **Indexing** generates embeddings for document chunks before `VectorStore.upsert_chunks`.
* **Retrieval** generates embeddings for user queries before `VectorStore.search_dense` (Plan 06).
* **Storage** receives pre-computed vectors only (reinforces ADR-006).
* Future BAAI/bge-m3 integration must implement compatible provider contracts within respective layers.
* The `llm/` package is not the embedding owner for either path.

#### Consequences

* Plan 06 can define a retrieval-side query embedding boundary without ambiguity.
* Storage remains a passive vector store.
* Preview flows remain side-effect free: embedding runs only on the index path.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared embedding module used by indexing and retrieval | Couples read and write paths |
| Storage generates query embeddings | Violates ADR-006 and component boundaries |
| Single global `EmbeddingProvider` in `core/` | Pollutes domain layer with infrastructure concerns per ADR-001 |

---

### ADR-014: Dense Retrieval Boundary

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 04 exposes `VectorStore.search_dense(vector, top_k)` as a storage primitive that accepts pre-computed vectors. ADR-013 assigns query-path embedding ownership to retrieval. Higher layers (MCP, agent) must not embed queries or call storage search primitives directly.

#### Decision

* Dense retrieval is implemented in `knowledge_assistant.retrieval`.
* `DenseRetriever` is the public orchestration entry point for dense search.
* Responsibilities:
  * accept `SearchQuery` (text + `top_k`);
  * generate query embeddings via `QueryEmbeddingProvider`;
  * validate embedding dimension against `DenseRetrievalSettings.dense_vector_size`;
  * call `VectorStore.search_dense(vector=..., top_k=query.top_k)`;
  * wrap `tuple[SearchResult, ...]` in `RetrievalResult`.
* The retrieval layer must **not** expose vectors to callers.
* Callers work only with text queries via `SearchQuery`.
* `DenseRetriever` must **not** expose vector-accepting public APIs or passthrough wrappers around `search_dense`.
* Raw dense similarity scores from storage are returned unchanged in `SearchResult.score` (no fusion, no reranking).
* `DenseRetriever` is a **leaf retriever**; future plans may compose it behind higher-level orchestrators without changing its public API.

#### Consequences

* MCP and agent plans depend on `DenseRetriever.retrieve`, not on storage or embedding internals.
* Retrieval tests inject fake `VectorStore` and stub embedding providers without Qdrant.
* Future hybrid retrieval composes `DenseRetriever` alongside other leaf retrievers behind a higher orchestrator.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP calls `VectorStore.search_dense` directly | Violates component boundaries; pushes embedding into MCP |
| Storage accepts query text | Violates ADR-006; couples persistence to embedding models |
| Shared retriever returning raw vectors | Leaks infrastructure concerns to callers |
| Reuse indexing `EmbeddingProvider.embed_texts` for queries | Different ownership and call shape; blurs ADR-013 boundaries |

---

### ADR-015: QueryEmbeddingProvider

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-013 separates write-path embeddings (indexing) from query-path embeddings (retrieval). Indexing defines `EmbeddingProvider.embed_texts` for batch chunk embedding. Retrieval needs a query-focused contract with a single-text entry point.

#### Decision

* Define a retrieval-local `QueryEmbeddingProvider` protocol in `retrieval/embeddings.py` with `embed_query(text: str) -> tuple[float, ...]`.
* Do **not** reuse indexing `EmbeddingProvider` or import from `knowledge_assistant.indexing.embeddings`.
* Real BAAI/bge-m3 query-path implementation is deferred to a future plan; it will implement this protocol.
* `DenseRetriever` depends on `QueryEmbeddingProvider`, not on indexing types.
* `llm/` is not the embedding owner for the query path (reinforces ADR-013).

#### Consequences

* Indexing and retrieval embedding contracts evolve independently.
* Retrieval unit tests mock `embed_query` without indexing package imports.
* Future BGE-M3 integration replaces `StubQueryEmbeddingProvider` within retrieval only.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Reuse indexing `EmbeddingProvider` | Different method (`embed_texts` vs `embed_query`); couples read/write paths |
| Shared embedding module in `core/` | Pollutes domain layer per ADR-001 |
| `EmbeddingProvider` in retrieval with alias import from indexing | Violates layer ownership per ADR-013 |

---

### ADR-016: Stub Query Embeddings

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Real BGE-M3 integration is deferred. Retrieval still needs a deterministic, testable query embedding implementation aligned with indexing stub philosophy (ADR-009) and default vector dimension (1024).

#### Decision

* Provide `StubQueryEmbeddingProvider` in `retrieval/embeddings.py`.
* Requirements:
  * deterministic;
  * hash-based (SHA-256 expansion);
  * no model runtime;
  * default dimension `1024` (matches `DEFAULT_DENSE_VECTOR_SIZE`, indexing stub, and storage schema).
* Algorithm mirrors `StubEmbeddingProvider` philosophy from Plan 05:
  1. Compute SHA-256 digest of query text (UTF-8).
  2. Expand digest bytes deterministically to `dimension` float components in `[-1.0, 1.0]`.
  3. L2-normalize the vector for cosine distance compatibility.
  4. Return `tuple[float, ...]` with length exactly `dimension`.
* `StubQueryEmbeddingProvider` is a development/testing stub, not a production embedding model.
* No real BGE-M3, `sentence-transformers`, `torch`, or `transformers` in Plan 06.

#### Consequences

* Retrieval tests run without GPU or model downloads.
* End-to-end dense retrieval against stub-indexed content is possible when indexing and retrieval use matching dimensions and compatible stub algorithms.
* Plan 07+ sparse retrieval and Plan 08 fusion are unaffected.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Import `StubEmbeddingProvider` from indexing | Couples retrieval to indexing; violates ADR-015 |
| Random vectors per query | Non-deterministic; breaks reproducible tests |
| Zero vector placeholder | Poor cosine behavior; less representative of real embeddings |
| Real BGE-M3 in Plan 06 | Explicitly deferred; adds model runtime dependencies |

---

### ADR-017: Sparse Retrieval Boundary

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 04 defers `search_sparse` to Plan 07 (ADR-004). ADR-013 assigns query-path embedding ownership to retrieval. ADR-014 establishes the dense leaf-retriever pattern. Sparse retrieval must mirror dense retrieval without coupling retrieval to `storage.models`.

#### Decision

* Sparse retrieval is implemented in `knowledge_assistant.retrieval`.
* `SparseRetriever` is the public orchestration entry point for sparse search.
* Responsibilities:
  * accept `SearchQuery` (text + `top_k`);
  * generate query sparse embeddings via `SparseQueryEmbeddingProvider`;
  * validate sparse query representation via retrieval-local rules;
  * call `VectorStore.search_sparse(indices=..., values=..., top_k=query.top_k)`;
  * wrap `tuple[SearchResult, ...]` in `RetrievalResult`.
* The retrieval layer must **not** expose sparse vectors to callers.
* Callers work only with text queries via `SearchQuery`.
* `SparseRetriever` must **not** expose vector-accepting public APIs or passthrough wrappers around `search_sparse`.
* Raw sparse similarity scores from storage are returned unchanged in `SearchResult.score`.
* `SparseRetriever` is a **leaf retriever**; Plan 08 may compose it alongside `DenseRetriever` without changing its public API.
* `DenseRetriever` remains unchanged by Plan 07.

#### Consequences

* MCP and agent plans can depend on `SparseRetriever.retrieve`, not on storage or sparse embedding internals.
* Retrieval tests inject fake `VectorStore` and stub sparse providers without Qdrant.
* Plan 08 composes `DenseRetriever` and `SparseRetriever` as peer leaf retrievers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| MCP calls `VectorStore.search_sparse` directly | Violates component boundaries; pushes embedding into MCP |
| Storage accepts query text | Violates ADR-006; couples persistence to embedding models |
| `SparseRetriever` imports `storage.models.SparseVector` | Violates retrieval boundary per Plan 06 |
| Single `HybridRetriever` replacing leaf retrievers | Premature; fusion belongs in Plan 08 |

---

### ADR-018: SparseQueryEmbeddingProvider

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-015 defines `QueryEmbeddingProvider` for dense query embeddings. Sparse query embeddings require a separate contract with different output shape (indices + values, not fixed-dimension dense vectors). Indexing embedding providers must not be reused for the query path (ADR-013).

#### Decision

* Define retrieval-local types and protocol in `retrieval/sparse_vectors.py` and `retrieval/embeddings.py`:
  * `SparseQueryVector` — frozen dataclass with retrieval-owned validation;
  * `SparseQueryEmbeddingProvider` protocol with `embed_query(text: str) -> SparseQueryVector`.
* Do **not** import `storage.models.SparseVector` in retrieval production code.
* Do **not** import from `knowledge_assistant.indexing.embeddings`.
* Real BAAI/bge-m3 sparse query-path implementation is deferred; it will implement this protocol.
* `SparseRetriever` depends on `SparseQueryEmbeddingProvider`, not on indexing types.
* `llm/` is not the embedding owner for the sparse query path (reinforces ADR-013).

#### Consequences

* Indexing and retrieval sparse contracts evolve independently.
* Retrieval unit tests mock `embed_query` without indexing package imports.
* Future BGE-M3 integration replaces `StubSparseQueryEmbeddingProvider` within retrieval only.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Reuse indexing write-path sparse provider | Different ownership; couples read/write paths |
| Return `storage.models.SparseVector` from provider | Couples retrieval to storage write boundary types |
| Shared sparse module in `core/` | Pollutes domain layer per ADR-001 |
| Primitives only, no `SparseQueryVector` | Loses retrieval-local validation |

---

### ADR-019: Sparse Embedding Ownership

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-013 establishes dense embedding ownership. Sparse vectors have parallel write-path (indexing) and query-path (retrieval) responsibilities. Without explicit sparse ownership documentation, future plans could blur boundaries.

#### Decision

```text
Indexing owns write-path sparse embeddings (document chunks).  [future plan]
Retrieval owns query-path sparse embeddings (search queries).   [Plan 07]
Storage owns neither.
```

* **Retrieval (Plan 07)** generates sparse embeddings for user queries before `VectorStore.search_sparse`, via `SparseQueryEmbeddingProvider.embed_query`, using retrieval-local `SparseQueryVector` only.
* **Indexing (future plan)** will generate sparse embeddings for document chunks before `VectorStore.upsert_chunks`. Plan 07 does not implement indexing sparse generation. ADR-010 placeholder remains in place.
* **Storage** receives pre-computed sparse `indices` and `values` on search; receives `SparseVector` on upsert from indexing (unchanged). Storage does not generate sparse embeddings.
* The `llm/` package is not the sparse embedding owner for either path.

#### Consequences

* Plan 07 delivers query-path sparse retrieval without coupling to indexing implementation.
* Storage remains a passive vector store for sparse search primitives.
* A future sparse indexing plan can implement write-path generation independently.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Implement write-path sparse in Plan 07 | Violates one-capability-per-plan principle |
| Single shared `SparseEmbeddingProvider` in `core/` | Pollutes domain layer per ADR-001 |
| Storage generates query sparse vectors | Violates ADR-006 |

---

### ADR-020: Reindex Requirement for Future Sparse Migration

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-010 stores a constant sparse placeholder on every chunk. Meaningful sparse retrieval requires per-chunk sparse vectors aligned with query sparse encoding. This migration is a future concern, not a Plan 07 deliverable.

#### Decision

* When a future plan replaces ADR-010 placeholders with real per-chunk sparse encoding, a **full reindex** will be required.
* Recovery path (future): caller-approved `index_documents(..., rebuild=True)`.
* Partial sparse vector updates or in-place migration are **not** planned.
* Sparse retrieval against placeholder-indexed corpora produces meaningless sparse rankings until that future migration completes.
* Dense retrieval is unaffected (sparse slot ignored by `search_dense`).

#### Consequences

* Plan 07 can ship sparse retrieval infrastructure without blocking on indexing changes.
* Operators will need a future reindex window before production sparse retrieval against real corpora.
* Plan 08 fusion requires meaningful sparse data from a future indexing plan for useful hybrid results.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Bundle migration into Plan 07 | Scope expansion; mixes retrieval with indexing |
| In-place sparse vector patch | Out of scope; adds complexity |
| Lazy reindex on first sparse query | Violates human-in-the-loop |

---

### ADR-021: Fusion Retrieval Boundary

**Status:** Accepted

**Date:** 2026-06-21

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

### ADR-022: Retriever Protocol for Composition

**Status:** Accepted

**Date:** 2026-06-21

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

* `FusionRetriever.__init__` accepts two `Retriever` dependencies (`dense_retriever`, `sparse_retriever` by convention).
* Parameter names document conventional wiring; the protocol does **not** encode modality — any `Retriever` implementation is valid.
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

### ADR-023: Reciprocal Rank Fusion Algorithm

**Status:** Accepted

**Date:** 2026-06-21

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
