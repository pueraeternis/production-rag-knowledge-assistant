"""LLM connection and generation settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    """Per-call generation overrides merged with LlmSettings defaults."""

    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stop: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.model is not None and not self.model.strip():
            msg = "GenerationSettings.model must be non-empty when set"
            raise ValueError(msg)
        if self.temperature is not None and self.temperature < 0:
            msg = "GenerationSettings.temperature must be >= 0 when set"
            raise ValueError(msg)
        if self.max_tokens is not None and self.max_tokens <= 0:
            msg = "GenerationSettings.max_tokens must be > 0 when set"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class LlmSettings:
    """Connection settings for an OpenAI-compatible LLM endpoint."""

    base_url: str
    api_key: str
    default_model: str
    timeout_seconds: float = 120.0
    default_generation: GenerationSettings = GenerationSettings(
        temperature=0.0,
        max_tokens=2048,
    )

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            msg = "LlmSettings.base_url must be non-empty"
            raise ValueError(msg)
        if not self.api_key:
            msg = "LlmSettings.api_key is required"
            raise ValueError(msg)
        if not self.default_model.strip():
            msg = "LlmSettings.default_model must be non-empty"
            raise ValueError(msg)
        if self.timeout_seconds <= 0:
            msg = "LlmSettings.timeout_seconds must be > 0"
            raise ValueError(msg)

    @classmethod
    def from_env(cls, **overrides: object) -> Self:
        """Build settings from ``LLM_*`` environment variables."""
        base_url = os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1")
        api_key = os.environ.get("LLM_API_KEY", "local")
        default_model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.6-35B-A3B")

        timeout_raw = os.environ.get("LLM_TIMEOUT_SECONDS", "120")
        temperature_raw = os.environ.get("LLM_TEMPERATURE", "0.0")
        max_tokens_raw = os.environ.get("LLM_MAX_TOKENS", "2048")

        timeout_seconds = float(timeout_raw)
        temperature = float(temperature_raw)
        max_tokens = int(max_tokens_raw)

        default_generation = GenerationSettings(
            temperature=temperature,
            max_tokens=max_tokens,
        )

        settings_kwargs: dict[str, object] = {
            "base_url": base_url.strip(),
            "api_key": api_key,
            "default_model": default_model.strip(),
            "timeout_seconds": timeout_seconds,
            "default_generation": default_generation,
        }
        settings_kwargs.update(overrides)
        return cls(**settings_kwargs)  # type: ignore[arg-type]
