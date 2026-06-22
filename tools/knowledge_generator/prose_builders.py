# ruff: noqa: E501, F541
# pyright: reportPrivateUsage=false
"""Type-specific prose builders for synthetic corpus generation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from corpus_templates_base import (
    Topic,
    _cell,
    _inc,
    _ticket,
    word_count,
)
from corpus_templates_base import (
    build_architecture_sections as _base_architecture_sections,
)
from corpus_templates_base import (
    build_handbook_sections as _base_handbook_sections,
)
from corpus_templates_base import (
    build_policy_sections as _base_policy_sections,
)
from corpus_templates_base import (
    build_runbook_sections as _base_runbook_sections,
)

if TYPE_CHECKING:
    from schemas import DocumentSpec

type Section = tuple[str, list[str]]


_META_FACT = re.compile(
    r"^(FinOps correlated|SRE validated|Security attested|Architecture review referenced|SRE paired|"
    r".* during the Q1 game day|.* remained least-privilege after the .* audit)",
    re.IGNORECASE,
)


def build_document_sections(
    document: DocumentSpec,
    required_sections: tuple[str, ...],
) -> list[Section]:
    systems = list(document.related_systems)
    topics = _topics_from_facts(document.required_facts)
    builders = {
        "architecture": build_architecture_sections,
        "runbook": build_runbook_sections,
        "policy": build_policy_sections,
        "handbook": build_handbook_sections,
        "rfc": build_rfc_sections,
        "postmortem": build_postmortem_sections,
        "company_profile": build_company_profile_sections,
        "organization": build_organization_sections,
        "product_portfolio": build_product_portfolio_sections,
        "glossary": build_glossary_sections,
        "finance_policy": build_finance_policy_sections,
        "finance_process": build_finance_process_sections,
        "finance_operations": build_finance_operations_sections,
    }
    builder = builders.get(document.type, build_handbook_sections)
    return builder(
        document.path,
        document.title,
        document.owner,
        systems,
        topics,
        document.required_facts,
    )


def pad_sections_to_min_words(
    document: DocumentSpec,
    sections: list[Section],
) -> list[Section]:
    mutable: list[list[str | list[str]]] = [
        [heading, list(paras)] for heading, paras in sections
    ]
    seen = {
        re.sub(r"\s+", " ", paragraph.lower()).strip()
        for _, paragraphs in sections
        for paragraph in paragraphs
    }
    used_stems: set[str] = set()
    idx = 0
    systems = list(document.related_systems)
    facts = [_substantive_fact(fact) for fact in document.required_facts]
    facts = [fact for fact in facts if fact]
    if not facts:
        facts = list(document.required_facts)
    stagnant = 0
    while (
        sections_word_count(mutable) < document.min_words
        and idx < 200
        and stagnant < 40
    ):
        sec_i = idx % len(mutable)
        heading = str(mutable[sec_i][0])
        if heading in ("Related documents", "Owner"):
            idx += 1
            stagnant += 1
            continue
        paras: list[str] = mutable[sec_i][1]  # type: ignore[assignment]
        system = systems[idx % len(systems)] if systems else "Atlas"
        cell = _cell(document.path, idx)
        ticket = _ticket(document.path, idx + 10)
        fact = facts[idx % len(facts)]
        candidates = _padding_candidates(
            document,
            heading,
            system,
            cell,
            ticket,
            fact,
            idx,
        )
        added = False
        for candidate in candidates:
            stem = _sentence_stem(candidate)
            key = re.sub(r"\s+", " ", candidate.lower()).strip()
            if key in seen or stem in used_stems or _overlaps_existing(candidate, seen):
                continue
            seen.add(key)
            used_stems.add(stem)
            paras.append(candidate)
            added = True
            stagnant = 0
            break
        if not added:
            stagnant += 1
        idx += 1
    return [(str(item[0]), list(item[1])) for item in mutable]  # type: ignore[arg-type]


def _sentence_stem(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()[:72]


def _substantive_fact(fact: str) -> str | None:
    if _META_FACT.match(fact.strip()):
        return None
    if re.search(r"DOCS-\d{4}", fact) and len(fact.split()) < 18:
        return None
    return fact


def _filter_substantive_topics(topics: list[Topic]) -> list[Topic]:
    steps = [
        (heading, summary)
        for heading, summary in topics
        if heading.lower().startswith("step")
    ]
    if steps:
        return steps
    filtered: list[Topic] = []
    for heading, summary in topics:
        if _META_FACT.match(summary.strip()):
            continue
        if (
            heading.startswith("Topic ")
            and re.search(r"DOCS-\d{4}", summary)
            and len(summary.split()) < 18
        ):
            continue
        filtered.append((heading, summary))
    return filtered or topics[:4]


def _padding_candidates(
    document: DocumentSpec,
    heading: str,
    system: str,
    cell: str,
    ticket: str,
    fact: str,
    idx: int,
) -> list[str]:
    owner = document.owner
    path = document.path
    doc_type = document.type
    variants = [
        f"**{heading} note ({ticket}):** {fact}",
        f"{owner} maintains a working draft for {heading.lower()} in wiki space {ticket}; iteration {idx + 1}.",
        f"During the {cell} review cycle, {owner} attached {system} telemetry supporting {heading.lower()} ({ticket}).",
        f"Stakeholders referenced {heading.lower()} when closing action item {ticket} in the {owner} backlog.",
        f"Quarterly readiness review #{idx + 1} captured {heading.lower()} decisions tied to `{path}` ({ticket}).",
    ]
    variants.extend(
        _pad_candidates(doc_type, owner, heading, system, cell, ticket, path, idx),
    )
    start = idx % len(variants)
    return variants[start:] + variants[:start]


def sections_word_count(sections: list[Section] | list[list[str | list[str]]]) -> int:
    text = " ".join(paragraph for _, paragraphs in sections for paragraph in paragraphs)  # type: ignore[union-attr]
    return word_count(text)


def _topics_from_facts(facts: tuple[str, ...]) -> list[Topic]:
    topics: list[Topic] = []
    for index, fact in enumerate(facts):
        cleaned = re.sub(r"^\*\*[^*]+\*\*\s*(—|:|at AcmeCloud:)\s*", "", fact)
        cleaned = re.sub(r"^Regarding \*\*[^*]+\*\*:\s*", "", cleaned)
        label = f"Topic {index + 1}"
        match = re.match(r"^\*\*([^*]+)\*\*", fact)
        if match:
            label = match.group(1)
        topics.append((label, cleaned))
    return topics


def _pad_candidates(
    doc_type: str,
    owner: str,
    heading: str,
    system: str,
    cell: str,
    ticket: str,
    path: str,
    idx: int = 0,
) -> list[str]:
    if doc_type == "glossary":
        return [
            f"Technical Writing refreshed {heading} examples in Confluence ({ticket}, pass {idx + 1}).",
            f"LMS module ACME-101 quizzes {heading.lower()} definitions before platform access ({ticket}).",
        ]
    if doc_type in {"company_profile", "organization", "product_portfolio"}:
        return [
            f"People Ops linked {heading.lower()} to onboarding materials in {ticket} (revision {idx + 1}).",
            f"Executive staff reviewed {heading.lower()} talking points ahead of the Q1 town hall ({ticket}).",
        ]
    if doc_type in {"finance_policy", "finance_process", "finance_operations"}:
        return [
            f"Finance archived {heading.lower()} evidence in the compliance register ({ticket}, cycle {idx + 1}).",
            f"Procurement sampled {heading.lower()} transactions during the quarterly audit ({ticket}).",
        ]
    if doc_type == "policy":
        return [
            f"Legal reviewed {heading.lower()} language for the annual attestation packet ({ticket}).",
            f"Compliance mapped {heading.lower()} controls to SOC 2 evidence item {ticket}.",
        ]
    return [
        f"{owner} recorded {heading.lower()} validation notes for {system} in `{cell}` ({ticket}).",
        f"Platform review {idx + 1} referenced {system} dashboards while updating {heading.lower()} ({ticket}).",
    ]


def _overlaps_existing(candidate: str, seen: set[str]) -> bool:
    normalized = re.sub(r"\s+", " ", candidate.lower()).strip()
    if len(normalized) < 48:
        return False
    fragment = normalized[:64]
    return any(fragment in existing or existing[:64] in normalized for existing in seen)


def _filter_architecture_topics(topics: list[Topic]) -> list[Topic]:
    skip_patterns = (
        r"documents how acmecloud",
        r"spans regional cells",
        r"core components include",
        r"validated overview on",
        r"architecture review referenced overview",
    )
    filtered: list[Topic] = []
    for heading, summary in topics:
        lowered = summary.lower()
        if any(re.search(pattern, lowered) for pattern in skip_patterns):
            continue
        if _META_FACT.match(summary.strip()):
            continue
        filtered.append((heading, summary))
    return filtered or topics[-4:]


def _filter_runbook_topics(topics: list[Topic]) -> list[Topic]:
    actionable: list[Topic] = []
    for heading, summary in topics:
        if _META_FACT.match(summary.strip()):
            continue
        if re.search(r"step-by-step operational response", summary, re.IGNORECASE):
            continue
        if (
            heading.startswith("Topic ")
            and re.search(r"DOCS-\d{4}", summary)
            and len(summary.split()) < 20
        ):
            continue
        actionable.append((heading, summary))
    if not actionable:
        return topics[:5]
    return [
        (f"Step {index + 1}", summary)
        for index, (_, summary) in enumerate(actionable[:8])
    ]


def build_architecture_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    filtered = _filter_architecture_topics(topics)
    sections = _base_architecture_sections(path, title, owner, systems, filtered)
    deduped: list[Section] = []
    seen_paras: set[str] = set()
    for heading, paragraphs in sections:
        unique_paras: list[str] = []
        for paragraph in paragraphs:
            key = re.sub(r"\s+", " ", paragraph.lower()).strip()
            if key in seen_paras:
                continue
            seen_paras.add(key)
            unique_paras.append(paragraph)
        deduped.append((heading, unique_paras))
    if deduped:
        context_idx = next(
            (i for i, (heading, _) in enumerate(deduped) if heading == "Context"),
            None,
        )
        if context_idx is not None:
            primary = systems[0] if systems else "Atlas"
            deduped[context_idx] = (
                "Context",
                [
                    f"AcmeCloud {owner} teams use this page during design reviews, on-call handoffs, and quarterly architecture audits.",
                    f"Downstream runbooks and RFCs must stay aligned with {primary} boundaries, Gatehouse ACLs, and cell residency rules.",
                ],
            )
    return deduped


def build_policy_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    substantive = _filter_substantive_topics(topics)
    return _base_policy_sections(path, title, owner, systems, substantive)


def build_runbook_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    actionable = _filter_runbook_topics(topics)
    sections = _base_runbook_sections(path, title, owner, systems, actionable[:1])
    procedure_paras = [
        f"**Step {index + 1} — {heading}:** {summary}"
        for index, (heading, summary) in enumerate(actionable)
    ]
    procedure_paras.extend(
        [
            "Record each command and Atlas deployment ID in the incident or change ticket.",
            "If execution exceeds 30 minutes without progress, escalate per the Escalation section below.",
        ],
    )
    mutable = list(sections)
    for index, (heading, _) in enumerate(mutable):
        if heading == "Procedure":
            mutable[index] = ("Procedure", procedure_paras)
            break
    pre_idx = next(
        (i for i, (heading, _) in enumerate(mutable) if heading == "Preconditions"),
        None,
    )
    if pre_idx is not None:
        _, pre_paras = mutable[pre_idx]
        mutable[pre_idx] = (
            "Preconditions",
            [
                paragraph
                for paragraph in pre_paras
                if not paragraph.startswith("**Step")
            ],
        )
    return mutable


def build_handbook_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    if path.endswith("engineering/engineering_handbook.md"):
        return _base_handbook_sections(path, title, owner, systems, topics)
    sys_label = ", ".join(systems) if systems else "Atlas"
    mid = max(1, len(topics) // 2 + 1)
    return [
        (
            "Overview",
            [
                f"{title} captures {owner} standards, workflows, and review expectations for teams using {sys_label}.",
                f"Readers should treat this guide as the authoritative reference for `{path}` during design reviews and on-call work.",
                f"Updates publish through the internal docs repo with mandatory review from the {owner} document owner.",
            ],
        ),
        (
            "Principles",
            [
                *[f"**{h}:** {s}" for h, s in topics[:mid]],
                "Documentation precedes production changes; design decisions link to RFCs when cross-team impact exists.",
            ],
        ),
        (
            "Responsibilities",
            [
                f"Engineering managers ensure direct reports follow this handbook before Atlas production access.",
                *[f"**{h}:** {s}" for h, s in topics[mid:]],
            ],
        ),
        (
            "Operating Model",
            [
                f"Teams work in two-week sprints with trunk-based development and Atlas-mediated deploys to `{_cell(path)}` first.",
                "Code review requires two approvals for Tier-0 paths; on-call engineers hold rollback authority during incidents.",
            ],
        ),
        (
            "Review Process",
            [
                f"{owner} owns quarterly handbook reviews; material updates require director approval.",
                "Training LMS modules reference this document; completion is tracked before Gatehouse prod elevation.",
            ],
        ),
        (
            "References",
            [
                f"Internal systems glossary: [Glossary](../company/glossary.md). Platform dependencies: {sys_label}.",
                "Incident handling: [Incident Response](../procedures/incident_response.md).",
            ],
        ),
    ]


def build_rfc_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    sys_label = ", ".join(systems) if systems else "Atlas"
    return [
        (
            "Context",
            [
                f"{title} captures an architecture decision affecting {sys_label} at AcmeCloud Analytics.",
                topics[0][1]
                if topics
                else f"Multiple teams requested guidance on {title.lower()}.",
            ],
        ),
        (
            "Decision",
            [
                topics[1][1]
                if len(topics) > 1
                else f"The architecture review board documented a binding decision for {sys_label}.",
                f"Status and ownership live with {owner}; superseding RFCs must reference `{path}`.",
            ],
        ),
        (
            "Alternatives Considered",
            [
                *[f"**{h}:** {s}" for h, s in topics[2:5]],
                "Each alternative was scored on operational cost, time-to-deliver, and compliance impact.",
            ],
        ),
        (
            "Consequences",
            [
                f"Accepted consequences include updated runbooks, Atlas routing changes, and Gatehouse ACL reviews for {sys_label}.",
                topics[5][1]
                if len(topics) > 5
                else "Teams must update dependent docs within one sprint of RFC acceptance.",
            ],
        ),
        (
            "Migration Plan",
            [
                f"Phased rollout starts in `{_cell(path)}` with Beacon monitoring and Ledger capacity checks.",
                f"Rollback criteria and owner checkpoints are tracked in {_ticket(path)}.",
            ],
        ),
        (
            "Related Systems",
            [
                f"Primary systems: {sys_label}. Authoritative codename definitions: [Glossary](../company/glossary.md).",
                "Postmortems and runbooks linked from the manifest must stay aligned with this RFC.",
            ],
        ),
    ]


def build_postmortem_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    sys_label = ", ".join(systems) if systems else "Atlas"
    return [
        (
            "Summary",
            [
                topics[0][1] if topics else title,
                f"Affected systems: {sys_label}. Incident bridge followed [Incident Response](../procedures/incident_response.md).",
            ],
        ),
        (
            "Impact",
            [
                topics[1][1]
                if len(topics) > 1
                else "Customer-facing impact assessed against published SLAs.",
                topics[6][1]
                if len(topics) > 6
                else "Executive stakeholders received a severity-scoped impact summary during the bridge.",
            ],
        ),
        (
            "Timeline",
            [
                f"Detection, mitigation, and recovery timestamps recorded in {_inc(path)} with UTC markers.",
                topics[2][1]
                if len(topics) > 2
                else "IC opened bridge within standard MTTA targets for the severity class.",
            ],
        ),
        (
            "Root Cause",
            [
                topics[3][1]
                if len(topics) > 3
                else f"Primary failure involved {systems[0] if systems else 'Atlas'} configuration drift.",
                f"Contributing telemetry reviewed in Beacon dashboards for `{_cell(path)}`.",
            ],
        ),
        (
            "Contributing Factors",
            [
                *[f"**{h}:** {s}" for h, s in topics[4:6]],
                "Runbook gaps and insufficient canary coverage noted during review.",
            ],
        ),
        (
            "Detection",
            [
                f"Internal SLO burn alerts on {sys_label} triggered paging before broad customer reports.",
                topics[5][1]
                if len(topics) > 5
                else "Synthetic probes did not cover all failure modes.",
            ],
        ),
        (
            "Resolution",
            [
                f"Mitigation steps executed per runbooks with Atlas rollback where applicable.",
                topics[7][1]
                if len(topics) > 7
                else "Full service restoration verified against Beacon and customer-facing probes.",
            ],
        ),
        (
            "Corrective Actions",
            [
                f"Follow-up tickets assigned to {owner} with due dates within two sprints ({_ticket(path)}).",
                "Documentation updates required for affected runbooks, RFCs, and on-call training modules.",
            ],
        ),
    ]


def build_company_profile_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "Company Overview",
            [
                "AcmeCloud Analytics is a B2B SaaS company founded in 2018 in Denver with approximately 500 employees.",
                "The company builds unified cloud analytics for mid-market and enterprise data teams across the US and EU.",
                topics[0][1]
                if topics
                else "AcmeCloud sells four integrated platforms under one commercial umbrella.",
            ],
        ),
        (
            "Mission",
            [
                "Mission: help data teams move from raw events to trusted insights and production AI without fragmented infrastructure.",
                "Founded by data infrastructure veterans; growth came through integrating lake, BI, ML, and observability capabilities.",
            ],
        ),
        (
            "Product Portfolio",
            [
                "Four customer-facing platforms: AcmeCloud Data Lake, Insights, AI Studio, and Observe.",
                "See [Product Portfolio](product_portfolio.md) for SKU details and platform-to-system mapping.",
                topics[2][1]
                if len(topics) > 2
                else "Each platform maps to internal codenames documented in the glossary.",
            ],
        ),
        (
            "Customers",
            [
                "Primary segments: mid-market SaaS, retail analytics, and enterprise data platform teams.",
                "Example customers include fictional logos used in sales enablement: Northwind Retail, Helios FinTech, and Apex Logistics.",
                topics[3][1]
                if len(topics) > 3
                else "Customer success and support SLAs differ by contract tier.",
            ],
        ),
        (
            "Operating Model",
            [
                "Remote-first across US and EU time zones with quarterly in-person engineering summits in Denver.",
                "Product and platform teams align to four platform pillars with shared SRE, Security, and Finance functions.",
                topics[4][1]
                if len(topics) > 4
                else "Annual planning sets OKRs by department with Finance-led budget cycles.",
            ],
        ),
        (
            "Regional Footprint",
            [
                "Production operates in three Atlas cells: `us-east`, `us-west`, and `eu-central` for data residency.",
                "Sales and support maintain follow-the-sun coverage; EU customers default to `eu-central` residency.",
            ],
        ),
        (
            "Internal Systems",
            [
                f"Platform teams rely on codenames such as {', '.join(systems[:4]) if systems else 'Atlas, Harbor, Beacon'}.",
                "Authoritative definitions: [Glossary](glossary.md). These names are internal and must not appear in customer PDFs.",
            ],
        ),
        (
            "Documentation Map",
            [
                "Start with this page, then [Org Structure](org_structure.md), department overviews, and `knowledge/README.md`.",
                "RFCs live under `knowledge/rfcs/`; postmortems under `knowledge/postmortems/`; policies under `knowledge/policies/`.",
                topics[5][1]
                if len(topics) > 5
                else "Benchmark retrieval paths are frozen for evaluation datasets.",
            ],
        ),
        (
            "Ownership",
            [
                f"{owner} maintains this overview with HR and executive staff; contact `hello@acmecloud.io`.",
                f"Updates require People Ops review and must stay aligned with `{path}` in the corpus manifest.",
            ],
        ),
    ]


def build_organization_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "Executive Leadership",
            [
                "CEO: Jordan Ellis. CFO: Priya Menon. CTO: Sam Okonkwo. CPO: Elena Vasquez.",
                topics[0][1]
                if topics
                else "Executive committee meets weekly on operations, product bets, and customer escalations.",
            ],
        ),
        (
            "Engineering and Platform",
            [
                "Engineering (~180): platform squads for Data, Analytics, AI, Observability, plus shared SRE.",
                "Dr. Amara Okafor leads AI Platform; Marcus Chen leads Data Platform.",
                topics[1][1]
                if len(topics) > 1
                else "Atlas production access requires manager approval via Gatehouse groups.",
            ],
        ),
        (
            "Go-to-Market",
            [
                "Sales, Marketing, and Customer Success (~120) align to four product pillars and enterprise accounts.",
                "Support operates tiered queues documented in Support SLAs with escalation to Engineering via on-call.",
            ],
        ),
        (
            "Corporate Functions",
            [
                "Finance, HR, Legal, and IT enable hiring, procurement, compliance, and endpoint management.",
                topics[2][1]
                if len(topics) > 2
                else "HR owns onboarding/offboarding checklists integrated with Gatehouse provisioning.",
            ],
        ),
        (
            "Reporting Lines",
            [
                "Engineering managers report to VPs by platform domain; SRE is a horizontal function with embedded liaisons.",
                "Product managers partner with engineering directors; RFC acceptance requires architecture review board quorum.",
            ],
        ),
        (
            "Headcount by Department",
            [
                "Approximate distribution: Engineering 180, GTM 120, Product 40, Support 60, G&A 100.",
                topics[3][1]
                if len(topics) > 3
                else "Headcount updates publish quarterly in the internal wiki.",
            ],
        ),
        (
            "Location and Remote Policy",
            [
                "HQ in Denver; remote-first across US states and select EU countries.",
                "See [Remote Work Policy](../policies/remote_work_policy.md) and [PTO and Leave](../hr/pto_and_leave.md).",
            ],
        ),
        (
            "Ownership",
            [
                f"{owner} owns org chart accuracy; updates route through People Ops ({path}).",
                "Major reorgs require executive approval and updated Gatehouse group mappings within five business days.",
            ],
        ),
    ]


def build_product_portfolio_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "Product Suite Overview",
            [
                "AcmeCloud sells four integrated platforms that share Atlas tenancy, Gatehouse ACLs, and Ledger metering.",
                topics[0][1]
                if topics
                else "Each product has a customer-facing brand and internal platform codename mapping.",
            ],
        ),
        (
            "AcmeCloud Data Lake",
            [
                "Harbor storage plus Mercury streaming ingest; workspace isolation via Gatehouse.",
                "Targets data engineers building curated datasets and batch pipelines.",
            ],
        ),
        (
            "AcmeCloud Insights",
            [
                "Semantic layer and ClickHouse query pools (RFC-001); governed self-serve SQL policies apply.",
                "Targets analysts and analytics engineers publishing dashboards.",
            ],
        ),
        (
            "AcmeCloud AI Studio",
            [
                "Orion model serving, feature stores, and training pipelines with responsible AI reviews.",
                "Targets ML engineers shipping production inference workloads.",
            ],
        ),
        (
            "AcmeCloud Observe",
            [
                "Beacon ingestion, SLO framework, and alerting integrated with Atlas tenant routing.",
                "Targets SRE and platform teams operating customer-facing services.",
            ],
        ),
        (
            "Platform Dependencies",
            [
                f"Shared systems: {', '.join(systems) if systems else 'Atlas, Harbor, Mercury, Orion, Beacon, Gatehouse, Ledger'}.",
                topics[1][1]
                if len(topics) > 1
                else "Cross-product dependencies documented in department overviews and RFCs.",
            ],
        ),
        (
            "Pricing and Packaging",
            [
                "Consumption-based pricing via Ledger meters for compute, storage, and inference.",
                "Enterprise packages include dedicated cells, enhanced SLAs, and FinOps review cadences.",
            ],
        ),
        (
            "Roadmap Linkages",
            [
                "Product roadmap themes align to RFCs and quarterly planning in [Roadmap Planning](../product/roadmap_planning.md).",
                topics[2][1]
                if len(topics) > 2
                else "Major bets require architecture review before Atlas routing changes.",
            ],
        ),
        (
            "Ownership",
            [
                f"{owner} maintains portfolio positioning with Finance and Sales Enablement.",
                f"Updates to `{path}` require Product Ops review and glossary cross-links.",
            ],
        ),
    ]


def build_glossary_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    facts: tuple[str, ...],
) -> list[Section]:
    codenames = {
        "Atlas": [
            "**Atlas** — control plane for tenant provisioning, cell routing (`us-east`, `us-west`, `eu-central`), platform configuration, and deployment orchestration.",
            "Primary owners: Engineering and SRE. Authoritative ops doc: [Deployment Runbook](../sre/deployment_runbook.md).",
        ],
        "Beacon": [
            "**Beacon** — observability ingestion pipeline for metrics, logs, and distributed traces before indexing and alert evaluation.",
            "Owner: Observability Platform. See [Observability Platform Overview](../observability-platform/observability_platform_overview.md).",
        ],
        "Mercury": [
            "**Mercury** — streaming pipeline runtime for real-time ingest and stream processing into Harbor.",
            "Owner: Data Platform. Supersedes legacy Kafka-only paths per RFC-006.",
        ],
        "Orion": [
            "**Orion** — model serving platform for online inference, canary deploys, and GPU scheduling.",
            "Owner: AI Platform. Paired with model registry promotion states and Beacon latency monitors.",
        ],
        "Ledger": [
            "**Ledger** — billing and usage metering for compute, storage, and inference consumption with per-workspace quotas.",
            "Owners: Finance and Data Platform. Feeds [Cloud Spend Governance](../finance/cloud_spend_governance.md).",
        ],
        "Gatehouse": [
            "**Gatehouse** — identity and access control: SSO, RBAC groups, workspace ACLs, and service accounts.",
            "Owner: Security. All production access and break-glass flows route through Gatehouse.",
        ],
        "Harbor": [
            "**Harbor** — data lake storage layer with object storage, Iceberg table formats, and partition layout policies.",
            "Owner: Data Platform. Underpins batch and streaming pipelines and the Insights semantic layer.",
        ],
    }
    sections: list[Section] = [
        (
            "Overview",
            [
                "This glossary is the authoritative reference for internal platform codenames and shared domain vocabulary at AcmeCloud Analytics (~500 employees, Denver HQ, remote-first US/EU).",
                "RFCs, postmortems, and runbooks must link here on first mention of a codename. Customer-facing names remain external brands.",
            ],
        ),
    ]
    for system in systems:
        if system in codenames:
            sections.append((system, list(codenames[system])))
    sections.extend(
        [
            (
                "Domain terms",
                [
                    "**Cell** — regional isolation unit. **Tenant** — customer org; **workspace** — data/compute boundary.",
                    "**SLO** — internal objective; **SLA** — customer-facing commitment in Support docs. **IC** — incident commander.",
                ],
            ),
            (
                "Usage conventions",
                [
                    "First mention in each doc should link to this glossary or expand codenames in parentheses.",
                    "Customer PDFs use external product names only; codenames are internal confidential terminology.",
                ],
            ),
            (
                "Product to platform mapping",
                [
                    "**AcmeCloud Data Lake** maps to Harbor + Mercury + Gatehouse workspace controls.",
                    "**AcmeCloud Insights** maps to Harbor curated layers plus ClickHouse query pools (RFC-001).",
                    "**AcmeCloud AI Studio** maps to Orion + Harbor feature stores + Gatehouse model ACLs.",
                    "**AcmeCloud Observe** maps to Beacon ingestion plus Atlas tenant routing for telemetry.",
                ],
            ),
        ],
    )
    return sections


def build_finance_policy_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "Purpose",
            [
                f"{title} defines how AcmeCloud employees and contractors purchase goods and services.",
                "Finance owns vendor onboarding, purchase order policy, and audit evidence for SOC 2 procurement controls.",
            ],
        ),
        (
            "Scope",
            [
                "Applies to all departments procuring software, hardware, cloud services, and professional services.",
                "Contractors must route spend through sponsoring managers; personal reimbursements follow the expense policy.",
            ],
        ),
        (
            "Purchasing Thresholds",
            [
                topics[0][1]
                if topics
                else "Purchase order required for transactions over $1,000 USD.",
                "Capital purchases over $25,000 require CFO approval and three competitive quotes when feasible.",
            ],
        ),
        (
            "Approval Workflow",
            [
                "Requester submits Jira procurement ticket with business justification and budget code.",
                "Manager approval required up to $10,000; Director approval up to $50,000; VP/CFO above that threshold.",
                topics[1][1]
                if len(topics) > 1
                else "SaaS renewals attach Ledger usage reports when affecting production systems.",
            ],
        ),
        (
            "Vendor Review",
            [
                "New vendors complete [Vendor Security Review](../security/vendor_security_review.md) before contract signature.",
                "Data processors require Legal and Security sign-off; access provisioning follows Gatehouse joiner workflows.",
            ],
        ),
        (
            "Security and Compliance Requirements",
            [
                "Vendors handling customer data must meet data classification requirements and sign DPAs.",
                topics[2][1]
                if len(topics) > 2
                else "SOC 2 evidence collected quarterly from top 20 vendors by spend.",
            ],
        ),
        (
            "Exceptions",
            [
                "Emergency purchases during SEV-1 incidents may proceed with verbal VP approval and retroactive PO within 48 hours.",
                f"Document exceptions in Jira with Finance ticket reference ({_ticket(path)}).",
            ],
        ),
        (
            "Audit Evidence",
            [
                "Finance retains POs, approval emails, and security questionnaires for seven years.",
                topics[3][1]
                if len(topics) > 3
                else "Internal audit samples 5% of transactions each quarter.",
            ],
        ),
    ]


def build_finance_process_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "Planning Cycle",
            [
                topics[0][1]
                if topics
                else "Annual budget cycle starts in October with department submissions due mid-November.",
                "Executive committee finalizes targets in December; board review in January.",
            ],
        ),
        (
            "Department Input",
            [
                "Department heads submit headcount, cloud, and vendor forecasts in the planning workbook.",
                "Engineering attaches Ledger trend exports and capacity notes from SRE reviews.",
            ],
        ),
        (
            "Finance Review",
            [
                f"Finance consolidates submissions, applies corporate allocations, and models scenarios in Ledger-linked models.",
                topics[1][1]
                if len(topics) > 1
                else "FinOps flags anomalies above 20% variance from prior year.",
            ],
        ),
        (
            "Executive Approval",
            [
                "CFO presents consolidated budget to CEO and board; approved targets publish to department VPs.",
                "Material mid-year changes require reforecast approval per this document.",
            ],
        ),
        (
            "Reforecast Process",
            [
                topics[2][1]
                if len(topics)
                else "Quarterly reforecast updates cloud and vendor actuals against plan.",
                "Departments explain variances over 10% with mitigation plans.",
            ],
        ),
        (
            "Ledger Integration",
            [
                "Ledger meters feed actuals for compute, storage, and inference; exports join budget models automatically.",
                "See [Cloud Spend Governance](cloud_spend_governance.md) for operational guardrails.",
            ],
        ),
        (
            "Ownership",
            [
                f"{owner} owns the planning calendar and workbook templates.",
                f"Questions route to `finance@acmecloud.io` with reference to `{path}`.",
            ],
        ),
    ]


def build_finance_operations_sections(
    path: str,
    title: str,
    owner: str,
    systems: list[str],
    topics: list[Topic],
    _facts: tuple[str, ...],
) -> list[Section]:
    return [
        (
            "FinOps Charter",
            [
                topics[0][1]
                if topics
                else "FinOps partners with Engineering and Finance to optimize cloud unit economics without compromising reliability.",
                "Team maintains dashboards tying Ledger usage to budget owners and department VPs.",
            ],
        ),
        (
            "Spend Visibility",
            [
                f"Ledger provides workspace-level meters for {', '.join(systems) if systems else 'Atlas, Harbor, Orion'} workloads.",
                "Weekly spend reports publish to `#finops` with top movers and anomaly callouts.",
            ],
        ),
        (
            "Budget Guardrails",
            [
                "Soft alerts at 80% of monthly budget; hard throttles require VP approval via Jira.",
                topics[1][1]
                if len(topics) > 1
                else "Tier-0 services exempt from automated throttles during incidents.",
            ],
        ),
        (
            "Anomaly Response",
            [
                "FinOps opens investigation within one business day when daily spend exceeds 130% of trailing average.",
                "Engineering owners attach root-cause notes; Security engaged if access patterns change.",
            ],
        ),
        (
            "Chargeback Model",
            [
                "Internal chargeback allocates shared platform costs by Ledger consumption with 5% overhead for G&A.",
                topics[2][1]
                if len(topics) > 2
                else "Product P&L reviews use chargeback exports in quarterly business reviews.",
            ],
        ),
        (
            "Governance Meetings",
            [
                "Monthly FinOps council with Finance, SRE, and platform leads reviews top accounts and savings initiatives.",
                f"Action items tracked in {_ticket(path)} with owners and due dates.",
            ],
        ),
        (
            "Ownership",
            [
                f"{owner} maintains this document with Finance leadership.",
                "Updates require FinOps lead approval and cross-link to [Budget Planning](budget_planning.md).",
            ],
        ),
    ]
