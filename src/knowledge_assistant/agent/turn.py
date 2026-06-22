"""Turn result types and source extraction for agent execution."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.llm.messages import ChatMessage, ChatRole, StreamChunk
from knowledge_assistant.mcp_server.schemas import SearchDocumentsResponse


@dataclass(frozen=True, slots=True)
class TurnSource:
    """Structured citation metadata surfaced at the turn boundary."""

    document_title: str
    document_path: str
    section_title: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class TurnResult:
    """Completed agent turn with answer text and structured sources."""

    state: AgentState
    answer: str
    sources: tuple[TurnSource, ...] = ()


class TurnStream(Protocol):
    """Typed stream of assistant text deltas with deferred turn result."""

    def __iter__(self) -> Iterator[StreamChunk]:
        """Yield incremental assistant text chunks."""
        ...

    def result(self) -> TurnResult:
        """Return the completed turn after stream exhaustion."""
        ...


class TurnExecutionError(RuntimeError):
    """Raised when a turn stream is incomplete or execution fails."""


def _source_key(source: TurnSource) -> tuple[str, str, int, int]:
    return (
        source.document_path,
        source.section_title,
        source.start_line,
        source.end_line,
    )


def sources_from_search_tool_content(content: str) -> tuple[TurnSource, ...]:
    """Extract deduplicated sources from a search_documents tool JSON payload."""
    try:
        response = SearchDocumentsResponse.model_validate_json(content)
    except ValidationError:
        return ()

    sources: list[TurnSource] = []
    seen: set[tuple[str, str, int, int]] = set()
    for hit in response.hits:
        turn_source = TurnSource(
            document_title=hit.source.document_title,
            document_path=hit.source.document_path,
            section_title=hit.source.section_title,
            start_line=hit.source.line_range.start_line,
            end_line=hit.source.line_range.end_line,
        )
        key = _source_key(turn_source)
        if key in seen:
            continue
        seen.add(key)
        sources.append(turn_source)
    return tuple(sources)


def collect_sources_from_messages(
    messages: tuple[ChatMessage, ...],
) -> tuple[TurnSource, ...]:
    """Collect deduplicated search sources from tool messages in rank order."""
    sources: list[TurnSource] = []
    seen: set[tuple[str, str, int, int]] = set()
    for message in messages:
        if message.role is not ChatRole.TOOL or not message.content:
            continue
        for source in sources_from_search_tool_content(message.content):
            key = _source_key(source)
            if key in seen:
                continue
            seen.add(key)
            sources.append(source)
    return tuple(sources)


def messages_added_during_turn(
    before: AgentState,
    after: AgentState,
) -> tuple[ChatMessage, ...]:
    """Return messages appended between two agent states."""
    return after.messages[len(before.messages) :]
