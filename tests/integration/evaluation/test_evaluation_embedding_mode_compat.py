"""Evaluation framework compatibility with bootstrap embedding modes."""

import uuid
from pathlib import Path

from qdrant_client import QdrantClient

from knowledge_assistant.bootstrap import BootstrapSettings, build_demo_environment
from knowledge_assistant.evaluation import EvaluationRunner, load_evaluation_dataset
from knowledge_assistant.evaluation.settings import EvaluationSettings
from knowledge_assistant.storage.config import StorageSettings
from knowledge_assistant.storage.qdrant_store import create_qdrant_vector_store


class TestEvaluationEmbeddingModeCompat:
    def test_evaluation_runner_works_with_bootstrap_retriever_stub_mode(self) -> None:
        """Plan 13 APIs remain unchanged when bootstrap wires stub embeddings."""
        settings = BootstrapSettings(
            corpus_root=Path("knowledge"),
            storage_settings=StorageSettings(
                collection_name=f"eval-embed-compat-{uuid.uuid4()}",
                dense_vector_size=1024,
            ),
        )
        store = create_qdrant_vector_store(
            settings.storage_settings,
            client=QdrantClient(":memory:"),
        )
        store.create_collection()
        environment = build_demo_environment(settings=settings, vector_store=store)
        dataset = load_evaluation_dataset(
            Path("data/evaluation/retrieval_benchmark_v1.json"),
        )
        runner_settings = EvaluationSettings(eval_top_k=1, metrics_k=(1,))
        runner = EvaluationRunner(settings=runner_settings)

        report = runner.run(
            environment.retriever,
            dataset,
            retriever_label="fusion+stub_embed",
        )

        assert report.retriever_label == "fusion+stub_embed"
        assert report.case_count == len(dataset.cases)
