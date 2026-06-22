"""Regression tests for FlagEmbedding reranker dependency compatibility."""

from __future__ import annotations

from importlib.metadata import version

import pytest
from packaging.version import Version

from knowledge_assistant.retrieval.config import BgeRerankerSettings
from knowledge_assistant.retrieval.rerank import load_flag_embedding_reranker_backend


def test_transformers_version_is_below_v5_for_flag_embedding_reranker() -> None:
    """FlagEmbedding 1.4.0 needs tokenizer.prepare_for_model (removed in v5)."""
    installed = Version(version("transformers"))
    assert installed < Version("5.0.0"), (
        "FlagEmbedding 1.4.0 reranker is incompatible with transformers>=5; "
        "pin transformers<5 in pyproject.toml"
    )


@pytest.mark.real_model
def test_flag_embedding_reranker_backend_scores_pair_on_cpu() -> None:
    settings = BgeRerankerSettings(device="cpu", use_fp16=False)
    backend = load_flag_embedding_reranker_backend(settings)
    scores = backend.compute_scores(
        [("remote work policy", "Employees may work remotely up to 3 days.")],
        batch_size=1,
        max_length=512,
    )
    assert len(scores) == 1
    assert isinstance(scores[0], float)
