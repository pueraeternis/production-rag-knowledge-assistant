"""Approval gate tests for rag demo destructive commands."""

from unittest.mock import MagicMock, patch

import pytest

from knowledge_assistant.cli import demo as demo_commands


@pytest.fixture
def mock_environment() -> MagicMock:
    environment = MagicMock()
    environment.corpus_exists.return_value = True
    environment.corpus_document_count.return_value = 2
    environment.collection_exists.return_value = True
    environment.settings.collection_name = "knowledge_chunks"
    environment.corpus_indexing_source.return_value = MagicMock()
    return environment


class TestDemoLoadApproval:
    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    def test_load_refuses_existing_collection_without_rebuild_and_approve(
        self,
        build_demo_environment: MagicMock,
        mock_environment: MagicMock,
    ) -> None:
        build_demo_environment.return_value = mock_environment

        exit_code = demo_commands.run_demo_load(rebuild=False, approved=False)

        assert exit_code == 1
        mock_environment.indexing_pipeline.index_documents.assert_not_called()

    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    def test_load_rejects_rebuild_without_approve(
        self,
        build_demo_environment: MagicMock,
        mock_environment: MagicMock,
    ) -> None:
        mock_environment.collection_exists.return_value = False
        build_demo_environment.return_value = mock_environment

        exit_code = demo_commands.run_demo_load(rebuild=True, approved=False)

        assert exit_code == 1
        mock_environment.indexing_pipeline.index_documents.assert_not_called()

    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    def test_load_allows_rebuild_when_collection_exists_and_approved(
        self,
        build_demo_environment: MagicMock,
        mock_environment: MagicMock,
    ) -> None:
        mock_environment.indexing_pipeline.index_documents.return_value = MagicMock(
            document_count=2,
            upserted_count=4,
        )
        build_demo_environment.return_value = mock_environment

        exit_code = demo_commands.run_demo_load(rebuild=True, approved=True)

        assert exit_code == 0
        mock_environment.indexing_pipeline.index_documents.assert_called_once()


class TestDemoResetApproval:
    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    def test_reset_rejects_without_approve(
        self,
        build_demo_environment: MagicMock,
    ) -> None:
        exit_code = demo_commands.run_demo_reset(approved=False)

        assert exit_code == 1
        build_demo_environment.assert_not_called()

    @patch("knowledge_assistant.cli.demo.build_demo_environment")
    def test_reset_deletes_collection_when_approved(
        self,
        build_demo_environment: MagicMock,
        mock_environment: MagicMock,
    ) -> None:
        build_demo_environment.return_value = mock_environment

        exit_code = demo_commands.run_demo_reset(approved=True)

        assert exit_code == 0
        mock_environment.vector_store.delete_collection.assert_called_once()
