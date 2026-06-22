"""Demo command orchestration for the rag CLI."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from knowledge_assistant.bootstrap import (
    DEMO_RETRIEVAL_PIPELINE_LABEL,
    build_demo_environment,
)

if TYPE_CHECKING:
    from knowledge_assistant.bootstrap import DemoEnvironment


def run_demo_info() -> int:
    """Print read-only demo status and return an exit code."""
    try:
        environment = build_demo_environment()
    except Exception as exc:
        print(f"error: failed to assemble demo environment: {exc}", file=sys.stderr)
        return 1

    try:
        _print_demo_info(environment)
    except Exception as exc:
        print(f"error: failed to read demo status: {exc}", file=sys.stderr)
        return 1

    return 0


def run_demo_load(*, rebuild: bool, approved: bool) -> int:
    """Index the canonical corpus into Qdrant."""
    try:
        environment = build_demo_environment()
    except Exception as exc:
        print(f"error: failed to assemble demo environment: {exc}", file=sys.stderr)
        return 1

    if not environment.corpus_exists():
        corpus_path = environment.settings.corpus_root.resolve()
        print(
            f"error: corpus directory not found: {corpus_path}",
            file=sys.stderr,
        )
        print(
            "generate the corpus first: python3 tools/knowledge_generator/generator.py",
            file=sys.stderr,
        )
        return 1

    document_count = environment.corpus_document_count()
    if document_count == 0:
        corpus_path = environment.settings.corpus_root.resolve()
        print(
            "error: corpus directory is empty or has no indexable documents: "
            f"{corpus_path}",
            file=sys.stderr,
        )
        return 1

    collection_exists = environment.collection_exists()
    if collection_exists and not (rebuild and approved):
        print(
            "error: collection already exists; refusing to modify without approval",
            file=sys.stderr,
        )
        print(
            "re-run with: rag demo load --rebuild --approve",
            file=sys.stderr,
        )
        return 1

    if rebuild and not approved:
        print(
            "error: rebuild requires explicit approval; pass --approve or --yes",
            file=sys.stderr,
        )
        return 1

    try:
        result = environment.indexing_pipeline.index_documents(
            (environment.corpus_indexing_source(),),
            rebuild=rebuild,
        )
    except Exception as exc:
        print(f"error: indexing failed: {exc}", file=sys.stderr)
        return 1

    print(
        "indexed demo corpus: "
        f"documents={result.document_count}, "
        f"chunks={result.upserted_count}, "
        f"collection={environment.settings.collection_name}",
    )
    return 0


def run_demo_reset(*, approved: bool) -> int:
    """Delete the demo Qdrant collection when explicitly approved."""
    if not approved:
        print(
            "error: reset requires explicit approval; pass --approve or --yes",
            file=sys.stderr,
        )
        return 1

    try:
        environment = build_demo_environment()
    except Exception as exc:
        print(f"error: failed to assemble demo environment: {exc}", file=sys.stderr)
        return 1

    collection_name = environment.settings.collection_name
    try:
        existed = environment.collection_exists()
        environment.vector_store.delete_collection()
    except Exception as exc:
        print(f"error: failed to reset collection: {exc}", file=sys.stderr)
        return 1

    if existed:
        print(f"removed collection: {collection_name}")
    else:
        print(f"collection already absent: {collection_name}")
    return 0


def _print_demo_info(environment: DemoEnvironment) -> None:
    corpus_exists = environment.corpus_exists()
    print(f"Corpus exists: {'yes' if corpus_exists else 'no'}")
    print(f"Corpus document count: {environment.corpus_document_count()}")
    print(
        f"Collection exists: {'yes' if environment.collection_exists() else 'no'}",
    )
    print(f"Collection chunk count: {environment.collection_chunk_count()}")
    print(f"Retrieval pipeline: {DEMO_RETRIEVAL_PIPELINE_LABEL}")
    print(f"Qdrant URL: {environment.settings.qdrant_url}")
    print(f"Collection name: {environment.settings.collection_name}")
    print(f"Corpus path: {environment.settings.corpus_root.resolve()}")
