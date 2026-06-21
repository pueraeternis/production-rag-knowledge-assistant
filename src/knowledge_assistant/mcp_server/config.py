"""MCP handler configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class McpServerSettings:
    """Handler defaults for the knowledge MCP boundary."""

    default_top_k: int = 5

    def __post_init__(self) -> None:
        if self.default_top_k < 1:
            msg = "default_top_k must be >= 1"
            raise ValueError(msg)
