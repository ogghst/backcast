# AI Agent Structured Output & Briefing Flow Analysis

Date: 2026-05-23

## 1. Overview

The AI chat system uses a **Briefing Room** orchestration pattern. A supervisor agent receives user requests, decides whether to handle them directly or delegate to specialist agents, and accumulates all findings into a shared `BriefingDocument`. Specialists run in isolation — they never see each other's message history, only the compiled briefing.

This analysis traces the full lifecycle of structured output: from specialist configuration, through agent execution and message extraction, into briefing compilation, and finally to supervisor synthesis.

---

## 2. Data Models

### 2.1 BriefingDocument (the accumulator)

```
briefing.py → BriefingDocument(BaseModel)
├── original_request: str              # User's current question
├── sections: list[BriefingSection]     # One per specialist invocation
├── supervisor_analysis: str | None     # Supervisor's overall reasoning
└── task_history: list[TaskAssignment]  # Who was delegated what and why
```

### 2.2 BriefingSection (specialist contribution)

```
briefing.py → BriefingSection(BaseModel)
├── specialist_name: str
├── task_description: str
├── findings: str                       # Cleaned prose (structured headers stripped)
├── supervisor_rationale: str | None
├── key_findings: list[str] | None      # Parsed from "## Key Findings" header
├── open_questions: list[str] | None    # Parsed from "## Open Questions" header
└── delegation_notes: str | None        # Parsed from "## Delegation Notes" header
```

### 2.3 TaskAssignment (delegation record)

```
briefing.py → TaskAssignment(BaseModel)
├── specialist: str
├── description: str
└── rationale: str | None
```

---

## 3. Specialist Output Format

### 3.1 What specialists produce

Specialists are LangChain agents compiled via `langchain_create_agent()`. They do **not** use Pydantic `response_format` for output in practice — only 3 of 8 specialists declare a `structured_output_schema`:

| Specialist | Schema | Actual usage |
|---|---|---|
| `evm_analyst` | `EVMMetricsRead` | Passed as `response_format` to `create_agent()` |
| `change_order_manager` | `ImpactAnalysisResponse` | Passed as `response_format` to `create_agent()` |
| `forecast_manager` | `ForecastRead` | Passed as `response_format` to `create_agent()` |
| All others | `None` | Free-form text |

The `response_format` parameter is consumed by LangChain's `create_agent()` — it uses the schema for structured output mode with the LLM. However, the supervisor orchestrator **does not read these structured outputs directly**. Instead, it always extracts the final AI response as raw text via `extract_final_ai_response()` and then parses markdown sections from it.

### 3.2 The _SCOPE_BOUNDARY prompt (output contract)

Every specialist receives this instruction appended to their context:

```
## OUTPUT FORMAT (MANDATORY)
After completing all tool calls, you MUST write a final response that summarizes
your analysis and conclusions in plain text. Do NOT leave your response empty.

Include these sections:
- ## Key Findings: Bullet list of your most important discoveries
- ## Open Questions: Questions that need answers from other specialists or the user
- ## Delegation Notes: Context for any specialist who should continue this work
```

This is the **de facto structured output contract** — it's prompt-enforced markdown, not schema-enforced Pydantic.

---

## 4. End-to-End Flow

### 4.1 Step-by-step trace

```
1. USER MESSAGE
   ↓
2. agent_service.py invokes the compiled supervisor graph
   ↓
3. INITIALIZE_BRIEFING NODE
   - Creates BriefingDocument(original_request=user_message)
   - OR restores existing briefing from checkpoint (follow-up messages)
   - Returns _briefing_update(doc) which:
     • Sets briefing_data = doc.model_dump()
     • Injects SystemMessage("## Current Briefing\n..." + doc.to_markdown())
     • Resets supervisor_iterations = 0
     ↓
4. SUPERVISOR NODE (LangChain agent)
   - Receives: user message + injected briefing SystemMessage
   - Has tools: get_briefing + handoff_to_{specialist}* + optional direct_tools
   - Decision:
     a) Respond directly → AIMessage with no tool_calls → END
     b) Delegate → calls handoff_to_{specialist}(task_description, rationale)
   ↓
5a. HANDOFF TOOL (if delegation)
   - Creates TaskAssignment(specialist, task_description, rationale)
   - Appends to briefing.task_history
   - Returns Command(goto=specialist_name, graph=Command.PARENT,
       update={messages, active_agent, briefing_data})
   ↓
5b. ROUTER (_make_supervisor_router)
   - Reads last AIMessage.tool_calls
   - Extracts specialist name from "handoff_to_{name}"
   - Prevents redispatch to already-completed specialists
   - Routes to specialist node or END
   ↓
6. SPECIALIST WRAPPER NODE (_create_specialist_wrapper)
   - Reads briefing from state → doc.to_markdown()
   - Extracts latest TaskAssignment (task_desc + rationale)
   - Constructs ISOLATED messages:
     HumanMessage("## Your Assignment\n{task}\n## Briefing\n{briefing}{_SCOPE_BOUNDARY}")
   - Invokes specialist_graph.ainvoke({messages, tool_call_count, max_tool_iterations})
   - Extracts findings: extract_final_ai_response(result.messages)
   - Parses structured sections: parse_structured_findings(findings)
   - Compiles into briefing: compile_specialist_output(...)
   - Returns Command(goto="supervisor", update={briefing_data, completed_specialists, ...})
   ↓
7. BACK TO SUPERVISOR (loop)
   - _briefing_update re-injects updated briefing as SystemMessage
   - Supervisor reads accumulated findings
   - If findings answer the request → responds directly → END
   - If not → delegates to another specialist → back to step 5a
   - Max 3 supervisor iterations enforced by router
   ↓
8. END → Final AIMessage streamed to user via WebSocket
```

### 4.2 State flow diagram

```
┌──────────────────────────────────────────────────────┐
│                 BackcastSupervisorState               │
│                                                      │
│  messages: [HumanMsg, ..., AIMsg]  (outer convo)     │
│  briefing_data: {BriefingDocument.model_dump()}      │
│  active_agent: "supervisor" | "<specialist>"         │
│  completed_specialists: set[str]                     │
│  supervisor_iterations: int  (max 3)                 │
│  tool_call_count: int                                │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
   ┌─────────────────────┐     handoff     ┌──────────────────────┐
   │    initialize_      │────────────────►│     supervisor       │
   │    briefing         │                 │   (LangChain agent)  │
   └─────────────────────┘                 └──────────┬───────────┘
                                                         │
                                              tool_call? │ no → END
                                                         │ yes
                                                         ▼
                                              ┌──────────────────────┐
                                              │  specialist_wrapper  │
                                              │  (isolated invoke)   │
                                              └──────────┬───────────┘
                                                         │
                                              Command(goto="supervisor")
                                                         │
                                                         ▼
                                              back to supervisor (loop)
```

---

## 5. Structured Output Parsing Pipeline

### 5.1 From specialist raw text to BriefingSection

The pipeline is entirely string-based (no Pydantic schema validation of specialist output):

```
Specialist LLM output (free-form text with optional markdown headers)
  │
  ▼
extract_final_ai_response(messages)
  - Walks messages in reverse
  - Finds last AIMessage without tool_calls
  - Falls back to concatenated ToolMessage content (DeepSeek compat)
  │
  ▼ Returns: str (raw findings text)
  │
  ▼
parse_structured_findings(findings)
  - Splits on "\n## " headers
  - Extracts bullet items under "## Key Findings" → list[str]
  - Extracts bullet items under "## Open Questions" → list[str]
  - Extracts prose under "## Delegation Notes" → str
  │
  ▼ Returns: {"key_findings": [...], "open_questions": [...], "delegation_notes": "..."}
  │
  ▼
compile_specialist_output(briefing_data, specialist_name, task_description, findings, ...)
  - Validates existing BriefingDocument from briefing_data
  - _strip_structured_sections(): removes "## Key Findings", "## Open Questions",
    "## Delegation Notes" from raw findings (to avoid duplication)
  - Creates BriefingSection(cleaned_findings + parsed fields)
  - Appends to doc.sections
  │
  ▼ Returns: updated BriefingDocument.model_dump()
```

### 5.2 BriefingSection field relationships

```
┌─────────────────────────────────────────────────┐
│ BriefingSection                                  │
│                                                  │
│ findings:     Cleaned prose                      │
│               (structured headers REMOVED)        │
│                                                  │
│ key_findings: Parsed bullets from "## Key..."    │
│ open_questions: Parsed bullets from "## Open..." │
│ delegation_notes: Parsed prose from "## Del..."  │
│                                                  │
│ These 3 fields are EXTRACTED from the raw text   │
│ and stored separately for structured access.      │
│ The raw findings field has them STRIPPED to       │
│ prevent duplication in to_markdown() rendering.   │
└─────────────────────────────────────────────────┘
```

---

## 6. Briefing Rendering (to_markdown)

The `BriefingDocument.to_markdown()` method produces a structured document:

```markdown
# Briefing Document

## Request
{original_request}

## Supervisor Analysis
{supervisor_analysis}

## Task History
1. **project_manager**: Analyze project costs
   - Rationale: User asked about budget status

## Specialist Findings

### project_manager (Iteration 1)
Task: Analyze project costs
Supervisor rationale: User asked about budget status

{cleaned findings prose — no structured headers}

**Key Findings:**
- Project is 15% over budget
- CPI trending downward

**Open Questions:**
- Should we flag this to the PM?

**Delegation Notes:** Cost element CE-001 needs immediate attention
---
```

This markdown is what the supervisor sees as a `SystemMessage` injected before every turn.

---

## 7. Key Architectural Observations

### 7.1 Dual output system

There are **two parallel structured output mechanisms** that don't interact:

1. **`response_format` (Pydantic schemas)**: 3 specialists declare schemas (`EVMMetricsRead`, `ImpactAnalysisResponse`, `ForecastRead`). These are passed to `langchain_create_agent()` which may use them for structured LLM output. But the orchestrator **never reads** these structured outputs — it always goes through the text extraction pipeline.

2. **Prompt-enforced markdown sections** (`_SCOPE_BOUNDARY`): The actual contract that the orchestrator relies on. All specialists receive instructions to include `## Key Findings`, `## Open Questions`, `## Delegation Notes` in their free-form text output. The `parse_structured_findings()` function extracts these.

The `response_format` schemas may influence LLM output quality but are effectively dead code in the orchestrator pipeline.

### 7.2 Specialists are fully isolated

- No shared message history between specialists
- Each specialist receives only: assignment description + full briefing markdown + `_SCOPE_BOUNDARY`
- Output is always extracted as text → parsed → compiled into briefing
- Specialists cannot see each other's raw tool interactions

### 7.3 The briefing is re-injected every supervisor turn

After every specialist return, `_briefing_update()` converts the full briefing to markdown and injects it as a fresh `SystemMessage`. This means:
- The supervisor always has current context
- But the message history grows linearly with briefing size × iteration count
- `SummarizationMiddleware` (trigger: 2000 tokens or 20 messages) compacts older messages — safe because the briefing is re-injected fresh each turn

### 7.4 Checkpoint-based briefing persistence

On follow-up messages, the `initialize_briefing_node` restores the existing briefing from `state.briefing_data` (persisted via checkpointer). This preserves specialist findings across conversation turns. Only `original_request` is updated to the current question.

---

## 8. Files Reference

| File | Role |
|---|---|
| `backend/app/ai/briefing.py` | BriefingDocument, BriefingSection, TaskAssignment Pydantic models + `to_markdown()` |
| `backend/app/ai/briefing_compiler.py` | `initialize_briefing()`, `parse_structured_findings()`, `compile_specialist_output()`, `_strip_structured_sections()` |
| `backend/app/ai/supervisor_state.py` | `BackcastSupervisorState` TypedDict (parent graph state) |
| `backend/app/ai/supervisor_orchestrator.py` | `SupervisorOrchestrator` class — builds the full parent graph, specialist wrappers, routing |
| `backend/app/ai/handoff_tools.py` | `create_handoff_tool()` / `create_all_handoff_tools()` — delegation via `Command(PARENT)` |
| `backend/app/ai/subagents/__init__.py` | 8 specialist configurations (name, description, system_prompt, allowed_tools, structured_output_schema) |
| `backend/app/ai/subagent_compiler.py` | `compile_subagents()` — compiles specialist configs into LangChain agent graphs |
| `backend/app/ai/message_utils.py` | `extract_final_ai_response()` — text extraction from message history |
| `backend/app/ai/state.py` | `AgentState` TypedDict — inner specialist state schema |
| `backend/app/ai/graph.py` | `create_graph()` — standalone agent graph (used by fallback path) |
