# Chat Validation and Acceptance Testing

**Status:** Backlog

**Created:** 2026-06-22

**Roadmap:** Phase 15 — Post-Demo Acceptance (informational)

**Depends on:**

* [Plan 19 — Interactive Chat Demo](../active/19-interactive-chat-demo.md) *(must be completed and moved to `docs/plans/completed/` before this work begins)*

**Plan principle:** One plan introduces one capability. This plan introduces **post-implementation manual validation and acceptance reporting** for the interactive chat demo only. It does **not** authorize code changes, automated test suites, CI jobs, or modifications to Plan 19 deliverables.

---

## Authorization

**Backlog.** Not authorized for execution until Plan 19 is complete and this plan is moved to `docs/plans/active/`.

---

## Objective

Execute a structured **manual validation pass** after Plan 19 implementation is complete. Verify that the final RAG Assistant behaves correctly from a **user perspective** and that the interactive chat workflow is **suitable for lecture demonstration**.

This work answers:

* Does the documented demo path work end-to-end with real infrastructure?
* Does the assistant ground knowledge answers in the indexed corpus?
* Does conversation memory behave as documented (in-session yes, cross-session no)?
* Does streaming and non-streaming mode behave predictably?
* Does the system recover gracefully from common failure modes?

**Deliverable:** a completed validation report at `docs/manual-validation/chat-validation.md` with pass/fail results, observations, and a final acceptance recommendation.

```text
Plan 19 complete (rag chat implemented)
        ↓
Activate this plan
        ↓
Prepare environment (corpus, Qdrant, LLM, real models)
        ↓
Execute manual validation scenarios (1–8)
        ↓
Record results in docs/manual-validation/chat-validation.md
        ↓
Produce acceptance recommendation
        ↓
Move plan to docs/plans/completed/
```

---

## Scope

### In scope

* Manual validation procedures defined in this plan;
* Creation and completion of `docs/manual-validation/chat-validation.md`;
* Recording pass/fail status per scenario;
* Documenting deviations from expected behavior;
* Final acceptance recommendation (accept / accept with caveats / reject);
* `docs/PROGRESS.md` entry on completion.

### Non-scope

* Code implementation or bug fixes discovered during validation;
* New automated tests or CI integration;
* Changes to Plan 19 source, architecture, or acceptance criteria;
* Retrieval benchmark re-evaluation (Plan 18 scope);
* Performance benchmarking or load testing;
* Web UI, session persistence, or transcript export.

**Ownership boundaries:**

| Concern | Owner |
| ------- | ----- |
| Interactive chat implementation | Plan 19 |
| Retrieval strategy evaluation | Plan 18 |
| Demo bootstrap (`rag demo *`) | Plan 15 |
| Manual validation execution | This plan |
| Bug fixes discovered during validation | Separate plan or hotfix after triage |

---

## Prerequisites

Validation assumes Plan 19 is complete and the standard lecture demo path is available.

### Environment

* Python 3.12+ with `uv sync` completed;
* Qdrant reachable (default `http://localhost:6333` via `QDRANT_URL`);
* OpenAI-compatible LLM endpoint configured in `.env` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`);
* Real embedding and reranker models enabled for meaningful retrieval quality:

```bash
export RAG_EMBEDDING_MODE=real
export RAG_RERANKER_MODE=real
```

### Corpus and index

* Plan 14 corpus generated locally under `knowledge/` (gitignored);
* Demo collection populated via `rag demo load` (or `rag demo load --rebuild --approve` after model mode change).

### Operator materials

* Terminal with transcript capture capability (`script`, copy/paste, or screenshots);
* Access to Qdrant dashboard or `curl` for collection inspection;
* Ability to simulate LLM endpoint failure (wrong `LLM_BASE_URL` or stopped server).

---

## Validation Report

### Location

```text
docs/manual-validation/chat-validation.md
```

Create this file when this plan is activated. Do not create it during backlog authoring.

### Template

The validation report must contain the following sections. Copy this template when starting validation:

```markdown
# Chat Validation Report

## Metadata

| Field | Value |
| ----- | ----- |
| Validation date | YYYY-MM-DD |
| Validator | name or role |
| Plan 19 commit / tag | git ref |
| Repository commit | git ref |

## Environment

| Component | Value |
| --------- | ----- |
| OS | |
| Python version | |
| Qdrant URL | |
| Collection name | |
| RAG_EMBEDDING_MODE | |
| RAG_RERANKER_MODE | |
| LLM_BASE_URL | (redact secrets) |
| LLM_MODEL | |

## Configuration notes

Brief description of `.env` and export variables used. Do not include API keys.

## Scenario results

| # | Scenario | Status | Notes |
| - | -------- | ------ | ----- |
| 1 | Default corpus load | PASS / FAIL | |
| 2 | RAG grounded answer | PASS / FAIL | |
| 3 | General non-knowledge question | PASS / FAIL | |
| 4 | In-session memory | PASS / FAIL | |
| 5 | Cross-session memory | PASS / FAIL | |
| 6 | Streaming validation | PASS / FAIL | |
| 7 | Non-streaming mode | PASS / FAIL | |
| 8 | Failure recovery | PASS / FAIL | |

## Detailed observations

### Scenario 1 — Default corpus load

(observations)

### Scenario 2 — RAG grounded answer

(observations)

### Scenario 3 — General non-knowledge question

(observations)

**Expected behavior decision:** (see plan section)

### Scenario 4 — In-session memory

(observations)

### Scenario 5 — Cross-session memory

(observations)

### Scenario 6 — Streaming validation

(observations)

### Scenario 7 — Non-streaming mode

(observations)

### Scenario 8 — Failure recovery

(observations)

## Deviations

List any behavior that differs from documented expectations. Reference ADRs, Plan 19, or prompt contract as applicable.

## Evidence

Attach or link:

* terminal transcripts;
* screenshots of startup banner, answers, and Sources blocks;
* Qdrant collection inspection output;
* `rag demo info` output before and after load.

## Final acceptance decision

**Recommendation:** ACCEPT / ACCEPT WITH CAVEATS / REJECT

**Rationale:**

(concise justification)

**Caveats (if any):**

(list items that do not block demo but should be disclosed to operators)

**Follow-up items (if any):**

(list bugs or improvements requiring separate plans — do not implement here)
```

---

## Validation Scenarios

Execute scenarios in order. Record results immediately in the validation report.

---

### Scenario 1 — Default Corpus Load

**Purpose:** Confirm the demo bootstrap path produces an indexed knowledge base ready for chat.

#### Steps

1. Generate the canonical corpus:

```bash
python3 tools/knowledge_generator/generator.py
```

2. Inspect demo readiness (read-only):

```bash
rag demo info
```

3. Load corpus into Qdrant:

```bash
rag demo load
```

   If a collection already exists and a clean load is required:

```bash
rag demo load --rebuild --approve
```

4. Confirm index state:

```bash
rag demo info
```

5. Inspect the Qdrant collection directly (dashboard or API). Record collection name, point count, and sample payload fields.

6. Start chat and observe startup diagnostics:

```bash
rag chat
```

   Exit immediately after reviewing the banner (`exit` or `Ctrl-D`). Do not send a message yet unless required to display diagnostics.

#### Verify

| Check | Expected |
| ----- | -------- |
| Corpus exists | `rag demo info` reports corpus directory present with document count > 0 |
| Collection exists | `rag demo info` reports collection exists after load |
| Chunks indexed | Collection chunk/point count > 0; matches or is consistent with `rag demo info` chunk count |
| Documents indexed | Sample Qdrant payloads contain document metadata (title, path, or equivalent indexed fields) |
| Startup diagnostics | `rag chat` banner reports index status, retrieval pipeline label, and LLM configuration without startup LLM probe (ADR-077) |
| No mutations from info | `rag demo info` performs no index changes |

#### Record

* `rag demo info` output before and after load;
* Qdrant collection inspection evidence;
* `rag chat` startup banner transcript.

---

### Scenario 2 — RAG Grounded Answer

**Purpose:** Confirm the assistant retrieves from the corpus, grounds the answer, and renders structured sources.

#### Steps

1. Ensure Scenario 1 prerequisites are satisfied.

2. Ask a corpus-grounded question. Use the Plan 19 example or equivalent:

```bash
rag chat --message "What is the remote work policy?"
```

   For interactive validation, the same question may be entered in the REPL.

3. Observe the full turn: assistant answer, then Sources block (unless `--no-sources`).

4. Open at least one cited source document under `knowledge/` and confirm the answer content aligns with the referenced section and line range.

#### Verify

| Check | Expected |
| ----- | -------- |
| Retrieval executed | Answer reflects documented policy content, not generic hallucination; tool usage consistent with agent behavior |
| Answer grounded | Statements trace to corpus content inspectable in `knowledge/` |
| Sources block rendered | Structured Sources section appears after answer completion (ADR-075) |
| Sources correspond to corpus | Each entry lists real `document_title`, `document_path`, `section_title`, and line range matching indexed documents |
| Source order | Sources deduplicated; order preserves search rank (ADR-075) |
| No CLI reparsing | Sources originate from `TurnResult.sources`, not reparsed MCP JSON in message history |

#### Record

* Full terminal transcript including Sources block;
* Path to at least one matched corpus file with relevant excerpt;
* Note whether inline prose citations match structured Sources entries.

---

### Scenario 3 — General Non-Knowledge Question

**Purpose:** Observe behavior for questions outside the knowledge base and confirm the assistant does not fabricate corpus citations.

#### Steps

1. Ask a general knowledge question unrelated to the corporate corpus:

```bash
rag chat --message "What is the capital of France?"
```

2. Record the complete response: whether `search_documents` was invoked (infer from answer style, timing, or tool indicators if visible), answer text, and presence or absence of a Sources block.

3. If search was invoked, note whether hits were returned and how the model handled weak or empty evidence.

#### Verify

| Check | Expected |
| ----- | -------- |
| Actual behavior documented | Validator records observed tool-use pattern and answer style verbatim |
| No fabricated citations | Sources block must not list corpus documents that were not retrieved for this turn |
| No fake Sources block | If no relevant corpus evidence exists, Sources section should be absent or empty — not populated with invented references |
| Prompt contract | Behavior consistent with `agent/prompts.py` SYSTEM_PROMPT: do not fabricate citations when evidence is insufficient (ADR-046) |

#### Expected Behavior Decision

Record the **intended product behavior** for questions outside the knowledge base. This section is completed during validation, not presumed in advance.

**Reference criteria (documented architecture):**

* `SYSTEM_PROMPT` instructs the model to use `search_documents` for factual questions about **documented knowledge** and to ground answers only in retrieved tool results.
* ADR-046 requires qualifying or refusing when evidence is insufficient.
* Plan 12 defers intent classification; the model may answer general knowledge directly without search, or search and find no relevant hits.

**Decision template (fill during validation):**

| Question | Recorded decision |
| -------- | ----------------- |
| Should the assistant answer general knowledge without search? | ACCEPTABLE / NOT ACCEPTABLE / OBSERVED ONLY |
| Should the assistant search first even for general knowledge? | YES / NO / MODEL-DEPENDENT |
| If search returns no relevant hits, what should the user see? | (describe expected answer pattern) |
| Should a Sources block appear for this question? | YES / NO — (justify) |
| Is observed behavior acceptable for lecture demo? | YES / YES WITH CAVEAT / NO |

**Acceptance guidance:**

* **Pass:** Observed behavior is documented, internally consistent, and does not fabricate corpus citations or display a misleading Sources block.
* **Fail:** Assistant cites non-existent corpus documents, renders a Sources block for fabricated hits, or claims corpus authority for general knowledge answers.

---

### Scenario 4 — In-Session Memory

**Purpose:** Confirm multi-turn conversation state persists within a single `rag chat` process.

#### Steps

1. Start interactive REPL:

```bash
rag chat
```

2. First turn:

```text
My name is Vitaliy.
```

3. Second turn (same session, without restarting):

```text
What is my name?
```

4. Exit the REPL.

#### Verify

| Check | Expected |
| ----- | -------- |
| Name remembered | Assistant correctly recalls "Vitaliy" from the prior turn in the same session |
| AgentState updated | Multi-turn REPL passes updated state from prior `TurnResult.state` (ADR-072) |
| No cross-turn corruption | Second turn answer is coherent; no duplicated or partial messages from prior turns |

#### Record

* REPL transcript for both turns;
* Note any unexpected resets or loss of context within the session.

---

### Scenario 5 — Cross-Session Memory

**Purpose:** Confirm conversation state does not persist across separate `rag chat` invocations.

#### Steps

1. Complete Scenario 4 (or run the same two-turn sequence in a prior session).

2. Exit `rag chat` completely (process terminates).

3. Start a **new** `rag chat` session.

4. Ask:

```text
What is my name?
```

#### Verify

| Check | Expected |
| ----- | -------- |
| No prior-session recall | Assistant does not remember "Vitaliy" or other content from the previous process |
| Fresh state | New `rag chat` starts with fresh `AgentState` and system prompt only (ADR-072) |
| No persistence artifacts | No session files, checkpointer state, or transcript recovery (ADR-073) |
| Honest response | Assistant indicates it does not know the user's name, asks for clarification, or responds without claiming prior-session context |

#### Record

* Transcript of the new session question and answer;
* Confirm process was a new invocation (new shell or confirmed PID change if relevant).

---

### Scenario 6 — Streaming Validation

**Purpose:** Confirm default streaming mode delivers incremental output with correct finalization and source rendering.

#### Steps

1. Start interactive streaming chat (default):

```bash
rag chat
```

2. Ask a question that produces a substantive answer (corpus-grounded question recommended):

```text
Summarize the vacation policy.
```

3. Observe output **during** generation and **after** completion.

4. Optionally repeat with `--message` for a captured single-turn transcript.

#### Verify

| Check | Expected |
| ----- | -------- |
| Incremental output | Text appears progressively on the terminal, not all at once after a long pause |
| No duplicated chunks | No visible repeated text segments or stuttering deltas in the stream |
| Final answer equals accumulated text | Complete rendered text matches what would be stored as the final assistant message |
| Sources after completion | Sources block appears only after stream completes, not interleaved with tokens (ADR-075) |
| State committed on success | Final assistant message present in conversation only after successful completion (ADR-072) |

#### Record

* Transcript or screen recording note describing streaming behavior;
* Mark any duplicated chunks, premature Sources rendering, or truncated finals.

---

### Scenario 7 — Non-Streaming Mode

**Purpose:** Confirm explicit non-streaming mode works with equivalent answer quality and source rendering.

#### Steps

1. Run the same or similar corpus question in non-streaming mode:

```bash
rag chat --no-stream --message "Summarize the vacation policy."
```

2. Compare answer content and Sources block to Scenario 2 or Scenario 6 results.

#### Verify

| Check | Expected |
| ----- | -------- |
| Deferred output | Answer appears after generation completes, not incrementally |
| Source rendering unchanged | Sources block format and content rules match streaming mode (ADR-075) |
| Answer quality unchanged | Substantive content comparable to streaming mode for the same question (wording may differ) |
| TurnResult boundary | Sources still rendered from `TurnResult.sources`, not reparsed messages |

#### Record

* Full non-streaming transcript;
* Brief comparison note versus streaming output.

---

### Scenario 8 — Failure Recovery

**Purpose:** Confirm the REPL remains usable after failures and does not corrupt `AgentState`.

#### Sub-scenario 8a — Unreachable LLM endpoint

1. Note current `LLM_BASE_URL` in `.env`.

2. Set `LLM_BASE_URL` to an unreachable host (or stop the LLM server).

3. Start or continue `rag chat` and submit a question.

4. Observe error handling. Restore correct `LLM_BASE_URL` and retry a successful turn in the **same** session.

#### Sub-scenario 8b — Interrupted stream

1. Restore working LLM configuration.

2. Start `rag chat` and ask a question that produces a long answer.

3. Press `Ctrl-C` during generation.

4. Submit a new question at the prompt.

#### Sub-scenario 8c — Ctrl-C during generation (explicit)

1. Repeat interrupt during streaming if not fully covered in 8b.

2. Verify REPL returns to prompt.

#### Verify

| Check | Expected |
| ----- | -------- |
| Session remains usable | After each failure, REPL accepts new input without requiring process restart |
| No corrupted AgentState | Subsequent successful turns produce coherent answers; no orphan partial assistant messages in context |
| No partial message committed | Streaming failure or interrupt does not append partial assistant text to `AgentState` (ADR-072) |
| Clear error feedback | LLM unreachable produces understandable stderr or inline error, not silent hang |
| No automatic fallback | No hidden non-streaming retry (ADR-080); operator may use `--no-stream` explicitly |
| Recovery | After restoring LLM endpoint, next turn succeeds |

#### Record

* Transcript for each sub-scenario showing failure and recovery;
* Note whether state before the failed turn was preserved correctly.

---

## Success Criteria

This plan is complete when:

- [ ] All eight validation scenarios are executed;
- [ ] Results are documented in `docs/manual-validation/chat-validation.md`;
- [ ] Pass/fail status is recorded for every scenario;
- [ ] Deviations from expected behavior are identified and described;
- [ ] Scenario 3 **Expected Behavior Decision** section is completed;
- [ ] Evidence (transcripts, screenshots, or inspection output) is attached or referenced;
- [ ] Final acceptance recommendation is produced (ACCEPT / ACCEPT WITH CAVEATS / REJECT);
- [ ] `docs/PROGRESS.md` updated with validation completion entry;
- [ ] Plan moved to `docs/plans/completed/`.

---

## Acceptance Criteria

### Validation execution

- [ ] Scenarios 1–8 executed in a real environment (not stub-only CI fixtures)
- [ ] Validation report created at `docs/manual-validation/chat-validation.md`
- [ ] Every scenario has PASS or FAIL with supporting evidence

### Behavioral confirmation

- [ ] Corpus load and index inspection succeed (Scenario 1)
- [ ] Grounded RAG answer with valid Sources block (Scenario 2)
- [ ] Non-knowledge question behavior documented without fabricated citations (Scenario 3)
- [ ] In-session memory works; cross-session memory does not (Scenarios 4–5; ADR-072, ADR-073)
- [ ] Streaming and non-streaming modes behave per Plan 19 (Scenarios 6–7)
- [ ] Failure recovery preserves session integrity (Scenario 8)

### Documentation

- [ ] Final acceptance recommendation recorded
- [ ] Follow-up items triaged (separate plans for code fixes — not implemented here)
- [ ] `docs/PROGRESS.md` entry added on completion

---

## Execution Steps

1. Confirm Plan 19 is complete and merged; record git refs in validation report.
2. Move this plan to `docs/plans/active/`.
3. Create `docs/manual-validation/` directory if absent.
4. Create `docs/manual-validation/chat-validation.md` from the template in this plan.
5. Prepare environment per Prerequisites.
6. Execute Scenarios 1–8; update report after each scenario.
7. Complete Scenario 3 Expected Behavior Decision.
8. Write final acceptance recommendation.
9. Update `docs/PROGRESS.md`.
10. Move this plan to `docs/plans/completed/`.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| LLM non-determinism | Different answers on repeat runs | Document observations; rerun once if ambiguous; focus on structural checks (Sources, memory, streaming) |
| Environment drift | Results not reproducible | Record full environment table and git refs |
| Validation finds bugs | Temptation to fix in-place | Log follow-up items; do not expand scope into implementation |
| Real model setup friction | Blocked validation | Document setup issues in report; distinguish infra failure from product failure |
| Scenario 3 ambiguity | Unclear pass/fail | Use Expected Behavior Decision table; fail only on fabricated citations or misleading Sources |

---

## Checklist (Execution)

- [ ] Plan 19 verified complete
- [ ] Plan activated in `docs/plans/active/`
- [ ] Validation report created
- [ ] Scenario 1 — Default corpus load
- [ ] Scenario 2 — RAG grounded answer
- [ ] Scenario 3 — General non-knowledge question (+ Expected Behavior Decision)
- [ ] Scenario 4 — In-session memory
- [ ] Scenario 5 — Cross-session memory
- [ ] Scenario 6 — Streaming validation
- [ ] Scenario 7 — Non-streaming mode
- [ ] Scenario 8 — Failure recovery
- [ ] Deviations documented
- [ ] Final acceptance recommendation
- [ ] `docs/PROGRESS.md` updated
- [ ] Plan moved to `docs/plans/completed/`

---

## References

* [Plan 19 — Interactive Chat Demo](../active/19-interactive-chat-demo.md) — chat workflow, streaming, sources, ADR-071–080
* [Plan 15 — Demo Bootstrap Workflow](../completed/15-demo-bootstrap-workflow.md) — `rag demo *` commands
* [Plan 12 — LangGraph Agent](../completed/12-langgraph-agent.md) — ADR-046 prompt and citation contract
* `src/knowledge_assistant/agent/prompts.py` — SYSTEM_PROMPT
* `PROJECT.md` — source attribution requirements
* `docs/ARCHITECTURE.md` — component boundaries and chat workflow
