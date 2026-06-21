"""Unit tests for evaluation dataset loading and validation."""

import json
from pathlib import Path
from typing import Any

import pytest

from knowledge_assistant.evaluation.dataset import (
    DocumentRegistry,
    EvaluationCase,
    EvaluationDataset,
    load_evaluation_dataset,
)
from knowledge_assistant.evaluation.exceptions import EvaluationDatasetError
from knowledge_assistant.evaluation.settings import EvaluationSettings

FIXTURES_DIR = Path("tests/unit/evaluation/fixtures")
BENCHMARK_PATH = Path("data/evaluation/retrieval_benchmark_v1.json")


class TestLoadEvaluationDataset:
    def test_loads_minimal_fixture(self) -> None:
        dataset = load_evaluation_dataset(FIXTURES_DIR / "minimal_dataset.json")

        assert dataset.dataset_id == "fixture_dataset"
        assert len(dataset.cases) == 2
        assert dataset.documents.path_for_key("policy-b") == (
            "knowledge/policies/policy_b.md"
        )

    def test_loads_committed_benchmark(self) -> None:
        dataset = load_evaluation_dataset(BENCHMARK_PATH)

        assert dataset.dataset_id == "retrieval_benchmark_v1"
        assert len(dataset.cases) >= 50
        assert dataset.documents.path_for_key("remote-work-policy") == (
            "knowledge/policies/remote_work_policy.md"
        )

    def test_rejects_duplicate_case_id(self) -> None:
        with pytest.raises(EvaluationDatasetError, match="duplicate case_id"):
            load_evaluation_dataset(FIXTURES_DIR / "duplicate_case_id.json")

    def test_rejects_unknown_document_key(self) -> None:
        with pytest.raises(EvaluationDatasetError, match="unknown document key"):
            load_evaluation_dataset(FIXTURES_DIR / "unknown_document_key.json")

    def test_rejects_empty_cases_array(self, tmp_path: Path) -> None:
        payload: dict[str, Any] = {
            "dataset_id": "empty",
            "documents": {"a": {"path": "knowledge/a.md"}},
            "cases": [],
        }
        path = tmp_path / "empty_cases.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(EvaluationDatasetError, match="cases must be a non-empty"):
            load_evaluation_dataset(path)

    def test_rejects_empty_dataset_id(self, tmp_path: Path) -> None:
        payload = {
            "dataset_id": "   ",
            "documents": {"a": {"path": "knowledge/a.md"}},
            "cases": [
                {
                    "case_id": "case-1",
                    "question": "Question?",
                    "expected_document_key": "a",
                },
            ],
        }
        path = tmp_path / "empty_id.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(EvaluationDatasetError, match="dataset_id"):
            load_evaluation_dataset(path)


class TestDocumentRegistry:
    def test_rejects_empty_registry(self) -> None:
        with pytest.raises(ValueError, match="documents registry must be non-empty"):
            DocumentRegistry(entries=())

    def test_unknown_key_raises_key_error(self) -> None:
        registry = DocumentRegistry(entries=(("policy-a", "knowledge/a.md"),))

        with pytest.raises(KeyError, match="unknown document key"):
            registry.path_for_key("missing")


class TestEvaluationSettings:
    @pytest.mark.parametrize(
        ("metrics_k", "message"),
        [
            ((6,), "must be <= eval_top_k"),
            ((), "metrics_k must be non-empty"),
            ((0,), "must be >= 1"),
        ],
    )
    def test_rejects_invalid_metrics_k(
        self,
        metrics_k: tuple[int, ...],
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            EvaluationSettings(eval_top_k=5, metrics_k=metrics_k)


class TestEvaluationDatasetConstruction:
    def test_rejects_duplicate_case_ids(self) -> None:
        registry = DocumentRegistry(entries=(("policy-a", "knowledge/a.md"),))
        cases = (
            EvaluationCase(
                case_id="dup",
                question="Q1?",
                expected_document_key="policy-a",
            ),
            EvaluationCase(
                case_id="dup",
                question="Q2?",
                expected_document_key="policy-a",
            ),
        )

        with pytest.raises(ValueError, match="duplicate case_id"):
            EvaluationDataset(
                dataset_id="test",
                description=None,
                corpus_version=None,
                documents=registry,
                cases=cases,
            )
