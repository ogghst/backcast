# Current Sprint

**Iteration:** LangGraph Agent Enhancement (E09-LANGGRAPH)
**Start Date:** 2026-03-09
**End Date:** TBD
**Status:** 🔄 **In Progress**

---

## Goal

Refactor the AI agent to use LangGraph's StateGraph pattern and establish a standardized framework for implementing tools and capabilities. This addresses the critical architecture gap identified in the gap analysis.

---

## Active Iteration

### 🎯 [E09-LANGGRAPH] LangGraph Agent Enhancement - 13 points
**Status:** 🔄 Analysis Phase
**Links:** [Iteration Plan](./iterations/2026-03-09-langgraph-agent-enhancement/iteration-plan.md)

**Scope:**
- Refactor agent to use proper StateGraph instead of custom loop
- Create standardized tool pattern and registration system
- Establish tool discovery and metadata framework
- Migrate existing tools to new pattern
- Enable scalable tool development for CRUD, Change Order, and Analysis tools

---

## Queued Stories

| Story                                              | Points | Priority | Status        | Dependencies |
| :------------------------------------------------- | :----- | :------- | :----------- | :----------- |
| **[E09-U08] AI-Assisted CRUD Tools**               | 8      | High     | ⏳ Not Started | E09-LANGGRAPH |
| **[E09-U09] Change Order AI**                      | 5      | High     | ⏳ Not Started | E08-LANGGRAPH |
| **[E09-U07] Project Assessment & Analysis**        | 5      | Medium   | ⏳ Not Started | E09-LANGGRAPH |
| **[E09-SESSION] Session Context Enhancement**      | 3      | Medium   | ⏳ Not Started | None |
| **[E09-MULTIMODAL] Multimodal Input/Output**       | 5      | Medium   | ⏳ Not Started | None |

**Total Points:** 39 (0 completed this sprint)

**Recently Completed:** E09-ANALYSIS (2), BUG-001 (3), E09-U10 (5), E09-U11 (5) = 20 points

---

## Success Criteria

- [x] Complete gap analysis between current implementation and requirements
- [x] WebSocket endpoint implemented for real-time streaming
- [x] WebSocket connection remains open until complete message is sent
- [ ] Full CRUD tools implemented for all bounded contexts
- [ ] Change order draft generation via AI
- [ ] Project assessment tools implemented
- [ ] Session context includes project/branch association
- [ ] Multimodal input/output support (images, files, diagrams)

---

## Gap Analysis Summary

### Implementation Status vs. Requirements

| Feature Category | Status | Details |
|-----------------|--------|---------|
| **✅ Fully Implemented** | | |
| WebSocket Streaming | Complete | WebSocket streaming implemented (E09-U10) |
| AI Provider Configuration | Complete | Multi-provider support (OpenAI, Azure, Ollama) via database |
| Assistant Management | Complete | CRUD with tool permissions |
| Text Input/Output | Complete | Standard messaging |
| RBAC Enforcement | Complete | Tool permission checking |
| **⚠️ Partially Implemented** | | |
| LangGraph Agent | Gap | Custom implementation, not using `StateGraph` |
| Session Context | Gap | No project/branch association in model |
| Tool Layer | Gap | Only 2 read-only project tools (need 15+) |
| Markdown Output | Gap | Text storage only, no rendering pipeline |
| **❌ Not Implemented** | Priority | |
| Multimodal Input | Medium | No image/file attachment support |
| CRUD via AI | High | Read-only tools only (E09-U08) |
| Change Order AI | High | No draft generation (E09-U09) |
| Analysis Tools | Medium | No EVM anomaly detection (E09-U07) |

---

## Implementation Plan

**Phase 3B: Tool Layer Expansion (E09-U08) - 8 points**

1. Implement create/update/delete tools for Projects
2. Implement create/update/delete tools for WBEs
3. Implement create/update/delete tools for Cost Elements
4. Implement Schedule Baseline tools
5. Implement Change Order tools
6. Implement Department/User management tools

**Phase 3C: Change Order AI (E09-U09) - 5 points**

1. Create change order draft generation tool
2. Implement requirement parsing
3. Add impact analysis integration
4. Create confirmation workflow

**Phase 3D: Analysis & Insights (E09-U07) - 5 points**

1. Implement project assessment tools
2. Add EVM anomaly detection
3. Create forecast analysis tools
4. Add optimization suggestion generation

**Phase 3E: Session Context Enhancement - 3 points**

1. Add `project_id` and `branch_id` to `AIConversationSession`
2. Create migration for new fields
3. Update session creation to accept context
4. Add context-aware tool filtering

**Phase 3F: Multimodal Support - 5 points**

1. Add image upload endpoint
2. Implement file attachment handling
3. Add Mermaid diagram generation
4. Create rich Markdown rendering pipeline

---

## Key Files Reference

**Backend:**
- `backend/app/ai/agent_service.py` - Agent orchestration
- `backend/app/ai/tools/__init__.py` - Tool implementations (only 2 tools currently)
- `backend/app/api/routes/ai_chat.py` - Chat API routes (WebSocket + HTTP)

**Frontend:**
- `frontend/src/features/ai/chat/components/ChatInterface.tsx` - Main UI
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` - WebSocket client

---

## Links

- [Sprint Backlog Archive](./sprint-backlog-archive.md) - Historical iteration records
- [Product Backlog](./product-backlog.md) - All pending work
- [Technical Debt Register](./technical-debt-register.md) - Active debt items
- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items
