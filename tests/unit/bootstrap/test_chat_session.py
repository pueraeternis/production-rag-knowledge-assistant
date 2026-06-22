"""Unit tests for bootstrap chat session assembly."""

from knowledge_assistant.agent.config import AgentSettings
from knowledge_assistant.agent.prompts import SYSTEM_PROMPT
from knowledge_assistant.agent.state import AgentState
from knowledge_assistant.bootstrap.chat import (
    build_chat_session,
    execute_turn,
    execute_turn_streaming,
    initial_agent_state,
)
from knowledge_assistant.bootstrap.environment import DemoEnvironment
from knowledge_assistant.llm.config import LlmSettings
from knowledge_assistant.llm.messages import ChatRole, GenerationResult
from knowledge_assistant.llm.streaming_stub_client import StreamingStubLLMClient
from knowledge_assistant.llm.stub_client import StubLLMClient


def test_initial_agent_state_seeds_system_prompt() -> None:
    state = initial_agent_state()
    assert isinstance(state, AgentState)
    assert state.messages[0].role is ChatRole.SYSTEM
    assert state.messages[0].content == SYSTEM_PROMPT


def test_build_chat_session_wires_environment_llm_and_registry(
    demo_environment: DemoEnvironment,
) -> None:
    llm = StubLLMClient(responses=(GenerationResult(content="ok"),))
    session = build_chat_session(
        bootstrap_settings=demo_environment.settings,
        vector_store=demo_environment.vector_store,
        llm_settings=LlmSettings(
            base_url="http://localhost:8000/v1",
            api_key="test",
            default_model="test-model",
        ),
        llm_client=llm,
        agent_settings=AgentSettings(max_tool_iterations=3),
    )

    assert session.environment.settings == demo_environment.settings
    assert session.environment.vector_store is demo_environment.vector_store
    assert session.llm_client is llm
    assert session.agent_settings.max_tool_iterations == 3
    assert any(
        definition.name == "search_documents"
        for definition in session.tool_registry.definitions()
    )


def test_execute_turn_returns_turn_result_without_callbacks(
    demo_environment: DemoEnvironment,
) -> None:
    llm = StubLLMClient(responses=(GenerationResult(content="Answer text"),))
    session = build_chat_session(
        bootstrap_settings=demo_environment.settings,
        vector_store=demo_environment.vector_store,
        llm_client=llm,
    )
    turn_result = execute_turn(session, initial_agent_state(), "hello")
    assert turn_result.answer == "Answer text"
    assert turn_result.state.final_response == "Answer text"


def test_execute_turn_streaming_returns_iterator(
    demo_environment: DemoEnvironment,
) -> None:
    llm = StreamingStubLLMClient(
        responses=(GenerationResult(content="unused"),),
        stream_deltas=("streamed",),
    )
    session = build_chat_session(
        bootstrap_settings=demo_environment.settings,
        vector_store=demo_environment.vector_store,
        llm_client=llm,
    )
    turn_stream = execute_turn_streaming(session, initial_agent_state(), "hello")
    assert [chunk.content_delta for chunk in turn_stream] == ["streamed"]
    assert turn_stream.result().answer == "streamed"
