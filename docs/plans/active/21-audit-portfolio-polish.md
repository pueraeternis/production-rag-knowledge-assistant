# Plan 21 — Audit Portfolio Polish and Claim Precision

**Status:** Active — Phase 1 complete (2026-07-01). Phase 2 and Phase 3 deferred.

**Created:** 2026-07-01

**Activated:** 2026-07-01

**Source:** [Repository Engineering Audit](../../audit/repository-audit.md) (2026-07-01)

**Depends on:** All plans through [Plan 20 — Real Sparse Embeddings Integration](../completed/20-real-sparse-embeddings-integration.md) (completed)

**Plan principle:** One plan addresses **portfolio credibility and open-source readiness** surfaced by the engineering audit. It improves claim precision, contributor onboarding, and documentation discoverability. It does **not** introduce new agent capabilities, MCP SDK transport, evaluation algorithms, or production infrastructure.

**Implementation model:** Plan 21 remains a **single plan** with phased tasks. The **current iteration authorizes Phase 1 only**. Phase 2 and Phase 3 remain documented future work within this plan — not separate plans. Implementation may be divided into multiple commits, but this iteration completes when all Phase 1 acceptance criteria are satisfied.

---

## Authorization

**License:** MIT (recorded at plan activation, 2026-07-01).

**Active — Phase 1 only.** The current engineering iteration authorizes Tasks 1.1 through 1.8 plus validation and `docs/PROGRESS.md` update. **Phase 1 completed 2026-07-01.**

**Not authorized in this iteration:** Phase 2 (optional dependency refactor, GitHub Actions CI, troubleshooting guide) and Phase 3 (`Makefile` / `justfile`). Those tasks remain **Deferred / future work** within Plan 21.

---

## Audit Recommendation Disposition

Each audit finding is evaluated against the engineering decision rule:

> Does this significantly strengthen this repository as evidence of Senior AI Systems Engineering?

| # | Audit finding | Disposition | Rationale |
| - | ------------- | ----------- | --------- |
| 1 | MCP positioning overstates runtime capability | **Accept** | Claim precision is a senior engineering signal. The handler boundary is sound; public wording must match implementation. Documentation-only fix, high portfolio impact. |
| 2 | Missing open-source governance files | **Accept** | Public portfolio repos without `LICENSE` and contributor guidance undermine legal clarity and hiring signals. Lightweight governance files are standard senior practice. |
| 3 | "Production" framing needs sharper qualification | **Accept** | The project already states educational intent in `PROJECT.md`. Aligning README language prevents mis-evaluation against enterprise service expectations. Low effort, high credibility gain. |
| 4 | Query rewriting and retrieval retry documented but not implemented | **Accept (documentation only)** | Surfacing deferred status in README prevents goals-vs-code mismatch. **Implementation rejected here** — already scoped as proposed Plan 12b; adding agent behavior is feature work, not audit remediation. |
| 5 | Onboarding depends on local model/infrastructure assumptions | **Accept (partial)** | Document a stub-first smoke path and expected command output. **Defer** `Makefile`/`justfile` convenience wrappers to Phase 3 — useful but not essential portfolio evidence. |
| 6 | Heavy runtime dependencies installed by default | **Defer to Phase 2** | Valid engineering improvement, but packaging `torch`/`FlagEmbedding` into optional extras touches bootstrap, CI, tests, and README across many files. Worth doing; not Phase 1 low-effort. |
| 7 | Evaluation benchmark is useful but narrow | **Accept (documentation only)** | Add explicit benchmark limitations. **Defer** negative queries, chunk-level labels, and multi-hop cases — valuable but belong in a separate evaluation expansion plan, not this polish plan. |
| 8 | README is long for first-pass scanning | **Accept** | Add a compact top-level value proposition with links to deeper sections. Improves GitHub first-screen signal without removing technical depth. |
| 9 | Architecture documentation is repetitive | **Defer** | Repetition supports educational clarity. Bulk deduplication risks drift and maintenance churn with limited portfolio return. Address only where README restates authoritative docs (covered by Findings 3 and 8). |
| 10 | ADR log is hard to consume at current size | **Accept** | ADR index and "current key decisions" summary improve navigability and demonstrate decision discipline. Low effort, high signal. |
| 11 | Synthetic corpus not browsable on GitHub | **Accept** | Short committed excerpts under `docs/examples/` let readers inspect corpus style without duplicating the generated knowledge base. Goal is inspection, not distribution. |
| 12 | Production observability intentionally absent | **Accept (documentation only)** | Add operational non-goals framing tied to `PROJECT.md`. **Defer** structured retrieval trace output — educational observability is worthwhile but is a separate capability plan. |
| 13 | Developer experience lacks command shortcuts | **Defer to Phase 3** | `Makefile`/`justfile` wrappers improve repeatability but do not materially change portfolio perception of architectural maturity. Optional polish. |
| 14 | Real-model benchmark results not auditable | **Accept** | Document reproduction steps and limitations in README rather than committing snapshot artifacts that go stale. Reproducible workflow is the credibility signal. |
| 15 | Agent memory is session-local | **Accept (documentation only)** | Document in implementation-status table. Durable memory remains out of scope per `PROJECT.md` non-goals. |

### Audit roadmap items explicitly excluded from this plan

| Audit roadmap item | Disposition | Rationale |
| ------------------ | ----------- | --------- |
| Implement MCP SDK server/client transport | **Reject (separate plan)** | Proposed Plan 12c. Major architectural integration, not portfolio polish. |
| Query rewriting and retrieval retry | **Reject (separate plan)** | Proposed Plan 12b. Agent capability expansion beyond audit remediation scope. |
| Extend evaluation with negative/chunk-level cases | **Defer (separate plan)** | Valuable RAG engineering work; scope belongs in evaluation expansion, not claim-precision plan. |
| Structured retrieval trace output | **Defer (separate plan)** | Observability hook is educational but introduces new runtime behavior. |
| JSON export for evaluation reports | **Reject** | Already delivered by [Plan 18](../completed/18-retrieval-strategy-evaluation.md) (`--output PATH`). |
| Transcript export for chat sessions | **Reject** | Explicitly deferred in Plan 19; low portfolio priority. |
| Exported architecture diagram images | **Reject** | Mermaid diagrams in README are sufficient; image assets add maintenance without architectural signal. |
| Langfuse or production monitoring stack | **Reject** | Explicit non-goal in `AGENTS.md` and `PROJECT.md`. |

---

## Goal

Strengthen the repository as public evidence of Senior AI Systems Engineering by:

1. aligning public claims with actual implementation state;
2. adding essential open-source governance artifacts;
3. improving first-run and first-read discoverability for GitHub visitors;
4. making deferred capabilities and intentional non-goals explicit;
5. documenting reproducible benchmark workflows and explicit evaluation limitations.

The repository should read as **architecturally mature, honest, and intentionally scoped** — not as an inflated production service or incomplete MCP runtime.

---

## Scope

### Authorized deliverables (Phase 1 — current iteration)

| Area | Deliverable |
| ---- | ----------- |
| Repository root | `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` |
| `.github/` | Issue template, pull request template |
| `README.md` | Portfolio summary, implementation-status table, production qualification, benchmark limitations, reproduction workflow, stub-first demo path, expected output snippets, operational non-goals |
| `docs/DECISIONS.md` | ADR index table and "current key decisions" summary |
| `docs/examples/` | Short representative corpus excerpts for GitHub inspection |
| `docs/PROGRESS.md` | Plan 21 Phase 1 completion entry (when implemented) |

### Deferred deliverables (Phase 2 and Phase 3 — not this iteration)

| Area | Deliverable | Phase |
| ---- | ----------- | ----- |
| `pyproject.toml` / packaging | Optional model dependency extra | Phase 2 |
| `.github/workflows/` | GitHub Actions CI workflow | Phase 2 |
| `docs/TROUBLESHOOTING.md` | Lightweight troubleshooting guide | Phase 2 |
| `Makefile` or `justfile` | Command wrappers | Phase 3 |

### Documentation alignment targets

| Document | Change |
| -------- | ------ |
| `README.md` | Primary public-facing corrections |
| `PROJECT.md` | Cross-link only if wording conflicts emerge during README edits |
| `docs/ARCHITECTURE.md` | No structural changes unless MCP terminology correction requires one sentence |
| `AGENTS.md` | No changes expected |

---

## Non-goals

This plan does **not** authorize:

* MCP SDK transport implementation (Plan 12c);
* query rewriting, intent classification, or retrieval retry loops (Plan 12b);
* Tier 2 MCP tools (`get_document`, `get_statistics`);
* durable agent memory or LangGraph checkpointers;
* evaluation benchmark expansion (negative queries, chunk-level labels, multi-hop cases);
* structured retrieval tracing or production observability;
* optional model dependency refactor (`pyproject.toml` extras) — Phase 2, deferred;
* GitHub Actions CI workflow — Phase 2, deferred;
* `docs/TROUBLESHOOTING.md` — Phase 2, deferred;
* `Makefile` / `justfile` command wrappers — Phase 3, deferred;
* web UI, REST API, authentication, deployment, or infrastructure;
* LLM-as-a-Judge or answer-faithfulness evaluation;
* changes to retrieval algorithms, agent graph, or MCP handler contracts.

---

## Success Criteria

When **Phase 1** of this plan is complete:

1. A GitHub visitor can determine within the first README screen: what is implemented, what is deferred, and what is intentionally out of scope.
2. The repository has an explicit open-source license and lightweight contributor/security guidance.
3. MCP is described accurately as an **MCP-style typed handler boundary** with deferred SDK transport.
4. "Production" language is consistently qualified as **production-style architecture patterns** for an **educational local demo**.
5. A reader can inspect short corpus excerpts in `docs/examples/` without running the generator.
6. README documents how to reproduce benchmark results, required environment preconditions, and explicit evaluation limitations — without committed snapshot artifacts.
7. `docs/DECISIONS.md` has a navigable index of active architectural constraints.
8. A new contributor can complete a stub-mode smoke demo using documented commands and expected outputs.
9. All existing validation passes unchanged: `uv run ruff format --check .`, `uv run ruff check .`, `uv run basedpyright`, `uv run pytest`.

---

## Expected Portfolio Impact

This plan strengthens the repository as a public GitHub portfolio project in six ways:

**Engineering credibility.** Honest MCP and production framing shows reviewers the author distinguishes architectural patterns from deployed services. A Senior Engineer reading the repo sees judgment, not inflation.

**Open-source maturity.** `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and GitHub templates signal that the project is intentionally public and maintainable — not a throwaway demo.

**Documentation quality.** A scannable README summary, ADR index, and stub-first demo path reduce time-to-understanding for reviewers evaluating depth of work.

**Claim precision.** The implementation-status table and qualified production language align public statements with code reality. Hiring managers can quickly see what is built, deferred, and out of scope.

**Architectural transparency.** Deferred capabilities (MCP SDK transport, query rewriting, durable memory) and operational non-goals are surfaced early, demonstrating scope discipline typical of senior system design.

**First impression for Senior Engineers and Hiring Managers.** The first README screen answers: *What is this? What proves the engineering? What is intentionally not here?* That framing converts a long technical README into a credible portfolio entry within seconds.

---

## Tasks

### Phase 1 — High impact / low effort (authorized — current iteration)

Complete all Phase 1 tasks in this iteration. Finish with validation and a `docs/PROGRESS.md` entry.

#### Task 1.1 — Add open-source governance files

**Motivation:** Public portfolio repositories without license and contributor guidance appear incomplete regardless of code quality.

**Expected impact:** Legal clarity for reuse; stronger open-source maturity signal for reviewers and hiring managers.

**Implementation summary:**

* Add `LICENSE` (recommend **MIT** unless project owner prefers Apache-2.0 — choose one and record in plan activation note).
* Add concise `CONTRIBUTING.md`: read-first order, validation commands, plan-driven workflow, no drive-by changes.
* Add `SECURITY.md`: supported versions, how to report vulnerabilities, no secrets in issues.
* Add `.github/ISSUE_TEMPLATE/bug_report.md` and `.github/pull_request_template.md` — lightweight, not bureaucratic.

**Acceptance criteria:**

* `LICENSE` file present at repository root with correct year and copyright holder.
* `CONTRIBUTING.md` references validation commands and plan workflow.
* `SECURITY.md` provides a contact/reporting path.
* Issue and PR templates exist and reference validation requirements.

---

#### Task 1.2 — Add README portfolio summary and implementation-status table

**Motivation:** Senior engineers and hiring managers scan READMEs quickly. The strongest signals (layered architecture, 592 tests, evaluation, demo workflow) must appear above the fold.

**Expected impact:** Higher GitHub portfolio conversion — readers reach value before operational detail.

**Implementation summary:**

* Add **"Why this repository is worth reading"** section (5–7 bullets) immediately after the opening paragraph.
* Add **"Current implementation status"** table marking:

  | Capability | Status |
  | ---------- | ------ |
  | LangGraph agent with tool loop | Implemented |
  | MCP-style typed handler boundary | Implemented (in-process) |
  | MCP SDK stdio/network transport | Deferred (Plan 12c) |
  | Hybrid retrieval + reranking | Implemented |
  | Retrieval evaluation benchmark | Implemented |
  | Query rewriting / retrieval retry | Deferred (Plan 12b) |
  | Tier 2 browse tools | Deferred |
  | Durable agent memory | Deferred |
  | Production deployment / auth / observability | Out of scope |

* Link deferred rows to `docs/PROGRESS.md` and relevant ADRs.

**Acceptance criteria:**

* Summary section appears in the first screen of rendered README.
* Status table distinguishes **Implemented**, **Deferred**, and **Out of scope**.
* No status row contradicts `docs/ARCHITECTURE.md` or `docs/PROGRESS.md`.

---

#### Task 1.3 — Correct MCP and production framing in README

**Motivation:** Overstating MCP transport or production readiness undermines credibility with senior reviewers who read `server.py` and `PROJECT.md` non-goals.

**Expected impact:** Honest positioning that reinforces architectural judgment rather than marketing inflation.

**Implementation summary:**

* Replace ambiguous "MCP Server" / "MCP integration" phrasing with **"MCP-style knowledge boundary (typed handlers; SDK transport deferred)"** where runtime transport is implied.
* Add a short callout near the architecture diagram: current state is in-process handlers matching the MCP tool contract.
* Add **"What production concerns are intentionally out of scope"** box linking to `PROJECT.md` non-goals (auth, deployment, observability, durable memory, etc.).
* Standardize language: **"production-style architecture patterns"** + **"local educational demo"**.

**Acceptance criteria:**

* README does not imply a runnable MCP SDK server exists today.
* Production-oriented phrasing is consistently qualified.
* `PROJECT.md` non-goals are linked from README.

---

#### Task 1.4 — Document stub-first smoke demo path with expected outputs

**Motivation:** First-time contributors encounter `uv`, Qdrant, corpus generation, and optional real models. A stub path reduces friction before value is visible.

**Expected impact:** Improved first-run success rate; demonstrates that stub mode is a first-class architectural choice, not a test hack.

**Implementation summary:**

* Add **"Fastest smoke demo (stub mode)"** section before the full chat demo path.
* Sequence: `uv sync` → start Qdrant → generate corpus → `rag demo info` → `rag demo load` → `rag evaluate compare` (stub providers).
* Include abbreviated **expected output snippets** for `rag demo info`, `rag demo load`, and `rag evaluate compare`.
* Note that CLI does not auto-load `.env`; link to environment variable documentation.
* Keep full real-model and chat paths as a separate **"Full demo (real models + chat)"** section.

**Acceptance criteria:**

* Stub path is documented as the recommended first run.
* At least one representative output snippet per command listed above.
* Full demo path remains documented and unchanged in capability.

---

#### Task 1.5 — Add ADR index to docs/DECISIONS.md

**Motivation:** ADRs are a portfolio strength only when readers can find current constraints quickly.

**Expected impact:** Faster navigation; clearer evidence of decision discipline.

**Implementation summary:**

* Add **ADR index table** at the top of `docs/DECISIONS.md` grouped by layer (core, storage, indexing, retrieval, MCP, agent, LLM, evaluation, bootstrap, CLI).
* Include columns: ADR ID, title, status (active/superseded), layer.
* Add **"Current key decisions"** summary (7–10 bullets) covering: domain model independence, vector store protocol, LlamaIndex containment, MCP handler boundary, retrieval score semantics, real model opt-in, approval gates.

**Acceptance criteria:**

* Index covers all ADRs with correct status.
* Key decisions summary reflects active constraints without duplicating full ADR text.
* No ADR body content is removed — index is additive.

---

#### Task 1.6 — Add short corpus excerpts under docs/examples/

**Motivation:** Generated `knowledge/` is gitignored; GitHub readers cannot inspect corpus quality or understand benchmark document references.

**Expected impact:** Immediate inspectability of synthetic knowledge base style; supports evaluation narrative without duplicating the generated knowledge base.

**Implementation summary:**

* Create `docs/examples/` with short representative excerpts only (e.g., one policy paragraph, one FAQ entry, one procedure step list) — not full generated documents.
* Add `docs/examples/README.md` explaining excerpts illustrate generator output style; full corpus is produced locally and remains gitignored.
* Optionally reference excerpts in README evaluation section.

**Acceptance criteria:**

* Excerpts are readable markdown matching generator style.
* `docs/examples/README.md` states excerpts are for inspection, not distribution of the full corpus.
* No secrets or realistic PII in excerpt content.
* No duplicate of the full generated knowledge base.

---

#### Task 1.7 — Document benchmark limitations and reproduction workflow

**Motivation:** Retrieval evaluation is a major strength; its scope must not be mistaken for complete RAG evaluation. Committed benchmark snapshots go stale; reproducible instructions stay credible.

**Expected impact:** Self-aware evaluation framing; readers can reproduce results locally without maintaining stale artifacts.

**Implementation summary:**

* Add **"Benchmark limitations"** subsection in README near evaluation results: document-level relevance only; no negative/off-topic cases; no answer faithfulness; no latency testing; corpus version not hash-verified in CI.
* Add **"Reproducing benchmark results"** instructions in README: required preconditions (indexed corpus, `RAG_EMBEDDING_MODE` / `RAG_RERANKER_MODE`, model availability), exact commands (`rag evaluate compare`, optional `--output`), and note that CI runs stub mode only.
* Do **not** commit benchmark result snapshots under `docs/evaluation/` or elsewhere.

**Acceptance criteria:**

* Limitations subsection is visible in README evaluation area.
* Reproduction section lists environment preconditions and exact commands to run real-mode evaluation locally.
* No committed benchmark result artifacts in the repository.

---

#### Task 1.8 — Document operational non-goals and session-local memory

**Motivation:** Readers evaluating "production-quality AI engineering" may look for tracing, metrics, and durable state. Their absence is acceptable only when explicit.

**Expected impact:** Prevents mis-scoring against intentional scope boundaries.

**Implementation summary:**

* Extend README out-of-scope box (Task 1.3) to include operational non-goals: no tracing, structured logs, health checks, deployment manifests, or runbooks.
* Add session-local memory note to implementation-status table: chat demo uses in-process conversation state; persistence deferred.

**Acceptance criteria:**

* Operational absences are listed and linked to `PROJECT.md` non-goals.
* Session-local memory status appears in implementation-status table.

---

### Phase 2 — High impact

**Status: Deferred / future work.** Not authorized in the current iteration. Remains part of Plan 21 for a future pass.

#### Task 2.1 — Move heavy model dependencies to optional extra

**Motivation:** Default `uv sync` installs `torch`, `transformers`, and `FlagEmbedding` even for stub-only contributors, increasing install time and platform risk.

**Expected impact:** Lighter default developer profile; clearer separation of stub vs real runtime paths — a packaging maturity signal.

**Implementation summary:**

* Create optional extra or dependency group (e.g. `knowledge-assistant[models]` or `[dependency-groups] models`).
* Move `torch`, `transformers`, `FlagEmbedding` out of default `dependencies`.
* Update bootstrap provider wiring docs and README install instructions.
* Ensure default `pytest` and CI stub path work without model extras installed.
* Add ADR entry for default lightweight dependency profile.

**Acceptance criteria:**

* `uv sync` without extras completes without `torch`.
* `uv sync --extra models` (or equivalent) enables real BGE runtime.
* All stub-mode tests pass on default install.
* README documents both install paths.

---

#### Task 2.2 — Add GitHub Actions CI workflow

**Motivation:** No CI workflow exists. Automated validation on push/PR is expected evidence of engineering discipline for public portfolio repos.

**Expected impact:** Visible quality gate for contributors and reviewers; stub-mode tests run on every change.

**Implementation summary:**

* Add `.github/workflows/ci.yml` running: `uv sync`, `ruff format --check`, `ruff check`, `basedpyright`, `pytest` (stub mode).
* Do not load real models in CI.
* Document CI behavior in `CONTRIBUTING.md`.

**Acceptance criteria:**

* Workflow runs on pull request and push to `main`.
* All four validation commands execute.
* CI passes on clean `main` branch.
* Real-model tests remain skipped in CI.

---

#### Task 2.3 — Add lightweight troubleshooting guide

**Motivation:** Setup friction (Qdrant unreachable, model download failures, LLM gateway misconfiguration) blocks demo completion without architectural issues.

**Expected impact:** Reduced support burden; faster recovery from common environment problems.

**Implementation summary:**

* Add `docs/TROUBLESHOOTING.md` covering: Qdrant connection errors, corpus not found, stub vs real provider env vars, `.env` not auto-loaded, LLM gateway 401/timeout, model download paths.
* Link from README quick start.

**Acceptance criteria:**

* Guide covers at least five common failure modes with symptoms and fixes.
* Linked from README.

---

### Phase 3 — Optional polish

**Status: Deferred / future work.** Not authorized in the current iteration. Remains part of Plan 21 for a future pass.

#### Task 3.1 — Add Makefile or justfile command wrappers

**Motivation:** Contributors must remember multiple `uv run` commands. Wrappers improve repeatability.

**Expected impact:** Minor DX improvement; low portfolio signal.

**Implementation summary:**

* Add `Makefile` (or `justfile`) with targets: `setup`, `format-check`, `lint`, `typecheck`, `test`, `validate`, `demo-info`, `demo-load`.
* Each target wraps documented `uv` commands — no new behavior.

**Acceptance criteria:**

* `make validate` runs all four quality commands.
* README mentions optional convenience targets.
* No duplication of logic outside `uv` commands.

---

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| README edits introduce drift from `PROJECT.md` / `ARCHITECTURE.md` | Edit README to summarize and link; verify status table against `docs/PROGRESS.md` |
| License choice unclear | Confirm MIT vs Apache-2.0 at plan activation |
| Corpus excerpts diverge from generator templates | Derive excerpts from current generator output; document relationship in `docs/examples/README.md` |

---

## Checklist

### Phase 1 (current iteration)

- [x] `LICENSE` added
- [x] `CONTRIBUTING.md` added
- [x] `SECURITY.md` added
- [x] GitHub issue and PR templates added
- [x] README portfolio summary added
- [x] README implementation-status table added
- [x] MCP and production framing corrected in README
- [x] Stub-first smoke demo path documented with expected outputs
- [x] ADR index and key decisions summary added to `docs/DECISIONS.md`
- [x] Short corpus excerpts committed under `docs/examples/`
- [x] Benchmark limitations and reproduction workflow documented in README
- [x] Operational non-goals and session-local memory documented
- [x] Validation suite passes
- [x] `docs/PROGRESS.md` updated

### Phase 2 (deferred / future work)

- [ ] Model dependencies moved to optional extra
- [ ] GitHub Actions CI workflow added
- [ ] `docs/TROUBLESHOOTING.md` added

### Phase 3 (deferred / future work)

- [ ] `Makefile` or `justfile` added

---

## Out of Scope

### Current iteration boundary

The following Plan 21 tasks are **not authorized** in the current Phase 1 iteration. They remain documented as **Deferred / future work** within this plan:

* optional model dependency refactor (Task 2.1);
* GitHub Actions CI workflow (Task 2.2);
* troubleshooting guide (Task 2.3);
* `Makefile` / `justfile` wrappers (Task 3.1).

### Permanently excluded from Plan 21

| Item | Reason |
| ---- | ------ |
| MCP SDK server/client transport | Major feature — proposed Plan 12c; exceeds polish scope |
| Query rewriting and retrieval retry | Agent capability — proposed Plan 12b |
| Tier 2 MCP browse tools | Separate MCP capability plan |
| Durable agent memory / checkpointers | Explicit `PROJECT.md` non-goal |
| Evaluation expansion (negative queries, chunk-level labels, multi-hop cases) | Separate evaluation plan; benchmark is intentionally narrow for education |
| Structured retrieval trace / observability hooks | New runtime behavior; defer to future observability plan |
| Corpus version hash verification in benchmark runner | Low portfolio priority; CI complexity |
| Committed benchmark result snapshots | Stale over time; reproduction workflow in README is sufficient |
| JSON evaluation export | Already implemented in Plan 18 |
| Chat transcript export | Deferred in Plan 19 |
| Exported architecture diagram images | Mermaid in README is sufficient |
| Langfuse, production monitoring, or metrics stack | Explicit non-goals |
| Authentication, deployment, Kubernetes, microservices | Explicit non-goals |
| LLM-as-a-Judge / answer faithfulness evaluation | Explicit non-goal |
| Bulk documentation deduplication across plans | Maintenance churn; low portfolio return |
| Web UI or REST API | Out of project scope |

---

## Related Documents

* [Repository Engineering Audit](../../audit/repository-audit.md)
* [PROJECT.md](../../../PROJECT.md) — scope and non-goals
* [docs/ARCHITECTURE.md](../../ARCHITECTURE.md) — MCP handler boundary
* [docs/PROGRESS.md](../../PROGRESS.md) — deferred capabilities
* [docs/plans/backlog/ROADMAP.md](../backlog/ROADMAP.md) — informational roadmap
* Proposed [Plan 12b](../completed/12-langgraph-agent.md) — query rewriting (not part of Plan 21)
* Proposed Plan 12c — MCP SDK transport (not part of Plan 21)
