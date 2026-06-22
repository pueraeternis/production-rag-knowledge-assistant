# ruff: noqa: E501
"""Quality gates for generated synthetic corpus documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schemas import CorpusManifest, DocumentSpec

from .metrics import (
    CorpusMetrics,
    DocumentMetrics,
    QualityIssue,
    body_text,
    paragraphs,
    section_titles,
    sentences,
    word_count,
)

KNOWN_FILLER_PHRASES: tuple[str, ...] = (
    "lorem ipsum",
    "placeholder text",
    "to be determined",
    "teams should treat this document as the operational source of truth",
    "cross-functional reviewers include security for access changes",
)

MAX_REPEATED_SENTENCE_RATIO = 0.20
MIN_SECTION_DIVERSITY = 0.75


def check_corpus(
    knowledge_root: Path,
    manifest: CorpusManifest,
    required_sections_by_type: dict[str, tuple[str, ...]],
) -> tuple[list[QualityIssue], CorpusMetrics]:
    """Run all corpus quality gates."""
    issues: list[QualityIssue] = []
    metrics = CorpusMetrics()
    section_structures: dict[str, int] = {}

    for document in manifest.documents:
        path = knowledge_root / document.path
        if not path.exists():
            issues.append(QualityIssue(document.path, "missing generated document"))
            continue

        markdown = path.read_text(encoding="utf-8")
        doc_issues, doc_metrics = check_document(
            document,
            markdown,
            required_sections_by_type[document.type],
        )
        issues.extend(doc_issues)
        metrics.per_doc.append(doc_metrics)
        metrics.duplicate_paragraphs += doc_metrics.duplicate_paragraphs
        metrics.duplicate_sentences += doc_metrics.duplicate_sentences
        metrics.filler_hits += doc_metrics.filler_hits
        key = "|".join(doc_metrics.section_titles)
        section_structures[key] = section_structures.get(key, 0) + 1

    _check_repeated_section_structures(section_structures, issues)
    _check_benchmark_paths(knowledge_root, manifest, issues)

    metrics.documents = len(metrics.per_doc)
    metrics.distinct_section_structures = len(section_structures)
    if metrics.per_doc:
        metrics.avg_repeated_sentence_ratio = sum(
            item.repeated_sentence_ratio for item in metrics.per_doc
        ) / len(metrics.per_doc)
        metrics.avg_section_diversity = sum(
            item.section_diversity for item in metrics.per_doc
        ) / len(metrics.per_doc)
    return issues, metrics


def check_document(
    document: DocumentSpec,
    markdown: str,
    required_sections: tuple[str, ...],
) -> tuple[list[QualityIssue], DocumentMetrics]:
    """Run quality gates for one document."""
    issues: list[QualityIssue] = []
    body = body_text(markdown)
    titles = section_titles(body)
    paras = paragraphs(body)
    duplicate_paragraphs = _duplicate_count(paras)
    duplicate_sentences, repeated_sentence_ratio = _sentence_duplication(paras)
    diversity = len(set(titles)) / len(titles) if titles else 0.0
    filler_hits = _filler_hits(body)
    wc = word_count(body)

    if wc < document.min_words:
        issues.append(
            QualityIssue(
                document.path,
                f"word count {wc} below minimum {document.min_words}",
            ),
        )
    if duplicate_paragraphs:
        issues.append(
            QualityIssue(
                document.path,
                f"duplicate paragraphs detected: {duplicate_paragraphs}",
            ),
        )
    if repeated_sentence_ratio > MAX_REPEATED_SENTENCE_RATIO:
        issues.append(
            QualityIssue(
                document.path,
                f"duplicate sentence ratio {repeated_sentence_ratio:.2%} exceeds {MAX_REPEATED_SENTENCE_RATIO:.0%}",
            ),
        )
    if diversity < MIN_SECTION_DIVERSITY:
        issues.append(
            QualityIssue(
                document.path,
                f"section diversity {diversity:.2%} below {MIN_SECTION_DIVERSITY:.0%}",
            ),
        )
    if filler_hits:
        issues.append(
            QualityIssue(
                document.path, f"known filler phrases detected: {filler_hits}"
            ),
        )

    missing_sections = [
        section
        for section in required_sections
        if section not in titles and section not in {"Owner", "Related documents"}
    ]
    if missing_sections:
        issues.append(
            QualityIssue(
                document.path,
                f"missing required sections: {', '.join(missing_sections)}",
            ),
        )

    return (
        issues,
        DocumentMetrics(
            path=document.path,
            word_count=wc,
            section_titles=titles,
            paragraph_count=len(paras),
            duplicate_paragraphs=duplicate_paragraphs,
            duplicate_sentences=duplicate_sentences,
            repeated_sentence_ratio=repeated_sentence_ratio,
            section_diversity=diversity,
            filler_hits=filler_hits,
        ),
    )


def _duplicate_count(items: list[str]) -> int:
    counts: dict[str, int] = {}
    for item in items:
        key = re.sub(r"\s+", " ", item.lower()).strip()
        counts[key] = counts.get(key, 0) + 1
    return sum(count - 1 for count in counts.values() if count > 1)


def _sentence_duplication(paras: list[str]) -> tuple[int, float]:
    all_sentences: list[str] = []
    for para in paras:
        all_sentences.extend(sentences(para))
    duplicate = _duplicate_count(all_sentences)
    ratio = duplicate / len(all_sentences) if all_sentences else 0.0
    return duplicate, ratio


def _filler_hits(text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in KNOWN_FILLER_PHRASES)


def _check_repeated_section_structures(
    section_structures: dict[str, int],
    issues: list[QualityIssue],
) -> None:
    for structure, count in section_structures.items():
        if count > 25:
            preview = structure.replace("|", " / ")
            issues.append(
                QualityIssue(
                    "<corpus>",
                    f"section structure repeated {count} times: {preview}",
                ),
            )


def _check_benchmark_paths(
    knowledge_root: Path,
    manifest: CorpusManifest,
    issues: list[QualityIssue],
) -> None:
    for benchmark_path in manifest.benchmark_paths:
        if not (knowledge_root / benchmark_path).exists():
            issues.append(QualityIssue(benchmark_path, "missing benchmark path"))
