"""Precondition tests for rag chat."""

import os
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
        assert "LLM model: test-model" in captured.out
        assert "http://localhost:8000" not in captured.out
        assert "Streamed answer" in captured.out

    def test_run_chat_suppresses_third_party_advisory_output(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("TRANSFORMERS_NO_ADVISORY_WARNINGS", raising=False)
        monkeypatch.delenv("HF_HUB_DISABLE_PROGRESS_BARS", raising=False)
        with patch(
            "knowledge_assistant.cli.chat.build_chat_session",
            side_effect=RuntimeError("stop early"),
        ):
            exit_code = chat_commands.run_chat(message="hello")

        assert exit_code == 1
        assert os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] == "1"
        assert os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] == "1"

    def test_repl_prompt_starts_on_new_line_after_streaming_answer(
        self,
        demo_environment: DemoEnvironment,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from knowledge_assistant.llm.config import LlmSettings
        from knowledge_assistant.llm.messages import GenerationResult
        from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient

        demo_environment.indexing_pipeline.index_documents(
            (demo_environment.corpus_indexing_source(),),
            rebuild=False,
        )
        session = build_chat_session(
            bootstrap_settings=demo_environment.settings,
            vector_store=demo_environment.vector_store,
            llm_settings=LlmSettings(
                base_url="http://localhost:8000/v1",
                api_key="test",
                default_model="test-model",
            ),
            llm_client=StreamingStubLLMClient(
                responses=(
                    GenerationResult(content=None, tool_calls=()),
                    GenerationResult(content=None, tool_calls=()),
                ),
                stream_deltas=("Hello Vitaliy!",),
            ),
        )
        inputs = iter(["My name is Vitaliy", "exit"])
        with patch(
            "builtins.input",
            lambda _prompt: next(inputs),  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
        ):
            exit_code = chat_commands.run_chat(session=session)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Hello Vitaliy!\n" in captured.out
        assert "Hello Vitaliy!You:" not in captured.out
