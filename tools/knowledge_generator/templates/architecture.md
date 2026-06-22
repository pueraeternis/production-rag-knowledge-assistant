---
type: architecture
required_sections:
  - Overview
  - Context
  - System Components
  - Control Plane
  - Data Plane
  - Dependencies
  - Scaling Model
  - Failure Modes
  - Operational Ownership
  - Owner
  - Related documents
writing_style:
  - Mature internal architecture page for a B2B SaaS platform team.
  - Concrete, system-specific, and suitable for onboarding engineers.
realism_requirements:
  - Name relevant AcmeCloud platform codenames.
  - Include operating cells, ownership, SLO or failure-mode details.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Prefer links to runbooks, RFCs, postmortems, and platform overviews.
prohibited_filler_patterns:
  - Placeholder architecture diagrams.
  - Generic cloud architecture language without AcmeCloud systems.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics architecture document.

Document:
- Path: {{ path }}
- Title: {{ title }}
- Owner: {{ owner }}
- Related systems: {{ related_systems }}

Required sections:
{{ required_sections }}

Required facts:
{{ required_facts }}

Related documents:
{{ related_documents }}

Return only Markdown with YAML front matter and body content.
