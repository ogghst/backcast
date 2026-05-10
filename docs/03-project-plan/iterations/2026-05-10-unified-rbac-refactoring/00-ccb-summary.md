# CCB Summary: Unified RBAC Refactoring

**Date**: 2026-05-10
**Author**: System Architecture Team
**Status**: Request for Approval

---

## Executive Summary

**Request**: Approval to unify three separate authorization systems into one coherent RBAC (Role-Based Access Control) system.

**Investment**: $51,680 / 8.2 weeks
**Risk Level**: Medium (with mitigations)
**Impact**: High (improves security, maintainability, and change order workflow)

**Recommendation**: **Approve with Conditions** - See Section 6

---

## 1. Goal

### Business Problem

Backcast currently manages authorization across three separate systems, creating:
1. **Operational complexity** - Multiple ways to assign permissions
2. **Security risk** - Inconsistent permission checks
3. **Maintenance burden** - Three systems to maintain instead of one
4. **Change order friction** - Approval authority management is separate from role management

### Business Objectives

- **Simplify administration**: Single interface for all role assignments
- **Improve security**: Consistent permission checking across all contexts
- **Enable flexibility**: Support per-project approver assignments (e.g., Dept Head for Project A, Director for Project B)
- **Reduce technical debt**: Unified system is easier to maintain and extend

### Success Criteria

| Metric | Target |
|--------|--------|
| Authorization systems | 3 → 1 |
| Permission check latency | <5ms (cached) |
| Data migration integrity | 100% |
| Security vulnerabilities | 0 critical/high |
| User disruption | <1 day downtime |

---

## 2. As-Is (Current State)

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              CURRENT AUTHORIZATION LANDSCAPE                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ System RBAC  │  │Project Roles │  │Change Order  │      │
│  │              │  │              │  │Approval      │      │
│  │ • admin      │  │ • project_   │  │Authority     │      │
│  │ • manager    │  │   admin      │  │Matrix        │      │
│  │ • viewer     │  │ • project_   │  │              │      │
│  │              │  │   manager    │  │ • dept_head  │      │
│  │ User.role    │  │ • project_   │  │ • director   │      │
│  │ (global)     │  │   editor     │  │              │      │
│  │              │  │ • project_   │  │ Impact level │      │
│  │ JsonRBAC     │  │   viewer     │  │ mapping      │      │
│  │ Service      │  │              │  │              │      │
│  └──────────────┘  │ProjectMember │  │Approval      │      │
│                    │ table        │  │Matrix        │      │
│                    └──────────────┘  │Service       │      │
│                                       └──────────────┘      │
│                                                              │
│  Problems:                                                  │
│  • Checker conflicts (RoleChecker vs ProjectRoleChecker)  │
│  • No per-project approvers (only system-level)           │
│  • Three systems to maintain                                │
└─────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Pain Point | Impact | Frequency |
|------------|--------|-----------|
| Checker conflicts | Routes can't use both checkers | Every new route |
| No scoped approvers | All projects use same approvers | Per project |
| Inconsistent permissions | Security risk | Ongoing |
| Maintenance overhead | 3x systems to patch | Every update |

---

## 3. Proposal

### Solution: Unified RBAC System

**Concept**: Single role assignment model that supports scopes (global, project, change_order)

### Key Design

```
┌─────────────────────────────────────────────────────────────┐
│                 PROPOSED UNIFIED RBAC SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         UserRoleAssignment (New Entity)             │     │
│  ├────────────────────────────────────────────────────┤     │
│  │ user_id:   Which user                              │     │
│  │ role_id:   Which role (RBACRole FK)                │     │
│  │ scope:     global | project | change_order         │     │
│  │ scope_id:  NULL | project_id | change_order_id     │     │
│  │ metadata:  {authority_level: "HIGH"}               │     │
│  │ granted_by: Who assigned this role                 │     │
│  └────────────────────────────────────────────────────┘     │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │         UnifiedRBACService (New Service)            │     │
│  ├────────────────────────────────────────────────────┤     │
│  │ assign_role()    - Grant role to user              │     │
│  │ revoke_role()    - Remove role from user            │     │
│  │ has_permission() - Check if user can do X          │     │
│  │ get_user_roles() - List user's roles               │     │
│  └────────────────────────────────────────────────────┘     │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │         UnifiedChecker (New FastAPI Dependency)    │     │
│  ├────────────────────────────────────────────────────┤     │
│  │ All routes use: UnifiedChecker(permission, scope)  │     │
│  │ Replaces: RoleChecker + ProjectRoleChecker         │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Example Use Cases

**Use Case 1: User with Different Roles**
```
User: Jane Smith
├── Global role: viewer (read-only system access)
├── Project A role: project_manager (full project control)
├── Project B role: project_viewer (read-only on Project B)
└── Project A approver: change_order_approver (MEDIUM authority)
```

**Use Case 2: Per-Project Approvers**
```
Project X: $50K change order
├── Approver: John Doe (dept_head, HIGH authority)
└── John can approve because HIGH ≥ MEDIUM impact

Project Y: $200K change order
├── Approver: Jane Smith (executive, CRITICAL authority)
└── Jane can approve because CRITICAL ≥ HIGH impact
```

---

## 4. To-Be (Future State)

### Future Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              FUTURE AUTHORIZATION LANDSCAPE                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ┌──────────────────┐                     │
│                    │  Unified RBAC    │                     │
│                    │     System       │                     │
│                    ├──────────────────┤                     │
│                    │ • Single entity  │                     │
│                    │ • Single service │                     │
│                    │ • Single checker │                     │
│                    │ • Scoped roles   │                     │
│                    └──────────────────┘                     │
│                           ↓                                  │
│              ┌─────────────────────────────┐                │
│              │    All Contexts Served      │                │
│              ├─────────────────────────────┤                │
│              │ • System RBAC (global)      │                │
│              │ • Project RBAC (per-project)│                │
│              │ • Change Order (per-project)│                │
│              └─────────────────────────────┘                │
│                                                              │
│  Benefits:                                                  │
│  • Single admin interface                                   │
│  • Consistent permission checking                            │
│  • Flexible per-project roles                               │
│  • Easier to maintain                                        │
└─────────────────────────────────────────────────────────────┘
```

### Future State Benefits

| Benefit | Metric | Value |
|---------|--------|-------|
| **Simplified admin** | Systems to maintain | 3 → 1 |
| **Security** | Consistent checks | 100% |
| **Flexibility** | Per-project approvers | Enabled |
| **Performance** | Check latency | <5ms |
| **Audit** | Complete trail | 100% |

### User Experience Improvements

**Before**:
```
Admin: "I need to assign Jane as project manager on Project X"
System: "Go to /projects/X/members and add her"
Admin: "Now I need her to approve change orders"
System: "Go to different screen, configure approval matrix"
Admin: "Why are these separate?"
```

**After**:
```
Admin: "I need to assign Jane roles on Project X"
System: "Here's the role assignment screen for Project X"
Admin: *Selects: project_manager, change_order_approver (MEDIUM)*
System: "Done. Jane can now manage projects and approve MEDIUM impact change orders"
```

---

## 5. Gaps & Risks

### Current Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| No audit trail for role changes | Compliance risk | Add UserRoleAssignmentAudit table |
| Scoped permissions not in ADR-007 | Architecture debt | Create ADR-007 extension |
| Auth context boundaries unclear | Maintenance risk | Document as Shared Kernel |

### Risk Summary

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration data loss | Low | Critical | Backup, dry-run, rollback plan |
| Performance degradation | Medium | Medium | Aggressive caching, benchmarks |
| Timeline overrun | Medium | Medium | 20% buffer in schedule |
| Security vulnerability | Low | Critical | Security review before deploy |

**Total Risk Exposure**: $178,750 (quantified with PMI methodology)

---

## 6. Options

### Option 1: Full Unification (RECOMMENDED)

**Approach**: Replace all three systems with unified RBAC in single deployment

| Aspect | Details |
|--------|---------|
| **Timeline** | 8.2 weeks |
| **Cost** | $51,680 |
| **Risk** | Medium (with mitigations) |
| **Disruption** | ~1 day downtime |

**Pros**:
- ✅ Solves all problems completely
- ✅ Cleanest architecture
- ✅ Easier long-term maintenance

**Cons**:
- ⚠️ Higher upfront risk
- ⚠️ Single cutover point

**Best For**: Long-term architectural health

---

### Option 2: Incremental Rollout

**Approach**: Phase migration over 12 weeks with feature flags

| Aspect | Details |
|--------|---------|
| **Timeline** | 12 weeks |
| **Cost** | ~$60,000 |
| **Risk** | Low |
| **Disruption** | Minimal |

**Pros**:
- ✅ Lower risk
- ✅ Can test in production
- ✅ Easier rollback

**Cons**:
- ❌ Longer timeline
- ❌ Parallel systems temporarily
- ❌ More complex coordination

**Best For**: Production stability priority

---

### Option 3: Minimal Fix

**Approach**: Fix only checker conflicts, keep existing systems

| Aspect | Details |
|--------|---------|
| **Timeline** | 2 weeks |
| **Cost** | ~$15,000 |
| **Risk** | Low |
| **Disruption** | None |

**Pros**:
- ✅ Fast
- ✅ Low risk
- ✅ Cheap

**Cons**:
- ❌ Doesn't solve scoped roles
- ❌ Technical debt remains
- ❌ Doesn't help change orders

**Best For**: Quick win, low resources

---

## 7. Recommendation

### Primary Recommendation: **Option 1 with Conditions**

**Approve** Option 1 (Full Unification) **subject to**:

1. **Security Review**: CISO approval before deployment
2. **Compliance Review**: Legal/compliance audit of audit trail
3. **Stakeholder Sign-off**: Change approvers validate workflow preservation
4. **Enhanced Audit Trail**: Add UserRoleAssignmentAudit table
5. **ADR Extension**: Document scoped permission pattern

### Investment Summary

| Item | Cost |
|------|------|
| Architecture & Design | $6,000 |
| Development | $18,000 |
| Testing & QA | $12,000 |
| Migration & DevOps | $4,800 |
| Documentation & Training | $5,400 |
| Security & Compliance Review | $4,000 |
| Contingency (20%) | $8,280 |
| **Total** | **$51,680** |

### Timeline

| Phase | Duration |
|-------|----------|
| Pre-implementation (CCB, reviews) | 2 weeks |
| Architecture & Design | 2 weeks |
| Development | 3 weeks |
| Testing & Migration | 2 weeks |
| Deployment & Documentation | 1 week |
| **Total** | **8.2 weeks** (with buffer) |

---

## 8. Decision Checklist

**For CCB Approval**:

- [ ] Business case validated (cost/benefit acceptable)
- [ ] Risk level acceptable (with mitigations)
- [ ] Timeline acceptable (8.2 weeks)
- [ ] Budget approved ($51,680)
- [ ] Security review scheduled
- [ ] Stakeholder engagement planned
- [ ] Rollback plan defined

**Next Steps After Approval**:

1. Week 1: Security & compliance review, stakeholder engagement
2. Week 2: Architecture finalization, ADR extension
3. Week 3-5: Development
4. Week 6-7: Testing, migration
5. Week 8: Deployment, documentation

---

## Appendix: Comparison Summary

| Criteria | Option 1 (Full) | Option 2 (Incremental) | Option 3 (Minimal) |
|----------|----------------|------------------------|-------------------|
| Timeline | 8.2 weeks | 12 weeks | 2 weeks |
| Cost | $51,680 | ~$60,000 | ~$15,000 |
| Risk | Medium | Low | Low |
| Solves All Problems | Yes | Yes (eventually) | No |
| Architectural Quality | Excellent | Good | Fair |
| Recommended | ✅ Yes | ⚠️ Alternative | ❌ No |

---

**Document Version**: 1.0
**Last Updated**: 2026-05-10
**Next Review**: After CCB Decision
