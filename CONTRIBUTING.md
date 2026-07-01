# Contributing

Thank you for your interest in Production RAG Knowledge Assistant. This repository is documentation-driven: implementation follows active plans in `docs/plans/active/`.

## Read first

Before making changes, read in order:

1. [AGENTS.md](AGENTS.md)
2. [PROJECT.md](PROJECT.md)
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. [docs/DECISIONS.md](docs/DECISIONS.md)
5. [docs/plans/active/](docs/plans/active/)
6. [docs/PROGRESS.md](docs/PROGRESS.md)

## Workflow

1. Confirm your work is covered by an **active plan**. If not, extend or create a plan before implementing.
2. Stay within plan scope and architectural boundaries (see `docs/ARCHITECTURE.md`).
3. Update documentation when behavior or architecture changes.
4. Record meaningful milestones in `docs/PROGRESS.md`.

Avoid drive-by refactors outside active-plan scope.

## Validation

Run all quality commands from the repository root before opening a pull request:

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

All commands must pass. Run tools through `uv run`, not directly.

## Pull requests

Use the pull request template. Include:

* what changed and why;
* which plan authorizes the work;
* confirmation that validation passed.

## Questions

Open a GitHub issue for bugs or discussion. Do not post secrets, API keys, or credentials in issues or pull requests.
