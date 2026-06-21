"""Agent-layer exception types."""


class AgentError(Exception):
    """Base error for agent orchestration failures."""


class UnknownToolError(AgentError):
    """Raised when dispatching a tool call with an unregistered name."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"unknown tool: {tool_name}")


class DuplicateToolError(AgentError):
    """Raised when registering a tool whose name is already present."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"duplicate tool registration: {tool_name}")


class MaxToolIterationsError(AgentError):
    """Raised when the tool-call iteration guard is exceeded."""

    def __init__(self, max_iterations: int) -> None:
        self.max_iterations = max_iterations
        super().__init__(
            f"maximum tool iterations ({max_iterations}) reached without completion",
        )
