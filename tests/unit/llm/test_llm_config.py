"""Unit tests for LLM settings."""

import pytest

from knowledge_assistant.llm.config import GenerationSettings, LlmSettings


def test_generation_settings_accepts_valid_overrides() -> None:
    settings = GenerationSettings(
        model="test-model",
        temperature=0.5,
        max_tokens=512,
        stop=("END",),
    )
    assert settings.model == "test-model"
    assert settings.temperature == 0.5
    assert settings.max_tokens == 512
    assert settings.stop == ("END",)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"model": ""}, "model must be non-empty"),
        ({"model": "   "}, "model must be non-empty"),
        ({"temperature": -0.1}, "temperature must be >= 0"),
        ({"max_tokens": 0}, "max_tokens must be > 0"),
    ],
)
def test_generation_settings_rejects_invalid_values(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        GenerationSettings(**kwargs)  # type: ignore[arg-type]


def test_llm_settings_validates_required_fields() -> None:
    settings = LlmSettings(
        base_url="http://localhost:8000/v1",
        api_key="local",
        default_model="test-model",
    )
    assert settings.timeout_seconds == 120.0
    assert settings.default_generation.temperature == 0.0
    assert settings.default_generation.max_tokens == 2048


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"base_url": ""}, "base_url must be non-empty"),
        ({"api_key": ""}, "api_key is required"),
        ({"default_model": ""}, "default_model must be non-empty"),
        ({"timeout_seconds": 0}, "timeout_seconds must be > 0"),
    ],
)
def test_llm_settings_rejects_invalid_values(
    kwargs: dict[str, str | float],
    match: str,
) -> None:
    settings_kwargs: dict[str, str | float] = {
        "base_url": "http://localhost:8000/v1",
        "api_key": "local",
        "default_model": "test-model",
    }
    settings_kwargs.update(kwargs)
    with pytest.raises(ValueError, match=match):
        LlmSettings(**settings_kwargs)  # type: ignore[arg-type]


def test_llm_settings_from_env_reads_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "remote-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_MAX_TOKENS", "1024")

    settings = LlmSettings.from_env()

    assert settings.base_url == "http://example.com/v1"
    assert settings.api_key == "secret"
    assert settings.default_model == "remote-model"
    assert settings.timeout_seconds == 90.0
    assert settings.default_generation.temperature == 0.2
    assert settings.default_generation.max_tokens == 1024


def test_llm_settings_from_env_applies_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://example.com/v1")
    settings = LlmSettings.from_env(default_model="override-model")
    assert settings.default_model == "override-model"
