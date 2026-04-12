# Plan: Store All Attachment Content in DB, Send to LLM

**Created:** 2026-04-12
**Based on:** User-approved approach from Analysis phase
**Approved Option:** All content in DB, no disk storage

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Store all file content (text and binary) directly in PostgreSQL; remove all disk-based file storage.
- **Architecture**: Upload endpoints extract text content from files (or base64-encode images), store it in a new `content` TEXT column on `ai_conversation_attachments`, and return metadata. The agent service reads stored content to build LLM messages with inline text blocks for documents and base64 data URLs for images.
- **Key Decisions**:
  1. 512 KB application-level size limit for content sent to the LLM per attachment
  2. Binary types (PDF, DOCX, XLSX, PPTX) have their extracted text sent to the LLM in full, not as placeholders
  3. No disk storage at all -- `file_path` column removed, `FileStorageService` removed, file-serving endpoints removed
  4. Images stored as base64 TEXT in DB, sent to LLM as `data:image/...;base64,...` data URLs
  5. Text files (TXT, CSV, JSON) stored as-is in the `content` column
  6. New Python dependencies: `pypdf`, `python-docx`, `openpyxl`, `python-pptx`

### Success Criteria

**Functional Criteria:**

- [ ] FC-1: User can upload a text file (TXT, CSV, JSON) and its content is stored in DB and sent to the LLM as a text block VERIFIED BY: integration test
- [ ] FC-2: User can upload a binary document (PDF, DOCX, XLSX, PPTX) and its extracted text content is stored in DB and sent to the LLM as a text block VERIFIED BY: integration test
- [ ] FC-3: User can upload an image (PNG, JPG) and it is stored as base64 in DB and sent to the LLM as an image_url data URL block VERIFIED BY: integration test
- [ ] FC-4: Files exceeding 512 KB content size are rejected at upload with a clear error message VERIFIED BY: unit test
- [ ] FC-5: Mixed attachments (image + document) in a single message are all processed correctly VERIFIED BY: integration test
- [ ] FC-6: Existing chat sessions continue to work; old attachments with null content gracefully degrade VERIFIED BY: integration test
- [ ] FC-7: Frontend displays uploaded images inline using base64 data from the attachment response VERIFIED BY: manual verification

**Technical Criteria:**

- [ ] TC-1: `file_path` column removed from `ai_conversation_attachments` table VERIFIED BY: migration runs cleanly
- [ ] TC-2: `content` TEXT column added to `ai_conversation_attachments` table VERIFIED BY: migration runs cleanly
- [ ] TC-3: `FileStorageService` class removed from `backend/app/ai/storage.py` VERIFIED BY: file deleted, no imports remain
- [ ] TC-4: File serving endpoints (`/images/{file_id}`, `/documents/{file_id}`) removed VERIFIED BY: route file no longer contains these endpoints
- [ ] TC-5: MyPy strict mode passes with zero errors VERIFIED BY: `uv run mypy app/`
- [ ] TC-6: Ruff passes with zero errors VERIFIED BY: `uv run ruff check .`
- [ ] TC-7: All affected tests pass with 80%+ coverage on changed files VERIFIED BY: `uv run pytest`
- [ ] TC-8: Frontend TypeScript compilation passes VERIFIED BY: `npm run build`

**TDD Criteria:**

- [ ] All tests written before implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage >= 80% on changed files
- [ ] Tests follow Arrange-Act-Assert pattern

### Scope Boundaries

**In Scope:**

- Database migration: add `content` column, remove `file_path` column
- Text extraction for PDF, DOCX, XLSX, PPTX, TXT, CSV, JSON
- Image storage as base64 in DB
- Upload endpoint rewrite: extract text/base64, store in DB, return metadata
- Agent service update: read stored content, build LLM content blocks
- Pydantic schema update: `FileAttachment` replaces `url` with `content` where needed
- Service layer update: `add_message()` stores content instead of file_path
- Remove `FileStorageService`, file-serving endpoints, disk directory constants
- Frontend update: `FilePreview` uses base64 data URLs for images, remove file download links
- Frontend update: `FileAttachment` type updated to match new API response
- Frontend update: `attachmentUpload.ts` updated to handle new response format
- Existing test updates to match new schema

**Out of Scope:**

- OCR for scanned PDFs (text extraction only from text-based PDFs)
- Audio/video file support
- File content compression
- Content deduplication
- Streaming text extraction for very large files
- PPTX slide-level content separation (all text concatenated)

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Add new Python dependencies for text extraction | `backend/pyproject.toml` | none | `pypdf`, `python-docx`, `openpyxl`, `python-pptx` installable | Low |
| 2 | Create DB migration: add `content` TEXT, remove `file_path` | `backend/alembic/versions/` | none | Migration upgrades and downgrades cleanly | Low |
| 3 | Update domain model: `AIConversationAttachment` | `backend/app/models/domain/ai.py` | task 2 | Model has `content` field, no `file_path` field, MyPy passes | Low |
| 4 | Create text extraction utility module | `backend/app/ai/file_extractors.py` (new) | task 1 | `extract_text(content_bytes, content_type) -> str` works for all supported types; returns None for unsupported types; handles extraction errors gracefully | Med |
| 5 | Write unit tests for text extraction utility | `backend/tests/unit/ai/test_file_extractors.py` (new) | task 4 | Tests for TXT, CSV, JSON, PDF, DOCX, XLSX, PPTX, unsupported type, empty content, oversized content | Med |
| 6 | Rewrite upload endpoints: store content in DB | `backend/app/api/routes/ai_upload.py` | task 3, 4 | `upload_file()` extracts text, stores in DB, returns metadata without disk write; `upload_image()` base64-encodes, stores in DB, returns metadata | High |
| 7 | Remove file-serving endpoints and disk constants | `backend/app/api/routes/ai_upload.py` | task 6 | `get_image()`, `get_document()` removed; `UPLOAD_BASE_DIR`, `IMAGES_DIR`, `DOCUMENTS_DIR` removed; `FileResponse` import removed | Low |
| 8 | Remove `FileStorageService` | `backend/app/ai/storage.py` | task 6 | File deleted or emptied; no remaining imports across codebase | Low |
| 9 | Update Pydantic schemas | `backend/app/models/schemas/ai.py` | task 3 | `FileAttachment.url` replaced with `content` (optional, for backward compat); `ImageUploadResponse` and `FileUploadResponse` updated to include `content` instead of `url` | Med |
| 10 | Update `add_message()` in service layer | `backend/app/services/ai_config_service.py` | task 3 | `add_message()` creates attachments with `content` field from `attachment_data["content"]` instead of `file_path` from `attachment_data["url"]` | Low |
| 11 | Update agent service: `_build_conversation_history()` and `format_multimodal_messages()` | `backend/app/ai/agent_service.py` | task 3, 10 | `format_multimodal_messages()` uses `content` field: images get `data:image/...;base64,...` data URLs; documents get inline text blocks with 512 KB truncation | High |
| 12 | Update WebSocket chat handler attachment dict conversion | `backend/app/api/routes/ai_chat.py` | task 9 | Attachment dicts passed to `add_message()` include `content` key from upload response | Low |
| 13 | Update existing backend tests | `backend/tests/unit/ai/test_attachments.py`, `backend/tests/integration/ai/test_attachment_context.py`, `backend/tests/unit/ai/test_llm_vision.py` | task 3, 9, 11 | All existing tests updated to use `content` instead of `file_path`; tests pass | Med |
| 14 | Update frontend types and upload API | `frontend/src/features/ai/chat/types.ts`, `frontend/src/features/ai/chat/api/attachmentUpload.ts`, `frontend/src/features/ai/types.ts` | task 9 | Types match new backend API; upload functions handle new response format | Med |
| 15 | Update `FilePreview` component for base64 images | `frontend/src/features/ai/chat/components/FilePreview.tsx` | task 14 | Images render from base64 data URLs; documents show filename only | Low |
| 16 | Update `useStreamingChat` attachment handling | `frontend/src/features/ai/chat/api/useStreamingChat.ts` | task 14 | Attachment data sent to WebSocket matches new schema | Low |
| 17 | Run full quality checks | all modified files | all tasks | MyPy zero errors, Ruff zero errors, tests pass, frontend builds | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FC-1 | T-001 | `tests/unit/ai/test_file_extractors.py` | TXT/CSV/JSON content extracted as-is |
| FC-2 | T-002 | `tests/unit/ai/test_file_extractors.py` | PDF/DOCX/XLSX/PPTX text extracted |
| FC-3 | T-003 | `tests/unit/ai/test_file_extractors.py` | Image base64 round-trip verified |
| FC-4 | T-004 | `tests/unit/ai/test_file_extractors.py` | Oversized content raises ValueError |
| FC-5 | T-005 | `tests/integration/ai/test_attachment_context.py` | Mixed attachments formatted correctly |
| FC-6 | T-006 | `tests/integration/ai/test_attachment_context.py` | Null content attachments degrade gracefully |
| TC-1/TC-2 | T-007 | `tests/unit/ai/test_attachments.py` | Migration verified via model fields |
| TC-5/TC-6 | T-008 | CI pipeline | MyPy and Ruff pass |

---

## Test Specification

### Test Hierarchy

```text
tests/
  unit/
    ai/
      test_file_extractors.py       -- NEW: text extraction for all file types
      test_attachments.py           -- UPDATED: use content instead of file_path
      test_llm_vision.py            -- UPDATED: use base64 data URLs instead of HTTP URLs
  integration/
    ai/
      test_attachment_context.py    -- UPDATED: content-based attachment flow
      test_agent_vision.py          -- UPDATED: agent service builds correct content blocks
```

### Test Cases (first 8)

| Test ID | Test Name | Criterion | Type | Verification |
|---|---|---|---|---|
| T-001 | `test_extract_text_from_txt_returns_raw_content` | FC-1 | Unit | TXT bytes returned as UTF-8 string |
| T-002 | `test_extract_text_from_pdf_returns_extracted_text` | FC-2 | Unit | PDF bytes produce non-empty text string |
| T-003 | `test_extract_text_from_docx_returns_paragraphs` | FC-2 | Unit | DOCX bytes produce concatenated paragraph text |
| T-004 | `test_extract_text_from_unsupported_type_returns_none` | FC-2 | Unit | Unknown MIME type returns None (no crash) |
| T-005 | `test_extract_text_oversized_content_raises_error` | FC-4 | Unit | Content > 512 KB raises ValueError with size message |
| T-006 | `test_format_multimodal_with_image_uses_base64_data_url` | FC-3 | Unit | Image attachment produces `data:image/png;base64,...` in content block |
| T-007 | `test_format_multimodal_with_document_inlines_text_content` | FC-2 | Unit | Document attachment produces text block with extracted content |
| T-008 | `test_build_conversation_history_with_null_content_degrades_gracefully` | FC-6 | Integration | Attachments with null content produce `[User attached: filename]` placeholder |

### Test Infrastructure Needs

- **Fixtures needed**: Sample files for each type (TXT, CSV, JSON, PDF, DOCX, XLSX, PPTX, PNG) as bytes fixtures in conftest or test file
- **Mocks/stubs**: No external service mocking needed; all extraction is local
- **Database state**: Existing conftest.py `db_session` fixture sufficient

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | Binary text extraction libraries may fail on malformed files | Medium | Low | Wrap extraction in try/except; return None on failure; upload endpoint rejects with clear message |
| Technical | Large files (approaching 10 MB upload limit) produce extracted text exceeding 512 KB | Medium | Medium | Enforce 512 KB limit at extraction time; reject oversized extractions early |
| Integration | Existing attachments with `file_path` but no `content` will break after migration | High | Medium | Migration runs after any prod data is created; since this is a dev feature with no prod data yet, no migration path for old data needed. Agent service handles null `content` gracefully with placeholder text. |
| Performance | Base64 encoding increases image storage by 33% in DB | Low | Low | 5 MB image limit keeps base64 at ~6.7 MB; PostgreSQL TEXT handles this fine |
| Frontend | Base64 data URLs may be very large for images, affecting message list rendering | Low | Low | Images are already limited to 5 MB; base64 at ~6.7 MB is manageable |

---

## Documentation References

### Required Reading

- Domain model: `backend/app/models/domain/ai.py` (lines 252-283)
- Upload routes: `backend/app/api/routes/ai_upload.py`
- Agent service: `backend/app/ai/agent_service.py` (lines 1413-1531)
- Config service: `backend/app/services/ai_config_service.py` (lines 479-532)
- Pydantic schemas: `backend/app/models/schemas/ai.py` (lines 327-409)
- Frontend upload: `frontend/src/features/ai/chat/api/attachmentUpload.ts`
- Frontend types: `frontend/src/features/ai/chat/types.ts` (lines 109-117)
- Frontend types: `frontend/src/features/ai/types.ts` (lines 245-252)

### Code References

- Similar pattern (content stored inline): `AIProviderConfig.value` (encrypted TEXT storage in same codebase)
- Text extraction libraries:
  - `pypdf` for PDF: `PdfReader(io.BytesIO(content)).pages`
  - `python-docx` for DOCX: `Document(io.BytesIO(content)).paragraphs`
  - `openpyxl` for XLSX: `load_workbook(io.BytesIO(content), read_only=True)`
  - `python-pptx` for PPTX: `Presentation(io.BytesIO(content)).slides`

---

## Prerequisites

### Technical

- [ ] New Python packages installed: `pypdf`, `python-docx`, `openpyxl`, `python-pptx`
- [ ] Database migration created and tested
- [ ] No existing production data with file_path-based attachments (confirmed: dev-only feature)

### Documentation

- [x] Analysis phase approved
- [x] Architecture docs reviewed (domain model, upload routes, agent service)
- [x] Existing tests reviewed

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  # === Level 0: No dependencies, can start immediately ===

  - id: BE-001
    name: "Add text extraction Python dependencies to pyproject.toml"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Create DB migration: add content TEXT column, remove file_path column"
    agent: pdca-backend-do-executor
    dependencies: []

  # === Level 1: Depends on migration and dependencies ===

  - id: BE-003
    name: "Update AIConversationAttachment domain model (content field, remove file_path)"
    agent: pdca-backend-do-executor
    dependencies: [BE-002]

  - id: BE-004
    name: "Create text extraction utility module (file_extractors.py)"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  # === Level 2: Depends on model and extraction utility ===

  - id: BE-005
    name: "Write unit tests for text extraction utility"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]
    kind: test

  - id: BE-006
    name: "Rewrite upload endpoints: extract text/base64, store in DB, no disk writes"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-004]

  - id: BE-007
    name: "Update Pydantic schemas (FileAttachment, upload responses)"
    agent: pdca-backend-do-executor
    dependencies: [BE-003]

  - id: BE-008
    name: "Remove FileStorageService (backend/app/ai/storage.py)"
    agent: pdca-backend-do-executor
    dependencies: [BE-006]

  # === Level 3: Service layer and agent service updates ===

  - id: BE-009
    name: "Update add_message() in ai_config_service.py to use content field"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-007]

  - id: BE-010
    name: "Update agent service: format_multimodal_messages() and _build_conversation_history()"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-009]

  - id: BE-011
    name: "Update WebSocket chat handler attachment dict conversion"
    agent: pdca-backend-do-executor
    dependencies: [BE-007, BE-009]

  # === Level 4: Test updates ===

  - id: BE-012
    name: "Update existing backend tests (attachments, vision, integration)"
    agent: pdca-backend-do-executor
    dependencies: [BE-003, BE-007, BE-010]
    kind: test

  - id: BE-013
    name: "Run full backend quality checks (MyPy, Ruff, pytest)"
    agent: pdca-backend-do-executor
    dependencies: [BE-012]
    kind: test

  # === Frontend tasks: can start once backend schemas are stable ===

  - id: FE-001
    name: "Update frontend types (FileAttachment, upload response types)"
    agent: pdca-frontend-do-executor
    dependencies: [BE-007]

  - id: FE-002
    name: "Update attachmentUpload.ts for new API response format"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Update FilePreview component for base64 image rendering"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-004
    name: "Update useStreamingChat attachment handling for new schema"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  # === Final validation ===

  - id: FE-005
    name: "Run frontend quality checks (lint, build)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002, FE-003, FE-004]
    kind: test
```

### Execution Notes for the Orchestrator

1. **BE-001 and BE-002** are independent and can run in parallel as the very first tasks.
2. **BE-003** (model update) and **BE-004** (extraction utility) depend on Level 0 tasks and can run in parallel.
3. **BE-006** (upload endpoints) is the critical path task -- it depends on both the model and the extraction utility.
4. **BE-005** (extraction tests) should run after BE-004 but can overlap with BE-006 if needed.
5. **BE-012** and **BE-013** (test updates and quality checks) are sequential and must run after all backend code changes.
6. **Frontend tasks (FE-001 through FE-005)** can start as soon as BE-007 (Pydantic schemas) is complete and can run in parallel with remaining backend work.
7. **BE-008** (remove FileStorageService) should run after BE-006 to ensure no code still references it.
8. All test tasks (`kind: test`) that touch the database should NOT be parallelized -- they share the same database and may destroy data.
