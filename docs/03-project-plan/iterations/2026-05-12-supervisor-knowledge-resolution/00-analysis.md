# Analysis: Supervisor-side Knowledge Resolution for Specialist Clarification

**Created:** 2026-05-12
**Request:** Enhance the supervisor agent to act on `open_questions` from specialist briefing sections -- either resolving them from conversation context or forwarding them to the user.

---

## Clarified Requirements

### Problem Statement

Specialist agents run in isolation with only the briefing document as context. When they produce `open_questions` (e.g., "Which baseline should I compare against?"), the data infrastructure already captures these questions into `BriefingSection.open_questions` and renders them into the briefing markdown. However, the supervisor prompt contains no instruction to read, evaluate, or act on these questions. They silently accumulate in the briefing document without ever reaching the user.

### Functional Requirements

1. After each specialist contribution, the supervisor must inspect `open_questions` in the updated briefing
2. The supervisor uses its own judgment to decide whether it can resolve a question from available context (previous user messages, other specialist findings, project knowledge)
3. Questions the supervisor cannot resolve must be surfaced to the user in a dedicated clarification section at the end of its response
4. When the user answers in a subsequent turn, those answers must flow into the briefing naturally (already works via `initialize_briefing_node` which sets `doc.original_request` to the latest user message)

### Non-Functional Requirements

- No structural changes to the graph topology (no new nodes, no new edges)
- No new database columns or migrations
- No increase in LLM token cost beyond what is already spent reading the briefing
- Must not interfere with the iteration safety guards (`max_supervisor_iterations: 3`, `completed_specialists` set)
- Must not conflict with the interrupt/approval flow (`InterruptNode`)

### Constraints

- The solution must work for both orchestrator modes: SUPERVISOR (primary target) and DEEP (secondary, if applicable)
- The `_SCOPE_BOUNDARY` prompt already instructs specialists to include `## Open Questions` -- this must not be removed or weakened
- Specialist isolation must be preserved (no direct message sharing)
- Supervisor judgment on question resolution is intentionally left flexible -- no hard rules about when to resolve vs. forward

---

## Context Discovery

### Product Scope

- No existing user story specifically addresses AI agent clarification loops
- The AI chat system's core value proposition is autonomous analysis -- requiring excessive user input defeats this purpose
- This feature targets the narrow case where a specialist genuinely cannot proceed without clarifying information

### Architecture Context

**Bounded contexts involved:**
- AI Chat (`backend/app/ai/`) -- sole context affected

**Existing patterns:**
- The briefing document pattern (`BriefingDocument` + `BriefingSection` + `BriefingCompiler`) already provides the full data pipeline: specialist output -> `parse_structured_findings()` -> `compile_specialist_output()` -> `BriefingSection.open_questions` -> `to_markdown()` renders `**Open Questions:**`
- The handoff tool pattern (`create_handoff_tool`) performs deterministic briefing updates
- The specialist wrapper (`_create_specialist_wrapper`) parses structured findings at line 558-569 of `supervisor_orchestrator.py`

**Key architectural facts:**
1. `open_questions` are already extracted from specialist output and stored in `BriefingSection.open_questions` (verified in `briefing_compiler.py` lines 112-115)
2. `open_questions` are already rendered in the briefing markdown (verified in `briefing.py` lines 88-91)
3. The briefing is already injected as a `SystemMessage` into the supervisor context (via `_briefing_update()` at line 131)
4. The supervisor prompt (`BRIEFING_ROOM_SUPERVISOR_PROMPT`) says nothing about open questions -- this is the identified gap
5. The briefing is re-injected every time the supervisor gets control (after each specialist returns, and on follow-up turns)

### Codebase Analysis

**Backend files analyzed:**

| File | Relevance |
|------|-----------|
| `app/ai/supervisor_orchestrator.py` | Contains the supervisor prompt, specialist wrapper, routing logic -- primary modification target |
| `app/ai/briefing.py` | `BriefingSection.open_questions` field and markdown rendering -- already complete |
| `app/ai/briefing_compiler.py` | `parse_structured_findings()` extracts open_questions -- already complete |
| `app/ai/handoff_tools.py` | Handoff tools with deterministic briefing updates -- no changes needed |
| `app/ai/supervisor_state.py` | `BackcastSupervisorState` schema -- no changes needed |
| `app/ai/agent_service.py` | Graph invocation, briefing persistence, message history -- no changes needed |
| `app/ai/subagents/__init__.py` | Specialist configs and system prompts -- no changes needed |
| `app/ai/deep_agent_orchestrator.py` | Alternative orchestrator mode -- not affected (uses task tool, not briefing) |
| `app/ai/tools/interrupt_node.py` | Approval flow -- independent of this feature |

**Existing test coverage:**
- `tests/ai/test_briefing.py` -- covers `BriefingSection.open_questions`, `parse_structured_findings` for open questions, and markdown rendering
- No tests exist for supervisor behavior regarding open questions (no integration test for the full loop)

**Gap confirmation:**

The grep for `open_questions` across the codebase shows:
- Data layer: captured, stored, rendered (complete)
- Supervisor prompt: **zero mentions** of open questions, clarification, or user questions (confirmed gap)
- Specialist prompt (`_SCOPE_BOUNDARY`): instructs specialists to include `## Open Questions` (complete)
- Specialist wrapper: passes `parsed.get("open_questions")` to `compile_specialist_output` (complete)

The gap is precisely and only in the supervisor prompt.

---

## Selected Solution: Prompt-Only Enhancement

**Architecture & Design:**

Add a dedicated section to `BRIEFING_ROOM_SUPERVISOR_PROMPT` instructing the supervisor to:

1. After reading the briefing, check each section for `**Open Questions:**`
2. Use judgment to decide whether each question can be resolved from available context (user messages, other specialist findings, project knowledge)
3. If a question can be resolved, incorporate the answer and proceed without bothering the user
4. If a question cannot be resolved, include it in a dedicated **Clarification Needed** section at the end of the response
5. Frame questions clearly and concisely so the user can answer in their next message

No code changes. No new tools. No new state fields. The briefing markdown already renders `**Open Questions:**` sections, and the supervisor already receives the briefing as a `SystemMessage` before every turn.

**UX Design:**

When specialists have unresolved questions, the supervisor's response would include a clarification section:

> "I've analyzed the change order impact on BR-CO-2026-001. The budget increase is 12% over baseline.
>
> **Clarification Needed:**
> 1. Should the schedule comparison use the original baseline or the revised Q2 baseline?
> 2. Are the holidays in March already accounted for in the current schedule?"

On the user's next message, `initialize_briefing_node` already updates `doc.original_request` to the new message, and the briefing (with its accumulated `open_questions`) is restored from DB persistence. The supervisor sees the user's answer and the previous open questions in the same briefing context -- resolution happens naturally through conversation flow.

**Implementation:**

- Modify `BRIEFING_ROOM_SUPERVISOR_PROMPT` constant in `supervisor_orchestrator.py` (1 block addition)
- Add 2-3 test cases verifying the prompt instructs clarification behavior
- No other file changes

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Zero code changes; zero risk to graph topology, state schema, or routing; briefing data pipeline already complete; immediate effect |
| Cons            | LLM compliance is probabilistic -- supervisor may ignore the instruction, hallucinate answers, or over-clarify; no programmatic enforcement |
| Complexity      | Low                        |
| Maintainability | Good -- prompt is self-contained and can be tuned independently |
| Performance     | Neutral -- no additional LLM calls or token overhead |

**Mitigations for the probabilistic con:**
- The prompt instruction is additive -- even partial compliance is an improvement over the current zero-awareness state
- The briefing re-injection on every supervisor turn means missed questions persist and get another chance on the next cycle
- If prompt compliance proves insufficient in practice, a programmatic guard can be added in a future iteration without architectural changes

---

## Decision Questions

1. Are there specialist domains where unanswered clarification questions could cause **material harm** (e.g., incorrect financial calculations, wrong approval authority)? If yes, the prompt instruction should include domain-specific warnings for those cases.
2. Should the prompt instruction specify a maximum number of questions to surface (e.g., top 3 most critical) to avoid overwhelming the user on complex analyses?
3. Should the `**Clarification Needed:**` heading be standardized (exact wording) so the frontend could detect and style it differently in the future?

---

## References

- `backend/app/ai/supervisor_orchestrator.py` -- supervisor prompt and specialist wrapper (lines 55-112, 419-591)
- `backend/app/ai/briefing.py` -- `BriefingSection.open_questions` field and markdown rendering
- `backend/app/ai/briefing_compiler.py` -- `parse_structured_findings()` and `compile_specialist_output()`
- `backend/app/ai/handoff_tools.py` -- deterministic briefing updates during handoff
- `backend/app/ai/agent_service.py` -- graph invocation and briefing persistence
- `docs/02-architecture/ai/supervisor-orchestrator.md` -- full architecture documentation
- `backend/tests/ai/test_briefing.py` -- existing test coverage for open_questions data flow
