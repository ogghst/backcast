# Plan: Tool Output Truncation (Context Window Protection)

**Created:** 2026-04-03
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Option 1 -- Inline in BackcastSecurityMiddleware

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 from analysis (Truncation Inline in BackcastSecurityMiddleware)
- **Architecture**: Extend the existing `BackcastSecurityMiddleware.awrap_tool_call()` to truncate ToolMessage content after handler execution. No new modules, classes, or middleware.
- **Key Decisions**:
  - Default budget: 20,000 characters (~5K tokens), adjustable per-tool
  - Truncation marker includes original size for LLM context
  - Tools opt out via `max_output_chars=None` (meaning "no limit")
  - Single private method `_truncate_output()` on the middleware class
  - Logging at WARNING level for every truncation event
  - Backward compatible: all existing tools unchanged unless output exceeds 20K chars

### Success Criteria

**Functional Criteria:**

- [ ] FR-1: Tool output exceeding 20,000 characters is truncated to the budget with a summary marker suffix. VERIFIED BY: T-001, T-002
- [ ] FR-2: Individual tools can specify a custom `max_output_chars` via `@ai_tool` decorator that overrides the default. VERIFIED BY: T-003
- [ ] FR-3: Tools marked with `max_output_chars=None` are exempt from truncation entirely. VERIFIED BY: T-004
- [ ] FR-4: Truncated outputs include a machine-readable suffix: `\n\n[Output truncated at {N} chars. Original size: {M} chars. Tool: {tool_name}]`. VERIFIED BY: T-001, T-002
- [ ] FR-5: Every truncation event is logged at WARNING level with tool_name, original_size, and truncated_size. VERIFIED BY: T-005
- [ ] FR-6: All existing tools function identically when output is below the budget (no content modification). VERIFIED BY: T-006

**Technical Criteria:**

- [ ] NFR-1: Truncation overhead < 1ms per tool call. VERIFIED BY: T-007 (timing benchmark test)
- [ ] NFR-2: Full MyPy strict mode compliance on all modified files. VERIFIED BY: `mypy` quality gate
- [ ] NFR-3: 90%+ test coverage for truncation logic. VERIFIED BY: `pytest --cov` on test file
- [ ] NFR-4: Zero configuration required for default behavior. VERIFIED BY: T-001 (no setup needed)
- [ ] Ruff zero errors on all modified files. VERIFIED BY: `ruff check` quality gate

**TDD Criteria:**

- [ ] All test cases written BEFORE implementation code
- [ ] Each test documents its failure mode (RED phase in DO)
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- `ToolMetadata` dataclass extension with `max_output_chars` field
- `@ai_tool` decorator extension with `max_output_chars` parameter
- `BackcastSecurityMiddleware._truncate_output()` private method
- Unit test file for all truncation logic
- `ToolMetadata.to_dict()` update to include the new field
- Annotating known high-output tools with appropriate limits

**Out of Scope:**

- Frontend changes (truncation is backend-only)
- Context window management beyond tool output (message compaction, etc.)
- Global configuration mechanism for default budget (hardcoded constant is sufficient)
- Truncation of non-string ToolMessage content (LangGraph always provides strings)
- New middleware class or new module/file for truncation logic
- Modifying the `_make_json_serializable` 100KB detection in agent_service.py
- Database schema changes

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|--------------|------------------|------------|
| 1 | Extend `ToolMetadata` with `max_output_chars` field | `backend/app/ai/tools/types.py` | None | Field exists with default `None`; `to_dict()` includes it; MyPy passes | Low |
| 2 | Extend `@ai_tool` decorator with `max_output_chars` parameter | `backend/app/ai/tools/decorator.py` | Task 1 | Parameter forwarded to `ToolMetadata`; tools can specify custom budget; MyPy passes | Low |
| 3 | Add `_truncate_output()` to `BackcastSecurityMiddleware` and integrate into `awrap_tool_call()` | `backend/app/ai/middleware/backcast_security.py` | Task 1 | Method truncates content over budget; marker suffix appended; WARNING logged; returns new ToolMessage | Medium |
| 4 | Write unit tests for truncation logic | `backend/tests/unit/ai/test_tool_output_truncation.py` | Task 1, 2, 3 | All 9 test cases pass; 90%+ coverage on truncation code paths | Medium |
| 5 | Annotate high-output tools with `max_output_chars` overrides | `backend/app/ai/tools/project_tools.py`, other tool files | Task 2 | Known list/analysis tools annotated; existing behavior preserved | Low |
| 6 | Run quality gates (MyPy, Ruff, test suite) | All modified files | Task 4, 5 | Zero errors on all gates | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FR-1: Default truncation at 20K chars | T-001 | `tests/unit/ai/test_tool_output_truncation.py` | Output > 20000 chars is truncated to 20000 + marker suffix |
| FR-1: Boundary at exactly 20K chars | T-002 | `tests/unit/ai/test_tool_output_truncation.py` | Output of exactly 20000 chars is NOT truncated |
| FR-2: Per-tool custom budget | T-003 | `tests/unit/ai/test_tool_output_truncation.py` | Tool with `max_output_chars=5000` truncates at 5000 |
| FR-3: Opt-out via None | T-004 | `tests/unit/ai/test_tool_output_truncation.py` | Tool with `max_output_chars=None` returns full output regardless of size |
| FR-5: Truncation logging | T-005 | `tests/unit/ai/test_tool_output_truncation.py` | WARNING log contains tool_name, original_size, truncated_size |
| FR-6: No-op for under-budget | T-006 | `tests/unit/ai/test_tool_output_truncation.py` | Output < 20000 chars returned unchanged |
| NFR-1: Performance < 1ms | T-007 | `tests/unit/ai/test_tool_output_truncation.py` | Truncation of 100K string completes in < 1ms |
| FR-4: Marker format correctness | T-008 | `tests/unit/ai/test_tool_output_truncation.py` | Marker matches exact format with original size and tool name |
| Edge: External tools (not in _tools_by_name) | T-009 | `tests/unit/ai/test_tool_output_truncation.py` | External tool output passes through unchanged (no metadata) |

---

## Test Specification

### Test Hierarchy

```
tests/unit/ai/
  test_tool_output_truncation.py
    ├── Default truncation behavior (T-001, T-002, T-006)
    ├── Per-tool override behavior (T-003, T-004)
    ├── Logging verification (T-005)
    ├── Marker format verification (T-008)
    ├── External tool passthrough (T-009)
    └── Performance benchmark (T-007)
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_truncate_output_over_default_budget` | FR-1 | Unit | 25K char output truncated to 20K + marker; marker contains original size "25000" |
| T-002 | `test_truncate_output_at_exact_budget_not_truncated` | FR-1 | Unit | 20K char output returned unchanged (no marker appended) |
| T-003 | `test_truncate_output_with_custom_budget` | FR-2 | Unit | Tool with `max_output_chars=5000` truncates 10K output to 5000 + marker |
| T-004 | `test_truncate_output_opt_out_none` | FR-3 | Unit | Tool with `max_output_chars=None` returns 50K output unchanged |
| T-005 | `test_truncate_output_logs_warning` | FR-5 | Unit | CapLog at WARNING contains "truncated" with tool_name, original_size, truncated_size |
| T-006 | `test_truncate_output_under_budget_unchanged` | FR-6 | Unit | 5K char output returned identically (assert content == original) |
| T-007 | `test_truncate_output_performance` | NFR-1 | Unit | Truncation of 100K string < 1ms (measured with time.perf_counter) |
| T-008 | `test_truncate_output_marker_format` | FR-4 | Unit | Marker matches regex `\[Output truncated at \d+ chars\. Original size: \d+ chars\. Tool: \w+\]` |
| T-009 | `test_truncate_output_external_tool_passthrough` | FR-6 | Unit | Tool not in `_tools_by_name` returns full output unchanged |

### Test Infrastructure Needs

- **Fixtures needed**: Mock `BackcastSecurityMiddleware` instance with fabricated `_tools_by_name` dict; mock `ToolCallRequest` and handler returning `ToolMessage` with controlled content length
- **Mocks/stubs**: No external services needed; pure string manipulation testing
- **Database state**: None required (unit tests only, no database interaction)

---

## Implementation Details

### File 1: `backend/app/ai/tools/types.py`

**Lines affected:** 243-272 (ToolMetadata dataclass)

**Change: Add `max_output_chars` field to ToolMetadata**

At line 261 (after `risk_level` field), add:

```
max_output_chars: int | None = None
```

This means: `None` = opt out of truncation (no limit). An `int` value = character budget for that tool.

**Change: Update `to_dict()` method (lines 263-272)**

Add `"max_output_chars": self.max_output_chars,` to the returned dictionary.

### File 2: `backend/app/ai/tools/decorator.py`

**Lines affected:** 30-113 (ai_tool function and inner decorator)

**Change: Add `max_output_chars` parameter to `ai_tool()` signature (line 30)**

Add `max_output_chars: int | None = None,` after `risk_level` parameter in the decorator function signature (line 36).

**Change: Update docstring (lines 37-95)**

Add documentation for the new parameter:
```
max_output_chars: Maximum characters for tool output before truncation.
    None means no truncation (opt-out). Defaults to None.
```

**Change: Forward to ToolMetadata construction (lines 106-113)**

Add `max_output_chars=max_output_chars,` to the `ToolMetadata(...)` constructor call.

### File 3: `backend/app/ai/middleware/backcast_security.py`

**Lines affected:** 1-28 (imports), 176-195 (awrap_tool_call handler section)

**Change: Add module-level constant (after line 28)**

```python
# Default maximum output characters for tool results (~5K tokens).
# Tools can override via max_output_chars in @ai_tool decorator.
DEFAULT_MAX_OUTPUT_CHARS: int = 20_000
```

**Change: Add `_truncate_output()` private method to `BackcastSecurityMiddleware` class**

Add after the `_check_risk_level` method (after line 364). The method signature:

```python
def _truncate_output(self, content: str, tool_name: str) -> str:
```

Logic:
1. Look up tool in `self._tools_by_name` by `tool_name`
2. If tool not found (external tool), return content unchanged
3. Get `_tool_metadata` from tool; if no metadata, return content unchanged
4. Get `max_output_chars` from metadata
5. If `max_output_chars is None`, return content unchanged (opt-out)
6. Use `DEFAULT_MAX_OUTPUT_CHARS` as budget if `max_output_chars` is not set
7. If `len(content) <= budget`, return content unchanged
8. Truncate: `content[:budget]` + marker suffix
9. Log WARNING with tool_name, original_size, truncated_size
10. Return truncated content

**Marker format:**

```
\n\n[Output truncated at {budget} chars. Original size: {original_len} chars. Tool: {tool_name}]
```

**Change: Integrate into `awrap_tool_call()` at lines 177-185**

After `final_result = await handler(request)` (line 178), before the return statement, add truncation call:

```python
# Truncate tool output if it exceeds budget
truncated_content = self._truncate_output(
    content=final_result.content,
    tool_name=tool_name,
)
if truncated_content != final_result.content:
    final_result = ToolMessage(
        content=truncated_content,
        tool_call_id=final_result.tool_call_id,
    )
```

### File 4: `backend/tests/unit/ai/test_tool_output_truncation.py` (NEW)

New test file containing all 9 test cases specified above.

### File 5: `backend/app/ai/tools/project_tools.py` (and other tool files as needed)

**Annotation of high-output tools with appropriate limits.**

Tools to annotate (initial pass based on likely output size):

| Tool | Current File | `max_output_chars` | Rationale |
|---|---|---|---|
| `list_projects` | `project_tools.py` | `50_000` | Returns paginated lists; user controls limit |
| Analysis tools | `templates/analysis_template.py` | `30_000` | Analysis results can be verbose but need detail |
| CRUD list tools | `templates/crud_template.py` | `50_000` | Generic list endpoints with pagination |

Note: The exact tools to annotate will be determined during Task 5 after auditing actual tool output sizes. The default 20K budget applies to unannotated tools automatically.

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Truncation cuts critical data that the LLM needs | Medium | High | Per-tool override via `max_output_chars`; tools needing full output opt out with `None`; marker tells LLM output was truncated so it can ask for specifics |
| Technical | Budget of 20K is too aggressive for some tools | Low | Medium | Default is conservative (~5K tokens, ~10% of typical 50K context window); per-tool override allows tuning |
| Integration | External tools (not in `_tools_by_name`) get truncated | Low | Medium | Code explicitly checks `_tools_by_name` first; external tools pass through unchanged (T-009) |
| Technical | Non-string ToolMessage.content causes error | Low | Low | LangGraph guarantees `ToolMessage.content` is always a string; defensive `isinstance` check in `_truncate_output` |
| Integration | `to_dict()` serialization of new field breaks consumers | Low | Low | Field defaults to `None`; existing consumers already handle optional fields |

---

## Prerequisites

### Technical

- [x] No database migrations required
- [x] No new dependencies required
- [x] Virtual environment and existing dev setup sufficient

### Documentation

- [x] Analysis phase approved (Option 1 selected, default budget confirmed at 20K chars)
- [x] Architecture context: middleware chain ordering understood
- [x] Codebase patterns: `@ai_tool` decorator, `ToolMetadata`, `_tool_metadata` attribute understood

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Extend ToolMetadata with max_output_chars field"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Extend @ai_tool decorator with max_output_chars parameter"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Add _truncate_output() method to BackcastSecurityMiddleware"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-004
    name: "Write unit tests for tool output truncation"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002, BE-003]

  - id: BE-005
    name: "Annotate high-output tools with max_output_chars overrides"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-006
    name: "Run quality gates and fix any issues"
    agent: pdca-backend-do-executor
    dependencies: [BE-004, BE-005]
```

---

## Documentation References

### Code References

- BackcastSecurityMiddleware: `backend/app/ai/middleware/backcast_security.py`
- ToolMetadata dataclass: `backend/app/ai/tools/types.py` (line 243)
- @ai_tool decorator: `backend/app/ai/tools/decorator.py` (line 30)
- ToolMessage usage in middleware: `backend/app/ai/middleware/backcast_security.py` (line 178)
- Middleware stack definition: `backend/app/ai/deep_agent_orchestrator.py` (line 139)
- Existing truncation pattern: `backend/app/ai/tools/subagent_task.py` (line 313)
- Large string detection precedent: `backend/app/ai/agent_service.py` (line 1409)
- Example tool with @ai_tool: `backend/app/ai/tools/project_tools.py` (line 24)

### Test References

- Existing unit test pattern: `backend/tests/unit/ai/test_execution_mode_validation.py`
- Integration test with middleware: `backend/tests/integration/ai/test_approval_workflow.py`
