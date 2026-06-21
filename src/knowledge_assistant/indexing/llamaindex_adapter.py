"""LlamaIndex adapter for loading and chunking local documents."""

import re
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

from knowledge_assistant.core.chunk import Chunk, ChunkMetadata
from knowledge_assistant.core.document import DocumentMetadata
from knowledge_assistant.core.identifiers import DocumentId
from knowledge_assistant.core.source import LineRange
from knowledge_assistant.indexing.config import IndexingSettings
from knowledge_assistant.indexing.exceptions import ChunkingError, DocumentLoadError
from knowledge_assistant.indexing.ids import chunk_id_for_chunk, normalize_source_path

_ATX_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
_SINGLE_H1_PATTERN = re.compile(r"^#\s+(.+)$")
_FALLBACK_LINE_RANGE = LineRange(start_line=1, end_line=1)


def _character_tokenizer(text: str) -> list[str]:
    return list(text)


def _read_raw_source_mirror(path: Path) -> str:
    """Read the on-disk file for title and line attribution only."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"failed to read raw source mirror: {path}"
        raise DocumentLoadError(msg) from exc


def _load_text_with_llamaindex(path: Path) -> str:
    """Load document text via LlamaIndex for chunking."""
    try:
        documents = SimpleDirectoryReader(input_files=[str(path)]).load_data()
    except Exception as exc:
        msg = f"failed to load document with LlamaIndex reader: {path}"
        raise DocumentLoadError(msg) from exc

    if not documents:
        msg = f"LlamaIndex reader returned no documents: {path}"
        raise DocumentLoadError(msg)
    if len(documents) > 1:
        msg = f"LlamaIndex reader returned multiple documents: {path}"
        raise DocumentLoadError(msg)

    return documents[0].text


def load_and_chunk_file(
    *,
    file_path: str,
    document_id: DocumentId,
    settings: IndexingSettings,
) -> tuple[DocumentMetadata, tuple[Chunk, ...]]:
    """Load one local file, chunk it, and return metadata and domain chunks.

    LlamaIndex ``SimpleDirectoryReader`` and ``SentenceSplitter`` own loading
    and chunking. A separate raw file read mirrors on-disk text for title
    extraction and ``LineRange`` attribution only.
    """
    path = Path(file_path)
    # Raw mirror preserves on-disk text for attribution; LlamaIndex owns ingest.
    raw_source_text = _read_raw_source_mirror(path)
    loaded_document_text = _load_text_with_llamaindex(path)

    normalized_path = normalize_source_path(str(path))
    metadata = DocumentMetadata(
        title=_extract_document_title(raw_source_text, normalized_path),
        path=normalized_path,
        source_uri=None,
    )

    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        tokenizer=_character_tokenizer,
    )
    try:
        chunk_texts = splitter.split_text(loaded_document_text)
    except Exception as exc:
        msg = f"failed to chunk document: {file_path}"
        raise ChunkingError(msg) from exc

    if not chunk_texts:
        msg = f"document produced no chunks: {file_path}"
        raise ChunkingError(msg)

    line_offsets = _build_line_start_offsets(raw_source_text)
    search_from = 0
    previous_end_char: int | None = None
    chunks: list[Chunk] = []
    for chunk_index, chunk_text in enumerate(chunk_texts):
        stripped_text = chunk_text.strip()
        if not stripped_text:
            continue

        start_char, end_char = _locate_chunk_offsets(
            raw_source_text,
            chunk_text,
            search_from=search_from,
            chunk_overlap=settings.chunk_overlap,
            previous_end_char=previous_end_char,
        )
        previous_end_char = end_char
        search_from = max(start_char + 1, end_char - settings.chunk_overlap)
        line_range = _char_offsets_to_line_range(
            line_offsets,
            start_char=start_char,
            end_char=end_char,
        )
        section_title = _section_title_at_offset(
            raw_source_text,
            start_char=start_char,
            file_suffix=path.suffix.lower(),
        )
        chunk_id = chunk_id_for_chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            text=stripped_text,
        )
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                metadata=ChunkMetadata(
                    document_id=document_id,
                    section_title=section_title,
                    line_range=line_range,
                    chunk_index=chunk_index,
                ),
                text=stripped_text,
            ),
        )

    if not chunks:
        msg = f"document produced no non-empty chunks: {file_path}"
        raise ChunkingError(msg)

    return metadata, tuple(chunks)


def _extract_document_title(raw_source_text: str, file_path: str) -> str:
    lines = raw_source_text.splitlines()
    if lines:
        first_line = lines[0].strip()
        match = _SINGLE_H1_PATTERN.match(first_line)
        if match is not None and not first_line.startswith("##"):
            return match.group(1).strip()
    return Path(file_path).stem


def _build_line_start_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, character in enumerate(text):
        if character == "\n":
            offsets.append(index + 1)
    return offsets


def _search_start_candidates(
    *,
    search_from: int,
    chunk_overlap: int,
    previous_end_char: int | None,
) -> tuple[int, ...]:
    candidates = [search_from]
    if previous_end_char is not None and chunk_overlap > 0:
        overlap_start = max(0, previous_end_char - chunk_overlap)
        if overlap_start < search_from:
            candidates.insert(0, overlap_start)
    return tuple(candidates)


def _locate_chunk_offsets(
    raw_source_text: str,
    chunk_text: str,
    *,
    search_from: int,
    chunk_overlap: int,
    previous_end_char: int | None,
) -> tuple[int, int]:
    stripped = chunk_text.strip()
    for start in _search_start_candidates(
        search_from=search_from,
        chunk_overlap=chunk_overlap,
        previous_end_char=previous_end_char,
    ):
        position = raw_source_text.find(stripped, start)
        if position >= 0:
            return position, position + len(stripped)

        position = raw_source_text.find(chunk_text, start)
        if position >= 0:
            return position, position + len(chunk_text)

    return 0, min(len(stripped), len(raw_source_text))


def _char_offsets_to_line_range(
    line_offsets: list[int],
    *,
    start_char: int,
    end_char: int,
) -> LineRange:
    if not original_text_length_valid(start_char, end_char, line_offsets):
        return _FALLBACK_LINE_RANGE

    start_line = _line_number_for_offset(line_offsets, start_char)
    end_offset = max(start_char, end_char - 1)
    end_line = _line_number_for_offset(line_offsets, end_offset)
    return LineRange(start_line=start_line, end_line=end_line)


def original_text_length_valid(
    start_char: int,
    end_char: int,
    line_offsets: list[int],
) -> bool:
    if end_char <= start_char or start_char < 0:
        return False
    return bool(line_offsets)


def _line_number_for_offset(line_offsets: list[int], offset: int) -> int:
    line_number = 1
    for index, _line_start in enumerate(line_offsets):
        next_start = line_offsets[index + 1] if index + 1 < len(line_offsets) else None
        if next_start is None or offset < next_start:
            return line_number
        line_number += 1
    return line_number


def _section_title_at_offset(
    raw_source_text: str,
    *,
    start_char: int,
    file_suffix: str,
) -> str:
    if file_suffix != ".md":
        return ""

    section_title = ""
    position = 0
    for line in raw_source_text.splitlines(keepends=True):
        line_start = position
        if line_start > start_char:
            break
        stripped = line.strip()
        match = _ATX_HEADING_PATTERN.match(stripped)
        if match is not None:
            section_title = match.group(2).strip()
        position += len(line)
    return section_title
