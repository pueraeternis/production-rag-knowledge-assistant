"""OpenAI-compatible LLM invocation boundary."""

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings
from knowledge_assistant.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
)
from knowledge_assistant.llm.messages import (
    ChatMessage,
    ChatRole,
    GenerationResult,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from knowledge_assistant.llm.openai_client import OpenAICompatibleLLMClient
from knowledge_assistant.llm.protocol import LLMClient, StreamingLLMClient
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.llm.stub_client import StubLLMClient

__all__ = [
    "ChatMessage",
    "ChatRole",
    "GenerationResult",
    "GenerationSettings",
    "LLMAuthenticationError",
    "LLMClient",
    "LLMError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LlmSettings",
    "OpenAICompatibleLLMClient",
    "StreamChunk",
    "StreamingLLMClient",
    "StreamingStubLLMClient",
    "StubLLMClient",
    "TokenUsage",
    "ToolCall",
    "ToolDefinition",
]
