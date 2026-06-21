"""Unit tests for StubLLMClient."""

import pytest

from knowledge_assistant.llm import (
    ChatMessage,
    ChatRole,
    GenerationResult,
    StubLLMClient,
)


def test_stub_client_returns_scripted_responses_in_order() -> None:
    client = StubLLMClient(
        responses=(
            GenerationResult(content="first"),
            GenerationResult(content="second"),
        )
    )
    message = (ChatMessage(role=ChatRole.USER, content="hello"),)

    first = client.chat(message)
    second = client.chat(message)

    assert first.content == "first"
    assert second.content == "second"


def test_stub_client_returns_tool_call_sequence() -> None:
    from knowledge_assistant.llm import ToolCall

    tool_result = GenerationResult(
        content=None,
        tool_calls=(
            ToolCall(id="call-1", name="search_documents", arguments='{"query":"x"}'),
        ),
        finish_reason="tool_calls",
    )
    text_result = GenerationResult(content="done", finish_reason="stop")
    client = StubLLMClient(responses=(tool_result, text_result))

    first = client.chat((ChatMessage(role=ChatRole.USER, content="search"),))
    second = client.chat((ChatMessage(role=ChatRole.USER, content="continue"),))

    assert first.tool_calls[0].name == "search_documents"
    assert second.content == "done"


def test_stub_client_requires_at_least_one_response() -> None:
    with pytest.raises(ValueError, match="at least one"):
        StubLLMClient(responses=())


def test_stub_client_raises_when_responses_are_exhausted() -> None:
    client = StubLLMClient(responses=(GenerationResult(content="once"),))
    message = (ChatMessage(role=ChatRole.USER, content="hello"),)
    client.chat(message)

    with pytest.raises(IndexError, match="exhausted"):
        client.chat(message)
