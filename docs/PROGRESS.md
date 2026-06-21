# Progress

Chronological record of completed milestones for Production RAG Knowledge Assistant.

---

## 2026-06-21 — Repository Governance Bootstrap

**Plan:** [01-project-bootstrap.md](plans/completed/01-project-bootstrap.md)

Established repository governance and documentation skeleton:

* aligned documentation precedence and read-first order across governance files;
* standardized terminology (Retrieval Layer);
* created `docs/` structure with architecture, decisions, and progress documents;
* documented bootstrap validation exception for pre-Python repository state.

---

## 2026-06-21 — Python Bootstrap

**Plan:** [02-python-bootstrap.md](plans/completed/02-python-bootstrap.md)

Established the Python project foundation:

* created `pyproject.toml` with `src` layout, `uv` configuration, and development dependency groups;
* generated `uv.lock` with tooling-only dependencies (`ruff`, `basedpyright`, `pytest`);
* created `src/knowledge_assistant/` package skeleton aligned with `docs/ARCHITECTURE.md`;
* configured ruff, basedpyright, and pytest;
* added `tests/unit/`, `tests/integration/`, and `tests/smoke/` layout with package import smoke tests;
* documented setup and validation workflow in `README.md`.

Bootstrap validation exception is superseded. All commits must pass the standard quality commands.

---

## 2026-06-21 — Domain Models

**Plan:** [03-domain-models.md](plans/completed/03-domain-models.md)

Established the shared domain model foundation in `knowledge_assistant.core`:

* implemented frozen dataclass domain types for documents, chunks, source attribution, retrieval, and indexing;
* defined `DocumentId` and `ChunkId` as `NewType` identifiers;
* implemented `IndexingSourceKind` and `ApprovalStatus` as stdlib enums;
* added `__post_init__` validation for all domain invariants;
* exported public API from `core/__init__.py`;
* added unit tests in `tests/unit/core/` covering construction, validation, and immutability;
* recorded ADR-001 in `docs/DECISIONS.md`;
* documented core domain layer in `docs/ARCHITECTURE.md`.

---

## 2026-06-21 — Storage Layer

**Plan:** [04-storage-layer.md](plans/completed/04-storage-layer.md)

Established the Qdrant storage boundary in `knowledge_assistant.storage`:

* defined `VectorStore` protocol with five methods (no `search_sparse`);
* implemented `QdrantVectorStore` with named `dense` and `sparse` vectors;
* added `ChunkUpsertItem`, `SparseVector`, and payload mapping for nine-field chunk payloads;
* added `StorageSettings` and `create_qdrant_vector_store` factory;
* added storage-specific exception types;
* added `qdrant-client` runtime dependency;
* added unit tests in `tests/unit/storage/` and integration tests with in-memory Qdrant;
* recorded ADR-002 through ADR-006 in `docs/DECISIONS.md`;
* documented storage layer boundary in `docs/ARCHITECTURE.md`.
