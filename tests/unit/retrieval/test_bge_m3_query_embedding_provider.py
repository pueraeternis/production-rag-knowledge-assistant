"""Unit tests for BGE-M3 retrieval query embedding adapter."""

from unittest.mock import MagicMock

from knowledge_assistant.retrieval.embeddings import BgeM3QueryEmbeddingProvider


class TestBgeM3QueryEmbeddingProvider:
    def test_embed_query_delegates_to_runtime(self) -> None:
        runtime = MagicMock()
        runtime.embed_query.return_value = (0.1, 0.2, 0.3)
        provider = BgeM3QueryEmbeddingProvider(runtime=runtime)

        vector = provider.embed_query("hybrid search")

        runtime.embed_query.assert_called_once_with("hybrid search")
        assert vector == (0.1, 0.2, 0.3)
