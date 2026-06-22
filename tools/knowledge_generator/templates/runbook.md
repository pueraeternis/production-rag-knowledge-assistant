---
type: runbook
required_sections:
  - Purpose
  - Preconditions
  - Procedure
  - Validation
  - Rollback
  - Escalation
  - Related Incidents
  - Owner
  - Related documents
writing_style:
  - Operational runbook for on-call engineers.
  - Step-oriented, direct, and usable during incidents.
realism_requirements:
  - Include preconditions, checks, rollback, escalation, and observability signals.
  - Mention affected cells, dashboards, tickets, or incident channels.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Link to incident response or deployment guidance when relevant.
prohibited_filler_patterns:
  - Aspirational operations language.
  - Missing rollback or validation criteria.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics runbook.

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
