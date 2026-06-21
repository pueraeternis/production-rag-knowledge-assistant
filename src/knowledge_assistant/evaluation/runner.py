"""Evaluation runner orchestrating retrieval over a benchmark dataset."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_assistant.core.retrieval import SearchQuery, SearchResult
from knowledge_assistant.evaluation.dataset import EvaluationDataset
from knowledge_assistant.evaluation.metrics import (
    document_path_from_result,
    hit_at_k,
    reciprocal_rank,
)
from knowledge_assistant.evaluation.report import EvaluationCaseResult, EvaluationReport
from knowledge_assistant.evaluation.settings import EvaluationSettings
from knowledge_assistant.retrieval.protocol import Retriever


@dataclass(frozen=True, slots=True)
class EvaluationRunner:
    """Runs retrieval evaluation for any Retriever implementation."""

    settings: EvaluationSettings

    def run(
        self,
        retriever: Retriever,
        dataset: EvaluationDataset,
        *,
        retriever_label: str,
    ) -> EvaluationReport:
        """Evaluate one retriever against all benchmark cases."""
        if not retriever_label.strip():
            msg = "retriever_label must be non-empty"
            raise ValueError(msg)

        case_results: list[EvaluationCaseResult] = []
        for case in dataset.cases:
            expected_document_path = dataset.documents.path_for_key(
                case.expected_document_key,
            )
            query = SearchQuery(
                text=case.question,
                top_k=self.settings.eval_top_k,
            )
            retrieval_result = retriever.retrieve(query)
            results = retrieval_result.results
            retrieved_document_paths = tuple(
                document_path_from_result(result) for result in results
            )

            hit_flags = {
                k: hit_at_k(
                    results,
                    expected_document_path=expected_document_path,
                    k=k,
                )
                for k in self.settings.metrics_k
            }
            rr = reciprocal_rank(
                results,
                expected_document_path=expected_document_path,
            )
            first_hit_rank = _first_hit_rank(
                results,
                expected_document_path=expected_document_path,
            )

            case_results.append(
                EvaluationCaseResult(
                    case_id=case.case_id,
                    question=case.question,
                    expected_document_key=case.expected_document_key,
                    expected_document_path=expected_document_path,
                    hit_at_k=hit_flags,
                    reciprocal_rank=rr,
                    first_hit_rank=first_hit_rank,
                    retrieved_document_paths=retrieved_document_paths,
                ),
            )

        case_count = len(case_results)
        hit_rate_at_k = {
            k: sum(1 for result in case_results if result.hit_at_k[k]) / case_count
            for k in self.settings.metrics_k
        }
        recall_at_k_values = {
            k: sum(1.0 if result.hit_at_k[k] else 0.0 for result in case_results)
            / case_count
            for k in self.settings.metrics_k
        }
        mrr = sum(result.reciprocal_rank for result in case_results) / case_count

        return EvaluationReport(
            retriever_label=retriever_label,
            dataset_id=dataset.dataset_id,
            eval_top_k=self.settings.eval_top_k,
            metrics_k=self.settings.metrics_k,
            case_count=case_count,
            hit_rate_at_k=hit_rate_at_k,
            recall_at_k=recall_at_k_values,
            mrr=mrr,
            cases=tuple(case_results),
        )


def _first_hit_rank(
    results: tuple[SearchResult, ...],
    *,
    expected_document_path: str,
) -> int | None:
    for rank, result in enumerate(results, start=1):
        if document_path_from_result(result) == expected_document_path:
            return rank
    return None
