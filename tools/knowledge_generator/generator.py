# ruff: noqa: E402
"""Generate the synthetic AcmeCloud knowledge corpus from tracked project assets."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = Path(__file__).resolve().parent
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from quality.checks import check_corpus
from quality.report import raise_on_quality_failure
from rendering import (
    load_template,
    render_document,
    render_prompt,
    render_readme,
)
from schemas import CorpusManifest, validate_manifest

DEFAULT_MANIFEST = TOOL_ROOT / "manifests" / "corpus.v1.yaml"
TEMPLATES = TOOL_ROOT / "templates"


def main() -> None:
    """Generate `knowledge/` from the tracked manifest and templates."""
    manifest = load_manifest(DEFAULT_MANIFEST)
    output_root = ROOT / manifest.output_root
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    templates = {
        document_type: load_template(TEMPLATES / f"{document_type}.md")
        for document_type in {document.type for document in manifest.documents}
    }
    required_sections_by_type = {
        document_type: template.required_sections
        for document_type, template in templates.items()
    }

    rendered_prompts = 0
    for document in manifest.documents:
        template = templates[document.type]
        _ = render_prompt(document, template)
        rendered_prompts += 1
        target = output_root / document.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_document(document, template), encoding="utf-8")

    (output_root / "README.md").write_text(
        render_readme(manifest.documents, manifest.systems, manifest.benchmark_paths),
        encoding="utf-8",
    )

    issues, metrics = check_corpus(output_root, manifest, required_sections_by_type)
    print(
        f"Generated {len(manifest.documents) + 1} markdown files "
        f"from {rendered_prompts} rendered prompts.",
    )
    raise_on_quality_failure(issues, metrics)


def load_manifest(path: Path) -> CorpusManifest:
    """Load JSON-compatible YAML manifest data."""
    raw = path.read_text(encoding="utf-8")
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("manifest root must be an object")
    return validate_manifest(cast("dict[str, Any]", data))


if __name__ == "__main__":
    main()
