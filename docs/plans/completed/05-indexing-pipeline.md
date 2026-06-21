# Plan 05 — Indexing Pipeline

**Status:** Completed

**Created:** 2026-06-21

**Roadmap:** Phase 3 — Storage and Indexing

**Depends on:** [Plan 04 — Storage Layer](../completed/04-storage-layer.md)

---

## Post-Completion Revision (2026-06-21)

Review follow-up clarifications applied after initial implementation:

* **Chunking ownership:** LlamaIndex `SentenceSplitter` owns chunk boundaries; raw `Path.read_text` is an attribution mirror only (title, section headings, `LineRange`).
* **Loading ownership:** LlamaIndex `SimpleDirectoryReader` owns document loading; exactly one LlamaIndex document per input file (zero or multiple → `DocumentLoadError`).
* **Overlap-aware attribution:** chunk offset lookup uses overlap-aware `search_from` advancement and retry from `previous_end_char - chunk_overlap`.
* **Exceptions:** splitter failures and empty chunk results raise `ChunkingError`; file read failures remain `DocumentLoadError`.
* **Empty discovery:** `index_documents` is a storage no-op when discovery returns zero files (no create/delete/upsert).

---

## Objective

Build the indexing layer that turns local documents into stored chunks in `VectorStore`.

```text
local file/directory
    ↓
LlamaIndex loading/chunking
    ↓
project domain models
    ↓
EmbeddingProvider
    ↓
VectorStore.upsert_chunks
```

After this plan is complete, the indexing workflow can:

* preview local indexing operations;
* load supported local documents;
* split documents into chunks;
* preserve source attribution metadata;
* generate deterministic UUID-compatible document and chunk IDs;
* generate dense and sparse vectors through an embedding boundary;
* upsert chunks into `VectorStore`.

The indexing layer depends on `VectorStore`, not on `qdrant_client` or `StorageSettings`. LlamaIndex types must not leak outside `knowledge_assistant.indexing`.

**Dependency rule:** `indexing → VectorStore` protocol — not `indexing → StorageSettings`.

---

## Scope

This plan authorizes indexing-layer implementation only within `src/knowledge_assistant/indexing/` and associated tests.

### In Scope

* local file and directory discovery for `.md` and `.txt` sources;
* LlamaIndex document loading and chunking behind an internal adapter;
* translation from LlamaIndex nodes to core domain models (`Document`, `DocumentMetadata`, `DocumentContent`, `Chunk`, `ChunkMetadata`, `LineRange`);
* deterministic UUID5-based `DocumentId` and `ChunkId` generation;
* `EmbeddingProvider` protocol and `StubEmbeddingProvider` development stub;
* constant sparse vector placeholder generation;
* `IndexingPipeline` with `preview_indexing` and `index_documents`;
* optional full rebuild via `delete_collection` → `create_collection` → `upsert_chunks`;
* `IndexingSettings` configuration;
* indexing-specific exception types;
* unit tests for discovery, adapter mapping, IDs, embeddings, and pipeline orchestration;
* integration tests using fake `VectorStore` or the existing in-memory Qdrant pattern from Plan 04;
* runtime dependency on LlamaIndex packages required for loading and chunking only;
* ADR entries for indexing architecture decisions;
* brief `docs/ARCHITECTURE.md` update for the indexing layer.

---

## Non-Scope

This plan does **not** authorize:

* URL-based indexing (`IndexingSourceKind.DOCUMENT_URL`, `IndexingSourceKind.DIRECTORY_URL`);
* PDF, DOCX, HTML, web crawling, or binary document parsing;
* real BAAI/bge-m3 embedding integration;
* BM25, sparse retrieval, BGE-M3 lexical vectors, or sparse search;
* `torch`, `sentence-transformers`, `transformers`, or other model runtime dependencies;
* interactive approval prompts inside the indexing service;
* MCP server or MCP client implementation;
* LangGraph agent implementation;
* retrieval implementation (dense, sparse, fusion, reranking);
* CLI behavior;
* Docker Compose or production Qdrant deployment;
* smoke tests against a live Qdrant service;
* direct `qdrant_client` imports in `knowledge_assistant.indexing`;
* `StorageSettings` or other storage configuration types in `knowledge_assistant.indexing` (indexing depends on `VectorStore` protocol only);
* changes to `knowledge_assistant.core` domain models;
* changes to `VectorStore` protocol or storage payload schema;
* partial document deletion or incremental index updates beyond full rebuild;
* exception hierarchy rooted at `AppError` (deferred to a future plan).

---

## Architectural Decisions

The following decisions are **accepted** for this plan. Implementation must follow them; they are not open for reinterpretation during implementation.

### ADR-007 — LlamaIndex Containment in Indexing Layer

**Status:** Accepted (established by this plan)

#### Context

Document loading and chunking require a mature ingestion library. The project stack includes LlamaIndex, but external layers must remain independent from LlamaIndex types and metadata schemas.

#### Decision

* Use LlamaIndex for document loading and chunking inside `knowledge_assistant.indexing` only.
* Confine all LlamaIndex imports to `llamaindex_adapter.py` (and optionally `documents.py` if file I/O helpers are needed without LlamaIndex types in public modules).
* Translate LlamaIndex `Document` / `BaseNode` outputs into core domain models before they leave the indexing package.
* Do not export LlamaIndex types from `indexing/__init__.py`.
* `knowledge_assistant.core`, `storage`, `retrieval`, `mcp_server`, `agent`, and `llm` must not import LlamaIndex.

#### Consequences

* LlamaIndex API changes are localized to the adapter module.
* Higher layers work exclusively with project domain types.
* Tests can mock or bypass the adapter while still validating pipeline orchestration.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Custom loaders/parsers without LlamaIndex | Reinvents chunking; contradicts project technology stack |
| LlamaIndex types in core domain models | Violates implementation-agnostic core layer per ADR-001 |
| LlamaIndex types in MCP contracts | Couples knowledge access API to ingestion library |

---

### ADR-008 — Deterministic UUID5 ID Generation

**Status:** Accepted (established by this plan)

#### Context

Plan 04 requires `ChunkId` values to be valid UUID strings for Qdrant point ID conversion. IDs must be stable across re-indexing runs so the same source content produces the same identifiers.

#### Decision

* The indexing layer owns ID generation; storage does not generate IDs.
* Use `uuid.uuid5` exclusively. Do not use `uuid.uuid4` for document or chunk IDs.
* Define a namespace constant in `indexing/ids.py`:

```python
INDEXING_ID_NAMESPACE = uuid.UUID("a3f2c8e1-4b5d-6e7f-8901-23456789abcd")
```

* **DocumentId:** `UUID5(INDEXING_ID_NAMESPACE, normalized_source_path)` as a string.
* **ChunkId:** `UUID5(INDEXING_ID_NAMESPACE, f"{document_id}|{chunk_index}|{text_digest}")` as a string, where `text_digest` is the lowercase hex SHA-256 digest of the chunk text after stripping leading/trailing whitespace.
* **Path normalization:** resolve to absolute path, normalize separators to forward slashes, and use the normalized string as the UUID5 name input. Store the normalized path in `DocumentMetadata.path`.
* Validate generated IDs are non-empty UUID strings before use.

#### Consequences

* Re-indexing the same file produces identical document and chunk IDs when source text and chunking configuration are unchanged.
* Content changes produce new chunk IDs for affected chunks.
* **Changing chunking configuration, splitter behavior, or chunk text invalidates previously generated `ChunkId` values and requires a full reindex.** This is acceptable and intentional.
* `ChunkId` depends on `DocumentId`, `chunk_index`, and a hash of chunk text. Therefore changes to `chunk_size`, `chunk_overlap`, LlamaIndex splitter behavior, or source text can change chunk boundaries, indices, or text — producing different IDs.
* IDs satisfy Plan 04 `InvalidChunkIdError` prevention at upsert time.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Random UUID4 per index run | Breaks idempotent re-indexing; complicates deduplication |
| Sequential integer IDs | Not UUID-compatible with Qdrant point ID mapping |
| Content-only hash without document scope | Collisions across different documents with identical chunk text |

---

### ADR-009 — EmbeddingProvider Boundary in Indexing Layer

**Status:** Accepted (established by this plan)

#### Context

Storage receives pre-computed vectors and must not generate embeddings (ADR-006). Real BGE-M3 integration is deferred, but the indexing layer needs a stable embedding contract for write-path vector generation.

#### Decision

* Define `EmbeddingProvider` as a `typing.Protocol` in `indexing/embeddings.py`.
* Protocol surface:

```python
EmbeddingVector = tuple[float, ...]

class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        """Return one dense embedding per input text, in the same order."""
        ...
```

* Provide `StubEmbeddingProvider` for tests and Plan 05 development: hash-based, fixed dimension, no model runtime. The name signals a testing/development stub, not a production embedding model.
* `IndexingSettings.dense_vector_size` defaults to `1024`. Callers must configure indexing and storage consistently. Storage independently validates vector dimensions at upsert time.
* Real BAAI/bge-m3 write-path implementation is deferred to a future plan; it will implement the same `EmbeddingProvider` protocol.
* Write-path embedding ownership is further specified in ADR-013.

#### Consequences

* Indexing tests run without GPU or model downloads.
* Future BGE-M3 indexing integration is a drop-in provider replacement.
* Query-path embedding ownership belongs to retrieval (ADR-013); Plan 06 defines that boundary.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Embedding generation in storage | Violates ADR-006 |
| Shared `llm/` embedding module | LLM boundary is for model inference calls; embeddings are retrieval/indexing concerns |
| Hardcoded vectors in pipeline | No reusable contract for future BGE-M3 integration |

---

### ADR-010 — Sparse Vector Placeholder Until Sparse Retrieval

**Status:** Accepted (established by this plan)

#### Context

Plan 04 collection schema requires both dense and sparse named vectors on every upsert (ADR-004). Real BGE-M3 sparse vectors and BM25 retrieval are deferred to Plan 07.

#### Decision

* Plan 05 attaches a **constant sparse vector placeholder** to every chunk at indexing time.
* Placeholder value (pure function in `indexing/embeddings.py`):

```python
SparseVector(indices=(0,), values=(1.0,))
```

* The placeholder is valid per storage `SparseVector` validation rules, deterministic, and carries no hashing logic or pseudo-lexical representation.
* Document clearly as a temporary stand-in until Plan 07 provides real sparse vectors.
* Do not implement BM25, BGE-M3 lexical encoding, or sparse search.

#### Consequences

* Upserts satisfy storage schema without model dependencies or placeholder complexity.
* Plan 07 replaces the constant with real sparse vectors; full reindex will be required.
* Dense retrieval in Plan 06 is unaffected.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Digest-derived pseudo-sparse vectors | Implies lexical structure that does not exist; unnecessary complexity |
| Empty sparse vectors | Zero-length edge cases; may not exercise storage sparse path |
| Random sparse vectors per run | Non-deterministic; breaks reproducibility |
| Defer sparse slot entirely | Would require storage schema change contradicting ADR-004 |

---

### ADR-011 — Local File Indexing Scope

**Status:** Accepted (established by this plan)

#### Context

The domain model defines four `IndexingSourceKind` values (Plan 03). The roadmap defers URL indexing to MCP plans. Plan 05 must bound ingestion scope explicitly.

#### Decision

* Plan 05 supports only:
  * `IndexingSourceKind.FILE` — single local file;
  * `IndexingSourceKind.DIRECTORY` — local directory with optional recursive walk.
* Supported file extensions: `.md`, `.txt` (case-insensitive).
* Reject `IndexingSourceKind.DOCUMENT_URL` and `IndexingSourceKind.DIRECTORY_URL` with `UnsupportedSourceKindError`.
* Reject unsupported extensions with `UnsupportedFileTypeError` (skip silently during directory walks or raise on explicit single-file sources — see Implementation Steps).
* `DocumentMetadata.source_uri` remains `None` for local files in Plan 05.

#### Consequences

* MCP URL indexing (Plan 10) will extend discovery without changing core domain enums.
* Indexing pipeline has a clear, testable local-filesystem boundary.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Implement URL fetching now | Out of Phase 3 scope; MCP plan owns remote sources |
| Support all text-like extensions | Expands parsing scope without plan authorization |
| Store `file://` URI in `source_uri` | Unnecessary for local demo; deferred |

---

### ADR-012 — Human Approval Enforced by Callers

**Status:** Accepted (established by this plan)

#### Context

`PROJECT.md` requires user confirmation before modifying the index. Plan 04 exposes destructive storage primitives; orchestration must not bypass the approval boundary.

#### Decision

* `IndexingPipeline` may implement `preview_indexing(...)` and `index_documents(...)`.
* The indexing service must **not** prompt the user or read interactive input.
* `index_documents(..., rebuild=True)` performs `delete_collection` → `create_collection` → `upsert_chunks`; the **caller** (future CLI, MCP, or agent) must obtain approval before invoking rebuild.
* `preview_indexing` returns `IndexingPreview` with `replaces_existing` reflecting whether the target collection currently exists and rebuild would be required.
* `ApprovalStatus` remains a core domain type; indexing does not transition approval state.

#### Consequences

* Indexing layer is reusable in automated tests without stdin mocking.
* MCP and CLI plans own interactive approval UX.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Built-in `input()` approval prompt | Couples library to interactive CLI; untestable in CI |
| Silent rebuild without preview | Violates human-in-the-loop requirement |

---

### ADR-013 — Embedding Boundary Ownership

**Status:** Accepted (established by this plan)

#### Context

Embedding generation appears on both the indexing write path and the retrieval query path. Without explicit ownership, Plan 06 retrieval design could duplicate indexing contracts, push embedding into storage, or blur layer boundaries.

#### Decision

```text
Indexing owns write-path embeddings.
Retrieval owns query-path embeddings.
Storage owns neither.
```

* **Indexing** generates embeddings for document chunks before `VectorStore.upsert_chunks`.
* **Retrieval** generates embeddings for user queries before `VectorStore.search_dense` (Plan 06).
* **Storage** receives pre-computed vectors only and never generates embeddings (reinforces ADR-006).
* Future BAAI/bge-m3 integration for indexing and retrieval must implement **compatible provider contracts** within their respective layers (same vector dimension and normalization expectations; separate protocol modules per layer are acceptable).
* The `llm/` package is not the embedding owner for either path.

#### Consequences

* Plan 06 can define a retrieval-side query embedding boundary without ambiguity.
* Storage remains a passive vector store.
* Preview and index flows have a clear boundary: embedding runs only on the index path (see Preview Requirements).

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Shared embedding module used by indexing and retrieval | Couples read and write paths; different call patterns and lifecycle |
| Storage generates query embeddings | Violates ADR-006 and component boundaries |
| Single global `EmbeddingProvider` in `core/` | Pollutes domain layer with infrastructure concerns per ADR-001 |

---

## Module Layout

Flat package structure under `src/knowledge_assistant/indexing/`:

```text
src/knowledge_assistant/indexing/
    __init__.py              # public exports only (no LlamaIndex types)
    config.py                # IndexingSettings
    documents.py             # local file discovery and path normalization
    embeddings.py            # EmbeddingProvider, StubEmbeddingProvider, sparse placeholder
    exceptions.py            # indexing-specific errors
    ids.py                   # INDEXING_ID_NAMESPACE, document_id_for_path, chunk_id_for_chunk
    llamaindex_adapter.py    # LlamaIndex load/chunk → domain models (only LlamaIndex imports here)
    pipeline.py              # IndexingPipeline orchestration
```

Do not create deep subpackages (`indexing/loaders/`, `indexing/utils/`).

### Public API (`indexing/__init__.py`)

Export intentionally:

* `IndexingSettings`
* `EmbeddingProvider`
* `StubEmbeddingProvider`
* `IndexingPipeline`
* Indexing exceptions used by callers

Do **not** export:

* LlamaIndex types;
* internal adapter functions;
* `INDEXING_ID_NAMESPACE` (internal; test via behavior).

---

## Indexing Flow

### Preview Flow

```text
tuple[IndexingSource, ...]
    ↓
validate supported kinds (FILE, DIRECTORY only)
    ↓
discover local files (.md, .txt)
    ↓
for each file: load + chunk (no embedding, no storage write)
    ↓
aggregate document_count, chunk_count
    ↓
check vector_store.collection_exists() → replaces_existing
    ↓
IndexingPreview
```

### Preview Requirements

`preview_indexing(...)` must:

* discover files;
* load documents;
* chunk documents;
* count documents and chunks;
* determine `replaces_existing` (via `vector_store.collection_exists()` only).

`preview_indexing(...)` must **not**:

* generate embeddings;
* generate sparse vectors;
* build `ChunkUpsertItem`;
* call `VectorStore.upsert_chunks`;
* call `VectorStore.create_collection`;
* call `VectorStore.delete_collection`;
* invoke `EmbeddingProvider.embed_texts`.

**Reason:** Preview must remain inexpensive even after real BGE-M3 integration. Approval UX depends on fast, side-effect-free estimates.

The only permitted `VectorStore` call during preview is `collection_exists()` for `replaces_existing`.

### Index Flow

```text
tuple[IndexingSource, ...]
    ↓
validate supported kinds
    ↓
discover local files
    ↓
for each file:
    load via LlamaIndex adapter
    chunk via LlamaIndex adapter
    map to Document + tuple[Chunk, ...]
    generate DocumentId, ChunkIds
    embed chunk texts via EmbeddingProvider
    build SparseVector placeholders
    assemble ChunkUpsertItem values
    ↓
if rebuild:
    vector_store.delete_collection()
    vector_store.create_collection()
elif not vector_store.collection_exists():
    vector_store.create_collection()
    ↓
vector_store.upsert_chunks(all_items)
```

**Rebuild contract:** When `rebuild=True`, the pipeline calls `delete_collection()`, then `create_collection()`, then `upsert_chunks(...)`. The caller is responsible for invoking rebuild only after human approval.

**Non-rebuild:** When `rebuild=False` and the collection does not exist, create it before upsert. When the collection exists, upsert into the existing collection (idempotent upsert by chunk ID).

---

## LlamaIndex Adapter Design

**Module:** `indexing/llamaindex_adapter.py`

All LlamaIndex imports are confined to this module.

### Loading

* Use LlamaIndex file reader utilities appropriate for `.md` and `.txt` (e.g. `SimpleDirectoryReader` with `input_files` for single files, or equivalent targeted loading API).
* Read and retain the **original document text** as a single string before chunking. This string is the source of truth for line attribution.
* Return an internal adapter result type (private to indexing) or directly produce domain objects — do not expose LlamaIndex `Document` to callers.

### Chunking

* Use LlamaIndex `SentenceSplitter` (or `TokenTextSplitter` with character-based sizing) configured from `IndexingSettings`:
  * `chunk_size` (default `1024` characters)
  * `chunk_overlap` (default `128` characters)
* Chunking operates on loaded document text. LlamaIndex produces chunk **text** and ordering; it is **not** authoritative for line numbers.
* Each chunk must map to:
  * `Chunk.text` — non-empty stripped text;
  * `ChunkMetadata.chunk_index` — zero-based order within document;
  * `ChunkMetadata.line_range` — 1-based inclusive line span in the source file;
  * `ChunkMetadata.section_title` — nearest preceding Markdown heading when determinable, else `""`;
  * `ChunkMetadata.document_id` — generated `DocumentId`.

### Adapter Functions

```python
def load_and_chunk_file(
    *,
    file_path: str,
    document_id: DocumentId,
    settings: IndexingSettings,
) -> tuple[DocumentMetadata, tuple[Chunk, ...]]:
    """Load one local file, chunk it, return metadata and domain chunks."""
    ...
```

Adapter responsibilities:

| Input | Output |
| ----- | ------ |
| Local file path | `DocumentMetadata` (title, path, `source_uri=None`) |
| Chunked nodes | `tuple[Chunk, ...]` with IDs, line ranges, section titles |

### LlamaIndex Metadata Mapping

* **Title:** filename stem (without extension), unless the document starts with a single `# Heading` line — then prefer that heading text stripped of `#` markers.
* **Path:** normalized absolute path as `str` (forward slashes).
* **Section title:** for `.md` files, track the most recent ATX heading (`#` through `######`) before the chunk start offset in the **original document text**; empty string for `.txt` or when no heading precedes the chunk.

### Line Attribution (Critical)

Source line ranges are a first-class requirement per `PROJECT.md`. LlamaIndex chunking must **not** be treated as authoritative for line attribution.

**Rules:**

1. **Original document text is the source of truth.** Keep the full file content as read from disk.
2. **Locate each chunk in the original text** by searching for the chunk string (or a normalized form) within the original document content. Record `start_char` and `end_char` offsets.
3. **Derive `LineRange` from offsets** by mapping character positions to 1-based line numbers in the original text (build a line-start offset table once per document).
4. **Do not rely on LlamaIndex node metadata** for line numbers. If LlamaIndex exposes start/end offsets or line fields, treat them as hints only; recompute from original text when possible.
5. **If offsets cannot be resolved** (e.g. ambiguous duplicate chunk text), prefer the first matching occurrence and document the behavior in tests; `(1, 1)` fallback is a last resort and must be covered by an explicit test if used.

Implement line attribution in indexing code (adapter or a dedicated pure helper), independent of LlamaIndex internals.

---

## Source Attribution Strategy

Source attribution fields required by ADR-005 must be populated at indexing time:

| Domain field | Indexing source |
| ------------ | --------------- |
| `DocumentMetadata.title` | filename stem or first Markdown H1 |
| `DocumentMetadata.path` | normalized file path |
| `DocumentMetadata.source_uri` | `None` (local files) |
| `ChunkMetadata.section_title` | nearest preceding Markdown heading in original text |
| `ChunkMetadata.line_range` | character offsets mapped to 1-based lines in original text |
| `ChunkMetadata.chunk_index` | zero-based chunk order |
| `Chunk.text` | chunk body text from LlamaIndex splitter |

`SourceReference` is not constructed during indexing; storage payload mapping (Plan 04) denormalizes the fields needed for later reconstruction.

**Attribution pipeline:**

```text
original file text (source of truth)
    ↓
LlamaIndex chunk text + chunk_index
    ↓
locate chunk in original text → char offsets
    ↓
char offsets → LineRange (1-based)
    ↓
nearest preceding Markdown heading → section_title
```

Indexing tests must verify:

* `LineRange` satisfies `start_line >= 1` and `end_line >= start_line`;
* **fixture documents with known line boundaries** produce exact expected `LineRange` values (primary attribution test strategy);
* Markdown files with headings populate `section_title` for chunks below those headings;
* plain `.txt` files use empty `section_title`;
* line attribution does not depend on LlamaIndex node metadata fields.

---

## ID Generation Strategy

**Module:** `indexing/ids.py`

```python
INDEXING_ID_NAMESPACE = uuid.UUID("a3f2c8e1-4b5d-6e7f-8901-23456789abcd")

def normalize_source_path(path: str) -> str: ...

def document_id_for_path(path: str) -> DocumentId: ...

def chunk_id_for_chunk(
    *,
    document_id: DocumentId,
    chunk_index: int,
    text: str,
) -> ChunkId: ...
```

**`normalize_source_path`:**

* Accept `str` path (indexing uses `pathlib` internally for resolution only).
* Resolve to absolute path.
* Convert to POSIX-style string (`/` separators).

**`document_id_for_path`:**

* `str(uuid.uuid5(INDEXING_ID_NAMESPACE, normalize_source_path(path)))`

**`chunk_id_for_chunk`:**

* `text_digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()`
* `name = f"{document_id}|{chunk_index}|{text_digest}"`
* `str(uuid.uuid5(INDEXING_ID_NAMESPACE, name))`

**Invariants (tested):**

* Same path → same `DocumentId`.
* Same document, index, text, and chunking configuration → same `ChunkId`.
* Different text or index → different `ChunkId`.
* All generated IDs pass `uuid.UUID(value)` parsing.

**Stability note:** `ChunkId` is stable only while `DocumentId`, `chunk_index`, and chunk text remain unchanged. Altering `IndexingSettings.chunk_size`, `chunk_overlap`, splitter implementation, or source document text may change chunk boundaries and IDs. A full reindex (with caller approval) is the recovery path.

---

## Embedding Boundary

**Module:** `indexing/embeddings.py`

```python
EmbeddingVector = tuple[float, ...]

class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        ...

@dataclass(frozen=True, slots=True)
class StubEmbeddingProvider:
    dimension: int = 1024

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[EmbeddingVector, ...]:
        ...
```

**`StubEmbeddingProvider` algorithm:**

1. For each text, compute SHA-256 digest.
2. Expand digest bytes deterministically to `dimension` float components in `[-1.0, 1.0]`.
3. L2-normalize the vector for cosine distance compatibility.
4. Return as `tuple[float, ...]` with length exactly `dimension`.

**Pipeline usage (index path only):**

* Batch all chunk texts from all discovered documents during `index_documents` only — not during `preview_indexing`.
* Call `embed_texts` once per pipeline run (or in document batches — implementation choice).
* Verify `len(dense_vector) == settings.dense_vector_size` (from `IndexingSettings`) before building `ChunkUpsertItem`.

**Dimension alignment:** `IndexingSettings.dense_vector_size` defaults to `1024` (planned BGE-M3 output dimension). Callers must configure indexing and storage consistently. Storage independently validates vector dimensions at upsert; indexing does not read `StorageSettings`.

Write-path ownership per ADR-013: indexing generates chunk embeddings; retrieval and storage do not.

---

## Sparse Vector Placeholder Strategy

**Function:** `sparse_placeholder_vector() -> SparseVector` (in `embeddings.py`)

Returns a constant placeholder for every chunk (ADR-010):

```python
SparseVector(indices=(0,), values=(1.0,))
```

* Valid per storage `SparseVector` validation (`indices` unique, matching lengths, all `indices >= 0`).
* Deterministic: same value for every chunk; no hashing or text input.
* Clearly documented as a temporary stand-in until Plan 07 real sparse vectors.
* Generated only on the index path (`index_documents`), not during preview.

Pipeline attaches one placeholder per `ChunkUpsertItem`.

---

## Indexing Service API

**Module:** `indexing/pipeline.py`

```python
@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Summary returned after a successful index run."""

    sources: tuple[IndexingSource, ...]
    document_count: int
    chunk_count: int
    upserted_count: int
    rebuilt: bool

class IndexingPipeline:
    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        settings: IndexingSettings,
    ) -> None: ...

    def preview_indexing(
        self,
        sources: tuple[IndexingSource, ...],
    ) -> IndexingPreview: ...

    def index_documents(
        self,
        sources: tuple[IndexingSource, ...],
        *,
        rebuild: bool = False,
    ) -> IndexingResult: ...
```

**`preview_indexing`:**

* Follows Preview Requirements (discovery, load, chunk, count, `replaces_existing` only).
* Sets `replaces_existing` to `True` when `vector_store.collection_exists()` is `True` (indicating an index rebuild would replace data if caller chooses `rebuild=True`).
* Returns core `IndexingPreview` (no new core types).
* Must not invoke `EmbeddingProvider` or produce vectors/`ChunkUpsertItem`.

**`index_documents`:**

* Performs full index flow (see Indexing Flow).
* Does not prompt for approval.
* Raises indexing exceptions on validation failures.
* Returns `IndexingResult` (indexing-layer type, not core).

**`IndexingSettings` (`config.py`):**

```python
@dataclass(frozen=True, slots=True)
class IndexingSettings:
    chunk_size: int = 1024
    chunk_overlap: int = 128
    dense_vector_size: int = 1024
    supported_extensions: tuple[str, ...] = (".md", ".txt")
```

Validation: `chunk_size > 0`, `chunk_overlap >= 0`, `chunk_overlap < chunk_size`, `dense_vector_size > 0`.

---

## Document Discovery

**Module:** `indexing/documents.py`

```python
def discover_files(
    source: IndexingSource,
    *,
    settings: IndexingSettings,
) -> tuple[str, ...]:
    """Return normalized absolute paths of supported files for one source."""
    ...
```

| `IndexingSourceKind` | Behavior |
| -------------------- | -------- |
| `FILE` | Resolve path; raise `UnsupportedFileTypeError` if extension not supported; return single-element tuple |
| `DIRECTORY` | Walk directory; if `recursive=True`, include subdirectories; collect supported extensions only; sort paths for deterministic ordering |
| `DOCUMENT_URL` | Raise `UnsupportedSourceKindError` |
| `DIRECTORY_URL` | Raise `UnsupportedSourceKindError` |

Raise `SourceNotFoundError` when file or directory path does not exist.

Directory walks **skip** unsupported extensions silently (do not fail the entire directory for one `.pdf`).

---

## Exception Hierarchy (indexing-local)

```python
class IndexingError(Exception): ...
class UnsupportedSourceKindError(IndexingError): ...
class UnsupportedFileTypeError(IndexingError): ...
class SourceNotFoundError(IndexingError): ...
class DocumentLoadError(IndexingError): ...
class ChunkingError(IndexingError): ...
class EmbeddingDimensionError(IndexingError): ...
```

Root `AppError` integration is deferred.

---

## Testing Strategy

| Level | Location | What is tested | VectorStore usage |
| ----- | -------- | -------------- | ----------------- |
| Unit | `tests/unit/indexing/` | discovery, path normalization, ID generation, adapter mapping, embeddings, sparse placeholder, `ChunkUpsertItem` assembly | None (mock adapter where needed) |
| Integration | `tests/integration/indexing/` | full `IndexingPipeline` with fake or in-memory `VectorStore` | Fake protocol implementation or Plan 04 in-memory Qdrant fixture |

### Unit Tests (required)

* local file discovery returns single supported file;
* recursive directory discovery finds nested `.md` and `.txt`;
* non-recursive directory discovery excludes nested files;
* unsupported source kind (`DOCUMENT_URL`, `DIRECTORY_URL`) raises `UnsupportedSourceKindError`;
* unsupported extension on explicit `FILE` source raises `UnsupportedFileTypeError`;
* directory walk skips unsupported extensions without error;
* LlamaIndex adapter maps output to domain `Chunk` and `DocumentMetadata`;
* deterministic `DocumentId` generation from path;
* deterministic `ChunkId` generation from document ID, index, and text;
* chunk metadata includes valid `LineRange`;
* Markdown heading extraction populates `section_title` where possible;
* `StubEmbeddingProvider` returns vectors of expected dimension;
* `sparse_placeholder_vector()` returns `SparseVector(indices=(0,), values=(1.0,))`;
* pipeline builds `ChunkUpsertItem` with correct fields (index path only);
* line attribution fixtures produce exact expected `LineRange` values;
* `knowledge_assistant.indexing` modules do not import `qdrant_client` or `knowledge_assistant.storage.config` / `StorageSettings` (static import check or grep-based test).

### Integration Tests (required)

* pipeline calls `vector_store.upsert_chunks` with expected item count;
* rebuild flow calls `delete_collection`, then `create_collection`, then `upsert_chunks` in order (track call order with fake store);
* preview does not call `upsert_chunks`, `create_collection`, or `delete_collection`;
* preview does not invoke `EmbeddingProvider.embed_texts`;
* preview does not build `ChunkUpsertItem` or sparse vectors;
* preview may call `collection_exists` only;
* index into empty store creates collection then upserts;
* re-indexing same content produces identical chunk IDs.

### Test Fixtures

* `tests/unit/indexing/fixtures/` — sample `.md` and `.txt` files with headings and **known, documented line ranges** for chunk attribution assertions.
* `tests/integration/indexing/conftest.py` — `FakeVectorStore` recording method calls and optionally wrapping in-memory Qdrant from Plan 04.

**Not in scope:** Docker Qdrant; real BGE-M3 model; URL fetching; MCP tests.

---

## Dependencies

Add runtime dependencies required for LlamaIndex loading and chunking only. Minimal set (implementation may pin compatible versions):

```toml
dependencies = [
    "qdrant-client>=1.12",
    "llama-index-core>=0.12",
]
```

Add a file-reader package if not included in core (e.g. `llama-index-readers-file`) when implementation requires it.

Do **not** add:

* `torch`
* `sentence-transformers`
* `transformers`
* `langgraph`
* `mcp`
* `openai`
* reranking libraries

Pin versions in `uv.lock` during implementation.

---

## Documentation Updates

During implementation, update:

* `docs/DECISIONS.md` — transcribe ADR-007 through ADR-013 from this plan;
* `docs/ARCHITECTURE.md` — add Indexing Layer section: module layout, dependency flow (`indexing → storage`), LlamaIndex containment, embedding boundary ownership (ADR-013: indexing write-path, retrieval query-path, storage neither), ID ownership;
* `docs/PROGRESS.md` — record Plan 05 completion.

Do not update `docs/plans/backlog/ROADMAP.md` (informational only).

---

## Acceptance Criteria

- [x] `IndexingPipeline` implements `preview_indexing` and `index_documents`
- [x] `preview_indexing` returns `IndexingPreview` without embedding, vector generation, or storage writes
- [x] `preview_indexing` does not call `upsert_chunks`, `create_collection`, or `delete_collection`
- [x] `preview_indexing` does not invoke `EmbeddingProvider.embed_texts`
- [x] `preview_indexing` may call `collection_exists` only (for `replaces_existing`)
- [x] `index_documents` upserts chunks via `VectorStore.upsert_chunks`
- [x] `index_documents(rebuild=True)` calls `delete_collection`, `create_collection`, `upsert_chunks` in order
- [x] Indexing service does not prompt for user approval
- [x] Only `IndexingSourceKind.FILE` and `IndexingSourceKind.DIRECTORY` are supported
- [x] Only `.md` and `.txt` files are indexed
- [x] LlamaIndex imports exist only in `llamaindex_adapter.py`
- [x] No LlamaIndex types exported from `indexing/__init__.py`
- [x] Adapter produces core `Document`, `DocumentMetadata`, `Chunk`, `ChunkMetadata`, `LineRange`
- [x] `DocumentId` and `ChunkId` generated via UUID5 (no UUID4)
- [x] Generated `ChunkId` values are valid UUID strings
- [x] `EmbeddingProvider` protocol defined in `indexing/embeddings.py`
- [x] `StubEmbeddingProvider` implemented as development stub (no model runtime)
- [x] Sparse placeholder is `SparseVector(indices=(0,), values=(1.0,))` on every chunk (index path only)
- [x] Line attribution derived from original document text, not LlamaIndex node metadata
- [x] Fixture tests verify exact `LineRange` values for known documents
- [x] `ChunkUpsertItem` values include `document_metadata`, dense vector, and sparse vector
- [x] Indexing layer depends on `VectorStore` protocol only; no `StorageSettings` import or reference in `knowledge_assistant.indexing`
- [x] No `qdrant_client` imports in `knowledge_assistant.indexing`
- [x] Unit tests exist in `tests/unit/indexing/`
- [x] Integration tests exist in `tests/integration/indexing/`
- [x] ADR-007 through ADR-013 transcribed into `docs/DECISIONS.md`
- [x] `docs/ARCHITECTURE.md` documents indexing layer boundary
- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes with zero errors on `src/knowledge_assistant/indexing/`
- [x] `uv run pytest` passes
- [x] `docs/PROGRESS.md` records plan completion

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| **Incorrect line attribution (highest technical risk)** | Original document text is source of truth; locate chunks by offset in original text; derive `LineRange` from char offsets; never trust LlamaIndex node line metadata; fixture tests with known line boundaries |
| Duplicate chunk text causes ambiguous offset lookup | Prefer first match; use fixture tests for ambiguous cases; document behavior |
| LlamaIndex version API drift | Pin package version; isolate usage in `llamaindex_adapter.py` |
| Chunk ID instability when chunking settings or splitter behavior change | Expected and intentional per ADR-008: `ChunkId` depends on `DocumentId`, `chunk_index`, and chunk text hash; changing `chunk_size`, `chunk_overlap`, splitter behavior, or source text invalidates prior IDs; full reindex with caller approval is the recovery path |
| Sparse placeholder unlike real BGE-M3 vectors | Explicit ADR-010 constant placeholder; Plan 07 replaces with real sparse encoding |
| `dense_vector_size` mismatch at upsert | Indexing validates against `IndexingSettings.dense_vector_size` before upsert; callers must configure indexing and storage consistently; storage independently rejects dimension mismatches |
| Preview accidentally runs embeddings after BGE-M3 integration | Explicit Preview Requirements; tests assert `embed_texts` not called during preview |
| Embedding ownership ambiguity with Plan 06 | ADR-013: indexing write-path, retrieval query-path, storage neither |
| Scope creep into URL indexing or MCP | Explicit non-scope; raise on unsupported source kinds |
| Accidental approval prompt in pipeline | Code review; integration tests without stdin |
| LlamaIndex types leak to storage or retrieval | Adapter boundary; no LlamaIndex exports; import lint test |

---

## Implementation Steps

1. **Transcribe ADRs** — record ADR-007 through ADR-013 from this plan in `docs/DECISIONS.md`.
2. **Add dependencies** — add LlamaIndex packages to `pyproject.toml`; run `uv lock`.
3. **Create `exceptions.py`** — define indexing exception types.
4. **Create `config.py`** — implement `IndexingSettings` with validation.
5. **Create `ids.py`** — implement path normalization and UUID5 ID functions.
6. **Create `documents.py`** — implement file discovery and unsupported kind/extension handling.
7. **Create `embeddings.py`** — implement `EmbeddingProvider`, `StubEmbeddingProvider`, and `sparse_placeholder_vector`.
8. **Create `llamaindex_adapter.py`** — implement load/chunk, domain mapping, section title extraction, and line attribution from original document text (not LlamaIndex metadata).
9. **Create `pipeline.py`** — implement `IndexingPipeline`, `IndexingResult`, preview and index flows, rebuild orchestration.
10. **Update `indexing/__init__.py`** — export public API only.
11. **Add unit tests** — create `tests/unit/indexing/` with fixtures for `.md` and `.txt` samples.
12. **Add integration tests** — create `tests/integration/indexing/` with `FakeVectorStore` and optional in-memory Qdrant.
13. **Add import guard tests** — verify no `qdrant_client` or `StorageSettings` references under `knowledge_assistant.indexing`.
14. **Update `docs/ARCHITECTURE.md`** — document indexing layer boundary and dependency flow.
15. **Run validation suite** — execute all four quality commands; fix issues until all pass.
16. **Update progress** — record completion in `docs/PROGRESS.md`.
17. **Verify non-scope compliance** — confirm no URL indexing, model runtime, MCP, retrieval, CLI, or approval prompts.

---

## Checklist

### Architectural Decisions (ADR-007 – ADR-013)

- [x] Transcribe ADR-007 (LlamaIndex Containment) into `docs/DECISIONS.md`
- [x] Transcribe ADR-008 (Deterministic UUID5 IDs) into `docs/DECISIONS.md`
- [x] Transcribe ADR-009 (EmbeddingProvider Boundary) into `docs/DECISIONS.md`
- [x] Transcribe ADR-010 (Sparse Placeholder) into `docs/DECISIONS.md`
- [x] Transcribe ADR-011 (Local File Scope) into `docs/DECISIONS.md`
- [x] Transcribe ADR-012 (Caller-Enforced Approval) into `docs/DECISIONS.md`
- [x] Transcribe ADR-013 (Embedding Boundary Ownership) into `docs/DECISIONS.md`

### Dependencies

- [x] Add LlamaIndex packages to `pyproject.toml`
- [x] Update `uv.lock`
- [x] Confirm no `torch`, `sentence-transformers`, `transformers`, or unauthorized dependencies

### Configuration and IDs

- [x] Create `indexing/config.py` with `IndexingSettings`
- [x] Create `indexing/ids.py` with `INDEXING_ID_NAMESPACE` and ID functions
- [x] Create `indexing/exceptions.py`

### Document Discovery

- [x] Create `indexing/documents.py`
- [x] Implement `FILE` source handling
- [x] Implement `DIRECTORY` recursive and non-recursive walks
- [x] Reject `DOCUMENT_URL` and `DIRECTORY_URL`
- [x] Filter `.md` and `.txt` only

### Embeddings

- [x] Create `indexing/embeddings.py`
- [x] Define `EmbeddingProvider` protocol
- [x] Implement `StubEmbeddingProvider`
- [x] Implement `sparse_placeholder_vector()` returning constant `SparseVector(indices=(0,), values=(1.0,))`

### LlamaIndex Adapter

- [x] Create `indexing/llamaindex_adapter.py` (sole LlamaIndex import site)
- [x] Load `.md` and `.txt` files
- [x] Chunk with configurable size and overlap
- [x] Map to `DocumentMetadata` and `Chunk` domain models
- [x] Extract Markdown `section_title` from headings
- [x] Compute `LineRange` from original document text offsets (not LlamaIndex metadata)

### Pipeline

- [x] Create `indexing/pipeline.py`
- [x] Implement `preview_indexing` → `IndexingPreview` per Preview Requirements (no embeddings)
- [x] Implement `index_documents` → `IndexingResult`
- [x] Build `ChunkUpsertItem` values with vectors and metadata
- [x] Implement rebuild flow (`delete_collection` → `create_collection` → `upsert_chunks`)
- [x] No interactive approval prompts

### Public API

- [x] Update `indexing/__init__.py` with intentional exports
- [x] No LlamaIndex types in public exports

### Unit Tests

- [x] Create `tests/unit/indexing/` package
- [x] Test file discovery (file, directory, recursive)
- [x] Test unsupported source kind rejection
- [x] Test unsupported extension handling
- [x] Test adapter domain mapping
- [x] Test deterministic document and chunk ID generation
- [x] Test `LineRange` against fixture documents with known line boundaries
- [x] Test section title extraction
- [x] Test `StubEmbeddingProvider` dimensions
- [x] Test constant sparse placeholder value
- [x] Test no `qdrant_client` or `StorageSettings` imports in indexing package

### Integration Tests

- [x] Create `tests/integration/indexing/` package
- [x] Test pipeline upsert invocation
- [x] Test rebuild call order
- [x] Test preview does not write to storage or invoke embeddings
- [x] Test preview does not build `ChunkUpsertItem`

### Validation Workflow

- [x] `uv run ruff format --check .` passes
- [x] `uv run ruff check .` passes
- [x] `uv run basedpyright` passes
- [x] `uv run pytest` passes

### Documentation

- [x] Update `docs/ARCHITECTURE.md` with indexing layer description
- [x] Update `docs/PROGRESS.md` with indexing pipeline milestone

### Non-Scope Verification

- [x] No URL indexing
- [x] No PDF/DOCX/HTML parsing
- [x] No real BGE-M3 or model runtime
- [x] No BM25 or sparse retrieval
- [x] No MCP implementation
- [x] No LangGraph implementation
- [x] No retrieval implementation
- [x] No CLI behavior
- [x] No Docker Compose for Qdrant
- [x] No `qdrant_client` or `StorageSettings` imports in indexing
- [x] No changes to `VectorStore` protocol
