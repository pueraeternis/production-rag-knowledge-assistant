"""Concrete turn stream implementation for streaming agent execution."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.exceptions import UnknownToolError
from knowledge_assistant.agent.state import AgentState, append_messages
from knowledge_assistant.agent.tools import ToolRegistry, tool_error_content
from knowledge_assistant.agent.turn import (
    TurnExecutionError,
    TurnResult,
    TurnSource,
    collect_sources_from_messages,
)
from knowledge_assistant.llm.config import GenerationSettings
from knowledge_assistant.llm.messages import ChatMessage, ChatRole, StreamChunk
from knowledge_assistant.llm.protocol import LLMClient, StreamingLLMClient

_MAX_ITERATIONS_MESSAGE = (
    "Tool iteration limit reached. Unable to complete additional tool calls."
)


class ConcreteTurnStream:
    """Iterator over streamed assistant deltas with deferred ``TurnResult``."""

    def __init__(
        self,
        *,
        state_before_turn: AgentState,
        working_state: AgentState,
        llm_client: StreamingLLMClient,
        tool_registry: ToolRegistry,
        settings: AgentSettings,
    ) -> None:
        self._state_before_turn = state_before_turn
        self._working_state = working_state
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._settings = settings
        self._generation_settings = GenerationSettings()
        self._result: TurnResult | None = None
        self._failed = False
        self._iterator: Iterator[StreamChunk] | None = None

    def __iter__(self) -> Iterator[StreamChunk]:
        if self._iterator is not None:
            return self._iterator
        self._iterator = self._stream_turn()
        return self._iterator

    def result(self) -> TurnResult:
        if self._result is not None:
            return self._result
        if self._failed:
            msg = "turn stream failed before completion"
            raise TurnExecutionError(msg)
        msg = "turn stream is not complete; exhaust the iterator first"
        raise TurnExecutionError(msg)

    def _stream_turn(self) -> Iterator[StreamChunk]:
        try:
            post_tool_state, sources, outcome = run_tool_loop(
                state=self._working_state,
                llm_client=self._llm_client,
                tool_registry=self._tool_registry,
                settings=self._settings,
                generation_settings=self._generation_settings,
            )
            if outcome == "refusal":
                self._result = TurnResult(
                    state=post_tool_state,
                    answer=_MAX_ITERATIONS_MESSAGE,
                    sources=sources,
                )
                return

            answer_parts: list[str] = []
            for chunk in self._llm_client.stream_chat(
                post_tool_state.messages,
                settings=self._generation_settings,
                tools=(),
            ):
                answer_parts.append(chunk.content_delta)
                yield chunk

            answer = "".join(answer_parts)
            assistant_message = ChatMessage(role=ChatRole.ASSISTANT, content=answer)
            final_state = replace(
                post_tool_state,
                messages=(*post_tool_state.messages, assistant_message),
                final_response=answer,
                pending_tool_calls=(),
            )
            self._result = TurnResult(
                state=final_state,
                answer=answer,
                sources=sources,
            )
        except Exception:
            self._failed = True
            raise


def run_tool_loop(
    *,
    state: AgentState,
    llm_client: LLMClient,
    tool_registry: ToolRegistry,
    settings: AgentSettings,
    generation_settings: GenerationSettings,
) -> tuple[AgentState, tuple[TurnSource, ...], str]:
    """Execute tool-loop rounds with ``chat()`` until final text generation."""
    working_state = state
    sources: list[TurnSource] = []
    seen_source_keys: set[tuple[str, str, int, int]] = set()

    while True:
        result = llm_client.chat(
            working_state.messages,
            settings=generation_settings,
            tools=tool_registry.definitions(),
        )

        if result.tool_calls:
            assistant_message = ChatMessage(
                role=ChatRole.ASSISTANT,
                content=result.content,
                tool_calls=result.tool_calls,
            )
            working_state = append_messages(working_state, (assistant_message,))

            if working_state.tool_iteration_count >= settings.max_tool_iterations:
                refusal = ChatMessage(
                    role=ChatRole.ASSISTANT,
                    content=_MAX_ITERATIONS_MESSAGE,
                )
                final_state = replace(
                    working_state,
                    messages=(*working_state.messages, refusal),
                    final_response=_MAX_ITERATIONS_MESSAGE,
                    pending_tool_calls=(),
                )
                return final_state, tuple(sources), "refusal"

            tool_messages: list[ChatMessage] = []
            for call in result.tool_calls:
                try:
                    tool_message = tool_registry.dispatch(call)
                except UnknownToolError as exc:
                    tool_message = ChatMessage(
                        role=ChatRole.TOOL,
                        content=tool_error_content(
                            error="unknown_tool",
                            detail=f"unknown tool: {exc.tool_name}",
                        ),
                        tool_call_id=call.id,
                    )
                tool_messages.append(tool_message)
                if tool_message.content:
                    for source in collect_sources_from_messages((tool_message,)):
                        key = (
                            source.document_path,
                            source.section_title,
                            source.start_line,
                            source.end_line,
                        )
                        if key in seen_source_keys:
                            continue
                        seen_source_keys.add(key)
                        sources.append(source)

            working_state = replace(
                append_messages(working_state, tuple(tool_messages)),
                tool_iteration_count=working_state.tool_iteration_count + 1,
                pending_tool_calls=(),
            )
            continue

        return working_state, tuple(sources), "stream_final"
