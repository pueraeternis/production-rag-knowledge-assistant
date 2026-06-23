"""Interactive chat command orchestration for the rag CLI."""

from __future__ import annotations

import os
import signal
import sys

from knowledge_assistant.bootstrap import (
    ChatSession,
    StreamChunk,
    TurnResult,
    TurnSource,
    TurnStream,
    build_chat_session,
    execute_turn,
    execute_turn_streaming,
    initial_agent_state,
)

_PROMPT = "You: "
_INTERRUPT_MESSAGE = "[generation interrupted]"


def _configure_quiet_chat_output() -> None:
    """Suppress third-party advisory logs that are not part of chat output."""
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def _finish_assistant_output() -> None:
    """Leave stdout on its own line before sources or the next REPL prompt."""
    print(flush=True)


class _StreamInterruptedError(Exception):
    """Raised when stream consumption is cancelled by SIGINT."""


def format_turn_sources(sources: tuple[TurnSource, ...]) -> str:
    """Render structured turn sources for terminal display."""
    if not sources:
        return ""

    lines = ["", "Sources:", ""]
    for index, source in enumerate(sources, start=1):
        lines.extend(
            (
                f"[{index}] {source.document_title}",
                f"    File: {source.document_path}",
                f"    Section: {source.section_title}",
                f"    Lines: {source.start_line}-{source.end_line}",
            ),
        )
    return "\n".join(lines)


def validate_chat_preconditions(session: ChatSession) -> int | None:
    """Validate corpus, index, and LLM configuration. Return exit code 3 on failure."""
    environment = session.environment
    if not environment.corpus_exists():
        corpus_path = environment.settings.corpus_root.resolve()
        print(
            f"error: corpus directory not found: {corpus_path}",
            file=sys.stderr,
        )
        print(
            "generate the corpus first: python3 tools/knowledge_generator/generator.py",
            file=sys.stderr,
        )
        return 3

    if environment.corpus_document_count() == 0:
        corpus_path = environment.settings.corpus_root.resolve()
        print(
            "error: corpus directory is empty or has no indexable documents: "
            f"{corpus_path}",
            file=sys.stderr,
        )
        return 3

    if not environment.collection_exists():
        print(
            "error: collection does not exist; run `rag demo load` first",
            file=sys.stderr,
        )
        return 3

    if environment.collection_chunk_count() == 0:
        print(
            "error: collection is empty; run `rag demo load` first",
            file=sys.stderr,
        )
        return 3

    return None


def print_chat_banner(
    session: ChatSession,
    *,
    streaming_enabled: bool,
) -> None:
    """Print configuration diagnostics without contacting the LLM."""
    environment = session.environment
    embedding_mode = environment.settings.embedding_mode
    reranker_mode = environment.settings.reranker_mode
    corpus_path = environment.settings.corpus_root.resolve()

    print("Chat ready")
    print(
        f"  Corpus: {corpus_path}/ ({environment.corpus_document_count()} documents)",
    )
    print(
        "  Collection: "
        f"{environment.settings.collection_name} "
        f"({environment.collection_chunk_count()} chunks)",
    )
    print(f"  Pipeline: {environment.pipeline_label}")
    print(f"  Embedding mode: {embedding_mode} | Reranker mode: {reranker_mode}")
    print(f"  LLM model: {session.llm_settings.default_model}")
    streaming_label = "enabled (default)" if streaming_enabled else "disabled"
    print(f"  Streaming: {streaming_label}")

    if embedding_mode == "stub" or reranker_mode == "stub":
        print(
            "  Note: stub provider mode — retrieval quality is non-authoritative; "
            "enable real embeddings/reranker for meaningful answers.",
        )
    print()


def render_turn_stream(turn_stream: TurnStream) -> TurnResult:
    """Consume a turn stream, writing deltas to stdout."""
    interrupted = False
    previous_handler = signal.getsignal(signal.SIGINT)

    def _handle_sigint(_signum: int, _frame: object) -> None:
        nonlocal interrupted
        interrupted = True
        raise _StreamInterruptedError

    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        chunk: StreamChunk
        for chunk in turn_stream:
            if interrupted:
                break
            sys.stdout.write(chunk.content_delta)
            sys.stdout.flush()
        if interrupted:
            print(file=sys.stderr)
            print(_INTERRUPT_MESSAGE, file=sys.stderr)
            raise _StreamInterruptedError
        _finish_assistant_output()
        return turn_stream.result()
    except _StreamInterruptedError:
        raise
    except Exception:
        print(file=sys.stderr)
        raise
    finally:
        signal.signal(signal.SIGINT, previous_handler)


def run_single_turn(
    session: ChatSession,
    *,
    message: str,
    stream: bool,
    show_sources: bool,
) -> int:
    """Execute one turn and exit."""
    state = initial_agent_state()
    turn_result: TurnResult
    try:
        if stream:
            turn_stream = execute_turn_streaming(session, state, message)
            turn_result = render_turn_stream(turn_stream)
        else:
            turn_result = execute_turn(session, state, message)
            sys.stdout.write(turn_result.answer)
            sys.stdout.flush()
            _finish_assistant_output()
    except _StreamInterruptedError:
        return 1
    except Exception as exc:
        print(f"error: turn failed: {exc}", file=sys.stderr)
        return 1

    if show_sources:
        sources_block = format_turn_sources(turn_result.sources)
        if sources_block:
            print(sources_block)
    return 0


def run_chat_repl(
    session: ChatSession,
    *,
    stream: bool,
    show_sources: bool,
) -> int:
    """Run the interactive REPL until exit, quit, or EOF."""
    state = initial_agent_state()
    while True:
        try:
            user_input = input(_PROMPT)
        except EOFError:
            print()
            return 0

        message = user_input.strip()
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            return 0

        state_before_turn = state
        try:
            if stream:
                turn_stream = execute_turn_streaming(session, state, message)
                turn_result = render_turn_stream(turn_stream)
            else:
                turn_result = execute_turn(session, state, message)
                sys.stdout.write(turn_result.answer)
                sys.stdout.flush()
                _finish_assistant_output()
        except _StreamInterruptedError:
            state = state_before_turn
            continue
        except Exception as exc:
            state = state_before_turn
            print(f"error: turn failed: {exc}", file=sys.stderr)
            continue

        state = turn_result.state
        if show_sources:
            sources_block = format_turn_sources(turn_result.sources)
            if sources_block:
                print(sources_block)

    return 0


def run_chat(
    *,
    message: str | None = None,
    stream: bool = True,
    show_sources: bool = True,
    session: ChatSession | None = None,
) -> int:
    """Build session, validate preconditions, and run REPL or single-turn chat."""
    _configure_quiet_chat_output()
    try:
        resolved_session = session or build_chat_session()
    except Exception as exc:
        print(f"error: failed to assemble chat session: {exc}", file=sys.stderr)
        return 1

    precondition_exit = validate_chat_preconditions(resolved_session)
    if precondition_exit is not None:
        return precondition_exit

    print_chat_banner(resolved_session, streaming_enabled=stream)

    if message is not None:
        return run_single_turn(
            resolved_session,
            message=message,
            stream=stream,
            show_sources=show_sources,
        )

    return run_chat_repl(
        resolved_session,
        stream=stream,
        show_sources=show_sources,
    )
