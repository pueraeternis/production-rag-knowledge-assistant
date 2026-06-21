"""Evaluation benchmark dataset models and JSON loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from knowledge_assistant.evaluation.exceptions import EvaluationDatasetError
from knowledge_assistant.evaluation.metrics import normalize_document_path


@dataclass(frozen=True, slots=True)
class DocumentRegistry:
    """Maps benchmark-local document keys to canonical corpus paths."""

    entries: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.entries:
            msg = "documents registry must be non-empty"
            raise ValueError(msg)
        seen_keys: set[str] = set()
        for key, path in self.entries:
            if not key.strip():
                msg = "document key must be non-empty"
                raise ValueError(msg)
            if not path.strip():
                msg = "document path must be non-empty"
                raise ValueError(msg)
            if key in seen_keys:
                msg = f"duplicate document key: {key}"
                raise ValueError(msg)
            seen_keys.add(key)

    def path_for_key(self, document_key: str) -> str:
        """Resolve a registry key to its normalized document path."""
        for key, path in self.entries:
            if key == document_key:
                return normalize_document_path(path)
        msg = f"unknown document key: {document_key}"
        raise KeyError(msg)

    @classmethod
    def from_mapping(cls, documents: dict[str, dict[str, Any]]) -> DocumentRegistry:
        """Build a registry from parsed JSON document entries."""
        entries = tuple(
            (key, normalize_document_path(entry["path"]))
            for key, entry in sorted(documents.items())
        )
        return cls(entries=entries)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One benchmark question with a single relevant document label."""

    case_id: str
    question: str
    expected_document_key: str

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            msg = "case_id must be non-empty"
            raise ValueError(msg)
        if not self.question.strip():
            msg = "question must be non-empty"
            raise ValueError(msg)
        if not self.expected_document_key.strip():
            msg = "expected_document_key must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class EvaluationDataset:
    """Committed retrieval benchmark with document registry and cases."""

    dataset_id: str
    description: str | None
    corpus_version: str | None
    documents: DocumentRegistry
    cases: tuple[EvaluationCase, ...]

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            msg = "dataset_id must be non-empty"
            raise ValueError(msg)
        if not self.cases:
            msg = "cases must be non-empty"
            raise ValueError(msg)
        seen_case_ids: set[str] = set()
        for case in self.cases:
            if case.case_id in seen_case_ids:
                msg = f"duplicate case_id: {case.case_id}"
                raise ValueError(msg)
            seen_case_ids.add(case.case_id)
            try:
                self.documents.path_for_key(case.expected_document_key)
            except KeyError as exc:
                msg = (
                    f"case {case.case_id} references unknown document key "
                    f"{case.expected_document_key!r}"
                )
                raise ValueError(msg) from exc


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    """Load and validate an evaluation dataset from a JSON file."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"failed to read evaluation dataset: {path}"
        raise EvaluationDatasetError(msg) from exc

    try:
        payload_obj = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON in evaluation dataset: {path}"
        raise EvaluationDatasetError(msg) from exc

    if not isinstance(payload_obj, dict):
        msg = "evaluation dataset root must be a JSON object"
        raise EvaluationDatasetError(msg)

    payload = cast("dict[str, Any]", payload_obj)

    dataset_id = payload.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        msg = "dataset_id must be a non-empty string"
        raise EvaluationDatasetError(msg)

    documents_raw_obj = payload.get("documents")
    if not isinstance(documents_raw_obj, dict) or not documents_raw_obj:
        msg = "documents must be a non-empty object"
        raise EvaluationDatasetError(msg)
    documents_raw = cast("dict[str, Any]", documents_raw_obj)

    for key, entry_obj in documents_raw.items():
        if not key.strip():
            msg = "document keys must be non-empty strings"
            raise EvaluationDatasetError(msg)
        if not isinstance(entry_obj, dict):
            msg = f"document entry for {key!r} must be an object"
            raise EvaluationDatasetError(msg)
        entry = cast("dict[str, Any]", entry_obj)
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            msg = f"document entry for {key!r} must include a non-empty path"
            raise EvaluationDatasetError(msg)

    cases_raw_obj = payload.get("cases")
    if not isinstance(cases_raw_obj, list) or not cases_raw_obj:
        msg = "cases must be a non-empty array"
        raise EvaluationDatasetError(msg)
    cases_raw = cast("list[Any]", cases_raw_obj)

    cases: list[EvaluationCase] = []
    for index, case_raw_obj in enumerate(cases_raw):
        if not isinstance(case_raw_obj, dict):
            msg = f"case at index {index} must be an object"
            raise EvaluationDatasetError(msg)
        case_raw = cast("dict[str, Any]", case_raw_obj)
        case_id = case_raw.get("case_id")
        question = case_raw.get("question")
        expected_document_key = case_raw.get("expected_document_key")
        if not isinstance(case_id, str) or not case_id.strip():
            msg = f"case at index {index} must include a non-empty case_id"
            raise EvaluationDatasetError(msg)
        if not isinstance(question, str) or not question.strip():
            msg = f"case {case_id} must include a non-empty question"
            raise EvaluationDatasetError(msg)
        if (
            not isinstance(expected_document_key, str)
            or not expected_document_key.strip()
        ):
            msg = f"case {case_id} must include a non-empty expected_document_key"
            raise EvaluationDatasetError(msg)
        cases.append(
            EvaluationCase(
                case_id=case_id,
                question=question,
                expected_document_key=expected_document_key,
            ),
        )

    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        msg = "description must be a string when present"
        raise EvaluationDatasetError(msg)

    corpus_version = payload.get("corpus_version")
    if corpus_version is not None and not isinstance(corpus_version, str):
        msg = "corpus_version must be a string when present"
        raise EvaluationDatasetError(msg)

    try:
        documents = DocumentRegistry.from_mapping(documents_raw)
    except ValueError as exc:
        raise EvaluationDatasetError(str(exc)) from exc

    try:
        return EvaluationDataset(
            dataset_id=dataset_id,
            description=description,
            corpus_version=corpus_version,
            documents=documents,
            cases=tuple(cases),
        )
    except ValueError as exc:
        raise EvaluationDatasetError(str(exc)) from exc
