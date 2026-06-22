"""Stable output formatting tests for rag demo info."""

from io import StringIO
from unittest.mock import MagicMock, patch

from knowledge_assistant.cli import demo as demo_commands


class TestDemoInfoFormat:
    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    @patch("sys.stdout", new_callable=StringIO)
    def test_demo_info_prints_required_fields(
        self,
        stdout: StringIO,
        build_demo_environment: MagicMock,
    ) -> None:
        environment = MagicMock()
        environment.corpus_exists.return_value = True
        environment.corpus_document_count.return_value = 3
        environment.collection_exists.return_value = True
        environment.collection_chunk_count.return_value = 12
        environment.pipeline_label = (
            "dense + sparse → fusion (RRF) → rerank (stub embeddings)"
        )
        environment.settings.qdrant_url = "http://localhost:6333"
        environment.settings.collection_name = "knowledge_chunks"
        environment.settings.corpus_root.resolve.return_value = "/tmp/knowledge"
        build_demo_environment.return_value = environment

        exit_code = demo_commands.run_demo_info()

        output = stdout.getvalue()
        assert exit_code == 0
        assert "Corpus exists: yes" in output
        assert "Corpus document count: 3" in output
        assert "Collection exists: yes" in output
        assert "Collection chunk count: 12" in output
        assert f"Retrieval pipeline: {environment.pipeline_label}" in output
        assert "Qdrant URL: http://localhost:6333" in output
        assert "Collection name: knowledge_chunks" in output
        assert "Corpus path: /tmp/knowledge" in output
