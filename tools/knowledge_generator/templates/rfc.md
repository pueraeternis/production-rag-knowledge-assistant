---
type: rfc
required_sections:
  - Context
  - Decision
  - Alternatives Considered
  - Consequences
  - Migration Plan
  - Related Systems
  - Owner
  - Related documents
writing_style:
  - Architecture decision record with tradeoffs and consequences.
  - Specific, dated, and grounded in AcmeCloud platform operations.
realism_requirements:
  - Include accepted, rejected, or superseded decision context.
  - Name affected systems and migration risks.
cross_link_requirements:
  - Include every related document listed in the manifest.
  - Cross-link postmortems or runbooks when they motivate the RFC.
prohibited_filler_patterns:
  - One-sided decisions with no alternatives.
  - Generic architecture prose without consequences.
  - Repeated paragraph openings.
---

Write a realistic AcmeCloud Analytics RFC document.

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
