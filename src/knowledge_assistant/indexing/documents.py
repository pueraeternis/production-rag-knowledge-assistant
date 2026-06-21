"""Local file discovery for indexing sources."""

from pathlib import Path

from knowledge_assistant.core.indexing import IndexingSource, IndexingSourceKind
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.exceptions import (
    SourceNotFoundError,
    UnsupportedFileTypeError,
    UnsupportedSourceKindError,
)
from knowledge_assistant.indexing.ids import normalize_source_path


def discover_files(
    source: IndexingSource,
    *,
    settings: IndexingSettings,
) -> tuple[str, ...]:
    """Return normalized absolute paths of supported files for one source."""
    if source.kind in (
        IndexingSourceKind.DOCUMENT_URL,
        IndexingSourceKind.DIRECTORY_URL,
    ):
        msg = f"unsupported indexing source kind: {source.kind.value}"
        raise UnsupportedSourceKindError(msg)

    if source.kind == IndexingSourceKind.FILE:
        return _discover_single_file(source.location, settings=settings)

    return _discover_directory(
        source.location,
        recursive=source.recursive,
        settings=settings,
    )


def _discover_single_file(
    location: str,
    *,
    settings: IndexingSettings,
) -> tuple[str, ...]:
    path = Path(location)
    if not path.exists():
        msg = f"source path not found: {location}"
        raise SourceNotFoundError(msg)
    if not _is_supported_extension(path, settings=settings):
        msg = f"unsupported file type: {path.suffix}"
        raise UnsupportedFileTypeError(msg)
    return (normalize_source_path(str(path)),)


def _discover_directory(
    location: str,
    *,
    recursive: bool,
    settings: IndexingSettings,
) -> tuple[str, ...]:
    path = Path(location)
    if not path.exists():
        msg = f"source path not found: {location}"
        raise SourceNotFoundError(msg)
    if not path.is_dir():
        msg = f"source path is not a directory: {location}"
        raise SourceNotFoundError(msg)

    candidates = path.rglob("*") if recursive else path.glob("*")

    discovered = [
        normalize_source_path(str(candidate))
        for candidate in candidates
        if candidate.is_file() and _is_supported_extension(candidate, settings=settings)
    ]
    return tuple(sorted(discovered))


def _is_supported_extension(path: Path, *, settings: IndexingSettings) -> bool:
    suffix = path.suffix.lower()
    supported = tuple(extension.lower() for extension in settings.supported_extensions)
    return suffix in supported
