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

---

### ADR-024: Reranking Boundary

**Status:** Accepted

**Date:** 2026-06-21

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

### ADR-025: Reranker Protocol

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 08 introduced `Retriever` for composable orchestration. Reranking is a separate concern from candidate retrieval: it scores and reorders already-retrieved `SearchResult` tuples. A dedicated protocol enables stub and future real cross-encoder implementations without coupling `RerankRetriever` to model runtimes.

#### Decision

* Define retrieval-local `Reranker` protocol in `retrieval/rerank.py` with `rerank(query: SearchQuery, candidates: tuple[SearchResult, ...]) -> tuple[SearchResult, ...]`.
* `RerankRetriever.__init__` accepts one `Retriever` and one `Reranker` via keyword-only parameters `base_retriever`, `reranker`, and `settings`.
* Parameter name `base_retriever` documents conventional wiring (typically `FusionRetriever`); the protocol does **not** encode retriever kind — any `Retriever` implementation is valid.
* `RerankRetriever` depends on `Retriever` and `Reranker`, not on `VectorStore` or embedding providers.
* Plan 09 provides `StubReranker` as the deterministic development/test implementation.
* **Candidate preservation (Plan 09 contract):** every `Reranker` implementation must return exactly `len(candidates)` results — rerankers do not add or remove candidates; they only rescale scores and reorder.
* **Contract enforcement:** `RerankRetriever` validates `len(reranked) == len(candidates)` when candidates are non-empty. Violations raise `ValueError` (no new exception types; no `assert` in production code).
* `Reranker.rerank` accepts the **caller** `SearchQuery`, not the expanded candidate query.

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

### ADR-026: Reranked Score Semantics and Candidate Pool

**Status:** Accepted

**Date:** 2026-06-21

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

* Every `Reranker` implementation must satisfy `len(output) == len(candidates)` for Plan 09.
* The **only** candidate reduction permitted in Plan 09 is `RerankRetriever` final truncation to `query.top_k` after `Reranker.rerank` returns.
* Score-threshold filtering, confidence cutoffs, and reranker-side candidate dropping are **not** part of the Plan 09 contract.

**Contract enforcement:**

* `RerankRetriever` validates `len(reranked) == len(candidates)` when `len(candidates) > 0`.
* Violations raise `ValueError`. Do not use `assert` for production correctness.

**Fewer candidates than requested from base retriever:**

* When the base retriever returns fewer than `candidate_top_k` results, rerank **all returned candidates**; do not error or pad.

**Deterministic ordering guarantee:**

For identical `query` and `candidates` inputs, reranking output must be **fully deterministic** — identical scores and ordering on every invocation.

**Fusion candidate pool independence:**

* Fusion candidate expansion (`FusionRetrievalSettings.leaf_top_k_multiplier`) and reranking candidate expansion (`RerankRetrievalSettings.candidate_top_k_multiplier`) are **independent**.
* `RerankRetriever` controls only the `top_k` it forwards to its injected `base_retriever`.

**Batch shape:**

* `Reranker.rerank` processes **one query and its full candidate tuple** in a single call (single-query batch).

#### Consequences

* Reranking behavior is fully testable with hand-computed score expectations for `StubReranker`.
* Expanding the candidate pool improves reranker recall when fusion ranks a relevant chunk outside the final `top_k`.
* Operators can tune `candidate_top_k_multiplier` without code changes.
* Contract violations surface immediately as `ValueError` from `RerankRetriever`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Rerank with `query.top_k` unchanged on base retriever | Reduces reranker benefit when fusion ordering places good chunks at the tail |
| Preserve RRF score alongside reranker score | Requires core model extension; deferred |
| Per-candidate `rerank_one` API | More round trips; harder to swap in batch cross-encoders later |
| Non-deterministic tie-breaking | Breaks reproducible tests and lecture demo expectations |
| Trust reranker contract without `RerankRetriever` validation | Silent contract violations; rejected in favor of fail-fast `ValueError` |

---

### ADR-027: Future BGE Cross-Encoder Reranker Integration

**Status:** Accepted (documentation only — no Plan 09 implementation)

**Date:** 2026-06-21

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

### ADR-028: MCP Server as Knowledge Boundary

**Status:** Accepted

**Date:** 2026-06-21

#### Context

`PROJECT.md` and `docs/ARCHITECTURE.md` position the Knowledge MCP Server as the system boundary between the agent and the knowledge subsystem. Plans 04–09 delivered storage, indexing, and retrieval. Plan 10 delivers the **handler layer** that higher layers call — not the full transport stack.

#### Decision

* Implement the knowledge boundary in `knowledge_assistant.mcp_server`.
* Plan 10 delivers **handler functions and schemas** — the stable knowledge-access contract.
* MCP owns tool handler functions, Pydantic validation, domain mapping, human approval enforcement, and citation DTO mapping.
* MCP does not own MCP SDK transport, conversation state, retrieval algorithms, chunking, embedding, storage logic, or answer generation.
* Handlers are thin: validate → map → delegate → map → return.

#### Consequences

* Plan 12 wraps handlers with MCP SDK client/server without changing handler contracts.
* Handler tests run without MCP SDK or network I/O.
* The knowledge boundary is testable before agent work begins.

---

### ADR-029: MCP Tools vs Resources Split

**Status:** Accepted

**Date:** 2026-06-21

#### Context

MCP supports tools and resources. Plan 10 must scope what the handler layer defines.

#### Decision

**Plan 10 defines three tool handlers** (Tier 1): `search_documents`, `index_documents_preview`, `index_documents_apply`.

**Deferred** (Tier 2 / Plan 12+): `get_document`, `get_statistics`, MCP resources (`knowledge://…` URIs), MCP SDK tool registration in `server.py`.

When MCP SDK registration is added (Plan 12), Tier 1 handler names and schemas remain stable.

#### Consequences

* Plan 10 scope stays focused on knowledge access.
* Repository browsing does not block Plan 10 completion.

---

### ADR-030: Human Approval Boundary for Index Modification

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-012 assigns approval enforcement to callers. MCP is the first external-facing caller for indexing.

#### Decision

* Split indexing into `index_documents_preview` (no mutation) and `index_documents_apply` (may mutate storage).
* `index_documents_apply` requires `approval_confirmed: bool` that must be exactly `True`.
* When `approval_confirmed is not True`, raise `ApprovalRequiredError` before calling `index_documents`.
* MCP must not call `input()` or block on interactive stdin.

#### Consequences

* Agents must deliberately approve index mutation.
* CLI (future) wraps preview → user prompt → apply.

---

### ADR-031: Source Attribution Contract

**Status:** Accepted

**Date:** 2026-06-21

#### Context

`PROJECT.md` requires citations with document title, document path, section title, and line range. `SearchResult` previously carried only `Chunk` + `score`.

#### Decision

* **Do not modify `ChunkMetadata`.**
* Add `source: SourceReference` to `SearchResult`.
* Populate `source` in `storage` when constructing `SearchResult` from Qdrant points via `payload_to_source_reference`.
* `Reranker` implementations preserve `source` when emitting rescored `SearchResult` tuples.
* Fusion preserves `source` from the best-ranked leaf occurrence when building fused results.
* MCP `formatting.py` maps `SearchResult.source` → `SourceReferenceSchema`; MCP does not import from `storage`.

#### Consequences

* Full PROJECT.md citations in search responses without indexing churn.
* Test fixtures across retrieval/storage updated for the new required field.

---

### ADR-032: MCP Dependency Boundaries

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 10 must not violate dependency flow.

#### Decision

**Allowed imports in `mcp_server` production code:** `knowledge_assistant.core.*`, `knowledge_assistant.retrieval.protocol.Retriever`, `knowledge_assistant.indexing.pipeline.IndexingPipeline`, `knowledge_assistant.indexing.pipeline.IndexingResult`, `pydantic` (in `schemas.py` only).

**Forbidden:** `storage`, `qdrant_client`, MCP SDK, LangGraph, OpenAI, LlamaIndex, concrete retrieval internals, `llm/`, `agent/`.

**Assembly rule:** `RerankRetriever` construction lives outside `mcp_server`.

#### Consequences

* Plan 10 MCP package has no storage or transport coupling.
* Import-boundary tests enforce rules mechanically.

---

### ADR-033: Pydantic Boundary Ownership

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-001 excludes Pydantic from `core`. Plan 10 must prevent schema leakage into lower layers.

#### Decision

* **Pydantic is permitted only in `knowledge_assistant.mcp_server.schemas.py`** (and tests for that module).
* Handler flow: Pydantic request → core domain type → delegate → core result → Pydantic response.
* `formatting.py` maps core types to Pydantic response models.

#### Consequences

* Clear boundary: JSON/tool contracts live in MCP; domain logic stays Pydantic-free below.

---

### ADR-034: MCP Handler Layer Without SDK Runtime

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 10 could deliver either handler functions only, or handlers plus a runnable MCP SDK server.

#### Decision

* **Plan 10 implements handler functions and Pydantic schemas only.**
* **Plan 10 does not add the `mcp` SDK runtime dependency.**
* `server.py` is a stub documenting deferred SDK registration (target: Plan 12).
* Plan 12 will add MCP SDK dependency, register Tier 1 handlers, and implement the MCP client in the agent.

#### Consequences

* Plan 10 validation uses direct handler invocation, not MCP subprocess tests.
* Tier 1 handler signatures are the stable API surface.

---

### ADR-035: OpenAI-Compatible API Standard

**Status:** Accepted

**Date:** 2026-06-21

#### Context

The project targets vLLM serving `Qwen/Qwen3.6-35B-A3B` via base URL but must remain provider-neutral. Multiple gateways expose the same HTTP contract.

#### Decision

* Standardize on an **OpenAI-compatible** `/v1/chat/completions` style API for model invocation.
* `OpenAICompatibleLLMClient` posts JSON to `{base_url}/chat/completions`.
* The same `LLMClient` protocol must work against vLLM, OpenAI, LiteLLM, Open WebUI proxy, and other OpenAI-compatible gateways.
* Provider-specific behavior stays inside `openai_client.py`.
* Non-streaming JSON responses only in Plan 11.

#### Consequences

* Local development copies `.env.example` → `.env` and points `LLM_BASE_URL` at a vLLM instance.
* Switching providers requires config changes only — no code changes in higher layers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Provider-native SDK protocols | Out of project scope |
| Raw text `/v1/completions` API | Plan 12 needs multi-turn chat and tool messages |
| LangChain / LangGraph LLM wrappers inside `llm/` | Couples boundary to agent framework |

---

### ADR-036: LLM Boundary Ownership

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-013 assigns embeddings to indexing and retrieval. ADR-027 assigns reranking to retrieval. ADR-032 forbids `mcp_server → llm`. Only the LangGraph agent may communicate with the LLM boundary.

#### Decision

* `knowledge_assistant.llm` owns **model invocation only**: protocol, transport DTOs, settings, HTTP adapter, stub client, and LLM-specific exceptions.
* `llm/` does **not** own retrieval, indexing, storage, MCP handlers, agent workflows, prompt templates, query rewriting, RAG context assembly, tool execution, embeddings, or reranking.
* Only `agent` (Plan 12) and `cli` (wiring) are expected consumers of `llm/`.
* `mcp_server`, `retrieval`, `indexing`, and `storage` must not import `llm/`.

#### Consequences

* Plan 12 composes `LLMClient` + MCP client without redesigning Plan 11 contracts.
* The seam after Plan 10 remains: MCP returns evidence; agent + LLM produce answers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared `llm/` module for embeddings + chat | Violates ADR-013 |
| MCP calls LLM for answer synthesis | Violates ADR-032 |
| RAG prompts in `llm/` | Encodes product behavior in wrong layer |

---

### ADR-037: Chat-First LLM Client Protocol

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 12 requires multi-turn conversation, system/user/assistant/tool roles, and model-emitted tool calls. A completion-only API would force redesign.

#### Decision

* Expose a **chat-oriented** `LLMClient.chat(...)` API as the sole entry point.
* `messages` is an immutable tuple; callers append per turn — the client does not mutate conversation state.
* `settings=None` merges per-call overrides with `LlmSettings` defaults.
* `tools=()` means no tools sent to the provider.
* Sync-first, non-streaming only in Plan 11.

#### Consequences

* Plan 12 LangGraph nodes call `chat` repeatedly as the conversation grows.
* Tool-calling orchestration stays in the agent.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate `complete(prompt: str)` method | Duplicates chat; encourages prompt strings in wrong layer |
| Async-only protocol | Existing codebase is sync; premature for Plan 11 |
| Streaming `chat` | Not required for CLI demo v1 |

---

### ADR-038: Tool-Call Transport DTOs Without Orchestration

**Status:** Accepted

**Date:** 2026-06-21

#### Context

OpenAI-compatible chat completions expose tool definitions in the request and `tool_calls` in the response. Plan 12 must pass MCP tool schemas to the model. Plan 11 must not execute tools.

#### Decision

* Plan 11 defines typed **transport DTOs** only: `ToolDefinition`, `ToolCall`.
* `GenerationResult` includes `tool_calls: tuple[ToolCall, ...]`.
* `ChatMessage` supports `role=tool` with `tool_call_id`.
* Mapping to/from provider JSON lives in `openai_client.py` only.
* Plan 11 must not execute tools, validate tool arguments against MCP contracts, or implement agent tool loops.

#### Consequences

* Plan 12 owns MCP tool schema construction and handler dispatch.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Defer tool DTOs to Plan 12 | Would require Plan 11 API redesign |
| Pydantic models for tool schemas in `llm/` | Unnecessary; dataclass + dict suffices |
| Tool execution inside `openai_client.py` | Violates MCP and agent ownership |

---

### ADR-039: LLM-Local Types and Dataclass Boundary

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-001 excludes Pydantic from `core`. ADR-033 confines Pydantic to `mcp_server/schemas.py`. `ChatMessage` is infrastructure transport data, not knowledge domain data.

#### Decision

* All Plan 11 DTOs use `@dataclass(frozen=True, slots=True)` with `__post_init__` validation.
* DTOs live in `llm/` — not in `knowledge_assistant.core`.
* Plan 11 does not add Pydantic to `llm/`.
* Validation errors raise `ValueError` at construction time.

#### Consequences

* Clear separation: `core` = knowledge domain; `llm` = model transport.
* Plan 12 translates between MCP Pydantic schemas and LLM dataclasses at the agent boundary.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `ChatMessage` in `core` | Not knowledge domain; couples domain to OpenAI message shape |
| Pydantic in `llm/schemas.py` | No strong justification |
| TypedDict messages | No runtime validation |

---

### ADR-040: Environment Configuration for LLM Settings

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Initial runtime uses vLLM with user-supplied base URL and credentials via `.env`. Generation defaults must be validated and separable from per-call overrides.

#### Decision

* Commit `.env.example` at repository root with `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`.
* Implement `LlmSettings.from_env()` using `os.environ.get` — no `python-dotenv` runtime dependency.
* Per-call `GenerationSettings` fields override `LlmSettings.default_generation` and `default_model` in merge logic.
* `.env` remains gitignored; `.env.example` is committed.

#### Consequences

* README documents copy `.env.example` → `.env` for local vLLM setup.
* Tests construct `LlmSettings(...)` directly without reading environment.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `python-dotenv` in library code | Hidden magic; tests use explicit settings |
| Pydantic `BaseSettings` | Unnecessary dependency for six variables |
| Single flat settings object | Plan 12 needs per-turn overrides |

---

### ADR-041: Embeddings and Reranking Remain Outside LLM

**Status:** Accepted

**Date:** 2026-06-21

#### Context

ADR-013 establishes embedding ownership for indexing and retrieval. ADR-027 places cross-encoder reranking in retrieval. A regression could add embedding helpers to `llm/` because “models live near LLMs.”

#### Decision

* `llm/` must **not** implement embeddings, sparse vectors, or reranking.
* `llm/` must not import `knowledge_assistant.retrieval` or `knowledge_assistant.indexing`.
* Import-boundary tests forbid embedding/reranker package names in `llm/`.
* Plan 11 documentation cross-links ADR-013 and ADR-027.

#### Consequences

* Embedding and reranker runtimes remain in their owning layers per existing ADRs.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared `models/` package for all ML inference | Premature; violates layer ownership |
| Reranker in `llm/` | ADR-027 explicitly rejects this |

---

### ADR-047: Evaluation Layer Ownership

**Status:** Accepted

**Date:** 2026-06-21

#### Context

`PROJECT.md` lists retrieval evaluation as a project goal. Plans 06–09 deliver composable retrievers behind `Retriever`. Higher layers (MCP, agent, LLM) must not own retrieval-quality measurement. Without an explicit evaluation boundary, metrics logic risks appearing in retrieval tests, CLI scripts, or agent workflows — violating component ownership and making strategy comparison inconsistent.

#### Decision

* Implement retrieval evaluation in a dedicated package: `knowledge_assistant.evaluation`.
* The evaluation layer owns benchmark dataset models, document registry, loading, retrieval metric definitions, aggregation, `EvaluationRunner` orchestration over `Retriever.retrieve`, structured `EvaluationReport` output, and `ComparisonReport` assembly for multi-strategy comparison.
* The evaluation layer owns the retrieval benchmark as a first-class asset under `data/evaluation/`.
* The evaluation layer does **not** own retrieval algorithms, indexing, storage, MCP handlers, agent orchestration, LLM inference, or answer generation.
* Evaluation measures ranked retrieval output only — inputs are `SearchQuery`; outputs are analyzed `RetrievalResult` tuples.
* Production code in `evaluation/` depends on `knowledge_assistant.core` and `knowledge_assistant.retrieval.protocol.Retriever` only, plus the Python standard library.
* Concrete retriever construction belongs in tests, future CLI wiring, or demo scripts — not in `evaluation/` production modules.

#### Consequences

* Retrieval strategies are comparable on equal footing using one runner and one dataset.
* Evaluation runs without Qdrant, MCP, LangGraph, or LLM when tests inject fake retrievers.
* Phase 8 lecture flow runs four wired retrievers against one benchmark and prints a `ComparisonReport` table.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Metrics inside `retrieval/` | Couples measurement to the subsystem under test |
| MCP tool `evaluate_retrieval` | Evaluation is offline/batch analysis, not agent knowledge access |
| Agent-side evaluation loop | Conflates orchestration quality with retrieval quality |
| pytest-only helpers without a package | Not reusable for CLI comparison or lecture demos |

---

### ADR-048: Evaluation Dataset Format

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Retrieval evaluation requires stable ground-truth labels independent of any one retriever. The project knowledge base consists of synthetic corporate documents per `PROJECT.md`. The benchmark is a project asset owned by the evaluation layer; test fixtures must not define benchmark validity.

#### Decision

* Store benchmark data as committed JSON files under `data/evaluation/`.
* Top-level schema includes `dataset_id`, optional `description`, optional `corpus_version`, a `documents` registry, and `cases`.
* `DocumentRegistry` maps benchmark-local `document_key` strings to canonical relative `path` strings.
* `EvaluationCase` fields: `case_id`, `question`, `expected_document_key` (single relevant document in v1).
* Loader: `load_evaluation_dataset(path: Path) -> EvaluationDataset` using stdlib `json` only.
* Validation at load time covers non-empty identifiers, registry integrity, unique `case_id` values, and resolvable document keys.
* Plan 13 v1 uses document-level labels only; chunk-level labels are deferred.
* Benchmark paths align with the planned synthetic knowledge-base layout under `knowledge/`.

#### Consequences

* Benchmark labels survive indexing-internal ID changes as long as indexed `SourceReference.document_path` matches registry paths.
* Datasets are version-controlled, diffable, and agent-legible.
* Corpus path changes require a benchmark dataset version bump, not silent relabeling.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| YAML dataset | Requires non-stdlib dependency |
| Dataset embedded only in Python test modules | Harder to reuse for CLI and lecture comparison |
| Benchmark derived from indexing test fixtures | Couples evaluation validity to test fixtures |
| `expected_document_id` (UUID5) as primary label | Tight coupling to indexing ID generation |

---

### ADR-049: Retrieval Metric Selection

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 13 must quantify retrieval quality with standard metrics comparable across dense, sparse, fusion, and rerank retrievers. The v1 dataset uses one relevant document per question (binary relevance at document granularity).

#### Decision

**Include in Plan 13:**

| Metric | Definition (per case) | Aggregation |
| ------ | ---------------------- | ------------- |
| **Hit Rate@K** | `1.0` if any result in top `K` matches the expected document path, else `0.0` | Macro mean across cases |
| **Recall@K** | Same as Hit Rate@K when exactly one relevant document exists per case | Macro mean across cases |
| **MRR** | `1 / rank` of the first matching document; `0.0` if no match within evaluated `top_k` | Mean across cases |

* `EvaluationSettings.metrics_k` defaults to `(1, 3, 5)`; `EvaluationSettings.eval_top_k` is passed to `SearchQuery.top_k`.
* Metrics inspect `RetrievalResult.results` order as returned by the retriever — no re-sorting in the evaluation layer.
* Relevance matching resolves `expected_document_key` → registry `path`, normalizes paths, and compares against `SearchResult.source.document_path`.
* **Defer NDCG** to a future evaluation plan.

#### Consequences

* Reports are easy to explain in the Production RAG lecture.
* Same metrics apply uniformly to all `Retriever` implementations.
* Hit Rate@K and Recall@K are numerically identical under v1 single-relevant-doc labels; both names are retained for future multi-document benchmarks.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Include NDCG now | Graded labels absent; redundant for v1 |
| Chunk-level precision only | Misaligned with document-scoped synthetic policies |
| Score-threshold metrics | Scores are incomparable across retriever types |

---

### ADR-050: Retriever Protocol as Evaluation Target

**Status:** Accepted

**Date:** 2026-06-21

#### Context

Plan 08 introduced `Retriever` as the composable retrieval contract. Plan 13 must evaluate dense, sparse, fusion, and rerank strategies without importing their concrete classes.

#### Decision

* `EvaluationRunner.run(...)` accepts `retriever: Retriever` from `retrieval.protocol`.
* The runner calls `retriever.retrieve(SearchQuery(text=case.question, top_k=settings.eval_top_k))` for each case.
* The runner does not call `VectorStore`, embedding providers, fusion math, or rerankers directly.
* `retriever_label: str` is a caller-supplied report field; the protocol has no name property.
* Evaluation code imports `Retriever` from `knowledge_assistant.retrieval.protocol` only.
* Default error handling is fail-fast — abort report on first retriever error.

#### Consequences

* Unit tests use fake retrievers without storage.
* Integration tests construct real retriever stacks in test conftest while keeping `evaluation/` modules import-clean.
* Lecture demo runs `EvaluationRunner` four times and assembles a `ComparisonReport`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Evaluate `VectorStore.search_*` directly | Bypasses retrieval orchestration under test |
| Hard-code four concrete retriever classes in runner | Breaks composability |
| Callable instead of protocol | Less consistent with ADR-022 |
| Swallow retriever errors and score as miss | Hides infrastructure failures |

---

### ADR-051: Demo Bootstrap Composition Root

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Plans 04–09 delivered storage, indexing, and composable retrieval. Plans 10–13 delivered MCP handlers, agent, and evaluation — each requiring externally injected `Retriever` and `IndexingPipeline` instances. Without a single composition root, CLI, tests, and future demo scripts would duplicate retriever wiring (violating ADR-032 assembly rule).

#### Decision

* Introduce `knowledge_assistant.bootstrap` as the **demo composition root**.
* `build_demo_environment()` assembles `VectorStore`, `IndexingPipeline`, and canonical `RerankRetriever` stack using stub providers.
* Bootstrap contains **dependency assembly only** — no CLI parsing, MCP handlers, agent logic, or evaluation metrics.
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

### ADR-052: CLI Owns Demo Orchestration

**Status:** Accepted

**Date:** 2026-06-22

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

### ADR-053: Canonical Demo Retrieval Pipeline

**Status:** Accepted

**Date:** 2026-06-22

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

### ADR-054: Demo Commands Require Explicit Approval for Destructive Operations

**Status:** Accepted

**Date:** 2026-06-22

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

### ADR-055: Dedicated Embeddings Package for Shared BGE-M3 Runtime

**Status:** Accepted

**Date:** 2026-06-22

#### Context

ADR-013 assigns write-path embedding ownership to indexing and query-path ownership to retrieval. Plan 16 must load one BGE-M3 model for both paths without violating layer boundaries or duplicating `torch` imports.

#### Decision

* Introduce `knowledge_assistant.embeddings` as the shared dense embedding runtime package.
* Indexing implements `BgeM3EmbeddingProvider(EmbeddingProvider)`; retrieval implements `BgeM3QueryEmbeddingProvider(QueryEmbeddingProvider)`.
* Layer protocols remain in their owning packages per ADR-013 and ADR-015.
* `embeddings/` must not import indexing, retrieval, storage, MCP, agent, LLM, or evaluation.

#### Consequences

* One model load path; `torch` / FlagEmbedding imports localized to `embeddings/`.
* Future sparse embedding runtime may extend the package without changing Plan 16 dense contracts.

---

### ADR-056: BGE-M3 Default Runtime Implementation (FlagEmbedding)

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Plan 16 must introduce real `BAAI/bge-m3` dense vectors with distinct query vs passage encoding. The stable contract must not lock all layers to FlagEmbedding.

#### Decision

* `DenseEmbeddingRuntime` is the stable protocol (`embed_passages`, `embed_query`).
* `BgeM3FlagEmbeddingRuntime` is the Plan 16 default implementation using FlagEmbedding internally.
* Dense-only inference: passage mode via `encode`; query mode via `encode_queries`.
* `create_dense_embedding_runtime(settings)` returns the protocol type.

#### Consequences

* Indexing and retrieval remain backend-agnostic.
* Heavier dependencies appear for the first time; CI default remains stub providers.

---

### ADR-057: Bootstrap-Owned Shared Embedding Runtime

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Indexing and retrieval both require the same BGE-M3 weights. Without explicit shared-runtime ownership, wiring could construct independent model instances.

#### Decision

* Bootstrap creates one `DenseEmbeddingRuntime` per `DemoEnvironment` when real embeddings are enabled.
* The same runtime is injected into `BgeM3EmbeddingProvider` and `BgeM3QueryEmbeddingProvider`.
* Default mode remains stub providers; real mode is opt-in via `RAG_EMBEDDING_MODE=real`.
* Bootstrap imports `knowledge_assistant.embeddings` factories only — not `torch` or FlagEmbedding directly.

#### Consequences

* Single model load per demo environment assembly.
* Unit tests continue injecting stub providers without loading models.

---

### ADR-058: Dense Embedding Migration Requires Full Reindex

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Stub-indexed and real BGE-M3 vectors occupy the same `dense` slot but are semantically incompatible.

#### Decision

* Switching dense embedding provider stub ↔ real requires full collection rebuild and reindex with caller approval.
* Recovery path: `rag demo load --rebuild --approve`.
* No in-place dense vector migration in Plan 16.
* Mixing stub-indexed dense vectors with real query embeddings (or vice versa) is unsupported.

#### Consequences

* Operators must plan a reindex window when enabling real embeddings.
* `rag demo info` reports embedding mode so operators detect mismatch risk.

---

### ADR-059: Dense Vector Normalization and Dimension Contract

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Qdrant dense search uses `COSINE` distance. Real model outputs must align with configured `dense_vector_size` and stub normalization behavior.

#### Decision

* Every `DenseEmbeddingRuntime` output length must equal configured `dense_vector_size` (default `1024`).
* Runtime applies L2 normalization when `normalize_embeddings=True` (default).
* `EmbeddingRuntimeSettings.dense_vector_size` is supplied from `StorageSettings` at bootstrap assembly.
* `batch_size` applies to `embed_passages` only; `embed_query` always processes one query.

#### Consequences

* Predictable cosine behavior when all layers share one dimension setting.
* Misconfiguration fails at runtime construction or first embed.

---

### ADR-060: Stub Providers Remain Default for CI and Fast Tests

**Status:** Accepted

**Date:** 2026-06-22

#### Context

Real BGE-M3 introduces `torch`, large downloads, and variable runtime. CI must remain fast and deterministic.

#### Decision

* `StubEmbeddingProvider` and `StubQueryEmbeddingProvider` remain in the codebase.
* Default `build_demo_environment()` uses stub providers unless configured for real embeddings.
* Real-model tests are opt-in via `@pytest.mark.embedding_model`, excluded from default CI.
* `rag demo info` pipeline label distinguishes stub vs real dense embedding modes.

#### Consequences

* CI validation stays lightweight.
* Operators opt into real embeddings deliberately.
