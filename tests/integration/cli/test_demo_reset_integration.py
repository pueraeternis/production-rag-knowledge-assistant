"""Integration tests for rag demo reset."""

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main


class TestDemoResetIntegration:
    def test_demo_reset_deletes_collection_when_approved(
        self,
        demo_environment: DemoEnvironment,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            "knowledge_assistant.cli.demo.build_demo_environment",
            lambda: demo_environment,
        )

        load_exit_code = main(["demo", "load"])
        assert load_exit_code == 0
        assert demo_environment.collection_chunk_count() > 0

        reset_exit_code = main(["demo", "reset", "--approve"])
        captured = capsys.readouterr()

        assert reset_exit_code == 0
        assert not demo_environment.collection_exists()
        assert demo_environment.collection_chunk_count() == 0
        assert demo_environment.settings.collection_name in captured.out
