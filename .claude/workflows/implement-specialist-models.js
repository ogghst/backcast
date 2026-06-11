export const meta = {
  name: 'implement-specialist-models',
  description: 'Implement per-specialist model selection code (backend + frontend), then validate with e2e tests',
  phases: [
    { title: 'Backend', detail: 'Write backend code for per-specialist model resolution' },
    { title: 'Frontend', detail: 'Write frontend code for specialist model config UI' },
    { title: 'E2E Test', detail: 'Start app at 192.168.1.15 and run e2e validation' },
  ],
}

// ── Phase 1: Backend Implementation ──
phase('Backend')

const backendResult = await agent(
  `WRITE CODE — do not produce a plan. Implement all changes described below.

## Task: Per-Specialist AI Provider/Model Selection (Backend)

Read the plan at /home/nicola/.claude/plans/analyze-changes-needed-to-sprightly-locket.md for full context.

### Files to modify (6 files):

**1. backend/app/ai/subagents/db_loader.py**
In \`assistant_config_to_specialist_dict()\`, add these fields to the returned dict:
- \`"model_id": str(config.model_id) if config.model_id else None\`
- \`"temperature": config.temperature\`
- \`"max_tokens": config.max_tokens\`

**2. backend/app/ai/subagent_compiler.py**
In \`compile_subagents()\`:
- Add keyword-only param \`specialist_models: dict[str, BaseChatModel] | None = None\`
- Inside the loop, resolve per-specialist model: \`specialist_model = (specialist_models or {}).get(name, model)\`
- Pass \`specialist_model\` (not \`model\`) to \`langchain_create_agent(model=specialist_model, ...)\`

**3. backend/app/ai/supervisor_orchestrator.py**
- Add \`specialist_models: dict[str, BaseChatModel] | None = None\` param to \`__init__()\`
- Store as \`self.specialist_models = specialist_models or {}\`
- At line ~273, forward to compile_subagents: add \`specialist_models=self.specialist_models\`

**4. backend/app/ai/agent_service.py**
Two changes:

a) In \`_prepare_graph_execution()\` after the main LLM creation (~line 718, after \`llm = await self._create_langchain_llm(...)\`), add specialist model resolution:

\`\`\`python
# Resolve specialist-specific models
specialist_models: dict[ChatOpenAI | ChatDeepSeek] = {}
try:
    specialist_configs = await load_specialists_from_db()
except Exception as exc:
    logger.warning("[SPECIALIST_MODELS] Failed to load specialist configs: %s", exc)
    specialist_configs = []

for sc in specialist_configs:
    smid = sc.get("model_id")
    if smid is None:
        continue
    try:
        s_client_config, s_model_name, _ = await self._get_llm_client_config(UUID(smid))
        s_llm = await self._create_langchain_llm(
            s_client_config,
            s_model_name,
            temperature=sc.get("temperature"),
            max_tokens=sc.get("max_tokens"),
        )
        specialist_models[sc["name"]] = s_llm
        logger.info("[SPECIALIST_MODELS] Resolved specialist '%s' -> model %s", sc["name"], s_model_name)
    except Exception as exc:
        logger.warning("[SPECIALIST_MODELS] Failed to resolve model for specialist '%s': %s", sc["name"], exc)
\`\`\`

Then pass \`specialist_models=specialist_models\` to \`GraphCreationParams(...)\`.

b) In \`_create_deep_agent_graph()\`, forward to orchestrator:
\`specialist_models=params.specialist_models\` in the \`SupervisorOrchestrator(...)\` constructor call.

Add the import for load_specialists_from_db at the top of agent_service.py if not already present:
\`from app.ai.subagents.db_loader import load_specialists_from_db\`

**5. backend/app/ai/graph_params.py**
Add field to GraphCreationParams dataclass:
\`specialist_models: dict[str, Any] | None = None\`

**6. backend/app/api/routes/ai_config.py**
Find where specialist cache invalidation happens (search for \`_invalidate_specialist_cache\`). In ALL places where it is called (create, update, delete handlers for specialist agent_type), ALSO add \`_invalidate_llm_caches()\`. Import it if not already imported.

### Critical requirements (from architecture review):
- Each specialist LLM resolution MUST be wrapped in individual try/except — one failure must NOT crash the whole execution
- load_specialists_from_db() call MUST be wrapped in try/except with fallback to empty list
- Pass temperature/max_tokens as None (not hardcoded defaults) — _create_langchain_llm already applies defaults
- Specialists with model_id=null MUST fall back to supervisor's model (they simply won't be in specialist_models dict)
- Reuse existing LLM config caches — do NOT create new caching mechanisms

### Quality checks (run on modified files only):
After all changes, run:
\`\`\`bash
cd /home/nicola/dev/backcast/backend && source .venv/bin/activate && uv run ruff check app/ai/subagents/db_loader.py app/ai/subagent_compiler.py app/ai/supervisor_orchestrator.py app/ai/agent_service.py app/ai/graph_params.py app/api/routes/ai_config.py && uv run mypy app/ai/subagents/db_loader.py app/ai/subagent_compiler.py app/ai/supervisor_orchestrator.py app/ai/agent_service.py app/ai/graph_params.py app/api/routes/ai_config.py
\`\`\`

Fix any linting or type errors.`,
  { label: 'backend-impl', phase: 'Backend', agentType: 'backend-developer' }
)

log(`Backend: ${backendResult}`)

// ── Phase 2: Frontend Implementation ──
phase('Frontend')

const frontendResult = await agent(
  `WRITE CODE — do not produce a plan. Implement all changes described below.

## Task: Per-Specialist Model Config UI (Frontend)

### Context
The backend now supports per-specialist model_id. Specialists with model_id=null use the supervisor's model (default). The frontend needs to let admins configure model selection for specialists.

### Read these files first to understand existing patterns:
1. frontend/src/features/ai/types.ts — current type definitions
2. frontend/src/features/ai/components/modal/ConfigurationSection.tsx — existing model selector (currently main-only)
3. frontend/src/features/ai/components/AIAssistantModal.tsx — modal that creates/edits assistant configs
4. frontend/src/features/ai/components/AIAssistantList.tsx — list showing assistant configs
5. frontend/src/features/ai/api/ — API hooks for fetching models/providers

### Files to modify:

**1. frontend/src/features/ai/types.ts**
- Make model_id nullable on specialist types: \`model_id: string | null\` (not just \`string\`)
- Ensure AIAssistantCreate allows \`model_id: string | null\` and \`temperature: number | null\` and \`max_tokens: number | null\`

**2. frontend/src/features/ai/components/modal/ConfigurationSection.tsx**
- Currently model selector only renders for agentType === "main"
- Change it to also render for agentType === "specialist"
- For specialists, add a first option "Use supervisor default" that sets model_id to null
- Show model options as "ProviderName / ModelName" format
- For specialists, show temperature and max_tokens as optional InputNumber fields (nullable)
- recursion_limit should remain main-agent-only

**3. frontend/src/features/ai/components/AIAssistantModal.tsx**
- STOP deleting model_id/temperature/max_tokens from specialist submissions (remove the \`delete values.model_id\` lines for specialists)
- Set proper initial values for specialists when editing
- Convert empty model_id string to null before submission

**4. frontend/src/features/ai/components/AIAssistantList.tsx**
- In the table, show "Supervisor default" for specialists with model_id === null
- Show actual model name for specialists with a configured model_id

**5. Tests** — update existing tests to match new nullable types, add test for specialist model selection

### Key requirements:
- "Use supervisor default" MUST be the default/first option for specialists
- The form must correctly send model_id: null (not empty string) when default is selected
- Follow existing Ant Design component patterns
- Match existing code style exactly

### Quality checks:
\`\`\`bash
cd /home/nicola/dev/backcast/frontend && npm run lint && npm run typecheck && npm test
\`\`\`

Fix any errors.`,
  { label: 'frontend-impl', phase: 'Frontend', agentType: 'frontend-developer' }
)

log(`Frontend: ${frontendResult}`)

// ── Phase 3: E2E Validation ──
phase('E2E Test')

const e2eResult = await agent(
  `Validate the per-specialist model selection feature end-to-end by starting the application and testing in the browser.

## Step 1: Start Backend
Start the backend server:
\`\`\`bash
cd /home/nicola/dev/backcast/backend && source .venv/bin/activate && uv run uvicorn app.main:app --host 192.168.1.15 --port 8020 &
\`\`\`
Wait for it to be ready (check http://192.168.1.15:8020/docs returns 200).

## Step 2: Start Frontend
Start the frontend dev server:
\`\`\`bash
cd /home/nicola/dev/backcast/frontend && npm run dev -- --host 192.168.1.15 --port 5173 &
\`\`\`
Wait for it to be ready.

## Step 3: E2E Test Scenarios (use Playwright MCP)

### Scenario 1: Specialist Model Config UI
1. Navigate to http://192.168.1.15:5173 and log in
2. Navigate to the AI configuration page where assistant configs are managed
3. Find a specialist config (agent_type='specialist') and click edit
4. VERIFY: A model selector dropdown is visible for the specialist
5. VERIFY: The dropdown includes a "Use supervisor default" option
6. VERIFY: The dropdown lists available models with provider names
7. Select a specific model (NOT default) for the specialist
8. Save the config
9. Re-open the same specialist config
10. VERIFY: The previously selected model is still selected

### Scenario 2: Default Fallback
1. Edit the same specialist config
2. Select "Use supervisor default" in the model dropdown
3. Save
4. Re-open and VERIFY: "Use supervisor default" is selected (model_id = null)

### Scenario 3: Backend Model Resolution (check logs)
1. Check backend logs for any errors related to specialist model resolution
2. If possible, configure a specialist with a specific model and trigger a chat that uses that specialist
3. Check logs for "[SPECIALIST_MODELS] Resolved specialist" messages

### Scenario 4: List Display
1. Navigate to the assistant config list
2. VERIFY: Specialists show "Supervisor default" or their model name in the model column
3. VERIFY: Main agents show their actual model name

## Step 4: Cleanup
Kill both the backend and frontend processes.

## Report
For each scenario, report PASS/FAIL with details of what was verified. If any scenario fails, include the specific error or UI state observed.`,
  { label: 'e2e-validation', phase: 'E2E Test' }
)

log(`E2E: ${e2eResult}`)

return {
  backendStatus: backendResult ? 'completed' : 'failed',
  frontendStatus: frontendResult ? 'completed' : 'failed',
  e2eStatus: e2eResult ? 'completed' : 'failed',
}
