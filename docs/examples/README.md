# Corpus Excerpts

Short representative excerpts from the **AcmeCloud Analytics** synthetic knowledge base illustrate the style and structure of documents produced by `tools/knowledge_generator/generator.py`.

These files are for **GitHub inspection only**. They are not a substitute for the full generated corpus.

| File | Illustrates |
| ---- | ----------- |
| [remote_work_policy_excerpt.md](remote_work_policy_excerpt.md) | HR policy language, eligibility rules, benchmark-aligned facts |
| [security_policy_faq_excerpt.md](security_policy_faq_excerpt.md) | Security requirements phrased as FAQ-style entries |
| [incident_response_procedure_excerpt.md](incident_response_procedure_excerpt.md) | Numbered operational procedure steps |

## Full corpus

The complete knowledge base (96 documents) is generated locally into `knowledge/`, which is gitignored. Regenerate with:

```bash
python3 tools/knowledge_generator/generator.py
```

See [README.md](../../README.md#knowledge-base) for corpus inventory and benchmark alignment.
