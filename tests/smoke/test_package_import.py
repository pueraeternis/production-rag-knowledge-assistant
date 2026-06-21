"""Smoke tests for package importability."""

import knowledge_assistant


def test_package_importable() -> None:
    """Verify the root package imports successfully."""
    assert knowledge_assistant.__version__


def test_version_is_non_empty_string() -> None:
    """Verify __version__ is a non-empty string."""
    assert isinstance(knowledge_assistant.__version__, str)
    assert knowledge_assistant.__version__
