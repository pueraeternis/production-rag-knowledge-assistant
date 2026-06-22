"""Integration tests for single-turn rag chat."""

from unittest.mock import patch

import pytest

from knowledge_assistant.bootstrap.chat import ChatSession
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli.main import main


class TestChatSingleTurn:
    def test_main_chat_message_runs_single_turn(
        self,
        streaming_chat_session: ChatSession,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            return_value=streaming_chat_session,
        ):
            exit_code = main(["chat", "--message", "What is remote work policy?"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Chat ready" in captured.out
        assert "Hello from chat" in captured.out

    def test_no_stream_prints_full_answer_at_once(
        self,
        indexed_environment: DemoEnvironment,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from knowledge_assistant.bootstrap import build_chat_session
        from knowledge_assistant.llm.config import LlmSettings
        from knowledge_assistant.llm.messages import GenerationResult
        from knowledge_assistant.llm.stub_client import StubLLMClient

        session = build_chat_session(
            bootstrap_settings=indexed_environment.settings,
            vector_store=indexed_environment.vector_store,
            llm_settings=LlmSettings(
                base_url="http://localhost:8000/v1",
                api_key="test",
                default_model="test-model",
            ),
            llm_client=StubLLMClient(
                responses=(
                    GenerationResult(content=None, tool_calls=()),
                    GenerationResult(content="Non-streaming answer"),
                ),
            ),
        )
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            return_value=session,
        ):
            exit_code = main(
                ["chat", "--no-stream", "--message", "hello"],
            )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Non-streaming answer" in captured.out
