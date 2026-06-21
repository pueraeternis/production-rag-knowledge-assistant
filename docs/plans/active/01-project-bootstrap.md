# Plan 01 — Project Bootstrap

**Status:** Active

**Created:** 2026-06-21

---

## Objective

Establish repository governance, documentation structure, and project bootstrap foundations so that subsequent implementation work can proceed in a documentation-driven, agent-legible manner.

---

## Scope

This plan authorizes:

* repository governance alignment (AGENTS.md, PROJECT.md, README.md, `.cursor/rules/`);
* documentation skeleton (`docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, plan directories);
* repository bootstrap validation rules (pre-Python exception);
* future Python project initialization (`pyproject.toml`, package layout, `uv` tooling, quality tooling configuration).

---

## Non-Scope

This plan does **not** authorize:

* application implementation;
* LangGraph agent implementation;
* MCP server implementation;
* retrieval layer implementation;
* indexing pipeline implementation;
* Qdrant integration;
* LLM integration;
* CLI chat functionality;
* document corpus generation;
* evaluation suites.

---

## Acceptance Criteria

- [x] Documentation precedence is consistent across all governance files
- [x] Read-first order is consistent across all governance files
- [x] Terminology uses "Retrieval Layer" everywhere (not "Retrieval Engine")
- [x] `docs/` skeleton exists with ARCHITECTURE, DECISIONS, PROGRESS, and plan directories
- [x] Bootstrap validation exception documented wherever validation is required
- [x] README.md points contributors to governance and documentation entry points
- [x] PROJECT.md has no duplicate headings or structural inconsistencies
- [ ] Python project initialization completed in a follow-up increment (future work under this plan)

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Governance documents drift out of sync | Single precedence order and read-first order enforced across all files |
| Contributors run validation before Python bootstrap | Documented bootstrap validation exception |
| Scope creep into application code | Explicit non-scope section; implementation requires future plans |
| Incomplete architecture documentation | ARCHITECTURE.md provides high-level outline aligned with PROJECT.md |

---

## Implementation Steps

1. Align governance documents (precedence, read-first order, terminology).
2. Create documentation skeleton.
3. Document bootstrap validation exception.
4. Update README as repository entry point.
5. Clean up PROJECT.md structure.
6. Initialize Python project (`pyproject.toml`, `src/knowledge_assistant/`, quality tooling) — future increment.

---

## Checklist

### Governance Alignment

- [x] Align documentation precedence across governance files
- [x] Align read-first order across governance files
- [x] Standardize "Retrieval Layer" terminology
- [x] Document bootstrap validation exception

### Documentation Skeleton

- [x] Create `docs/ARCHITECTURE.md`
- [x] Create `docs/DECISIONS.md`
- [x] Create `docs/PROGRESS.md`
- [x] Create `docs/plans/active/`, `backlog/`, `completed/`

### Repository Entry Points

- [x] Update `README.md`
- [x] Clean up `PROJECT.md`

### Python Bootstrap (Future Increment)

- [ ] Create `pyproject.toml` with `uv` configuration
- [ ] Create `src/knowledge_assistant/` package skeleton
- [ ] Configure ruff, basedpyright, and pytest
- [ ] Add initial validation to CI (if applicable)
- [ ] Mark bootstrap validation exception as no longer applicable
