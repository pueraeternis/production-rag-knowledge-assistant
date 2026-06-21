"""Agent configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentSettings:
    """Runtime settings for LangGraph agent orchestration."""

    max_tool_iterations: int = 5

    def __post_init__(self) -> None:
        if self.max_tool_iterations < 1:
            msg = "max_tool_iterations must be >= 1"
            raise ValueError(msg)
