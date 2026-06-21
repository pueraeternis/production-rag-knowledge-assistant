# Agent Guide — Production RAG Knowledge Assistant

## Repository Purpose

Production RAG Knowledge Assistant is an educational project demonstrating modern enterprise knowledge assistant architecture built with:

* LangGraph
* MCP (Model Context Protocol)
* LlamaIndex
* Qdrant
* Hybrid Retrieval
* Reranking
* OpenAI-compatible LLMs

The repository serves as a practical implementation accompanying a Production RAG lecture.

The project intentionally prioritizes architectural clarity over production-scale complexity.

Documentation is the source of truth.

---

## Read-First Order

1. AGENTS.md (this file)
2. PROJECT.md
3. docs/ARCHITECTURE.md
4. docs/DECISIONS.md
5. docs/plans/active/
6. docs/PROGRESS.md

Always understand the documented architecture before implementing changes.

---

## Documentation Precedence

When sources conflict, use the following precedence:

1. PROJECT.md
2. docs/ARCHITECTURE.md
3. docs/DECISIONS.md
4. docs/plans/active/
5. docs/PROGRESS.md
6. Chat Context

Repository artifacts override conversational context.

---

## Agent Execution Workflow

1. Read AGENTS.md.
2. Read PROJECT.md.
3. Read docs/ARCHITECTURE.md.
4. Read docs/DECISIONS.md.
5. Read docs/plans/active/.
6. Verify scope.
7. Implement only what is covered by the active plan.
8. Update documentation when architectural decisions are introduced.
9. Record progress after completing work.

---

## Core Architecture

The system consists of four major layers:

```text
User
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

All knowledge access must happen through MCP tools and resources.

---

## Project Scope

The project demonstrates:

* conversational knowledge assistant;
* MCP integration;
* document indexing;
* hybrid retrieval;
* reranking;
* source attribution;
* retrieval evaluation.

The project is intentionally limited to a single knowledge assistant use case.

---

## Non-Goals

Do not introduce:

* multi-agent systems;
* microservices;
* distributed architecture;
* Kubernetes;
* PostgreSQL;
* Redis;
* authentication systems;
* Langfuse;
* LLM-as-a-Judge;
* workflow orchestration platforms;
* production infrastructure.

If a feature is not explicitly required by PROJECT.md or an active plan, do not implement it.

---

## Agent Responsibilities

The LangGraph agent is responsible for:

* conversation handling;
* chat history;
* intent classification;
* tool selection;
* response generation;
* query rewriting.

The agent is the only component that communicates with the LLM.

---

## MCP Responsibilities

The Knowledge MCP Server is responsible for:

* indexing documents;
* searching documents;
* retrieving document content;
* exposing knowledge-related tools;
* exposing knowledge-related resources.

The MCP server must not implement agent behavior.

The MCP server is a tool provider, not an autonomous system.

---

## Retrieval Responsibilities

The retrieval layer is responsible for:

* dense retrieval;
* sparse retrieval;
* result fusion;
* reranking;
* source metadata management.

The retrieval layer must not communicate with the LLM directly.

---

## Human-in-the-Loop

Potentially destructive operations require explicit user approval.

Examples:

* index rebuild;
* reindexing documents;
* index replacement.

The system must never modify the knowledge index without user confirmation.

---

## Source Attribution

All knowledge answers must be grounded in retrieved content.

The system should expose:

* document title;
* document path;
* section title;
* line range.

Users must always be able to inspect answer sources.

---

## Technology Constraints

Required technologies:

* Python
* LangGraph
* MCP
* LlamaIndex
* Qdrant
* BAAI/bge-m3
* BAAI/bge-reranker-v2-m3

Use `uv` for dependency management.

Quality commands (required after Python bootstrap):

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

### Bootstrap Validation Exception

**Status:** Superseded (Python bootstrap completed — see [docs/PROGRESS.md](docs/PROGRESS.md)).

Before `pyproject.toml` existed, documentation-only commits were exempt from the quality commands above.

Standard validation is now mandatory for all commits.

---

## Documentation as Source of Truth

| Artifact               | Purpose                         |
| ---------------------- | ------------------------------- |
| PROJECT.md             | Project vision and scope        |
| docs/ARCHITECTURE.md   | System architecture             |
| docs/DECISIONS.md      | Architectural decisions         |
| docs/PROGRESS.md       | Development history             |
| docs/plans/active/     | Authorized implementation scope |

When code and documentation disagree:

* update code to match documentation; or
* update documentation if the architectural change is intentional.

Never leave the repository in an inconsistent state.

---

## Roadmap

For long-term project direction see:

docs/plans/backlog/ROADMAP.md

The roadmap is informational only and does not authorize implementation.