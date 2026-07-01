# Plan 21 Phase 1 Follow-Up Audit

Audit date: 2026-07-01

Scope: follow-up review after Plan 21 Phase 1 implementation, focused on portfolio polish, open-source readiness, README claim precision, MCP framing, production-scope qualification, onboarding clarity, ADR discoverability, and documentation consistency.

Validation performed:

- `uv run ruff format --check .` passed.
- `uv run ruff check .` passed.
- `uv run basedpyright` passed with 0 errors.
- `uv run pytest` passed: 592 passed, 4 skipped, 2 warnings.

## Executive Summary

Plan 21 Phase 1 was implemented well. The repository is now materially stronger as a public GitHub portfolio project.

The most important previous audit risks were addressed: MCP is now described as an **MCP-style typed handler boundary** with deferred SDK transport; production-readiness language is explicitly scoped to a **local educational demo** demonstrating **production-style architecture patterns**; open-source governance files were added; the README first screen now explains what is implemented, deferred, and out of scope; and the stub-first demo path lowers onboarding friction.

The repository now reads as more honest, more maintainable, and more open-source ready. The added documentation is not just cosmetic; it directly improves claim precision and reviewer trust.

There are two small remaining documentation issues:

- the new README stub-demo expected output appears to undercount corpus documents (`96`) relative to the documented/generated/indexed corpus file count including `knowledge/README.md` (`97`);
- the new ADR index improves navigation, but it does not clearly distinguish accepted historical decisions from decisions superseded by later plans.

Neither issue blocks portfolio use. Overall, Plan 21 Phase 1 succeeds.

## Plan 21 Phase 1 Verification

### Task 1.1 — Add open-source governance files

Status: Passed

`LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, and `.github/pull_request_template.md` are present. The contribution guide references the read-first order, active-plan workflow, and validation commands. The security policy gives a responsible disclosure path and clearly scopes the project as educational.

### Task 1.2 — Add README portfolio summary and implementation-status table

Status: Passed

The README now opens with a concise value proposition and a "Why this repository is worth reading" section. The implementation-status table clearly separates implemented, deferred, and out-of-scope capabilities. This substantially improves first-screen clarity.

### Task 1.3 — Correct MCP and production framing in README

Status: Passed

MCP is now accurately described as an in-process, MCP-style typed handler boundary. The README explicitly states that no runnable MCP SDK stdio/network server exists today. Production language is consistently qualified as production-style architecture patterns for a local educational demo.

### Task 1.4 — Document stub-first smoke demo path with expected outputs

Status: Partially passed

The stub-first smoke path is present and useful. It documents `uv sync`, Qdrant startup, corpus generation, `rag demo info`, `rag demo load`, and `rag evaluate compare`, with representative output snippets.

The only issue is a likely expected-output mismatch: README snippets show `Corpus document count: 96` and `documents=96`, while the repository documents that generation produces 97 markdown files including `knowledge/README.md`, and `docs/ARCHITECTURE.md` states demo corpus discovery includes `README.md`. The smoke path is still valuable, but the snippet should match actual CLI semantics.

### Task 1.5 — Add ADR index to docs/DECISIONS.md

Status: Partially passed

The ADR index and current key decisions summary are present and greatly improve navigation. The index covers the decision set and links into the ADR bodies.

The remaining weakness is status precision. Several older ADRs are effectively superseded or legacy after later plans, but the table lists them as `Accepted`. For example, sparse placeholder decisions are superseded for production indexing by Plan 20, as `docs/ARCHITECTURE.md` already notes. The index is useful, but it does not fully satisfy the "active/superseded" discoverability intent.

### Task 1.6 — Add short corpus excerpts under docs/examples/

Status: Passed

`docs/examples/` contains representative markdown excerpts for remote work, security FAQ, and incident response procedure content. `docs/examples/README.md` explains that these are inspection excerpts, not the full generated corpus. This improves GitHub browseability without committing the generated knowledge base.

### Task 1.7 — Document benchmark limitations and reproduction workflow

Status: Passed

The README now includes benchmark limitations and reproduction instructions. It clearly states that evaluation is document-level retrieval only, excludes answer faithfulness, lacks negative/off-topic cases, does not benchmark latency, and requires local real-model evaluation for authoritative numbers.

### Task 1.8 — Document operational non-goals and session-local memory

Status: Passed

The README now explicitly lists operational non-goals: no authentication, deployment manifests, health checks, tracing, metrics dashboards, production runbooks, or durable conversation persistence. The implementation-status table also identifies durable agent memory as deferred and session-local today.

### Validation

Status: Passed

The full validation suite passed unchanged:

- formatting check passed;
- ruff lint passed;
- basedpyright passed with 0 errors;
- pytest passed with 592 passed, 4 skipped.

## Remaining Issues

### 1. README stub-demo expected output likely undercounts indexed corpus documents

Severity: Low

Explanation: The new README smoke-demo snippet says `Corpus document count: 96` and `indexed demo corpus: documents=96`. Elsewhere the repository says generation produces 97 markdown files: 96 corpus documents plus `knowledge/README.md`. `docs/ARCHITECTURE.md` also states `DemoEnvironment.corpus_document_count()` includes `README.md` and matches indexing discovery.

Recommendation: Update the smoke-demo expected output to either use `97` for CLI-discovered/indexed files or label the value more carefully as "96 corpus documents plus generated README". The important point is to keep README snippets aligned with actual CLI behavior.

### 2. ADR index does not clearly distinguish active from superseded historical decisions

Severity: Low

Explanation: The ADR index improves discoverability, but its status column lists legacy decisions such as sparse placeholder ADRs as `Accepted`, even though later architecture documentation treats those constraints as superseded for current production indexing behavior. This can confuse readers trying to identify current constraints.

Recommendation: Keep ADR body history intact, but adjust the index status column or add a "Current relevance" column with values such as `Active`, `Historical`, or `Superseded by ADR-081/084`. This would preserve the audit trail while making current architecture faster to understand.

## Updated Scores

### Engineering Quality: 8.7 / 10

Previous audit: 8.5 / 10.

Engineering quality was already strong. Plan 21 did not change code architecture, but it improved repository governance and reduced claim ambiguity, which matters for engineering credibility. Validation remains clean.

### Documentation: 9.0 / 10

Previous audit: 8.5 / 10.

The README first screen is much stronger, deferred capabilities are visible, benchmark limitations are explicit, and ADR navigation improved. Minor points come off for the corpus-count snippet mismatch and ADR status precision.

### Architecture: 9.0 / 10

Previous audit: 9.0 / 10.

The architecture itself is unchanged and remains excellent. The documentation now represents it more accurately, especially around MCP and production scope.

### Production Readiness: 7.0 / 10

Previous audit: 6.5 / 10.

The project is still not a production service, by design. The score improves because the repository now frames production-style patterns honestly and documents operational non-goals clearly. Actual production capabilities remain intentionally out of scope.

### Open Source Quality: 8.0 / 10

Previous audit: 6.5 / 10.

This is the largest improvement. License, contribution guide, security policy, and GitHub templates substantially improve public readiness. A CI workflow and lighter optional model dependencies would raise this further, but those were correctly deferred.

### Educational Value: 9.2 / 10

Previous audit: 9.0 / 10.

The educational value improved because readers can now understand scope, deferred work, corpus examples, and benchmark limitations without digging through plans first.

### GitHub Portfolio Value: 9.0 / 10

Previous audit: 8.5 / 10.

The repository now presents much better in the first minute of review. It signals maturity, honesty, architecture discipline, and open-source awareness. The remaining issues are small polish items, not credibility blockers.

## Pinned Repository Recommendation

Yes. This repository should be considered a pinned GitHub repository candidate.

After Plan 21 Phase 1, the repo is strong enough to represent Senior AI Systems Engineering work publicly. It demonstrates layered AI system design, retrieval engineering, evaluation, source attribution, testing discipline, ADR discipline, and scoped open-source governance. The README now makes those strengths visible quickly and avoids overstating MCP or production readiness.

The repository is not perfect, but it is credible and portfolio-ready.

## Final Recommendation

Minor follow-up needed.

The remaining work is small documentation correction, not another major phase: align the README corpus-count snippets with actual CLI behavior and clarify ADR index status for superseded historical decisions.
