# Plan 11 — LLM Boundary

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 6 — LLM Integration

**Depends on:**

* [Plan 02 — Python Bootstrap](../completed/02-python-bootstrap.md)

**Architecture audit:** Incorporates findings from the pre-Plan-11 architecture audit (2026-06-21). No architectural blockers were identified; this plan addresses audit recommendations explicitly.

**Plan principle:** One plan introduces one architectural capability. Plan 11 introduces the **LLM invocation boundary** only.

---

## Objective

Design and implement a thin, provider-neutral, OpenAI-compatible model invocation layer that higher layers (Plan 12 LangGraph agent, future CLI wiring) can call without importing retrieval, indexing, MCP, or agent code.

```text
LangGraph Agent (Plan 12)
    ↓
LLMClient.chat(messages, settings?, tools?)   ← Plan 11 delivers this layer
    ↓
OpenAI-compatible /v1/chat/completions
    ↓
vLLM / OpenAI / LiteLLM / Open WebUI proxy / other gateway
```

After this plan is complete:

* **`knowledge_assistant.llm`** exposes a chat-oriented `LLMClient` protocol with typed message, settings, tool-call transport DTOs, and `GenerationResult`;
* production wiring can call a remote model via `OpenAICompatibleLLMClient(LlmSettings)` configured from environment variables;
* tests use `StubLLMClient` and mocked HTTP — no live model calls in CI;
* import-boundary tests enforce that `llm/` does not depend on knowledge layers or frameworks;
* `docs/ARCHITECTURE.md` documents the LLM boundary section (currently missing);
* ADR entries ADR-035 through ADR-041 are recorded on completion.

**Dependency rule:** `llm` production code may depend on the Python standard library, an OpenAI-compatible HTTP transport dependency (see Design Evaluation 1), and internal `knowledge_assistant.llm` modules only. Plan 11 does **not** require imports from `knowledge_assistant.core`; production code should not import `core` unless a concrete need arises during implementation. It must **not** depend on `storage`, `indexing`, `retrieval`, `mcp_server`, `agent`, `qdrant_client`, `llama_index`, `langgraph`, `mcp`, embedding packages, or reranker packages.

**Critical guardrail (from architecture audit):** if Plan 11 imports `mcp_server` or `retrieval`, or assembles retrieved chunks into prompts, the boundary has been violated.

---

## Scope

This plan authorizes implementation within:

* `src/knowledge_assistant/llm/` — protocol, DTOs, settings, clients, exceptions;
* `.env.example` at repository root;
* associated unit tests and HTTP-mocked integration tests;
* ADR entries and documentation updates.

### In Scope

* `LLMClient` protocol — chat-centric, sync-first, non-streaming;
* LLM-local frozen dataclass DTOs: `ChatMessage`, `ChatRole`, `ToolDefinition`, `ToolCall`, `GenerationSettings`, `GenerationResult`, optional `TokenUsage`;
* `LlmSettings` with `from_env()` loader and validation;
* `OpenAICompatibleLLMClient` — maps DTOs to `/v1/chat/completions` JSON and back;
* `StubLLMClient` — deterministic, scriptable responses for tests;
* `exceptions.py` — typed error mapping (timeout, unauthorized, malformed response, transport failures);
* `.env.example` with documented OpenAI-compatible variables;
* unit tests: settings validation, message/tool DTO validation, stub client, response parsing, error mapping;
* integration tests: `OpenAICompatibleLLMClient` against mocked HTTP;
* import-boundary tests for `llm/`;
* ADR entries ADR-035 through ADR-041;
* updates to `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, and `README.md` (local LLM setup section).

---

## Non-Scope

This plan does **not** authorize:

* LangGraph agent implementation (Plan 12);
* MCP SDK runtime, MCP client, or MCP server transport (Plan 12);
* prompt templates for RAG answers, system prompts, or citation rendering;
* RAG context assembly (chunk text → prompt sections);
* source citation rendering in final answers;
* query rewriting, intent classification, or retrieval retry flows;
* conversation memory, LangGraph state, or checkpointers;
* tool execution loop or tool-calling orchestration (when to call tools, MCP handler dispatch);
* MCP tool schema generation from handler signatures;
* structured output parsing (JSON mode, Pydantic parse helpers);
* streaming chat completions;
* embeddings or embedding providers (ADR-013);
* reranking or cross-encoder model runtime (ADR-027);
* evaluation framework or demo dataset generation;
* real vLLM/Qwen integration tests in CI;
* async `LLMClient` API (defer unless Plan 12 requires it — start sync per audit);
* DI container, plugin registry, or multi-provider factory beyond direct client construction;
* changes to `knowledge_assistant.core` domain models;
* changes to `mcp_server`, `retrieval`, `indexing`, or `storage`;
* `AppError`-rooted exception hierarchy (deferred);
* smoke tests against live LLM endpoints.

**ROADMAP Phase 6 wording:** “prompt contracts” in the roadmap means **typed message and generation contracts** (this plan), not RAG/system prompt templates (Plan 12).

---

## Architectural Decisions

The following decisions are **proposed** for this plan. Implementation must follow them; reopen only via plan revision.

### ADR-035 — OpenAI-Compatible API Standard

**Status:** Accepted

#### Context

The project targets an initial runtime of vLLM serving `Qwen/Qwen3.6-35B-A3B` via base URL, but must remain provider-neutral. `PROJECT.md` and `docs/ARCHITECTURE.md` position the LLM boundary as the sole model-call layer. Multiple gateways expose the same HTTP contract.

#### Decision

* The project standardizes on an **OpenAI-compatible** `/v1/chat/completions` style API for model invocation.
* `OpenAICompatibleLLMClient` posts JSON to `{base_url}/chat/completions` (with `base_url` typically ending in `/v1`).
* The same `LLMClient` protocol must work against:
  * vLLM;
  * OpenAI;
  * LiteLLM;
  * Open WebUI proxy;
  * other OpenAI-compatible gateways.
* The protocol and DTOs must **not** depend on a specific provider SDK response shape or model family.
* Provider-specific behavior (headers, retries, path normalization) stays inside `openai_client.py` implementation modules.
* Non-streaming JSON responses only in Plan 11 (`stream: false` or omitted).

#### Consequences

* Local development copies `.env.example` → `.env` and points `LLM_BASE_URL` at a vLLM instance.
* Switching providers requires config changes only — no code changes in higher layers.
* Request/response mapping tests use fixture JSON, not provider SDK mocks.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Provider-native SDK protocols (Anthropic, etc.) | Out of project scope; lecture uses OpenAI-compatible stack |
| Raw text `/v1/completions` API | Plan 12 needs multi-turn chat and tool messages; chat API supersedes |
| LangChain / LangGraph LLM wrappers inside `llm/` | Couples boundary to agent framework; violates layering |
| Hardcoded Qwen request fields | Violates provider neutrality |

---

### ADR-036 — LLM Boundary Ownership

**Status:** Accepted

#### Context

ADR-013 assigns embeddings to indexing and retrieval. ADR-027 assigns reranking to retrieval. ADR-032 forbids `mcp_server → llm`. AGENTS.md states only the LangGraph agent may communicate with the LLM boundary. Plan 10 delivers knowledge access without answer generation.

#### Decision

* `knowledge_assistant.llm` owns **model invocation only**:
  * `LLMClient` protocol;
  * chat message and tool-call transport DTOs;
  * generation settings;
  * connection settings (`LlmSettings`);
  * OpenAI-compatible HTTP adapter;
  * stub client for tests;
  * LLM-specific exceptions.
* `llm/` does **not** own:
  * retrieval, indexing, or storage;
  * MCP tool handlers or MCP transport;
  * agent workflows, routing, or memory;
  * prompt templates for grounded answers;
  * query rewriting;
  * RAG context assembly;
  * tool execution or orchestration loops;
  * embeddings or reranking.
* Only `agent` (Plan 12) and `cli` (wiring) are expected consumers of `llm/` in the documented architecture.
* `mcp_server`, `retrieval`, `indexing`, and `storage` must not import `llm/`.

#### Consequences

* Plan 12 composes `LLMClient` + MCP client without redesigning Plan 11 contracts.
* Import-boundary tests enforce the ownership split mechanically.
* The seam after Plan 10 remains: MCP returns evidence; agent + LLM produce answers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared `llm/` module for embeddings + chat | Violates ADR-013; blurs retrieval/indexing ownership |
| MCP calls LLM for answer synthesis | Violates ADR-032 and documented dependency flow |
| RAG prompts in `llm/` | Encodes product behavior in wrong layer; untestable without retrieval |

---

### ADR-037 — Chat-First LLM Client Protocol

**Status:** Accepted

#### Context

Plan 12 requires multi-turn conversation, system/user/assistant/tool roles, and model-emitted tool calls for MCP integration. A completion-only API would force redesign. Existing layers (`VectorStore`, `Retriever`) establish a protocol + settings + stub pattern.

#### Decision

* Expose a **chat-oriented** API as the sole `LLMClient` entry point — not a raw text completion API.
* Protocol shape:

```python
class LLMClient(Protocol):
    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        ...
```

* `messages` is an immutable tuple; callers append new messages per turn — the client does not mutate conversation state.
* `settings=None` merges per-call overrides with `LlmSettings` defaults.
* `tools=()` means no tools sent to the provider (empty tuple, not `None`, for a stable signature).
* Sync-first implementation; async extension deferred to a future ADR if Plan 12 requires it.
* Non-streaming only in Plan 11.

#### Consequences

* Plan 12 LangGraph nodes call `chat` repeatedly as the conversation grows.
* Tool-calling orchestration (execute MCP handlers, append `role=tool` messages) stays in the agent.
* Unit tests script multi-turn sequences via `StubLLMClient`.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Separate `complete(prompt: str)` method | Duplicates chat; encourages prompt strings in wrong layer |
| Async-only protocol | Existing codebase is sync; premature for Plan 11 |
| Streaming `chat` | Not required for CLI demo v1; adds parser complexity |
| LangGraph `BaseChatModel` adapter in `llm/` | Framework coupling in infrastructure layer |

---

### ADR-038 — Tool-Call Transport DTOs Without Orchestration

**Status:** Accepted

#### Context

OpenAI-compatible chat completions expose tool definitions in the request and `tool_calls` in the response. Plan 12 must pass MCP tool schemas to the model and interpret returned tool calls. Plan 11 must not execute tools or decide when to call them.

#### Decision

* Plan 11 defines typed **transport DTOs** only:
  * `ToolDefinition` — `name`, `description`, `parameters: dict[str, object]` (JSON Schema object);
  * `ToolCall` — `id`, `name`, `arguments: str` (JSON string, OpenAI-compatible).
* `GenerationResult` includes `tool_calls: tuple[ToolCall, ...]` (empty when the model returns text only).
* `ChatMessage` supports `role=tool` with `tool_call_id` and optional `name` for tool result messages.
* `llm/` maps these DTOs to/from provider JSON in `openai_client.py` only.
* Plan 11 must **not**:
  * execute tools;
  * validate tool arguments against MCP handler contracts;
  * map MCP handler names to `ToolDefinition` instances;
  * implement agent tool loops.

#### Consequences

* Plan 12 owns MCP tool schema construction and handler dispatch.
* LLM tests verify JSON mapping with fixture payloads, not MCP semantics.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Defer tool DTOs to Plan 12 | Would require Plan 11 API redesign when agent work starts |
| Pydantic models for tool schemas in `llm/` | Unnecessary; dataclass + `dict` parameters suffice (see Design Evaluations) |
| Tool execution inside `openai_client.py` | Violates MCP and agent ownership |

---

### ADR-039 — LLM-Local Types and Dataclass Boundary

**Status:** Accepted

#### Context

ADR-001 excludes Pydantic from `core`. ADR-033 confines Pydantic to `mcp_server/schemas.py`. `ChatMessage` is infrastructure transport data, not knowledge domain data. The pre-Plan-11 audit recommends frozen dataclasses in `llm/` for consistency with `core` and to avoid ADR-033 conflicts.

#### Decision

* All Plan 11 DTOs use `@dataclass(frozen=True, slots=True)` with `__post_init__` validation where needed.
* `ChatMessage`, `ChatRole`, `ToolDefinition`, `ToolCall`, `GenerationSettings`, `GenerationResult`, and `TokenUsage` live in `llm/` — **not** in `knowledge_assistant.core`.
* Plan 11 does **not** add Pydantic to `llm/`.
* Plan 11 does **not** import from `knowledge_assistant.core` — no concrete need is identified for Plan 11 deliverables. If implementation later discovers a justified use of a core type, that is an implementation choice, not a Plan 11 requirement; do **not** record a permanent architectural rule forbidding `llm → core`.

#### Consequences

* Clear separation by default: `core` = knowledge domain; `llm` = model transport.
* Plan 11 keeps `llm/` self-contained; a future plan may introduce `llm → core` if a concrete need emerges.
* Plan 12 translates between MCP Pydantic schemas and LLM dataclasses at the agent boundary.
* Validation errors raise `ValueError` at construction time (consistent with other layers).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `ChatMessage` in `core` | Not knowledge domain; couples domain layer to OpenAI message shape |
| Pydantic in `llm/schemas.py` | No strong justification; ADR-033 pattern is MCP-specific |
| TypedDict messages | No runtime validation; weaker invariant enforcement |

---

### ADR-040 — Environment Configuration for LLM Settings

**Status:** Accepted

#### Context

Initial runtime uses vLLM with user-supplied base URL and credentials via `.env`. `StorageSettings.from_env()` establishes a minimal explicit loader pattern. Generation defaults must be validated and separable from per-call overrides.

#### Decision

* Add `.env.example` at repository root with:

```dotenv
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=local
LLM_MODEL=Qwen/Qwen3.6-35B-A3B
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2048
LLM_TIMEOUT_SECONDS=120
```

* Implement `LlmSettings.from_env()` (or equivalent explicit loader on `LlmSettings`) using `os.environ.get` — **no** `python-dotenv` runtime dependency in Plan 11 (users and shells load `.env`; tests pass explicit constructor args).
* Environment → settings mapping:

| Environment variable | `LlmSettings` / defaults field | Validation |
| -------------------- | -------------------------------- | ---------- |
| `LLM_BASE_URL` | `base_url` | non-empty after strip |
| `LLM_API_KEY` | `api_key` | required string (may be dummy e.g. `local` for vLLM) |
| `LLM_MODEL` | `default_model` | non-empty after strip |
| `LLM_TIMEOUT_SECONDS` | `timeout_seconds` | `> 0` |
| `LLM_TEMPERATURE` | `default_generation.temperature` | `>= 0` |
| `LLM_MAX_TOKENS` | `default_generation.max_tokens` | `> 0` |

* `LlmSettings` structure:

```python
@dataclass(frozen=True, slots=True)
class LlmSettings:
    base_url: str
    api_key: str
    default_model: str
    timeout_seconds: float = 120.0
    default_generation: GenerationSettings = ...  # built from env temperature/max_tokens
```

* `GenerationSettings` holds per-call overrides: `model`, `temperature`, `max_tokens`, optional `stop: tuple[str, ...]`.
* Per-call `GenerationSettings` fields override `LlmSettings.default_generation` and `default_model` in `OpenAICompatibleLLMClient` merge logic.
* `.env` remains gitignored; `.env.example` is committed.

#### Consequences

* README documents copy `.env.example` → `.env` for local vLLM setup.
* Tests construct `LlmSettings(...)` directly without reading environment.
* Model name in `.env.example` is illustrative default only — not hardcoded in client logic.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| `python-dotenv` in library code | Hidden magic; tests should use explicit settings |
| Pydantic `BaseSettings` | Unnecessary dependency for six variables |
| Single flat settings object without per-call `GenerationSettings` | Plan 12 needs per-turn temperature/token overrides |

---

### ADR-041 — Embeddings and Reranking Remain Outside LLM

**Status:** Accepted

#### Context

ADR-013 establishes embedding ownership for indexing (write path) and retrieval (query path). ADR-027 places cross-encoder reranking in retrieval. A future regression could add embedding helpers to `llm/` because “models live near LLMs.”

#### Decision

* `llm/` must **not** implement embeddings, sparse vectors, or reranking.
* `llm/` must not import `knowledge_assistant.retrieval` or `knowledge_assistant.indexing`.
* Import-boundary tests explicitly forbid embedding/reranker package names (`sentence_transformers`, `transformers`, `torch`) in `llm/`.
* Plan 11 documentation cross-links ADR-013 and ADR-027 in the LLM architecture section.

#### Consequences

* Embedding and reranker runtimes remain in their owning layers per existing ADRs.
* Plan 11 scope cannot creep into “model utilities.”

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared `models/` package for all ML inference | Premature; violates established layer ownership |
| Reranker in `llm/` because it uses a transformer | ADR-027 explicitly rejects this |

---

## Design Evaluations

### 1. HTTP transport for OpenAI-compatible API

Plan 11 requires an **OpenAI-compatible HTTP transport** that posts JSON to `/v1/chat/completions` and maps responses into Plan 11 DTOs. The transport must preserve:

* OpenAI-compatible API behavior (request/response contract per ADR-035);
* DTO ownership (`ChatMessage`, `GenerationResult`, etc. remain llm-local dataclasses);
* provider neutrality (no model-family or vendor-specific branches in the protocol);
* testability (mockable without live endpoints in CI).

| Option | Pros | Cons |
| ------ | ---- | ---- |
| **`httpx` (recommended)** | Explicit request/response control; `MockTransport` for tests; no provider SDK shape leakage | New runtime dependency |
| Official `openai` Python SDK with `base_url` | Battle-tested parsing; widely used with vLLM | SDK types may leak into tests; must still map to Plan 11 DTOs at boundary |
| Stdlib `urllib` | Zero deps | Verbose; poor ergonomics for JSON + timeouts |

**Decision:** implement the transport in `openai_client.py` using **`httpx` as the recommended default**. An alternative HTTP client or the official `openai` SDK is permitted if it satisfies the four constraints above, keeps provider-specific code inside `openai_client.py`, and does not expose SDK types through the public `llm/` API. Automated tests mock the transport — no network in CI.

### 2. Schema technology

**Decision:** frozen stdlib dataclasses only (ADR-039). No Pydantic in `llm/`.

### 3. Client construction vs factory

**Decision:** prefer direct construction: `OpenAICompatibleLLMClient(settings)` and `StubLLMClient(...)`. No DI container or `create_llm_client()` factory unless implementation discovers unavoidable wiring complexity (unlikely).

### 4. `ChatRole` representation

**Decision:** stdlib `enum.Enum` with values `system`, `user`, `assistant`, `tool` — serializes to OpenAI role strings.

### 5. `GenerationResult` fields

| Field | Type | Notes |
| ----- | ---- | ----- |
| `content` | `str \| None` | Assistant text; may be `None` when `tool_calls` present |
| `tool_calls` | `tuple[ToolCall, ...]` | Empty tuple when none |
| `finish_reason` | `str \| None` | Pass-through from provider (`stop`, `length`, `tool_calls`, etc.) |
| `model` | `str \| None` | Resolved model name from response |
| `usage` | `TokenUsage \| None` | Optional `prompt_tokens`, `completion_tokens`, `total_tokens` |

### 6. Exception taxonomy

| Exception | When raised |
| --------- | ----------- |
| `LLMError` | Base for all LLM boundary failures |
| `LLMTimeoutError` | HTTP timeout exceeded (`LLM_TIMEOUT_SECONDS`) |
| `LLMAuthenticationError` | HTTP 401/403 |
| `LLMResponseError` | Malformed JSON, missing `choices`, unexpected shape |
| `LLMTransportError` | Connection errors, non-auth HTTP failures (optional subclass of `LLMError`) |

Map provider errors in `openai_client.py` only; protocol methods raise typed `LLMError` subclasses — not raw HTTP client exceptions.

### 7. `StubLLMClient` behavior

**Decision:** scriptable queue of `GenerationResult` responses keyed by call index or by matching last user message substring. Default single response for simple tests. Deterministic — no randomness, no network.

### 8. Request merge rules (`OpenAICompatibleLLMClient`)

Resolved per call:

| Field | Precedence |
| ----- | ---------- |
| `model` | `settings.model` → `LlmSettings.default_model` |
| `temperature` | `settings.temperature` → `default_generation.temperature` |
| `max_tokens` | `settings.max_tokens` → `default_generation.max_tokens` |
| `stop` | `settings.stop` → `default_generation.stop` → omitted |
| `timeout` | always `LlmSettings.timeout_seconds` |

POST body includes `messages` and `tools` arrays mapped from DTOs. Omit `tools` key when `tools=()`.

### 9. Public client type name

| Name | Assessment |
| ---- | ---------- |
| `OpenAICompatibleLLMClient` | **Selected.** Pairs with `StubLLMClient`; distinguishes the concrete HTTP adapter from the `LLMClient` protocol; signals LLM-boundary ownership without implying OpenAI-only deployment. |
| `OpenAICompatibleClient` | Shorter, but ambiguous outside the `llm/` package and does not mirror `StubLLMClient` naming. |
| `OpenAIClient` | Implies OpenAI as the provider; misleading when the primary target is vLLM, LiteLLM, or other gateways. |

**Decision:** keep **`OpenAICompatibleLLMClient`** as the public concrete client name exported from `llm/__init__.py`.

---

## Module Layout

```text
llm/
    __init__.py          # minimal public exports (see API Design)
    protocol.py          # LLMClient Protocol
    messages.py          # ChatRole, ChatMessage, ToolDefinition, ToolCall,
                         # GenerationResult, TokenUsage
    config.py            # LlmSettings, GenerationSettings, from_env loader
    exceptions.py        # LLMError hierarchy
    openai_client.py     # OpenAICompatibleLLMClient (HTTP transport)
    stub_client.py       # StubLLMClient
```

**Explicitly not authorized in Plan 11:**

```text
llm/prompts.py           # deferred to Plan 12
llm/schemas.py           # no Pydantic
llm/factory.py           # no DI container
llm/streaming.py         # deferred
agent/                   # Plan 12
```

**Repository root:**

```text
.env.example             # committed LLM configuration template
```

---

## API Design

### `LLMClient` (protocol.py)

```python
class LLMClient(Protocol):
    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        ...
```

### `ChatRole` (messages.py)

`enum.Enum`: `SYSTEM`, `USER`, `ASSISTANT`, `TOOL` with `.value` matching OpenAI role strings.

### `ChatMessage` (messages.py)

| Field | Type | Required | Validation |
| ----- | ---- | -------- | ---------- |
| `role` | `ChatRole` | yes | — |
| `content` | `str \| None` | no | `tool` role may have `content`; `assistant` with only tool calls may have `None` |
| `name` | `str \| None` | no | optional |
| `tool_call_id` | `str \| None` | no | required when `role=TOOL` |

### `ToolDefinition` (messages.py)

| Field | Type | Validation |
| ----- | ---- | ---------- |
| `name` | `str` | non-empty |
| `description` | `str` | non-empty |
| `parameters` | `dict[str, object]` | JSON Schema object (`type: object` at top level) |

### `ToolCall` (messages.py)

| Field | Type | Validation |
| ----- | ---- | ---------- |
| `id` | `str` | non-empty |
| `name` | `str` | non-empty |
| `arguments` | `str` | valid JSON object string (parseable) |

### `GenerationSettings` (config.py)

| Field | Type | Default | Validation |
| ----- | ---- | ------- | ---------- |
| `model` | `str \| None` | `None` | non-empty when set |
| `temperature` | `float \| None` | `None` | `>= 0` when set |
| `max_tokens` | `int \| None` | `None` | `> 0` when set |
| `stop` | `tuple[str, ...]` | `()` | — |

### `LlmSettings` (config.py)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `base_url` | `str` | e.g. `http://localhost:8000/v1` |
| `api_key` | `str` | sent as `Authorization: Bearer …` |
| `default_model` | `str` | e.g. `Qwen/Qwen3.6-35B-A3B` |
| `timeout_seconds` | `float` | default `120.0` |
| `default_generation` | `GenerationSettings` | env-derived defaults |

`classmethod from_env(cls, **overrides) -> Self` — mirror `StorageSettings.from_env()` pattern.

### `OpenAICompatibleLLMClient` (openai_client.py)

```python
class OpenAICompatibleLLMClient:
    def __init__(self, settings: LlmSettings) -> None: ...

    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult: ...
```

### `StubLLMClient` (stub_client.py)

```python
class StubLLMClient:
    def __init__(
        self,
        responses: tuple[GenerationResult, ...],
    ) -> None: ...

    def chat(...) -> GenerationResult: ...  # returns scripted sequence
```

### Public exports (`llm/__init__.py`)

Export **only**:

```python
__all__ = [
    "ChatMessage",
    "ChatRole",
    "GenerationResult",
    "GenerationSettings",
    "LLMClient",
    "LLMError",
    "LLMAuthenticationError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LlmSettings",
    "OpenAICompatibleLLMClient",
    "StubLLMClient",
    "ToolCall",
    "ToolDefinition",
    "TokenUsage",
]
```

Do **not** export: HTTP client library types, internal parsers, private helpers, or `LLMTransportError` unless promoted intentionally.

Add `__version__` re-export only if already present at package root — do not duplicate version in `llm/`.

---

## Dependency Rules

### Allowed in `llm/` production code

| Dependency | Usage |
| ---------- | ----- |
| Python standard library | dataclasses, enum, typing, json, os |
| OpenAI-compatible HTTP transport | Recommended: `httpx` in `openai_client.py`; alternatives allowed per Design Evaluation 1 |
| `knowledge_assistant.llm.*` | internal modules |
| `knowledge_assistant.core` | **Not required for Plan 11.** Allowed only if implementation discovers a concrete need; not a Plan 11 deliverable |

### Forbidden in `llm/` production code

| Dependency | Reason |
| ---------- | ------ |
| `knowledge_assistant.storage` | Violates dependency flow |
| `knowledge_assistant.indexing` | Embedding ownership (ADR-013) |
| `knowledge_assistant.retrieval` | Deterministic layer; `retrieval → llm` forbidden |
| `knowledge_assistant.mcp_server` | `mcp_server → llm` forbidden (ADR-032) |
| `knowledge_assistant.agent` | Reverse dependency |
| `qdrant_client`, `llama_index`, `langgraph`, `mcp` | Framework / infrastructure leakage |
| `torch`, `transformers`, `sentence-transformers` | Embeddings/reranking |
| `pydantic` | Dataclass boundary (ADR-039) |

### Who may import `llm/`

| Consumer | Allowed |
| -------- | ------- |
| `agent` | yes (Plan 12) |
| `cli` | yes (wiring) |
| `core`, `storage`, `indexing`, `retrieval`, `mcp_server` | **no** |

---

## Testing Strategy

### Unit Tests — `tests/unit/llm/`

| Module | Focus |
| ------ | ----- |
| `test_config.py` | `LlmSettings` / `GenerationSettings` validation; `from_env` with `monkeypatch` |
| `test_messages.py` | `ChatMessage`, `ToolDefinition`, `ToolCall` invariants |
| `test_stub_client.py` | scripted multi-turn responses; tool_call sequences |
| `test_openai_client.py` | request JSON mapping; response parsing; settings merge (mock HTTP transport) |
| `test_exceptions.py` | timeout, 401, malformed body → typed exceptions |
| `test_llm_imports.py` | forbidden knowledge-layer imports; HTTP transport dependency confined to `openai_client.py` (no permanent `core` prohibition) |

### Integration Tests — `tests/integration/llm/`

| Module | Focus |
| ------ | ----- |
| `test_openai_client_integration.py` | `OpenAICompatibleLLMClient` with mocked HTTP transport and realistic fixture payloads |
| `conftest.py` | shared fixtures, sample `/v1/chat/completions` JSON |

**Not required:** live vLLM, live OpenAI, subprocess tests, Qdrant, MCP.

### Error mapping test cases (mandatory)

| Scenario | Expected exception |
| -------- | ------------------- |
| HTTP timeout | `LLMTimeoutError` |
| HTTP 401 / 403 | `LLMAuthenticationError` |
| Empty `choices` array | `LLMResponseError` |
| Missing `message` field | `LLMResponseError` |
| Invalid JSON body | `LLMResponseError` |
| Malformed `tool_calls` entry | `LLMResponseError` |

### Validation Commands

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

---

## Manual Validation

Plan 11 supports **manual** verification against a real OpenAI-compatible endpoint configured through `.env`. This flow is for local development only — it is **not** executed in CI and is **not** a substitute for automated tests.

Intended use: validate connectivity to a local vLLM instance or other OpenAI-compatible deployment before Plan 12 agent integration.

### Steps

1. **Configure `.env`** — copy `.env.example` to `.env` and set `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and optional generation defaults to match the running server.
2. **Create client** — load settings and construct the production client:

```python
from knowledge_assistant.llm import (
    ChatMessage,
    ChatRole,
    LlmSettings,
    OpenAICompatibleLLMClient,
)

settings = LlmSettings.from_env()
client = OpenAICompatibleLLMClient(settings)
```

3. **Send a simple user message**:

```python
result = client.chat(
    (ChatMessage(role=ChatRole.USER, content="Reply with the word ok."),),
)
```

4. **Verify successful response** — assert `result.content` is non-empty (or inspect manually); confirm no transport, authentication, or parsing exceptions.

This verification may be documented in `README.md` as an optional developer workflow. It does not require a committed script, smoke test module, or CI job.

---

## Dependencies

**Plan 11 adds (recommended):**

* `httpx` — HTTP transport for `OpenAICompatibleLLMClient` in `openai_client.py`

**Plan 11 may add (alternative):**

* another HTTP client or the official `openai` SDK — only if the chosen implementation satisfies Design Evaluation 1 and keeps SDK types out of the public API

**Plan 11 does not add:**

* `langgraph`, `mcp`, `python-dotenv`, `torch`, `transformers`, `sentence-transformers`, `pydantic` (already present for MCP — not imported by `llm/`)

---

## Documentation Updates

On implementation completion:

* `docs/DECISIONS.md` — ADR-035 through ADR-041;
* `docs/ARCHITECTURE.md`:
  * new **LLM Boundary** section (protocol, settings, clients, dependency rule);
  * chat invocation diagram (`agent → llm → OpenAI-compatible endpoint`);
  * explicit note that embeddings and reranking are not in `llm/`;
* `docs/PROGRESS.md` — Plan 11 completion entry;
* `README.md` — section on copying `.env.example` to `.env`, pointing at a local vLLM (or compatible) server, and optional manual validation steps;
* `.env.example` — committed at repository root.

Do not update `docs/plans/backlog/ROADMAP.md` (informational).

---

## Implementation Steps

1. **Exceptions** — `exceptions.py` with `LLMError` hierarchy.
2. **Messages** — `messages.py` DTOs with validation (`ChatRole`, `ChatMessage`, `ToolDefinition`, `ToolCall`, `GenerationResult`, `TokenUsage`).
3. **Config** — `config.py` with `GenerationSettings`, `LlmSettings`, `from_env()`.
4. **Protocol** — `protocol.py` with `LLMClient`.
5. **Stub client** — `StubLLMClient` with scripted responses.
6. **OpenAI client** — `OpenAICompatibleLLMClient` with HTTP transport (recommended: httpx), request builder, response parser, settings merge, error mapping.
7. **Public API** — `__init__.py` exports per API Design section.
8. **`.env.example`** — document required variables.
9. **Unit tests** — config, messages, stub, client mapping, exceptions, import boundaries.
10. **Integration tests** — mocked HTTP round-trip with fixture JSON.
11. **Documentation** — ARCHITECTURE, DECISIONS, PROGRESS, README.
12. **Validation** — full quality suite.

---

## Acceptance Criteria

### LLM Package and Boundaries

- [x] `llm/` package per module layout
- [x] Plan 11 implementation does not import `core` unless a concrete need is documented in the change set
- [x] No imports from `storage`, `indexing`, `retrieval`, `mcp_server`, `agent`
- [x] No `langgraph`, `mcp`, `qdrant_client`, `llama_index`, embedding, or reranker packages in `llm/` production code
- [x] HTTP transport dependency used only in `openai_client.py`
- [x] No Pydantic in `llm/`
- [x] `llm/` does not implement embeddings or reranking

### Protocol and DTOs

- [x] `LLMClient.chat` accepts `messages`, optional `settings`, and `tools` tuple
- [x] `ChatMessage` supports `system`, `user`, `assistant`, `tool` roles
- [x] `ToolDefinition` and `ToolCall` transport DTOs exist
- [x] `GenerationResult` includes `content`, `tool_calls`, `finish_reason`
- [x] DTOs are frozen dataclasses with validation

### Configuration

- [x] `.env.example` committed with all six `LLM_*` variables
- [x] `LlmSettings.from_env()` loads and validates environment variables
- [x] `base_url` and `default_model` non-empty; `timeout_seconds > 0`; `temperature >= 0`; `max_tokens > 0`
- [x] A developer can verify connectivity to a real OpenAI-compatible endpoint using configuration from `.env` without modifying source code (manual validation only; not CI)

### Clients

- [x] `StubLLMClient` returns deterministic scripted responses without network
- [x] `OpenAICompatibleLLMClient` posts to `{base_url}/chat/completions`
- [x] Request/response mapping covered by unit tests with mocked HTTP
- [x] Error mapping: timeout, unauthorized, malformed response

### Public API

- [x] `llm/__init__.py` exports only documented public types
- [x] `OpenAICompatibleLLMClient(settings)` direct construction works

### Tests and Validation

- [x] Unit tests for settings, messages, stub, client, exceptions, imports
- [x] Integration test with mocked HTTP transport
- [x] Full validation commands pass

### Documentation

- [x] ADR-035 through ADR-041 in `docs/DECISIONS.md`
- [x] LLM Boundary section in `docs/ARCHITECTURE.md`
- [x] Plan 11 recorded in `docs/PROGRESS.md`
- [x] `README.md` documents `.env.example`, local LLM setup, and optional manual endpoint validation

### Non-Scope (must not block Plan 11)

- [x] No LangGraph, MCP SDK, prompts, RAG assembly, or tool execution loop
- [x] No streaming or structured output parsing
- [x] No changes to `mcp_server`, `retrieval`, `indexing`, or `storage`

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into RAG prompts | ADR-036; explicit non-scope; import guards |
| Plan 12 needs tool calls but Plan 11 omitted them | ADR-038 defines transport DTOs in Plan 11 |
| Pydantic boundary conflict with ADR-033 | ADR-039 — dataclasses only in `llm/` |
| Embedding logic drifts into `llm/` | ADR-041 + import guards forbid retrieval/indexing |
| Provider JSON shape differences | Parser tests with vLLM-style fixtures; tolerant optional fields |
| HTTP transport choice (`httpx` vs SDK) | Design Evaluation 1 documents recommended default and allowed alternatives |
| vLLM requires dummy API key | Document `LLM_API_KEY=local`; client always sends Bearer header |
| ROADMAP “prompt contracts” misread | Plan states: message/generation contracts only |

---

## Follow-Up Work (Not Plan 11)

| Item | Target |
| ---- | ------ |
| Plan 12 — LangGraph Agent | Completed — [12-langgraph-agent.md](../completed/12-langgraph-agent.md) |
| Streaming chat completions | Future plan or Plan 12 revision if required |
| Async `LLMClient` | Future ADR if LangGraph async demands it |
| Structured output helpers | Plan 12+ if intent routing needs JSON mode |
| Live LLM smoke tests | Optional `tests/smoke/` — not Plan 11 |

---

## Checklist

- [x] Read AGENTS.md, PROJECT.md, ARCHITECTURE.md, DECISIONS.md, Plan 10, pre-Plan-11 audit
- [x] Implement LLM DTOs and protocol (dataclass boundary)
- [x] Implement `LlmSettings.from_env()` and `.env.example`
- [x] Implement `StubLLMClient` and `OpenAICompatibleLLMClient`
- [x] Add unit and integration tests with import boundaries
- [x] Run full validation suite
- [x] Optionally verify manual endpoint validation flow against a real server
- [x] Update DECISIONS.md, ARCHITECTURE.md, PROGRESS.md, README.md
- [x] Move plan to `completed/` when acceptance criteria satisfied
