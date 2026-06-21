# Architectural Decisions

This document records meaningful architectural decisions for Production RAG Knowledge Assistant.

For project vision and scope, see [PROJECT.md](../PROJECT.md).

---

## ADR Template

Use the following template for new decision records.

```markdown
## ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded | Deprecated

**Date:** YYYY-MM-DD

### Context

What problem or architectural question prompted this decision?

### Decision

What was decided?

### Consequences

What are the positive and negative outcomes of this decision?

### Alternatives Considered

What other options were evaluated and why were they rejected?
```

---

## Decision Log

### ADR-001: Domain Model Technology

**Status:** Accepted

**Date:** 2026-06-21

#### Context

The system needs shared domain types exchanged by indexing, retrieval, MCP, agent, and storage layers. These types must remain implementation-agnostic — independent from Qdrant, LlamaIndex, MCP, LangGraph, and OpenAI APIs.

#### Decision

* Core domain entities and value objects use `@dataclass(frozen=True, slots=True)`.
* Typed identifiers use `typing.NewType` for `DocumentId` and `ChunkId`.
* Pydantic, TypedDict, ORM models, and infrastructure-specific schemas are excluded from `knowledge_assistant.core`.
* Closed enumerations (`IndexingSourceKind`, `ApprovalStatus`) use stdlib `enum.Enum`.
* Domain models contain data and validation only; no business workflows or I/O.
* Core modules depend only on the Python standard library and other modules inside `knowledge_assistant.core`.

#### Consequences

* All layers can exchange typed, immutable domain objects without coupling to infrastructure.
* Static type checkers distinguish `DocumentId` from `ChunkId` and from arbitrary `str` fields.
* Pydantic remains available for future boundary layers (configuration, MCP contracts, LLM structured outputs) without polluting the core domain.
* Validation is limited to domain invariants in `__post_init__`; format validation for IDs is deferred to generating layers.

#### Alternatives Considered

| Alternative | Why rejected |
| ----------- | ------------ |
| Plain `str` for identifiers | No compile-time distinction between identifier types |
| Frozen dataclass wrapper for IDs | Unnecessary allocation for a single string field |
| `uuid.UUID` for identifiers | Couples identifier format to UUID; indexing may use content-derived IDs |
| Pydantic constrained types | Out of scope for core domain layer |
| TypedDict | No runtime validation; less suitable for immutable value objects with invariants |
