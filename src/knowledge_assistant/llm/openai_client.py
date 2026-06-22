"""OpenAI-compatible HTTP chat completion client."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, Self, cast

import httpx

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings
from knowledge_assistant.llm.exceptions import (
    LLMAuthenticationError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTransportError,
)
from knowledge_assistant.llm.messages import (
    ChatMessage,
    GenerationResult,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _merge_generation_settings(
    llm_settings: LlmSettings,
    call_settings: GenerationSettings | None,
) -> dict[str, object]:
    defaults = llm_settings.default_generation
    overrides = call_settings or GenerationSettings()

    model = overrides.model or llm_settings.default_model
    temperature = (
        overrides.temperature
        if overrides.temperature is not None
        else defaults.temperature
    )
    max_tokens = (
        overrides.max_tokens
        if overrides.max_tokens is not None
        else defaults.max_tokens
    )
    stop = overrides.stop or defaults.stop

    body: dict[str, object] = {
        "model": model,
    }
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if stop:
        body["stop"] = list(stop)
    return body


def _tool_call_to_payload(call: ToolCall) -> dict[str, object]:
    return {
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.name,
            "arguments": call.arguments,
        },
    }


def _message_to_payload(message: ChatMessage) -> dict[str, object]:
    payload: dict[str, object] = {"role": message.role.value}
    if message.content is not None:
        payload["content"] = message.content
    elif message.tool_calls:
        payload["content"] = None
    if message.name is not None:
        payload["name"] = message.name
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    if message.tool_calls:
        payload["tool_calls"] = [
            _tool_call_to_payload(tool_call) for tool_call in message.tool_calls
        ]
    return payload


def _tool_to_payload(tool: ToolDefinition) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def build_chat_request_body(
    messages: tuple[ChatMessage, ...],
    *,
    llm_settings: LlmSettings,
    settings: GenerationSettings | None = None,
    tools: tuple[ToolDefinition, ...] = (),
) -> dict[str, object]:
    """Build the JSON body for an OpenAI-compatible chat completion request."""
    body = _merge_generation_settings(llm_settings, settings)
    body["messages"] = [_message_to_payload(message) for message in messages]
    if tools:
        body["tools"] = [_tool_to_payload(tool) for tool in tools]
    return body


def _parse_tool_calls(raw_tool_calls: object) -> tuple[ToolCall, ...]:
    if not isinstance(raw_tool_calls, list):
        msg = "tool_calls must be a list"
        raise LLMResponseError(msg)

    entries = cast("list[object]", raw_tool_calls)
    parsed: list[ToolCall] = []
    for entry_obj in entries:
        if not isinstance(entry_obj, dict):
            msg = "tool_calls entry must be an object"
            raise LLMResponseError(msg)
        entry = cast("dict[str, Any]", entry_obj)
        function_obj = entry.get("function")
        if not isinstance(function_obj, dict):
            msg = "tool_calls entry is missing function object"
            raise LLMResponseError(msg)
        function = cast("dict[str, Any]", function_obj)
        tool_id = entry.get("id")
        name = function.get("name")
        arguments = function.get("arguments")
        if not isinstance(tool_id, str) or not tool_id.strip():
            msg = "tool_calls entry is missing id"
            raise LLMResponseError(msg)
        if not isinstance(name, str) or not name.strip():
            msg = "tool_calls entry is missing function name"
            raise LLMResponseError(msg)
        if not isinstance(arguments, str):
            msg = "tool_calls entry is missing function arguments"
            raise LLMResponseError(msg)
        try:
            parsed.append(ToolCall(id=tool_id, name=name, arguments=arguments))
        except ValueError as exc:
            msg = f"malformed tool_calls entry: {exc}"
            raise LLMResponseError(msg) from exc
    return tuple(parsed)


def _parse_usage(raw_usage: object) -> TokenUsage | None:
    if raw_usage is None:
        return None
    if not isinstance(raw_usage, dict):
        msg = "usage must be an object"
        raise LLMResponseError(msg)
    usage = cast("dict[str, Any]", raw_usage)
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    if not all(
        isinstance(value, int)
        for value in (prompt_tokens, completion_tokens, total_tokens)
    ):
        msg = "usage fields must be integers"
        raise LLMResponseError(msg)
    assert isinstance(prompt_tokens, int)
    assert isinstance(completion_tokens, int)
    assert isinstance(total_tokens, int)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def parse_chat_response(payload: dict[str, Any]) -> GenerationResult:
    """Parse an OpenAI-compatible chat completion JSON response."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "response choices must be a non-empty list"
        raise LLMResponseError(msg)

    choice_items = cast("list[object]", choices)
    first_choice_obj = choice_items[0]
    if not isinstance(first_choice_obj, dict):
        msg = "choice must be an object"
        raise LLMResponseError(msg)
    first_choice = cast("dict[str, Any]", first_choice_obj)

    message_obj = first_choice.get("message")
    if not isinstance(message_obj, dict):
        msg = "choice is missing message object"
        raise LLMResponseError(msg)
    message = cast("dict[str, Any]", message_obj)

    content_obj = message.get("content")
    content: str | None
    if content_obj is None:
        content = None
    elif isinstance(content_obj, str):
        content = content_obj
    else:
        msg = "message content must be a string when present"
        raise LLMResponseError(msg)

    raw_tool_calls = message.get("tool_calls")
    tool_calls: tuple[ToolCall, ...] = ()
    if raw_tool_calls is not None:
        tool_calls = _parse_tool_calls(raw_tool_calls)

    finish_reason_obj = first_choice.get("finish_reason")
    finish_reason: str | None
    if finish_reason_obj is None:
        finish_reason = None
    elif isinstance(finish_reason_obj, str):
        finish_reason = finish_reason_obj
    else:
        msg = "finish_reason must be a string when present"
        raise LLMResponseError(msg)

    model_obj = payload.get("model")
    model: str | None
    if model_obj is None:
        model = None
    elif isinstance(model_obj, str):
        model = model_obj
    else:
        msg = "model must be a string when present"
        raise LLMResponseError(msg)

    usage = _parse_usage(payload.get("usage"))

    return GenerationResult(
        content=content,
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        model=model,
        usage=usage,
    )


def _parse_stream_chunk_payload(payload: dict[str, Any]) -> str | None:
    """Extract a text delta from one SSE JSON payload."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    choice_items = cast("list[object]", choices)
    first_choice_obj = choice_items[0]
    if not isinstance(first_choice_obj, dict):
        msg = "stream choice must be an object"
        raise LLMResponseError(msg)
    first_choice = cast("dict[str, Any]", first_choice_obj)

    delta_obj = first_choice.get("delta")
    if not isinstance(delta_obj, dict):
        return None
    delta = cast("dict[str, Any]", delta_obj)

    if delta.get("tool_calls") is not None:
        msg = "streaming does not support tool call deltas"
        raise LLMResponseError(msg)

    content_obj = delta.get("content")
    if content_obj is None:
        return None
    if not isinstance(content_obj, str):
        msg = "stream delta content must be a string when present"
        raise LLMResponseError(msg)
    return content_obj


def iter_sse_content_deltas(lines: Iterator[str]) -> Iterator[str]:
    """Yield non-empty text deltas from OpenAI-compatible SSE lines."""
    for raw_line in lines:
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        try:
            payload_obj = json.loads(data)
        except json.JSONDecodeError as exc:
            msg = "stream data line is not valid JSON"
            raise LLMResponseError(msg) from exc
        if not isinstance(payload_obj, dict):
            msg = "stream data payload must be a JSON object"
            raise LLMResponseError(msg)
        payload = cast("dict[str, Any]", payload_obj)
        content_delta = _parse_stream_chunk_payload(payload)
        if content_delta:
            yield content_delta


class OpenAICompatibleLLMClient:
    """Posts chat completion requests to an OpenAI-compatible HTTP endpoint."""

    def __init__(
        self,
        settings: LlmSettings,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.timeout_seconds)

    def chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> GenerationResult:
        body = build_chat_request_body(
            messages,
            llm_settings=self._settings,
            settings=settings,
            tools=tools,
        )
        url = _chat_completions_url(self._settings.base_url)
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self._client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            msg = f"LLM request timed out after {self._settings.timeout_seconds}s"
            raise LLMTimeoutError(msg) from exc
        except httpx.RequestError as exc:
            msg = f"LLM transport error: {exc}"
            raise LLMTransportError(msg) from exc

        if response.status_code in (401, 403):
            msg = f"LLM authentication failed with HTTP {response.status_code}"
            raise LLMAuthenticationError(msg)

        if response.status_code >= 400:
            msg = f"LLM request failed with HTTP {response.status_code}"
            raise LLMTransportError(msg)

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            msg = "LLM response body is not valid JSON"
            raise LLMResponseError(msg) from exc

        if not isinstance(payload, dict):
            msg = "LLM response body must be a JSON object"
            raise LLMResponseError(msg)

        return parse_chat_response(cast("dict[str, Any]", payload))

    def stream_chat(
        self,
        messages: tuple[ChatMessage, ...],
        *,
        settings: GenerationSettings | None = None,
        tools: tuple[ToolDefinition, ...] = (),
    ) -> Iterator[StreamChunk]:
        body = build_chat_request_body(
            messages,
            llm_settings=self._settings,
            settings=settings,
            tools=tools,
        )
        body["stream"] = True
        url = _chat_completions_url(self._settings.base_url)
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with self._client.stream(
                "POST",
                url,
                headers=headers,
                json=body,
            ) as response:
                if response.status_code in (401, 403):
                    msg = f"LLM authentication failed with HTTP {response.status_code}"
                    raise LLMAuthenticationError(msg)

                if response.status_code >= 400:
                    msg = f"LLM request failed with HTTP {response.status_code}"
                    raise LLMTransportError(msg)

                for content_delta in iter_sse_content_deltas(
                    response.iter_lines(),
                ):
                    yield StreamChunk(content_delta=content_delta)
        except httpx.TimeoutException as exc:
            msg = f"LLM request timed out after {self._settings.timeout_seconds}s"
            raise LLMTimeoutError(msg) from exc
        except httpx.RequestError as exc:
            msg = f"LLM transport error: {exc}"
            raise LLMTransportError(msg) from exc

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
