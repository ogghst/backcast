# Analysis: Clarification Interrupt Protocol for Mid-Turn User Interaction

**Created:** 2026-05-12
**Request:** Phase 2 - Reuse the InterruptNode pattern (currently used for HIGH-risk tool approvals) to create a clarification interrupt protocol. When the supervisor encounters open_questions in the briefing that it cannot answer, it publishes a clarification_request event, the frontend renders the question, the user answers inline, and the answer is injected back into graph state for enriched re-delegation.

---

## Clarified Requirements

### Functional Requirements

1. The supervisor agent must be able to pause execution mid-turn and ask the user a clarifying question before proceeding with specialist delegation
2. Clarification questions arise from `open_questions` in the briefing that the supervisor cannot answer from available context
3. The user's answer must be injected back into the briefing (not raw messages) so that subsequent specialists benefit from the clarified context
4. After receiving a clarification response, the supervisor should re-delegate to the appropriate specialist with the enriched briefing
5. The clarification interaction must work through the existing WebSocket + event bus streaming architecture
6. The frontend must render clarification questions inline (within the chat flow, not a modal) with a text input for the user's response

### Non-Functional Requirements

1. Latency: clarification interaction should not add more than 2 seconds of overhead beyond the user's response time
2. Reliability: WebSocket disconnect during a clarification wait must be handled gracefully (timeout + auto-recovery or error message)
3. Token efficiency: clarification cycles should not re-invoke specialists that already completed; only the target specialist should re-run
4. Iteration safety: clarification cycles must interact correctly with `max_supervisor_iterations` (default 3)

### Constraints

1. Must not break the existing approval interrupt flow for HIGH-risk tools
2. Must work within the current LangGraph StateGraph architecture (no framework changes)
3. Must be compatible with the existing `AgentEventBus` event streaming model
4. Frontend changes must reuse existing Ant Design components and follow the established chat UI patterns
5. The specialist `_SCOPE_BOUNDARY` prompt already instructs specialists to output `## Open Questions` -- this is the trigger mechanism

---

## Context Discovery

### Product Scope

- AI chat system provides a conversational interface for project budget management queries
- Users may ask ambiguous questions ("What's the status of PRJ-001?") where "status" could mean budget, schedule, EVM performance, or change orders
- The supervisor orchestrator currently has no mechanism to ask for clarification -- it must guess which specialist to delegate to

### Architecture Context

**Bounded contexts involved:**
- AI Chat (bounded context containing the supervisor orchestrator, specialists, event bus, and WebSocket streaming)

**Existing patterns to follow:**
- InterruptNode pattern: pause graph execution, send event via bus, wait for WebSocket response, resume
- Event bus pub/sub: `AgentEventBus.publish()` with typed events consumed by WebSocket handler
- Approval dialog: `ApprovalDialog.tsx` renders a modal for approve/reject binary decisions
- Briefing-based state: `BriefingDocument` is the single source of truth between supervisor turns
- Specialist wrappers: isolated execution with only the briefing as context, returning findings via `Command` state updates

**Architectural constraints:**
- `BackcastSupervisorState` uses `operator.add` reducers for `messages`, `tool_call_count`, `supervisor_iterations`
- `completed_specialists` uses `operator.or_` (set union) -- prevents re-dispatch to already-completed specialists
- The router `_make_supervisor_router` enforces iteration caps and prevents redispatch
- LangGraph's `interrupt()` mechanism exists but is NOT currently used -- the approval flow uses polling instead
- `InterruptNode` currently lives at the `BackcastSecurityMiddleware` level for tool approval, not at the graph orchestration level

### Codebase Analysis

**Backend:**

Key files and their roles:

- `/home/nicola/dev/backcast/backend/app/ai/supervisor_orchestrator.py` -- The `SupervisorOrchestrator` class builds the parent StateGraph. The `_create_specialist_wrapper` method already parses `open_questions` from specialist output via `parse_structured_findings()` and stores them in `BriefingSection.open_questions`. The supervisor prompt instructs reading the briefing before delegating but provides no mechanism to ask the user questions.

- `/home/nicola/dev/backcast/backend/app/ai/tools/interrupt_node.py` -- `InterruptNode` extends `ToolNode` and manages approval flow via `_send_approval_request()`, polling (`_check_approval`), and resumption (`execute_after_approval`). It stores `pending_approvals` and `interrupt_state` dicts. The approval uses polling (not LangGraph's native `interrupt()`) because it was built before that mechanism was available.

- `/home/nicola/dev/backcast/backend/app/ai/execution/agent_event.py` -- `AgentEvent` is a frozen dataclass with `event_type`, `data`, `timestamp`, `execution_id`, `sequence`. Adding `clarification_request` is simply a new `event_type` string.

- `/home/nicola/dev/backcast/backend/app/ai/execution/agent_event_bus.py` -- The bus is a generic pub/sub channel. It does not filter or validate event types -- any string works. Terminal events (`complete`, `error`) set `is_completed=True`.

- `/home/nicola/dev/backcast/backend/app/ai/agent_service.py` -- `_run_agent_graph()` processes streaming events from `graph.astream_events()`. The `register_approval_response()` and `resume_graph_after_approval()` methods exist but the resume path is currently unused (the approval uses polling, not true graph resumption). A new `register_clarification_response()` method would follow the same pattern.

- `/home/nicola/dev/backcast/backend/app/ai/supervisor_state.py` -- `BackcastSupervisorState` has `briefing_data` (dict), `supervisor_iterations` (add reducer), `completed_specialists` (set union reducer), and `active_agent` (string). No field for pending clarification state.

- `/home/nicola/dev/backcast/backend/app/ai/briefing.py` -- `BriefingDocument` already has `sections[].open_questions: list[str] | None`. This is the natural source of clarification triggers.

- `/home/nicola/dev/backcast/backend/app/ai/handoff_tools.py` -- `create_handoff_tool()` returns `Command(goto=agent_name, graph=Command.PARENT)` with briefing updates. This pattern would be extended for a clarification tool.

- `/home/nicola/dev/backcast/backend/app/models/schemas/ai.py` -- `WSApprovalRequestMessage` and `WSApprovalResponseMessage` define the WebSocket protocol for approval flow. New `WSClarificationRequestMessage` and `WSClarificationResponseMessage` would be needed.

**Frontend:**

- `/home/nicola/dev/backcast/frontend/src/features/ai/components/ApprovalDialog.tsx` -- Modal dialog for binary approve/reject decisions. NOT directly reusable for clarification because: (a) it renders a modal overlay, not an inline chat element; (b) it expects binary response, not free-text input; (c) it has countdown timer and risk level display irrelevant to clarification.

- `/home/nicola/dev/backcast/frontend/src/features/ai/chat/types.ts` -- Defines `WSApprovalRequestMessage`, `WSApprovalResponseMessage`, and type guards. New clarification types would follow the same pattern.

- The chat interface (`ChatInterface.tsx`) handles WebSocket messages and routes them by type. Adding a `clarification_request` handler follows the existing dispatch pattern.

---

## Solution Options

### Option 1: Clarification as a Supervisor Tool (ask_user tool) -- SELECTED

**Architecture & Design:**

Add a new `ask_user` tool to the supervisor's tool set. The tool supports two clarification phases:

**Phase 1 — Pre-delegation clarification:** The supervisor reviews the user's initial request and the briefing. If the request is ambiguous (e.g., "What's the status of PRJ-001?" where "status" could mean budget, schedule, or EVM), the supervisor calls `ask_user` before delegating to any specialist.

**Phase 2 — Specialist → human forwarding:** After a specialist executes and returns findings with `open_questions`, the supervisor reads the updated briefing. If the specialist surfaced questions the supervisor cannot answer from context, the supervisor calls `ask_user` to forward those questions to the user. The specialist's `_SCOPE_BOUNDARY` prompt already instructs it to output `## Open Questions`, and `parse_structured_findings()` in `_create_specialist_wrapper` already extracts them into `BriefingSection.open_questions`. No specialist-side changes are needed — the pipeline already exists.

The `ask_user(question: str, context: str)` tool:
1. Publishes a `clarification_request` event via the event bus
2. Polls for a response (same pattern as approval polling)
3. Returns the user's answer as a tool result
4. The supervisor then proceeds with enriched context

This is a tool-level approach -- the graph never pauses. The tool itself blocks (awaiting the WebSocket response) and returns the result to the supervisor as a `ToolMessage`.

**UX Design:**

The frontend renders the clarification question as an inline card within the chat stream, with a text input and submit button. The user types their answer, clicks submit, and the response is sent via WebSocket. The chat shows a "waiting for your response" indicator.

Flow (pre-delegation):
1. User sends message
2. Supervisor reads briefing, finds ambiguity in the request
3. `ask_user` tool is called, frontend shows inline question card
4. User types answer, submits
5. Answer returns to supervisor as tool result
6. Supervisor delegates to specialist with enriched context
7. Specialist executes, briefing is updated
8. Supervisor synthesizes final response

Flow (specialist → human forwarding):
1. User sends message
2. Supervisor delegates to specialist
3. Specialist executes, returns findings with `open_questions`
4. Supervisor reads updated briefing, sees `open_questions` it cannot resolve
5. `ask_user` tool is called with the specialist's question, frontend shows inline question card
6. User types answer, submits
7. Answer returns to supervisor as tool result
8. Supervisor synthesizes final response using specialist's partial findings + clarified answer
9. If needed, supervisor delegates to a different specialist with enriched briefing

**Implementation:**

Backend files to create/modify:
- `backend/app/ai/tools/clarification_tool.py` -- New `create_ask_user_tool()` function
- `backend/app/ai/supervisor_orchestrator.py` -- Add `ask_user` to supervisor tools; update supervisor prompt to instruct: (a) review user request for ambiguity before delegating, (b) check `open_questions` in briefing sections after specialist completion and forward to user when unresolvable
- `backend/app/ai/agent_service.py` -- Add `register_clarification_response()`, add `_pending_clarifications` dict
- `backend/app/models/schemas/ai.py` -- Add `WSClarificationRequestMessage`, `WSClarificationResponseMessage`
- `backend/app/api/routes/ai_chat.py` -- Handle `clarification_response` WebSocket message type

Frontend files to create/modify:
- `frontend/src/features/ai/chat/components/ClarificationCard.tsx` -- New inline component
- `frontend/src/features/ai/chat/types.ts` -- Add clarification types and type guards
- `frontend/src/features/ai/chat/components/ChatInterface.tsx` -- Handle `clarification_request` event

**Key design decisions:**
- `ask_user` is NOT a handoff tool -- it is a direct supervisor tool that returns a string result
- The tool blocks the graph execution at the supervisor level, so no state corruption risk
- The polling mechanism reuses the same pattern as approval polling with 5-minute timeout
- The user's answer is appended to the briefing's `supervisor_analysis` field, not to raw messages
- `supervisor_iterations` does NOT increment during clarification (no specialist cycle consumed)
- The `completed_specialists` set is untouched during clarification
- For specialist → human forwarding, the same specialist is NOT re-dispatched after clarification (blocked by `completed_specialists` set union reducer). Instead, the supervisor synthesizes using the specialist's partial findings + the clarified answer, or delegates to a different specialist if the answer reveals a different domain is needed
- Maximum 4 clarification calls per turn (default, configurable via `MAX_CLARIFICATIONS_PER_TURN` env var) to prevent infinite clarification loops (enforced in the tool, not via `max_supervisor_iterations`)
- Clarification answers ARE persisted as distinct messages in the chat history, so the user can see the full Q&A thread in the conversation

**Trade-offs:**

| Aspect          | Assessment                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------ |
| Pros            | Minimal architecture change; tool-level blocking is well-understood; no graph topology change; supervisor naturally decides when to ask; answer is injected as tool result (clean state flow); specialist → human forwarding uses the existing `open_questions` pipeline with zero specialist-side changes |
| Cons            | Blocking tool call ties up the event loop thread; tool-level blocking may not work well with LangGraph's `astream_events()` if the framework expects tools to return quickly; polling adds latency; same specialist cannot re-run after clarification (supervisor must synthesize or delegate elsewhere) |
| Complexity      | Medium                                                                                     |
| Maintainability | Good -- follows the existing InterruptNode polling pattern; single new tool                |
| Performance     | Acceptable -- blocking only during active user wait; no specialist re-invocation overhead  |

---

### Option 2: Clarification via State-Level Interrupt (Graph Pause/Resume)

**Architecture & Design:**

Use LangGraph's native `interrupt()` mechanism to pause the graph at the supervisor node. When the supervisor identifies open questions:
1. The supervisor returns a `Command` with `update` containing `pending_clarification: dict` in state
2. The router detects `pending_clarification` and routes to a new `clarification_wait` node
3. The `clarification_wait` node calls `interrupt()` with the question payload
4. The graph is paused, and a `clarification_request` event is published via the event bus
5. When the user responds, `graph.update_state()` injects the answer
6. The graph resumes, the `clarification_wait` node returns the answer
7. The supervisor re-delegates with enriched context

This approach uses true graph pausing rather than tool-level polling.

**UX Design:**

Same inline card experience as Option 1, but the graph is truly paused. The frontend shows the same clarification question card. On WebSocket disconnect during wait, the graph remains paused in the checkpointer and can be resumed on reconnection.

**Implementation:**

Backend files to create/modify:
- `backend/app/ai/supervisor_state.py` -- Add `pending_clarification: dict | None` field
- `backend/app/ai/supervisor_orchestrator.py` -- Add `clarification_wait` node, modify router
- `backend/app/ai/agent_service.py` -- Add graph pause/resume methods using LangGraph's `Command` + `interrupt()`
- `backend/app/models/schemas/ai.py` -- Add clarification WS message types
- `backend/app/api/routes/ai_chat.py` -- Handle `clarification_response`, call graph resume

Frontend: Same as Option 1.

**Key design decisions:**
- New `clarification_wait` function node in the parent graph
- Router checks for `pending_clarification` before checking handoff tools
- `interrupt()` call preserves full graph state in checkpointer
- Resume uses `graph.invoke(None, config={"configurable": {"thread_id": ...}})` with state update
- The clarification response is injected via `graph.update_state()` before resuming

**Trade-offs:**

| Aspect          | Assessment                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Pros            | True graph pausing is cleaner semantically; state is preserved in checkpointer; handles WebSocket disconnect naturally (graph stays paused); no polling loop overhead |
| Cons            | LangGraph interrupt/resume API is less mature than tool-level blocking; requires adding a node to the graph topology; graph resume from a streaming context is complex; the current codebase does NOT use LangGraph interrupts anywhere (approval uses polling instead) -- this is uncharted territory |
| Complexity      | High                                                                                                |
| Maintainability | Fair -- introduces a new mechanism (interrupt/resume) not currently used in the codebase            |
| Performance     | Good -- no polling loop; graph state preserved efficiently                                          |

---

### Option 3: Pre-Delegation Briefing Review with Clarification (Supervisor Prompt + ask_user Tool)

**Architecture & Design:**

This is a variant of Option 1 that adds a structured pre-delegation review step. Instead of the supervisor ad-hoc deciding to ask questions, the system enforces a clarification step:
1. After `initialize_briefing` but before the first specialist delegation, the supervisor is prompted to review the user request and identify ambiguities
2. If the request is ambiguous, the supervisor calls `ask_user` with a structured question
3. The answer is stored in a new `clarifications: list[Q&A]` field on the BriefingDocument
4. Only after all clarifications are resolved does the supervisor proceed with delegation

This differs from Option 1 by making clarification a mandatory review step rather than an ad-hoc tool call.

**UX Design:**

Same inline card, but the flow is more predictable:
1. User sends message
2. Briefing is initialized
3. Supervisor reviews and asks clarification questions (one at a time, max 2)
4. User answers
5. Supervisor delegates with enriched briefing

The advantage is that the user sees the clarification request early (before any specialist runs), avoiding the frustration of waiting for a specialist to finish only to be asked a question afterward.

**Implementation:**

Same backend files as Option 1, plus:
- `backend/app/ai/briefing.py` -- Add `clarifications: list[ClarificationQA]` field to BriefingDocument
- `backend/app/ai/supervisor_orchestrator.py` -- Add a `clarification_check` step in the supervisor prompt
- `backend/app/ai/briefing_compiler.py` -- Add `compile_clarification()` function

Frontend: Same as Option 1.

**Trade-offs:**

| Aspect          | Assessment                                                                                         |
| --------------- | -------------------------------------------------------------------------------------------------- |
| Pros            | Predictable UX (clarification happens before any specialist work); avoids wasted specialist calls; clarifications are persisted in the briefing document for audit trail |
| Cons            | Over-engineered for simple requests (forces a review step even when no clarification is needed); the supervisor may not always know what's ambiguous before reading specialist findings; reduces supervisor autonomy |
| Complexity      | Medium-High                                                                                        |
| Maintainability | Good -- clarifications are part of the briefing document                                           |
| Performance     | Best -- avoids any wasted specialist calls                                                         |

---

## Comparison Summary

| Criteria           | Option 1: ask_user Tool (SELECTED) | Option 2: Graph Interrupt/Resume | Option 3: Pre-Delegation Review |
| ------------------ | ---------------------------------- | -------------------------------- | ------------------------------- |
| Development Effort | 3-4 days                           | 5-7 days                         | 4-5 days                        |
| UX Quality         | Good (natural flow)                | Good (same UX)                   | Best (clarification upfront)    |
| Flexibility        | Best (ad-hoc, any time)            | Good (graph-level)               | Fair (forced pre-step)          |
| Risk               | Low (follows known pattern)        | High (new mechanism, untested)   | Medium (adds process overhead)  |
| Best For           | Incremental, safe delivery         | Long-term architecture           | Predictable UX patterns         |

---

## Decision

**Selected: Option 1 (ask_user Tool)** with specialist → human forwarding.

The `ask_user` tool serves both clarification phases: (1) pre-delegation request disambiguation, and (2) forwarding specialist `open_questions` to the user. This is possible because the specialist → open_questions pipeline already exists (`_SCOPE_BOUNDARY` prompt → `parse_structured_findings()` → `BriefingSection.open_questions`) with zero specialist-side changes needed.

**Rationale:**

1. **It follows an established pattern.** The approval flow already uses tool-level blocking + polling. The `ask_user` tool uses the exact same mechanism.

2. **Lowest risk.** No graph topology changes, no new LangGraph mechanisms, no state schema changes.

3. **Supervisor autonomy.** The supervisor decides when clarification is needed at either phase, rather than forcing a mandatory review step.

4. **Specialist → human forwarding is free.** The `open_questions` pipeline already exists. The only addition is prompting the supervisor to check `open_questions` after specialist completion and forward them via `ask_user` when it cannot resolve them.

5. **No iteration budget impact.** `supervisor_iterations` does not increment during clarification (no specialist cycle consumed).

**Constraint: same specialist cannot re-run after clarification.** The `completed_specialists` set union reducer prevents re-dispatch. The supervisor must either synthesize from partial findings + clarified answer, or delegate to a different specialist. This is acceptable because most specialist `open_questions` are clarifications the supervisor can resolve with the user's answer (e.g., "Which WBE did you mean?") without needing the same specialist to re-execute.

**Alternative consideration:** If LangGraph's interrupt/resume mechanism matures and the team gains experience with it (e.g., by migrating the approval flow from polling to interrupts), then Option 2 becomes attractive as a cleaner architectural approach. However, introducing interrupts for the first time via a new feature increases risk unnecessarily.

**Key implementation detail:** The `ask_user` tool must work with LangGraph's `astream_events()`. Tool calls in this streaming model are executed within the `on_tool_start`/`on_tool_end` event cycle. The tool function itself is an async function that blocks on polling -- this is compatible because LangGraph awaits each tool call before proceeding to the next node. The existing approval polling proves this pattern works.

---

## Decision Questions

1. ~~**Should the clarification have a maximum count?**~~ **Resolved: Default 4 per turn, configurable via `MAX_CLARIFICATIONS_PER_TURN` env var.**

2. ~~**Should clarification answers be visible in the chat history?**~~ **Resolved: Yes — clarification answers are persisted as distinct messages in the conversation history.**

3. ~~**Priority question:** Is the primary use case (a) the supervisor asking before delegating ("Which project did you mean?"), (b) a specialist returning open questions that the supervisor then forwards to the user, or (c) both?~~ **Resolved: Both.** The `ask_user` tool supports pre-delegation clarification and specialist → human forwarding of `open_questions`. The tool is supervisor-only; specialists do not call it directly.

---

## References

- `/home/nicola/dev/backcast/backend/app/ai/supervisor_orchestrator.py` -- Supervisor graph construction and specialist wrappers
- `/home/nicola/dev/backcast/backend/app/ai/tools/interrupt_node.py` -- Existing approval interrupt pattern
- `/home/nicola/dev/backcast/backend/app/ai/agent_service.py` -- Graph execution, event processing, approval registration
- `/home/nicola/dev/backcast/backend/app/ai/supervisor_state.py` -- State schema
- `/home/nicola/dev/backcast/backend/app/ai/briefing.py` -- BriefingDocument with `open_questions` field
- `/home/nicola/dev/backcast/backend/app/ai/handoff_tools.py` -- Handoff tool pattern (Command-based delegation)
- `/home/nicola/dev/backcast/backend/app/ai/execution/agent_event_bus.py` -- Event bus pub/sub
- `/home/nicola/dev/backcast/backend/app/models/schemas/ai.py` -- WebSocket message schemas
- `/home/nicola/dev/backcast/backend/app/api/routes/ai_chat.py` -- WebSocket handler
- `/home/nicola/dev/backcast/frontend/src/features/ai/components/ApprovalDialog.tsx` -- Approval UI (reference for frontend patterns)
- `/home/nicola/dev/backcast/frontend/src/features/ai/chat/types.ts` -- Frontend WS message types
- `/home/nicola/dev/backcast/docs/02-architecture/ai/supervisor-orchestrator.md` -- Supervisor orchestrator architecture documentation
- `/home/nicola/dev/backcast/docs/02-architecture/ai/agent-common-concepts.md` -- Shared agent infrastructure documentation
