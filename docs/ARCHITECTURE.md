# Architecture

Production RAG Knowledge Assistant is a documentation-driven educational project demonstrating modern enterprise knowledge assistant architecture.

For project vision and scope, see [PROJECT.md](../PROJECT.md).

---

## System Overview

```text
User
  ↓
CLI Chat
  ↓
LangGraph Agent
  ↓
MCP Client
  ↓
Knowledge MCP Server
  ↓
Retrieval Layer
  ↓
Qdrant
```

The agent never interacts with Qdrant directly.

All knowledge access happens through MCP tools and resources.

---

## Component Boundaries

| Component        | Owns                                                   | Must not own                            |
| ---------------- | ------------------------------------------------------ | --------------------------------------- |
| LangGraph Agent  | Conversation handling, routing, tool selection, memory | Retrieval implementation, Qdrant access |
| MCP Server       | Knowledge tools and resources                          | Agent behavior, conversation management |
| Retrieval Layer  | Dense retrieval, sparse retrieval, fusion, reranking   | LLM interaction                         |
| Indexing Layer   | Loading, parsing, chunking, indexing                   | Retrieval decisions                     |
| Qdrant Storage   | Vector storage and metadata                            | Business logic                          |
| LLM Boundary     | All model calls                                        | Retrieval implementation                |

---

## Retrieval Layer

The retrieval layer is deterministic and must not call LLMs. Plan 06 implements dense retrieval; Plan 07 implements sparse retrieval. Fusion and reranking are deferred to later plans.

### Dense retrieval path

```text
SearchQuery (text, top_k)
    ↓
DenseRetriever.retrieve()
    ↓
QueryEmbeddingProvider.embed_query(query.text)
    ↓
validate len(vector) == DenseRetrievalSettings.dense_vector_size
    ↓
VectorStore.search_dense(vector=vector, top_k=query.top_k)
    ↓
RetrievalResult(query=query, results=...)
```

### Sparse retrieval path

```text
SearchQuery (text, top_k)
    ↓
SparseRetriever.retrieve()
    ↓
SparseQueryEmbeddingProvider.embed_query(query.text)
    ↓
SparseQueryVector (retrieval-local validation, non-empty enforced)
    ↓
VectorStore.search_sparse(indices=..., values=..., top_k=query.top_k)
    ↓
RetrievalResult(query=query, results=...)
```

Future hybrid retrieval will compose dense and sparse leaf retrievers behind a higher orchestrator:

```text
Dense Search
      +
Sparse Search (BGE-M3 lexical vectors)
      ↓
Fusion
      ↓
Reranker
      ↓
Top Context
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `DenseRetrievalSettings` |
| `embeddings.py` | `QueryEmbeddingProvider`, `StubQueryEmbeddingProvider`, `SparseQueryEmbeddingProvider`, `StubSparseQueryEmbeddingProvider` |
| `exceptions.py` | Retrieval-specific error types |
| `dense.py` | `DenseRetriever` orchestration |
| `sparse_vectors.py` | `SparseQueryVector` (retrieval-local) |
| `sparse.py` | `SparseRetriever` orchestration |

**Query embedding ownership (ADR-013, ADR-015, ADR-019):** retrieval generates query-path dense and sparse embeddings via retrieval-local providers; indexing generates write-path chunk embeddings; storage generates neither.

**Retrieval boundary:** production retrieval code depends on `core` and `storage.protocol.VectorStore` only. Retrieval must **not** import `storage.models`, `qdrant_client`, or indexing packages. Indexing may import `storage.models` for upsert boundary types.

**Public contract:** callers submit `SearchQuery` text and receive `RetrievalResult`. Vectors are internal to retrieval and must not leak to MCP, agent, or other higher layers.

**Sparse placeholder constraint (ADR-020):** indexing still stores a constant sparse placeholder per ADR-010 until a future sparse indexing plan replaces it. Meaningful sparse retrieval against production-indexed corpora requires that future plan and a full reindex with caller approval. Plan 07 delivers the read path only.

**Dependency rule:** retrieval depends on the `VectorStore` protocol only — not on `qdrant_client`, `StorageSettings`, or other storage modules. See [ADR-014](DECISIONS.md#adr-014-dense-retrieval-boundary) through [ADR-020](DECISIONS.md#adr-020-reindex-requirement-for-future-sparse-migration).

---

## Dependency Flow

Preferred:

```text
agent
  ↓
mcp_server
  ↓
retrieval
  ↓
storage
```

```text
agent
  ↓
llm
```

```text
indexing
  ↓
storage
```

Forbidden:

```text
mcp_server → llm
retrieval → llm
storage → llm
storage → agent
retrieval → agent
```

---

## Core Domain Layer

The `core/` package defines shared domain types used across all layers. Types are immutable frozen dataclasses with `__post_init__` validation (see [ADR-001](DECISIONS.md#adr-001-domain-model-technology)).

| Module | Types |
| ------ | ----- |
| `identifiers.py` | `DocumentId`, `ChunkId` |
| `document.py` | `Document`, `DocumentMetadata`, `DocumentContent` |
| `chunk.py` | `Chunk`, `ChunkMetadata` |
| `source.py` | `LineRange`, `SourceReference` |
| `retrieval.py` | `SearchQuery`, `SearchResult`, `RetrievalResult` |
| `indexing.py` | `IndexingSourceKind`, `IndexingSource`, `IndexingPreview`, `ApprovalStatus` |

Core models are implementation-agnostic. They must not import from `agent`, `retrieval`, `indexing`, `storage`, `mcp_server`, `llm`, `cli`, or third-party application libraries. Boundary layers translate between domain types and infrastructure-specific schemas.

`SourceReference` is the canonical citation model for user-visible source attribution. It is distinct from `DocumentMetadata` and `ChunkMetadata`, which serve indexing and storage concerns.

---

## Qdrant Storage Layer

The `storage/` package is the only component that imports `qdrant_client`. Indexing and retrieval depend on the `VectorStore` protocol, not on Qdrant APIs directly.

```text
indexing
  ↓
VectorStore (protocol)
  ↓
QdrantVectorStore
  ↓
Qdrant
```

```text
retrieval
  ↓
VectorStore (protocol)
  ↓
QdrantVectorStore
  ↓
Qdrant
```

| Module | Responsibility |
| ------ | -------------- |
| `protocol.py` | `VectorStore` protocol (six methods: create, delete, exists, upsert, search_dense, search_sparse) |
| `models.py` | `ChunkUpsertItem`, `SparseVector` boundary types |
| `mapping.py` | Pure payload ↔ domain translation |
| `collection.py` | Vector names and collection defaults |
| `config.py` | `StorageSettings` |
| `qdrant_store.py` | `QdrantVectorStore` implementation, `search_sparse`, and `create_qdrant_vector_store` factory |
| `validation.py` | Structural validation for sparse search inputs |
| `exceptions.py` | Storage-specific error types |

Storage receives pre-computed vectors on write and pre-computed query vectors on read. It does not generate embeddings. See [ADR-002](DECISIONS.md#adr-002-vectorstore-protocol-abstraction) through [ADR-006](DECISIONS.md#adr-006-storage-does-not-generate-embeddings).

---

## Indexing Layer

The `indexing/` package turns local documents into stored chunks via the `VectorStore` protocol. It is the only component that imports LlamaIndex (confined to `llamaindex_adapter.py`). See [ADR-007](DECISIONS.md#adr-007-llamaindex-containment-in-indexing-layer) through [ADR-013](DECISIONS.md#adr-013-embedding-boundary-ownership).

```text
local file/directory
    ↓
LlamaIndex SimpleDirectoryReader (loading)
    ↓
loaded document text
    ↓
LlamaIndex SentenceSplitter (chunking)
    ↓
core domain models
    ↓
EmbeddingProvider (write path)
    ↓
VectorStore.upsert_chunks

parallel attribution mirror:
Path.read_text → raw source text → title, section_title, LineRange
```

| Module | Responsibility |
| ------ | -------------- |
| `config.py` | `IndexingSettings` |
| `documents.py` | Local file discovery (`.md`, `.txt`) |
| `embeddings.py` | `EmbeddingProvider`, `StubEmbeddingProvider`, sparse placeholder |
| `exceptions.py` | Indexing-specific error types |
| `ids.py` | UUID5 `DocumentId` and `ChunkId` generation |
| `llamaindex_adapter.py` | LlamaIndex load/chunk + raw attribution mirror → domain models (sole LlamaIndex import site) |
| `pipeline.py` | `IndexingPipeline` with `preview_indexing` and `index_documents` |

**Loading and chunking:** LlamaIndex `SimpleDirectoryReader` owns loading; `SentenceSplitter` owns chunk boundaries. A separate raw file read mirrors on-disk text for source attribution only — it is not the primary loader and does not replace LlamaIndex ingestion.

**Reader contract:** one input file must yield exactly one LlamaIndex document; zero or multiple documents raise `DocumentLoadError`.

**Source attribution:** raw on-disk text is the source of truth for `LineRange`. Character offsets are resolved in indexing code (including overlap-aware lookup) and mapped to 1-based lines. LlamaIndex node metadata is not used for line numbers.

**Empty discovery:** `preview_indexing` may return zero document/chunk counts for empty directories. `index_documents` is a storage no-op when no files are discovered — it does not create, delete, or upsert collections.

**Chunking errors:** file read failures raise `DocumentLoadError`; LlamaIndex splitter failures and empty chunk results raise `ChunkingError`.

**Dependency rule:** indexing depends on the `VectorStore` protocol only — not on `qdrant_client` or `StorageSettings`.

**Embedding ownership (ADR-013):** indexing generates write-path chunk embeddings; retrieval will generate query-path embeddings (Plan 06); storage generates neither.

**ID ownership (ADR-008):** indexing generates deterministic UUID5 document and chunk IDs; storage does not generate IDs.

**Human approval (ADR-012):** `preview_indexing` estimates impact without embeddings or storage writes; callers must obtain approval before `index_documents(..., rebuild=True)`.

**Sparse vectors (ADR-010, ADR-020):** indexing attaches a constant sparse placeholder until a future sparse indexing plan provides per-chunk BGE-M3 sparse vectors. A full reindex with caller approval will be required when that migration occurs.

---

## Source Layout

```text
src/knowledge_assistant/
    core/           # shared domain types, IDs, validation
    agent/          # LangGraph agent and graph definitions
    mcp_server/     # Knowledge MCP server
    retrieval/      # hybrid retrieval, fusion, reranking
    indexing/       # LlamaIndex ingestion and chunking
    llm/            # OpenAI-compatible LLM boundary
    storage/        # Qdrant integration
    cli/            # CLI entrypoints
```

---

## Human-in-the-Loop

Potentially destructive indexing operations require explicit user approval.

Examples:

* index rebuild;
* reindexing;
* index replacement.

---

## Source Attribution

All knowledge answers must be grounded in retrieved content.

The system exposes:

* document title;
* document path;
* section title;
* line range.

---

## Documentation Precedence

When sources conflict:

1. PROJECT.md
2. docs/ARCHITECTURE.md
3. docs/DECISIONS.md
4. docs/plans/active/
5. docs/PROGRESS.md
6. Chat Context
