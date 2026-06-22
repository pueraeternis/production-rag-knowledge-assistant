"""Manifest schema validation for the synthetic knowledge corpus generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Literal, cast

DocumentType = Literal[
    "architecture",
    "policy",
    "runbook",
    "handbook",
    "rfc",
    "postmortem",
    "company_profile",
    "organization",
    "product_portfolio",
    "glossary",
    "finance_policy",
    "finance_process",
    "finance_operations",
]

ALLOWED_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        "architecture",
        "policy",
        "runbook",
        "handbook",
        "rfc",
        "postmortem",
        "company_profile",
        "organization",
        "product_portfolio",
        "glossary",
        "finance_policy",
        "finance_process",
        "finance_operations",
    },
)


@dataclass(frozen=True, slots=True)
class BenchmarkAlignment:
    """Benchmark metadata for retrieval dataset alignment."""

    document_key: str
    dataset: str = "retrieval_benchmark_v1"


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    """Single document entry from the corpus manifest."""

    path: str
    title: str
    type: DocumentType
    owner: str
    owner_contact: str
    related_systems: tuple[str, ...]
    related_documents: tuple[str, ...]
    required_facts: tuple[str, ...]
    status: str
    last_reviewed: str
    min_words: int
    benchmark_alignment: BenchmarkAlignment | None = None


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    """Validated corpus manifest."""

    version: int
    company: str
    output_root: str
    systems: dict[str, str]
    documents: tuple[DocumentSpec, ...]
    benchmark_paths: tuple[str, ...]


def validate_manifest(data: dict[str, Any]) -> CorpusManifest:
    """Validate untyped manifest data and return typed specs."""
    version = _required_int(data, "version")
    company = _required_str(data, "company")
    output_root = _required_str(data, "output_root")
    defaults = _optional_dict(data, "defaults")
    systems = _required_str_dict(data, "systems")
    benchmark_paths = tuple(_required_str_list(data, "benchmark_paths"))

    raw_documents = data.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ValueError("manifest must define a non-empty documents list")

    document_entries = cast("list[Any]", raw_documents)
    documents = tuple(
        _parse_document(entry, defaults, systems) for entry in document_entries
    )
    _validate_unique_paths(documents)
    _validate_benchmark_paths(documents, benchmark_paths)
    return CorpusManifest(
        version=version,
        company=company,
        output_root=output_root,
        systems=systems,
        documents=documents,
        benchmark_paths=benchmark_paths,
    )


def _parse_document(
    raw: object,
    defaults: dict[str, Any],
    systems: dict[str, str],
) -> DocumentSpec:
    if not isinstance(raw, dict):
        raise TypeError("document entries must be objects")

    document_data = cast("dict[str, Any]", raw)
    path = _required_str(document_data, "path")
    _validate_relative_markdown_path(path)

    doc_type = _required_str(document_data, "type")
    if doc_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValueError(f"{path}: unsupported document type {doc_type!r}")

    related_systems = tuple(_required_str_list(document_data, "related_systems"))
    unknown_systems = sorted(
        system for system in related_systems if system not in systems
    )
    if unknown_systems:
        raise ValueError(
            f"{path}: unknown related systems: {', '.join(unknown_systems)}",
        )

    related_documents = tuple(_required_str_list(document_data, "related_documents"))
    for related in related_documents:
        _validate_relative_markdown_path(related)

    required_facts = tuple(_required_str_list(document_data, "required_facts"))
    if len(required_facts) < 3:
        raise ValueError(f"{path}: at least three required facts are required")

    benchmark_alignment = _parse_benchmark_alignment(
        document_data.get("benchmark_alignment"),
    )
    return DocumentSpec(
        path=path,
        title=_required_str(document_data, "title"),
        type=cast("DocumentType", doc_type),
        owner=_required_str(document_data, "owner"),
        owner_contact=str(
            document_data.get(
                "owner_contact",
                defaults.get("owner_contact", "docs@acmecloud.io"),
            ),
        ),
        related_systems=related_systems,
        related_documents=related_documents,
        required_facts=required_facts,
        status=str(document_data.get("status", defaults.get("status", "Approved"))),
        last_reviewed=str(
            document_data.get(
                "last_reviewed",
                defaults.get("last_reviewed", "2026-03-01"),
            ),
        ),
        min_words=int(document_data.get("min_words", defaults.get("min_words", 700))),
        benchmark_alignment=benchmark_alignment,
    )


def _parse_benchmark_alignment(raw: object) -> BenchmarkAlignment | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError("benchmark_alignment must be an object")
    alignment_data = cast("dict[str, Any]", raw)
    return BenchmarkAlignment(
        document_key=_required_str(alignment_data, "document_key"),
        dataset=str(alignment_data.get("dataset", "retrieval_benchmark_v1")),
    )


def _validate_unique_paths(documents: tuple[DocumentSpec, ...]) -> None:
    seen: set[str] = set()
    for document in documents:
        if document.path in seen:
            raise ValueError(f"duplicate document path: {document.path}")
        seen.add(document.path)


def _validate_benchmark_paths(
    documents: tuple[DocumentSpec, ...],
    benchmark_paths: tuple[str, ...],
) -> None:
    document_paths = {document.path for document in documents}
    missing = sorted(path for path in benchmark_paths if path not in document_paths)
    if missing:
        raise ValueError(f"benchmark paths missing from manifest: {', '.join(missing)}")


def _validate_relative_markdown_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError(f"path must be repository-relative without '..': {path}")
    if parsed.suffix != ".md":
        raise ValueError(f"path must end with .md: {path}")


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"required string field missing: {key}")
    return value


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise TypeError(f"required integer field missing: {key}")
    return value


def _required_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list):
        raise TypeError(f"required string list field missing: {key}")
    items = cast("list[Any]", value)
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"required string list field missing: {key}")
    return items


def _required_str_dict(data: dict[str, Any], key: str) -> dict[str, str]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"required string dictionary field missing: {key}")
    str_dict = cast("dict[Any, Any]", value)
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in str_dict.items()):
        raise ValueError(f"required string dictionary field missing: {key}")
    return dict(str_dict)


def _optional_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"optional field must be an object when present: {key}")
    return cast("dict[str, Any]", value)
