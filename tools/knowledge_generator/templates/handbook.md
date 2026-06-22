---
type: handbook
required_sections:
  - Overview
  - Principles
  - Responsibilities
  - Operating Model
  - Review Process
  - References
writing_style:
  - Internal handbook page for team norms, standards, or process guidance.
  - Practical and specific enough to answer retrieval questions.
realism_requirements:
  - Include team ownership, review cadence, examples, and operational constraints.
  - Use AcmeCloud terminology consistently.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Link to policies, runbooks, or platform docs for adjacent responsibilities.
prohibited_filler_patterns:
  - Generic team handbook advice.
  - Culture-only prose without operational facts.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics handbook document.

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
