# Plan 14 — Synthetic Corporate Knowledge Base

**Status:** Completed

**Created:** 2026-06-21

**Revised:** 2026-06-22 (tracked corpus generator, manifest, templates, and quality gates)

**Roadmap:** Phase 9 — Synthetic Knowledge Base

**Depends on:**

* [Plan 13 — Evaluation Framework](../completed/13-evaluation-framework.md)

**Plan principle:** One plan introduces one deliverable asset class. Plan 14 defines the **canonical synthetic knowledge corpus specification** and the **local generated corpus** under `knowledge/` — markdown documents representing AcmeCloud Analytics internal documentation. Generated corpus files are **not** source-controlled. It does **not** modify retrieval, indexing, storage, MCP, agent, evaluation framework, CLI, or model integrations.

---

## Authorization

**Completed.** Corpus regeneration uses tracked project tooling under `tools/knowledge_generator/`. The generated `knowledge/` corpus remains local and gitignored.

---

## Corpus quality requirements

Generated documents must **not** use generic boilerplate padding or repeated paragraph templates to satisfy word counts.

### Document-type templates

Each document category uses a distinct tracked Markdown prompt template under `tools/knowledge_generator/templates/`:

| Type | Example paths | Required sections |
| ---- | ------------- | ----------------- |
| Architecture | `*_overview.md`, `ingestion_architecture.md` | Overview, System Components, Control Plane, Data Plane, Dependencies, Scaling Model, Operational Ownership, Failure Modes, Related Systems |
| Runbook | `*runbook*.md`, `*playbook*.md` | Purpose, Preconditions, Procedure, Validation, Rollback, Escalation, Related Incidents |
| Policy | `policies/*`, `procedures/*` | Purpose, Scope, Requirements, Exceptions, Enforcement, Review Cycle |
| RFC | `rfcs/*` | Context, Problem, Decision, Alternatives Considered, Tradeoffs, Consequences, Rollout, Related Systems |
| Postmortem | `postmortems/*` | Summary, Impact, Timeline, Root Cause, Contributing Factors, Detection, Resolution, Action Items |
| Handbook | `*handbook*.md`, guides, standards | Overview, Principles, Responsibilities, Operating Model, Review Process, References |

**Forbidden** across unrelated documents: repeated `Example (` / `Failure mode (` / `Decision rationale (` / `Operational checklist (` section patterns.

### Automated quality gates

`python3 tools/knowledge_generator/generator.py` fails if any document:

* falls below minimum word count;
* contains duplicate paragraphs;
* exceeds repeated sentence or paragraph ratio thresholds;
* contains known filler phrases;
* omits required sections declared by its document-type template;
* misses any benchmark path declared in `tools/knowledge_generator/manifests/corpus.v1.yaml`.

Gate metrics (duplicate paragraphs, duplicate sentences, section diversity) print on each generation run.

---

## Objective

Define and generate locally a realistic **enterprise internal documentation corpus** for the fictional company **AcmeCloud Analytics**.

Plan 14 delivers:

1. **Corpus specification** — this document (inventory, conventions, cross-links, benchmark alignment).
2. **Local generated corpus** — **80–100** markdown files materialized under `knowledge/` on the developer machine.

The repository tracks the **plan/specification**, reusable generator, templates, manifest, and quality gates. Generated `knowledge/*.md` files remain local data; `knowledge/` is listed in `.gitignore` and must not be committed.

The corpus is the shared asset consumed by (after local generation):

* indexing pipeline demos and integration tests;
* hybrid retrieval evaluation;
* MCP `search_documents` and indexing handlers;
* LangGraph agent demonstrations;
* retrieval benchmark grounding (`data/evaluation/retrieval_benchmark_v1.json`).

```text
knowledge/                          ← local generated corpus root (repository-relative; gitignored)
    ├── company/
    ├── engineering/
    ├── data-platform/
    ├── analytics-platform/
    ├── ai-platform/
    ├── observability-platform/
    ├── sre/
    ├── security/
    ├── product/
    ├── support/
    ├── finance/
    ├── hr/
    ├── rfcs/                       ← architecture decision records
    ├── postmortems/                ← incident post-incident reviews
    ├── policies/                   ← benchmark-aligned corporate policies
    └── procedures/                 ← benchmark-aligned cross-functional procedures
```

After this plan is complete (specification archived; corpus generated locally):

* **80–100** markdown documents exist under `knowledge/` on the local filesystem;
* documents resemble Confluence-style internal docs for a ~500-person B2B SaaS company;
* **RFCs**, **postmortems**, and **fictional internal service names** add enterprise realism;
* cross-links, ownership metadata, and overlapping terminology are intentional;
* retrieval difficulty is designed to make Dense vs Sparse vs Fusion vs Rerank comparisons meaningful;
* all seven paths referenced by `retrieval_benchmark_v1.json` exist verbatim in the local corpus;
* a corpus index (`knowledge/README.md`) maps departments, ownership, document categories, RFCs, and postmortems.

**Dependency rule:** corpus generation is **content-only**. No imports from `knowledge_assistant.*`. No production Python modules in `src/`. Reusable generation tooling lives in tracked `tools/knowledge_generator/`. Generated corpus output lives in gitignored `knowledge/`. No CLI. No changes to `data/evaluation/` unless explicitly listed in [Evaluation Alignment](#evaluation-alignment).

---

## Scope

### In Scope

* AcmeCloud Analytics company narrative, org structure, and product portfolio definition;
* corpus directory layout under `knowledge/` (local generated root);
* document inventory (categories, counts, ownership) — authoritative manifest in this plan;
* knowledge-relationship and cross-link design rules;
* retrieval-complexity design guidance for corpus authors;
* evaluation alignment with `retrieval_benchmark_v1.json`;
* detailed outlines for **12 representative documents**;
* authoring conventions (front matter, headings, cross-reference syntax);
* **local corpus generation** producing **80–100** markdown files under gitignored `knowledge/`;
* generated markdown files under ignored `knowledge/` (not tracked in git);
* RFC and postmortem document types with required section schemas;
* fictional internal platform system names used consistently across the corpus;
* `knowledge/README.md` corpus index (generated locally);
* `.gitignore` rule excluding `knowledge/`;
* regeneration instructions (approved generator command documented in this plan and `docs/PROGRESS.md`);
* updates to `docs/PROGRESS.md` on completion.

### Non-Scope

This plan does **not** authorize:

* **committing generated corpus files** — `knowledge/*.md` must not be staged or pushed;
* changes to `src/knowledge_assistant/retrieval/`;
* changes to `src/knowledge_assistant/indexing/`;
* changes to `src/knowledge_assistant/storage/`;
* changes to `src/knowledge_assistant/mcp_server/`;
* changes to `src/knowledge_assistant/agent/`;
* changes to `src/knowledge_assistant/evaluation/`;
* changes to `data/evaluation/retrieval_benchmark_v1.json` (paths are satisfied by corpus layout; benchmark expansion is deferred);
* CLI commands or demo scripts (Plan 15 — Demo Bootstrap Workflow);
* automated LLM corpus generation pipelines in tracked `src/` repository code;
* non-markdown formats (PDF, HTML export, Confluence API);
* Docker Compose, live Qdrant indexing, or embedding model runtime;
* ADR entries (no architectural boundary change — corpus specification is documentation; generated output is a local asset).

---

## Company Narrative

### AcmeCloud Analytics

**AcmeCloud Analytics** is a B2B SaaS company (~500 employees, founded 2018, HQ in Denver, remote-first US/EU footprint) that sells a unified cloud analytics suite to mid-market and enterprise customers.

**Mission:** Help data teams move from raw events to trusted insights and production AI features without operating fragmented infrastructure.

**Revenue model:** Annual platform subscriptions with usage-based overages on compute, storage, and inference.

### Product Portfolio

| Platform | Customer-facing name | Primary buyers | Core value |
| -------- | -------------------- | -------------- | ---------- |
| **Data Platform** | AcmeCloud Data Lake | Data Engineering, Analytics Eng | Ingestion, warehousing, schema governance, batch/stream pipelines |
| **Analytics Platform** | AcmeCloud Insights | Analytics, BI, Product | Semantic layer, dashboards, self-serve SQL, embedded analytics |
| **AI Platform** | AcmeCloud AI Studio | ML Engineering, Applied Science | Feature store, training, model registry, online inference |
| **Observability Platform** | AcmeCloud Observe | SRE, Platform, Support | Metrics, logs, traces, alerting, SLOs, incident tooling integrations |

Platforms share: unified identity via **Gatehouse** (internal IAM), a common control plane (**Atlas** + AcmeCloud Console), regional cells (`us-east`, `us-west`, `eu-central`), and usage metering through **Ledger**.

### Internal Platform Systems

Fictional **internal codenames** for AcmeCloud backend systems. Authors must use these names consistently across architecture docs, RFCs, postmortems, runbooks, and incident procedures. Customer-facing product names (AcmeCloud Data Lake, Insights, AI Studio, Observe) remain the external brand; internal docs often refer to codenames.

| Codename | Role | Primary owners | Appears in |
| -------- | ---- | -------------- | ---------- |
| **Atlas** | Control plane — tenant provisioning, cell routing, platform config, deployment orchestration | Engineering, SRE | `company/glossary.md`, `company/product_portfolio.md`, platform overviews, RFCs, postmortems, `sre/deployment_runbook.md` |
| **Beacon** | Observability ingestion — metrics, logs, trace intake and buffering before indexing | Observability Platform | `observability-platform/*`, RFC 003, postmortem `2025-11-03-*`, alerting docs |
| **Mercury** | Streaming pipeline runtime — real-time ingest, stream processing jobs | Data Platform | `data-platform/streaming_pipeline_guide.md`, RFC 004, postmortems |
| **Orion** | Model serving platform — online inference, canary deploys, GPU scheduling | AI Platform | `ai-platform/model_serving_runbook.md`, `online_inference_slos.md`, postmortem `2026-01-22-*` |
| **Ledger** | Billing and usage metering — compute/storage/inference consumption, quotas | Finance, Data Platform | `finance/cloud_spend_governance.md`, platform overviews, RFC 004 |
| **Gatehouse** | Identity and access control — SSO, RBAC, workspace ACLs, service accounts | Security | `security/access_management.md`, `data-platform/workspace_isolation.md`, onboarding/access procedures |
| **Harbor** | Data lake storage layer — object storage, table formats, partition layout | Data Platform | `data-platform/data_platform_overview.md`, `ingestion_architecture.md`, RFC 001, postmortem `2025-09-17-*` |

**Naming rules:**

* First mention in each doc: `Harbor (data lake storage layer)` or link to `company/glossary.md`;
* Postmortems and RFCs must name affected systems explicitly in **Related systems** / **Impact** sections;
* Do not introduce additional internal codenames without a plan revision;
* Benchmark policy docs may reference Gatehouse for access provisioning but need not name every system.

### Engineering Culture (documentation tone)

Internal docs should read like a mature Confluence space:

* page owner and last-reviewed date in YAML front matter;
* status labels: `Draft`, `Approved`, `Deprecated`;
* explicit **Owner**, **Reviewers**, and **Related documents** sections;
* acronyms defined once per doc and repeated across docs (intentional terminology overlap);
* procedural numbered steps and architecture diagrams described in prose (no image files required);
* occasional “see also” links to policies in `knowledge/policies/`, procedures in `knowledge/procedures/`, RFCs in `knowledge/rfcs/`, and postmortems in `knowledge/postmortems/`.

### Fictional Leadership (for ownership realism)

| Role | Name | Department |
| ---- | ---- | ---------- |
| CEO | Jordan Ellis | Company |
| CTO | Priya Nair | Engineering |
| VP Data Platform | Marcus Chen | Data Platform |
| VP Analytics | Elena Vasquez | Analytics Platform |
| VP AI | Dr. Amara Okafor | AI Platform |
| VP Platform / SRE | Sam Okonkwo | SRE / Observability |
| CISO | Rachel Kim | Security |
| VP Product | Leo Hartmann | Product |
| VP Support | Nina Petrov | Support |
| CFO | David Walsh | Finance |
| CHRO | Teresa Morales | HR |

---

## Department Structure

Approximate headcount distribution (500 total):

| Department | Headcount | Primary corpus folders | Owns |
| ---------- | --------- | ---------------------- | ---- |
| **Engineering** | 120 | `engineering/` | SDLC, code review, release engineering, shared libraries |
| **Data Platform** | 85 | `data-platform/` | Pipelines, lakehouse, ingestion, data quality, schema registry |
| **Analytics Platform** | 70 | `analytics-platform/` | Semantic layer, dashboards, query engine, embedded analytics |
| **AI Platform** | 55 | `ai-platform/` | Feature store, training, model registry, inference, responsible AI |
| **SRE** | 45 | `sre/`, `procedures/` (shared) | Reliability, on-call, incident ops, change management, DR |
| **Observability Platform** | 40 | `observability-platform/` | Metrics/logs/traces product internals and customer-facing observability docs |
| **Security** | 25 | `security/`, `policies/security_policy.md` | AppSec, GRC, access control, vendor security |
| **Product** | 35 | `product/` | Roadmap, PRDs, launch process, feature flags |
| **Support** | 50 | `support/` | Tiering, escalation, customer comms, support runbooks |
| **Finance** | 20 | `finance/`, `policies/expense_policy.md`, `policies/travel_policy.md` | Procurement, budgets, expenses, travel |
| **HR** | 25 | `hr/`, `policies/` (people policies) | Onboarding, remote work, equipment, PTO, performance |
| **Company** | 30 (G&A, legal, marketing) | `company/` | Mission, org, glossary, vendor list, office ops |
| **Architecture (cross-functional)** | — | `rfcs/` | Major technical decisions with alternatives and consequences |
| **Incident history (cross-functional)** | — | `postmortems/` | Production incident reviews linked to runbooks and RFCs |

**Cross-functional rule:** Policies with legal/HR/Finance blast radius live in `knowledge/policies/`. Executable runbooks and incident procedures that span departments live in `knowledge/procedures/` or `knowledge/sre/` with cross-links. Accepted RFCs are authoritative for architecture decisions; postmortems reference but do not override runbooks.

---

## Corpus Layout

### Canonical Root

All paths are **repository-relative**, POSIX forward slashes, lowercase `snake_case` filenames. The tree below is created **locally** under gitignored `knowledge/` when the corpus is generated:

```text
knowledge/                          # local generated root — gitignored; do not commit
├── README.md                       # corpus index (required after generation)
├── company/
├── engineering/
├── data-platform/
├── analytics-platform/
├── ai-platform/
├── observability-platform/
├── sre/
├── security/
├── product/
├── support/
├── finance/
├── hr/
├── rfcs/                           # architecture decision records
├── postmortems/                    # incident post-incident reviews
├── policies/                       # DO NOT relocate benchmark policy files
└── procedures/                     # DO NOT relocate benchmark procedure files
```

### Local Corpus Generation

| Item | Location | Git tracking |
| ---- | -------- | ------------ |
| Corpus specification | This plan (`docs/plans/completed/14-synthetic-knowledge-base.md`) | Tracked |
| Regeneration command | `python3 tools/knowledge_generator/generator.py` (from repository root) | Documented in plan and `docs/PROGRESS.md` |
| Generator, templates, manifest, quality gates | `tools/knowledge_generator/` | **Tracked** project assets |
| Generated corpus | `knowledge/**/*.md` | **Gitignored** — must not be committed |

Fresh clones can regenerate the full **96-document** corpus locally from tracked assets. `tools/knowledge_generator/manifests/corpus.v1.yaml` is the single source of truth for document inventory, paths, types, owners, related systems, related documents, required facts, and benchmark alignment metadata. Indexing and evaluation consume the **local** `knowledge/` tree after generation.

### Authoring Conventions

Every document **must** begin with YAML front matter:

```yaml
---
title: "Human Readable Title"
owner: "Department Name"
owner_contact: "team-alias@acmecloud.io"
status: "Approved"
last_reviewed: "2026-03-15"
confluence_ref: "ACME-1234"          # fictional Confluence page ID
related:
  - "../sre/oncall_policy.md"
  - "../policies/security_policy.md"
---
```

Body requirements:

* H1 matches `title`;
* include **Overview**, **Scope**, **Owner**, **Related documents** sections (order may vary);
* minimum **800 words** for policy/procedure docs; **600 words** for technical overviews; **1000 words** for architecture docs (ensures meaningful chunking);
* use inline markdown links to sibling documents: `[On-Call Policy](../sre/oncall_policy.md)`;
* include at least **two** cross-links to documents outside the author's primary folder (enforced during implementation review);
* use consistent product terms: *cell*, *control plane*, *data plane*, *tenant*, *workspace*, *pipeline*, *job*, *model version*, *SLO*, *error budget*;
* use internal system codenames per [Internal Platform Systems](#internal-platform-systems): Atlas, Beacon, Mercury, Orion, Ledger, Gatehouse, Harbor.

#### RFC Documents (`knowledge/rfcs/`)

RFC front matter **must** include `rfc_id` and `rfc_status`:

```yaml
---
title: "RFC 003 — Observability Ingestion Rework (Beacon)"
rfc_id: "RFC-003"
rfc_status: "Accepted"               # Accepted | Rejected | Superseded
owner: "Observability Platform"
owner_contact: "observe-platform@acmecloud.io"
last_reviewed: "2025-11-20"
supersedes: "RFC-012"               # optional; required when Superseded
related_systems:
  - Beacon
  - Atlas
related:
  - "../observability-platform/observability_platform_overview.md"
  - "../postmortems/2025-11-03-observability-ingestion-delay.md"
---
```

RFC body **must** include these sections:

1. **Context**
2. **Decision**
3. **Alternatives considered**
4. **Consequences**
5. **Related systems** (Atlas, Beacon, etc.)
6. **Related documents** (platform docs, postmortems, superseded RFCs)

Minimum **900 words** per RFC.

#### Postmortem Documents (`knowledge/postmortems/`)

Postmortem front matter **must** include `incident_date` and `severity`:

```yaml
---
title: "Postmortem — 2025-02-14 eu-central Cell Outage"
incident_date: "2025-02-14"
severity: "SEV-1"
owner: "SRE"
owner_contact: "sre-incidents@acmecloud.io"
last_reviewed: "2025-02-28"
related_systems:
  - Atlas
  - Harbor
  - Mercury
related:
  - "../procedures/incident_response.md"
  - "../sre/postmortem_template.md"
  - "../rfcs/rfc_004_multi_region_cells.md"
---
```

Postmortem body **must** include these sections:

1. **Summary**
2. **Impact**
3. **Timeline**
4. **Root cause**
5. **Contributing factors**
6. **Detection**
7. **Resolution**
8. **Follow-up actions**
9. **Owning teams**
10. **Related runbooks** (links to operational docs)

Minimum **800 words** per postmortem. Filename pattern: `YYYY-MM-DD-short-slug.md`.

### Indexing Discovery

The indexing pipeline accepts directory paths recursively. After local corpus generation, index from:

```text
knowledge/
```

`knowledge/` is **gitignored** (see `.gitignore`). Generated markdown under `knowledge/` is a local workspace artifact, not a repository deliverable. Do not commit generated corpus files.

---

## Document Inventory

**Target:** 96 documents (within **80–100** range).

Benchmark-mandated files (7) are counted below and **must not be renamed or moved**.

Sixteen lower-priority reference docs from the original inventory were **removed** to make room for RFCs and postmortems while staying within the 80–100 cap. See [Removed from Inventory](#removed-from-inventory).

### `knowledge/company/` (4)

| File | Category | Owner | Words (target) |
| ---- | -------- | ----- | -------------- |
| `company_overview.md` | Company | Company / CEO office | 900 |
| `org_structure.md` | Company | HR | 800 |
| `product_portfolio.md` | Company | Product | 1000 |
| `glossary.md` | Company | Technical Writing | 1400 |

**`glossary.md` must define:** Atlas, Beacon, Mercury, Orion, Ledger, Gatehouse, Harbor — with one-line role, owning team, and links to authoritative platform docs.

**`product_portfolio.md` must map:** each customer-facing platform to the internal systems it depends on (e.g. Data Lake → Harbor + Mercury; Observe → Beacon; AI Studio → Orion).

### `knowledge/engineering/` (6)

| File | Category | Owner |
| ---- | -------- | ----- |
| `engineering_handbook.md` | Process | Engineering |
| `sdlc_overview.md` | Process | Engineering |
| `code_review_guidelines.md` | Process | Engineering |
| `branching_and_release_strategy.md` | Process | Engineering |
| `testing_strategy.md` | Quality | Engineering |
| `service_tiers.md` | Architecture | Engineering / SRE |

### `knowledge/data-platform/` (10)

| File | Category | Owner |
| ---- | -------- | ----- |
| `data_platform_overview.md` | Architecture | Data Platform |
| `ingestion_architecture.md` | Architecture | Data Platform |
| `batch_pipeline_guide.md` | Runbook | Data Platform |
| `streaming_pipeline_guide.md` | Runbook | Data Platform |
| `schema_registry.md` | Architecture | Data Platform |
| `data_quality_framework.md` | Process | Data Platform |
| `data_lineage.md` | Architecture | Data Platform |
| `workspace_isolation.md` | Security / architecture | Data Platform |
| `sla_and_freshness.md` | Operations | Data Platform |
| `backfill_procedures.md` | Runbook | Data Platform |

**Harbor** and **Mercury** must appear in `data_platform_overview.md`, `ingestion_architecture.md`, and `streaming_pipeline_guide.md`.

### `knowledge/analytics-platform/` (6)

| File | Category | Owner |
| ---- | -------- | ----- |
| `analytics_platform_overview.md` | Architecture | Analytics Platform |
| `semantic_layer.md` | Architecture | Analytics Platform |
| `dashboard_standards.md` | Standards | Analytics Platform |
| `query_performance_guide.md` | Runbook | Analytics Platform |
| `self_serve_sql_policy.md` | Policy / tech | Analytics Platform |
| `analytics_release_process.md` | Process | Analytics Platform |

### `knowledge/ai-platform/` (8)

| File | Category | Owner |
| ---- | -------- | ----- |
| `ai_platform_overview.md` | Architecture | AI Platform |
| `feature_store_guide.md` | Architecture | AI Platform |
| `model_training_pipelines.md` | Architecture | AI Platform |
| `model_registry.md` | Architecture | AI Platform |
| `model_serving_runbook.md` | Runbook | AI Platform |
| `responsible_ai_guidelines.md` | Policy | AI Platform |
| `online_inference_slos.md` | Operations | AI Platform |
| `ml_incident_playbook.md` | Runbook | AI Platform |

**Orion** must appear in `ai_platform_overview.md`, `model_serving_runbook.md`, and `online_inference_slos.md`.

### `knowledge/observability-platform/` (6)

| File | Category | Owner |
| ---- | -------- | ----- |
| `observability_platform_overview.md` | Architecture | Observability Platform |
| `metrics_collection.md` | Architecture | Observability Platform |
| `logging_standards.md` | Standards | Observability Platform |
| `distributed_tracing.md` | Architecture | Observability Platform |
| `alerting_and_routing.md` | Operations | Observability Platform |
| `slo_framework.md` | Process | Observability Platform / SRE |

**Beacon** must appear in `observability_platform_overview.md`, `metrics_collection.md`, and `alerting_and_routing.md`.

### `knowledge/sre/` (9)

| File | Category | Owner |
| ---- | -------- | ----- |
| `oncall_policy.md` | Policy | SRE |
| `incident_management.md` | Process | SRE |
| `postmortem_template.md` | Process | SRE |
| `change_management.md` | Process | SRE |
| `capacity_planning.md` | Operations | SRE |
| `disaster_recovery.md` | Runbook | SRE |
| `deployment_runbook.md` | Runbook | SRE |
| `status_page_operations.md` | Runbook | SRE / Support |
| `error_budget_policy.md` | Policy | SRE |

**Note:** `procedures/incident_response.md` is the **benchmark-canonical** incident procedure (see below). `sre/incident_management.md` covers roles, severity, and communications; it must cross-link to `incident_response.md` without duplicating step-by-step response.

### `knowledge/security/` (7)

| File | Category | Owner |
| ---- | -------- | ----- |
| `access_management.md` | Policy | Security |
| `secrets_management.md` | Standards | Security |
| `vulnerability_management.md` | Process | Security |
| `data_classification.md` | Policy | Security |
| `vendor_security_review.md` | Process | Security |
| `security_incident_bridge.md` | Runbook | Security |
| `customer_data_handling.md` | Policy | Security |

**Note:** `policies/security_policy.md` is the **employee-facing** security policy (benchmark). `security/` holds operational security docs. **Gatehouse** is the primary subject of `access_management.md`.

### `knowledge/product/` (4)

| File | Category | Owner |
| ---- | -------- | ----- |
| `product_development_lifecycle.md` | Process | Product |
| `prd_guidelines.md` | Standards | Product |
| `roadmap_planning.md` | Process | Product |
| `feature_flags.md` | Standards | Product / Engineering |

### `knowledge/support/` (5)

| File | Category | Owner |
| ---- | -------- | ----- |
| `support_tier_structure.md` | Operations | Support |
| `escalation_matrix.md` | Operations | Support |
| `customer_ticket_handling.md` | Process | Support |
| `support_slas.md` | Policy | Support |
| `customer_incident_comms.md` | Runbook | Support |

### `knowledge/finance/` (3)

| File | Category | Owner |
| ---- | -------- | ----- |
| `budget_planning.md` | Process | Finance |
| `procurement_policy.md` | Policy | Finance |
| `cloud_spend_governance.md` | Operations | Finance / SRE |

**Ledger** must appear in `cloud_spend_governance.md` and be cross-linked from `product_portfolio.md`.

### `knowledge/hr/` (3)

| File | Category | Owner |
| ---- | -------- | ----- |
| `pto_and_leave.md` | Policy | HR |
| `performance_review_cycle.md` | Process | HR |
| `offboarding_checklist.md` | Process | HR |

### `knowledge/policies/` (8) — includes 6 benchmark files

| File | Category | Owner | Benchmark |
| ---- | -------- | ----- | --------- |
| `remote_work_policy.md` | Policy | HR | **yes** |
| `onboarding_policy.md` | Policy | HR | **yes** |
| `travel_policy.md` | Policy | Finance / HR | **yes** |
| `security_policy.md` | Policy | Security | **yes** |
| `equipment_policy.md` | Policy | HR / IT | **yes** |
| `expense_policy.md` | Policy | Finance | **yes** |
| `acceptable_use_policy.md` | Policy | Security / HR | no |
| `code_of_conduct.md` | Policy | HR / Legal | no |

### `knowledge/procedures/` (5) — includes 1 benchmark file

| File | Category | Owner | Benchmark |
| ---- | -------- | ----- | --------- |
| `incident_response.md` | Procedure | SRE | **yes** |
| `emergency_change_process.md` | Procedure | SRE | no |
| `access_provisioning.md` | Procedure | Security / IT | no |
| `data_access_request.md` | Procedure | Security / Data Platform | no |
| `customer_escalation.md` | Procedure | Support | no |

### `knowledge/rfcs/` (6)

| File | Status | Related systems | Owner |
| ---- | ------ | --------------- | ----- |
| `rfc_001_clickhouse_migration.md` | Accepted | Harbor, Analytics query layer | Analytics Platform |
| `rfc_002_feature_store_design.md` | Accepted | Orion, Harbor, Gatehouse | AI Platform |
| `rfc_003_observability_rework.md` | Accepted | Beacon, Atlas | Observability Platform |
| `rfc_004_multi_region_cells.md` | Accepted | Atlas, Mercury, Harbor, Ledger | SRE / Engineering |
| `rfc_005_llm_gateway.md` | Rejected | Orion, Gatehouse | AI Platform |
| `rfc_006_kafka_to_mercury_migration.md` | Superseded | Mercury, Harbor | Data Platform |

**RFC relationship rules:**

* `rfc_006` is **Superseded** by accepted streaming guidance in `streaming_pipeline_guide.md` and partially by `rfc_004` (cell-local Mercury deploys);
* `rfc_005` is **Rejected** — documents why an internal LLM gateway was not built; `ai_platform_overview.md` must reference the rejection rationale;
* Accepted RFCs must be linked from at least one platform overview and one postmortem or runbook where applicable.

### `knowledge/postmortems/` (6)

| File | Severity | Primary systems | Owning teams |
| ---- | -------- | --------------- | ------------ |
| `2025-02-14-eu-central-outage.md` | SEV-1 | Atlas, Harbor, Mercury | SRE, Data Platform |
| `2025-06-01-feature-store-degradation.md` | SEV-2 | Orion, Harbor, Gatehouse | AI Platform, Data Platform |
| `2025-09-17-schema-registry-failure.md` | SEV-2 | Harbor, Atlas, Gatehouse | Data Platform, SRE |
| `2025-11-03-observability-ingestion-delay.md` | SEV-2 | Beacon, Atlas | Observability Platform, SRE |
| `2026-01-22-model-serving-latency.md` | SEV-2 | Orion, Atlas | AI Platform, SRE |
| `2025-08-12-gatehouse-auth-outage.md` | SEV-1 | Gatehouse, Atlas | Security, SRE |

Each postmortem must link to **at least two** related runbooks and **at least one** RFC or platform architecture doc.

### Removed from Inventory

The following **16** documents were removed from the original inventory to make room for RFCs and postmortems while staying within **80–100** files. Do **not** author these unless a future plan revision expands the cap:

* `company/office_and_remote_locations.md`
* `engineering/api_design_standards.md`
* `engineering/technical_debt_policy.md`
* `data-platform/third_party_connectors.md`
* `data-platform/cost_optimization_data.md`
* `analytics-platform/embedded_analytics.md`
* `analytics-platform/customer_facing_metrics_definitions.md`
* `observability-platform/dashboard_templates.md`
* `observability-platform/observability_data_retention.md`
* `product/launch_checklist.md`
* `product/pricing_and_packaging.md`
* `support/internal_support_tools.md`
* `finance/vendor_payment_terms.md`
* `hr/dei_and_conduct.md`
* `ai-platform/gpu_capacity_and_quotas.md`
* `ai-platform/prompt_and_eval_standards.md`

### Inventory Summary

| Area | Count |
| ---- | ----- |
| company | 4 |
| engineering | 6 |
| data-platform | 10 |
| analytics-platform | 6 |
| ai-platform | 8 |
| observability-platform | 6 |
| sre | 9 |
| security | 7 |
| product | 4 |
| support | 5 |
| finance | 3 |
| hr | 3 |
| policies | 8 |
| procedures | 5 |
| rfcs | 6 |
| postmortems | 6 |
| **Total** | **96** |

Implementation must **generate locally** exactly **80–100** documents per the inventory below (**96 files** in the authoritative manifest). Do not add files outside this manifest without a plan revision. Do not commit generated files.

---

## Knowledge Relationships

### Cross-Link Clusters (intentional overlap)

Authors must implement these relationship clusters so retrieval evaluation and demos reflect real enterprise search friction.

#### Cluster A — Incident Response (multi-perspective)

| Document | Viewpoint | Key terms |
| -------- | --------- | --------- |
| `procedures/incident_response.md` | Step-by-step operational response | sev-1, bridge, incident commander, acknowledgment SLA |
| `sre/incident_management.md` | Roles, severity matrix, comms cadence | severity, stakeholder updates, incident commander |
| `sre/oncall_policy.md` | Rotation, paging, handoff | PagerDuty, primary/secondary, escalation timeout |
| `observability-platform/alerting_and_routing.md` | Alert routes to on-call | Beacon, alert rules, routing policies |
| `security/security_incident_bridge.md` | Security join criteria for incidents | Gatehouse, data breach, forensics |
| `support/customer_incident_comms.md` | External customer messaging | status page, support macros, customer SLA |
| `ai-platform/ml_incident_playbook.md` | Model degradation / inference incidents | Orion rollback, feature drift |
| `postmortems/*.md` | Historical incidents — root cause, timeline | Atlas, Harbor, Mercury, Orion, Beacon, Gatehouse |

**Required cross-links:** Each document in Cluster A links to at least two others in the cluster. `sre/postmortem_template.md` links to `postmortems/` index in `knowledge/README.md`. At least three postmortems link back to `incident_response.md`.

#### Cluster B — Remote / Hybrid Work (policy overlap)

| Document | Viewpoint |
| -------- | --------- |
| `policies/remote_work_policy.md` | Eligibility, geography, core hours |
| `policies/equipment_policy.md` | Home office hardware, monitors |
| `policies/security_policy.md` | VPN, MFA, Gatehouse access for remote |
| `policies/expense_policy.md` | Internet stipend, coworking reimbursement |
| `hr/pto_and_leave.md` | Availability expectations while on leave |

#### Cluster C — Pipelines (terminology collision)

| Document | Meaning of “pipeline” |
| -------- | --------------------- |
| `data-platform/batch_pipeline_guide.md` | ETL/ELT batch jobs into Harbor |
| `data-platform/streaming_pipeline_guide.md` | Mercury streaming jobs |
| `ai-platform/model_training_pipelines.md` | ML training workflows |
| `engineering/branching_and_release_strategy.md` | CI/CD release pipeline via Atlas |
| `sre/deployment_runbook.md` | Production deploy pipeline |

#### Cluster D — Access & Identity

| Document | Viewpoint |
| -------- | --------- |
| `policies/security_policy.md` | Employee responsibilities |
| `security/access_management.md` | Gatehouse RBAC, SSO groups, least privilege |
| `procedures/access_provisioning.md` | Joiner/mover/leaver steps via Gatehouse |
| `data-platform/workspace_isolation.md` | Tenant/workspace boundaries |
| `policies/onboarding_policy.md` | Day-one Gatehouse group checklist |
| `postmortems/2025-08-12-gatehouse-auth-outage.md` | Historical Gatehouse failure modes |

#### Cluster E — SLOs and Error Budgets

| Document | Viewpoint |
| -------- | --------- |
| `observability-platform/slo_framework.md` | How SLOs are defined in Beacon |
| `sre/error_budget_policy.md` | Budget spend and release freeze |
| `ai-platform/online_inference_slos.md` | Orion inference SLOs |
| `analytics-platform/analytics_release_process.md` | Release gates tied to SLOs |
| `support/support_slas.md` | Customer-facing SLA (distinct from internal SLO) |

#### Cluster F — Architecture Decisions (RFCs)

| Document | Viewpoint |
| -------- | --------- |
| `rfcs/rfc_001_clickhouse_migration.md` | Analytics query engine on Harbor data |
| `rfcs/rfc_002_feature_store_design.md` | Feature store boundaries (Orion + Harbor) |
| `rfcs/rfc_003_observability_rework.md` | Beacon ingestion architecture |
| `rfcs/rfc_004_multi_region_cells.md` | Atlas cell topology, Mercury/Harbor placement |
| `rfcs/rfc_005_llm_gateway.md` | Rejected — documents abandoned internal gateway |
| `rfcs/rfc_006_kafka_to_mercury_migration.md` | Superseded — historical streaming migration |

**Required cross-links:** Each Accepted RFC links to at least one platform overview and one operational doc. Rejected/Superseded RFCs must state what was chosen instead.

#### Cluster G — Incident History ↔ Design Intent (postmortems)

| Postmortem | RFC / architecture doc | Runbook |
| ---------- | ---------------------- | ------- |
| `2025-02-14-eu-central-outage.md` | `rfc_004_multi_region_cells.md` | `disaster_recovery.md`, `streaming_pipeline_guide.md` |
| `2025-06-01-feature-store-degradation.md` | `rfc_002_feature_store_design.md` | `feature_store_guide.md`, `ml_incident_playbook.md` |
| `2025-09-17-schema-registry-failure.md` | `schema_registry.md` | `backfill_procedures.md` |
| `2025-11-03-observability-ingestion-delay.md` | `rfc_003_observability_rework.md` | `alerting_and_routing.md` |
| `2026-01-22-model-serving-latency.md` | `model_serving_runbook.md` | `online_inference_slos.md` |
| `2025-08-12-gatehouse-auth-outage.md` | `security/access_management.md` | `access_provisioning.md` |

### Ownership Relationships

* Every doc lists **Owner** in front matter and a prose **Owner** section naming the responsible team alias.
* **Reviewers** differ from owners on cross-functional docs (e.g. `travel_policy.md` owned by HR, reviewed by Finance).
* Glossary (`company/glossary.md`) defines internal codenames and domain terms; platform docs use codenames consistently per [Internal Platform Systems](#internal-platform-systems);
* informal abbreviations may still collide (e.g. “DP” = Data Platform vs “data plane”) — intentional sparse-retrieval challenge.

### Process Dependencies

Document explicit “Prerequisites” where applicable:

* `emergency_change_process.md` → requires `change_management.md` exception path;
* `data_access_request.md` → requires `data_classification.md` labels and Gatehouse group approval;
* `model_serving_runbook.md` → requires `model_registry.md` promotion state and Orion release channel;
* `offboarding_checklist.md` → triggers `access_provisioning.md` Gatehouse revocation section;
* `streaming_pipeline_guide.md` → references `rfc_006` as superseded historical context;
* `ai_platform_overview.md` → references `rfc_005` rejection when discussing external LLM routing.

---

## Retrieval Complexity Strategy

The corpus is a **retrieval benchmark instrument**, not just demo filler. Authors must seed content to expose strategy differences.

### 1. Ambiguous Queries

Design questions answerable by multiple docs where **one** benchmark or “gold” doc is most authoritative:

| Query style | Competing docs | Gold doc (example) |
| ----------- | -------------- | ------------------ |
| “What do I do when paged overnight?” | `oncall_policy.md`, `incident_response.md`, `incident_management.md` | `oncall_policy.md` for rotation rules; `incident_response.md` for first steps |
| “How do we handle customer outages?” | `incident_response.md`, `customer_incident_comms.md`, `status_page_operations.md` | depends on sub-question |
| “What caused the eu-central outage?” | `2025-02-14-eu-central-outage.md`, `rfc_004_multi_region_cells.md`, `disaster_recovery.md` | postmortem for root cause; RFC for design intent |
| “pipeline failure troubleshooting” | batch vs Mercury streaming vs ML vs Atlas deploy runbooks | context-dependent |
| “security during incidents” | `security_policy.md`, `security_incident_bridge.md`, `incident_response.md` | `security_incident_bridge.md` for security join |
| “why no internal LLM gateway?” | `rfc_005_llm_gateway.md`, `ai_platform_overview.md` | rejected RFC is authoritative |

**Authoring guidance:** Include distinctive phrases in gold sections so rerankers can separate near-duplicates (e.g. exact SLA numbers, named roles, specific tool names).

### 2. Competing Documents

Pair docs with overlapping vocabulary but different intent:

* `support_slas.md` vs `sla_and_freshness.md` vs `online_inference_slos.md` — all discuss “SLA”;
* `travel_policy.md` vs `expense_policy.md` — both mention receipts and international travel;
* `rfc_005_llm_gateway.md` vs `ai_platform_overview.md` — gateway decision vs current architecture;
* `2025-11-03-observability-ingestion-delay.md` vs `rfc_003_observability_rework.md` — incident history vs intended Beacon design.

### 3. Similar Terminology (Dense vs Sparse)

* **Dense-favoring:** conceptual paraphrases (“work from home eligibility”, “distributed workforce policy”, “observability ingestion rework”);
* **Sparse-favoring:** exact tokens (`SEV-1`, `PagerDuty`, `RFC-004`, internal codenames **`Atlas`**, **`Beacon`**, **`Mercury`**, **`Orion`**, **`Ledger`**, **`Gatehouse`**, **`Harbor`**);
* **Fusion-favoring:** queries mixing codenames and paraphrase (“Beacon ingestion delay in eu-central cell”, “Orion canary rollback procedure”).

### 4. Ownership Questions

Embed explicit ownership statements:

* “The Data Platform team owns Harbor operations and Mercury job configuration.”
* “Gatehouse provisions workspace ACLs; Security owns the access policy.”
* “Finance approves expenses over $5,000; HR owns remote work eligibility.”

Supports future agent/eval questions like “Who approves international travel?”

### 5. Procedural Questions

Numbered steps with distinctive imperatives in benchmark-aligned docs:

* `incident_response.md` — “Step 1: Acknowledge the page within 5 minutes.”
* `onboarding_policy.md` — day-by-day onboarding timeline.
* `access_provisioning.md` — joiner ticket sequence.

Sparse retrieval should match “Step 1”, “within 5 minutes”, “acknowledge”.

### 6. Architecture Questions

Long explanatory sections with structure diagrams in prose:

* `data_platform_overview.md`, `observability_platform_overview.md`, `ai_platform_overview.md` — similar headings (“Overview”, “Control plane”, “Data plane”) but different content;
* RFCs vs platform overviews — RFCs contain **Decision** and **Alternatives**; overviews describe current state. Queries like “why did we choose ClickHouse?” should favor `rfc_001_clickhouse_migration.md`.

Reranking should prefer the platform-specific overview when the query names that platform; postmortems when the query asks about historical failures.

### 7. RFC and Postmortem Retrieval Patterns

| Query style | Gold doc type | Example |
| ----------- | ------------- | ------- |
| “Why was X rejected?” | Rejected RFC | `rfc_005_llm_gateway.md` |
| “What alternatives were considered for feature store?” | Accepted RFC | `rfc_002_feature_store_design.md` |
| “What was the root cause of the schema registry incident?” | Postmortem | `2025-09-17-schema-registry-failure.md` |
| “What follow-up actions came from the Beacon delay?” | Postmortem | `2025-11-03-observability-ingestion-delay.md` |
| “How does Atlas handle multi-region?” | Accepted RFC + overview | `rfc_004_multi_region_cells.md` |

### Difficulty Tier Tagging (implementation optional metadata)

Authors may add HTML comment at document end (not rendered in body search if stripped, but useful for human curation):

```markdown
<!-- retrieval_tier: benchmark | hard | medium -->
```

Do not rely on this for automated scoring in Plan 14.

---

## Evaluation Alignment

### Benchmark Contract (`retrieval_benchmark_v1.json`)

Plan 13 committed **70 cases** across **7 documents**. Registry paths are **frozen** for Plan 14:

| Document key | Required path | Department owner |
| ------------ | ------------- | ---------------- |
| `remote-work-policy` | `knowledge/policies/remote_work_policy.md` | HR |
| `onboarding-policy` | `knowledge/policies/onboarding_policy.md` | HR |
| `travel-policy` | `knowledge/policies/travel_policy.md` | Finance / HR |
| `security-policy` | `knowledge/policies/security_policy.md` | Security |
| `equipment-policy` | `knowledge/policies/equipment_policy.md` | HR / IT |
| `expense-policy` | `knowledge/policies/expense_policy.md` | Finance |
| `incident-response` | `knowledge/procedures/incident_response.md` | SRE |

### Required Actions

| Action | Owner | When |
| ------ | ----- | ---- |
| Create all seven files with content satisfying all 70 benchmark questions | Plan 14 implementation | Plan 14 |
| Keep `corpus_version: "v1"` unchanged | — | Plan 14 |
| Do **not** edit `data/evaluation/retrieval_benchmark_v1.json` | — | Plan 14 |

### Benchmark Content Checklist (per document)

Implementation must verify each question in `retrieval_benchmark_v1.json` is answerable from the target document body:

* **remote_work_policy** — 10 questions (eligibility, geography, core hours, bandwidth, coworking, approval chain, contractors, time zones, equipment for video, days per week).
* **onboarding_policy** — 10 questions (first day, probation, buddy, week-one training, equipment timing, documents, role training, manager checklist, payroll/benefits, credentials).
* **travel_policy** — 10 questions (airfare class, booking lead time, international approver, ride-share, per diem, trip extension, insurance, hotels, loyalty points, reimbursement docs).
* **security_policy** — 10 questions (password rotation, MFA, USB, phishing, unapproved software, encryption, lost devices, clean desk, breach notification, credential sharing).
* **equipment_policy** — 10 questions (laptop models, refresh cycle, damage, OS choice, return on exit, monitors/docks, broken hardware reporting, personal devices, accessories, sales phones).
* **expense_policy** — 10 questions (entertainment limit, submission deadline, internet, receipts, approval threshold, personal cards, pre-approval categories, currency, subscriptions, late reports).
* **incident_response** — 10 questions (first step, bridge lead, severity definitions, comms channels, legal involvement, post-incident reviews, sev-1 ack time, all-hands authority, customer notifications, forensic artifacts).

### Future Benchmark Expansion (out of Plan 14 scope)

When Plan 18 or a future evaluation revision adds cases:

1. Add new `document_key` entries to a new dataset file (e.g. `retrieval_benchmark_v2.json`);
2. Bump `corpus_version`;
3. Prefer new keys for platform docs (`data-platform-overview`, `oncall-policy`, etc.).

**Suggested v2 candidates** (document only — do not implement in Plan 14):

| Proposed key | Path |
| ------------ | ---- |
| `oncall-policy` | `knowledge/sre/oncall_policy.md` |
| `observability-overview` | `knowledge/observability-platform/observability_platform_overview.md` |
| `data-platform-overview` | `knowledge/data-platform/data_platform_overview.md` |
| `feature-store-guide` | `knowledge/ai-platform/feature_store_guide.md` |

### Path Normalization

Registry paths match indexing `SourceReference.document_path` values. Corpus files must use exact filenames. Index from repository root `knowledge/` so stored paths align with registry strings.

---

## Sample Document Outlines (12)

### 1. `knowledge/procedures/incident_response.md` (benchmark)

**Purpose:** Canonical step-by-step production incident response procedure.

**Owner:** SRE (`sre-oncall@acmecloud.io`)

**Sections:**

1. Overview and scope (production vs non-production)
2. Severity definitions (SEV-1 through SEV-4) with acknowledgment targets
3. Step 1 — Acknowledge and triage (explicit **5-minute** SEV-1 ack)
4. Step 2 — Open incident bridge (Zoom bridge, Slack `#incident-warroom`)
5. Step 3 — Assign Incident Commander and roles (IC, comms lead, scribe)
6. Step 4 — Customer impact assessment and status page update
7. Step 5 — Legal and security engagement criteria
8. Step 6 — Mitigation and recovery
9. Step 7 — Post-incident review requirements and template link
10. Forensic artifact preservation checklist
11. Related documents

**Expected cross-links:**

* `../sre/incident_management.md`
* `../sre/oncall_policy.md`
* `../security/security_incident_bridge.md`
* `../support/customer_incident_comms.md`
* `../postmortems/2025-02-14-eu-central-outage.md`
* `../observability-platform/alerting_and_routing.md`

**Internal systems referenced:** Atlas (cell status), Beacon (alert source), Gatehouse (war-room access).

---

### 2. `knowledge/policies/remote_work_policy.md` (benchmark)

**Purpose:** Employee remote and hybrid work eligibility and rules.

**Owner:** HR (`people-ops@acmecloud.io`)

**Sections:**

1. Purpose and applicability (employees vs contractors)
2. Eligibility criteria (role, tenure, performance)
3. Hybrid and fully remote schedules (days per week, core hours)
4. Geographic restrictions and international work
5. Time zone and availability expectations
6. Home office setup (cross-ref equipment policy)
7. Internet bandwidth minimum (**25 Mbps** download)
8. Coworking space rules
9. Approval workflow (manager + HR for permanent remote)
10. Exceptions and review cadence

**Expected cross-links:**

* `equipment_policy.md`, `security_policy.md`, `expense_policy.md`
* `../hr/pto_and_leave.md`

---

### 3. `knowledge/observability-platform/observability_platform_overview.md`

**Purpose:** Architecture of AcmeCloud Observe (metrics, logs, traces).

**Owner:** Observability Platform (`observe-platform@acmecloud.io`)

**Sections:**

1. Product positioning vs external APM tools
2. **Atlas** control plane integration for tenant config
3. **Beacon** ingestion pipeline (metrics, logs, traces)
4. Storage and indexing downstream of Beacon
5. Multi-tenant isolation and retention tiers
6. Integration with PagerDuty and incident workflow
7. SLO tooling integration
8. Regional deployment model (`eu-central` cell called out)
9. Link to `rfc_003_observability_rework.md`
10. Related documents

**Expected cross-links:**

* `metrics_collection.md`, `alerting_and_routing.md`, `slo_framework.md`
* `../rfcs/rfc_003_observability_rework.md`
* `../postmortems/2025-11-03-observability-ingestion-delay.md`
* `../sre/oncall_policy.md`
* `../procedures/incident_response.md`

---

### 4. `knowledge/data-platform/data_platform_overview.md`

**Purpose:** High-level architecture of AcmeCloud Data Lake.

**Owner:** Data Platform (`data-platform@acmecloud.io`)

**Sections:**

1. Platform capabilities and customer personas
2. Ingestion sources overview
3. **Harbor** storage layer (lakehouse, table formats, partitions)
4. Compute — batch jobs vs **Mercury** streaming runtime
5. Schema registry and governance
6. Workspace and tenant model via **Gatehouse**
7. SLAs and freshness guarantees (link to `sla_and_freshness.md`)
8. **Ledger** metering hooks for storage and compute
9. Security and classification hooks
10. Related documents

**Expected cross-links:**

* `ingestion_architecture.md`, `schema_registry.md`, `streaming_pipeline_guide.md`
* `../rfcs/rfc_004_multi_region_cells.md`, `../rfcs/rfc_006_kafka_to_mercury_migration.md`
* `../postmortems/2025-09-17-schema-registry-failure.md`

---

### 5. `knowledge/sre/oncall_policy.md`

**Purpose:** On-call rotation, paging, and escalation rules.

**Owner:** SRE (`sre-oncall@acmecloud.io`)

**Sections:**

1. Scope (which services require 24/7 on-call)
2. Rotation structure (primary, secondary, shadow)
3. PagerDuty schedule and handoff checklist
4. Escalation timeouts (primary **15 min**, secondary **10 min**)
5. Compensation and time-off rules
6. Incident bridge expectations when paged
7. Relationship to `incident_response.md` (defer step-by-step)
8. On-call readiness requirements (laptop, VPN, access)
9. Escalation to management
10. Related documents

**Expected cross-links:**

* `../procedures/incident_response.md`
* `incident_management.md`
* `../observability-platform/alerting_and_routing.md`
* `../engineering/service_tiers.md`

---

### 6. `knowledge/policies/security_policy.md` (benchmark)

**Purpose:** Company-wide information security policy for all employees.

**Owner:** Security (`security@acmecloud.io`)

**Sections:**

1. Scope and compliance baseline (SOC 2)
2. Account security (MFA required, password rules, no sharing)
3. Device security (encryption, lost device reporting)
4. Acceptable use and software installation
5. Removable media and USB restrictions
6. Phishing reporting procedure
7. Clean desk and confidential document handling
8. Data breach notification chain (CISO, legal, CEO)
9. Remote work security controls
10. Policy violations and exceptions

**Expected cross-links:**

* `../security/access_management.md`, `secrets_management.md`, `data_classification.md`
* `remote_work_policy.md`, `equipment_policy.md`
* `../procedures/incident_response.md`

---

### 7. `knowledge/ai-platform/model_serving_runbook.md`

**Purpose:** Operational runbook for deploying and rolling back inference services.

**Owner:** AI Platform (`ml-platform@acmecloud.io`)

**Sections:**

1. Prerequisites (model registry promotion, feature store compatibility, Orion release channel)
2. **Orion** deployment pipeline stages (canary, full rollout)
3. Health checks and inference SLO monitoring via Beacon
4. Rollback triggers (latency, error rate, drift)
5. Coordination with Atlas for cell-level routing
6. Coordination with SRE for production changes
7. ML-specific incident severities
8. Link to postmortem `2026-01-22-model-serving-latency.md`
9. Post-deploy validation
10. Related documents

**Expected cross-links:**

* `model_registry.md`, `online_inference_slos.md`, `ml_incident_playbook.md`
* `../rfcs/rfc_002_feature_store_design.md`
* `../postmortems/2026-01-22-model-serving-latency.md`
* `../sre/deployment_runbook.md`, `change_management.md`
* `../procedures/incident_response.md`

---

### 8. `knowledge/sre/incident_management.md`

**Purpose:** Incident role definitions, severity matrix, and communication cadence (not step-by-step response).

**Owner:** SRE (`sre-incidents@acmecloud.io`)

**Sections:**

1. Incident vs problem vs change request
2. Severity matrix (customer impact, data loss, security)
3. Role definitions (IC, comms lead, scribe, domain experts)
4. Bridge cadence and executive updates
5. All-hands incident declaration authority
6. Legal involvement criteria (cross-ref security)
7. Post-incident review policy
8. Metrics (MTTA, MTTR)
9. Tooling (PagerDuty, Jira incident project)
10. Related documents — **must** link to `incident_response.md` for procedures

**Expected cross-links:**

* `../procedures/incident_response.md`
* `oncall_policy.md`, `postmortem_template.md`
* `../postmortems/2025-02-14-eu-central-outage.md`
* `../support/customer_incident_comms.md`

---

### 9. `knowledge/company/company_overview.md`

**Purpose:** Onboarding-friendly company introduction.

**Owner:** Company (`hello@acmecloud.io`)

**Sections:**

1. Mission and history
2. Product suite summary (four platforms)
3. Customer segments and example logos (fictional)
4. Org highlights by department
5. Values and operating principles
6. Key locations and remote-first philosophy
7. How to navigate internal documentation (RFCs, postmortems, glossary codenames)
8. Links to `glossary.md` (Atlas, Beacon, etc.) and `product_portfolio.md`

**Expected cross-links:**

* `product_portfolio.md`, `org_structure.md`, `glossary.md`
* `../policies/code_of_conduct.md`
* `../policies/onboarding_policy.md`

---

### 10. `knowledge/ai-platform/feature_store_guide.md`

**Purpose:** How teams register, version, and consume features for training and serving.

**Owner:** AI Platform (`feature-store@acmecloud.io`)

**Sections:**

1. Feature store architecture (online vs offline store backed by Harbor)
2. Entity definitions and naming conventions
3. Feature registration workflow
4. Backfill and point-in-time correctness
5. Integration with **Orion** serving and `model_training_pipelines.md`
6. Access control via **Gatehouse** and PII handling
7. Monitoring and freshness alerts (Beacon)
8. Common failure modes (link postmortem `2025-06-01-feature-store-degradation.md`)
9. Alignment with `rfc_002_feature_store_design.md`
10. Related documents

**Expected cross-links:**

* `model_training_pipelines.md`, `model_registry.md`, `responsible_ai_guidelines.md`
* `../rfcs/rfc_002_feature_store_design.md`
* `../postmortems/2025-06-01-feature-store-degradation.md`
* `../data-platform/schema_registry.md` (terminology collision: “registry”)
* `../security/data_classification.md`

---

### 11. `knowledge/rfcs/rfc_004_multi_region_cells.md`

**Purpose:** Accepted architecture decision for Atlas cell topology across `us-east`, `us-west`, `eu-central`.

**Owner:** SRE / Engineering (`platform-arch@acmecloud.io`)

**RFC status:** Accepted

**Sections:**

1. **Context** — single-region scaling limits, data residency requirements
2. **Decision** — three cells, Atlas routing, Harbor/Mercury placement per cell, Ledger per-cell metering
3. **Alternatives considered** — active-active all regions; single region + CDN; customer-dedicated stacks
4. **Consequences** — operational complexity, failover drills, cross-cell query limitations
5. **Related systems** — Atlas, Harbor, Mercury, Ledger
6. **Related documents** — `data_platform_overview.md`, `disaster_recovery.md`, postmortem `2025-02-14-eu-central-outage.md`

---

### 12. `knowledge/postmortems/2025-11-03-observability-ingestion-delay.md`

**Purpose:** SEV-2 review of Beacon ingestion backlog affecting alert delivery latency.

**Owner:** SRE + Observability Platform

**Sections:**

1. **Summary** — 47-minute alert delay in `us-west`
2. **Impact** — delayed pages, no customer data loss
3. **Timeline** — detection through resolution (UTC timestamps)
4. **Root cause** — misconfigured Beacon shard allocator after Atlas cell migration
5. **Contributing factors** — insufficient canary monitoring, outdated runbook
6. **Detection** — internal SLO burn alert on Beacon lag
7. **Resolution** — shard rebalance, Atlas config rollback
8. **Follow-up actions** — JIRA tickets, owners, due dates
9. **Owning teams** — Observability Platform, SRE
10. **Related runbooks** — `alerting_and_routing.md`, `incident_response.md`, `rfc_003_observability_rework.md`

---

## Implementation Checklist

### Phase 1 — Scaffold

- [x] Add `knowledge/` to `.gitignore`
- [x] Document regeneration command in this plan and `docs/PROGRESS.md`
- [x] Create `knowledge/README.md` with department index, RFC index, postmortem index, internal systems table, benchmark path callout (local generation)
- [x] Create directory structure per [Corpus Layout](#corpus-layout) including `rfcs/` and `postmortems/` (local generation)
- [x] Add authoring templates (standard doc, RFC, postmortem) to `knowledge/README.md`

### Phase 2 — Benchmark Documents (blocking)

- [x] Author `knowledge/policies/remote_work_policy.md` (satisfy 10 benchmark questions)
- [x] Author `knowledge/policies/onboarding_policy.md`
- [x] Author `knowledge/policies/travel_policy.md`
- [x] Author `knowledge/policies/security_policy.md`
- [x] Author `knowledge/policies/equipment_policy.md`
- [x] Author `knowledge/policies/expense_policy.md`
- [x] Author `knowledge/procedures/incident_response.md`
- [x] Manual review: each of 70 benchmark questions answerable from gold doc

### Phase 3 — Company Foundation and Internal Systems

- [x] Author `company/glossary.md` with all seven internal codenames
- [x] Author `company/product_portfolio.md` with platform-to-system mapping
- [x] Author remaining `company/` docs (2)

### Phase 4 — RFCs and Postmortems

- [x] Author all 6 RFCs with required sections and status labels
- [x] Author all 6 postmortems with required sections
- [x] Verify Cluster F and Cluster G cross-links

### Phase 5 — Relationship Clusters

- [x] Implement Cluster A (incident + postmortems) cross-links
- [x] Implement Cluster B (remote work) cross-links
- [x] Implement Cluster C (pipeline terminology) docs
- [x] Implement Cluster D (access/identity + Gatehouse) cross-links
- [x] Implement Cluster E (SLO/SLA) cross-links

### Phase 6 — Department Corpora

- [x] `engineering/` (6 docs)
- [x] `data-platform/` (10 docs) — Harbor, Mercury throughout
- [x] `analytics-platform/` (6 docs)
- [x] `ai-platform/` (8 docs) — Orion throughout
- [x] `observability-platform/` (6 docs) — Beacon throughout
- [x] `sre/` (9 docs)
- [x] `security/` (7 docs) — Gatehouse throughout
- [x] `product/` (4 docs)
- [x] `support/` (5 docs)
- [x] `finance/` (3 docs) — Ledger in `cloud_spend_governance.md`
- [x] `hr/` (3 docs)
- [x] `policies/` remaining (2 docs: acceptable use, code of conduct)
- [x] `procedures/` remaining (4 docs)

### Phase 7 — Quality Gate

- [x] Total document count is **96** per inventory (within 80–100) after local generation
- [x] `knowledge/` is listed in `.gitignore`
- [x] No generated `knowledge/*.md` files are staged in git
- [x] Regeneration command documented (`python3 tools/knowledge_generator/generator.py`)
- [x] Every document has YAML front matter per conventions
- [x] RFCs and postmortems include required section schemas
- [x] Every document meets minimum word count
- [x] Every non-benchmark document has ≥ 2 cross-folder links
- [x] Internal codenames used consistently per [Internal Platform Systems](#internal-platform-systems)
- [x] No files from [Removed from Inventory](#removed-from-inventory) authored
- [x] No real company names, real URLs, or live API keys
- [x] Spell-check and consistent AcmeCloud product naming
- [x] Update `docs/PROGRESS.md` with Plan 14 completion entry
- [x] Move this plan to `docs/plans/completed/` when acceptance criteria pass

**Deferral rule:** The authoritative manifest is **96 files**. Do not defer benchmark docs, RFCs, postmortems, `glossary.md`, or Cluster A incident documents.

---

## Acceptance Criteria

- [x] **Company narrative** — AcmeCloud Analytics identity, four platforms, ~500 employees, seven internal systems documented
- [x] **Department structure** — all listed departments represented with ownership
- [x] **Corpus specification** — this plan defines layout, inventory, conventions, and benchmark alignment
- [x] **Local corpus** — `knowledge/` exists locally after generation with layout matching this plan including `rfcs/` and `postmortems/`; `knowledge/README.md` present
- [x] **Git hygiene** — `knowledge/` is ignored by git; no generated corpus markdown files are staged
- [x] **Regeneration** — command `python3 tools/knowledge_generator/generator.py` documented in this plan and `docs/PROGRESS.md`
- [x] **Document inventory** — **96** markdown files per authoritative manifest (within 80–100) after local generation
- [x] **RFC layer** — 6 RFCs with status, context, decision, alternatives, consequences, related systems, related documents
- [x] **Postmortem layer** — 6 postmortems with all required sections and runbook cross-links
- [x] **Internal systems** — Atlas, Beacon, Mercury, Orion, Ledger, Gatehouse, Harbor in glossary, product portfolio, platform docs, RFCs, postmortems, and incident cluster
- [x] **Knowledge relationships** — clusters A–G implemented with cross-links
- [x] **Retrieval complexity** — ambiguous/competing terminology, codenames, RFC/postmortem patterns per strategy section
- [x] **Evaluation alignment** — seven benchmark paths exist in local corpus; 70 questions manually verified; no benchmark JSON edits
- [x] **Sample outlines** — twelve representative outlines realized as full documents
- [x] **Non-scope respected** — no changes to retrieval, indexing, storage, MCP, agent, evaluation code, CLI, or models; no committed corpus files
- [x] **Progress recorded** — `docs/PROGRESS.md` updated on completion

---

## Risks and Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Generated corpus accidentally committed | `knowledge/` in `.gitignore`; verify `git status` before commit |
| Fresh clone missing corpus | Document `python3 tools/knowledge_generator/generator.py` in plan and PROGRESS; tracked manifest/templates make regeneration reproducible; Plan 15 demo bootstrap may automate |
| Benchmark paths drift from corpus layout | Frozen paths in [Evaluation Alignment](#evaluation-alignment); verify after regeneration |
| Corpus too small for chunking demos | Enforce minimum word counts; 96-doc manifest |
| Inconsistent internal codenames | Glossary is authoritative; Phase 7 consistency check |
| RFC/postmortem sections omitted | Required section schemas in authoring conventions; Phase 7 checklist |
| Accidental real PII or trademarks | Fictional customers, emails, and Confluence IDs only |
| Over-duplication hurts reranker signal | Gold docs use distinctive numbers/names; competing docs overlap vocabulary only |
| Implementation agent invents new architecture | All files must map to inventory; no new top-level folders without plan revision |
| Corpus authorship bottleneck | Phase 2 benchmark docs first; clusters second; department fill parallelizable |

---

## Follow-Up Work (Not Plan 14)

| Item | Target |
| ---- | ------ |
| Plan 15 — Demo Bootstrap Workflow | `rag demo info`, `rag demo load`, `rag demo reset`; generate and index local `knowledge/` corpus |
| Plan 16 — Real Embeddings Integration | BAAI/bge-m3 for indexing and retrieval embeddings |
| Plan 17 — Real Reranker Integration | BAAI/bge-reranker-v2-m3 cross-encoder runtime |
| Plan 18 — End-to-End Evaluation | Dense vs Sparse vs Fusion vs Rerank benchmark comparison (`ComparisonReport`) |
| Plan 19 — Interactive Chat Experience | `rag chat`; agent, MCP, and source-citation demo UX |
| `retrieval_benchmark_v2.json` | Additional document keys for platform and SRE docs |
| Integration test indexing full corpus | `tests/integration/evaluation/` conftest |
| `PROJECT.md` knowledge base section update | Reference AcmeCloud Analytics by name (optional docs chore) |

---

## Readiness Assessment

**Completed.** Plan 13 evaluation framework is complete. Benchmark registry paths are declared. Corpus specification is archived; local generation produces the gitignored `knowledge/` tree.

Post-completion workflow:

1. Run `python3 tools/knowledge_generator/generator.py` from repository root.
2. Confirm **96** files under `knowledge/` and `git check-ignore knowledge/README.md`.
3. Index from local `knowledge/` for demos and evaluation.
4. Do not stage or commit generated `knowledge/*.md` files.

---

## Checklist (Plan Meta)

- [x] Plan created in `docs/plans/active/`
- [x] Corpus implemented
- [x] Acceptance criteria satisfied
- [x] `docs/PROGRESS.md` updated
- [x] Plan moved to `docs/plans/completed/`
