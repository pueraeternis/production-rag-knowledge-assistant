"""Pydantic request and response models for MCP knowledge handlers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LineRangeSchema(BaseModel):
    """Inclusive 1-based line span within a source document."""

    model_config = ConfigDict(frozen=True)

    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class SourceReferenceSchema(BaseModel):
    """Citation metadata for a retrieved chunk."""

    model_config = ConfigDict(frozen=True)

    document_title: str = Field(min_length=1)
    document_path: str = Field(min_length=1)
    section_title: str
    line_range: LineRangeSchema


class SearchHitSchema(BaseModel):
    """One ranked retrieval hit with source attribution."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    score: float
    source: SourceReferenceSchema


class SearchDocumentsRequest(BaseModel):
    """Input for ranked chunk retrieval."""

    model_config = ConfigDict(frozen=True)

    query: str
    top_k: int | None = Field(default=None, ge=1)

    @field_validator("query")
    @classmethod
    def query_must_be_non_empty_after_strip(cls, value: str) -> str:
        if not value.strip():
            msg = "query must be non-empty"
            raise ValueError(msg)
        return value


class SearchDocumentsResponse(BaseModel):
    """Ranked retrieval evidence for grounding; does not include generated answers."""

    model_config = ConfigDict(frozen=True)

    query: str
    top_k: int
    hits: tuple[SearchHitSchema, ...]


class IndexingSourceSchema(BaseModel):
    """Local file or directory source for indexing."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["file", "directory"]
    location: str
    recursive: bool = False

    @field_validator("location")
    @classmethod
    def location_must_be_non_empty_after_strip(cls, value: str) -> str:
        if not value.strip():
            msg = "location must be non-empty"
            raise ValueError(msg)
        return value


class IndexDocumentsPreviewRequest(BaseModel):
    """Input for indexing impact preview."""

    model_config = ConfigDict(frozen=True)

    sources: tuple[IndexingSourceSchema, ...] = Field(min_length=1)


class IndexDocumentsPreviewResponse(BaseModel):
    """Estimated indexing impact without storage mutation."""

    model_config = ConfigDict(frozen=True)

    sources: tuple[IndexingSourceSchema, ...]
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    replaces_existing: bool


class IndexDocumentsApplyRequest(BaseModel):
    """Input for approved indexing mutation."""

    model_config = ConfigDict(frozen=True)

    sources: tuple[IndexingSourceSchema, ...] = Field(min_length=1)
    rebuild: bool = False
    approval_confirmed: bool


class IndexDocumentsApplyResponse(BaseModel):
    """Summary of a completed indexing run."""

    model_config = ConfigDict(frozen=True)

    sources: tuple[IndexingSourceSchema, ...]
    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    upserted_count: int = Field(ge=0)
    rebuilt: bool
