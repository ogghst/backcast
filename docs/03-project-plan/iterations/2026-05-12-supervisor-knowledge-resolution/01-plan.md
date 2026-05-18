# Plan: Supervisor-side Knowledge Resolution for Specialist Clarification

**Created:** 2026-05-12
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Prompt-Only Enhancement (no structural changes)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option:** Prompt-Only Enhancement -- add a section to `BRIEFING_ROOM_SUPERVISOR_PROMPT` instructing the supervisor to inspect, resolve, or surface open questions from specialist briefing sections.
- **Architecture:** Zero code changes. The entire data pipeline (capture, storage, rendering) is already complete. The sole gap is that `BRIEFING_ROOM_SUPERVISOR_PROMPT` in `supervisor_orchestrator.py` contains zero mention of open questions.
- **Key Decisions:**
  1. No new nodes, edges, state fields, tools, or database columns.
  2. The supervisor's existing briefing injection (`_briefing_update`) already delivers the full briefing markdown including `**Open Questions:**` sections before every supervisor turn. The prompt merely needs to tell the supervisor to act on them.
  3. No programmatic enforcement -- compliance is prompt-driven. Partial LLM compliance is an improvement over current zero-awareness state.

### Decision Questions (Resolved)

1. **Material harm domains?** No domain-specific warnings in this iteration. The current specialist domains (project management, EVM, change orders, forecasting) do not have immediate safety-critical consequences from unanswered clarification questions. If this changes (e.g., approval authority specialists), domain warnings can be added in a future iteration.
2. **Maximum question cap?** Yes -- cap at 5 most critical questions. This prevents user overload on complex multi-specialist analyses while still surfacing all questions that genuinely need resolution.
3. **Standardized heading?** Yes -- use `**Clarification Needed:**` as the exact heading string. This enables future frontend detection/styling without any structural commitment today.

### Success Criteria

**Functional Criteria:**

- [ ] AC-1: The supervisor prompt contains a dedicated section instructing the supervisor to inspect briefing sections for `**Open Questions:**` and act on them. VERIFIED BY: unit test asserting the prompt constant contains the required keywords.
- [ ] AC-2: The prompt instructs the supervisor to resolve questions from available context where possible (user messages, other specialist findings, project knowledge). VERIFIED BY: unit test asserting the prompt contains resolution guidance language.
- [ ] AC-3: The prompt instructs the supervisor to surface unresolvable questions to the user under a `**Clarification Needed:**` heading. VERIFIED BY: unit test asserting the prompt contains the exact heading string.
- [ ] AC-4: The prompt instructs the supervisor to cap surfaced questions at a maximum of 5, prioritizing the most critical. VERIFIED BY: unit test asserting the prompt references the cap.
- [ ] AC-5: The prompt instruction does not interfere with existing supervisor behaviors (iteration safety guards, completion rules, handoff logic). VERIFIED BY: existing test suite (`test_briefing_room_orchestrator.py`) continues to pass without modification.
- [ ] AC-6: The specialist `_SCOPE_BOUNDARY` prompt is not modified and continues to instruct specialists to include `## Open Questions`. VERIFIED BY: unit test asserting `_SCOPE_BOUNDARY` remains unchanged.

**Technical Criteria:**

- [ ] TC-1: Code quality: ruff format + ruff check + mypy strict pass on `supervisor_orchestrator.py`. VERIFIED BY: running quality commands on modified file only.
- [ ] TC-2: No new imports, no new functions, no new state fields in the modified file. Only a string constant is extended. VERIFIED BY: code review.

**Business Criteria:**

- [ ] BC-1: When a specialist produces open questions the supervisor cannot resolve, the user receives a clearly framed clarification section in the supervisor's response. VERIFIED BY: prompt content specifies the behavior; end-to-end verification is a future e2e test (out of scope for this iteration).

### Scope Boundaries

**In Scope:**

- Extending `BRIEFING_ROOM_SUPERVISOR_PROMPT` constant in `supervisor_orchestrator.py` with a new section on open question handling.
- Unit tests verifying the prompt constant contains the required instructions.
- Ensuring existing tests pass unchanged.

**Out of Scope:**

- Any changes to `briefing.py`, `briefing_compiler.py`, `handoff_tools.py`, `supervisor_state.py`, `agent_service.py`, or subagent prompts.
- Integration or e2e tests that require actual LLM calls (the supervisor is an LLM; compliance is probabilistic and cannot be deterministically tested without mocking the LLM response).
- Frontend detection or styling of the `**Clarification Needed:**` section.
- Programmatic enforcement of open question surfacing (future iteration if prompt compliance proves insufficient).
- Changes to the DEEP orchestrator mode (uses a different pattern -- task tool, not briefing).

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Write unit tests asserting `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains open question handling instructions | `backend/tests/ai/test_briefing_room_orchestrator.py` | None | Tests fail (RED) because the prompt does not yet contain the required language. All 4 test cases defined below exist and fail. | Low |
| 2 | Add open question handling section to `BRIEFING_ROOM_SUPERVISOR_PROMPT` | `backend/app/ai/supervisor_orchestrator.py` | Task 1 | All tests from Task 1 pass (GREEN). Existing tests in `test_briefing_room_orchestrator.py` continue to pass. No new imports or functions added. | Low |
| 3 | Verify quality gates pass on modified file | `backend/app/ai/supervisor_orchestrator.py` | Task 2 | `ruff check`, `ruff format`, and `mypy` all pass with zero errors on the modified file. | Low |

### Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Write unit tests for supervisor prompt open question handling (RED phase)"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Add open question handling section to BRIEFING_ROOM_SUPERVISOR_PROMPT (GREEN phase)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Run quality gates (ruff, mypy) on modified file and verify existing tests pass"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]
```

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| AC-1: Prompt inspects `**Open Questions:**` | T-001 | `tests/ai/test_briefing_room_orchestrator.py` | Assert `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains substring instructing inspection of `**Open Questions:**` in briefing sections. |
| AC-2: Prompt instructs resolution from context | T-002 | `tests/ai/test_briefing_room_orchestrator.py` | Assert prompt contains language about resolving questions from available context (user messages, specialist findings). |
| AC-3: Prompt surfaces unresolvable under `**Clarification Needed:**` | T-003 | `tests/ai/test_briefing_room_orchestrator.py` | Assert prompt contains the exact string `**Clarification Needed:**` and instructions to surface unresolved questions there. |
| AC-4: Prompt caps questions at 5 | T-004 | `tests/ai/test_briefing_room_orchestrator.py` | Assert prompt references a maximum of 5 questions to surface. |
| AC-5: Existing tests unaffected | T-005 | `tests/ai/test_briefing_room_orchestrator.py` | All existing tests in the file continue to pass (verified in Task 3). |
| AC-6: `_SCOPE_BOUNDARY` unchanged | T-006 | `tests/ai/test_briefing_room_orchestrator.py` | Assert `_SCOPE_BOUNDARY` still contains `## Open Questions` instruction. |

---

## Test Specification

### Test Hierarchy

```
tests/ai/test_briefing_room_orchestrator.py
├── TestSupervisorPromptOpenQuestions (NEW class)
│   ├── T-001: test_prompt_instructs_inspection_of_open_questions
│   ├── T-002: test_prompt_instructs_resolution_from_context
│   ├── T-003: test_prompt_instructs_clarification_heading_for_unresolvable
│   └── T-004: test_prompt_caps_surfaced_questions
└── (All existing test classes unchanged)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_prompt_instructs_inspection_of_open_questions` | AC-1 | Unit | `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains both `"**Open Questions:**"` and language instructing the supervisor to check each briefing section for it. |
| T-002 | `test_prompt_instructs_resolution_from_context` | AC-2 | Unit | `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains language about using available context (user messages, specialist findings) to resolve questions before surfacing. |
| T-003 | `test_prompt_instructs_clarification_heading_for_unresolvable` | AC-3 | Unit | `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains `"**Clarification Needed:**"` as a heading and instructions to include unresolved questions under it. |
| T-004 | `test_prompt_caps_surfaced_questions` | AC-4 | Unit | `BRIEFING_ROOM_SUPERVISOR_PROMPT` contains a reference to a maximum (5) number of questions to surface, with prioritization guidance. |
| T-005 | (Existing test suite) | AC-5 | Regression | All tests in `test_briefing_room_orchestrator.py` pass without modification. |
| T-006 | `test_scope_boundary_unchanged` | AC-6 | Unit | `_SCOPE_BOUNDARY` constant still contains `"## Open Questions"` and the output format instruction. |

### Test Infrastructure Needs

- **Fixtures needed:** None. Tests are simple string assertions on module-level constants.
- **Mocks/stubs:** None.
- **Database state:** None. Pure unit tests with no IO.
- **Import:** `from app.ai.supervisor_orchestrator import BRIEFING_ROOM_SUPERVISOR_PROMPT, _SCOPE_BOUNDARY`

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | LLM ignores the prompt instruction and does not surface open questions | Medium | Low | Partial compliance is still an improvement over zero-awareness. Briefing re-injection on every turn gives repeated chances. Future iteration can add programmatic guard. |
| Technical | LLM hallucinates answers instead of forwarding questions | Low | Medium | Prompt instruction explicitly says "do NOT guess" for questions outside available context. The cap of 5 limits damage surface. |
| Integration | New prompt section changes LLM token usage patterns, affecting response latency | Low | Low | The instruction is ~100 tokens. The briefing (which already contains the open questions) is already injected. No additional API calls. |
| Regression | Prompt change breaks existing supervisor behavior (routing, handoff, completion) | Low | High | Existing test suite covers routing, completion, iteration guards. Task 3 verifies all existing tests pass. Prompt-only change cannot affect deterministic code paths. |

---

## Prerequisites

### Technical

- [x] No database migrations required
- [x] No new dependencies required
- [x] Environment already configured for backend testing

### Documentation

- [x] Analysis phase approved (`00-analysis.md`)
- [x] `supervisor_orchestrator.py` source reviewed (lines 55-112 for prompt constants)
- [x] `briefing.py` source reviewed (lines 88-91 for `**Open Questions:**` rendering)
- [x] Existing test patterns reviewed (`test_briefing_room_orchestrator.py`)

---

## Implementation Guidance for DO Phase

### Target Location

The new section should be inserted into `BRIEFING_ROOM_SUPERVISOR_PROMPT` (lines 55-89 of `backend/app/ai/supervisor_orchestrator.py`) after the `## Guidelines` section and before the `## CRITICAL COMPLETION RULES` section. This positions it logically: the supervisor reads the briefing, follows general guidelines, then applies the open question protocol before deciding on completion.

### What the Prompt Section Should Contain

The added prompt section must instruct the supervisor to:

1. After reading the briefing, check each specialist section for `**Open Questions:**`
2. For each question, decide if it can be resolved from: (a) the user's original request, (b) other specialist findings, (c) general project knowledge visible in the briefing
3. If resolvable, incorporate the answer silently and proceed
4. If unresolvable, include it under a `**Clarification Needed:**` section in the response
5. Frame questions concisely so the user can answer in their next message
6. Limit surfaced questions to a maximum of 5, prioritizing the most critical
7. Do NOT guess or fabricate answers to questions that cannot be resolved from available context

### What NOT to Change

- `_SCOPE_BOUNDARY` -- specialist-side instruction already correct
- `_BRIEFING_HANDOFF_SUFFIX` -- not the target of this iteration
- `_BRIEFING_CONTEXT_PREFIX` -- briefing delivery mechanism unchanged
- Any code outside the `BRIEFING_ROOM_SUPERVISOR_PROMPT` string constant

---

## Documentation References

### Required Reading

- Supervisor orchestrator architecture: `docs/02-architecture/ai/supervisor-orchestrator.md`
- AI chat implementation notes: `backend/app/ai/supervisor_orchestrator.py` (source comments, lines 1-16)

### Code References

- Supervisor prompt constant: `backend/app/ai/supervisor_orchestrator.py` lines 55-89
- Briefing markdown rendering with open questions: `backend/app/ai/briefing.py` lines 88-91
- Existing prompt content tests: `backend/tests/ai/test_briefing_room_orchestrator.py` class `TestBuildFallbackGraph` (checks "Briefing Room" in prompt)
