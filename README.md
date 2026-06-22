# Production RAG Knowledge Assistant

Educational project demonstrating a production-style knowledge assistant using LangGraph, MCP, LlamaIndex, Qdrant, hybrid retrieval, and reranking.

## Getting Started

Read the following documents in order before contributing or implementing changes:

1. [AGENTS.md](AGENTS.md) — agent and contributor guide
2. [PROJECT.md](PROJECT.md) — project vision, scope, and goals
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture and component boundaries
4. [docs/plans/active/](docs/plans/active/) — authorized implementation scope (empty when no plan is active)

Additional references:

* [docs/DECISIONS.md](docs/DECISIONS.md) — architectural decision records
* [docs/PROGRESS.md](docs/PROGRESS.md) — development history
* [docs/plans/backlog/ROADMAP.md](docs/plans/backlog/ROADMAP.md) — long-term direction (informational)

Documentation is the source of truth. Implementation follows active plans.

## Agent Orchestration

Plan 12 delivers the LangGraph agent in `knowledge_assistant.agent` — graph routing, MCP tool adapters, RAG prompts, and `run_turn` for conversational turns. Interactive CLI chat (`rag chat`) remains Plan 19. See [Plan 12](docs/plans/completed/12-langgraph-agent.md) and [docs/PROGRESS.md](docs/PROGRESS.md).

## Demo Bootstrap

Plan 15 delivers the demo composition root and CLI commands for indexing the canonical corpus into Qdrant.

**Prerequisites:** Python 3.12+, `uv sync`, Qdrant reachable at `QDRANT_URL` (default `http://localhost:6333`).

```bash
# 1. Generate the synthetic corpus (Plan 14)
python3 tools/knowledge_generator/generator.py

# 2. Inspect demo readiness (read-only)
uv run rag demo info

# 3. Index corpus into Qdrant
uv run rag demo load

# 4. Confirm index ready
uv run rag demo info
```

To replace an existing collection (both flags required):

```bash
uv run rag demo load --rebuild --approve
```

To delete the demo collection:

```bash
uv run rag demo reset --approve
```

Optional environment variable: `RAG_CORPUS_ROOT` (default `knowledge`) overrides the corpus directory path.

See [Plan 15](docs/plans/completed/15-demo-bootstrap-workflow.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Real Dense Embeddings

Plan 16 delivers an opt-in BGE-M3 dense embedding runtime. Default demo and CI wiring still use stub providers.

1. Copy and edit environment variables (see `.env.example`):

| Variable | Purpose |
| -------- | ------- |
| `RAG_EMBEDDING_MODE` | `stub` (default) or `real` |
| `RAG_EMBEDDING_MODEL` | Hugging Face model id (default `BAAI/bge-m3`) |
| `RAG_EMBEDDING_DEVICE` | `cpu`, `cuda`, or `mps` |
| `RAG_EMBEDDING_BATCH_SIZE` | Passage batch size for indexing |
| `RAG_EMBEDDING_MAX_LENGTH` | Token limit for encoding |
| `RAG_EMBEDDING_NORMALIZE` | L2-normalize vectors (`true`/`false`) |

2. Enable real embeddings and rebuild the index (vectors are incompatible with stub mode):

```bash
export RAG_EMBEDDING_MODE=real
uv run rag demo load --rebuild --approve
```

3. Confirm pipeline mode:

```bash
uv run rag demo info
```

Optional real-model smoke tests (not run in default CI):

```bash
uv run pytest -m embedding_model
```

See [Plan 16](docs/plans/completed/16-real-dense-embeddings-integration.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Retrieval Evaluation

Plan 13 delivers the retrieval evaluation layer in `knowledge_assistant.evaluation` — benchmark loading, Hit Rate@K / Recall@K / MRR metrics, `EvaluationRunner`, and multi-strategy `ComparisonReport` assembly. The committed benchmark lives under `data/evaluation/`. See [Plan 13](docs/plans/completed/13-evaluation-framework.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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

## Local LLM Setup

Plan 11 provides an OpenAI-compatible LLM boundary for chat completions. For local development against vLLM or another compatible gateway:

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Edit `.env` and set at minimum:

| Variable | Purpose |
| -------- | ------- |
| `LLM_BASE_URL` | OpenAI-compatible base URL (e.g. `http://localhost:8000/v1`) |
| `LLM_API_KEY` | Bearer token (vLLM often accepts `local`) |
| `LLM_MODEL` | Model name served by the endpoint |

Optional generation defaults: `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`.

3. Optional manual connectivity check (not run in CI):

```python
from knowledge_assistant.llm import (
    ChatMessage,
    ChatRole,
    LlmSettings,
    OpenAICompatibleLLMClient,
)

settings = LlmSettings.from_env()
client = OpenAICompatibleLLMClient(settings)
result = client.chat(
    (ChatMessage(role=ChatRole.USER, content="Reply with the word ok."),),
)
print(result.content)
```

Load `.env` into your shell before calling `from_env()` (for example with your shell or process manager). The library does not load `.env` at runtime.
