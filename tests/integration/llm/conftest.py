"""Shared fixtures for LLM integration tests."""

import pytest

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings


@pytest.fixture
def llm_settings() -> LlmSettings:
    return LlmSettings(
        base_url="http://testserver/v1",
        api_key="integration-key",
        default_model="Qwen/Qwen3.6-35B-A3B",
        default_generation=GenerationSettings(temperature=0.0, max_tokens=256),
    )
