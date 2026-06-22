"""Unit tests for BGE-M3 indexing embedding adapter."""

from unittest.mock import MagicMock

from knowledge_assistant.indexing.embeddings import BgeM3EmbeddingProvider


class TestBgeM3EmbeddingProvider:
    def test_embed_texts_delegates_to_runtime(self) -> None:
        runtime = MagicMock()
        runtime.embed_passages.return_value = ((1.0, 2.0), (3.0, 4.0))
        provider = BgeM3EmbeddingProvider(runtime=runtime)

        vectors = provider.embed_texts(("first", "second"))

        runtime.embed_passages.assert_called_once_with(("first", "second"))
        assert vectors == ((1.0, 2.0), (3.0, 4.0))

    def test_empty_input_delegates_to_runtime(self) -> None:
        runtime = MagicMock()
        runtime.embed_passages.return_value = ()
        provider = BgeM3EmbeddingProvider(runtime=runtime)

        assert provider.embed_texts(()) == ()
        runtime.embed_passages.assert_called_once_with(())
