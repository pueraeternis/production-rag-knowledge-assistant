# Roadmap

**Status:** Informational

This document describes the planned evolution of Production RAG Knowledge Assistant.

The roadmap is informational only.

Authorized implementation scope is defined exclusively by active plans.

---

# Project Progression

The project has completed architecture construction (foundation through evaluation framework). Remaining work moves toward a working educational demo:

```text
Foundation
→ Retrieval
→ MCP
→ Agent
→ Evaluation
→ Knowledge Corpus
→ Demo Bootstrap
→ Real Models
→ Benchmark Evaluation
→ Interactive Demo
```

Phases 1–8 are complete. Phases 9–14 deliver corpus content, demo workflow, real model integration, benchmark evaluation, and interactive chat.

---

# Phase 1 — Foundation

Goal:

Establish project structure, development workflow, and architectural boundaries.

Plans:

* Plan 01 — Project Bootstrap *(completed)*
* Plan 02 — Python Bootstrap *(completed)*

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

* Plan 03 — Domain Models *(completed)*

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

* Plan 04 — Storage Layer *(completed)*
* Plan 05 — Indexing Pipeline *(completed)*

Deliverables:

* Qdrant integration
* document loading
* chunking
* embedding generation (stub provider)
* indexing workflow

Key Principle:

Indexing and retrieval are separate concerns.

---

# Phase 4 — Retrieval

Goal:

Implement production-style retrieval.

Plans:

* Plan 06 — Dense Retrieval *(completed)*
* Plan 07 — Sparse Retrieval *(completed)*
* Plan 08 — Fusion *(completed)*
* Plan 09 — Reranking *(completed)*

Deliverables:

* vector retrieval
* BM25 retrieval
* rank fusion
* reranking (stub reranker)

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

Notes:

At Phase 4 completion, dense, sparse, and reranker paths used development stubs. Real model runtimes were delivered in Phases 11–12 (Plans 16–17).

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
* durable conversation memory and LangGraph checkpointers

Interactive CLI chat UX is deferred to Phase 14 (Plan 19).

---

# Phase 8 — Evaluation

Goal:

Measure retrieval quality and demonstrate production practices.

Plans:

* Plan 13 — Evaluation Framework *(completed: [13-evaluation-framework.md](../completed/13-evaluation-framework.md))*

Deliverables *(Plan 13 — implemented)*:

* retrieval metrics (Hit Rate@K, Recall@K, MRR)
* committed retrieval benchmark (`data/evaluation/retrieval_benchmark_v1.json`)
* `EvaluationRunner` and strategy comparison (`ComparisonReport`)
* evaluation layer in `knowledge_assistant.evaluation`

Deferred *(not part of Plan 13; future plans)*:

* CLI subcommand wiring for evaluation output — Phase 13 (Plan 18)
* full-benchmark integration tests against indexed corpus — Phase 13 (Plan 18)

**Next roadmap phase (at Phase 8 completion):** Phase 9 — Synthetic Knowledge Base (Plan 14). Phases 9–12 are now complete; see Phase 13 for the current next phase.

---

# Phase 9 — Synthetic Knowledge Base

Goal:

Create the canonical AcmeCloud Analytics enterprise corpus.

Plans:

* Plan 14 — Synthetic Corporate Knowledge Base *(completed: [14-synthetic-knowledge-base.md](../completed/14-synthetic-knowledge-base.md))*

Scope:

* 80–100 markdown documents
* realistic company structure
* cross-linked documentation
* policies
* runbooks
* platform architecture docs
* RFCs
* postmortems
* internal service catalog

Deliverables *(Plan 14 — implemented)*:

* corpus specification — [14-synthetic-knowledge-base.md](../completed/14-synthetic-knowledge-base.md)
* tracked generator assets under `tools/knowledge_generator/` with manifest, templates, and quality gates
* local generated corpus — **96** markdown files under gitignored `knowledge/` (regenerate: `python3 tools/knowledge_generator/generator.py`)
* `knowledge/README.md` corpus index (generated locally)
* benchmark-aligned policy and procedure paths for `retrieval_benchmark_v1.json`
* `.gitignore` entry for `knowledge/`

Notes:

This phase is **content-only**. No retrieval, indexing, CLI, MCP, agent, or model changes.

Generated corpus files are **not** source-controlled. The repository tracks the specification, generator, templates, manifest, quality gates, and regeneration instructions.

The local `knowledge/` tree is the single canonical knowledge base for demo bootstrap, benchmark evaluation, and interactive chat after generation. Fresh clones can regenerate it with `python3 tools/knowledge_generator/generator.py`. Do not create a separate demo corpus.

---

# Phase 10 — Demo Bootstrap Experience

Goal:

Provide a zero-to-working-demo experience.

Plans:

* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md) *(completed)*

User flow:

```text
git clone
docker compose up
rag demo load
rag chat
```

Scope:

* CLI demo commands
* corpus discovery against `knowledge/` from Plan 14
* indexing execution
* collection initialization
* demo status commands

Commands:

* `rag demo info` — corpus and index status
* `rag demo load` — index the canonical corpus
* `rag demo reset` — reset demo index state

Notes:

The workflow must use the canonical knowledge corpus created in Plan 14. Do not create a separate demo corpus.

Interactive chat is deferred to Phase 14 (Plan 19). This phase delivers bootstrap and indexing only.

---

# Phase 11 — Real Embeddings Integration

Goal:

Replace stub embedding providers with production models.

Plans:

* Plan 16 — Real Dense Embeddings Integration *(completed: [16-real-dense-embeddings-integration.md](../completed/16-real-dense-embeddings-integration.md))*

Scope:

* BAAI/bge-m3
* indexing embeddings (`EmbeddingProvider`)
* retrieval query embeddings (`QueryEmbeddingProvider`)

Notes:

Indexing sparse vector generation remains a separate concern (see ADR-020). This plan targets dense embedding paths only.

---

# Phase 12 — Real Reranker Integration

Goal:

Replace stub reranker with production cross-encoder.

Plans:

* Plan 17 — Real Reranker Integration *(completed: [17-real-reranker.md](../completed/17-real-reranker.md))*

Scope:

* BAAI/bge-reranker-v2-m3

**Next roadmap phase:** Phase 13 — End-to-End Evaluation (Plan 18).

---

# Phase 13 — End-to-End Evaluation

Goal:

Run Dense vs Sparse vs Fusion vs Rerank against the evaluation benchmark using real indexed corpus data.

Plans:

* Plan 18 — Retrieval Strategy Evaluation *(completed)*

Scope:

* index canonical corpus (via Plan 15 bootstrap)
* run all four retrieval strategies through `EvaluationRunner` via `rag evaluate`
* produce side-by-side strategy comparison

Outputs:

* `ComparisonReport` via `rag evaluate compare`
* retrieval metrics (Hit Rate@K, Recall@K, MRR)
* CLI stdout reports

Notes:

Requires Plan 14 corpus, Plan 15 bootstrap workflow, and real model integration (Phases 11–12) for meaningful absolute benchmark quality. Framework and benchmark from Plan 13 are prerequisites. Stub provider modes verify wiring without authoritative model-quality claims (ADR-070).

**Next roadmap phase:** Phase 14 — Interactive Chat Experience (Plan 19).

Goal:

Deliver the user-facing conversational demo.

Plans:

* Plan 19 — Interactive Chat Experience *(backlog — not yet authored)*

Scope:

* CLI chat (`rag chat`)
* agent integration
* MCP integration
* source citations
* conversational demo UX

Notes:

Completes the lecture demonstration path begun in Phase 10. Depends on indexed corpus, real models, and working agent/MCP wiring.

---

# Architectural Priorities

The project prioritizes:

1. Retrieval quality
2. Source attribution
3. MCP integration
4. Agent orchestration
5. Realistic demo experience

The project does not prioritize:

* multi-agent systems
* distributed infrastructure
* production deployment
* enterprise platform features

The retrieval layer is the most important subsystem in the project.

All higher-level functionality depends on retrieval quality.
