# Production RAG Knowledge Assistant

Educational project demonstrating a production-style knowledge assistant using LangGraph, MCP, LlamaIndex, Qdrant, hybrid retrieval, and reranking.

## Getting Started

Read the following documents in order before contributing or implementing changes:

1. [AGENTS.md](AGENTS.md) — agent and contributor guide
2. [PROJECT.md](PROJECT.md) — project vision, scope, and goals
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture and component boundaries
4. [docs/plans/active/](docs/plans/active/) — authorized implementation scope

Additional references:

* [docs/DECISIONS.md](docs/DECISIONS.md) — architectural decision records
* [docs/PROGRESS.md](docs/PROGRESS.md) — development history

Documentation is the source of truth. Implementation follows active plans.

## Python Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

Install dependencies and create the local virtual environment:

```bash
uv sync
```

Run all development tools through `uv run`. Do not invoke `pytest`, `ruff`, or `basedpyright` directly.

## Validation

From the repository root, run the full quality suite before committing:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

Standard validation is mandatory for all commits. The bootstrap validation exception (pre-`pyproject.toml` documentation-only commits) was superseded when [Plan 02 — Python Bootstrap](docs/plans/completed/02-python-bootstrap.md) completed.
