"""Integration tests for rag demo info."""

import pytest

from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main


class TestDemoInfoIntegration:
    def test_demo_info_reports_state_after_load(
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

        capsys.readouterr()
        info_exit_code = main(["demo", "info"])
        captured = capsys.readouterr()

        assert info_exit_code == 0
        assert "Corpus exists: yes" in captured.out
        assert "Corpus document count: 3" in captured.out
        assert "Collection exists: yes" in captured.out
        assert "Collection chunk count:" in captured.out
        chunk_count_line = next(
            line
            for line in captured.out.splitlines()
            if "Collection chunk count:" in line
        )
        chunk_count = int(chunk_count_line.split(":")[-1].strip())
        assert chunk_count > 0
