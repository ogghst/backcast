# Implementation Plan: Multimodal Input/Output

**Created:** 2026-04-11
**Iteration:** E09-MULTIMODAL
**Points:** 5
**Status:** 🔄 In Progress

---

## Scope & Success Criteria

### Goal

Enable the AI chat system to handle multimodal inputs (images, files) and produce rich formatted outputs (rendered Markdown, diagrams). This enhances the user experience beyond plain text input/output.

### Success Criteria

**Functional Criteria:**

- [ ] Users can attach images to chat messages VERIFIED BY: Integration test `tests/integration/ai/test_multimodal.py::test_image_attachment`
- [ ] Users can attach files to chat messages VERIFIED BY: Integration test `tests/integration/ai/test_multimodal.py::test_file_attachment`
- [ ] AI can see/analyze attached images VERIFIED BY: E2E test with vision model
- [ ] AI generates Mermaid diagrams that render in chat VERIFIED BY: Already implemented ✅
- [ ] Markdown from AI renders with rich formatting VERIFIED BY: Visual test `tests/frontend/ai/test_markdown_rendering.py::test_markdown_blocks_render_correctly`
- [ ] File metadata tracked in conversation messages VERIFIED BY: Unit test `tests/unit/ai/test_attachments.py::test_attachment_metadata`

**Technical Criteria:**

- [ ] Backend stores attachments efficiently (<100MB per file) VERIFIED BY: File size validation tests
- [ ] Supported image formats: PNG, JPG, JPEG, GIF, WebP VERIFIED BY: Format validation tests
- [ ] Supported document formats: PDF, CSV (future expansion) VERIFIED BY: Format validation tests
- [ ] Frontend renders Markdown securely (no XSS) VERIFIED BY: Security tests with malicious Markdown
- [ ] Code Quality: MyPy strict mode (zero errors) VERIFIED BY: `mypy app/`
- [ ] Code Quality: Ruff clean (zero errors) VERIFIED BY: `ruff check app/`
- [ ] 80%+ test coverage for new code VERIFIED BY: `pytest --cov`

**Business Criteria:**

- [ ] Users can share screenshots and diagrams for analysis VERIFIED BY: User acceptance testing
- [ ] AI-generated visualizations render correctly VERIFIED BY: Visual regression tests

### Scope Boundaries

**In Scope:**

- Image upload endpoint (multipart/form-data)
- File storage (local filesystem, S3-compatible API for future)
- Attachment metadata model and migration
- Frontend attachment UI (drag-and-drop, file picker)
- Vision model integration (OpenAI GPT-4V, Azure OpenAI, or compatible)
- Rich Markdown rendering with syntax highlighting, tables, lists
- Mermaid diagram rendering (already ✅ implemented)

**Out of Scope:**

- Video file support (future iteration)
- Audio file support (future iteration)
- Real-time drawing/sketching (future iteration)
- File editing/collaboration (future iteration)
- Cloud storage integration (S3, Azure Blob) - local filesystem only for now

---

## Work Decomposition

### Task Breakdown

| #   | Task | Files | Dependencies | Success Criteria | Complexity |
| --- | --- | --- | --- | --- | --- |
| **Phase 1: Backend File Handling (2 points)** |
| 1.1 | Create attachment model and migration | `backend/app/models/domain/ai.py` | None | Migration applies, model has FK to message | Low |
| 1.2 | Create file upload endpoint | `backend/app/api/routes/ai_chat.py` | 1.1 | POST /attachments accepts multipart/form-data | Medium |
| 1.3 | Implement file storage service | `backend/app/ai/storage.py` | None | Files saved to local filesystem with unique names | Medium |
| 1.4 | Add attachment to AI message context | `backend/app/ai/agent_service.py` | 1.1, 1.2 | Agent receives attachment metadata in context | Medium |
| **Phase 2: Vision Model Integration (1 point)** |
| 2.1 | Add vision message type to LLM client | `backend/app/ai/llm_client.py` | None | LLM client accepts image_url content type | Medium |
| 2.2 | Update agent to include images in messages | `backend/app/ai/agent_service.py` | 2.1 | Multi-modal messages sent to LLM | Medium |
| 2.3 | Test vision model integration | `tests/integration/ai/test_vision.py` | 2.2 | Vision model responds to image input | High |
| **Phase 3: Frontend Attachment UI (1 point)** |
| 3.1 | Create attachment button and file picker | `frontend/src/features/ai/chat/components/ChatInput.tsx` | None | Button triggers file selection dialog | Low |
| 3.2 | Implement drag-and-drop for files | `frontend/src/features/ai/chat/components/ChatInput.tsx` | 3.1 | Drop zone shows visual feedback, uploads file | Medium |
| 3.3 | Display attachment previews | `frontend/src/features/ai/chat/components/MessageContent.tsx` | 3.2 | Thumbnails shown for images, icons for files | Low |
| 3.4 | Add remove attachment action | `frontend/src/features/ai/chat/components/ChatInput.tsx` | 3.2 | X button removes attachment before send | Low |
| **Phase 4: Markdown Rendering (1 point)** |
| 4.1 | Add Markdown rendering library | `frontend/package.json` | None | react-markdown, remark-gfm installed | Low |
| 4.2 | Create Markdown component with syntax highlighting | `frontend/src/components/common/Markdown.tsx` | 4.1 | Code blocks have syntax highlighting | Medium |
| 4.3 | Integrate Markdown in chat messages | `frontend/src/features/ai/chat/components/MessageContent.tsx` | 4.2 | AI Markdown renders with formatting | Low |
| 4.4 | Security: sanitize Markdown input | `frontend/src/components/common/Markdown.tsx` | 4.2 | XSS attempts are neutralized | High |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
| --- | --- | --- | --- |
| Users can attach images to chat messages | T-001 | `tests/integration/ai/test_multimodal.py::test_image_attachment` | Upload returns attachment_id, message includes image |
| Users can attach files to chat messages | T-002 | `tests/integration/ai/test_multimodal.py::test_file_attachment` | Upload returns attachment_id, file metadata stored |
| AI can see/analyze attached images | T-003 | `tests/integration/ai/test_vision.py::test_vision_model_receives_image` | LLM receives message with image_url content |
| Markdown renders with rich formatting | T-004 | `tests/frontend/ai/test_markdown_rendering.py` | Headers, lists, code, tables render correctly |
| Mermaid diagrams render | T-005 | `tests/frontend/ai/test_mermaid_rendering.py` | Already implemented ✅ |
| File size validation works | T-006 | `tests/unit/ai/test_attachments.py::test_file_size_limit` | Files >100MB rejected with 413 error |
| XSS prevention | T-007 | `tests/security/ai/test_markdown_xss.py` | Script tags in Markdown are escaped |

---

## Test Specification

### Test Hierarchy

```
├── Unit Tests (tests/unit/ai/)
│   ├── test_attachments.py - Attachment model, validation
│   ├── test_storage.py - File storage service
│   └── test_vision_client.py - Vision message formatting
├── Integration Tests (tests/integration/ai/)
│   ├── test_multimodal.py - End-to-end file upload, attachment
│   ├── test_vision.py - Vision model integration
│   └── test_attachments_api.py - Attachment endpoints
├── Frontend Tests (tests/frontend/ai/)
│   ├── test_attachment_ui.tsx - Attachment button, drag-drop
│   ├── test_markdown_rendering.tsx - Markdown component
│   └── test_message_attachments.tsx - Message display with attachments
└── Security Tests (tests/security/ai/)
    └── test_markdown_xss.py - XSS prevention in Markdown
```

### Test Cases (First 5)

| Test ID | Test Name | Criterion | Type | Expected Result |
| --- | --- | --- | --- | --- |
| T-001 | test_image_upload_saves_file_and_returns_attachment_id | FR-1 | Integration | POST /attachments returns {id, filename, content_type, size} |
| T-002 | test_attachment_model_has_message_foreign_key | FR-1 | Unit | AIConversationAttachment.message_id references ai_conversation_messages.id |
| T-003 | test_vision_message_includes_image_url | FR-3 | Unit | LLM client formats message with {type: "image_url", image_url: {url: "..."}} |
| T-004 | test_drag_and_drop_shows_preview | FR-5 | Frontend | Dropping image shows thumbnail before upload |
| T-005 | test_markdown_renders_code_with_syntax_highlighting | FR-6 | Frontend | ```python blocks render with highlighted syntax |

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| Technical | Vision model availability/cost | Medium | Medium | Support multiple providers (OpenAI, Azure, Ollama); graceful fallback to text-only |
| Technical | File storage fills disk | Low | High | Add disk space monitoring; implement file cleanup; add max file size limits |
| Security | Malicious file upload (malware) | Low | High | Validate file types; scan uploads (future); serve with Content-Disposition |
| Security | XSS via Markdown | Medium | High | Use react-markdown with sanitization; test with XSS payloads |
| Performance | Large uploads slow chat | Low | Medium | Add upload progress indicator; limit file size to 100MB |
| UX | Vision model quality varies | Medium | Medium | Add disclaimer about AI vision accuracy; allow user to describe image |

---

## Documentation References

### Required Reading

- [AI Chat Architecture](/home/nicola/dev/backcast/docs/02-architecture/ai/README.md)
- [Backend Coding Standards](/home/nicola/dev/backcast/docs/02-architecture/backend/coding-standards.md)
- [API Conventions](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/api-conventions.md)
- [Security Practices](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/security-practices.md)

### Code References

**Backend:**
- [AI Chat Routes](/home/nicola/dev/backcast/backend/app/api/routes/ai_chat.py) - WebSocket and REST endpoints
- [Agent Service](/home/nicola/dev/backcast/backend/app/ai/agent_service.py) - Agent orchestration
- [LLM Client](/home/nicola/dev/backcast/backend/app/ai/llm_client.py) - LLM abstraction
- [AI Schemas](/home/nicola/dev/backcast/backend/app/models/schemas/ai.py) - Pydantic schemas

**Frontend:**
- [Chat Interface](/home/nicola/dev/backcast/frontend/src/features/ai/chat/components/ChatInterface.tsx) - Main chat UI
- [Message Content](/home/nicola/dev/backcast/frontend/src/features/ai/chat/components/MessageContent.tsx) - Message display
- [Streaming Hook](/home/nicola/dev/backcast/frontend/src/features/ai/chat/api/useStreamingChat.ts) - WebSocket client

**External References:**
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [react-markdown Docs](https://github.com/remarkjs/react-markdown)
- [Mermaid JS](https://mermaid.js.org/)

---

## File Creation/Modification List

### Files to Create

**Backend:**
- `backend/app/ai/storage.py` - File storage service (local filesystem)
- `backend/app/models/schemas/attachment.py` - Attachment request/response schemas
- `tests/unit/ai/test_storage.py` - Storage service tests
- `tests/integration/ai/test_multimodal.py` - Multimodal integration tests
- `tests/integration/ai/test_vision.py` - Vision model tests

**Frontend:**
- `frontend/src/components/common/Markdown.tsx` - Markdown rendering component
- `frontend/src/features/ai/chat/components/FilePreview.tsx` - Attachment preview component
- `tests/frontend/ai/test_markdown_rendering.test.tsx` - Markdown rendering tests

### Files to Modify

**Backend:**
- `backend/app/models/domain/ai.py` - Add `AIConversationAttachment` model
- `backend/app/api/routes/ai_chat.py` - Add POST /attachments endpoint
- `backend/app/ai/llm_client.py` - Add vision message type support
- `backend/app/ai/agent_service.py` - Include attachments in message context
- `backend/alembic/versions/XXXX_multimodal_attachments.py` - Create migration

**Frontend:**
- `frontend/package.json` - Add react-markdown, remark-gfm, rehype-highlight deps
- `frontend/src/features/ai/chat/components/ChatInput.tsx` - Add attachment button, drag-drop
- `frontend/src/features/ai/chat/components/MessageContent.tsx` - Render Markdown, show attachments
- `frontend/src/features/ai/chat/api/useStreamingChat.ts` - Handle attachment uploads

---

## Definition of Done

### Overall Iteration Completion

**Code Implementation:**
- [ ] Attachment model created with migration applied
- [ ] File upload endpoint handles multipart/form-data
- [ ] File storage service saves files to local filesystem
- [ ] Vision model integration working (at least one provider)
- [ ] Frontend attachment UI (button + drag-drop)
- [ ] Attachment previews in chat messages
- [ ] Markdown rendering with syntax highlighting
- [ ] XSS prevention in Markdown rendering

**Testing:**
- [ ] Unit tests for storage service pass
- [ ] Integration tests for file upload pass
- [ ] Vision model integration tests pass
- [ ] Frontend attachment UI tests pass
- [ ] Markdown rendering tests pass
- [ ] Security/XSS tests pass
- [ ] 80%+ test coverage for new code

**Code Quality:**
- [ ] Zero MyPy errors
- [ ] Zero Ruff errors
- [ ] Zero ESLint errors (frontend)
- [ ] TypeScript strict mode passes

**Documentation:**
- [ ] API documentation updated for /attachments endpoint
- [ ] Frontend attachment usage documented
- [ ] Known limitations documented (file size, supported formats)

---

## Next Steps: DO Phase

**DO Phase Instructions:**
1. Create feature branch: `feature/multimodal-io`
2. Follow TDD: Write tests first, implement to make them pass
3. Implement tasks in order (backend first, then frontend)
4. Run quality gates after each phase

**CHECK Phase Instructions:**
- Verify all success criteria met
- Run full test suite (backend + frontend)
- Manual testing: Attach an image, ask AI to describe it
- Visual testing: Verify Markdown renders correctly

---

**PLAN Phase Complete** ✓
