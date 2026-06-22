"""Precondition tests for rag chat."""

from unittest.mock import patch

import pytest

from knowledge_assistant.bootstrap.chat import ChatSession, build_chat_session
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.cli import chat as chat_commands
from knowledge_assistant.llm.config import LlmSettings
from knowledge_assistant.llm.messages import GenerationResult
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.llm.stub_client import StubLLMClient


def _chat_session(environment: DemoEnvironment) -> ChatSession:
    return build_chat_session(
        bootstrap_settings=environment.settings,
        vector_store=environment.vector_store,
        llm_settings=LlmSettings(
            base_url="http://localhost:8000/v1",
            api_key="test",
            default_model="test-model",
        ),
        llm_client=StubLLMClient(responses=(GenerationResult(content="ok"),)),
    )


class TestChatPreconditions:
    def test_missing_collection_returns_exit_code_3(
        self,
        demo_environment: DemoEnvironment,
    ) -> None:
        session = _chat_session(demo_environment)
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            return_value=session,
        ):
            exit_code = chat_commands.run_chat(message="hello")

        assert exit_code == 3

    def test_empty_collection_returns_exit_code_3(
        self,
        demo_environment: DemoEnvironment,
    ) -> None:
        demo_environment.vector_store.create_collection()
        session = _chat_session(demo_environment)
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            return_value=session,
        ):
            exit_code = chat_commands.run_chat(message="hello")

        assert exit_code == 3

    def test_successful_single_turn_prints_answer(
        self,
        demo_environment: DemoEnvironment,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )
        llm = StreamingStubLLMClient(
            responses=(GenerationResult(content="unused"),),
            stream_deltas=("Streamed answer",),
        )
        session = build_chat_session(
            bootstrap_settings=demo_environment.settings,
            vector_store=demo_environment.vector_store,
            llm_settings=LlmSettings(
                base_url="http://localhost:8000/v1",
                api_key="test",
                default_model="test-model",
            ),
            llm_client=llm,
        )
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            return_value=session,
        ):
            exit_code = chat_commands.run_chat(message="What is policy A?")

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Chat ready" in captured.out
        assert "Streamed answer" in captured.out
