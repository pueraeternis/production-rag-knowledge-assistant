# Production Incident Response Procedure (excerpt)

> Representative excerpt from `knowledge/procedures/incident_response.md`. Fictional SRE procedure for retrieval benchmarking.

## Purpose

Step-by-step operational response for production incidents affecting AcmeCloud customer-facing platforms. Non-production incidents use the lighter-weight engineering escalation path.

## Preconditions

- Active Gatehouse session with `procedures-incident_response-write` group membership.
- Change ticket DOCS-8111 or active incident bridge for emergency execution.
- Beacon dashboards for Atlas open and recording baseline metrics for `us-west`.

## Procedure

**Step 1 — Acknowledge and triage:** Acknowledge the page within **5 minutes** for SEV-1 incidents. Primary on-call acknowledges in PagerDuty, posts in `#incident-warroom`, and begins triage using Beacon dashboards and Atlas cell health panels. Execute in `us-west`; verify Atlas metrics between steps.

**Step 2 — Open incident bridge:** Open a Zoom bridge linked from the PagerDuty incident and Slack `#incident-warroom`. The bridge remains active until mitigation is verified. Execute in `us-east`; verify Beacon metrics between steps.

**Step 3 — Assign roles:** The **Incident Commander (IC) leads the incident response bridge call** and coordinates domain experts. Assign comms lead, scribe, and technical leads. IC is typically the primary on-call unless escalated.

**Step 4 — Customer impact and status page:** Assess customer impact using support ticket rate and synthetic probes. Comms lead coordinates Customer Incident Communications and status page updates for SEV-1/SEV-2.

**Step 5 — Legal and security engagement:** **Legal must be involved** when incidents involve personal data exposure, regulatory notification triggers, or active attacker activity. Security joins via bridge when Gatehouse, data exfiltration, or forensic preservation is required.

Record each command and Atlas deployment ID in the incident or change ticket. If execution exceeds 30 minutes without progress, escalate per the Escalation section in the full procedure.

## Related documents

- [Incident Management](../sre/incident_management.md)
- [On-Call Policy](../sre/oncall_policy.md)
- [Customer Incident Communications](../support/customer_incident_comms.md)
