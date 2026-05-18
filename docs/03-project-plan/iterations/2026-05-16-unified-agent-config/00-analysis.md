# Analysis: Unified AI Agent Configuration (Main + Specialist Architecture)

**Created:** 2026-05-16
**Request:** Redesign the AI chat agent system to unify configurable AI assistants with hardcoded specialist agents. Enable main agents to use some tools directly while delegating complex operations to specialists. Remove deep orchestrator mode.

---

## Problem Statement

The AI chat has two parallel, disconnected systems:

1. **AI Assistants** (DB-configurable): 3 seed rows in `ai_assistant_configs`. Users pick one per conversation. Tool access via RBAC role. No concept of "main" vs "specialist".

2. **AI Specialists** (hardcoded in `subagents/__init__.py`): 8 fixed dicts with explicit `allowed_tools`, system prompts. The supervisor orchestrator has **zero direct tool access** — it only delegates via handoff tools. Every single Backcast operation requires delegation overhead.

The supervisor cannot do anything directly. "Change as-of date" (a trivial `set_temporal_context` call) goes through: supervisor reads briefing → handoff to specialist → specialist invokes tool → findings compiled back → supervisor synthesizes. This adds latency, tokens, and a full specialist invocation for what should be a one-call operation.

---

## Key Decisions

- **Model**: All specialists inherit the main agent's LLM model (v1). Per-specialist models deferred.
- **Routing**: Admin-configured `direct_tools` list on main agent. LLM sees both direct + handoff tools, routing is implicit.
- **Default direct tools**: Temporal context (`get/set_temporal_context`) + `global_search`. Fully configurable per main agent.
- **Orchestrator**: Supervisor only. Remove deep orchestrator mode (`OrchestratorMode.DEEP`).

---

## Architecture

### Model Changes (`AIAssistantConfig`)

New columns:

| Column | Type | Purpose |
|--------|------|---------|
| `agent_type` | `String(20)` | `"main"` or `"specialist"` |
| `allowed_tools` | `JSONB (nullable)` | Tool whitelist for specialists. `None` = all tools. |
| `delegation_config` | `JSONB (nullable)` | For main agents: `{ direct_tools: [...], allowed_specialists: [...] or null }` |
| `structured_output_schema` | `String(100, nullable)` | FQCN for Pydantic model (e.g., `EVMMetricsRead`). Specialist-only. |
| `is_system` | `Boolean` | System agents can't be deleted, only disabled |

### Orchestrator Changes (`SupervisorOrchestrator`)

- Supervisor gets `get_briefing` + handoff tools + `direct_tools` from main agent's `delegation_config`
- Supervisor prompt becomes conditional (direct tools available vs delegate-only)
- Specialist configs loaded from DB instead of hardcoded dicts

### Tool Routing (3 layers, preserved)

1. Execution mode (SAFE/STANDARD/EXPERT) → risk level filter
2. RBAC role → permission filter
3. allowed_tools → specialist whitelist (main agents skip this)

### Specialist Loading

```python
# Current: get_all_subagents() -> hardcoded dicts
# New: DB query -> convert to same dict schema -> compile_subagents()
# Cached with TTL (5 min), invalidated on specialist CRUD
```

---

## Side Effects

1. **Performance**: DB query per graph compilation. Mitigated by TTL cache.
2. **Specialist name immutability**: Names used as graph node names, routing keys. Locked after creation.
3. **Structured output schema**: Only 3 schemas exist today. String reference resolved via registry.
4. **Deep orchestrator removal**: Eliminates one code path, simplifies maintenance.

---

## Business Value

1. **Speed for common operations**: Direct tool access eliminates briefing overhead for simple queries.
2. **Simplified orchestration**: One orchestration strategy to maintain, test, and debug.
3. **Admin-configurable specialists**: No code changes needed to tune specialist behavior.
4. **Delegation scoping**: Different main agents delegate to different specialist subsets.
5. **Future extensibility**: DB-backed specialists enable per-specialist models, metrics, A/B testing.

---

## Implementation Phases

### Phase 1: Database + model changes
- Alembic migration (new columns)
- Update `AIAssistantConfig` domain model
- Update Pydantic schemas with validation rules
- Create specialist seed data

### Phase 2: Specialist loading from DB
- `assistant_config_to_specialist_dict()` converter
- Specialist config cache (TTL + invalidation)
- Update `SupervisorOrchestrator` to load from DB
- Keep hardcoded fallback

### Phase 3: Direct tools for main agents
- Update `SupervisorOrchestrator.create_supervisor_graph` for direct tools
- Conditional supervisor prompt
- Pass `main_assistant_config` through orchestrator chain

### Phase 4: API + frontend
- Updated CRUD endpoints with `agent_type` filter
- Specialist management in admin UI
- Direct tools + specialist selector in main agent form
- Chat selector filters to `agent_type="main"` only

### Phase 5: Remove deep orchestrator
- Remove `deep_agent_orchestrator.py`
- Remove `OrchestratorMode.DEEP`, `AI_ORCHESTRATOR` setting, deep code path in `agent_service.py`

### Phase 6: Cleanup
- Remove `subagents/__init__.py` hardcoded specialists
- Remove `get_all_subagents()` / `get_subagent_by_name()`

---

## Critical Files

- `backend/app/models/domain/ai.py` — `AIAssistantConfig` model (+ new columns)
- `backend/app/ai/supervisor_orchestrator.py` — Core orchestrator (+ direct tools, DB loading)
- `backend/app/ai/subagents/__init__.py` — Hardcoded specialists (to be removed)
- `backend/app/ai/subagent_compiler.py` — Shared compilation logic
- `backend/app/ai/agent_service.py` — Runtime graph creation (+ pass main config, remove deep path)
- `backend/app/ai/deep_agent_orchestrator.py` — To be removed
- `backend/app/ai/config.py` — `AgentConfig` dataclass, `OrchestratorMode` (remove DEEP)
- `backend/app/models/schemas/ai.py` — Pydantic schemas (+ new fields + validation)
