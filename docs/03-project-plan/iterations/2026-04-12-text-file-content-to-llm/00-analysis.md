# Analysis: Send Non-Image File Attachment Content to LLM

**Created:** 2026-04-12
**Request:** Non-image file attachments (TXT, CSV, JSON, etc.) currently get a placeholder `[User attached: filename.txt]` in messages sent to the LLM. The LLM never sees the actual file content. The user wants text-readable file content read and sent to the LLM as part of the conversation, stored in the database (not on disk), with MIME type persisted.

---

## Clarified Requirements

### Functional Requirements

1. **Read text file content**: For text-readable file types (`.txt`, `.csv`, `.json`), the upload endpoint must read the file content as a string
2. **Store content in DB**: File content must be stored in the `ai_conversation_attachments` table (PostgreSQL), not on disk at `uploads/ai/documents/`
3. **Store MIME type**: The `content_type` column already exists and stores MIME type -- this requirement is already met
4. **Send content to LLM**: When building conversation history, text file content must be included in the message payload sent to the LLM, not just a filename placeholder
5. **Preserve image flow**: Image attachments continue to use `image_url` blocks for vision models -- no changes to image handling

### Non-Functional Requirements

1. **Size limit**: Text file content stored in DB must have a reasonable size limit to avoid bloating the conversation history sent to the LLM context window
2. **Backward compatibility**: Existing attachments (8 rows in DB, 5 images + 3 text files) must continue to work
3. **Type safety**: All new columns and fields must pass MyPy strict mode
4. **Test coverage**: New code must have 80%+ test coverage

### Constraints

1. **Single-server deployment**: No S3/cloud storage; DB storage is the right choice for this deployment model
2. **OpenAI-compatible API**: Content must be formatted as text blocks compatible with OpenAI chat completions
3. **No frontend changes required**: The upload API contract (request/response shape) stays the same; only backend behavior changes

---

## Context Discovery

### Product Scope

- This is an enhancement to the existing multimodal I/O iteration (2026-04-11-multimodal-io)
- The prior iteration established image vision support (upload, storage, LLM formatting)
- This request fills the gap for non-image file types

### Architecture Context

- **Bounded context**: AI Chat (non-versioned entities, `SimpleEntityBase`)
- **Layered architecture**: API route -> Service -> Domain Model / ORM
- **Key pattern**: `AIConfigService.add_message()` creates attachment records; `AgentService._build_conversation_history()` reconstructs LangChain messages from DB

### Codebase Analysis

**Backend -- Current Attachment Flow (end-to-end):**

1. **Upload** (`ai_upload.py:167`): `upload_file()` reads file bytes, validates size/type, writes to `uploads/ai/documents/{uuid}.{ext}`, returns `FileUploadResponse` with `file_id`, `url`, `content_type`
2. **DB persist** (`ai_config_service.py:479`): `add_message()` receives attachment dicts with keys `filename`, `content_type`, `url`, `file_size`. Creates `AIConversationAttachment` rows where `file_path` stores the API URL (e.g., `/api/v1/ai/chat/documents/{uuid}.txt`)
3. **LLM formatting** (`agent_service.py:1467`): `format_multimodal_messages()` checks `content_type.startswith("image/")`. Images get `image_url` blocks; non-images get `[User attached: filename]` text appended -- **this is the gap**
4. **History rebuild** (`agent_service.py:1413`): `_build_conversation_history()` loads attachments from DB, passes them to `format_multimodal_messages()`

**Frontend -- No changes needed:**
- `attachmentUpload.ts` calls `POST /upload-file` and receives `FileUploadResponse` -- same shape
- `MessageInput.tsx` handles file selection and preview -- no changes
- `ChatInterface.tsx` orchestrates upload-then-send -- no changes

**Existing DB state:**
- 8 attachments total: 5 images, 3 text files (all `text/plain`, 133 bytes each)
- No `content` column exists in `ai_conversation_attachments`
- `file_path` currently stores API URLs, not filesystem paths

---

## Solution Options

### Option 1: Add `content` Column, Store Text Inline, Eliminate Disk for Documents

**Architecture & Design:**

Add a nullable `content` column (TEXT) to `ai_conversation_attachments`. The upload endpoint reads text-based files, stores content directly in the DB row, and skips disk write entirely for those types. Binary files (PDF, DOCX, XLSX, PPTX) remain on disk with `file_path` pointing to the API URL as today.

When building conversation history, `format_multimodal_messages()` reads the `content` field from the attachment ORM object and includes it as a text block in the LLM message.

**File type handling matrix:**

| Type | MIME | Content stored in DB? | Disk write? | Sent to LLM? |
|------|------|-----------------------|-------------|---------------|
| TXT | `text/plain` | Yes (TEXT column) | No | Yes (inline text) |
| CSV | `text/csv` | Yes (TEXT column) | No | Yes (inline text) |
| JSON | `application/json` | Yes (TEXT column) | No | Yes (inline text) |
| PDF | `application/pdf` | No | Yes (disk) | No (placeholder) |
| DOCX | `application/vnd.openxmlformats...` | No | Yes (disk) | No (placeholder) |
| XLSX | `application/vnd.openxmlformats...` | No | Yes (disk) | No (placeholder) |
| PPTX | `application/vnd.openxmlformats...` | No | Yes (disk) | No (placeholder) |

**Implementation:**

1. **Migration**: Add `content = sa.Column(Text, nullable=True)` to `ai_conversation_attachments`
2. **Domain model** (`ai.py`): Add `content: Mapped[str | None] = mapped_column(Text, nullable=True)` to `AIConversationAttachment`
3. **Upload endpoint** (`ai_upload.py`): For text MIME types, decode `content` bytes to UTF-8 string, store in DB, skip disk write. For binary types, write to disk as today.
4. **Service** (`ai_config_service.py`): `add_message()` accepts optional `content` key in attachment dicts, passes to ORM
5. **LLM formatting** (`agent_service.py`): `format_multimodal_messages()` checks if attachment has `content` field (populated from DB via eager load). If so, appends it as a text block.
6. **WebSocket handler** (`ai_chat.py`): Pass `content` through the attachment dict chain when saving user message

**Key design decision -- where to read the content:**
- The upload endpoint already has the raw bytes in memory (line 200: `content = await file.read()`)
- For text types, decode to string at upload time and store in DB immediately
- No need for a "read from disk later" method

**Size limit for text content in DB:**
- Enforce a `MAX_TEXT_CONTENT_SIZE = 512 * 1024` (512KB) limit at upload time
- Files exceeding this limit get a truncation warning in the text block sent to LLM
- The existing 10MB `MAX_FILE_SIZE` applies at the upload validation level

**Trade-offs:**

| Aspect          | Assessment                                                                 |
| --------------- | -------------------------------------------------------------------------- |
| Pros            | Simplest change; text content travels with the attachment row; no disk I/O for text files; clean separation text vs binary |
| Cons            | DB rows for text attachments will be larger; no PDF/DOCX text extraction in this scope |
| Complexity      | Low -- 4 files to modify, 1 migration, straightforward logic              |
| Maintainability | Good -- follows existing patterns; no new services or abstractions        |
| Performance     | Good for text -- no disk read during LLM formatting; slightly larger DB rows |

---

### Option 2: Add `content` Column + Binary File Text Extraction via Libraries

**Architecture & Design:**

Same as Option 1 for the `content` column and text file handling, but adds text extraction for binary document types (PDF, DOCX, XLSX) using Python libraries (`pypdf`, `python-docx`, `openpyxl`). Extracted text is stored in the same `content` column.

**Implementation:**

1. All of Option 1, plus:
2. Add dependencies: `pypdf`, `python-docx`, `openpyxl` to `pyproject.toml`
3. Create `backend/app/ai/file_content_reader.py` -- a utility that dispatches to the correct extractor based on MIME type
4. Upload endpoint calls `file_content_reader.extract_text(content_bytes, mime_type)` for all document types
5. For binary types, both disk write AND text extraction happen -- disk for download/retrieval, DB for LLM context

**Trade-offs:**

| Aspect          | Assessment                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------ |
| Pros            | LLM can reason about PDFs, DOCX, XLSX content; maximum utility for the user               |
| Cons            | New dependencies (3 libraries); text extraction is lossy (formatting, tables, images in PDFs); larger scope; library versioning/maintenance burden |
| Complexity      | Medium -- adds a new module, 3 dependencies, and per-type extraction logic                 |
| Maintainability | Fair -- extraction quality varies by file; library updates may change behavior             |
| Performance     | Fair -- extraction adds CPU overhead at upload time; XLSX/PDF parsing can be slow for large files |

---

### Option 3: Keep Disk Storage, Add `content` Column Populated at LLM-Format Time

**Architecture & Design:**

Keep the current disk-based storage for all file types. Add a `content` column but populate it lazily -- when `_build_conversation_history()` encounters a non-image attachment without content, read the file from disk, store in DB, then include in LLM message.

**Implementation:**

1. Migration: same `content` column
2. Upload endpoint: unchanged -- all files go to disk as today
3. `_build_conversation_history()`: when processing attachments, check if `content` is NULL and file is text type. If so, read from disk path, store in DB, use for LLM message
4. The `DOCUMENTS_DIR` resolution would need to be accessible from the agent service context

**Trade-offs:**

| Aspect          | Assessment                                                                                |
| --------------- | ----------------------------------------------------------------------------------------- |
| Pros            | No upload endpoint changes; lazy migration of existing data                               |
| Cons            | Adds disk I/O during LLM message formatting (critical path); couples agent service to filesystem layout; file_path stores API URLs not real paths -- path resolution is fragile |
| Complexity      | Medium -- path resolution logic is tricky; lazy loading adds state management             |
| Maintainability | Poor -- tight coupling between agent service and filesystem; race conditions on lazy write |
| Performance     | Poor -- disk read on every LLM call until content is populated; first-call latency spike  |

---

## Comparison Summary

| Criteria           | Option 1: Text-only DB storage  | Option 2: + Binary extraction   | Option 3: Lazy disk read       |
| ------------------ | ------------------------------- | -------------------------------- | ------------------------------ |
| Development Effort | 2-3h (small scope)              | 5-7h (dependencies + extraction) | 4-5h (path resolution + lazy) |
| UX Quality         | Good (TXT/CSV/JSON work)        | Best (all file types)            | Good (TXT/CSV/JSON work)      |
| Flexibility        | Good (extensible later)         | Best (covers all types now)      | Fair (fragile path logic)     |
| Best For           | Quick win, text files           | Maximum LLM reasoning power      | Avoiding upload changes       |

---

## Recommendation

**I recommend Option 1** because:

1. **Simplicity**: It is the minimum viable change that solves the stated requirement. The user specifically listed `.txt`, `.csv`, `.json` as the target types. Option 1 covers exactly those with minimal code changes.

2. **No new dependencies**: Option 2 adds 3 Python libraries for PDF/DOCX/XLSX extraction, which introduces versioning risk and maintenance burden for a feature that may not be needed immediately.

3. **Performance**: Text content is stored at upload time (already in memory), so there is zero additional I/O during LLM message formatting. This is the right time to store it -- the bytes are already loaded.

4. **Extensibility**: If binary file text extraction is needed later, Option 1 can be extended to Option 2 without schema changes -- just add the extraction logic and populate the same `content` column.

5. **Eliminates disk writes for text files**: For the 3 text MIME types, no file is written to disk at all. This simplifies the upload endpoint and removes the need for the document retrieval endpoint for these types.

**Alternative consideration:** Choose Option 2 if users regularly upload PDF/DOCX/XLSX files and expect the LLM to reason about their content. This can be deferred to a follow-up iteration since the architecture does not change -- only the extraction logic and dependencies.

---

## Decision Questions

1. **Should the text content size limit be 512KB or smaller?** The current MAX_FILE_SIZE is 10MB, but sending 10MB of text in a single LLM context window is impractical. A 512KB limit for inline content seems reasonable, with truncation beyond that. Do you want a different threshold?

2. **Should binary file types (PDF, DOCX, XLSX, PPTX) continue to get the `[User attached: filename]` placeholder, or should they be blocked from upload until text extraction is implemented?** Blocking them would be a UX regression. Keeping the placeholder is honest -- the LLM knows a file was attached but cannot see its content.

3. **Should the `file_path` column be made nullable for text-type attachments stored in DB?** Since text files will no longer be written to disk, the `file_path` column would have no meaningful value for them. Making it nullable is cleaner than storing a dummy value.

---

## References

- Upload endpoint: `backend/app/api/routes/ai_upload.py`
- Storage service: `backend/app/ai/storage.py`
- Agent message building: `backend/app/ai/agent_service.py` (lines 1413-1531)
- Domain model: `backend/app/models/domain/ai.py` (`AIConversationAttachment` at line 252)
- Pydantic schemas: `backend/app/models/schemas/ai.py` (`FileAttachment` at line 327)
- Service layer: `backend/app/services/ai_config_service.py` (`add_message()` at line 479)
- Frontend upload: `frontend/src/features/ai/chat/api/attachmentUpload.ts`
- Migration: `backend/alembic/versions/4b64f142cdf3_add_ai_conversation_attachments_table.py`
- Prior iteration: `docs/03-project-plan/iterations/2026-04-11-multimodal-io/`
