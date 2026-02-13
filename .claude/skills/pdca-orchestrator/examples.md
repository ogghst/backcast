# PDCA Orchestrator - Use Cases & Examples

## Common Use Cases

### Test Coverage Improvement

**User Request**: "I need to improve the test coverage for the EVS versioning system"

**Flow**:
1. Delegate to `pdca-analyzer`: Analyze current coverage, identify gaps
2. Delegate to `pdca-planner`: Create improvement plan with measurable goals
3. Delegate to `pdca-backend-do-executor`: Implement tests following TDD
4. Delegate to `pdca-checker`: Verify coverage improvements
5. Delegate to `pdca-act-executor`: Standardize testing patterns

### Performance Optimization

**User Request**: "The PostgreSQL queries for temporal ranges are slow, can you help optimize them?"

**Flow**:
1. Delegate to `pdca-analyzer`: Baseline current performance, identify bottlenecks
2. Delegate to `pdca-planner`: Plan optimization approach with success metrics
3. Delegate to `pdca-backend-do-executor`: Implement optimizations
4. Delegate to `pdca-checker`: Measure and verify improvements
5. Delegate to `pdca-act-executor`: Document best practices

### Refactoring

**User Request**: "The service layer for cost elements is getting complex, I need to refactor it"

**Flow**:
1. Delegate to `pdca-analyzer`: Analyze current complexity, identify issues
2. Delegate to `pdca-planner`: Plan refactoring with success criteria
3. Delegate to `pdca-backend-do-executor`: Execute refactoring with tests
4. Delegate to `pdca-checker`: Verify functionality and quality metrics
5. Delegate to `pdca-act-executor`: Standardize new architecture patterns

## Decision Matrix

When receiving user requests, use this matrix to determine the approach:

| Instruction Type                  | Action                                              |
| -------------------------------- | --------------------------------------------------- |
| Scope change or new requirement   | Return to pdca-analyzer                             |
| Clarification on existing plan    | Continue with current phase                         |
| Request to skip analysis/planning | Delegate directly to developer agents               |
| Bug fix or quick implementation   | Delegate to backend-developer or frontend-developer |
| Validation request                | Delegate to pdca-checker                            |

## Agent Selection Guide

### For Full PDCA Cycles

| Agent                       | Use When                                                  |
| --------------------------- | --------------------------------------------------------- |
| `pdca-analyzer`            | Any new initiative requiring analysis                          |
| `pdca-planner`             | After analysis approved, planning needed                   |
| `pdca-backend-do-executor`  | Backend TDD implementation with 02-do.md tracking         |
| `pdca-frontend-do-executor` | Frontend TDD implementation with 02-do.md tracking        |
| `pdca-checker`              | After DO phase complete, validation needed                |
| `pdca-act-executor`         | After CHECK phase, improvements approved to implement   |

### For Direct Implementation (Short-Circuit)

| Agent                       | Use When                                                  |
| --------------------------- | --------------------------------------------------------- |
| `backend-developer`         | Backend code, APIs, database, EVCS patterns               |
| `frontend-developer`        | React components, hooks, UI features                      |

## Proactive Triggers

Use the orchestrator when:

- User describes a problem that requires analysis before solution
- Implementing features that need validation and iteration
- Working on performance optimization that requires measurement
- Refactoring code that needs careful testing and validation
- User mentions continuous improvement, optimization, or iteration

## Status Update Examples

### Phase Start
```
📋 Starting Analysis Phase

Delegating to pdca-analyzer to baseline current test coverage and identify gaps in the EVS versioning system.

**Context provided**:
- Current coverage target: 80%
- Focus areas: temporal query logic, branch isolation
- Success criteria: Coverage ≥85%, all critical paths tested

Awaiting analysis...
```

### Phase Completion
```
✅ Analysis phase completed

**Key findings**:
- Current coverage: 72% (8% below target)
- Gap analysis: Missing tests for branch merge scenarios
- Recommended approach: Incremental TDD with parallel backend/frontend work

Proceeding to PLAN phase...
```

### Blocker Notification
```
⚠️ Blocker in Plan Phase

**Issue**: API contract undefined for cost-element pagination
**Impact**: Frontend implementation blocked
**Proposed resolution**: Define contract in backend implementation before frontend starts
**Decision needed**: Should we implement pagination first or defer it?
```

### Cycle Complete
```
✅ PDCA Cycle Complete

**Summary**:
- Coverage improved: 72% → 87% (+15%)
- Tests added: 47 new tests, all passing
- Patterns standardized: Temporal query test template created
- Technical debt: 2 items identified for future iteration

**Artifacts**: docs/03-project-plan/iterations/2026-02-13-test-coverage/
```
