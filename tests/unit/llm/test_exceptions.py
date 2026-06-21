"""Unit tests for LLM exception hierarchy."""

from knowledge_assistant.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    LLMTransportError,
)


def test_llm_exception_hierarchy() -> None:
    assert issubclass(LLMTimeoutError, LLMError)
    assert issubclass(LLMAuthenticationError, LLMError)
    assert issubclass(LLMResponseError, LLMError)
    assert issubclass(LLMTransportError, LLMError)
