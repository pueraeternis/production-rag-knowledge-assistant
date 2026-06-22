---
type: policy
required_sections:
  - Purpose
  - Scope
  - Requirements
  - Exceptions
  - Enforcement
  - Review Cycle
writing_style:
  - Employee-facing internal policy with clear obligations and thresholds.
  - Audit-friendly, specific, and non-marketing.
realism_requirements:
  - Include approvers, review cadence, exceptions, and compliance checks.
  - State concrete limits, timelines, or eligibility rules from required facts.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Link to procedures when policy enforcement requires operational steps.
prohibited_filler_patterns:
  - Vague policy principles without measurable rules.
  - Placeholder compliance text.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics policy document.

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
