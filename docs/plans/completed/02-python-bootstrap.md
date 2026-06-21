# Plan 02 — Python Bootstrap

**Status:** Completed

**Created:** 2026-06-21

**Completed:** 2026-06-21

**Roadmap:** Phase 1 — Foundation

---

## Objective

Establish the Python project foundation — packaging, source layout, development tooling, and validation workflow — so that all subsequent implementation plans can add domain logic, integrations, and features within a consistent, enforceable development environment.

After this plan is complete, the bootstrap validation exception no longer applies and all commits must pass the standard quality commands.

---

## Scope

This plan authorizes repository and runtime bootstrap activities only:

### Project and Dependency Management

* `pyproject.toml` creation with project metadata, build system, and `uv` configuration;
* `uv` project initialization and lockfile generation (`uv.lock`);
* Python version constraint declaration;
* development dependency groups (no application runtime dependencies).

### Package Layout

* `src/` layout with `src/knowledge_assistant/` as the root package;
* component package skeleton aligned with [docs/ARCHITECTURE.md](../../ARCHITECTURE.md):

```text
src/knowledge_assistant/
    __init__.py       # __version__
    py.typed
    core/
    agent/
    mcp_server/
    retrieval/
    indexing/
    llm/
    storage/
    cli/
```

* minimal `__init__.py` files in each package (no business logic, no runtime side effects);
* root package `__version__` and `py.typed` marker.

### Quality Tooling Configuration

* **ruff** — formatting and linting rules in `pyproject.toml`;
* **basedpyright** — type-checking configuration (`pyproject.toml` and/or `pyrightconfig.json`);
* **pytest** — test discovery, `tests/` layout, and minimal configuration in `pyproject.toml`.

### Test Layout

* `tests/` directory structure aligned with testing standards:

```text
tests/
    unit/
    integration/
    smoke/
```

* minimal smoke test(s) verifying package importability and tooling execution (not business logic tests).

### Development Dependencies

Authorize only tooling required for bootstrap validation:

* `ruff`
* `basedpyright`
* `pytest`

No LangGraph, MCP, LlamaIndex, Qdrant, embedding, reranking, or LLM client libraries at this stage.

### Validation Workflow

* document local validation commands in `README.md`;
* ensure the following commands pass from repository root:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

* update governance references to reflect that the bootstrap validation exception is superseded after plan completion.

### Documentation Updates

* update `docs/PROGRESS.md` when the plan completes;
* update `README.md` with Python setup and validation instructions;
* update governance references to reflect that the bootstrap validation exception is superseded after plan completion.

---

## Non-Scope

This plan does **not** authorize:

* LangGraph agent implementation;
* MCP server or MCP client implementation;
* retrieval layer implementation (dense, sparse, fusion, reranking);
* Qdrant integration or storage logic;
* LlamaIndex integration or indexing pipeline implementation;
* LLM boundary implementation;
* CLI chat functionality or entrypoint behavior;
* domain models (`Document`, `Chunk`, `SearchResult`, etc.);
* configuration loading for external services;
* business logic in any package;
* application runtime dependencies;
* document corpus generation;
* evaluation suites;
* Docker, Kubernetes, or deployment infrastructure;
* authentication or secrets management;
* CI/CD platform setup beyond documenting the local validation workflow (optional GitHub Actions may be added in a future plan).

Future plans (starting with Plan 03 — Domain Models) build on this foundation independently.

---

## Acceptance Criteria

- [x] `pyproject.toml` exists with project metadata, `src` layout, and `uv` configuration
- [x] `uv.lock` is generated and committed
- [x] `src/knowledge_assistant/` root package exists with `__version__` and `py.typed`
- [x] All component package directories exist with minimal `__init__.py` files and no business logic
- [x] `tests/unit/`, `tests/integration/`, and `tests/smoke/` directories exist
- [x] At least one smoke test passes and verifies package importability
- [x] ruff formatting and linting are configured and pass
- [x] basedpyright is configured and passes with zero errors on bootstrap code
- [x] pytest is configured and all tests pass
- [x] No application runtime dependencies are declared in `pyproject.toml`
- [x] `uv run ruff format --check .` passes from repository root
- [x] `uv run ruff check .` passes from repository root
- [x] `uv run basedpyright` passes from repository root
- [x] `uv run pytest` passes from repository root
- [x] `README.md` documents Python setup and validation workflow
- [x] Bootstrap validation exception is documented as superseded in governance files (or noted as complete in progress documentation)
- [x] `docs/PROGRESS.md` records plan completion
- [x] Package layout matches `docs/ARCHITECTURE.md` source layout

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Scope creep into domain or integration code | Explicit non-scope section; packages contain only empty `__init__.py` files |
| Premature runtime dependency addition | Restrict dependencies to development tooling; defer application libraries to later plans |
| Package layout diverges from architecture | Mirror `docs/ARCHITECTURE.md` source layout exactly |
| Tooling configuration drift across governance files | Single validation command block in `pyproject.toml`; README as contributor entry point |
| basedpyright fails on empty packages | Configure appropriate strictness for bootstrap; use minimal typed bootstrap code only |
| Contributors invoke tools outside `uv run` | Document and enforce `uv run` workflow in README and governance files |
| Incomplete package skeleton blocks later plans | Validate import paths and test discovery before marking plan complete |

---

## Implementation Steps

1. **Initialize uv project** — create `pyproject.toml` with project name, version, Python constraint, and `src` layout build configuration.
2. **Add development dependencies** — add `ruff`, `basedpyright`, and `pytest` via `uv`; generate `uv.lock`.
3. **Create root package** — add `src/knowledge_assistant/__init__.py` with `__version__`, and `py.typed`.
4. **Create component package skeleton** — add empty `__init__.py` files for `core`, `agent`, `mcp_server`, `retrieval`, `indexing`, `llm`, `storage`, and `cli`.
5. **Configure ruff** — add `[tool.ruff]` and `[tool.ruff.format]` sections with project-appropriate rules.
6. **Configure basedpyright** — add type-checking configuration targeting `src/knowledge_assistant`.
7. **Configure pytest** — add `[tool.pytest.ini_options]` with `testpaths` and discovery settings.
8. **Create test layout** — add `tests/unit/`, `tests/integration/`, `tests/smoke/` with package `__init__.py` files as needed.
9. **Add smoke test** — minimal test confirming `knowledge_assistant` imports and `__version__` is accessible.
10. **Run validation suite** — execute all four quality commands; fix any configuration or layout issues until all pass.
11. **Update documentation** — update `README.md`, `docs/PROGRESS.md`, and governance references for superseded bootstrap validation exception.
12. **Verify non-scope compliance** — confirm no business logic, runtime dependencies, or integration code was introduced.

---

## Checklist

### Project Initialization

- [x] Create `pyproject.toml` with `[project]` metadata (name, version, description, requires-python)
- [x] Configure build backend for `src` layout
- [x] Set Python version constraint (>=3.12 recommended)
- [x] Run `uv lock` and commit `uv.lock`
- [x] Verify `.venv` is gitignored (already in `.gitignore`)

### Development Dependencies

- [x] Add `ruff` as development dependency
- [x] Add `basedpyright` as development dependency
- [x] Add `pytest` as development dependency
- [x] Confirm no runtime/application dependencies are present

### Package Skeleton

- [x] Create `src/knowledge_assistant/__init__.py` with `__version__`
- [x] Create `src/knowledge_assistant/py.typed`
- [x] Create `src/knowledge_assistant/core/__init__.py`
- [x] Create `src/knowledge_assistant/agent/__init__.py`
- [x] Create `src/knowledge_assistant/mcp_server/__init__.py`
- [x] Create `src/knowledge_assistant/retrieval/__init__.py`
- [x] Create `src/knowledge_assistant/indexing/__init__.py`
- [x] Create `src/knowledge_assistant/llm/__init__.py`
- [x] Create `src/knowledge_assistant/storage/__init__.py`
- [x] Create `src/knowledge_assistant/cli/__init__.py`
- [x] Verify no business logic exists in any `__init__.py`

### Tooling Configuration

- [x] Configure ruff lint rules in `pyproject.toml`
- [x] Configure ruff format settings in `pyproject.toml`
- [x] Configure basedpyright in `pyproject.toml` and/or `pyrightconfig.json`
- [x] Configure pytest `testpaths` and discovery in `pyproject.toml`

### Test Layout

- [x] Create `tests/unit/` directory
- [x] Create `tests/integration/` directory
- [x] Create `tests/smoke/` directory
- [x] Add `tests/smoke/test_package_import.py` (or equivalent minimal smoke test)
- [x] Confirm smoke test passes

### Validation Workflow

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes
- [x] Document setup steps in `README.md` (`uv sync`, validation commands)
- [x] Document that bootstrap validation exception no longer applies

### Documentation

- [x] Update `docs/PROGRESS.md` with Python bootstrap milestone
- [x] Update governance references for superseded bootstrap validation exception
- [x] Verify package layout matches `docs/ARCHITECTURE.md`

### Non-Scope Verification

- [x] No LangGraph code
- [x] No MCP code
- [x] No retrieval implementation
- [x] No Qdrant integration
- [x] No LlamaIndex integration
- [x] No LLM client code
- [x] No CLI functionality beyond empty package
- [x] No domain models or business logic
