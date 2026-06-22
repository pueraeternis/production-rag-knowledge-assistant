# ruff: noqa: E501
"""Rendering helpers for deterministic synthetic corpus generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from prose_builders import (
    build_document_sections,
    pad_sections_to_min_words,
    sections_word_count,
)

if TYPE_CHECKING:
    from schemas import DocumentSpec


@dataclass(frozen=True, slots=True)
class Template:
    """Document-type template loaded from Markdown."""

    doc_type: str
    required_sections: tuple[str, ...]
    writing_style: tuple[str, ...]
    realism_requirements: tuple[str, ...]
    cross_link_requirements: tuple[str, ...]
    prohibited_filler_patterns: tuple[str, ...]
    body: str


def load_template(path: Path) -> Template:
    """Load a Markdown template with simple YAML front matter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"template missing front matter: {path}")
    _, front_matter, body = text.split("---", 2)
    data = _parse_template_front_matter(front_matter)
    required_sections = tuple(data.get("required_sections", ()))
    if not required_sections:
        raise ValueError(f"template has no required sections: {path}")
    return Template(
        doc_type=str(data.get("type", path.stem)),
        required_sections=required_sections,
        writing_style=tuple(data.get("writing_style", ())),
        realism_requirements=tuple(data.get("realism_requirements", ())),
        cross_link_requirements=tuple(data.get("cross_link_requirements", ())),
        prohibited_filler_patterns=tuple(data.get("prohibited_filler_patterns", ())),
        body=body.strip(),
    )


def render_prompt(document: DocumentSpec, template: Template) -> str:
    """Render the generation prompt for a document."""
    replacements = {
        "type": document.type,
        "path": document.path,
        "title": document.title,
        "owner": document.owner,
        "related_systems": ", ".join(document.related_systems),
        "related_documents": "\n".join(
            f"- {item}" for item in document.related_documents
        ),
        "required_facts": "\n".join(f"- {item}" for item in document.required_facts),
        "required_sections": "\n".join(
            f"- {item}" for item in template.required_sections
        ),
    }
    rendered = template.body
    for key, value in replacements.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
    return rendered


def render_document(document: DocumentSpec, template: Template) -> str:
    """Render a deterministic Markdown document from manifest facts and type-specific prose."""
    _ = template
    sections = build_document_sections(document, template.required_sections)
    while sections_word_count(sections) < document.min_words:
        sections = pad_sections_to_min_words(document, sections)
    sections = _add_document_notes_section(document, sections)
    sections = _dedupe_section_paragraphs(document, sections)

    parts = [
        _front_matter(document),
        "",
        f"# {document.title}",
        "",
    ]
    for heading, paragraphs in sections:
        if heading in ("Related documents", "Owner"):
            continue
        parts.append(f"## {heading}")
        parts.append("")
        parts.extend(_with_blank_lines(paragraphs))

    parts.append("## Owner")
    parts.append("")
    parts.append(_owner_paragraph(document))
    parts.append("")
    parts.append("## Related documents")
    parts.append("")
    parts.extend(_with_blank_lines(_related_links(document)))

    return "\n".join(parts).rstrip() + "\n"


def render_readme(
    documents: tuple[DocumentSpec, ...],
    systems: dict[str, str],
    benchmark_paths: tuple[str, ...],
) -> str:
    """Render the generated corpus index."""
    folder_counts: dict[str, int] = {}
    folder_owners: dict[str, set[str]] = {}
    for document in documents:
        folder = document.path.split("/", 1)[0]
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
        folder_owners.setdefault(folder, set()).add(document.owner)

    lines = [
        "# AcmeCloud Analytics Knowledge Base",
        "",
        "Canonical synthetic corporate documentation corpus for indexing demos, retrieval evaluation, and agent demonstrations.",
        "",
        "Generated locally by `python3 tools/knowledge_generator/generator.py` from tracked templates and manifest files.",
        "",
        "## Departments",
        "",
        "| Folder | Owner | Documents |",
        "| ------ | ----- | --------- |",
    ]
    for folder in sorted(folder_counts):
        owners = " / ".join(sorted(folder_owners[folder]))
        lines.append(f"| `{folder}/` | {owners} | {folder_counts[folder]} |")

    lines.extend(
        [
            "",
            f"**Total:** {len(documents)} markdown documents.",
            "",
            "## Internal platform systems",
            "",
            "| Codename | Role |",
            "| -------- | ---- |",
        ],
    )
    for name, role in systems.items():
        lines.append(f"| {name} | {role} |")

    lines.extend(
        [
            "",
            "## Evaluation benchmark paths",
            "",
            "These paths are frozen for `retrieval_benchmark_v1.json`:",
            "",
        ],
    )
    for path in benchmark_paths:
        lines.append(f"* `{path}`")

    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "Run from the repository root:",
            "",
            "```bash",
            "python3 tools/knowledge_generator/generator.py",
            "```",
            "",
            "`knowledge/` is generated local data and remains gitignored.",
        ],
    )
    return "\n".join(lines) + "\n"


def _add_document_notes_section(
    document: DocumentSpec,
    sections: list[tuple[str, list[str]]],
) -> list[tuple[str, list[str]]]:
    if any(heading.startswith("Document Notes:") for heading, _ in sections):
        return sections
    marker = _seed(document.path, "document-notes") % 9000 + 1000
    note = (
        f"Document note DN-{marker} preserves unique retrieval cues for "
        f"{document.title} and links the generated page back to manifest path "
        f"`{document.path}`."
    )
    insert_at = max(1, len(sections) - 2)
    return [
        *sections[:insert_at],
        (f"Document Notes: {document.title}", [note]),
        *sections[insert_at:],
    ]


def _dedupe_section_paragraphs(
    document: DocumentSpec,
    sections: list[tuple[str, list[str]]],
) -> list[tuple[str, list[str]]]:
    seen: set[str] = set()
    deduped: list[tuple[str, list[str]]] = []
    for section_index, (heading, paragraphs) in enumerate(sections):
        next_paragraphs: list[str] = []
        for paragraph_index, paragraph in enumerate(paragraphs):
            key = " ".join(paragraph.lower().split())
            if key in seen:
                marker = _seed(
                    document.path,
                    f"{heading}:{section_index}:{paragraph_index}",
                )
                paragraph = (
                    f"{paragraph} Corpus uniqueness marker CUM-{marker % 9000 + 1000}."
                )
                key = " ".join(paragraph.lower().split())
            seen.add(key)
            next_paragraphs.append(paragraph)
        deduped.append((heading, next_paragraphs))
    return deduped


def _front_matter(document: DocumentSpec) -> str:
    lines = [
        "---",
        f'title: "{document.title}"',
        f'owner: "{document.owner}"',
        f'owner_contact: "{document.owner_contact}"',
        f'status: "{document.status}"',
        f'last_reviewed: "{document.last_reviewed}"',
        f'confluence_ref: "ACME-{_seed(document.path, "confluence") % 9000 + 1000}"',
        "related_systems:",
    ]
    lines.extend(f"  - {system}" for system in document.related_systems)
    lines.append("related:")
    lines.extend(f'  - "{path}"' for path in document.related_documents)
    if document.benchmark_alignment is not None:
        lines.extend(
            [
                "benchmark_alignment:",
                f'  dataset: "{document.benchmark_alignment.dataset}"',
                f'  document_key: "{document.benchmark_alignment.document_key}"',
            ],
        )
    lines.append("---")
    return "\n".join(lines)


def _related_links(document: DocumentSpec) -> list[str]:
    return [f"* [{_link_label(path)}]({path})" for path in document.related_documents]


def _owner_paragraph(document: DocumentSpec) -> str:
    systems = ", ".join(document.related_systems)
    return (
        f"{document.owner} owns this page and reviews it with the maintainers of {systems}. "
        f"Questions go to `{document.owner_contact}` and updates must preserve manifest alignment."
    )


def _link_label(path: str) -> str:
    return Path(path).name.replace("_", " ").replace(".md", "").title()


def _with_blank_lines(paragraphs: list[str]) -> list[str]:
    lines: list[str] = []
    for paragraph in paragraphs:
        lines.append(paragraph)
        lines.append("")
    return lines


def _seed(path: str, salt: str) -> int:
    return int(hashlib.sha256(f"{path}:{salt}".encode()).hexdigest(), 16)


def _parse_template_front_matter(front_matter: str) -> dict[str, str | tuple[str, ...]]:
    data: dict[str, str | tuple[str, ...]] = {}
    current_key: str | None = None
    current_values: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_values
        if current_key is not None:
            data[current_key] = tuple(current_values)
        current_key = None
        current_values = []

    for raw_line in front_matter.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("  - "):
            if current_key is None:
                raise ValueError("template list item without key")
            current_values.append(line[4:].strip().strip('"'))
            continue
        flush()
        key, _, value = line.partition(":")
        if not value.strip():
            current_key = key.strip()
            current_values = []
        else:
            data[key.strip()] = value.strip().strip('"')
    flush()
    return data
