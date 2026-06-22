---
type: company_profile
required_sections:
  - Company Overview
  - Mission
  - Product Portfolio
  - Customers
  - Operating Model
  - Regional Footprint
  - Internal Systems
  - Documentation Map
  - Ownership
writing_style:
  - Onboarding-friendly company introduction for new hires and partners.
  - Business narrative, not platform architecture documentation.
realism_requirements:
  - Describe company history, mission, customers, and documentation navigation.
  - Mention internal systems only as a glossary pointer, not as control/data plane framing.
cross_link_requirements:
  - Link to product portfolio, org structure, glossary, and onboarding policies.
prohibited_filler_patterns:
  - Control plane or data plane architecture sections.
  - Generic ownership boilerplate with operating context filler.
  - Software engineering handbook language.
---

Write a realistic AcmeCloud Analytics company profile document.

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
