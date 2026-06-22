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

Plan 12 delivers the LangGraph agent in `knowledge_assistant.agent` — graph routing, MCP tool adapters, RAG prompts, `run_turn`, and Plan 19 streaming turn execution with `TurnResult` / `TurnStream`. See [Plan 12](docs/plans/completed/12-langgraph-agent.md) and [Plan 19](docs/plans/completed/19-interactive-chat-demo.md).

## Interactive Chat

Plan 19 delivers `rag chat` — streaming interactive REPL and single-turn mode against the indexed corpus.

**Prerequisites:** demo corpus indexed (`rag demo load`), LLM gateway configured in `.env` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).

```bash
# After demo bootstrap (see Demo Bootstrap below)
cp .env.example .env   # configure LLM_* variables

# Interactive streaming REPL (default)
uv run rag chat

# Single turn (testing / scripts)
uv run rag chat --message "What is the remote work policy?"

# Explicit non-streaming
uv run rag chat --no-stream --message "Summarize vacation policy"

# Omit structured Sources block
uv run rag chat --no-sources
```

Chat validates corpus and index preconditions at startup (exit `3` if missing). It does **not** probe the LLM at startup — connectivity is checked on the first message. For meaningful retrieval quality, enable real embeddings/reranker and reindex before chatting.

See [Plan 19](docs/plans/completed/19-interactive-chat-demo.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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

## Real Dense Embeddings (BGE-M3)

Plan 16 adds opt-in real `BAAI/bge-m3` dense embeddings for indexing and retrieval. Stub providers remain the default for CI and fast local development.

```bash
export RAG_EMBEDDING_MODE=real
export RAG_EMBEDDING_DEVICE=cpu   # or cuda when GPU is available
uv run rag demo info
```

The first real embedding run may download `BAAI/bge-m3` from Hugging Face. When `RAG_EMBEDDING_DEVICE=cuda` is set but CUDA is unavailable, initialization fails fast without falling back to CPU.

**Reindex after switching stub → real** (vectors are incompatible):

```bash
uv run rag demo load --rebuild --approve
```

Useful settings: `RAG_EMBEDDING_MODEL`, `RAG_EMBEDDING_BATCH_SIZE`, `RAG_EMBEDDING_MAX_LENGTH`, `RAG_EMBEDDING_NORMALIZE`, and `RAG_EMBEDDING_ENABLE_REAL_TESTS=true` for the optional local real-model smoke test — see `.env.example`.

**Evaluation comparison:** index with stub vs real bootstrap settings, run `rag evaluate run` or `rag evaluate compare` — see [Retrieval Evaluation](#retrieval-evaluation).

See [Plan 16](docs/plans/completed/16-real-dense-embeddings-integration.md).

## Real Reranker

Plan 17 adds an opt-in real BGE reranker behind the existing retrieval protocol. Stub reranking remains the default for fast local runs and CI.

To enable the real reranker for demo retrieval wiring:

```bash
export RAG_RERANKER_MODE=real
export RAG_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
export RAG_RERANKER_DEVICE=cpu   # or auto, cuda, cuda:0
uv run rag demo info
```

`rag demo info` reports the configured reranker mode/model but does not load the model. The first non-empty real rerank call loads `FlagEmbedding` and may download model weights from Hugging Face unless they are already cached. CPU is supported; GPU users can set `RAG_RERANKER_DEVICE=cuda` or an explicit device and may set `RAG_RERANKER_USE_FP16=true` for supported GPU execution.

Useful settings: `RAG_RERANKER_BATCH_SIZE` (default `16`), `RAG_RERANKER_MAX_LENGTH` (default `1024`), and `RAG_RERANKER_ENABLE_REAL_TESTS=true` for the optional local real-model smoke test — see `.env.example`. Scores from the real reranker are ordinal relevance scores, not probabilities.

See [Plan 17](docs/plans/completed/17-real-reranker.md).

## Retrieval Evaluation

Plan 13 delivers the retrieval evaluation layer in `knowledge_assistant.evaluation` — benchmark loading, Hit Rate@K / Recall@K / MRR metrics, `EvaluationRunner`, and multi-strategy `ComparisonReport` assembly. The committed benchmark lives under `data/evaluation/`.

Plan 18 wires evaluation execution through the `rag` CLI after the corpus is indexed:

```bash
# Prerequisites: corpus generated and indexed (see Demo Bootstrap above)
uv run rag demo load

# Evaluate one strategy
uv run rag evaluate run --strategy dense
uv run rag evaluate run --strategy sparse
uv run rag evaluate run --strategy fusion
uv run rag evaluate run --strategy rerank

# Compare all four canonical strategies
uv run rag evaluate compare
```

Optional flags: `--dataset PATH` (default `data/evaluation/retrieval_benchmark_v1.json`), `--eval-top-k INT` (default `5`), `--metrics-k` comma-separated (default `1,3,5`).

**Stub vs real benchmarks (ADR-070):** evaluate inherits `RAG_EMBEDDING_MODE` and `RAG_RERANKER_MODE` from bootstrap. Stub modes run successfully and are useful for wiring checks, but absolute metric values are not authoritative for lecture claims about BGE-M3 or the BGE reranker. For meaningful benchmark numbers:

```bash
export RAG_EMBEDDING_MODE=real
export RAG_RERANKER_MODE=real   # optional; affects rerank strategy only
uv run rag demo load --rebuild --approve
uv run rag evaluate compare
```

Evaluate fails with exit code `3` when the collection is missing or empty — run `rag demo load` first.

See [Plan 13](docs/plans/completed/13-evaluation-framework.md), [Plan 18](docs/plans/completed/18-retrieval-strategy-evaluation.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
