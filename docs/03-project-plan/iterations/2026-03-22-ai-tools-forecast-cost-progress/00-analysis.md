# Analysis: AI Tools for Forecast, Cost Registration, and Progress Entry

**Created:** 2026-03-22
**Request:** Add AI tools for cost element forecasts, cost registrations, and progress tracking to the Backcast EVS system

---

## Clarified Requirements

### Functional Requirements

The user requests AI tool wrappers for three existing service layers to enable natural language interaction with:

1. **ForecastService** (branchable entity):
   - Get forecast by cost element ID
   - Create/update forecasts with branch support
   - Compare forecast to budget (variance analysis)
   - List forecasts with filtering

2. **CostRegistrationService** (global facts):
   - Get budget status (budget, used, remaining, percentage)
   - Create cost registrations (actual costs)
   - List cost registrations with pagination
   - Get cost trends by period (daily/weekly/monthly)
   - Get cumulative costs over time

3. **ProgressEntryService** (global facts):
   - Get latest progress entry for cost element
   - Record progress (create/update)
   - Get progress history for charts/trends

4. **Bulk Summary Tool**:
   - Get comprehensive summary of cost elements including forecasts, costs, and progress

### Non-Functional Requirements

- Follow existing tool patterns from `cost_element_template.py` and `analysis_template.py`
- Use `@ai_tool` decorator with proper permissions
- Include temporal logging for observability
- Use LangChain BaseTool integration
- Register tools in `__init__.py`
- Maintain consistency with existing AI tool architecture

### Constraints

- Service layer is already complete - tools MUST wrap existing methods, NOT duplicate business logic
- Must respect EVCS versioning architecture (temporal context for branchable entities)
- Must follow RBAC permission model
- Tools should be AI-friendly (return structured dictionaries, not domain models)

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- **E09-U08: AI-Assisted CRUD Tools** (8 points, High priority) - Currently in progress
  - "Implement create/update/delete tools for Cost Elements and related entities"
  - Includes Schedule Baseline, Forecast, Cost Registration, and Progress Entry tools

**Business Requirements:**
From `docs/01-product-scope/functional-requirements.md`:
- **Section 6: Cost Management Requirements** - Budget tracking, cost imputation, forecast updates
- **Section 6.1.1: Cost Element Schedule Baseline** - Versioned, branchable forecasts
- **EVM Requirements** - Progress tracking and cost registration are fundamental to EVM calculations

### Architecture Context

**Bounded Contexts Involved:**
- **Cost Management** (Cost Elements, Forecasts, Cost Registrations)
- **Progress Tracking** (Progress Entries)
- **AI Agent** (Tool orchestration and natural language interface)

**Existing Patterns to Follow:**

1. **Tool Decorator Pattern** (`backend/app/ai/tools/decorator.py`):
   ```python
   @ai_tool(
       name="tool_name",
       description="Human-readable description for LLM",
       permissions=["permission-scope"],
       category="category-name",
   )
   async def tool_function(
       param: type,
       context: Annotated[ToolContext, InjectedToolArg] = None,
   ) -> dict[str, Any]:
   ```

2. **Temporal Context Pattern** (for branchable entities):
   - Import `log_temporal_context` and `add_temporal_metadata`
   - Call `log_temporal_context()` at tool start
   - Call `add_temporal_metadata()` on return
   - Update descriptions to mention temporal context enforcement

3. **Service Wrapping Pattern**:
   - Import service methods (NOT duplicate logic)
   - Use `context.session` for database access
   - Use `context.user_id` for actor tracking
   - Convert domain models to AI-friendly dictionaries

4. **Tool Registration Pattern** (`backend/app/ai/tools/__init__.py`):
   - Import template module
   - Add tool functions to list in `create_project_tools()`
   - Tools are already BaseTool instances from decorator

**Architectural Constraints:**
- **EVCS Versioning**: Forecasts are branchable (use `ForecastService` with branch parameter)
- **Global Facts**: Cost registrations and progress entries are versionable but NOT branchable
- **RBAC**: Tools must check permissions via decorator
- **Temporal Logging**: All tools should log temporal context for observability

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `backend/app/api/routes/forecasts.py` - Forecast REST API endpoints
- `backend/app/api/routes/cost_registrations.py` - Cost Registration REST API endpoints
- `backend/app/api/routes/progress_entries.py` - Progress Entry REST API endpoints (if exists)

**Data Models:**
- `backend/app/models/domain/forecast.py` - Forecast entity (branchable)
- `backend/app/models/domain/cost_registration.py` - CostRegistration entity (global facts)
- `backend/app/models/domain/progress_entry.py` - ProgressEntry entity (global facts)

**Service Layer (Complete):**
- `backend/app/services/forecast_service.py` - `ForecastService` class
  - Key methods: `get_by_id()`, `get_for_cost_element()`, `create_forecast()`, `update_forecast()`, `list()`
- `backend/app/services/cost_registration_service.py` - `CostRegistrationService` class
  - Key methods: `get_budget_status()`, `create_cost_registration()`, `get_cost_registrations()`, `get_costs_by_period()`, `get_cumulative_costs()`
- `backend/app/services/progress_entry_service.py` - `ProgressEntryService` class
  - Key methods: `get_latest_progress()`, `create()`, `update()`, `get_progress_history()`

**Similar Patterns:**
- `backend/app/ai/tools/templates/cost_element_template.py` - Cost Element CRUD tools (temporal, branchable)
- `backend/app/ai/tools/templates/analysis_template.py` - EVM analysis tools (wraps `EVMService`)

**Tool Registration:**
- `backend/app/ai/tools/__init__.py` - Central tool registry
- Currently has 45+ tools across multiple templates
- Pattern: Import template module, extend tools list, re-export

**Frontend:**
- No changes required - tools are discovered dynamically via OpenAPI/assistant configuration
- Frontend already handles tool execution via WebSocket streaming

---

## Solution Options

### Option 1: Single Comprehensive Template (Recommended)

**Architecture & Design:**
Create a single template file `forecast_cost_progress_template.py` that contains all tools for the three service layers. Tools are organized into clear sections by service:

- **Forecast Tools** (4 tools): get, create, update, compare-to-budget
- **Cost Registration Tools** (5 tools): budget-status, create, list, trends, cumulative
- **Progress Entry Tools** (3 tools): get-latest, create, history
- **Summary Tool** (1 tool): comprehensive cost element summary

**UX Design:**
- Natural language queries like "What's the forecast for mechanical assembly?" map to forecast tools
- "How much budget is left for engineering?" maps to budget status tool
- "Record 50% progress for electrical assembly" maps to progress create tool
- "Show cost trends for January" maps to cost trends tool
- "Give me a summary of all cost elements" maps to summary tool

**Implementation:**
- **File**: `backend/app/ai/tools/templates/forecast_cost_progress_template.py`
- **Imports**: Service classes, Pydantic schemas, temporal logging helpers
- **Pattern**: Follow `cost_element_template.py` structure with temporal context for forecasts
- **Registration**: Add 13 tools to `__init__.py` in a new section
- **Permissions**:
  - Forecasts: `forecast-read`, `forecast-create`, `forecast-update`
  - Cost Registrations: `cost-registration-read`, `cost-registration-create`
  - Progress Entries: `progress-entry-read`, `progress-entry-create`

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Cohesive organization (related tools together)<br>- Single import in `__init__.py`<br>- Easier to maintain cross-tool dependencies (e.g., summary tool)<br>- Follows existing template pattern<br>- Clear separation of concerns (one section per service) |
| Cons            | - Larger file (~600-800 lines)<br>- All tools must be loaded together (minor performance impact) |
| Complexity      | Low - follows established patterns |
| Maintainability | Good - clear organization, comprehensive docstrings |
| Performance     | Excellent - minimal overhead, tools are lazy-loaded |

---

### Option 2: Separate Templates per Service

**Architecture & Design:**
Create three separate template files, one for each service layer:

- `forecast_template.py` - Forecast tools (4 tools)
- `cost_registration_template.py` - Cost Registration tools (5 tools)
- `progress_entry_template.py` - Progress Entry tools (3 tools)
- Summary tool goes in `forecast_template.py` (or separate file)

**UX Design:**
Same as Option 1 - UX is identical from user perspective.

**Implementation:**
- **Files**: 3-4 separate template files
- **Registration**: 3-4 separate imports and tool list extensions in `__init__.py`
- **Pattern**: Same as Option 1, just split across files

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Smaller files (~200-300 lines each)<br>- Clear separation by bounded context<br>- Can load services independently<br>- Easier to locate specific tools |
| Cons            | - More imports in `__init__.py`<br>- Summary tool needs to import from multiple services<br>- Harder to maintain cross-tool dependencies<br>- More files to manage |
| Complexity      | Low-Medium - multiple files to coordinate |
| Maintainability | Fair - good separation but more coordination overhead |
| Performance     | Excellent - same as Option 1 |

---

### Option 3: Hybrid Approach with Feature-Based Grouping

**Architecture & Design:**
Create templates based on user workflows rather than service boundaries:

- `cost_tracking_template.py` - Tools for cost registration and budget status
- `forecasting_template.py` - Tools for forecasts and variance analysis
- `progress_tracking_template.py` - Tools for progress entry and history
- `cost_element_summary_template.py` - Bulk summary tool

**UX Design:**
Same as Option 1 - UX is identical from user perspective.

**Implementation:**
- **Files**: 4 separate template files organized by workflow
- **Registration**: 4 separate imports in `__init__.py`
- **Pattern**: Same as Option 1, organized by user intent

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Aligned with user mental models<br>- Workflow-based organization<br>- Easier for non-technical users to understand |
| Cons            | - Doesn't match service layer architecture<br>- Harder to locate which file contains a tool<br>- More complex dependencies (cost tracking needs both cost_reg and forecast services)<br>- Creates artificial boundaries |
| Complexity      | Medium - architectural mismatch |
| Maintainability | Fair - workflow-based but architecturally misaligned |
| Performance     | Excellent - same as Option 1 |

---

## Comparison Summary

| Criteria           | Option 1 (Single Template) | Option 2 (Separate Templates) | Option 3 (Workflow-Based) |
| ------------------ | ---------- | ---------- | ---------- |
| Development Effort | 3-4 hours | 4-5 hours | 5-6 hours |
| UX Quality         | Excellent | Excellent | Excellent |
| Flexibility        | High | High | Medium |
| Maintainability    | Good | Fair | Fair |
| Architectural Fit  | Excellent | Good | Poor |
| Best For           | Cohesive feature delivery | Service separation | Workflow-centric organization |

---

## Recommendation

**I recommend Option 1 (Single Comprehensive Template) because:**

1. **Architectural Alignment**: The three services (Forecast, CostRegistration, ProgressEntry) are tightly coupled in the EVM domain. They're all used together for project performance tracking. Keeping them in one template reflects this domain cohesion.

2. **Simplified Maintenance**: A single file with clear sections is easier to maintain than multiple files. Cross-tool dependencies (like the summary tool) are simpler to implement.

3. **Consistent with Existing Patterns**: The `cost_element_template.py` already follows this pattern (Cost Element + Schedule Baseline tools together). This establishes precedent for keeping related entity tools together.

4. **Easier Testing**: A single template file can be tested as a unit. Integration tests can verify all tools work together correctly.

5. **Minimal Performance Impact**: Tools are lazy-loaded BaseTool instances. Having 13 tools in one file vs. 3 files has negligible performance difference.

6. **Clearer Documentation**: Comprehensive docstrings at the top of the file can explain the entire EVM tracking workflow, making it easier for developers to understand the big picture.

**Alternative consideration:** Choose Option 2 if the project team strongly prefers service-level separation or if there's a plan to add many more tools to each service in the future. However, for the current scope (13 tools total), Option 1 is more pragmatic.

---

## Decision Questions

1. **Tool Granularity**: Should the "compare forecast to budget" be a separate tool or integrated into the forecast get tool? (Recommend: separate tool for clearer LLM intent matching)

2. **Temporal Logging**: Should cost registration and progress entry tools include temporal logging even though they're not branchable? (Recommend: yes, for consistency and observability)

3. **Error Handling**: Should tools return error dictionaries or raise exceptions? (Recommend: return error dicts to match existing pattern)

4. **Bulk Operations**: Should we add bulk tools (e.g., create multiple cost registrations at once)? (Recommend: no, out of scope for current iteration)

5. **Summary Tool Scope**: Should the summary tool include WBE-level aggregates or only cost element details? (Recommend: cost element details only, WBE aggregates can be added later)

---

## User Decisions (2026-03-22)

All decisions align with analysis recommendations:

| Question | Decision | Rationale |
|----------|----------|-----------|
| **1. Tool Granularity** | Separate tool | Clearer LLM intent matching, simpler tool logic |
| **2. Temporal Logging** | Yes, log all tools | Consistent observability, better debugging/audit trail |
| **3. Error Handling** | Return error dicts | Consistent with existing 45+ tools, AI handles error in response |
| **4. Bulk Operations** | No, single records only | Simpler implementation, faster delivery, clear scope |
| **5. Summary Scope** | Cost element details only | Simpler, aligned with service layer scope, WBE aggregates can be added later |

**Implementation Impact:**
- Proceed with **Option 1 (Single Comprehensive Template)**
- 13 tools total: 4 forecast, 5 cost registration, 3 progress entry, 1 summary
- All tools use temporal logging for consistency
- Error handling follows existing pattern: `{"error": str, "details": dict}`
- No bulk operations in this iteration
- Summary tool focuses on cost element level data only

---

## References

**Architecture Docs:**
- [AI Tool Development Guide](../../02-architecture/ai/tool-development-guide.md)
- [Temporal Context Patterns](../../02-architecture/ai/temporal-context-patterns.md)
- [Bounded Contexts](../../02-architecture/01-bounded-contexts.md)

**Product Scope:**
- [Functional Requirements - Cost Management](../../01-product-scope/functional-requirements.md#6-cost-management-requirements)
- [EVM Requirements](../../01-product-scope/evm-requirements.md)

**Related User Stories:**
- [E09-U08: AI-Assisted CRUD Tools](../sprint-backlog.md) - Active iteration

**Existing Code:**
- [Cost Element Template](../../../backend/app/ai/tools/templates/cost_element_template.py) - Reference pattern
- [Analysis Template](../../../backend/app/ai/tools/templates/analysis_template.py) - Reference pattern
- [Tool Registration](../../../backend/app/ai/tools/__init__.py) - Registration pattern
- [Service Layer](../../../backend/app/services/) - ForecastService, CostRegistrationService, ProgressEntryService
