"""Parser and command dispatch tests for rag chat."""

from unittest.mock import patch

from knowledge_assistant.cli.main import main


def test_main_chat_single_turn_dispatches_message_flag() -> None:
    with patch("knowledge_assistant.cli.chat.run_chat", return_value=0) as run_chat:
        exit_code = main(["chat", "--message", "hello"])

    assert exit_code == 0
    run_chat.assert_called_once_with(
        message="hello",
        stream=True,
        show_sources=True,
    )


def test_main_chat_no_stream_and_no_sources_flags() -> None:
    with patch("knowledge_assistant.cli.chat.run_chat", return_value=0) as run_chat:
        exit_code = main(["chat", "--no-stream", "--no-sources"])

    assert exit_code == 0
    run_chat.assert_called_once_with(
        message=None,
        stream=False,
        show_sources=False,
    )
