"""Unit tests for OpenAI-compatible client request/response mapping."""

import json
from typing import cast

import httpx
import pytest

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings
from knowledge_assistant.llm.exceptions import (
    LLMAuthenticationError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTransportError,
)
from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    ToolCall,
    ToolDefinition,
)
from knowledge_assistant.llm.openai_client import (
    OpenAICompatibleLLMClient,
    build_chat_request_body,
    parse_chat_response,
)


@pytest.fixture
def llm_settings() -> LlmSettings:
    return LlmSettings(
        base_url="http://testserver/v1",
        api_key="test-key",
        default_model="default-model",
        default_generation=GenerationSettings(temperature=0.0, max_tokens=128),
    )


def test_build_chat_request_body_merges_settings(llm_settings: LlmSettings) -> None:
    body = build_chat_request_body(
        (ChatMessage(role=ChatRole.USER, content="hello"),),
        llm_settings=llm_settings,
        settings=GenerationSettings(
            model="override-model", temperature=0.7, max_tokens=64
        ),
        tools=(
            ToolDefinition(
                name="search_documents",
                description="Search docs",
                parameters={"type": "object", "properties": {}},
            ),
        ),
    )

    assert body["model"] == "override-model"
    assert body["temperature"] == 0.7
    assert body["max_tokens"] == 64
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    tools = body["tools"]
    assert isinstance(tools, list)
    tool_items = cast(list[object], tools)
    first_tool_obj = tool_items[0]
    assert isinstance(first_tool_obj, dict)
    first_tool = cast(dict[str, object], first_tool_obj)
    function_obj = first_tool["function"]
    assert isinstance(function_obj, dict)
    function = cast(dict[str, object], function_obj)
    assert function["name"] == "search_documents"


def test_build_chat_request_body_serializes_assistant_tool_calls(
    llm_settings: LlmSettings,
) -> None:
    body = build_chat_request_body(
        (
            ChatMessage(
                role=ChatRole.ASSISTANT,
                content=None,
                tool_calls=(
                    ToolCall(
                        id="call-1",
                        name="search_documents",
                        arguments='{"query": "policy"}',
                    ),
                ),
            ),
        ),
        llm_settings=llm_settings,
    )

    messages = cast("list[dict[str, object]]", body["messages"])
    assistant = messages[0]
    tool_calls = cast("list[dict[str, object]]", assistant["tool_calls"])
    function = cast("dict[str, object]", tool_calls[0]["function"])
    assert function["name"] == "search_documents"
    assert function["arguments"] == '{"query": "policy"}'


def test_build_chat_request_body_omits_tools_when_empty(
    llm_settings: LlmSettings,
) -> None:
    body = build_chat_request_body(
        (ChatMessage(role=ChatRole.USER, content="hello"),),
        llm_settings=llm_settings,
    )
    assert "tools" not in body
    assert body["model"] == "default-model"


def test_parse_chat_response_maps_text_and_usage() -> None:
    payload = {
        "model": "remote-model",
        "choices": [
            {
                "message": {"content": "hello"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }

    result = parse_chat_response(payload)

    assert result.content == "hello"
    assert result.finish_reason == "stop"
    assert result.model == "remote-model"
    assert result.usage is not None
    assert result.usage.total_tokens == 15


def test_parse_chat_response_maps_tool_calls() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "search_documents",
                                "arguments": '{"query":"x"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    result = parse_chat_response(payload)

    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_documents"


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"choices": []}, "non-empty list"),
        ({"choices": [{"finish_reason": "stop"}]}, "missing message"),
        (
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "search_documents",
                                        "arguments": "not-json",
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            "malformed tool_calls",
        ),
    ],
)
def test_parse_chat_response_rejects_malformed_payload(
    payload: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(LLMResponseError, match=match):
        parse_chat_response(payload)


def _mock_transport(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_openai_client_posts_to_chat_completions(llm_settings: LlmSettings) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "model": "default-model",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            },
        )

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=_mock_transport(httpx.MockTransport(handler)),
    )

    result = client.chat((ChatMessage(role=ChatRole.USER, content="hello"),))

    assert result.content == "ok"
    assert captured["url"] == "http://testserver/v1/chat/completions"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["authorization"] == "Bearer test-key"


def test_openai_client_maps_timeout_to_llm_timeout_error(
    llm_settings: LlmSettings,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=_mock_transport(httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMTimeoutError, match="timed out"):
        client.chat((ChatMessage(role=ChatRole.USER, content="hello"),))


@pytest.mark.parametrize("status_code", [401, 403])
def test_openai_client_maps_auth_errors(
    llm_settings: LlmSettings,
    status_code: int,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="unauthorized")

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=_mock_transport(httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMAuthenticationError):
        client.chat((ChatMessage(role=ChatRole.USER, content="hello"),))


def test_openai_client_maps_invalid_json_to_response_error(
    llm_settings: LlmSettings,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=_mock_transport(httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMResponseError, match="valid JSON"):
        client.chat((ChatMessage(role=ChatRole.USER, content="hello"),))


def test_openai_client_maps_non_auth_http_errors_to_transport_error(
    llm_settings: LlmSettings,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=_mock_transport(httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMTransportError, match="HTTP 500"):
        client.chat((ChatMessage(role=ChatRole.USER, content="hello"),))
