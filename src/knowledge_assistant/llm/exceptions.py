"""LLM boundary exception types."""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for LLM boundary failures."""


class LLMTimeoutError(LLMError):
    """Raised when an HTTP request exceeds the configured timeout."""


class LLMAuthenticationError(LLMError):
    """Raised when the provider returns HTTP 401 or 403."""


class LLMResponseError(LLMError):
    """Raised when the provider response is malformed or incomplete."""


class LLMTransportError(LLMError):
    """Raised for connection failures and non-authentication HTTP errors."""
