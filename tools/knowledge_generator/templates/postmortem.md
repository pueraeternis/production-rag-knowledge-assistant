---
type: postmortem
required_sections:
  - Summary
  - Impact
  - Timeline
  - Root Cause
  - Contributing Factors
  - Detection
  - Resolution
  - Corrective Actions
  - Owner
  - Related documents
writing_style:
  - Blameless production incident review.
  - Chronological, concrete, and tied to follow-up actions.
realism_requirements:
  - Include severity, affected systems, customer impact, detection, and corrective actions.
  - Reference runbooks, RFCs, or platform docs that changed after the incident.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Link to incident response and affected system documentation when possible.
prohibited_filler_patterns:
  - Blame language.
  - Vague root causes without corrective actions.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics postmortem.

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
