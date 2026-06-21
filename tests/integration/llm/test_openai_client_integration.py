"""Integration tests for OpenAICompatibleLLMClient with mocked HTTP."""

import json

import httpx

from knowledge_assistant.llm import ChatMessage, ChatRole, OpenAICompatibleLLMClient
from knowledge_assistant.llm.config import LlmSettings

SAMPLE_CHAT_COMPLETION_RESPONSE = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 1710000000,
    "model": "Qwen/Qwen3.6-35B-A3B",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The answer is grounded in retrieved evidence.",
            },
            "finish_reason": "stop",
        },
    ],
    "usage": {
        "prompt_tokens": 42,
        "completion_tokens": 12,
        "total_tokens": 54,
    },
}


def test_openai_client_round_trip_with_realistic_fixture(
    llm_settings: LlmSettings,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["model"] == llm_settings.default_model
        assert body["messages"] == [
            {"role": "user", "content": "What is hybrid retrieval?"},
        ]
        return httpx.Response(200, json=SAMPLE_CHAT_COMPLETION_RESPONSE)

    client = OpenAICompatibleLLMClient(
        llm_settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.chat(
        (ChatMessage(role=ChatRole.USER, content="What is hybrid retrieval?"),),
    )

    assert result.content == "The answer is grounded in retrieved evidence."
    assert result.finish_reason == "stop"
    assert result.model == "Qwen/Qwen3.6-35B-A3B"
    assert result.usage is not None
    assert result.usage.total_tokens == 54
