"""Retrieval configuration."""

import os
from dataclasses import dataclass
from typing import Literal, cast

RerankerMode = Literal["stub", "real"]


@dataclass(frozen=True, slots=True)
class DenseRetrievalSettings:
    """Configuration for dense retrieval and query embedding dimensions."""

    dense_vector_size: int = 1024

    def __post_init__(self) -> None:
        if self.dense_vector_size <= 0:
            msg = "dense_vector_size must be > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FusionRetrievalSettings:
    """Configuration for hybrid rank-based fusion."""

    rrf_k: int = 60
    leaf_top_k_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.rrf_k < 1:
            msg = "rrf_k must be >= 1"
            raise ValueError(msg)
        if self.leaf_top_k_multiplier < 1:
            msg = "leaf_top_k_multiplier must be >= 1"
            raise ValueError(msg)

    def resolve_leaf_top_k(self, query_top_k: int) -> int:
        """Candidate pool size forwarded to each leaf retriever."""
        return query_top_k * self.leaf_top_k_multiplier


@dataclass(frozen=True, slots=True)
class RerankRetrievalSettings:
    """Configuration for reranked retrieval candidate pool expansion."""

    candidate_top_k_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.candidate_top_k_multiplier < 1:
            msg = "candidate_top_k_multiplier must be >= 1"
            raise ValueError(msg)

    def resolve_candidate_top_k(self, query_top_k: int) -> int:
        """Candidate pool size forwarded to the base retriever."""
        return query_top_k * self.candidate_top_k_multiplier


@dataclass(frozen=True, slots=True)
class BgeRerankerSettings:
    """Configuration for the BGE cross-encoder reranker runtime."""

    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "auto"
    batch_size: int = 16
    max_length: int = 1024
    use_fp16: bool = False

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            msg = "model_name must be non-empty"
            raise ValueError(msg)
        if not _is_supported_device(self.device):
            msg = "device must be 'auto', 'cpu', 'cuda', or an explicit cuda device"
            raise ValueError(msg)
        if self.batch_size < 1:
            msg = "batch_size must be >= 1"
            raise ValueError(msg)
        if self.max_length < 1:
            msg = "max_length must be >= 1"
            raise ValueError(msg)
        if self.device == "cpu" and self.use_fp16:
            msg = "use_fp16 must be false for cpu device"
            raise ValueError(msg)

    @classmethod
    def from_env(cls, **overrides: object) -> "BgeRerankerSettings":
        """Load BGE reranker runtime settings from environment variables."""
        defaults = cls()
        model_name = str(
            overrides.pop(
                "model_name",
                os.environ.get("RAG_RERANKER_MODEL", defaults.model_name),
            ),
        )
        device = str(
            overrides.pop(
                "device",
                os.environ.get("RAG_RERANKER_DEVICE", defaults.device),
            ),
        )
        batch_size = _parse_int_value(
            overrides.pop(
                "batch_size",
                _parse_positive_int_env(
                    "RAG_RERANKER_BATCH_SIZE",
                    defaults.batch_size,
                ),
            ),
            name="batch_size",
        )
        max_length = _parse_int_value(
            overrides.pop(
                "max_length",
                _parse_positive_int_env(
                    "RAG_RERANKER_MAX_LENGTH",
                    defaults.max_length,
                ),
            ),
            name="max_length",
        )
        use_fp16 = _parse_bool_value(
            overrides.pop(
                "use_fp16",
                _parse_bool_env("RAG_RERANKER_USE_FP16", defaults.use_fp16),
            ),
            name="use_fp16",
        )
        if overrides:
            unexpected = ", ".join(sorted(overrides))
            msg = f"unexpected BGE reranker settings overrides: {unexpected}"
            raise TypeError(msg)
        return cls(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            max_length=max_length,
            use_fp16=use_fp16,
        )


def parse_reranker_mode(value: str | None) -> RerankerMode:
    """Parse the bootstrap reranker implementation mode."""
    mode = (value or "stub").strip().lower()
    if mode not in {"stub", "real"}:
        msg = "reranker mode must be 'stub' or 'real'"
        raise ValueError(msg)
    return cast(RerankerMode, mode)


def _is_supported_device(device: str) -> bool:
    if device in {"auto", "cpu", "cuda"}:
        return True
    if not device.startswith("cuda:"):
        return False
    suffix = device.removeprefix("cuda:")
    return suffix.isdigit()


def _parse_positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        msg = f"{name} must be an integer"
        raise ValueError(msg) from exc


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    msg = f"{name} must be a boolean"
    raise ValueError(msg)


def _parse_bool_value(value: object, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    msg = f"{name} must be a boolean"
    raise ValueError(msg)


def _parse_int_value(value: object, *, name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            msg = f"{name} must be an integer"
            raise ValueError(msg) from exc
    msg = f"{name} must be an integer"
    raise ValueError(msg)
