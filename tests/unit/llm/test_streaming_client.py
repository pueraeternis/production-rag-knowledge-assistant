"""Unit tests for streaming LLM capability."""

import json

import httpx
import pytest

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings
from knowledge_assistant.llm.exceptions import LLMResponseError
from knowledge_assistant.llm.messages import ChatMessage, ChatRole, GenerationResult
from knowledge_assistant.llm.openai_client import (
    OpenAICompatibleLLMClient,
    iter_sse_content_deltas,
)
from knowledge_assistant.llm.protocol import StreamingLLMClient
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.llm.stub_client import StubLLMClient


@pytest.fixture
def llm_settings() -> LlmSettings:
    return LlmSettings(
        base_url="http://testserver/v1",
        api_key="test-key",
        default_model="default-model",
        default_generation=GenerationSettings(temperature=0.0, max_tokens=128),
    )


def test_iter_sse_content_deltas_parses_text_chunks() -> None:
    lines = iter(
        [
            'data: {"choices":[{"delta":{"content":"Hel"}}]}',
            "",
            'data: {"choices":[{"delta":{"content":"lo"}}]}',
            "data: [DONE]",
        ],
    )
    assert list(iter_sse_content_deltas(lines)) == ["Hel", "lo"]


def test_iter_sse_content_deltas_rejects_tool_call_deltas() -> None:
    lines = iter(
        [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0}]}}]}',
        ],
    )
    with pytest.raises(LLMResponseError, match="tool call deltas"):
        list(iter_sse_content_deltas(lines))


def test_streaming_stub_client_yields_configured_deltas() -> None:
    client = StreamingStubLLMClient(
        responses=(GenerationResult(content="ignored"),),
        stream_deltas=("A", "B"),
    )
    chunks = list(
        client.stream_chat((ChatMessage(role=ChatRole.USER, content="hi"),)),
    )
    assert [chunk.content_delta for chunk in chunks] == ["A", "B"]
    assert client.stream_call_count == 1


def test_stub_llm_client_does_not_implement_stream_chat() -> None:
    client = StubLLMClient(responses=(GenerationResult(content="ok"),))
    assert not isinstance(client, StreamingLLMClient)


def test_openai_client_stream_chat_posts_with_stream_flag(
    llm_settings: LlmSettings,
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        sse = 'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=sse)

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    chunks = list(
        client.stream_chat((ChatMessage(role=ChatRole.USER, content="hello"),)),
    )
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["stream"] is True
    assert [chunk.content_delta for chunk in chunks] == ["Hi"]
