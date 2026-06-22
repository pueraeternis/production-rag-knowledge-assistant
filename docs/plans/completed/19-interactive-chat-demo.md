# Plan 19 — Interactive Chat Demo

**Status:** Completed

**Created:** 2026-06-22

**Revised:** 2026-06-22 (architectural corrections — streaming capability protocol, turn result boundary, no LLM probe, no auto-fallback, graph topology preserved)

**Roadmap:** Phase 14 — Interactive Chat Experience

**Depends on:**

* [Plan 10 — Knowledge MCP Server](../completed/10-knowledge-mcp-server.md)
* [Plan 11 — LLM Boundary](../completed/11-llm-boundary.md)
* [Plan 12 — LangGraph Agent](../completed/12-langgraph-agent.md)
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md)
* [Plan 16 — Real Dense Embeddings Integration](../completed/16-real-dense-embeddings-integration.md)
* [Plan 17 — Real Reranker Integration](../completed/17-real-reranker.md)
* [Plan 18 — Retrieval Strategy Evaluation](../completed/18-retrieval-strategy-evaluation.md)

**Plan principle:** One plan introduces one architectural capability. Plan 19 introduces the **interactive CLI chat workflow** — wiring existing agent, LLM, MCP adapters, and bootstrap retrieval stack into a **streaming** terminal REPL. It does **not** introduce retrieval algorithms, **LangGraph topology changes**, MCP transport, memory persistence, or evaluation features.

---

## Authorization

**Active.** ADR-042 through ADR-046 (Plan 12 carryover) and ADR-071 through ADR-080 to be recorded in `docs/DECISIONS.md` during implementation.

---

## Objective

Deliver the final lecture demonstration path:

```text
User
  ↓
rag chat
  ↓
CLI (REPL / single-turn / terminal rendering)
  ↓
Bootstrap (ChatSession assembly, turn facades)
  ↓
LangGraph Agent (existing graph; streaming as execution strategy)
  ↓
LLM Boundary (chat + optional StreamingLLMClient capability)
  ↓
MCP Tool Adapters
  ↓
Retrieval Layer (canonical rerank stack)
  ↓
Qdrant
```

After this plan is complete:

* a developer can run **`rag chat`** for an interactive streaming REPL against the indexed Plan 14 corpus;
* **`rag chat --message TEXT`** executes a single turn and exits (testing and scripting);
* assistant answers **stream to the terminal by default** via a typed stream abstraction; final text is accumulated into `AgentState`;
* **source attribution renders after stream completion** from structured `TurnResult.sources` — not by CLI reparsing MCP JSON from message history;
* startup prints **diagnostics** (index status, pipeline label, LLM configuration) — **without** a test LLM request;
* all dependency assembly lives in **`knowledge_assistant.bootstrap`** — not duplicated in CLI;
* streaming failures do not corrupt conversation state; the REPL remains usable;
* validation suite passes with unit/integration tests and import-boundary enforcement.

**LangGraph constraint (explicit):** Plan 19 must **not** redesign LangGraph execution. Specifically:

* **no new graph nodes**;
* **no new graph routes** or conditional edges;
* **no new `GraphState` fields** or state types;
* **no graph topology changes**.

Streaming is an **execution strategy around the existing Plan 12 graph** — not a graph redesign.

**Ownership boundaries (explicit):**

| Concern | Owner |
| ------- | ----- |
| Retrieval algorithms and scoring | `knowledge_assistant.retrieval` |
| MCP handler contracts and formatting | `knowledge_assistant.mcp_server` |
| LangGraph orchestration and turn execution | `knowledge_assistant.agent` |
| Model HTTP transport (sync + streaming capability) | `knowledge_assistant.llm` |
| Chat dependency assembly and turn facades | `knowledge_assistant.bootstrap` |
| Terminal REPL, stream consumption, source display, signals | `knowledge_assistant.cli` |

**Streaming ownership (explicit):**

| Concern | Owner |
| ------- | ----- |
| Streaming transport (SSE/chunk parsing) | `llm` (`StreamingLLMClient`) |
| Typed turn stream and `TurnResult` assembly | `agent` |
| Stream consumption and terminal rendering | `cli` |
| `ChatSession` wiring and turn facades | `bootstrap` |

Plan 19 must not implement, stub, or partially deliver query rewriting, retrieval retry, MCP SDK transport, session persistence, transcript export, startup LLM probes, or automatic streaming fallback.

---

## Prerequisites and Integration Context

Plans 10–18 deliver the integration surface Plan 19 consumes without redesign:

| Layer | Ready for Plan 19 | Gap Plan 19 closes |
| ----- | ----------------- | ------------------ |
| **MCP (Plan 10)** | `search_documents`, indexing handlers, `SourceReferenceSchema` | Tier 2 tools, MCP SDK — remain deferred |
| **LLM (Plan 11)** | `LLMClient.chat()`, `OpenAICompatibleLLMClient`, `StubLLMClient` | Optional **`StreamingLLMClient`** capability — Plan 19 adds without changing `LLMClient` |
| **Agent (Plan 12)** | `run_turn`, `StateGraph`, `ToolRegistry`, MCP adapters | No CLI, no streaming, no `TurnResult` boundary |
| **Bootstrap (Plan 15)** | `build_demo_environment()`, `DemoEnvironment`, `rag demo *` | Does not wire LLM, agent, or tool registry |
| **Embeddings (Plan 16)** | `RAG_EMBEDDING_MODE`, BGE-M3 runtime | Sparse indexing still stub (ADR-020) — not chat scope |
| **Reranker (Plan 17)** | `RAG_RERANKER_MODE`, `BgeReranker` | Chat uses canonical rerank stack only |
| **Evaluate (Plan 18)** | Precondition/exit-code patterns, CLI import boundaries | Chat mirrors index preconditions, not evaluation logic |

**Deferred items that remain deferred:** query rewriting and retrieval retry (Plan 12b), MCP SDK transport (Plan 12c), durable memory/checkpointers, transcript export, web UI, REST API, Tier 2 MCP tools.

**Documentation gap to resolve:** ADR-042 through ADR-046 (Plan 12) are documented in the completed plan but not yet accepted in `docs/DECISIONS.md`. Plan 19 implementation accepts them retroactively.

---

## Required User Workflow

The lecture and README chat path after Plan 19:

```text
# 1. Generate canonical corpus (Plan 14)
python3 tools/knowledge_generator/generator.py

# 2. Start Qdrant (operator responsibility)
# default: http://localhost:6333

# 3. Index corpus (Plan 15)
rag demo info
rag demo load

# 4. Configure LLM endpoint
# copy .env.example → .env; set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

# 5. (Recommended) Enable real models and reindex
export RAG_EMBEDDING_MODE=real
export RAG_RERANKER_MODE=real
rag demo load --rebuild --approve

# 6. Interactive streaming chat (Plan 19)
rag chat

# 7. Single-turn mode (testing, scripts)
rag chat --message "What is the remote work policy?"

# 8. Explicit non-streaming mode
rag chat --no-stream --message "Summarize vacation policy"

# 9. Omit source block
rag chat --no-sources
```

Prerequisites assumed by the workflow:

* Python 3.12+ and `uv sync` completed;
* Qdrant reachable at configured URL;
* Plan 14 corpus generated locally under `knowledge/`;
* demo collection populated (`rag demo load`) before `rag chat`;
* LLM gateway reachable at `LLM_BASE_URL` when the operator sends the first message (connectivity validated by first turn, not startup probe);
* meaningful retrieval quality benefits from real embeddings/reranker per Plans 16–17 (not required for wiring).

Plan 19 does **not** add corpus generation, Docker Compose, automatic indexing inside `rag chat`, or startup LLM health checks.

---

## Scope

### Authorized implementation areas

| Area | Purpose |
| ---- | ------- |
| `src/knowledge_assistant/llm/` | `StreamingLLMClient` capability protocol, SSE transport |
| `src/knowledge_assistant/agent/` | `TurnResult`, `TurnStream`, streaming execution strategy (no graph topology change) |
| `src/knowledge_assistant/bootstrap/` | `ChatSession`, `build_chat_session()`, turn facades |
| `src/knowledge_assistant/cli/` | `chat` subcommand, REPL, stream consumption, rendering |
| `tests/unit/llm/` | Streaming capability and SSE client tests |
| `tests/unit/agent/` | Turn stream and `TurnResult` tests |
| `tests/unit/bootstrap/` | Chat session assembly tests |
| `tests/unit/cli/` | Chat parsing, rendering, import boundaries |
| `tests/integration/chat/` | End-to-end chat with stub LLM |
| `docs/ARCHITECTURE.md` | CLI chat section, streaming ownership, turn result boundary |
| `docs/DECISIONS.md` | ADR-042–046 acceptance + ADR-071–080 |
| `docs/PROGRESS.md` | Plan 19 completion entry |
| `docs/plans/backlog/ROADMAP.md` | Phase 14 status update on completion |
| `README.md` | Chat quickstart |

### In Scope

* `rag chat` CLI subcommand with interactive REPL;
* **streaming assistant responses by default**;
* **Plan 11 `LLMClient.chat()` contract unchanged**;
* optional **`StreamingLLMClient`** capability protocol with `stream_chat(...)`;
* `OpenAICompatibleLLMClient` implements `StreamingLLMClient`;
* `StubLLMClient` remains `LLMClient` only — not forced to stream; tests may use a separate `StreamingStubLLMClient` test double;
* agent exposes **`TurnStream`** (`Iterator[StreamChunk]`) and returns **`TurnResult`** with structured `sources`;
* **no stdout callbacks** passed into agent or bootstrap turn execution;
* tool-loop rounds use `chat()`; **final** user-visible answer uses `stream_chat()` when streaming enabled and client supports `StreamingLLMClient`;
* accumulated final assistant `ChatMessage` committed to `AgentState` only after successful stream completion;
* CLI renders sources from **`TurnResult.sources`** after stream completion;
* startup diagnostics banner (configuration only);
* bootstrap `ChatSession` assembling `DemoEnvironment`, `LLMClient`, `ToolRegistry`, `AgentSettings`;
* precondition checks: corpus directory, non-empty collection, LLM **configuration** resolvable (`LlmSettings.from_env()`);
* flags: `--message`, `--no-stream`, `--no-sources`;
* graceful exit: `exit`, `quit`, EOF (`Ctrl-D`), clean shutdown;
* **Ctrl-C during generation:** cancel stream consumption, do not append partial assistant message to state;
* single-turn `--message` mode for tests;
* unit and integration tests per [Testing Strategy](#testing-strategy);
* ADR-042–046 acceptance (Plan 12 carryover) + ADR-071–080;
* documentation updates listed above.

### Non-Scope

Plan 19 does **not** authorize:

* memory persistence, LangGraph checkpointers, vector memory, session files;
* query rewriting, retrieval retry, intent classification nodes (Plan 12b);
* MCP SDK transport (Plan 12c);
* web UI, REST API, WebSockets, SSE **servers**;
* authentication, multi-user support, observability platforms;
* **LangGraph topology changes** — no new nodes, routes, or `GraphState` fields;
* retrieval algorithm changes or new strategies;
* changes to `EvaluationRunner`, benchmark, or `rag evaluate`;
* **transcript export** or conversation logging to disk;
* automatic indexing inside `rag chat`;
* interactive `input()` approval prompts for indexing (remain flag-based per ADR-054);
* async `asyncio` graph execution or async LLM client;
* Tier 2 MCP tools or MCP resources;
* sparse BGE-M3 indexing (ADR-020);
* multi-session management (parallel sessions, session IDs);
* LLM-as-a-Judge or answer quality evaluation;
* new evaluation features or benchmark changes;
* **startup LLM connectivity probes** or test requests to the model;
* **`--skip-llm-probe`** or equivalent probe flags;
* **`RAG_CHAT_STREAM_FALLBACK`** or automatic non-streaming retry;
* **CLI reparsing MCP JSON from `AgentState.messages`** for source display.

---

## Architectural Decisions (Proposed ADRs)

Record in `docs/DECISIONS.md` during implementation.

### ADR-042 through ADR-046 — LangGraph Agent (Plan 12 carryover)

**Status:** Accepted (retroactive acceptance during Plan 19 documentation pass)

Accept the five agent ADRs as documented in [Plan 12](../completed/12-langgraph-agent.md):

* **ADR-042** — LangGraph agent boundary
* **ADR-043** — In-process MCP handler adapters before SDK transport
* **ADR-044** — Agent tool registry and dispatch
* **ADR-045** — In-memory conversation state only
* **ADR-046** — RAG prompt and citation contract

No semantic changes to Plan 12 decisions. Plan 19 extends ADR-045: CLI holds `AgentState` in process memory for REPL duration only.

---

### ADR-071 — Chat Execution Ownership

**Status:** Proposed

#### Context

Plan 12 delivers `run_turn` but no user-facing execution path. Plan 15 bootstrap assembles retrieval only. Without explicit ownership, chat loop logic could land in `agent/` (UI concerns), `cli/` (dependency construction), or ad hoc scripts.

#### Decision

* **Chat execution** is the workflow: assemble session → validate prerequisites → run conversation turns → consume typed streams → render output. It is not a new top-level package.
* **CLI (`knowledge_assistant.cli.chat`)** owns:
  * argument parsing;
  * interactive REPL loop and prompts;
  * **consuming** `TurnStream` and writing chunks to `stdout`;
  * post-turn source rendering from `TurnResult.sources`;
  * signal handling (`Ctrl-C`, `Ctrl-D`);
  * exit codes.
* **Bootstrap (`knowledge_assistant.bootstrap`)** owns:
  * `ChatSession` assembly (`DemoEnvironment` + `LLMClient` + `ToolRegistry` + settings);
  * `build_chat_session()` factory;
  * thin facades delegating to agent turn APIs (**no REPL logic, no stdout callbacks**).
* **Agent (`knowledge_assistant.agent`)** owns:
  * turn orchestration via **existing** LangGraph graph;
  * `TurnStream` and `TurnResult` production;
  * structured source extraction during turn execution;
  * `AgentState` transitions.
* **LLM (`knowledge_assistant.llm`)** owns transport only.

MCP, retrieval, indexing, and evaluation do not participate in chat CLI orchestration beyond injected dependencies.

#### Consequences

* `cli/chat.py` imports `bootstrap` only (plus stdlib), matching `demo.py` / `evaluate.py` pattern.
* Agent never receives terminal callbacks or `stdout` references.
* Integration tests can call bootstrap facades directly or CLI `main([...])`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| REPL inside `agent/repl.py` | Mixes UX with orchestration; violates component ownership |
| `on_delta=write_stdout` in agent/bootstrap | Couples agent to terminal rendering |
| CLI imports `agent` and `llm` directly | Breaks established CLI import boundaries |
| MCP tool `chat` | Chat is user workflow, not knowledge handler |

---

### ADR-072 — Conversation State Lifetime

**Status:** Proposed

#### Context

ADR-045 establishes in-memory graph state without checkpointers. Plan 19 adds a REPL. Operators need clarity on what happens across turns, restarts, and failures.

#### Decision

* **Lifetime:** `AgentState` lives in the **`rag chat` process** for the duration of one CLI invocation.
* **Initialization:** each `rag chat` start creates fresh state with system prompt (`prompts.SYSTEM_PROMPT`) prepended once.
* **Multi-turn:** REPL loop passes updated `AgentState` from prior `TurnResult.state` into each turn facade call.
* **Termination:** process exit discards all state. No persistence.
* **Restart behavior:** re-running `rag chat` starts a **new** conversation with empty history (except system prompt).
* **Partial turn failure:** if a turn fails before successful completion, **do not** append a partial assistant message; on streaming failure mid-generation, revert to pre-turn state snapshot.
* **Multi-session:** **not supported** — one REPL per process; no session IDs.

#### Consequences

* Tests use explicit `AgentState` fixtures per turn sequence.
* No filesystem or database artifacts.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| LangGraph `MemorySaver` checkpointer | Explicit non-scope |
| Append partial assistant text on failure | Corrupts history; complicates recovery |
| Session files | Transcript export is non-scope |

---

### ADR-073 — Session Persistence Policy

**Status:** Proposed

#### Context

Operators may expect chat history to survive restarts. Project non-goals exclude long-term memory. Plan 19 explicitly excludes transcript export and memory persistence.

#### Decision

* **No session persistence** in Plan 19.
* **No transcript export** — stdout is ephemeral.
* **No conversation logging** to repository paths.
* **No checkpointer** configuration on LangGraph compile.
* **Single-process session** — one `AgentState` holder in CLI REPL.

#### Consequences

* Simpler implementation and tests.
* Future persistence requires a new plan and ADR.

---

### ADR-074 — Bootstrap Ownership of Chat Wiring

**Status:** Proposed

#### Context

Plan 15 established bootstrap as demo composition root (ADR-051). Plan 18 extended bootstrap with strategy retrievers (ADR-068). Chat requires LLM + agent + MCP adapter wiring not present in `DemoEnvironment`.

#### Decision

* Add **`bootstrap/chat.py`** with:
  * frozen `ChatSession` dataclass;
  * `build_chat_session(settings?) -> ChatSession`;
  * `initial_agent_state() -> AgentState`;
  * `execute_turn(...) -> TurnResult` (non-streaming);
  * `execute_turn_streaming(...) -> TurnStream` (streaming default path).
* `ChatSession` fields (minimum):
  * `environment: DemoEnvironment`
  * `llm_client: LLMClient`
  * `tool_registry: ToolRegistry`
  * `agent_settings: AgentSettings`
  * `llm_settings: LlmSettings` (for diagnostics banner only)
* Assembly rules:
  * `build_chat_session()` calls `build_demo_environment()` then `build_default_tool_registry(...)`;
  * production LLM: `OpenAICompatibleLLMClient(LlmSettings.from_env())` — implements `StreamingLLMClient`;
  * tests inject `StubLLMClient`, `StreamingStubLLMClient`, or mocks via constructor overrides.
* Bootstrap facades delegate to agent turn APIs and return **`TurnResult` / `TurnStream`** — they do **not** accept rendering callbacks.
* Bootstrap **may import** `knowledge_assistant.agent`, `knowledge_assistant.llm`, `knowledge_assistant.mcp_server.config`.
* Bootstrap must **not** import `cli`.

#### Consequences

* Extends ADR-051 analogously to ADR-068.
* Clean separation: bootstrap wires; agent produces typed results; CLI renders.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Wiring entirely in CLI | Duplicates assembly; violates CLI import rules |
| Facades with `on_delta` callbacks | UI coupling into bootstrap/agent |
| Agent self-wires DemoEnvironment | Boundary violation |

---

### ADR-075 — Source Citation Rendering

**Status:** Proposed

#### Context

ADR-046 assigns citation contract to agent prompts. Users need consistent terminal source blocks. Tool results contain `SourceReferenceSchema` via MCP. Scanning `AgentState.messages` and reparsing MCP JSON in CLI is fragile and couples presentation to message serialization details.

#### Decision

* **Source extraction owner:** **agent** (during turn execution), surfaced through **`TurnResult.sources`**.
* Introduce agent-local structured type (name illustrative):

```python
@dataclass(frozen=True, slots=True)
class TurnSource:
    document_title: str
    document_path: str
    section_title: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class TurnResult:
    state: AgentState
    answer: str
    sources: tuple[TurnSource, ...] = ()
```

* When `search_documents` executes during a turn, agent maps MCP `SearchHitSchema.source` fields into `TurnSource` values and includes them in `TurnResult.sources` (deduplicated by `(document_path, section_title, start_line, end_line)`, preserving search rank order).
* **During streaming:** CLI renders **assistant text chunks only** — no interleaved source blocks.
* **After successful stream completion:** CLI renders a **Sources** section from **`TurnResult.sources`** via `format_turn_sources(sources) -> str` in `cli/chat.py`:

```text
Sources:

[1] Remote Work Policy
    File: policies/remote_work_policy.md
    Section: Work From Another Country
    Lines: 84-112
```

* **`--no-sources`:** skip rendering entirely.
* **CLI must not** scan `AgentState.messages` or reparse MCP tool JSON for sources.
* **Do not re-fetch** from storage or MCP after the turn.
* Retrieval and MCP ownership unchanged — agent reads source fields already present in tool execution results.

#### Consequences

* Source display is deterministic and testable at `TurnResult` boundary.
* CLI formatter tests use `tuple[TurnSource, ...]` fixtures — not raw tool message JSON.
* Model may still cite inline in prose (prompt contract); structured block is authoritative for inspection.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| CLI scans `AgentState.messages` and parses MCP JSON | Fragile; couples CLI to tool serialization |
| Parse citations from assistant text | Fragile; duplicates MCP attribution |
| Stream sources after each token | Noisy UX; violates requirement |
| Storage re-fetch by chunk ID | Agent would bypass MCP |

---

### ADR-076 — Interactive Loop Design

**Status:** Proposed

#### Context

Plan 19 requires REPL, single-turn mode, graceful exit, and streaming default.

#### Decision

* **REPL prompt:** `You: ` (constant in `cli/chat.py` only).
* **Assistant prefix:** none during streaming (raw tokens); newline before sources block when present.
* **Input handling:**
  * empty line → ignore, re-prompt;
  * `exit` / `quit` (case-insensitive, stripped) → clean exit code 0;
  * EOF → clean exit code 0;
  * `--message TEXT` → single turn, no REPL, exit after render.
* **Output routing:** user-visible chat output via `stdout`; errors via `stderr`.
* **Turn sequence (streaming default):**

```text
read user input
  ↓
turn_stream = bootstrap.execute_turn_streaming(session, state, message)
  ↓
for chunk in turn_stream:
    write chunk.content_delta to stdout (flush=True)    ← CLI only
  ↓
turn_result = turn_stream.result()                      ← TurnResult after exhaustion
  ↓
state = turn_result.state
  ↓
print format_turn_sources(turn_result.sources) (unless --no-sources)
  ↓
on failure: state unchanged; print error; continue REPL
```

* **Non-streaming (`--no-stream`):** `turn_result = bootstrap.execute_turn(session, state, message)`; CLI prints `turn_result.answer` at once; then sources.

#### Consequences

* Agent → typed stream; CLI → terminal. No callback coupling.
* Single-turn mode: `rag chat --message "..."`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `on_delta` callback through bootstrap | UI dependency in agent path |
| `prompt_toolkit` / `rich` REPL | New dependencies; out of scope |

---

### ADR-077 — Startup Validation Behavior

**Status:** Proposed

#### Context

`rag evaluate` fails fast on missing index (exit 3). Chat needs operator diagnostics before the first turn. A startup LLM probe adds latency, API cost, and complexity; the first user message naturally validates LLM connectivity.

#### Decision

* **On `rag chat` startup**, after building `ChatSession`, print a **configuration banner**:

```text
Chat ready
  Corpus: knowledge/ (96 documents)
  Collection: knowledge_chunks (12450 chunks)
  Pipeline: dense (bge-m3) + sparse → fusion (RRF) → rerank (bge-reranker-v2-m3)
  Embedding mode: real | Reranker mode: real
  LLM: http://localhost:8000/v1 (model: Qwen/...)
  Streaming: enabled (default)
```

* **Preconditions (fail-fast, exit code 3):**
  * corpus directory exists with ≥1 indexable document (same rules as demo);
  * collection exists and `collection_chunk_count > 0`;
  * `LlmSettings.from_env()` succeeds (required configuration present and valid).
* **No startup LLM request** — no probe, no test completion, no health-check `chat()` call.
* **LLM connectivity** is validated on the **first user turn** (or `--message` turn). Connection failures surface as turn errors (REPL continues) or exit 1 in single-turn mode.
* **Stub provider notice:** when `RAG_EMBEDDING_MODE=stub` or `RAG_RERANKER_MODE=stub`, banner includes non-authoritative retrieval notice (consistent with ADR-070).

#### Consequences

* Faster startup; no spurious API calls.
* Integration tests need no `--skip-llm-probe` flag — inject stub LLM via `build_chat_session(llm_client=...)`.
* Operators configure LLM via `.env`; misconfiguration on missing vars fails at startup (exit 3); unreachable endpoint fails on first turn.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Startup `chat(max_tokens=1)` probe | Unnecessary latency and API calls |
| `--skip-llm-probe` flag | Exists only to compensate for probe; probe removed |
| No preconditions | Poor UX for missing index |
| Auto-run `demo load` | Violates human-in-the-loop |

---

### ADR-078 — Streaming Architecture and Ownership

**Status:** Proposed

#### Context

Plan 11 defines sync non-streaming `LLMClient.chat()` (ADR-037). Plan 19 requires streaming without redesigning agent graph topology, MCP, or retrieval. OpenAI-compatible APIs support SSE on `/chat/completions` with `stream: true`.

#### Decision

**1. Capability-based LLM protocol (Plan 11 contract unchanged):**

```python
@dataclass(frozen=True, slots=True)
class StreamChunk:
    """One incremental model text delta."""
    content_delta: str


class LLMClient(Protocol):
    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        ...


class StreamingLLMClient(LLMClient, Protocol):
    def stream_chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> Iterator[StreamChunk]:
        ...
```

* **`LLMClient` is unchanged** — existing Plan 11 implementations remain valid without modification.
* **Streaming is an optional capability** — `StreamingLLMClient` extends `LLMClient`; only clients that support streaming implement it.
* **`StubLLMClient` stays `LLMClient` only** — not forced to implement `stream_chat`. Tests use `StreamingStubLLMClient` (or inject a streaming fake) when testing stream paths.
* **`OpenAICompatibleLLMClient` implements `StreamingLLMClient`** with SSE parsing.
* Callers that need streaming check capability (e.g. `isinstance(client, StreamingLLMClient)`) before calling `stream_chat`. If streaming is requested but unsupported, fail with a clear error directing the operator to `--no-stream`.

**2. Agent typed stream (no UI callbacks):**

```python
class TurnStream(Protocol):
    def __iter__(self) -> Iterator[StreamChunk]: ...
    def result(self) -> TurnResult:
        """Available after stream exhaustion; raises if turn incomplete."""
        ...
```

* Agent produces `TurnStream` for streaming turns and `TurnResult` for non-streaming turns.
* **Agent never receives stdout callbacks, write functions, or CLI references.**

**3. LangGraph execution constraint:**

* **No new graph nodes, routes, or `GraphState` fields.**
* Streaming is an **execution strategy** around the existing Plan 12 graph:
  * tool-loop rounds invoke existing graph path using **`chat()`** (tool calls require complete `GenerationResult`);
  * final user-visible text generation, when streaming is enabled and client supports `StreamingLLMClient`, uses **`stream_chat()`** outside or at the end of the existing turn flow — without altering `StateGraph` topology.
* `run_turn(...)` remains for non-streaming and backward-compatible tests.

**4. Ownership:**

| Concern | Owner |
| ------- | ----- |
| SSE parsing, HTTP stream | `llm/openai_client.py` |
| `StreamChunk`, `StreamingLLMClient` | `llm/protocol.py`, `llm/messages.py` |
| `TurnStream`, `TurnResult`, source extraction | `agent/` (e.g. `turn.py` or `graph.py`) |
| When to use `stream_chat` vs `chat` | `agent/` turn execution strategy |
| Iterating `TurnStream`, writing to stdout | `cli/chat.py` |
| `ChatSession` wiring, turn facades | `bootstrap/chat.py` |

#### Consequences

* Plan 11 `chat()` tests and callers unchanged.
* Stub clients not forced to grow streaming behavior.
* Clear agent → CLI boundary via `TurnStream` / `TurnResult`.
* Graph inspectability preserved — same nodes and edges as Plan 12.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Add `stream_chat` to `LLMClient` directly | Forces all implementations to support streaming |
| `on_delta` callback in agent/bootstrap | UI coupling |
| New LangGraph streaming nodes | Graph redesign; violates Plan 19 constraint |
| LangGraph `astream_events` | Framework coupling; topology change risk |
| WebSocket server | Non-scope |

---

### ADR-079 — Error Handling, Recovery, and Ctrl-C

**Status:** Proposed

#### Context

Streaming introduces partial output and interruptibility. Conversation state must remain recoverable.

#### Decision

* **Pre-turn snapshot:** turn facade retains `state_before_turn` before execution.
* **Streaming success path:** after `TurnStream` exhaustion, `turn_stream.result()` returns `TurnResult` with full `answer` and updated `state`.
* **Streaming transport error mid-stream:**
  * discard partial assistant message;
  * restore `state_before_turn`;
  * print error to stderr;
  * REPL continues.
* **No automatic retry** with non-streaming mode.
* **Partial stdout:** user may have seen partial text; print newline + `[generation interrupted]` to stderr (not added to state).
* **Ctrl-C during stream consumption (CLI):**
  * CLI signal handler stops iterating `TurnStream`;
  * cancel underlying HTTP stream if accessible through client/session cleanup;
  * restore `state_before_turn`;
  * return to REPL prompt;
  * best-effort; tests use stubs without signals.
* **Exit codes:** `0` success; `1` operational failure (including single-turn LLM failure); `2` usage; `3` precondition failure (index/config only — not LLM reachability).

#### Consequences

* Session recoverable after failures.
* No hidden fallback behavior.

---

### ADR-080 — Streaming Mode Selection (No Automatic Fallback)

**Status:** Proposed

#### Context

Operators may need non-streaming for debugging or providers with broken SSE. Automatic hidden retry adds complexity and masks misconfiguration.

#### Decision

* **Default:** streaming **on** when client implements `StreamingLLMClient`.
* **`--no-stream` flag:** use `execute_turn(...) -> TurnResult` with `chat()` for all LLM calls; CLI prints `turn_result.answer` at once after turn completes.
* **On streaming failure:**
  * display error to stderr;
  * preserve session state (pre-turn snapshot restore per ADR-079);
  * continue REPL;
  * **do not** automatically retry with non-streaming.
* **No `RAG_CHAT_STREAM_FALLBACK` environment variable.**
* **No automatic non-streaming retry.**
* Operator explicitly re-issues the question with `--no-stream` if desired.
* **Sources rendering:** identical for both modes — from `TurnResult.sources` after answer completion.

#### Consequences

* Predictable, explicit behavior.
* Streaming remains default for lecture demo.
* Misconfigured streaming surfaces clearly; operator opts into `--no-stream`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `RAG_CHAT_STREAM_FALLBACK=1` auto-retry | Hidden behavior; masks errors |
| Streaming off by default | Violates Plan 19 requirement |
| Silent fallback on any stream error | Operator loses visibility |

---

## Design Evaluations

### 1. Chat execution ownership

**Decision:** CLI owns REPL and rendering; bootstrap owns wiring and facades; agent owns `TurnStream`/`TurnResult` (ADR-071). Agent never receives terminal callbacks.

### 2. Conversation state lifetime

**Decision:** Process-scoped in-memory only (ADR-072). Extends ADR-045.

### 3. Session persistence policy

**Decision:** No persistence, no export, no checkpointer (ADR-073).

### 4. Bootstrap ownership of chat wiring

**Decision:** `bootstrap/chat.py` with `execute_turn` / `execute_turn_streaming` facades returning typed results (ADR-074).

### 5. Source citation rendering

**Decision:** Agent extracts structured `TurnSource` into `TurnResult`; CLI formats `TurnResult.sources` (ADR-075). No CLI message-history JSON parsing.

### 6. Interactive loop design

**Decision:** CLI consumes `TurnStream`; REPL with `--message` single-turn (ADR-076).

### 7. Startup validation behavior

**Decision:** Configuration + index preconditions only; **no LLM probe** (ADR-077). First turn validates connectivity.

### 8. Error handling and recovery

**Decision:** Snapshot restore; no partial assistant in state; no auto-retry (ADR-079).

### 9. Streaming architecture and ownership

**Decision:** `StreamingLLMClient` capability; `TurnStream` abstraction; graph topology unchanged (ADR-078).

### 10. Streaming mode selection

**Decision:** Streaming default; `--no-stream` explicit; no automatic fallback (ADR-080).

---

## LLM Boundary Extension

### Module changes

```text
src/knowledge_assistant/llm/
    messages.py          # ADD StreamChunk
    protocol.py          # KEEP LLMClient; ADD StreamingLLMClient
    openai_client.py     # IMPLEMENT StreamingLLMClient (SSE)
    stub_client.py       # UNCHANGED — LLMClient only
    streaming_stub_client.py   # OPTIONAL test double implementing StreamingLLMClient
    streaming.py         # OPTIONAL: parse_sse_line() helpers
```

### Protocol shape

```python
class LLMClient(Protocol):
    def chat(...) -> GenerationResult: ...
    # unchanged from Plan 11


class StreamingLLMClient(LLMClient, Protocol):
    def stream_chat(...) -> Iterator[StreamChunk]: ...
```

### SSE parsing rules (`OpenAICompatibleLLMClient.stream_chat`)

* POST with `"stream": true`.
* Read response as text stream (`httpx` `stream=True`).
* Parse SSE `data:` lines; stop on `[DONE]`.
* Yield `StreamChunk(content_delta=...)` for non-empty `delta.content`.
* If chunk contains `delta.tool_calls`, raise `LLMResponseError` — streaming is for final text generation only.
* Sync blocking iteration — no `asyncio`.

### Compatibility guarantees

* **No signature changes** to `LLMClient.chat()`.
* **`StubLLMClient` unchanged** — remains valid `LLMClient` without streaming.
* Existing Plan 11 unit tests pass without modification.
* Streaming tests target `OpenAICompatibleLLMClient` and optional `StreamingStubLLMClient`.

---

## Agent Extension

### LangGraph constraint (repeated)

Plan 19 agent changes are limited to **turn execution strategy** and **result types**:

| Change | Allowed? |
| ------ | -------- |
| New `TurnResult`, `TurnSource`, `TurnStream` types | Yes |
| `run_turn_streaming(...) -> TurnStream` facade | Yes |
| Internal helper for final `stream_chat` call | Yes |
| New graph nodes (`stream_node`, etc.) | **No** |
| New conditional routes | **No** |
| New `GraphState` fields | **No** |

### Turn execution strategy

1. **Tool loop:** existing graph invocation using `LLMClient.chat()` — unchanged routing (`agent_node` ↔ `tool_node` ↔ `should_continue`).
2. **Final answer (streaming):** when streaming enabled and `isinstance(llm_client, StreamingLLMClient)`, perform final text generation via `stream_chat()` and expose chunks through `TurnStream`; accumulate full `answer` before committing assistant `ChatMessage` to `AgentState`.
3. **Final answer (non-streaming):** existing `run_turn` path; return `TurnResult`.
4. **Source extraction:** when `search_documents` tool executes during the turn, map hit `source` fields to `TurnSource` and attach to `TurnResult.sources`.

### Public APIs

| API | Returns | Use case |
| --- | ------- | -------- |
| `run_turn(...)` | `TurnResult` | `--no-stream`; backward-compatible tests |
| `run_turn_streaming(...)` | `TurnStream` | default `rag chat`; CLI iterates chunks |

`TurnStream.result() -> TurnResult` provides `state`, `answer`, and `sources` after successful completion.

### No UI coupling

Agent and bootstrap APIs must **not** accept:

* `on_delta` callbacks;
* `write`/`flush` callables;
* `stdout`/`stderr` references;
* CLI types.

---

## Bootstrap Chat Session

### `ChatSession` dataclass

```python
@dataclass(frozen=True, slots=True)
class ChatSession:
    environment: DemoEnvironment
    llm_client: LLMClient
    tool_registry: ToolRegistry
    agent_settings: AgentSettings
    llm_settings: LlmSettings
```

### `build_chat_session`

```python
def build_chat_session(
    *,
    bootstrap_settings: BootstrapSettings | None = None,
    llm_settings: LlmSettings | None = None,
    llm_client: LLMClient | None = None,
    vector_store: VectorStore | None = None,
) -> ChatSession:
    ...
```

Production default: `OpenAICompatibleLLMClient` (implements `StreamingLLMClient`). Tests inject `StubLLMClient`, `StreamingStubLLMClient`, or fakes.

### Facade functions

| Function | Returns | Responsibility |
| -------- | ------- | -------------- |
| `initial_agent_state()` | `AgentState` | System prompt seeded |
| `execute_turn(session, state, message)` | `TurnResult` | Non-streaming full turn |
| `execute_turn_streaming(session, state, message)` | `TurnStream` | Streaming turn; CLI consumes iterator |

Facades delegate to agent; **no rendering callbacks**.

### Bootstrap integration diagram

```text
BootstrapSettings.from_env()
        ↓
build_demo_environment()
        ↓
build_default_tool_registry(...)
        ↓
OpenAICompatibleLLMClient(...)    # StreamingLLMClient
        ↓
ChatSession
        ↓
execute_turn_streaming(...) → TurnStream → TurnResult
        ↓
CLI iterates TurnStream, renders, prints TurnResult.sources
```

---

## CLI Chat Command

### Parser (`cli/main.py`)

```text
rag chat [--message TEXT] [--no-stream] [--no-sources]
```

| Flag | Default | Purpose |
| ---- | ------- | ------- |
| `--message TEXT` | none | Single-turn; skip REPL |
| `--no-stream` | false | Use `execute_turn` / `chat()` only |
| `--no-sources` | false | Skip post-turn Sources block |

**Removed flags:** `--skip-llm-probe` (no startup probe).

### `cli/chat.py` responsibilities

| Function | Responsibility |
| -------- | -------------- |
| `run_chat(...)` | Entry: build session, diagnostics, dispatch REPL or single-turn |
| `run_chat_repl(...)` | Interactive loop; consumes `TurnStream` |
| `run_single_turn(...)` | `--message` path |
| `print_chat_banner(session)` | Configuration diagnostics (no LLM call) |
| `validate_chat_preconditions(session)` | Corpus + index + config; exit 3 on failure |
| `format_turn_sources(sources)` | Render `tuple[TurnSource, ...]` to stdout text |
| `render_turn_stream(turn_stream)` | Iterate chunks, write stdout, return `TurnResult` |
| SIGINT handler | Stop stream iteration; CLI-owned |

### `rag chat` flow (REPL, streaming default)

```text
parse args
    ↓
build_chat_session()
    ↓
validate_chat_preconditions() → exit 3 if fail
    ↓
print_chat_banner()
    ↓
state = initial_agent_state()
    ↓
loop:
    read "You: " prompt
    ↓
    if exit/quit/EOF → break
    ↓
    turn_stream = execute_turn_streaming(session, state, message)
    ↓
    turn_result = render_turn_stream(turn_stream)   # CLI writes chunks
    ↓
    state = turn_result.state
    ↓
    print format_turn_sources(turn_result.sources) (unless --no-sources)
    ↓
exit 0
```

### `rag chat --message` flow

```text
parse args → build session → preconditions → banner
    ↓
execute_turn or execute_turn_streaming (per --no-stream)
    ↓
render answer + sources
    ↓
exit 0 (or 1 on turn failure)
```

### Exit codes

| Code | Condition |
| ---- | --------- |
| `0` | clean exit (EOF, quit, single-turn success) |
| `1` | operational failure (turn error, LLM unreachable on turn) |
| `2` | argparse usage error |
| `3` | precondition failure (missing corpus, empty collection, invalid LLM **configuration**) |

**Note:** LLM reachability is **not** exit 3 — it fails on first turn as exit 1 (single-turn) or REPL error message (interactive).

---

## Module Layout

### LLM (extend)

```text
src/knowledge_assistant/llm/
    messages.py              # StreamChunk
    protocol.py              # LLMClient (unchanged) + StreamingLLMClient
    openai_client.py         # implements StreamingLLMClient
    stub_client.py           # LLMClient only — unchanged
```

### Agent (extend)

```text
src/knowledge_assistant/agent/
    turn.py                  # NEW (recommended): TurnResult, TurnSource, TurnStream
    graph.py                 # run_turn_streaming; execution strategy only
```

### Bootstrap (extend)

```text
src/knowledge_assistant/bootstrap/
    chat.py                  # ChatSession, facades
    __init__.py              # export chat public API
```

### CLI (extend)

```text
src/knowledge_assistant/cli/
    main.py                  # chat subparser (3 flags)
    chat.py                  # REPL, TurnStream consumption, source formatting
```

### Tests (new/extend)

```text
tests/unit/llm/test_streaming_client.py
tests/unit/agent/test_turn_result.py
tests/unit/agent/test_streaming_turn.py
tests/unit/bootstrap/test_chat_session.py
tests/unit/cli/test_chat_parsing.py
tests/unit/cli/test_chat_sources.py
tests/unit/cli/test_chat_preconditions.py
tests/integration/chat/test_chat_single_turn.py
tests/integration/chat/test_chat_repl_stub.py
tests/integration/chat/conftest.py
```

### Unchanged packages

```text
src/knowledge_assistant/retrieval/     # no production changes
src/knowledge_assistant/mcp_server/    # no handler changes
src/knowledge_assistant/evaluation/    # no changes
src/knowledge_assistant/indexing/      # no changes
src/knowledge_assistant/storage/       # no changes
```

---

## Dependency Rules

### Allowed

| Consumer | May import |
| -------- | ---------- |
| `bootstrap/chat.py` | `bootstrap.*`, `agent`, `llm`, `mcp_server.config`, `core` |
| `cli/chat.py` | `bootstrap`, stdlib |
| `cli/main.py` | `cli.demo`, `cli.evaluate`, `cli.chat`, stdlib |
| `agent/turn.py`, `agent/graph.py` | `llm` protocol/messages, `core` (for source types if shared) |
| tests | all layers with fixtures |

### Forbidden

| Consumer | Must not import |
| -------- | --------------- |
| `cli/chat.py` | `agent`, `llm`, `mcp_server`, `retrieval`, `storage`, `indexing`, `evaluation` |
| `agent/` | `cli`, `bootstrap` |
| `llm/` | `agent`, `mcp_server`, `retrieval`, `cli` |

---

## Configuration

### Inherited environment variables

No new required environment variables:

| Variable | Effect on chat |
| -------- | -------------- |
| `QDRANT_URL` | vector store endpoint |
| `RAG_CORPUS_ROOT` | corpus path (precondition) |
| `RAG_EMBEDDING_MODE` | stub vs real dense embeddings |
| `RAG_RERANKER_MODE` | stub vs real reranker |
| `LLM_BASE_URL` | chat completion endpoint (banner + turns) |
| `LLM_API_KEY` | authentication |
| `LLM_MODEL` | default model |
| `LLM_TIMEOUT_SECONDS` | request timeout |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` | generation defaults |

### Removed configuration

| Variable | Status |
| -------- | ------ |
| `RAG_CHAT_STREAM_FALLBACK` | **Removed** — no automatic fallback |

### CLI flags

| Flag | Purpose |
| ---- | ------- |
| `--message` | single-turn |
| `--no-stream` | explicit non-streaming |
| `--no-sources` | omit Sources block |

---

## Testing Strategy

### Unit tests — `tests/unit/llm/`

| Focus |
| ----- |
| `StreamingLLMClient` SSE parsing; `LLMClient.chat()` regression unchanged; `StubLLMClient` does not implement streaming |

### Unit tests — `tests/unit/agent/`

| Focus |
| ----- |
| `TurnResult.sources` populated from search tool execution; `TurnStream` yields chunks then `result()`; tool round uses `chat()`; graph topology unchanged (no new nodes in `graph.py` structure tests) |

### Unit tests — `tests/unit/bootstrap/`

| Focus |
| ----- |
| `build_chat_session`; facades return `TurnStream`/`TurnResult` without callbacks |

### Unit tests — `tests/unit/cli/`

| Focus |
| ----- |
| `format_turn_sources(TurnSource)` — not message JSON parsing; preconditions (corpus, index, config); no probe tests |

### Integration tests — `tests/integration/chat/`

| Focus |
| ----- |
| `main(["chat", "--message", ...])` with injected `StreamingStubLLMClient`; REPL stub; sources from `TurnResult` |

### Explicitly removed tests

* startup LLM probe behavior;
* `--skip-llm-probe` flag parsing;
* `RAG_CHAT_STREAM_FALLBACK` auto-retry;
* `format_sources_from_state` / AgentState message JSON scanning.

### CI constraints

* No live LLM in default CI.
* Inject stub/streaming-stub clients via `build_chat_session(llm_client=...)`.

---

## Implementation Phases

### Phase 1 — LLM streaming capability

1. Add `StreamChunk` and `StreamingLLMClient` protocol.
2. Implement `OpenAICompatibleLLMClient` as `StreamingLLMClient`.
3. Add optional `StreamingStubLLMClient` for tests.
4. Verify Plan 11 `LLMClient` tests unchanged.

### Phase 2 — Agent turn boundary (no graph redesign)

1. Add `TurnSource`, `TurnResult`, `TurnStream`.
2. Add `run_turn_streaming` execution strategy — **no new graph nodes/routes/state fields**.
3. Source extraction into `TurnResult.sources` during turn.
4. Unit tests.

### Phase 3 — Bootstrap facades

1. Add `bootstrap/chat.py` with `execute_turn` / `execute_turn_streaming`.
2. Export public API.
3. Unit tests.

### Phase 4 — CLI chat command

1. Add `cli/chat.py` — consumes `TurnStream`, renders `TurnResult.sources`.
2. Parser: `--message`, `--no-stream`, `--no-sources`.
3. Preconditions and banner (no LLM probe).
4. SIGINT during stream consumption.
5. Integration tests.

### Phase 5 — Documentation and ADRs

1. ADR-042–046 and ADR-071–080 in `DECISIONS.md`.
2. Update `ARCHITECTURE.md`, `README.md`, `PROGRESS.md`, `ROADMAP.md`.

---

## Acceptance Criteria

Plan 19 is complete when:

- [x] `rag chat` starts interactive REPL with startup banner and precondition checks
- [x] Assistant responses **stream by default** to terminal via CLI consumption of `TurnStream`
- [x] Final assistant text is stored in `AgentState.messages` after successful completion
- [x] Sources render **after** stream from **`TurnResult.sources`** (unless `--no-sources`)
- [x] **CLI does not reparse MCP JSON from `AgentState.messages` for sources**
- [x] `--message` runs single turn and exits
- [x] `--no-stream` uses non-streaming `execute_turn` / `chat()` end-to-end
- [x] Streaming failure does not corrupt `AgentState`; REPL continues; **no automatic non-streaming retry**
- [x] Ctrl-C during generation aborts stream consumption and returns to prompt (best-effort)
- [x] **Plan 11 `LLMClient.chat()` contract unchanged**; existing llm tests pass
- [x] **`StreamingLLMClient` capability** implemented by `OpenAICompatibleLLMClient`; `StubLLMClient` not required to stream
- [x] **No startup LLM probe** — no test request at chat startup
- [x] **No `RAG_CHAT_STREAM_FALLBACK`** or hidden retry behavior
- [x] **LangGraph topology unchanged** — no new nodes, routes, or `GraphState` fields
- [x] **Agent does not receive terminal callbacks** (`on_delta`, stdout writers, etc.)
- [x] Bootstrap owns chat wiring; CLI imports bootstrap only
- [x] No retrieval/MCP changes; canonical rerank retriever used
- [x] ADR-042–046 and ADR-071–080 recorded in `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents chat workflow, `TurnResult` boundary, streaming capability
- [x] `README.md` includes chat quickstart
- [x] `uv run ruff format --check .`, `ruff check .`, `basedpyright`, `pytest` pass

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Provider SSE incompatibility | Streaming breaks | Operator uses explicit `--no-stream`; clear error message |
| Tool calls appear in stream | Corrupt orchestration | Tool rounds use `chat()` only; stream parser rejects tool deltas |
| Ctrl-C leaves hung httpx connection | Resource leak | Response close on CLI interrupt |
| CLI import boundary creep | Architecture drift | AST import tests |
| Graph scope creep | Delay, boundary violation | Explicit non-scope checklist; graph structure tests |
| `TurnSource` mapping drift from MCP | Wrong citations | Unit tests on agent extraction from `SearchHitSchema` |
| First-turn LLM failure surprise | Operator confusion | Banner documents LLM endpoint; clear stderr on turn failure |

---

## Follow-Up Work (Not Plan 19)

| Item | Proposed plan |
| ---- | ------------- |
| Query rewriting and retrieval retry | Plan 12b |
| MCP SDK transport | Plan 12c |
| Tier 2 MCP browse tools | Plan 10b |
| Sparse BGE-M3 indexing | Future indexing plan |
| Session persistence / checkpointer | Future plan |
| Transcript export | Out of scope |
| Web UI | Out of project scope |

---

## Checklist (Implementation)

### LLM layer

- [x] `StreamChunk` DTO
- [x] `StreamingLLMClient` protocol (`LLMClient` unchanged)
- [x] `OpenAICompatibleLLMClient` implements `StreamingLLMClient`
- [x] `StubLLMClient` unchanged
- [x] Optional `StreamingStubLLMClient` for tests
- [x] Plan 11 `chat()` regression tests pass

### Agent layer

- [x] `TurnSource`, `TurnResult`, `TurnStream`
- [x] `run_turn_streaming` execution strategy
- [x] **No new graph nodes/routes/GraphState fields**
- [x] Source extraction into `TurnResult.sources`
- [x] **No callbacks in public APIs**
- [x] Unit tests

### Bootstrap layer

- [x] `ChatSession`, `build_chat_session()`
- [x] `execute_turn()` → `TurnResult`
- [x] `execute_turn_streaming()` → `TurnStream`
- [x] Unit tests

### CLI layer

- [x] `cli/chat.py` consumes `TurnStream`
- [x] `format_turn_sources(sources)` — not `AgentState` parsing
- [x] `--message`, `--no-stream`, `--no-sources`
- [x] Banner + preconditions (no LLM probe)
- [x] SIGINT handler
- [x] Import boundary tests

### Documentation

- [x] ADR-042–046 acceptance
- [x] ADR-071–080
- [x] `ARCHITECTURE.md` updates
- [x] `README.md` chat quickstart
- [x] `PROGRESS.md` entry on completion

### Validation

- [x] Full quality suite passes

---

## Appendix A — End-to-End Sequence (Streaming Turn)

```text
User types question
  ↓
CLI: state_before = state
  ↓
turn_stream = bootstrap.execute_turn_streaming(session, state, message)
  ↓
agent: existing graph tool loop (chat()) → search_documents
  ↓
agent: extract TurnSource values from search hits
  ↓
agent: final generation via StreamingLLMClient.stream_chat()
  ↓
CLI: for chunk in turn_stream: write chunk.content_delta to stdout
  ↓
turn_result = turn_stream.result()
  ↓
state = turn_result.state; answer = turn_result.answer
  ↓
CLI: format_turn_sources(turn_result.sources)
  ↓
REPL prompt
```

---

## Appendix B — Revision Summary (2026-06-22)

| Area | Previous draft | Revised |
| ---- | -------------- | ------- |
| LLM protocol | `stream_chat` on `LLMClient` | `StreamingLLMClient(LLMClient)` capability; Plan 11 unchanged |
| Agent → CLI | `on_delta` callbacks | `TurnStream` / `TurnResult` typed boundary |
| Sources | CLI parses `AgentState` tool JSON | `TurnResult.sources` from agent |
| Startup | LLM probe + `--skip-llm-probe` | Config + index only; first turn validates LLM |
| Fallback | `RAG_CHAT_STREAM_FALLBACK` auto-retry | Removed; explicit `--no-stream` only |
| Graph | Streaming inside nodes (loose) | Explicit: no topology changes |
| Stub LLM | Required `stream_chat` | `StubLLMClient` unchanged; optional streaming stub for tests |

---

## Appendix C — Conflict Resolution Summary

| Gap | Plan 19 resolution |
| --- | ------------------- |
| Non-streaming LLM | `StreamingLLMClient` optional capability (ADR-078) |
| UI coupling | `TurnStream` / `TurnResult`; no callbacks (ADR-071, ADR-078) |
| Fragile source display | `TurnResult.sources` (ADR-075) |
| Startup probe cost | Removed (ADR-077) |
| Hidden fallback | Removed (ADR-080) |
| Graph redesign risk | Explicit non-scope (Objective, Scope, ADR-078) |
| ADR-042–046 missing | Accept in Phase 5 |
