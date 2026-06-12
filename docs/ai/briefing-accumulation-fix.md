# Briefing Accumulation Fix & Session Restore

**Date:** 2026-06-12
**Branch:** `llm_per_specialist`

## Problem

When a user asked a follow-up question in the same AI chat session, the `BriefingDocument.original_request` was **overwritten** with the new question instead of being preserved. The entire briefing knowledge was effectively reset on every follow-up, losing context of what specialists had already researched.

Additionally, when reopening a chat session, the briefing panel showed follow-up question titles but **not the specialist findings content** (sections, analysis, key findings).

### Root Cause 1 — Briefing Overwrite

In `backend/app/ai/supervisor_orchestrator.py` (~line 413):

```python
# BEFORE: overwrites original request on every turn
doc.original_request = user_request
```

The `BriefingDocument` model had no mechanism to track follow-up questions separately from the original request.

### Root Cause 2 — Session Restore Gap

The REST session API (`AIConversationSessionPublic`) only returned `briefing_markdown` (flat text) and `briefing_specialists` (names array). The structured `briefing_data` (with sections, findings, key findings) was not included in the response, so the frontend fell back to `document: null` on session restore, losing all specialist content.

## Solution

### Briefing Accumulation

Added `follow_up_requests: list[str]` field to `BriefingDocument`:

```python
class BriefingDocument(BaseModel):
    original_request: str
    follow_up_requests: list[str] = []  # NEW
    sections: list[BriefingSection] = []
```

Changed the overwrite to append:

```python
# AFTER: preserves original, appends follow-up
doc.follow_up_requests.append(user_request)
```

Specialist assignment context now includes the full conversation history:

```python
_request_context = [f"Original request: {original_request}"]
for i, fq in enumerate(doc.follow_up_requests, 1):
    _request_context.append(f"Follow-up {i}: {fq}")
```

### Session Restore

Added `briefing_data` to `AIConversationSessionPublic` schema and enriched it in the session API response:

```python
# backend/app/api/routes/ai_chat.py
session_public.briefing_data = session.briefing_data
```

Frontend `ChatInterface.tsx` maps the structured data on restore:

```typescript
document: session.briefing_data ? {
    original_request: session.briefing_data.original_request,
    follow_up_requests: session.briefing_data.follow_up_requests ?? [],
    sections: (session.briefing_data.sections ?? []).map(s => ({
        specialist_name: s.specialist_name,
        summary: s.findings,  // backend uses 'findings', frontend uses 'summary'
        // ...
    })),
} : null,
```

## Files Changed

| File | Change |
|------|--------|
| `backend/app/ai/briefing.py` | Added `follow_up_requests` field + markdown rendering |
| `backend/app/ai/supervisor_orchestrator.py` | Core fix: append instead of overwrite, context building |
| `backend/app/ai/graph_params.py` | Added `follow_up_requests` to WS briefing events |
| `backend/app/ai/tools/briefing_tools.py` | Added `follow_up_requests` to tool output |
| `backend/app/models/schemas/ai.py` | Added `briefing_data` to session schema + `follow_up_requests` to public schema |
| `backend/app/api/routes/ai_chat.py` | Enrich session response with `briefing_data` |
| `frontend/src/features/ai/chat/types.ts` | Added `follow_up_requests` to `BriefingDocumentData` |
| `frontend/src/features/ai/types.ts` | Added `briefing_data` to session type |
| `frontend/src/features/ai/chat/api/useStreamingChat.ts` | Backward-compat shim for `follow_up_requests` |
| `frontend/src/features/ai/chat/components/ChatInterface.tsx` | Session restore mapping from `briefing_data` |

## Verification

E2E tested via Playwright with DB verification at each step:
- `original_request` preserved across 3 messages
- `follow_up_requests` appends (not replaces)
- Briefing panel renders "Follow-up Questions" heading + numbered list
- DB JSONB stores correct data
- No backend errors

Full report: `e2e/20260612_1430-briefing-accumulation/report.md`
