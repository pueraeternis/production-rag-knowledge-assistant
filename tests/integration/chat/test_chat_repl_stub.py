"""Integration tests for interactive rag chat REPL."""

import pytest

from knowledge_assistant.bootstrap.chat import ChatSession
from knowledge_assistant.cli import chat as chat_commands


class TestChatReplStub:
    def test_repl_exits_on_quit(
        self,
        streaming_chat_session: ChatSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        inputs = iter(["quit"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

        exit_code = chat_commands.run_chat(
            session=streaming_chat_session,
        )
        assert exit_code == 0

    def test_repl_ignores_empty_lines(
        self,
        streaming_chat_session: ChatSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        inputs = iter(["", "exit"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]

        exit_code = chat_commands.run_chat(
            session=streaming_chat_session,
        )
        assert exit_code == 0
