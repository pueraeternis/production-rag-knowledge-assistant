# Plan 12 — LangGraph Agent

**Status:** Completed

**Created:** 2026-06-21

**Completed:** 2026-06-21

**Roadmap:** Phase 7 — Agent Layer

**Depends on:**

* [Plan 10 — Knowledge MCP Server](../completed/10-knowledge-mcp-server.md)
* [Plan 11 — LLM Boundary](../completed/11-llm-boundary.md)

**Plan principle:** One plan introduces one architectural capability. Plan 12 introduces the **LangGraph conversational agent** that orchestrates LLM inference and MCP knowledge tools — without violating documented component boundaries.

---

## Authorization

**Completed.** Implementation authorized when this plan was moved to `docs/plans/active/` and delivered per acceptance criteria below.

ADR entries ADR-042 through ADR-046 are recorded in this plan. Acceptance into `docs/DECISIONS.md` and a dedicated **Agent Layer** section in `docs/ARCHITECTURE.md` remain follow-up documentation tasks outside this housekeeping pass.

---

## Objective

Design and implement a thin **LangGraph-based** conversational RAG agent that:

* owns conversation handling and tool-calling orchestration;
* calls the LLM only through `knowledge_assistant.llm.LLMClient`;
* accesses knowledge only through MCP handler adapters (Tier 1 handlers from Plan 10);
* produces grounded answers with source attribution derived from MCP search results;
* structurally supports indexing preview/apply with explicit approval gates;
* does **not** import retrieval, storage, indexing internals, or provider SDKs in agent core.

```text
User input
    ↓
LangGraph graph (agent_node ↔ tool_node)
    ↓
LLMClient.chat(messages, settings=..., tools=...)
    ↓
optional model-emitted ToolCall
    ↓
tool_node → ToolRegistry → MCP handler adapters
    ↓
Knowledge MCP handlers (search_documents, index_documents_*)
    ↓
tool-result ChatMessage (role=tool)
    ↓
LLMClient.chat(...) again
    ↓
final grounded assistant answer
```

After this plan is complete:

* **`knowledge_assistant.agent`** exposes a compiled LangGraph workflow, typed graph state, tool registry, and RAG prompt templates;
* the agent answers knowledge questions via `search_documents` tool calls and cites MCP `SourceReferenceSchema` fields;
* indexing tools are registered and dispatchable; apply requires `approval_confirmed=True` with no interactive stdin in agent core;
* tests use `StubLLMClient` and fake/injected MCP dependencies — no live LLM or Qdrant in CI;
* import-boundary tests enforce agent layering;
* ADR entries ADR-042 through ADR-046 are recorded on completion;
* `docs/ARCHITECTURE.md` gains an **Agent Layer** section.

**Critical guardrail:** LangGraph is the **primary** orchestration mechanism. A plain custom `Agent.run()` loop that replaces the graph is **not acceptable**. Small internal helpers (for example, parsing tool arguments or formatting citations) are allowed only when invoked **from LangGraph nodes** and do not substitute for graph routing.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/agent/` — graph, state, tools, prompts, config, exceptions;
* associated unit and integration tests under `tests/unit/agent/` and `tests/integration/agent/`;
* `pyproject.toml` — add `langgraph` runtime dependency;
* ADR entries and documentation updates on completion.

### In Scope

* LangGraph `StateGraph` with `agent_node`, `tool_node`, and conditional `should_continue` routing;
* typed in-memory graph state (messages, tool iteration count, optional final response);
* `LLMClient.chat()` integration using Plan 11 DTOs (`ChatMessage`, `ToolDefinition`, `ToolCall`, `GenerationResult`, `GenerationSettings`);
* `AgentTool` protocol, `ToolRegistry`, and Tier 1 tool adapters:
  * `SearchDocumentsTool` → `search_documents`
  * `IndexDocumentsPreviewTool` → `index_documents_preview`
  * `IndexDocumentsApplyTool` → `index_documents_apply`
* RAG system/user prompt templates and citation contract (prompt assembly in agent, not in `llm/`);
* max tool-call iteration guard;
* deterministic test doubles (`StubLLMClient`, fake `Retriever` / `IndexingPipeline` injected into handlers);
* import-boundary tests for `agent/` core modules;
* ADR-042 through ADR-046 (proposed below);
* updates to `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/PROGRESS.md` on completion.

---

## Non-Scope

This plan does **not** authorize:

* real MCP SDK client/server transport (deferred — see Design Evaluation 1 and ADR-043);
* CLI chat UX, interactive approval prompts, or stdin inside agent core (future CLI plan);
* durable conversation memory, LangGraph checkpointers, or multi-session persistence;
* query rewriting, intent classification, or retrieval retry loops (deferred — see Design Evaluation 2);
* LangChain tool abstractions (`@tool`, `StructuredTool`, LangChain agents);
* direct `Retriever`, `VectorStore`, `IndexingPipeline`, or Qdrant access from agent core;
* LlamaIndex, OpenAI SDK, httpx, or embedding/reranker packages in agent core;
* streaming chat completions or async graph execution (sync-first per Plan 11);
* multi-agent systems, workflow orchestration platforms, or distributed deployment;
* real BGE embedding or reranker runtime;
* Langfuse / tracing, authentication, evaluation framework, demo dataset generation;
* MCP Tier 2 tools (`get_document`, `get_statistics`) or MCP resources;
* changes to MCP handler contracts beyond adapter wiring;
* changes to `llm/`, `retrieval/`, `indexing/`, or `storage/` except documentation cross-links.

**ROADMAP note:** Phase 7 roadmap text lists query rewriting and retrieval retry. This draft **defers** those capabilities to a future plan (proposed **Plan 12b — Query Rewriting and Retrieval Retry**). Update `docs/plans/backlog/ROADMAP.md` when this plan is activated.

---

## Architectural Decisions (Proposed ADRs)

The following decisions are **proposed** for Plan 12. Implementation must follow them; reopen only via plan revision. Record in `docs/DECISIONS.md` on implementation — not during this drafting phase.

### ADR-042 — LangGraph Agent Boundary

**Status:** Proposed

#### Context

`PROJECT.md` and `docs/ARCHITECTURE.md` assign conversation handling, routing, tool selection, and memory to the LangGraph agent. Plan 11 delivers `LLMClient` without orchestration. Plan 10 delivers MCP handlers without transport. The agent must compose both without violating dependency flow.

#### Decision

* Implement agent orchestration in `knowledge_assistant.agent` using **LangGraph `StateGraph`** as the sole workflow engine for turn processing.
* The agent owns:
  * graph state and node functions;
  * when to call `LLMClient.chat`;
  * tool schema exposure to the model;
  * dispatch of model-emitted `ToolCall` values to MCP handler adapters;
  * appending assistant and tool messages to in-memory history;
  * RAG prompt templates and citation instructions;
  * max tool iteration enforcement.
* The agent does **not** own:
  * retrieval algorithms, indexing algorithms, or storage;
  * MCP SDK transport;
  * LLM HTTP transport (Plan 11);
  * durable memory or checkpointers.
* Orchestration must **not** be implemented as a top-level custom loop that bypasses LangGraph routing. Entry APIs may invoke `compiled_graph.invoke(...)` or equivalent LangGraph APIs only.

#### Consequences

* Agent behavior is inspectable as a graph (nodes, edges, conditional routing).
* Tests assert routing and state transitions without mocking a monolithic `run()` method.
* Future query-rewrite or retry subgraphs can attach as additional LangGraph nodes in a later plan.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Custom `while tool_calls: ...` as primary orchestration | Hides routing; contradicts project stack and user requirement |
| LangChain `AgentExecutor` | Couples to LangChain agent framework; unnecessary |
| MCP server calls LLM for answers | Violates ADR-032 and dependency flow |
| Agent calls `Retriever` directly | Violates documented architecture |

---

### ADR-043 — Local MCP Handler Adapters Before MCP SDK Transport

**Status:** Proposed

#### Context

Plan 10 (ADR-034) delivered handler functions without MCP SDK runtime. Plan 12 must connect the agent to knowledge tools. Two integration options exist: in-process handler adapters vs real MCP SDK transport.

#### Decision

* Plan 12 agent tool adapters call Plan 10 handler functions **directly in-process**:
  * inject `Retriever` and `IndexingPipeline` into adapter closures or tool instances at wiring time;
  * validate tool arguments with existing `mcp_server/schemas.py` Pydantic models;
  * map handler responses to tool-result `ChatMessage.content` (JSON or structured text).
* Plan 12 does **not** add MCP SDK client/server transport, stdio pipes, or network MCP sessions.
* MCP SDK transport remains deferred to a **future plan** (proposed **Plan 12c — MCP SDK Transport** or equivalent backlog item).
* Handler names and Pydantic schemas remain stable so SDK registration can wrap the same handlers later.

#### Consequences

* Agent integration tests run without MCP SDK or subprocesses.
* Educational architecture diagram still shows “MCP Client → MCP Server”; Plan 12 implements the **logical** boundary via adapters; physical transport is a follow-up.
* CLI or demo wiring constructs `Retriever` / `IndexingPipeline` once and passes them into tool adapters.

#### Alternatives Considered

| Alternative | Why rejected for Plan 12 |
| ----------- | -------------------------- |
| Real MCP SDK transport now | Adds transport complexity before basic RAG loop is proven; Plan 10 explicitly deferred SDK |
| Agent imports `retrieval` / `indexing` directly | Violates architecture; bypasses MCP boundary |

---

### ADR-044 — Agent Tool Registry and Tool Dispatch

**Status:** Proposed

#### Context

Plan 11 defines `ToolDefinition` and `ToolCall` transport DTOs only. Plan 10 defines MCP handler contracts. The agent must bridge model tool calls to handler execution without LangChain tool types.

#### Decision

* Introduce project-local abstractions in `agent/tools.py`:
  * `AgentTool` protocol — `name`, `definition() -> ToolDefinition`, `execute(arguments: dict[str, object]) -> str`;
  * `ToolRegistry` — register tools, expose `definitions()`, dispatch `ToolCall` by name.
* Concrete tools wrap MCP handlers:
  * `SearchDocumentsTool` → `mcp_server.tools.search_documents`
  * `IndexDocumentsPreviewTool` → `mcp_server.tools.index_documents_preview`
  * `IndexDocumentsApplyTool` → `mcp_server.tools.index_documents_apply`
* Tool adapters:
  * build `ToolDefinition.parameters` JSON Schema aligned with MCP Pydantic request models;
  * parse `ToolCall.arguments` JSON, validate via MCP request models, call handlers, serialize responses for `role=tool` messages.
* Do **not** use LangChain `@tool`, `StructuredTool`, or LangGraph prebuilt ToolNode that requires LangChain tools unless LangGraph provides a LangChain-free dispatch path — prefer a custom `tool_node` function.
* Unknown tool names and malformed arguments produce deterministic tool-error messages (not unhandled exceptions leaking to the graph).

#### Consequences

* Tool dispatch is testable independently of LangGraph and LLM.
* MCP remains the knowledge contract owner; agent only adapts.
* Plan 12c can swap adapter backend from in-process handlers to MCP SDK client without changing graph shape.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| LangChain tool decorators | Unnecessary framework coupling |
| Tool execution inside `llm/openai_client.py` | Violates Plan 11 boundary |
| Hard-coded if/elif dispatch without registry | Poor extensibility for Tier 2 tools later |

---

### ADR-045 — In-Memory Conversation State Only

**Status:** Proposed

#### Context

The lecture demo requires multi-turn conversation within a session. Production patterns (Postgres checkpointer, Redis, vector memory) are explicit non-goals per `AGENTS.md`.

#### Decision

* Plan 12 stores conversation history **only in graph state** for the current invocation/session:
  * `messages: tuple[ChatMessage, ...]` accumulated across turns;
  * no LangGraph checkpointer, no SQLite/Postgres saver, no filesystem persistence.
* Each `invoke` (or public `run_turn`) accepts prior state or starts from system prompt + new user message.
* Callers (future CLI) may hold state between REPL iterations in process memory.
* Deferred: durable memory, long-term memory, multi-session storage, thread IDs.

#### Consequences

* Tests remain deterministic with explicit state fixtures.
* Persistence becomes a future plan with explicit ADR if ever needed.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| LangGraph `MemorySaver` checkpointer | Out of scope; adds persistence semantics not required for lecture |
| Store retrieved chunks in durable agent memory | Violates “knowledge documents belong to knowledge layer” rule |

---

### ADR-046 — RAG Prompt and Citation Contract

**Status:** Proposed

#### Context

`PROJECT.md` requires grounded answers with citations (document title, path, section title, line range). Plan 11 intentionally excluded RAG prompts. MCP search results expose `SourceReferenceSchema` via `SearchHitSchema.source`.

#### Decision

* RAG prompt templates live in `agent/prompts.py` (Plan 12 scope).
* System prompt instructs the model to:
  * use `search_documents` for factual knowledge questions;
  * ground answers only in retrieved tool results;
  * cite sources using MCP-exposed fields (`document_title`, `document_path`, `section_title`, `line_range.start_line`–`line_range.end_line`);
  * refuse or qualify when evidence is insufficient.
* Citation rendering uses **MCP search result source fields** — not storage payloads, not `ChunkMetadata`, not Qdrant internals.
* Prompt assembly appends tool results as `ChatMessage(role=TOOL, ...)`; the agent does not re-fetch chunks from storage for citation metadata.
* Exact citation format (e.g. markdown footnotes vs inline brackets) is defined in prompts and verified by prompt-contract tests — not by asserting exact LLM wording in integration tests.

#### Consequences

* Grounding behavior is documented and testable at the prompt/template level.
* Source attribution chain remains: storage → `SearchResult.source` → MCP schema → agent prompts → user-visible answer.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Prompts in `llm/prompts.py` | Product/orchestration behavior belongs to agent |
| Post-hoc citation extraction from assistant text | Fragile; duplicates MCP attribution |
| Citations from chunk IDs resolved via storage | Agent would bypass MCP |

---

## Design Evaluations

### 1. MCP integration: local adapters vs SDK transport

| Option | Description | Assessment |
| ------ | ----------- | ---------- |
| **A — Local handler adapters (selected)** | Tool classes call `mcp_server.tools.*` in-process with injected dependencies | Matches Plan 10 ADR-034; simplest test path; preserves logical MCP boundary |
| B — MCP SDK transport | Agent uses MCP client over stdio/HTTP to remote server | Architecturally “purer” for MCP diagram; heavy for educational scope now |

**Decision:** Option A for Plan 12. Document Option B as future **Plan 12c — MCP SDK Transport**.

### 2. Query rewriting and retrieval retry

| Capability | Plan 12? | Rationale |
| ---------- | -------- | --------- |
| Basic tool-calling RAG loop (search → answer) | **In scope** | Core lecture flow |
| Single-pass `search_documents` per question | **In scope** | Sufficient for v1 demo |
| LLM-driven query rewriting before search | **Deferred** | Adds extra nodes/prompts; not required for first grounded answer |
| Automatic retrieval retry on empty/weak results | **Deferred** | Requires rewrite policy + termination rules |
| LangGraph-native rewrite/retry subgraph | **Future plan** | Proposed **Plan 12b** if roadmap prioritizes quality iteration |

**Decision:** defer query rewriting and retrieval retry to **Plan 12b**. Plan 12 delivers one search tool call (or sequential tool calls within the iteration guard) without a dedicated rewrite node. If the model emits a poor query, behavior is governed by prompts only — no agent-side rewrite loop.

### 3. LangChain dependency surface

LangGraph may pull `langchain-core` transitively. Plan 12 adds **`langgraph` only** explicitly to `pyproject.toml`.

**Rule:** agent production code imports **`langgraph` graph APIs only**. Do not import LangChain tools, agents, or chat models. If LangGraph prebuilt utilities require LangChain types, reimplement minimal node functions instead.

### 4. Sync vs async execution

Plan 11 `LLMClient.chat` is sync. MCP handlers are sync.

**Decision:** sync LangGraph node functions and sync public API (`run_turn(...)`). Async graph execution deferred unless a later plan adopts async LLM.

### 5. Max tool-call iterations

**Decision:** configurable via `AgentSettings.max_tool_iterations` (default **5**). `should_continue` routes to `END` when:

* latest assistant message has no tool calls; or
* `tool_iteration_count >= max_tool_iterations` (append deterministic error tool message or assistant refusal — implementation choice, must be tested).

Each visit to `tool_node` increments `tool_iteration_count` once (even if multiple parallel tool calls in one assistant message — count **rounds**, not individual calls).

### 6. Pydantic in agent package

Agent core state uses stdlib dataclasses or `TypedDict`. Pydantic appears **only** at the MCP adapter boundary when constructing MCP request models from tool arguments (import from `mcp_server.schemas` — do not duplicate schemas in agent).

---

## LangGraph Graph Shape

### Topology

```text
START
  ↓
agent_node
  ↓
should_continue
  ├─ (tool calls pending AND iterations remaining) → tool_node → agent_node
  └─ (else) → END
```

### Node responsibilities

| Node | Responsibility |
| ---- | -------------- |
| `agent_node` | Call `LLMClient.chat(state.messages, tools=registry.definitions())`. Append assistant `ChatMessage` from `GenerationResult` (content and/or tool_calls serialized into message representation used by Plan 11 DTOs). Set `final_response` when model returns text-only completion intended as user-visible answer. |
| `tool_node` | Read tool calls from latest assistant turn. For each call: `registry.dispatch(tool_call)` → append `ChatMessage(role=TOOL, tool_call_id=..., content=...)`. Increment `tool_iteration_count`. On dispatch errors, append tool message with structured error text (deterministic). |
| `should_continue` | Conditional edge function: if latest message implies pending tool execution and under iteration limit → `"tool_node"`; else → `END`. |

### Graph state structure

Prefer a frozen dataclass or `TypedDict` registered with LangGraph reducers.

**Recommended fields:**

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `messages` | `tuple[ChatMessage, ...]` | Full chat history including system, user, assistant, tool messages. Reducer: append new messages each node return. |
| `tool_iteration_count` | `int` | Tool rounds executed; starts at 0. |
| `final_response` | `str \| None` | Optional user-visible answer text when graph completes without needing caller to parse last assistant message. |

**Not in Plan 12 state:** durable thread IDs, retrieved chunk cache separate from messages, rewrite attempt counters, checkpointer metadata.

**Entry behavior:** public API accepts a user message string, prepends/extends `messages` with `ChatMessage(role=USER, ...)`, initializes or continues state, invokes compiled graph.

### Message history rules

* System prompt inserted once at session start (caller or factory responsibility).
* User messages appended before graph invoke.
* Assistant messages appended only by `agent_node` from `GenerationResult`.
* Tool results appended only by `tool_node`.
* Do not store raw `SearchHitSchema` objects outside `messages`; tool content is serialized JSON/text in tool messages.

---

## LLM Integration

### Call site

Only `agent_node` (and only through a thin helper if needed) calls:

```python
result = llm_client.chat(
    state.messages,
    settings=generation_settings,  # optional per-call overrides
    tools=tool_registry.definitions(),
)
```

### DTO usage (Plan 11)

| DTO | Agent usage |
| --- | ----------- |
| `ChatMessage` | State history; roles `SYSTEM`, `USER`, `ASSISTANT`, `TOOL` |
| `ToolDefinition` | Exposed to model via registry |
| `ToolCall` | Parsed from `GenerationResult.tool_calls` |
| `GenerationResult` | Drives assistant message append and routing |
| `GenerationSettings` | Optional; defaults from `LlmSettings` in wiring |

### Provider isolation

Agent core (`state.py`, `graph.py`, `tools.py`, `prompts.py`, `exceptions.py`) must **not** import:

* `OpenAICompatibleLLMClient`
* `openai_client`
* httpx

Wiring/tests construct `StubLLMClient` or `OpenAICompatibleLLMClient` outside core and inject `LLMClient` protocol instance into graph factory.

---

## Tool Registry and MCP Handler Adapters

### `AgentTool` protocol

```python
class AgentTool(Protocol):
    @property
    def name(self) -> str: ...

    def definition(self) -> ToolDefinition: ...

    def execute(self, arguments: dict[str, object]) -> str: ...
```

`execute` returns a string placed in `ChatMessage.content` for `role=tool` (typically JSON from Pydantic `model_dump_json()` on MCP responses).

### `ToolRegistry`

| Method | Behavior |
| ------ | -------- |
| `register(tool: AgentTool) -> None` | Add tool; duplicate names raise `DuplicateToolError` |
| `definitions() -> tuple[ToolDefinition, ...]` | Stable order for LLM requests |
| `dispatch(call: ToolCall) -> ChatMessage` | Lookup by `call.name`, parse arguments, execute, return TOOL message with `tool_call_id=call.id` |

### Concrete tools

| Tool class | MCP handler | Notes |
| ---------- | ------------- | ----- |
| `SearchDocumentsTool` | `search_documents` | Requires injected `Retriever`, `McpServerSettings` |
| `IndexDocumentsPreviewTool` | `index_documents_preview` | Requires injected `IndexingPipeline` |
| `IndexDocumentsApplyTool` | `index_documents_apply` | Enforces MCP `approval_confirmed`; adapter validates bool |

Factory functions (e.g. `build_default_tool_registry(retriever, pipeline, settings)`) may live in `agent/tools.py` or a dedicated `wiring.py` module that is **excluded from import-boundary “core”** tests if it imports concrete types for demo/bootstrap.

### Tool definition schema source

JSON Schema in `ToolDefinition.parameters` must match MCP request models:

* `SearchDocumentsRequest`: `query` (required), `top_k` (optional)
* `IndexDocumentsPreviewRequest`: `sources` (required array)
* `IndexDocumentsApplyRequest`: `sources`, `rebuild`, `approval_confirmed`

Hand-author schemas in agent code aligned with `mcp_server/schemas.py` — do not generate from Pydantic at runtime in Plan 12.

---

## Search / Answer Flow

### Happy path (knowledge question)

```text
1. User message appended to state.messages
2. agent_node → LLMClient.chat(..., tools=[search_documents, ...])
3. Model returns GenerationResult with ToolCall(name="search_documents", ...)
4. should_continue → tool_node
5. tool_node → SearchDocumentsTool → search_documents handler
6. Tool result appended (JSON hits with source fields)
7. agent_node → LLMClient.chat(...) without requiring another tool call
8. Model returns grounded natural-language answer
9. should_continue → END; final_response set
```

### Grounding and citations

* System prompt (in `prompts.py`) requires answers to use only provided search hits.
* Each hit includes `source: SourceReferenceSchema` — prompts instruct citation format referencing these fields.
* If search returns zero hits, tool message states empty result; model should acknowledge insufficient evidence (prompt contract — test via stub LLM sequence and prompt content tests).

### Source attribution chain

```text
SearchResult.source (core)
    ↓
MCP SearchHitSchema.source (Plan 10)
    ↓
tool message JSON
    ↓
LLM context
    ↓
user-visible citations (prompt contract)
```

Agent must not read `SourceReference` from storage or core retrieval types directly — only from MCP tool responses.

---

## Indexing Flow

### Structural support (Plan 12)

* `IndexDocumentsPreviewTool` and `IndexDocumentsApplyTool` registered alongside search.
* Model may call preview to estimate impact; apply requires explicit `approval_confirmed: true` in tool arguments matching MCP schema.
* If model calls apply without approval, MCP handler raises `ApprovalRequiredError` — adapter catches and returns deterministic tool error message.

### Human-in-the-loop UX

* **No** `input()` or stdin in agent core.
* Approval UX deferred to CLI wiring (future plan): CLI shows preview → user confirms → CLI re-invokes agent with apply tool call or sets a flag.
* Plan 12 tests may call apply tool directly with `approval_confirmed=True` via stub LLM scripts.

### Conservative scope

Indexing through the agent is **structurally supported** but not the primary demo path. Rich approval UX and indexing-first workflows are optional follow-ups.

---

## Conversation Memory

| Allowed | Deferred |
| ------- | -------- |
| In-memory `messages` tuple for one session | LangGraph checkpointer |
| Caller retains state between REPL turns in process | Persistent memory stores |
| | Long-term / multi-session memory |

---

## Public API and Module Layout

```text
agent/
    __init__.py       # intentional public exports
    state.py          # AgentState, reducers
    graph.py          # build_agent_graph(), compile, node functions
    tools.py          # AgentTool, ToolRegistry, concrete tools, registry factory
    prompts.py        # SYSTEM_PROMPT, citation instructions
    config.py         # AgentSettings (max_tool_iterations, default top_k hints)
    exceptions.py     # AgentError, UnknownToolError, MaxToolIterationsError, ...
```

**Optional (wiring only, not import-boundary “core”):**

```text
agent/wiring.py       # compose graph with concrete Retriever, IndexingPipeline, LLMClient
```

**Explicitly not in Plan 12:**

```text
agent/memory.py       # deferred
agent/rewrite.py      # deferred Plan 12b
cli/                  # no CLI implementation unless doc-only references
```

### Suggested public exports (`agent/__init__.py`)

```python
__all__ = [
    "AgentSettings",
    "AgentState",
    "UnknownToolError",
    "MaxToolIterationsError",
    "ToolRegistry",
    "build_agent_graph",
    "run_turn",  # or equivalent thin invoke wrapper
]
```

Keep exports minimal. Do not export private node functions unless needed for tests.

### Entry API sketch

```python
def run_turn(
    *,
    state: AgentState,
    user_message: str,
    llm_client: LLMClient,
    tool_registry: ToolRegistry,
    settings: AgentSettings | None = None,
) -> AgentState:
    """Append user message, invoke compiled LangGraph, return updated state."""
```

---

## Dependency Rules

### Allowed in agent core production code

| Dependency | Usage |
| ---------- | ----- |
| Python standard library | dataclasses, typing, json, enum |
| `langgraph` | StateGraph, compilation, conditional edges |
| `knowledge_assistant.llm` | protocol + DTOs only in core |
| `knowledge_assistant.mcp_server.tools` | handler functions |
| `knowledge_assistant.mcp_server.schemas` | request/response validation at adapter boundary |
| `knowledge_assistant.mcp_server.config` | `McpServerSettings` defaults |
| `knowledge_assistant.mcp_server.exceptions` | `ApprovalRequiredError` mapping |

### Allowed only in wiring / tests / factory modules

| Dependency | Usage |
| ---------- | ----- |
| `OpenAICompatibleLLMClient`, `StubLLMClient` | test and CLI construction |
| `knowledge_assistant.retrieval.*` concrete retrievers | inject into `search_documents` |
| `knowledge_assistant.indexing.pipeline` | inject into indexing handlers |
| Fake doubles in tests | isolated fixtures |

### Forbidden in agent core

| Dependency | Reason |
| ---------- | ------ |
| `qdrant_client`, `knowledge_assistant.storage` | Storage access only via MCP handlers at wiring |
| `knowledge_assistant.retrieval` (except via MCP handler injection in wiring) | No direct retrieval |
| `knowledge_assistant.indexing` (except via MCP handler injection in wiring) | No direct indexing |
| `llama_index`, `openai`, httpx | Wrong layers |
| `langchain`, LangChain tools | Avoid framework coupling |
| `mcp` SDK | Deferred ADR-043 |
| Embedding/reranker packages | ADR-013, ADR-041 |

### Who may import `agent/`

| Consumer | Allowed |
| -------- | ------- |
| `cli` | yes (future) |
| tests | yes |
| `llm`, `mcp_server`, `retrieval`, `indexing`, `storage` | **no** |

---

## Testing Strategy

### Unit tests — `tests/unit/agent/`

| Module | Focus |
| ------ | ----- |
| `test_state.py` | state validation, reducer append behavior |
| `test_tools.py` | registry dispatch, unknown tool, malformed JSON arguments, duplicate registration |
| `test_tool_adapters.py` | search/preview/apply adapters with fake handler dependencies |
| `test_graph_routing.py` | compiled graph routing with `StubLLMClient` |
| `test_prompts.py` | prompt templates include citation contract keywords/requirements |
| `test_exceptions.py` | error types |
| `test_agent_imports.py` | forbidden imports in core modules |

### Graph routing scenarios (mandatory)

| Scenario | Expected route |
| -------- | -------------- |
| LLM returns text only, no tool calls | `agent_node` → `END` |
| LLM returns tool call, then final text | `agent_node` → `tool_node` → `agent_node` → `END` |
| LLM keeps requesting tools until iteration limit | graph stops at max iterations; deterministic error/refusal |
| Unknown tool name from stub LLM | tool error message; graph may continue or END per design (must be documented in tests) |

### Integration tests — `tests/integration/agent/`

| Module | Focus |
| ------ | ----- |
| `test_agent_search_flow.py` | end-to-end: user question → stub LLM emits search → fake retriever hits → stub LLM final answer; assert tool called and state contains tool message with sources |
| `test_agent_indexing_tools.py` | preview + apply with approval; apply rejected without approval |
| `conftest.py` | `StubLLMClient` scripts, fake `Retriever`, fake `IndexingPipeline`, compiled graph fixture |

**Not required:** live LLM, live Qdrant, MCP SDK subprocess, network.

**Optional:** reuse existing in-memory Qdrant test patterns only if low-cost for one integration test — not mandatory for Plan 12 acceptance.

### Determinism rules

* All LLM behavior via `StubLLMClient` queued `GenerationResult` sequences.
* No assertions on exact natural-language answer wording except where prompt contract mandates fixed substrings (e.g. citation field labels in templates).
* Assert on: tool names invoked, message roles, routing path, iteration count, presence of source fields in tool JSON.

### Import boundary test pattern

Mirror `tests/unit/llm/test_llm_imports.py` and `tests/unit/mcp_server/test_mcp_imports.py`:

* scan `agent/*.py` excluding optional `wiring.py`;
* forbid `storage`, `qdrant_client`, `retrieval.dense`, `openai`, `httpx`, `llama_index`, etc.

---

## Runtime Dependencies

**Plan 12 adds:**

* `langgraph` — graph orchestration (explicit `pyproject.toml` dependency)

**Plan 12 does not add explicitly:**

* `langchain` / `langchain-core` — avoid direct use; transitive dependency from LangGraph is acceptable if unavoidable
* `mcp` SDK — deferred
* OpenAI SDK — remains in `llm/` only

Pin `langgraph` to a version compatible with Python 3.12+ and sync node functions during implementation.

---

## Documentation Updates (on implementation)

* `docs/DECISIONS.md` — accept ADR-042 through ADR-046;
* `docs/ARCHITECTURE.md` — new **Agent Layer** section (graph shape, tool registry, dependency rules, local MCP adapters note);
* `docs/PROGRESS.md` — Plan 12 completion entry;
* `README.md` — brief note that agent orchestration exists (optional CLI wiring may still be future);
* Consider updating `docs/plans/backlog/ROADMAP.md` Phase 7 deliverables to reflect deferred query rewriting (when activating plan).

Do **not** move this file to `docs/plans/active/` until explicitly authorized.

---

## Implementation Steps

1. **Config and exceptions** — `AgentSettings`, agent error hierarchy.
2. **State** — `AgentState` dataclass/TypedDict and message append reducer.
3. **Prompts** — system prompt with grounding and citation contract.
4. **Tools** — `AgentTool`, `ToolRegistry`, three MCP adapter tools, registry factory.
5. **Graph nodes** — `agent_node`, `tool_node`, `should_continue` conditional.
6. **Graph build** — `build_agent_graph(llm_client, tool_registry, settings) -> CompiledGraph`.
7. **Public API** — `run_turn` wrapper, `__init__.py` exports.
8. **Unit tests** — state, tools, routing, prompts, imports.
9. **Integration tests** — search flow, indexing tools, stub LLM sequences.
10. **Dependency** — add `langgraph` to `pyproject.toml`, lockfile update.
11. **Documentation** — ARCHITECTURE, DECISIONS, PROGRESS.
12. **Validation** — full quality suite.

---

## Acceptance Criteria

### LangGraph and orchestration

- [x] `langgraph` added to `pyproject.toml`
- [x] Compiled LangGraph implements `agent_node` / `tool_node` / `should_continue` topology
- [x] No top-level custom orchestration loop replaces LangGraph routing
- [x] Max tool iteration guard enforced and tested

### LLM integration

- [x] Agent core calls `LLMClient.chat` with Plan 11 DTOs only
- [x] Agent core does not import OpenAI provider modules or httpx
- [x] Multi-turn tool loop: assistant tool call → tool message → final assistant text

### Tool registry and MCP adapters

- [x] `ToolRegistry` dispatches `ToolCall` by name
- [x] `SearchDocumentsTool`, `IndexDocumentsPreviewTool`, `IndexDocumentsApplyTool` wrap Plan 10 handlers
- [x] Unknown tool and malformed arguments handled deterministically
- [x] Apply tool rejects missing approval via MCP error mapping

### RAG behavior

- [x] Agent can answer with no tools (general/conversational stub path)
- [x] Agent can execute `search_documents` tool call from stub LLM
- [x] Agent produces final answer after tool result in state
- [x] Prompt templates require grounding and citation using MCP source fields

### Boundaries

- [x] No direct `storage`, `qdrant_client`, or retrieval internals in agent core imports
- [x] No LlamaIndex, OpenAI SDK, or MCP SDK in agent core
- [x] Import-boundary tests pass

### Tests and validation

- [x] Graph routing tests (no tool / with tool / max iterations)
- [x] Tool registry tests
- [x] Integration test with `StubLLMClient` and fake MCP handler dependencies
- [x] `uv run ruff format --check .`, `ruff check .`, `basedpyright`, `pytest` pass

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| LangGraph API churn | Pin version; keep graph minimal; test routing explicitly |
| LangChain transitive dependency confusion | Document “no LangChain imports in agent code” in ADR-042 and import tests |
| Tool argument schema drift vs MCP | Single source: mirror `mcp_server/schemas.py`; adapter validation tests |
| Over-scoping CLI or MCP SDK | Strict non-scope; adapters only |
| Flaky tests asserting LLM prose | Assert structure, routing, and tool payloads only |

---

## Open Questions

1. **Default `max_tool_iterations`:** draft recommends **5** — confirm during activation.
2. **`wiring.py` placement:** single module under `agent/` vs defer all composition to future CLI plan — recommend optional `agent/wiring.py` excluded from core import tests.
3. **Parallel tool calls:** if model emits multiple tool calls in one turn, Plan 12 should execute all in `tool_node` before returning to `agent_node` — confirm during implementation.
4. **Future plan numbering:** **Plan 12b** (query rewrite/retry), **Plan 12c** (MCP SDK transport), **Plan 13+** (CLI chat) — align with ROADMAP when activating.

---

## Readiness Assessment

**Ready to move to active?** **Yes, with minor review.**

The draft defines graph shape, state, boundaries, tool adapters, deferred items, ADR candidates, tests, and acceptance criteria aligned with Plans 10–11 and `docs/ARCHITECTURE.md`. Before activation:

1. Review proposed ADRs (especially ADR-043 local adapters vs long-term MCP diagram).
2. Confirm ROADMAP Phase 7 text update for deferred query rewriting.
3. Confirm `langgraph` version pin strategy during implementation kickoff.

No architectural blockers identified relative to completed plans.

---

## Checklist

- [x] Plan moved to `docs/plans/active/`
- [ ] ADR-042 through ADR-046 accepted in `docs/DECISIONS.md` *(follow-up)*
- [x] `agent/` package implemented per module layout
- [x] `langgraph` dependency added
- [x] Unit and integration tests complete
- [x] `docs/ARCHITECTURE.md` Agent Layer section added
- [x] `docs/PROGRESS.md` updated
- [x] Full validation suite passes
- [x] Plan moved to `docs/plans/completed/` on completion
