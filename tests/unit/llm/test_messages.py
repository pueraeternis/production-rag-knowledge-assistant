"""Unit tests for LLM message and tool DTOs."""

import pytest

from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    GenerationResult,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


def test_chat_message_supports_all_roles() -> None:
    system = ChatMessage(role=ChatRole.SYSTEM, content="You are helpful.")
    user = ChatMessage(role=ChatRole.USER, content="Hello")
    assistant = ChatMessage(role=ChatRole.ASSISTANT, content="Hi")
    tool = ChatMessage(
        role=ChatRole.TOOL,
        content='{"result": "ok"}',
        tool_call_id="call-1",
    )

    assert system.role is ChatRole.SYSTEM
    assert user.role is ChatRole.USER
    assert assistant.role is ChatRole.ASSISTANT
    assert tool.role is ChatRole.TOOL


def test_tool_role_requires_tool_call_id() -> None:
    with pytest.raises(ValueError, match="tool_call_id is required"):
        ChatMessage(role=ChatRole.TOOL, content="done")


def test_tool_definition_requires_json_schema_object() -> None:
    tool = ToolDefinition(
        name="search_documents",
        description="Search the knowledge base",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    assert tool.name == "search_documents"


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"name": "", "description": "d", "parameters": {"type": "object"}}, "name"),
        (
            {"name": "n", "description": "", "parameters": {"type": "object"}},
            "description",
        ),
        (
            {"name": "n", "description": "d", "parameters": {"type": "string"}},
            "type 'object'",
        ),
    ],
)
def test_tool_definition_rejects_invalid_values(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        ToolDefinition(**kwargs)  # type: ignore[arg-type]


def test_tool_call_requires_json_object_arguments() -> None:
    call = ToolCall(id="call-1", name="search_documents", arguments='{"query":"x"}')
    assert call.arguments == '{"query":"x"}'


@pytest.mark.parametrize(
    ("arguments", "match", "error_type"),
    [
        ("not-json", "valid JSON", ValueError),
        ('["list"]', "JSON object", TypeError),
    ],
)
def test_tool_call_rejects_invalid_arguments(
    arguments: str,
    match: str,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type, match=match):
        ToolCall(id="call-1", name="search_documents", arguments=arguments)


def test_generation_result_defaults_tool_calls_to_empty_tuple() -> None:
    result = GenerationResult(content="hello")
    assert result.tool_calls == ()
    assert result.finish_reason is None


def test_token_usage_validates_non_negative_counts() -> None:
    usage = TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3)
    assert usage.total_tokens == 3

    with pytest.raises(ValueError, match="prompt_tokens"):
        TokenUsage(prompt_tokens=-1, completion_tokens=0, total_tokens=0)
