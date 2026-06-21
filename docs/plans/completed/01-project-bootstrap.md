# Plan 01 — Project Bootstrap

**Status:** Completed

**Created:** 2026-06-21

**Completed:** 2026-06-21

---

## Objective

Establish repository governance and documentation structure so that subsequent implementation work can proceed in a documentation-driven, agent-legible manner.

---

## Scope

This plan authorizes:

* repository governance alignment (AGENTS.md, PROJECT.md, README.md, `.cursor/rules/`);
* documentation skeleton (`docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, plan directories);
* repository bootstrap validation rules (pre-Python exception).

---

## Non-Scope

This plan does **not** authorize:

* Python project initialization (`pyproject.toml`, package layout, `uv` tooling, quality tooling configuration);
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

Python bootstrap is authorized by [Plan 02 — Python Bootstrap](02-python-bootstrap.md).

---

## Acceptance Criteria

- [x] Documentation precedence is consistent across all governance files
- [x] Read-first order is consistent across all governance files
- [x] Terminology uses "Retrieval Layer" everywhere (not "Retrieval Engine")
- [x] `docs/` skeleton exists with ARCHITECTURE, DECISIONS, PROGRESS, and plan directories
- [x] Bootstrap validation exception documented wherever validation is required
- [x] README.md points contributors to governance and documentation entry points
- [x] PROJECT.md has no duplicate headings or structural inconsistencies

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Governance documents drift out of sync | Single precedence order and read-first order enforced across all files |
| Contributors run validation before Python project exists | Documented bootstrap validation exception |
| Scope creep into application code | Explicit non-scope section; implementation requires future plans |
| Incomplete architecture documentation | ARCHITECTURE.md provides high-level outline aligned with PROJECT.md |

---

## Implementation Steps

1. Align governance documents (precedence, read-first order, terminology).
2. Create documentation skeleton.
3. Document bootstrap validation exception.
4. Update README as repository entry point.
5. Clean up PROJECT.md structure.

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
