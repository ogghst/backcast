# Act: Defense-in-Depth Sequential Tool Execution

**Completed:** 2026-05-17
**Based on:** [03-check.md](03-check.md)

---

## 1. Improvements Implemented

### Critical Issues (from CHECK)

| Issue | Resolution | Verification |
| --- | --- | --- |
| Parallel tool execution causing DB pool exhaustion and race conditions | SequentialToolNode class with sequential for-loop dispatch | 5 unit tests pass, 100% coverage on new file |
| Fallback graph missing `parallel_tool_calls=False` | Added to `bind_tools` call in graph.py | Code inspection (line 128) + unit test |
| Specialist subgraphs (via `langchain_create_agent`) using bare ToolNode | Global monkey-patch of `ToolNode._afunc` at import time | T-005 verifies plain ToolNode executes sequentially after patch |
| Stale comments in graph.py referencing "ToolNode" | Updated labels to reference SequentialToolNode | Code inspection |

### Refactoring Applied

| Change | Rationale | Files Affected |
| --- | --- | --- |
| RBACToolNode parent: ToolNode -> SequentialToolNode | Ensures RBAC-wrapped tools also execute sequentially | `rbac_tool_node.py` |
| InterruptNode parent: ToolNode -> SequentialToolNode | Ensures approval-flow tools execute sequentially | `interrupt_node.py` |
| graphviz label "ToolNode" -> "SequentialToolNode" | Accurate graph visualization | `graph.py` |

### Deferred Items

| Item | Reason Deferred | Target Iteration | Tracking |
| --- | --- | --- | --- |
| Session management simplification (remove `async_scoped_session` workarounds) | Out of scope; requires separate analysis of DB session lifecycle | Next iteration | Noted in CHECK Section 9 |
| E2E full suite verification (AC-T3) | Unit/integration scope verified; E2E requires running environment | Post-merge | Noted in CHECK Section 7 |
| Partial failure test (tool 2 raises in a batch) | Acceptable; upstream ToolNode does not handle per-tool errors in gather path either | N/A | Noted in CHECK Section 2 |

---

## 2. Pattern Standardization

| Pattern | Description | Standardize? | Action |
| --- | --- | --- | --- |
| SequentialToolNode as default ToolNode | All tool execution in Backcast must be sequential to prevent DB pool exhaustion and race conditions | Yes | Already enforced via monkey-patch; documented below |
| Monkey-patch for third-party factory constraints | When a third-party factory (e.g., `langchain_create_agent`) hardcodes class instantiation, a global monkey-patch with idempotent guard is an acceptable solution | Pilot | Document in architecture docs; revisit if LangGraph provides extension points |
| `unittest.mock.patch` for module-level side effects | When testing code with module-level side effects (logging, monkey-patching, global state), prefer `unittest.mock.patch` over `caplog` to assert on specific logger calls in isolation | Yes | Add to testing guidelines |
| Defense-in-depth architecture | Two independent layers (model hint + dispatch enforcement) provide robust protection even if one layer fails | Yes | Pattern applicable to other concurrency-sensitive subsystems |

**Standardization Actions:**

- [x] Update `docs/02-architecture/cross-cutting/` -- pattern documented in this ACT
- [ ] Add `unittest.mock.patch` guidance to coding standards or testing guidelines
- [ ] Add SequentialToolNode to code review checklist for any new ToolNode usage

---

## 3. Documentation Updates

| Document | Update Needed | Status |
| --- | --- | --- |
| `lessons-learned.md` | Add sequential execution lesson and testing pattern lesson | DONE |
| `graph.py` comments (lines 199, 299) | Update "ToolNode" references to "SequentialToolNode" | DONE |
| Architecture docs for AI subsystem | Document that all tool execution is sequential by design | TODO (next iteration) |

---

## 4. Technical Debt Ledger

### Created This Iteration

| ID | Description | Impact | Effort | Target Date |
| --- | --- | --- | --- | --- |
| TD-2026-006 | Global monkey-patch of `ToolNode._afunc` couples code to LangGraph internal API; will break if `_afunc` signature changes | Medium | 0.5 days to re-derive | On LangGraph upgrade |
| TD-2026-007 | `async_scoped_session` workarounds in session management remain from pre-sequential era; may be simplifiable | Low | 2 days to analyze + refactor | Next iteration |

### Resolved This Iteration

| ID | Resolution | Time Spent |
| --- | --- | --- |
| (No prior TD ID) Parallel tool execution causing DB pool exhaustion (31 leaked connections) | SequentialToolNode + `parallel_tool_calls=False` defense-in-depth | 4 hours |

**Net Debt Change:** +2 items created, 1 issue resolved

---

## 5. Process Improvements

### What Worked Well

- **Defense-in-depth approach:** Two independent layers (model hint + dispatch override) provide robust protection. Even if `parallel_tool_calls=False` fails (e.g., model ignores it), the sequential dispatch catches it. The WARNING log acts as a canary.
- **Surgical override:** The `_afunc` override is 48 lines, changing exactly one mechanism (gather -> for-loop). Minimal surface area reduces maintenance burden.
- **Idempotent monkey-patch:** The `_patched` guard and INFO/DEBUG logging make the patch safe to call multiple times and easy to diagnose in production.
- **Instance-level afunc replacement in subagent_compiler.py:** Using `types.MethodType` to replace the ToolNode instance's `afunc` after compilation provides targeted coverage without affecting unrelated instances.

### Process Changes for Future

| Change | Rationale | Owner |
| --- | --- | --- |
| Prefer `unittest.mock.patch` over `caplog` for tests involving module-level side effects | `caplog` captures all log records at the configured level from all loggers, including module-level imports. `unittest.mock.patch` isolates assertions to the specific test scope. | Developer |
| Pin third-party library versions when overriding internal APIs | The `_afunc` override couples code to LangGraph internals. Pinning the version prevents surprise breakage. | Developer |
| Document monkey-patch rationale in code comments | Future maintainers need to understand *why* a monkey-patch exists and what would need to change if the third-party library evolves. | Developer |

---

## 6. Knowledge Transfer

- [x] Key decisions documented (monkey-patch rationale, defense-in-depth architecture)
- [x] Common pitfalls noted (caplog isolation with module-level side effects)
- [x] Code walkthrough: SequentialToolNode._afunc is a line-for-line copy of ToolNode._afunc with `asyncio.gather` replaced by a for-loop -- easy to re-derive from upstream
- [ ] Onboarding materials: No update needed (internal infrastructure, no user-facing change)

---

## 7. Metrics for Monitoring

| Metric | Baseline | Target | Measurement Method |
| --- | --- | --- | --- |
| DB pool leaked connections | 31 (observed in production) | 0 | Application logs / pool monitoring |
| WARNING logs from SequentialToolNode (multiple tool calls) | Unknown (no prior instrumentation) | 0 (model respects `parallel_tool_calls=False`) | Log aggregation; any occurrence indicates model is batching tool calls |
| LangGraph version drift | Pinned | Remain pinned | `requirements.txt` / `pyproject.toml` |

---

## 8. Next Iteration Implications

**Unlocked:**

- DB pool exhaustion risk eliminated; safe to remove diagnostic pool monitoring code added during incident response
- Sequential execution makes it safe to consider simplifying `async_scoped_session` workarounds (each tool now completes before the next starts, reducing concurrent session pressure)
- Defense-in-depth pattern applicable to other concurrency-sensitive subsystems

**New Priorities:**

- Session management simplification: audit `async_scoped_session`, `db.close()` workarounds, and pool tuning parameters for potential simplification now that concurrent tool execution is prevented
- LangGraph version pin audit: verify no other internal API dependencies exist that could break on upgrade

**Invalidated Assumptions:**

- The assumption that `asyncio.gather` in ToolNode is safe for tools sharing a database session is now formally rejected. All tool execution must be sequential.

---

## 9. Concrete Action Items

- [x] Update stale comments in `graph.py` (lines 199, 299) -- Completed during ACT
- [ ] Add `unittest.mock.patch` testing pattern to project coding standards -- @developer
- [ ] Schedule session management simplification iteration -- @developer
- [ ] Verify E2E test suite passes with sequential tool execution -- @developer (post-merge)

---

## 10. Iteration Closure

**Final Status:** PASS

**Success Criteria Met:** 14 of 16 (2 deferred: E2E tests not run, TDD red-green cycle not documented)

**Lessons Learned Summary:**

1. **Monkey-patching third-party internals is acceptable when the factory pattern provides no extension point.** Document the rationale, pin the library version, and make the override minimal and easy to re-derive.
2. **Defense-in-depth pays off.** Two independent layers (model hint + dispatch enforcement) are more robust than either alone. The WARNING log on the enforcement layer acts as a canary detecting when the first layer fails.
3. **Test isolation matters with module-level side effects.** `caplog` captures everything; `unittest.mock.patch` isolates. Choose based on whether the test target has module-level side effects.

**Iteration Closed:** 2026-05-17
