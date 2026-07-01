---
name: Bug report
about: Report incorrect behavior or documentation inconsistency
title: ''
labels: bug
assignees: ''
---

## Summary

A clear description of the bug or inconsistency.

## Steps to reproduce

1.
2.
3.

## Expected behavior

What you expected to happen.

## Actual behavior

What happened instead. Include command output or error messages when relevant.

## Environment

- OS:
- Python version:
- `uv` version:
- Embedding mode (`RAG_EMBEDDING_MODE`): stub / real
- Reranker mode (`RAG_RERANKER_MODE`): stub / real

## Validation

If you changed code, confirm you ran:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

## Additional context

Links to related plans, ADRs, or documentation sections.
