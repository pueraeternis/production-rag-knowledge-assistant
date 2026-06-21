"""MCP handler exception types and stable error codes."""

APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class ApprovalRequiredError(Exception):
    """Raised when index mutation is requested without explicit approval."""

    error_code: str = APPROVAL_REQUIRED

    def __init__(
        self,
        message: str = "approval_confirmed must be True",
    ) -> None:
        super().__init__(message)
        self.message = message
