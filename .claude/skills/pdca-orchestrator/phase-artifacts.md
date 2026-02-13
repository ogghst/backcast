# PDCA Phase Artifacts

## Output Location

All PDCA iteration artifacts are stored in:
```
docs/03-project-plan/iterations/YYYY-MM-DD-{title}/
```

## Canonical Filenames

Each phase MUST produce its corresponding file. These are the **completion signals** for phase progression:

| Phase    | Filename          | Purpose                              |
| -------- | ----------------- | ------------------------------------- |
| Analysis | `00-analysis.md`  | Requirements, options, decision       |
| Plan     | `01-plan.md`      | Task breakdown, success criteria       |
| Do       | `02-do.md`        | Implementation log, TDD cycles        |
| Check    | `03-check.md`     | Verification, metrics, root cause     |
| Act      | `04-act.md`       | Improvements, standardization, closure |

## File Content Requirements

### 00-analysis.md

**Must contain**:
- Problem statement and user intent
- Requirements clarification
- 2-3 solution options with trade-offs
- Recommended option with rationale
- Links to relevant documentation reviewed

**Validation**: Non-empty markdown, approved option clearly stated

### 01-plan.md

**Must contain**:
- Approved approach summary from analysis
- Measurable success criteria (functional, technical, TDD)
- Task breakdown with dependencies
- Test specifications (what to test, not how)
- Risk assessment

**Validation**: Non-empty markdown, success criteria are measurable

### 02-do.md

**Must contain**:
- Progress summary with running totals
- TDD cycle log (RED → GREEN → REFACTOR)
- Files changed with descriptions
- Decisions made during implementation
- Next steps or remaining work

**Validation**: Non-empty markdown, TDD cycles logged

### 03-check.md

**Must contain**:
- Acceptance criteria verification matrix
- Test quality and coverage assessment
- Code quality metrics (MyPy, Ruff, ESLint, etc.)
- Root cause analysis for any issues
- Improvement options with recommendations

**Validation**: Non-empty markdown, all success criteria verified

### 04-act.md

**Must contain**:
- Improvements implemented with verification
- Pattern standardization decisions
- Documentation updates completed
- Technical debt ledger changes
- Iteration closure status

**Validation**: Non-empty markdown, closure status clearly stated

## Completion Signals

**DO NOT advance to next phase until**:

1. The file exists at the expected path
2. The file is non-empty (contains actual content)
3. The file is valid markdown (not malformed)

## Shared Context File

Location: `docs/03-project-plan/iterations/{iteration}/_agent-context.md`

**Purpose**: Communication between DO-phase agents working in parallel

**Structure**:
```markdown
# Agent Communication Log

## Backend Agent Updates

- [timestamp] Created `POST /api/cost-elements` endpoint
- [timestamp] API contract: `{ name: string, budget: number }`

## Frontend Agent Updates

- [timestamp] Waiting for API contract for cost elements
- [timestamp] Consumed API contract, implementing form

## Blockers

- [agent] [timestamp] Need clarification on X

## Signals

- [timestamp] SIGNAL: api-contract-ready:cost-element
- [timestamp] SIGNAL: ready-for-integration
```

## Signals Reference

| Signal                        | Emitter | Consumers    | Meaning                       |
| ----------------------------- | ------- | ------------ | ----------------------------- |
| `api-contract-ready:{entity}` | Backend | Frontend     | API schema is finalized       |
| `blocker:{id}`                | Any     | Orchestrator | Work is blocked               |
| `ready-for-integration`       | Both    | Checker      | Ready for integration testing |

## Template References

Phase prompts reference templates in `docs/04-pdca-prompts/_templates/`:

- `00-analysis-template.md` - Analysis phase output
- `01-plan-template.md` - Plan phase output
- `02-do-template.md` - Do phase log
- `03-check-template.md` - Check phase output
- `04-act-template.md` - Act phase output

These templates ensure consistent formatting and required sections across iterations.
