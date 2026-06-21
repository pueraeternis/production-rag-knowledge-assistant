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

---

## 2026-06-21 — Indexing Pipeline

**Plan:** [05-indexing-pipeline.md](plans/completed/05-indexing-pipeline.md)

Established the indexing layer in `knowledge_assistant.indexing`:

* implemented local file discovery for `.md` and `.txt` sources;
* added LlamaIndex adapter confined to `llamaindex_adapter.py` with line attribution from original text;
* implemented deterministic UUID5 `DocumentId` and `ChunkId` generation;
* defined `EmbeddingProvider` protocol with `StubEmbeddingProvider` development stub;
* added constant sparse vector placeholder for storage schema compliance;
* implemented `IndexingPipeline` with `preview_indexing` and `index_documents` (including rebuild flow);
* added `llama-index-core` and `llama-index-readers-file` runtime dependencies;
* added unit tests in `tests/unit/indexing/` and integration tests in `tests/integration/indexing/`;
* recorded ADR-007 through ADR-013 in `docs/DECISIONS.md`;
* documented indexing layer boundary in `docs/ARCHITECTURE.md`.

**Revision (post-review):** overlap-aware line attribution; `ChunkingError` for splitter failures; empty-directory `index_documents` storage no-op; LlamaIndex `SimpleDirectoryReader` owns loading with raw on-disk text as attribution mirror only.

---

## 2026-06-21 — Dense Retrieval

**Plan:** [06-dense-retrieval.md](plans/completed/06-dense-retrieval.md)

Established the dense retrieval path in `knowledge_assistant.retrieval`:

* implemented `DenseRetriever` orchestrating query embedding and `VectorStore.search_dense`;
* defined retrieval-local `QueryEmbeddingProvider` protocol separate from indexing `EmbeddingProvider`;
* added `StubQueryEmbeddingProvider` (hash-based, deterministic, L2-normalized, default dimension 1024);
* added `DenseRetrievalSettings` with `dense_vector_size` validation;
* added retrieval-specific exception types;
* added unit tests in `tests/unit/retrieval/` and integration tests with fake `VectorStore` in `tests/integration/retrieval/`;
* recorded ADR-014 through ADR-016 in `docs/DECISIONS.md`;
* documented retrieval layer dense path in `docs/ARCHITECTURE.md`.
