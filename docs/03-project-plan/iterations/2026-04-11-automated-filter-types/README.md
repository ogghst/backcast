# Iteration: Automated Filter Types via OpenAPI (TD-014)

**Status:** Analysis Complete - Awaiting Decision
**Created:** 2026-04-11
**Priority:** Medium (Technical Debt / Developer Efficiency)

---

## Quick Summary

**Problem:** Frontend filter types are manually synchronized with backend whitelists, creating drift risk and maintenance burden.

**Proposed Solution:** Expose filterable fields in OpenAPI schema and auto-generate TypeScript types.

**Recommendation:** Option 1 (OpenAPI Extension + Post-Processing) - Best balance of flexibility, maintainability, and implementation complexity.

**Estimated Effort:** 3 days

---

## Analysis Document

The full analysis is available in [`00-analysis.md`](./00-analysis.md).

**Key Findings:**

1. **Current State**: 6 services have hardcoded `allowed_fields` lists; frontend has 6 manual filter types
2. **Technical Feasibility**: FastAPI supports `openapi_extra` for custom extensions; post-processing script can generate types
3. **Risk**: Low - isolated changes, backward compatibility possible
4. **Benefit**: High - eliminates manual sync, improves type safety, reduces bugs

---

## Decision Required

Please review the analysis and decide:

1. **Approve Option 1** (OpenAPI Extension + Post-Processing) - Proceed with implementation
2. **Approve Option 2** (Model-Based Schema Annotation) - Alternative approach
3. **Defer** (Option 3) - Maintain manual sync with better documentation
4. **Request Changes** - Ask for modifications to the proposal

---

## Next Steps (If Approved)

1. **PLAN Phase**: Create detailed task breakdown with success criteria
2. **DO Phase**: Implement backend changes, generator script, and frontend migration
3. **CHECK Phase**: Verify generated types work correctly and all tests pass
4. **ACT Phase**: Update documentation and clean up manual types

---

## Related Documentation

- [Migration Plan](../../02-architecture/cross-cutting/automated-filter-types-migration.md)
- [ADR-008: Server-Side Filtering](../../02-architecture/decisions/ADR-008-server-side-filtering.md)
- [Full Analysis](./00-analysis.md)
