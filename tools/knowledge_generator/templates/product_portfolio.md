---
type: product_portfolio
required_sections:
  - Product Suite Overview
  - AcmeCloud Data Lake
  - AcmeCloud Insights
  - AcmeCloud AI Studio
  - AcmeCloud Observe
  - Platform Dependencies
  - Pricing and Packaging
  - Roadmap Linkages
  - Ownership
writing_style:
  - Product management portfolio page mapping customer-facing brands to platform capabilities.
realism_requirements:
  - Name all four products and link to internal platform codenames via glossary.
cross_link_requirements:
  - Link to company overview, glossary, and finance cloud spend docs.
prohibited_filler_patterns:
  - Generic engineering handbook sections.
  - Architecture control plane framing as primary narrative.
---

Write a realistic AcmeCloud Analytics product portfolio document.

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
