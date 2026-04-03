# Analysis: Prompt Caching Optimization (Static/Dynamic Boundary)

**Created:** 2026-04-03
**Request:** Separate the system prompt into a static prefix (cacheable by the LLM provider) and a dynamic suffix (project/temporal context that varies per session) to enable LLM provider prompt caching.

---

## Clarified Requirements

### Problem Statement

The system prompt is rebuilt on every invocation via `_build_system_prompt()`. The base prompt (`DEFAULT_SYSTEM_PROMPT` or a custom assistant prompt) is concatenated with dynamic context (project_id). This causes the entire prompt to differ across sessions that have different project contexts, defeating LLM provider prompt caching since providers cache based on exact prefix matching of the message sequence.

### Functional Requirements

- Separate the system prompt into a **static prefix** (the base prompt that remains stable) and a **dynamic suffix** (project context that varies per session)
- Maintain compatibility with `langchain_create_agent()` which takes a single `system_prompt` string parameter
- Preserve graph cache key computation (currently keyed by `hash(system_prompt)` where `system_prompt` is the base prompt from `assistant_config`)
- Work with both streaming and non-streaming execution paths
- Work with both subagent-enabled and direct-tool modes

### Non-Functional Requirements

- Enable prompt caching by LLM providers (Anthropic Claude, OpenAI) for cost reduction and latency improvement
- Maintain existing graph cache hit rate
- Preserve existing security model (tool-level enforcement, not prompt-level)
- Zero behavioral change in LLM output quality

### Constraints

- `langchain_create_agent()` accepts `system_prompt` as a single string -- cannot pass a tuple or list of messages
- Graph cache key uses the base prompt hash, which is correct and should not change
- The dynamic project context is per-session, not per-assistant -- it cannot be baked into the graph
- `TASK_SYSTEM_PROMPT` and `_build_system_prompt_suffix()` are appended at graph compile time in the orchestrator, making them part of the static prefix from the LLM's perspective

---

## Context Discovery

### Architecture Context

**Bounded Context:** AI Chat (non-versioned, `SimpleEntityBase`)

**Key Architectural Insight:** The system has **two separate caching layers** that are relevant:

1. **Graph Cache** (`CompiledGraphCache` in `graph_cache.py`): Caches compiled LangGraph agent graphs keyed by `(model_name, allowed_tools, execution_mode, system_prompt_hash)`. This cache works correctly today -- the hash is computed from the base prompt, not the dynamic context.

2. **LLM Provider Prompt Cache**: External to the application. Anthropic Claude and OpenAI cache prompt prefixes server-side. They require the prefix of the message sequence to be identical across requests to get a cache hit.

**Current data flow for the system prompt:**

```
agent_service._run_agent_graph()
  -> _build_system_prompt(base_prompt, project_id, ...)
     -> returns single string: base_prompt + optional project context section
  -> history.insert(0, SystemMessage(content=system_prompt))
  -> graph.astream_events({"messages": history, ...})

agent_service._create_deep_agent_graph()
  -> DeepAgentOrchestrator(system_prompt=base_prompt)  # base prompt only
  -> orchestrator.create_agent()
     -> final_system_prompt = base_prompt + TASK_SYSTEM_PROMPT + suffix
     -> langchain_create_agent(system_prompt=final_system_prompt)
```

**Critical observation:** There are TWO places where the system prompt is assembled:

1. **At graph compile time** (`DeepAgentOrchestrator.create_agent()`): The orchestrator assembles `base_prompt + TASK_SYSTEM_PROMPT + subagent_prompt_suffix` and passes it to `langchain_create_agent()`. This becomes the graph's baked-in system prompt.

2. **At invocation time** (`_run_agent_graph()`): `_build_system_prompt()` creates a new string with `base_prompt + project_context` and inserts it as a `SystemMessage` at the start of the conversation history. This is the message sent to the LLM on every turn.

The LLM receives BOTH: the graph's baked-in system prompt (from `create_agent`) AND the history's `SystemMessage` (from `_run_agent_graph`). The history `SystemMessage` is what varies per session and breaks prompt caching.

### Codebase Analysis

**Backend files involved:**

- `backend/app/ai/agent_service.py` -- `_build_system_prompt()` (line 1332), `_run_agent_graph()` (line 607), `_create_deep_agent_graph()` (line 299)
- `backend/app/ai/deep_agent_orchestrator.py` -- `create_agent()` (line 85), `_build_system_prompt_suffix()` (line 230)
- `backend/app/ai/graph_cache.py` -- `GraphCacheKey` dataclass, `CompiledGraphCache`
- `backend/app/ai/tools/subagent_task.py` -- `TASK_SYSTEM_PROMPT` constant

**Current prompt composition (what the LLM sees):**

1. **SystemMessage in history** (per-invocation, varies by project_id):
   - `base_prompt` + optional `"\n\nYou are operating in the context of a specific project (ID: {project_id})..."`
2. **Graph's internal system prompt** (per-graph, static for cached graphs):
   - `base_prompt + TASK_SYSTEM_PROMPT + _build_system_prompt_suffix()`

The graph's internal prompt is already static and cacheable. The history `SystemMessage` is the one that varies and breaks caching.

**Security model:** Project context enforcement is at the **tool level** via `ToolContext`, not in the system prompt. The system prompt text is purely informational -- it helps the LLM produce better responses but does not enforce anything. This is explicitly documented in `_build_system_prompt()` docstring.

**Existing patterns:**
- `DEFAULT_SYSTEM_PROMPT` is duplicated in both `agent_service.py` (line 142) and `deep_agent_orchestrator.py` (line 28) -- identical content, two locations
- ContextVar pattern (`set_request_context()`) already bridges per-request context into cached graphs

---

## Solution Options

### Option 1: Move Dynamic Context from SystemMessage to HumanMessage

**Architecture & Design:**

Instead of inserting project context into the `SystemMessage` at history position 0, insert it as a separate `HumanMessage` prefix (or use the existing user message with context prepended). The `SystemMessage` would contain only the static base prompt.

In `_run_agent_graph()`, the project context would be prepended to the user's actual message as a context block, e.g.:

```
[Context: You are in project scope ID {project_id}. Use project-scoped tools.]

{user's actual message}
```

This keeps the `SystemMessage` completely static across all sessions using the same assistant config, maximizing LLM provider cache hits.

**Implementation:**

1. Modify `_build_system_prompt()` to always return just `base_prompt` (remove project_id logic)
2. Modify `_run_agent_graph()` to prepend project context to the user's `HumanMessage` instead
3. No changes to `DeepAgentOrchestrator` or graph cache key computation
4. No changes to `langchain_create_agent()` call signature

**Trade-offs:**

| Aspect          | Assessment                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| Pros            | Minimal code change (2 files, ~20 lines); SystemMessage fully static; graph cache unaffected           |
| Cons            | Project context mixed into user message (less semantically clean); LLM may treat it differently than system-level instruction; context appears in every user turn (token overhead on multi-turn conversations) |
| Complexity      | Low                                                                                                    |
| Maintainability | Good -- simplifies `_build_system_prompt()` to a passthrough                                           |
| Performance     | Good prompt cache hit rate; slight token overhead from repeating context in each turn                  |

---

### Option 2: Dual SystemMessage Strategy (Static + Dynamic)

**Architecture & Design:**

Insert TWO `SystemMessage` objects at the start of history instead of one. The first `SystemMessage` contains the static base prompt (identical across all sessions). The second contains the dynamic project context (varies per session).

```
history = [
    SystemMessage(content=base_prompt),           # STATIC -- cacheable
    SystemMessage(content=project_context),       # DYNAMIC -- varies
    ... conversation history ...
]
```

LLM providers that support prompt caching (Anthropic Claude, OpenAI) cache based on prefix matching. If the first `SystemMessage` is identical across requests, it will be cached. The second message varies but only invalidates the cache from that point forward -- the first message's cache is still utilized.

**Implementation:**

1. Modify `_build_system_prompt()` to return a `tuple[str, str]` of `(static, dynamic)` instead of a single string
2. Modify `_run_agent_graph()` to insert both messages into history
3. No changes to `DeepAgentOrchestrator` (graph-level prompt remains unchanged)
4. No changes to graph cache key computation

**Trade-offs:**

| Aspect          | Assessment                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| Pros            | Clean semantic separation (system-level instructions vs. session context); provider cache hits on static prefix; no token overhead per turn |
| Cons            | Multiple SystemMessages may behave differently across providers; slightly more complex than Option 1; need to verify LangChain handles dual SystemMessages correctly |
| Complexity      | Low-Medium                                                                                             |
| Maintainability | Good -- clear separation of concerns                                                                   |
| Performance     | Best prompt cache behavior; no per-turn token overhead                                                 |

---

### Option 3: Remove Project Context from System Prompt Entirely (Rely on Tool-Level Enforcement)

**Architecture & Design:**

Remove the project context section from the system prompt completely. The system prompt would be purely the base prompt. Project awareness would be communicated to the LLM through the tool results themselves -- when the LLM calls `get_project_context`, it learns about the project scope naturally.

This aligns with the existing security model where enforcement is at the tool level. The system prompt currently says "enforcement happens at tool level via ToolContext" in its docstring, so this approach follows that principle to its logical conclusion.

**Implementation:**

1. Modify `_build_system_prompt()` to return just `base_prompt` unconditionally (remove all dynamic context logic)
2. Remove the `project_id`, `as_of`, `branch_name`, `branch_mode` parameters from `_build_system_prompt()` since they are unused
3. No changes to `DeepAgentOrchestrator` or graph cache

**Trade-offs:**

| Aspect          | Assessment                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| Pros            | Simplest implementation; SystemMessage fully static; eliminates the prompt injection surface area entirely; consistent with stated security architecture |
| Cons            | LLM may produce less contextually relevant first responses (does not know project scope until it calls `get_project_context`); slight UX regression in the first turn |
| Complexity      | Lowest                                                                                                 |
| Maintainability | Best -- removes unused parameters and simplifies the method signature                                  |
| Performance     | SystemMessage fully static -- maximum cache hit rate                                                   |

---

## Comparison Summary

| Criteria           | Option 1: HumanMessage Prefix            | Option 2: Dual SystemMessage            | Option 3: Remove Dynamic Context          |
| ------------------ | ---------------------------------------- | --------------------------------------- | ----------------------------------------- |
| Development Effort | Small (~20 lines, 2 files)               | Small (~30 lines, 2 files)              | Smallest (~10 lines, 1 file)              |
| Cache Effectiveness | Full (SystemMessage static)             | Partial (static prefix cached)          | Full (SystemMessage static)               |
| UX Quality         | Fair (context mixed with user message)   | Good (clean separation)                 | Good (first turn slightly less contextual) |
| Token Efficiency   | Poor (context repeated per turn)         | Good (context once in history)          | Best (no dynamic context tokens)          |
| Semantic Clarity   | Fair                                      | Good                                    | Best (aligns with security model)         |
| Flexibility        | Low (hard to extend)                     | Medium (can add more dynamic sections)  | Low (no dynamic context at all)           |
| Risk               | Low                                       | Medium (dual SystemMessage provider compat) | Low                                    |
| Best For           | Quick win, minimal disruption            | Balanced approach                       | Architectural purity, maximum simplicity  |

---

## Recommendation

**I recommend Option 3: Remove Dynamic Context from System Prompt Entirely**, with a small enhancement to address the UX concern.

**Rationale:**

1. **Architectural alignment.** The codebase already enforces project context at the tool level via `ToolContext`. The `_build_system_prompt()` docstring explicitly states: "Context: Project and temporal context are enforced at the tool level via ToolContext, not in the system prompt... The LLM has no control over temporal parameters." Adding project context to the system prompt is informational only and partially contradicts this stated design.

2. **Maximum caching benefit.** Removing the dynamic section entirely makes the `SystemMessage` completely static, ensuring 100% prompt cache hit rate across all sessions with the same assistant configuration.

3. **Simplicity.** The change removes code and parameters rather than adding complexity. `_build_system_prompt()` becomes a trivial method that could potentially be eliminated entirely (the caller can use the base prompt directly).

4. **Token efficiency.** No additional tokens spent on project context in the system prompt. The LLM discovers project scope naturally through tool calls, which is already the enforced behavior.

5. **The UX concern is manageable.** The first-turn response may be slightly less contextual, but:
   - The LLM still has access to `get_project_context` tool and will call it when needed
   - In the subagent path (primary), the main agent delegates to subagents who have direct tool access and project context in their `ToolContext`
   - In the direct tools path, the LLM has `get_project_context` available

**Alternative consideration:** Choose Option 2 if you want to preserve the current first-turn UX where the LLM immediately knows the project scope and produces a context-aware greeting without a tool call. This adds ~20 lines of code for a marginal UX improvement on the very first message.

**Proposed implementation for Option 3:**

1. Simplify `_build_system_prompt()` to return `base_prompt` unconditionally, or inline the base prompt directly at the call site
2. Remove unused parameters (`project_id`, `as_of`, `branch_name`, `branch_mode`) from the method signature
3. Update any tests that assert on the project context section being present
4. Verify that the existing `get_project_context` tool works correctly to provide project awareness on demand

**Files to change:**
- `backend/app/ai/agent_service.py` -- simplify or remove `_build_system_prompt()`, update `_run_agent_graph()` call site
- `backend/app/ai/deep_agent_orchestrator.py` -- deduplicate `DEFAULT_SYSTEM_PROMPT` (import from a shared location)

---

## Decision Questions

1. Is the first-turn UX (LLM knowing project scope without a tool call) important enough to warrant keeping some form of dynamic context in the prompt?
2. Should the `DEFAULT_SYSTEM_PROMPT` constant be consolidated into a single location (currently duplicated in `agent_service.py` and `deep_agent_orchestrator.py`)?
3. Which LLM provider(s) are you actively using or planning to use? This affects which prompt caching strategy the provider supports and whether Option 2's dual SystemMessage approach is viable.

---

## References

- `backend/app/ai/agent_service.py` -- `_build_system_prompt()` (line 1332), `_run_agent_graph()` (line 607), `_create_deep_agent_graph()` (line 299)
- `backend/app/ai/deep_agent_orchestrator.py` -- `create_agent()` (line 85), `_build_system_prompt_suffix()` (line 230)
- `backend/app/ai/graph_cache.py` -- `GraphCacheKey`, `CompiledGraphCache`
- `backend/app/ai/tools/subagent_task.py` -- `TASK_SYSTEM_PROMPT`
- `docs/02-architecture/ai-chat-developer-guide.md`
