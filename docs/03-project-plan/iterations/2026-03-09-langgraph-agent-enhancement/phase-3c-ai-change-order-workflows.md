# Phase 3C: AI-Assisted Change Order Workflows (E09-U09)

**Status:** ✅ Completed

**Implementation Date:** 2025-03-20

## Overview

Implemented AI-powered change order draft generation with natural language requirement parsing and impact analysis integration.

## Components Implemented

### 1. AI Requirement Parser (`app/ai/change_order_parser.py`)

**New File:** `app/ai/change_order_parser.py`

**Key Features:**
- `ChangeOrderRequirementParser` class for natural language processing
- Extracts structured data from unstructured requirements:
  - Title and description refinement
  - Business justification
  - Budget impact estimates
  - Schedule impact (days)
  - Risk level assessment (Low/Medium/High)
  - Affected entities identification
  - Approval recommendations
  - Confidence scores

**Methods:**
- `parse_requirements()`: Core parsing using LLM
- `analyze_with_impact()`: Combines AI parsing with actual impact analysis
- `_validate_risk_level()`: Normalizes risk levels
- `_get_llm_client()`: Retrieves configured AI client
- `_get_model_name()`: Gets model for parsing

### 2. Change Order Service Enhancement (`app/services/change_order_service.py`)

**New Method:** `generate_draft()`

**Location:** Lines 1958-2060

**Features:**
- AI-powered draft generation
- Automatic branch creation (BR-{code} pattern)
- Fallback to manual data if AI fails
- Stores AI analysis in `impact_analysis_results` field
- Maps AI risk levels to impact levels (LOW/MEDIUM/HIGH)

**Signature:**
```python
async def generate_draft(
    self,
    project_id: UUID,
    title: str,
    description: str,
    reason: str,
    actor_id: UUID,
    branch: str = "main",
) -> ChangeOrder
```

**Returns:**
- Created ChangeOrder in Draft status
- Contains AI-generated analysis in `impact_analysis_results`

### 3. AI Tool Update (`app/ai/tools/templates/change_order_template.py`)

**Updated Tool:** `generate_change_order_draft`

**Changes:**
- Added `actor_id` parameter using `context.user_id`
- Enhanced response format with AI analysis data:
  - `estimated_budget_impact`: AI-parsed budget impact
  - `estimated_schedule_impact_days`: AI-parsed schedule impact
  - `risk_assessment`: AI risk evaluation
  - `recommendation`: AI approval recommendation
  - `confidence_score`: Analysis confidence (0.0-1.0)
  - `affected_entities`: List of impacted entities
  - `impact_level`: Mapped impact level
  - `branch`: Branch name
  - `code`: Change order code

## Testing

### Unit Tests (`tests/unit/ai/test_change_order_parser.py`)

**Test Coverage:**
- ✅ `test_parse_requirements_success`: Successful parsing with AI
- ✅ `test_parse_requirements_invalid_json`: JSON parsing error handling
- ✅ `test_validate_risk_level`: Risk level normalization
- ✅ `test_parse_requirements_no_provider`: Missing provider handling
- ✅ `test_parse_requirements_no_model`: Missing model handling
- ✅ `test_analyze_with_impact_only`: Analysis without existing change order

**All tests pass:** 6/6 ✅

### Integration Tests (`tests/integration/services/test_change_order_generate_draft.py`)

**Test Coverage:**
- ✅ `test_generate_draft_success`: Full draft generation with AI
- ✅ `test_generate_draft_ai_fallback`: Fallback when AI fails
- ✅ `test_generate_draft_project_not_found`: Error handling
- ✅ `test_generate_draft_branch_creation`: Branch structure verification

## Quality Assurance

### Ruff Linting
✅ **All checks pass** for:
- `app/ai/change_order_parser.py`
- `app/services/change_order_service.py`
- `app/ai/tools/templates/change_order_template.py`

### MyPy Type Checking
✅ **Strict mode pass** for all modified files:
- Zero type errors
- Proper type hints throughout
- Correct use of generics and protocols

## Usage Examples

### Via AI Tool (Natural Language)

```
User: "I need to add safety sensors to the assembly line.
       Updated regulations require this. It will cost about €25,000
       and take 5 days to install."

AI: Generates draft change order with:
    - Title: "Add Safety Sensors"
    - Description: "Install additional safety sensors on assembly line"
    - Reason: "Updated safety regulations require additional sensors"
    - Budget Impact: €25,000
    - Schedule Impact: 5 days
    - Risk Level: Low
    - Recommendation: Approve
    - Confidence: 0.85
```

### Via API (Programmatic)

```python
service = ChangeOrderService(session)

draft = await service.generate_draft(
    project_id=project_uuid,
    title="Add Safety Sensors",
    description="Install additional safety sensors on assembly line",
    reason="Updated safety regulations require additional sensors",
    actor_id=user_uuid,
)

# Access AI-generated analysis
ai_analysis = draft.impact_analysis_results["ai_analysis"]
print(f"Budget Impact: €{ai_analysis['estimated_budget_impact']}")
print(f"Confidence: {ai_analysis['confidence_score']}")
```

## Integration Points

### 1. ImpactAnalysisService
- `analyze_with_impact()` merges AI estimates with actual project data
- Provides confidence scores based on data availability
- Falls back to AI estimates when actual analysis unavailable

### 2. Branching System
- Creates BR-{code} branch automatically
- Follows existing change order branching patterns
- Maintains branch isolation for negotiation phase

### 3. Approval Workflow
- Generates draft in "Draft" status
- Includes impact level for approval matrix routing
- Provides recommendation for approver guidance

## Architecture Compliance

✅ **Layered Architecture:**
- AI parsing in `app/ai/` (infrastructure layer)
- Service logic in `app/services/` (service layer)
- Model access via existing repository pattern

✅ **EVCS Patterns:**
- Uses `TemporalBase` for ChangeOrder
- Proper branch creation and management
- Follows versioning and branching protocols

✅ **Error Handling:**
- Graceful fallback when AI unavailable
- Proper exception propagation
- Clear error messages for debugging

## Performance Considerations

- **AI Latency:** LLM calls may take 1-3 seconds
- **Caching:** AI responses not cached (consider for future)
- **Fallback:** Manual data creation ensures reliability
- **Database:** Single transaction for draft + branch creation

## Future Enhancements

### Potential Improvements:
1. **Iterative Refinement:** Allow users to ask AI to modify drafts
2. **Confidence Thresholds:** Require human review below threshold
3. **Historical Learning:** Improve estimates from past change orders
4. **Multi-entity Detection:** Better entity recognition for WBEs/CEs
5. **Schedule Analysis:** Integrate with schedule baseline service
6. **Cost Breakdown:** Detailed cost element impact analysis

### Known Limitations:
1. AI estimates may not reflect actual project constraints
2. Entity detection relies on naming patterns
3. Schedule impact is purely time-based (no dependency analysis)
4. No integration with resource availability

## Files Modified

### New Files:
- `app/ai/change_order_parser.py` (274 lines)
- `tests/unit/ai/test_change_order_parser.py` (256 lines)
- `tests/integration/services/test_change_order_generate_draft.py` (213 lines)

### Modified Files:
- `app/services/change_order_service.py` (+103 lines)
- `app/ai/tools/templates/change_order_template.py` (+26 lines, -9 lines)

### Documentation:
- `docs/03-implementation/phase-3c-ai-change-order-workflows.md` (this file)

## Verification Commands

```bash
# Run unit tests
uv run pytest tests/unit/ai/test_change_order_parser.py -v

# Run integration tests
uv run pytest tests/integration/services/test_change_order_generate_draft.py -v

# Run linting
uv run ruff check app/ai/change_order_parser.py app/services/change_order_service.py

# Run type checking
uv run mypy app/ai/change_order_parser.py --strict
uv run mypy app/services/change_order_service.py --strict
```

## Dependencies

### Required:
- `openai` - For LLM client
- `langchain` - For AI tool integration
- Existing `ImpactAnalysisService`
- Existing `AIConfigService`

### AI Configuration:
- Requires configured AI provider
- Requires configured AI model
- Requires API key for chosen provider

## Security Considerations

✅ **RBAC Integration:**
- Tool requires `change-order-create` permission
- User ID tracked for audit trail
- No privileged operations without authorization

✅ **Data Privacy:**
- Project data sent to external AI (if using cloud provider)
- Consider local models for sensitive data
- AI prompts don't expose internal implementation details

✅ **Input Validation:**
- All inputs validated via Pydantic schemas
- SQL injection protected via ORM
- Prompt injection mitigated via structured prompts

## Rollback Plan

If issues arise:
1. AI tool can be disabled via `allowed_tools` config
2. Service method has fallback to manual data
3. Existing change order creation workflow unchanged
4. No database schema changes required

## Success Criteria

✅ **All criteria met:**
1. ✅ `generate_draft()` method implemented in ChangeOrderService
2. ✅ AI-powered requirement parser created
3. ✅ Integration with ImpactAnalysisService
4. ✅ AI tool updated to use new method
5. ✅ All tests pass (unit + integration)
6. ✅ Code quality checks pass (Ruff + MyPy)
7. ✅ Documentation complete

---

**Implementation by:** Claude (Backend Architect)
**Review Status:** Ready for code review
**Next Steps:** Deploy to staging environment for user acceptance testing
