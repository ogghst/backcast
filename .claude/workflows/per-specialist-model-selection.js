export const meta = {
  name: 'per-specialist-model-selection',
  description: 'Validate architecture, implement per-specialist AI provider selection (backend + frontend), and e2e test',
  phases: [
    { title: 'Validate', detail: 'Adversarial architecture review of the plan' },
    { title: 'Backend', detail: 'Implement per-specialist model resolution pipeline' },
    { title: 'Frontend', detail: 'Add specialist provider/model config UI' },
    { title: 'E2E Test', detail: 'Start app at 192.168.1.15 and run e2e tests' },
  ],
}

// ── Phase 1: Validate Architecture ──
phase('Validate')

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    decision: { type: 'string', enum: ['approved', 'approved_with_notes', 'rejected'] },
    robustness_issues: { type: 'array', items: { type: 'string' } },
    reliability_issues: { type: 'array', items: { type: 'string' } },
    suggested_improvements: { type: 'array', items: {
      type: 'object',
      properties: {
        description: { type: 'string' },
        file: { type: 'string' },
        priority: { type: 'string', enum: ['critical', 'important', 'nice-to-have'] },
      },
      required: ['description', 'priority'],
    }},
    fallback_default_provider: { type: 'string', enum: ['sound', 'unsound'] },
    cache_coherence: { type: 'string', enum: ['sound', 'unsound'] },
    error_handling: { type: 'string', enum: ['adequate', 'needs_improvement'] },
    notes: { type: 'string' },
  },
  required: ['decision', 'robustness_issues', 'reliability_issues', 'suggested_improvements', 'fallback_default_provider', 'cache_coherence', 'error_handling'],
}

const reviewResult = await agent(`You are reviewing the architectural plan for allowing specialist agents to use a different AI provider than their supervisor in the Backcast project.

Read the plan at /home/nicola/.claude/plans/analyze-changes-needed-to-sprightly-locket.md

Then READ these critical files to understand the current implementation:
1. backend/app/ai/subagents/db_loader.py — specialist dict conversion
2. backend/app/ai/subagent_compiler.py — compile_subagents() function
3. backend/app/ai/supervisor_orchestrator.py — SupervisorOrchestrator class (especially __init__ and create_supervisor_graph)
4. backend/app/ai/agent_service.py — _prepare_graph_execution() around line 460-770 and _get_llm_client_config() around line 340-390 and _create_langchain_llm() around line 395-465
5. backend/app/ai/graph_params.py — GraphCreationParams dataclass
6. backend/app/api/routes/ai_config.py — cache invalidation handlers for specialist configs
7. backend/app/models/domain/ai.py — AIAssistantConfig model (around line 121-180)

Evaluate:
1. **Robustness**: What happens when a specialist's model_id points to an inactive provider? When the DB is slow? When multiple specialists share the same model_id — is caching correct? What if load_specialists_from_db() fails?
2. **Reliability**: Is the fallback to supervisor's model truly seamless? Could a partially-resolved specialist_models dict cause inconsistent behavior? Are there race conditions with cache invalidation?
3. **Default provider fallback**: When a specialist has model_id=null, does it reliably fall back to the supervisor's model? Verify the code path.
4. **Cache coherence**: If a specialist's model_id changes, will the LLM instance be re-created? Check that _invalidate_llm_caches() and _invalidate_specialist_cache() are both called in the right places.
5. **Error handling**: If _create_langchain_llm() fails for one specialist, does it affect others?

Be adversarial. Find real issues, not theoretical ones. Return your findings.`, { schema: REVIEW_SCHEMA, phase: 'Validate' })

log(`Architecture review: ${reviewResult.decision}`)
if (reviewResult.robustness_issues.length > 0) log(`Robustness issues: ${reviewResult.robustness_issues.join('; ')}`)
if (reviewResult.reliability_issues.length > 0) log(`Reliability issues: ${reviewResult.reliability_issues.join('; ')}`)

// ── Phase 2: Backend Implementation ──
phase('Backend')

const reviewNotes = reviewResult.notes || ''
const improvements = reviewResult.suggested_improvements || []

const backendPrompt = `Implement per-specialist AI provider/model selection in the Backcast backend.

## Plan (read full plan at /home/nicola/.claude/plans/analyze-changes-needed-to-sprightly-locket.md)

### What to implement:

**1. backend/app/ai/subagents/db_loader.py** — Add model_id, temperature, max_tokens to specialist dict:
- In assistant_config_to_specialist_dict(), add:
  - "model_id": str(config.model_id) if config.model_id else None
  - "temperature": config.temperature (nullable float)
  - "max_tokens": config.max_tokens (nullable int)

**2. backend/app/ai/subagent_compiler.py** — Per-specialist model resolution:
- Add specialist_models: dict[str, BaseChatModel] | None = None keyword-only param to compile_subagents()
- For each specialist: specialist_model = specialist_models.get(name, model)
- Pass specialist_model to langchain_create_agent() instead of model

**3. backend/app/ai/supervisor_orchestrator.py** — Forward specialist_models:
- Add specialist_models: dict[str, BaseChatModel] | None = None to __init__()
- Store as self.specialist_models = specialist_models or {}
- Forward to compile_subagents() call at ~line 273

**4. backend/app/ai/agent_service.py** — Pre-resolve specialist LLMs:
- In _prepare_graph_execution() after main LLM creation (~line 718):
  - Load specialist configs via load_specialists_from_db()
  - For each with non-null model_id: call _get_llm_client_config(UUID(smid)) + _create_langchain_llm(client_config, model_name, temperature=sc.get("temperature"), max_tokens=sc.get("max_tokens"))
  - Build specialist_models dict mapping specialist name → LLM instance
  - Pass to GraphCreationParams(specialist_models=specialist_models)
- In _create_deep_agent_graph(): pass params.specialist_models to SupervisorOrchestrator()

**5. backend/app/ai/graph_params.py** — Add specialist_models field:
- Add specialist_models: dict[str, Any] | None = None to GraphCreationParams

**6. backend/app/api/routes/ai_config.py** — Cache invalidation:
- In specialist config update/delete handlers, add _invalidate_llm_caches() alongside _invalidate_specialist_cache()

### Architecture review findings to address:
${improvements.filter(i => i.priority === 'critical').map(i => `- [CRITICAL] ${i.description}`).join('\n')}
${improvements.filter(i => i.priority === 'important').map(i => `- [IMPORTANT] ${i.description}`).join('\n')}

### Key requirements:
- Specialists with model_id=null MUST fall back to the supervisor's model (default behavior)
- If _create_langchain_llm() fails for one specialist, log warning and skip — do NOT affect other specialists
- Reuse existing _llm_config_cache and _llm_cache for specialist LLM instances
- All specialist LLM resolution happens in _prepare_graph_execution() (async context with DB session)
- Must pass: cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest -k "test_" (run quality on modified files only)

Read the existing code carefully before making changes. Match existing patterns and style.`

const backendResult = await agent(backendPrompt, { label: 'backend-implementation', phase: 'Backend', agentType: 'backend-developer' })

log(`Backend implementation: ${backendResult}`)

// ── Phase 3: Frontend Implementation ──
phase('Frontend')

const frontendPrompt = `Add specialist provider/model configuration UI to the Backcast frontend.

## Context
The backend now supports per-specialist model_id (AIAssistantConfig.model_id). When null, specialists use the supervisor's model. The frontend needs to let admins configure which model each specialist uses.

## What to implement:

### 1. Read existing AI config UI first:
- Check frontend/src/features/ai/ for existing AI configuration components
- Check frontend/src/pages/ for any admin/settings pages with AI config
- Check what API endpoints exist in backend/app/api/routes/ai_config.py for model/provider listing

### 2. Add model selection to specialist config forms:
- Find the existing form/modal where specialist (AIAssistantConfig with agent_type='specialist') configs are edited
- Add a model selector dropdown that:
  - Fetches available models from the API (GET /api/v1/ai/models or similar)
  - Shows provider name + model name (e.g., "Z.AI / glm-4.7", "OpenAI / gpt-4o")
  - Has a "Use supervisor default" option (sets model_id to null)
  - Pre-selects the current model_id if set
- Add temperature and max_tokens inputs (optional, nullable) to the same form

### 3. Ensure the API types are updated:
- Check if frontend/src/features/ai/types.ts or generated types include model_id on assistant config schemas
- If using OpenAPI-generated types, run: cd frontend && npm run generate-client
- If manual types, add model_id: string | null, temperature: number | null, max_tokens: number | null

### Key requirements:
- "Use supervisor default" must be the default selection (model_id = null) — this is the safe default
- Show model provider name alongside model name for clarity
- Follow existing UI patterns (Ant Design components, form layouts)
- Must pass: cd frontend && npm run lint && npm run typecheck
- Run tests: cd frontend && npm test

Read the existing AI config UI code carefully before making changes. Match existing patterns and component structure.`

const frontendResult = await agent(frontendPrompt, { label: 'frontend-implementation', phase: 'Frontend', agentType: 'frontend-developer' })

log(`Frontend implementation: ${frontendResult}`)

// ── Phase 4: E2E Validation ──
phase('E2E Test')

const e2ePrompt = `Validate the per-specialist model selection feature end-to-end.

## Setup
1. Start the backend: cd /home/nicola/dev/backcast/backend && source .venv/bin/activate && uv run uvicorn app.main:app --host 192.168.1.15 --port 8020
2. Start the frontend: cd /home/nicola/dev/backcast/frontend && npm run dev -- --host 192.168.1.15 --port 5173
3. Wait for both to be ready

## E2E Test Scenarios

### Scenario 1: Verify specialist model config UI
1. Navigate to http://192.168.1.15:5173 and log in
2. Navigate to the AI configuration page where specialist configs are managed
3. Verify that each specialist config shows a model selector dropdown
4. Verify the dropdown includes "Use supervisor default" option and lists available models
5. Select a specific model for one specialist (e.g., project_manager)
6. Save and verify the selection persists after page reload

### Scenario 2: Verify backend uses correct model
1. Open the AI chat interface
2. Send a message that triggers the specialist whose model was changed
3. Check backend logs (tail -f backend/logs/app.log) for "[SPECIALIST_MODELS] Resolved specialist" messages
4. Verify the specialist uses the configured model, not the supervisor's model

### Scenario 3: Verify default fallback
1. Set a specialist's model_id back to null ("Use supervisor default")
2. Send another chat message triggering that specialist
3. Verify in logs that no specialist-specific LLM is created for that specialist
4. Verify the specialist uses the supervisor's model

### Scenario 4: Error resilience
1. If possible, configure a specialist with a model from an inactive provider
2. Send a chat message triggering that specialist
3. Verify the system falls back gracefully (log warning, use default model)

After testing, shut down both servers. Report all findings.`

const e2eResult = await agent(e2ePrompt, { label: 'e2e-validation', phase: 'E2E Test' })

log(`E2E validation complete: ${e2eResult}`)

return {
  architectureReview: reviewResult.decision,
  robustnessIssues: reviewResult.robustness_issues,
  reliabilityIssues: reviewResult.reliability_issues,
  improvements: reviewResult.suggested_improvements,
  backendStatus: backendResult ? 'completed' : 'failed',
  frontendStatus: frontendResult ? 'completed' : 'failed',
  e2eStatus: e2eResult ? 'completed' : 'failed',
}
