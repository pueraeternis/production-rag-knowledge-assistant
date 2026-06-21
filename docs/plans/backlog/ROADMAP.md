# Roadmap

**Status:** Informational

This document describes the planned evolution of Production RAG Knowledge Assistant.

The roadmap is informational only.

Authorized implementation scope is defined exclusively by active plans.

---

# Phase 1 — Foundation

Goal:

Establish project structure, development workflow, and architectural boundaries.

Plans:

* Plan 01 — Project Bootstrap
* Plan 02 — Python Bootstrap

Deliverables:

* repository structure
* uv project
* quality tooling
* package layout
* development workflow

---

# Phase 2 — Core Domain

Goal:

Define the core data model shared across all system layers.

Plans:

* Plan 03 — Domain Models

Deliverables:

* Document
* Chunk
* SearchResult
* SourceReference
* Indexing models
* Retrieval models

Notes:

Domain models should remain implementation-agnostic and independent from Qdrant, LangGraph, MCP, and LlamaIndex.

---

# Phase 3 — Storage and Indexing

Goal:

Build the document ingestion pipeline.

Plans:

* Plan 04 — Storage Layer
* Plan 05 — Indexing Pipeline

Deliverables:

* Qdrant integration
* document loading
* chunking
* embedding generation
* indexing workflow

Key Principle:

Indexing and retrieval are separate concerns.

---

# Phase 4 — Retrieval

Goal:

Implement production-style retrieval.

Plans:

* Plan 06 — Dense Retrieval
* Plan 07 — Sparse Retrieval
* Plan 08 — Fusion
* Plan 09 — Reranking

Deliverables:

* vector retrieval
* BM25 retrieval
* rank fusion
* reranking

Target Pipeline:

Dense Search
+
BM25 Search
↓
Fusion
↓
Reranker
↓
Top Context

---

# Phase 5 — Knowledge Access

Goal:

Expose retrieval capabilities through MCP.

Plans:

* Plan 10 — Knowledge MCP Server *(completed)*

Deliverables *(Plan 10 — implemented)*:

* `search_documents` — ranked chunk retrieval with source attribution
* `index_documents_preview` — indexing impact preview without storage mutation
* `index_documents_apply` — indexing mutation after explicit human approval

Deferred *(not part of Plan 10; future plans)*:

* `get_document` — repository document browse (Tier 2)
* `get_statistics` — index diagnostics (Tier 2)
* URL indexing — remote source ingestion (ADR-011 local sources only in Plan 05/10)
* MCP SDK runtime and transport — handler layer only in Plan 10 (ADR-034); agent uses in-process adapters per Plan 12 (ADR-043 design)
* MCP resources (`knowledge://…` URIs)

Notes:

Local indexing sources accept file or directory paths (`.md`, `.txt`). Directory sources are recursively discovered before indexing. Index modification operations require human approval via `approval_confirmed=True` on the apply handler.

---

# Phase 6 — LLM Integration

Goal:

Introduce model interaction boundaries.

Plans:

* Plan 11 — LLM Boundary *(completed)*

Deliverables *(Plan 11 — implemented)*:

* OpenAI-compatible `LLMClient` chat protocol
* generation settings and environment configuration
* typed LLM message, generation, and tool-call transport contracts (`ChatMessage`, `ToolDefinition`, `ToolCall`, `GenerationResult`)

Notes:

“Prompt contracts” in this phase means **typed LLM transport contracts**, not RAG or system prompt templates. RAG prompt templates, citation rendering, and agent-side prompt assembly were delivered in Plan 12.

---

# Phase 7 — Agent Layer

Goal:

Build the conversational assistant.

Plans:

* Plan 12 — LangGraph Agent *(completed: [12-langgraph-agent.md](../completed/12-langgraph-agent.md))*

Deliverables *(Plan 12 — implemented)*:

* LangGraph agent orchestration (`agent_node`, `tool_node`, conditional routing)
* conversation handling with in-memory graph state
* MCP Tier 1 tool adapters (`search_documents`, `index_documents_preview`, `index_documents_apply`)
* RAG prompt templates with citation contract
* tool registry and max tool-iteration guard

Deferred *(not part of Plan 12; future plans)*:

* query rewriting and retrieval retry — proposed **Plan 12b**
* MCP SDK client/server transport — proposed **Plan 12c**
* CLI chat UX and interactive approval prompts
* durable conversation memory and LangGraph checkpointers

**Next roadmap phase:** Phase 8 — Evaluation (Plan 13). No plan file is in backlog yet; see Phase 8 below.

---

# Phase 8 — Evaluation

Goal:

Measure retrieval quality and demonstrate production practices.

Plans:

* Plan 13 — Evaluation Framework

Deliverables:

* retrieval metrics
* benchmark dataset
* evaluation scenarios

---

# Phase 9 — Demo Completion

Goal:

Complete the educational RAG assistant.

Plans:

* Plan 14 — Demo Dataset
* Plan 15 — End-to-End Demo

Deliverables:

* synthetic company knowledge base
* complete assistant workflow
* lecture demonstration environment

---

# Architectural Priorities

The project prioritizes:

1. Retrieval quality
2. Source attribution
3. MCP integration
4. Agent orchestration

The project does not prioritize:

* multi-agent systems
* distributed infrastructure
* production deployment
* enterprise platform features

The retrieval layer is the most important subsystem in the project.

All higher-level functionality depends on retrieval quality.
