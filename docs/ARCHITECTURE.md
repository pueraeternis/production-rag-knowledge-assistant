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

The retrieval layer implements a hybrid retrieval pipeline:

```text
Dense Search
      +
BM25 Search
      ↓
Fusion
      ↓
Reranker
      ↓
Top Context
```

The retrieval layer is deterministic and must not call LLMs.

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
