# ruff: noqa: E501, F541
"""Document-type-specific authoring templates for Plan 14 synthetic corpus."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

type Section = tuple[str, list[str]]
type DocType = Literal[
    "architecture",
    "runbook",
    "policy",
    "handbook",
    "rfc",
    "postmortem",
]
type Topic = tuple[str, str]

CELLS = ("us-east", "us-west", "eu-central")


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _seed(path: str, salt: str = "") -> int:
    return int(hashlib.sha256(f"{path}:{salt}".encode()).hexdigest(), 16)


def _pick(path: str, options: list[str], offset: int = 0) -> str:
    return options[(_seed(path) + offset) % len(options)]


def _cell(path: str, offset: int = 0) -> str:
    return CELLS[(_seed(path) + offset) % len(CELLS)]


def _ticket(path: str, offset: int = 0) -> str:
    return f"DOCS-{_seed(path, str(offset)) % 9000 + 1000}"


def _inc(path: str, offset: int = 0) -> str:
    return f"INC-{_seed(path, f'inc{offset}') % 9000 + 1000}"


def classify_doc_type(path: str) -> DocType | str:
    if path == "company/glossary.md":
        return "glossary"
    if path.startswith("rfcs/"):
        return "rfc"
    if path.startswith("postmortems/"):
        return "postmortem"
    if path.startswith("policies/"):
        return "policy"
    if path.endswith("_overview.md") or "architecture" in path:
        return "architecture"
    if any(token in path for token in ("runbook", "playbook", "backfill_procedures")):
        return "runbook"
    if path.startswith("procedures/"):
        return "policy"
    if any(
        token in path
        for token in (
            "handbook",
            "standards",
            "guidelines",
            "framework",
            "sdlc",
            "code_review",
            "branching",
            "testing_strategy",
            "service_tiers",
            "release_process",
            "checklist",
            "lifecycle",
            "governance",
            "classification",
            "isolation",
            "lineage",
            "registry",
            "slos",
            "policy",
            "matrix",
            "comms",
            "management",
            "planning",
            "oncall",
            "change",
            "deployment",
            "disaster",
            "incident",
            "alerting",
            "routing",
            "freshness",
            "quality",
            "semantic",
            "dashboard",
            "query_performance",
            "self_serve",
            "feature_store",
            "training",
            "registry",
            "inference",
            "ingestion",
            "batch_pipeline",
            "streaming",
            "workspace",
            "access",
            "secrets",
            "vulnerability",
            "customer_data",
            "prd",
            "roadmap",
            "pricing",
            "escalation",
            "support",
            "finops",
            "cloud_spend",
            "pto",
            "offboarding",
            "performance",
            "guide",
        )
    ):
        return "handbook"
    return "handbook"


def _expand_topic(
    path: str,
    heading: str,
    summary: str,
    owner: str,
    system: str,
    offset: int,
) -> str:
    """One substantive paragraph from a topic summary — no boilerplate labels."""
    cell = _cell(path, offset)
    ticket = _ticket(path, offset)
    variants = [
        (
            f"**{heading}** — {summary} "
            f"In production, {owner} validates this through {system} dashboards in cell `{cell}` "
            f"before quarterly review; changes are tracked under {ticket}."
        ),
        (
            f"For **{heading}**, {summary} "
            f"On-call engineers cross-check {system} metrics against Atlas routing tables in `{cell}` "
            f"and document outcomes in the {owner} Confluence space."
        ),
        (
            f"**{heading}** at AcmeCloud: {summary} "
            f"Security and {owner} require Gatehouse ACL review when {system} paths change; "
            f"last formal audit referenced {ticket}."
        ),
        (
            f"Regarding **{heading}**: {summary} "
            f"Cell `{cell}` runs staged validation on {system} before Atlas promotes configuration; "
            f"rollback steps must be attached to {ticket}."
        ),
    ]
    return _pick(path, variants, offset + _seed(heading) % 7)


def build_architecture_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
) -> list[Section]:
    sys_label = ", ".join(systems) if systems else "Atlas"
    primary = systems[0] if systems else "Atlas"
    secondary = systems[1] if len(systems) > 1 else "Harbor"
    return [
        (
            "Overview",
            [
                f"{title} documents how AcmeCloud's {owner} organization designs, deploys, and operates "
                f"the platform services behind customer-facing products.",
                f"This architecture spans regional cells (`us-east`, `us-west`, `eu-central`) and integrates "
                f"with internal systems: {sys_label}.",
            ],
        ),
        (
            "Context",
            [
                topics[0][1]
                if topics
                else f"Platform teams maintain {title.lower()} as the canonical reference for {sys_label} boundaries.",
                f"Readers include on-call engineers, new hires, and architecture reviewers evaluating changes to {primary}.",
            ],
        ),
        (
            "System Components",
            [
                f"Core components include {sys_label}, each with distinct ownership boundaries and SLO dashboards in Beacon.",
                *[
                    _expand_topic(path, h, s, owner, systems[i % len(systems)], i)
                    for i, (h, s) in enumerate(topics)
                ],
            ],
        ),
        (
            "Control Plane",
            [
                f"**Atlas** provisions tenants, routes traffic across cells, and gates production promotes for {primary} workloads. "
                f"Configuration snapshots are versioned; emergency rollback uses snapshot restore per "
                f"[Deployment Runbook](../sre/deployment_runbook.md).",
                f"**Gatehouse** enforces workspace ACLs and service accounts that {owner} teams use to access {sys_label}. "
                f"Break-glass access during incidents requires active IC approval.",
            ],
        ),
        (
            "Data Plane",
            [
                f"The data plane executes customer workloads: {secondary} stores curated datasets, "
                f"while {primary} handles request-path processing described in this document.",
                f"Cross-cell data movement is denied by default; Atlas metadata records allowed replication paths "
                f"for compliance with EU residency requirements.",
            ],
        ),
        (
            "Dependencies",
            [
                f"Upstream dependencies include Atlas routing, Gatehouse identity, and Ledger metering for capacity planning.",
                f"Downstream consumers include Insights dashboards, Support runbooks, and SRE error-budget reporting "
                f"when {primary} SLOs burn.",
                f"RFC and postmortem records in `knowledge/rfcs/` and `knowledge/postmortems/` document major dependency changes.",
            ],
        ),
        (
            "Scaling Model",
            [
                f"Horizontal scaling adds shards per cell; {owner} capacity reviews occur monthly with Finance via Ledger usage trends.",
                f"Autoscaling policies target 70% average utilization with 15-minute cooldown to avoid oscillation during deploys.",
                f"Large tenants may receive dedicated cell partitions after architecture review board approval.",
            ],
        ),
        (
            "Operational Ownership",
            [
                f"{owner} (`{path}`) owns day-2 operations, on-call rotations, and documentation freshness.",
                f"Production changes require two reviewer approvals when touching Tier-0 services; "
                f"Beacon dashboard links are mandatory in change tickets.",
                f"Quarterly game days validate failover for `{_cell(path)}` using synthetic load generators.",
            ],
        ),
        (
            "Failure Modes",
            [
                f"Degraded {primary} latency or elevated error rates trigger paging via PagerDuty; "
                f"mitigation follows [Incident Response](../procedures/incident_response.md).",
                f"Partial cell isolation may occur when Atlas routing detects unhealthy shards; "
                f"customers in other cells remain unaffected when blast radius is contained.",
                f"Post-incident reviews must reference this document when failure class matches {title.lower()}.",
            ],
        ),
        (
            "Related Systems",
            [
                f"Authoritative codename definitions live in [Glossary](../company/glossary.md). "
                f"Systems referenced here: {sys_label}.",
                f"FinOps tracks spend through Ledger; Security reviews Gatehouse policy changes quarterly.",
            ],
        ),
    ]


def build_runbook_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
) -> list[Section]:
    primary = systems[0] if systems else "Atlas"
    steps = [s for _, s in topics]
    step_headings = [h for h, _ in topics]
    return [
        (
            "Purpose",
            [
                f"This runbook guides {owner} engineers through `{title}` for production systems ({', '.join(systems)}).",
                f"Use during planned maintenance or incident mitigation when {primary} behavior must change under time pressure.",
            ],
        ),
        (
            "Preconditions",
            [
                f"Active Gatehouse session with `{path.replace('/', '-').replace('.md', '')}-write` group membership.",
                f"Change ticket {_ticket(path)} or active incident bridge for emergency execution.",
                f"Beacon dashboards for {primary} open and recording baseline metrics for `{_cell(path)}`.",
                steps[0]
                if steps
                else f"Confirm {primary} health checks are green before proceeding.",
            ],
        ),
        (
            "Procedure",
            [
                *[
                    f"**Step {i + 1} — {step_headings[i]}:** {steps[i]} "
                    f"Execute in `{_cell(path, i)}`; verify {systems[i % len(systems)]} metrics between steps."
                    for i in range(len(topics))
                ],
                f"Record each command and Atlas deployment ID in the incident or change ticket.",
                f"If execution exceeds 30 minutes without progress, escalate per the Escalation section below.",
            ],
        ),
        (
            "Validation",
            [
                f"Confirm {primary} P99 latency and error rate return to SLO within 15 minutes of completion.",
                f"Run synthetic probes tagged `runbook-{path.rsplit('/', maxsplit=1)[-1].replace('.md', '')}` against `{_cell(path)}`.",
                "Support queue volume should not increase; check #support-warroom for customer reports.",
            ],
        ),
        (
            "Rollback",
            [
                f"Revert last Atlas deployment using snapshot restore documented in [Deployment Runbook](../sre/deployment_runbook.md).",
                f"For {primary} canary releases, flip traffic to previous stable version via Orion/Atlas route table.",
                f"Document rollback timestamp and validating engineer in {_inc(path)} or linked change ticket.",
            ],
        ),
        (
            "Escalation",
            [
                f"Page `{owner.lower().replace(' ', '-')}-oncall` if validation fails after one rollback attempt.",
                f"SEV-1: engage IC and open bridge per [Incident Response](../procedures/incident_response.md).",
                f"VP Platform (Sam Okonkwo) may declare all-hands incident if multiple cells are affected.",
            ],
        ),
        (
            "Related Incidents",
            [
                f"Review postmortems involving {', '.join(systems)} before modifying this runbook.",
                f"Link new incidents to {_ticket(path, 99)} documentation update tasks within five business days.",
            ],
        ),
    ]


def build_policy_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
) -> list[Section]:
    return [
        (
            "Purpose",
            [
                f"{title} establishes mandatory requirements for {owner} stakeholders at AcmeCloud Analytics.",
                f"This policy supports consistent operations across Gatehouse-protected systems and regional cells.",
            ],
        ),
        (
            "Scope",
            [
                f"Applies to all employees, contractors, and partners with access to AcmeCloud systems referenced in `{path}`.",
                "Exceptions require written approval from the policy owner and HR or Legal where applicable.",
            ],
        ),
        (
            "Requirements",
            [
                *[f"**{h}:** {s}" for h, s in topics],
                "All production access must route through Gatehouse; shadow admin accounts are prohibited.",
                f"{owner} publishes an annual attestation summary to the compliance committee.",
                "Compliance evidence may be requested during quarterly audits; violations are tracked in the policy register with remediation SLAs.",
            ],
        ),
        (
            "Exceptions",
            [
                f"Temporary exceptions during SEV-1 incidents follow the emergency change process with retroactive approval within 24 hours.",
                f"{owner} may grant short-term exceptions for migrations documented in {_ticket(path)} with Security sign-off.",
            ],
        ),
        (
            "Enforcement",
            [
                f"Violations are escalated to {owner} and HR; repeated violations may result in access revocation via Gatehouse.",
                "Internal compliance scans compare Gatehouse group membership to Workday records monthly.",
                f"Security partners with {owner} on investigations involving customer or confidential data.",
            ],
        ),
        (
            "Review Cycle",
            [
                f"{owner} reviews this policy annually and after material regulatory or product changes.",
                f"Employees submit feedback via `#policy-feedback` Slack; approved updates publish within ten business days.",
                f"Last substantive review tracked under {_ticket(path, 1)} in the compliance register.",
            ],
        ),
    ]


def build_handbook_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
) -> list[Section]:
    sys_label = ", ".join(systems) if systems else "Atlas"
    primary = systems[0] if systems else "Atlas"
    mid = max(1, len(topics) // 2 + 1)
    return [
        (
            "Overview",
            [
                f"{title} is the {owner} reference for how teams build, ship, and operate software at AcmeCloud.",
                f"It complements platform runbooks and applies to engineers working with {sys_label} across all regional cells.",
                f"New hires complete LMS training modules referencing `{path}` before receiving Gatehouse production elevation.",
            ],
        ),
        (
            "Principles",
            [
                *[f"**{h}:** {s}" for h, s in topics[:mid]],
                "Documentation precedes production changes; design decisions link to RFCs when cross-team impact exists.",
                f"Blameless postmortems are mandatory for SEV-1/SEV-2 events touching {sys_label}.",
            ],
        ),
        (
            "Responsibilities",
            [
                f"Engineering managers ensure direct reports follow this handbook before Atlas production access.",
                f"Staff engineers mentor teams on {sys_label} best practices and review architecture exceptions.",
                *[f"**{h}:** {s}" for h, s in topics[mid:]],
            ],
        ),
        (
            "Operating Model",
            [
                f"Teams work in two-week sprints with trunk-based development and Atlas-mediated deploys to `{_cell(path)}` first.",
                "Code review requires two approvals for Tier-0 paths; on-call engineers hold rollback authority during incidents.",
                "Cross-team changes coordinate through architecture office hours and Jira epics linked to RFCs.",
                f"{owner} publishes a quarterly engineering newsletter summarizing changes to `{path}`.",
            ],
        ),
        (
            "Review Process",
            [
                f"{owner} owns quarterly handbook reviews; material updates require director approval.",
                "Proposed edits open as GitHub PRs to the internal docs repo with required reviewer from document owner.",
                "Training LMS modules reference this document; completion is tracked before Gatehouse prod elevation.",
            ],
        ),
        (
            "References",
            [
                f"Internal systems glossary: [Glossary](../company/glossary.md). Platform dependencies: {sys_label}.",
                "Incident handling: [Incident Response](../procedures/incident_response.md). "
                "Change management: [Change Management](../sre/change_management.md).",
                f"Service tiers and paging expectations: [Service Tiers](../sre/service_tiers.md) when {primary} is involved.",
            ],
        ),
    ]


def build_sections(
    doc_type: DocType,
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
) -> list[Section]:
    builders = {
        "architecture": build_architecture_sections,
        "runbook": build_runbook_sections,
        "policy": build_policy_sections,
        "handbook": build_handbook_sections,
    }
    if doc_type in builders:
        return builders[doc_type](path, title, owner, systems, topics)
    return build_handbook_sections(path, title, owner, systems, topics)


def pad_sections_to_min_words(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    sections: list[Section],
    min_words: int,
    doc_type: DocType | str,
) -> list[Section]:
    """Add unique sentences without labeled template prefixes."""
    mutable: list[list[str | list[str]]] = [[h, list(ps)] for h, ps in sections]
    idx = 0
    max_additions = 50
    while word_count(_assemble(title, mutable)) < min_words and idx < max_additions:
        sec_i = idx % len(mutable)
        heading = str(mutable[sec_i][0])
        paras: list[str] = mutable[sec_i][1]  # type: ignore[assignment]
        sys = systems[idx % len(systems)] if systems else "Atlas"
        cell = _cell(path, idx)
        ticket = _ticket(path, idx + 10)
        if doc_type == "glossary":
            candidates = [
                f"Technical Writing maintains {heading} examples in Confluence space DOCS; last refresh {ticket}.",
                f"New hires quiz on {heading} definitions in LMS module ACME-101 before platform access.",
                f"Customer-facing docs must not use the codename {heading} without Legal review.",
                f"RFC index cross-links {heading} mentions to authoritative definitions in this section.",
                f"Postmortems involving {heading} must link here in the root-cause narrative ({ticket}).",
            ]
        else:
            candidates = [
                f"{owner} validated {heading.lower()} on {sys} in `{cell}` during the Q1 game day; notes in {ticket}.",
                f"FinOps correlated {sys} usage with Ledger exports when reviewing {heading.lower()} for `{path}` ({ticket}).",
                f"Security attested Gatehouse groups tied to {heading.lower()} remained least-privilege after the `{cell}` audit ({ticket}).",
                f"SRE paired with {owner} on a {sys} rollback drill covering {heading.lower()} scenarios in `{cell}` ({ticket}).",
                f"Architecture review referenced {heading.lower()} when approving the `{cell}` {sys} change window ({ticket}).",
            ]
        para = candidates[idx % len(candidates)]
        if para not in paras:
            paras.append(para)
        idx += 1
    return [(str(s[0]), list(s[1])) for s in mutable]  # type: ignore[arg-type]


def _assemble(title: str, sections: list[list[str | list[str]]]) -> str:
    parts = [title]
    for heading, paras in sections:
        parts.append(str(heading))
        parts.extend(str(p) for p in paras)  # type: ignore[union-attr]
    return " ".join(parts)


def section_headings(sections: list[Section]) -> list[str]:
    return [h for h, _ in sections]


TEMPLATE_CATALOG: dict[DocType | str, list[str]] = {
    "architecture": [
        "Overview",
        "System Components",
        "Control Plane",
        "Data Plane",
        "Dependencies",
        "Scaling Model",
        "Operational Ownership",
        "Failure Modes",
        "Related Systems",
    ],
    "runbook": [
        "Purpose",
        "Preconditions",
        "Procedure",
        "Validation",
        "Rollback",
        "Escalation",
        "Related Incidents",
    ],
    "policy": [
        "Purpose",
        "Scope",
        "Requirements",
        "Exceptions",
        "Enforcement",
        "Review Cycle",
    ],
    "handbook": [
        "Overview",
        "Principles",
        "Responsibilities",
        "Operating Model",
        "Review Process",
        "References",
    ],
    "rfc": [
        "Context",
        "Problem",
        "Decision",
        "Alternatives Considered",
        "Tradeoffs",
        "Consequences",
        "Rollout",
        "Related Systems",
    ],
    "postmortem": [
        "Summary",
        "Impact",
        "Timeline",
        "Root Cause",
        "Contributing Factors",
        "Detection",
        "Resolution",
        "Action Items",
    ],
}
