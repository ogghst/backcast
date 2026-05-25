# Use Cases: Document Repository

**Created:** 2026-05-25
**Scope:** Core document operations — creation, read, update, versioning, delete, entity linking

---

## Actors

| Actor | Role |
|-------|------|
| Project Manager | Full CRUD on documents, folders, entity links |
| Project Editor | Upload, edit metadata, create folders. No delete. |
| Project Viewer | Read-only: browse, search, download |
| AI Assistant | Search and read document content via tools |

---

## UC-01: Upload Document

**Actor:** PM, Editor
**Trigger:** User clicks "Upload" or drags files onto the document browser

**Main Flow:**
1. User selects one or more files from their machine
2. System validates: file extension in allowed list, size ≤ 50 MB, project storage quota not exceeded
3. System computes SHA-256 checksum
4. System uploads file binary to RustFS via `StorageService.upload_file()`
5. System extracts text content via `file_extractors.extract_text()` (PDF, DOCX, XLSX, PPTX, TXT, CSV, MD)
6. System creates `Document` record (name, extension, folder_id, project_id, created_by)
7. System creates `DocumentVersion` record (version_number=1, storage_key, content_type, size_bytes, checksum, extracted_text, uploaded_by)
8. System sets `Document.current_version_id` to the new version's ID
9. System returns document metadata to the frontend
10. Frontend refreshes the document list

**Alternates:**
- **A1: File too large** — System rejects with error message showing max size
- **A2: Unsupported extension** — System rejects with list of allowed types
- **A3: Quota exceeded** — System rejects with current usage / quota info
- **A4: Duplicate filename in folder** — System allows it (documents are identified by ID, not name). User can rename after upload.

**Postconditions:** Document binary stored in RustFS, metadata + extracted text in PostgreSQL, document visible in browser.

---

## UC-02: Browse Documents

**Actor:** PM, Editor, Viewer
**Trigger:** User navigates to Documents tab (project, WBE, or cost element)

**Main Flow:**
1. System loads folder tree for the project (left pane)
2. System loads documents for the selected folder or entity context (right pane)
3. If entity-scoped (WBE / cost element): system filters to documents linked to that entity via `document_entity_links`
4. Document list shows: name, extension icon, size, version count, uploaded by, date, tags
5. User can click a folder to filter, or click "All Documents" for the flat list

**Entity-scoped behavior:**
- **Project tab:** Shows all project documents with folder tree
- **WBE tab:** Shows documents linked to this WBE, no folder tree
- **Cost Element tab:** Shows documents linked to this cost element, no folder tree

**Postconditions:** None (read-only).

---

## UC-03: Download Document

**Actor:** PM, Editor, Viewer
**Trigger:** User clicks "Download" on a document

**Main Flow:**
1. System generates a presigned URL for the current version's `storage_key` (15 min expiry)
2. System returns the presigned URL to the frontend
3. Frontend opens the URL in a new tab / triggers browser download

**Alternates:**
- **A1: Download specific version** — User opens version history first, then clicks download on a specific version

**Postconditions:** None (read-only, download tracked in audit log if implemented).

---

## UC-04: Upload New Version

**Actor:** PM, Editor
**Trigger:** User clicks "Upload new version" on an existing document

**Main Flow:**
1. User selects a file from their machine
2. System validates: file extension matches original document (or is compatible), size ≤ 50 MB
3. System uploads file binary to RustFS (new storage key with incremented version)
4. System extracts text content from the new file
5. System creates new `DocumentVersion` record with incremented `version_number`
6. System updates `Document.current_version_id` to point to the new version
7. System updates `Document.size_bytes` from the new version
8. Frontend refreshes document detail to show updated version

**Alternates:**
- **A1: Document is locked by another user** — System rejects with "locked by {user}" message

**Postconditions:** New version stored, current version pointer updated, previous versions preserved.

---

## UC-05: Search Documents

**Actor:** PM, Editor, Viewer, AI Assistant
**Trigger:** User types in search bar, or AI calls `search_documents` tool

**Main Flow:**
1. User enters search query (free text)
2. Optional: user filters by folder, tags, extension
3. System searches across:
   - `documents.name` (trigram match via `pg_trgm`)
   - `document_versions.extracted_text` (trigram match)
   - `documents.tags` (JSONB contains)
   - `documents.description` (trigram match)
4. System returns matching documents ranked by relevance, with text excerpts highlighting matches
5. Frontend displays results with highlighted excerpts

**AI tool variant:**
- AI calls `search_documents(project_id, query, tags?, folder_id?)`
- Returns document metadata + excerpt, not full content
- AI can then call `read_document(document_id)` for full content

**Postconditions:** None (read-only).

---

## UC-06: Update Document Metadata

**Actor:** PM, Editor
**Trigger:** User clicks "Edit" on a document

**Main Flow:**
1. System opens document detail drawer/modal in edit mode
2. User modifies: name, description, tags
3. User clicks "Save"
4. System updates the `Document` record
5. Frontend refreshes document detail

**Alternates:**
- **A1: Move to folder** — User selects a different folder from the tree. System updates `folder_id`.
- **A2: Lock/unlock** — User toggles lock. System sets `is_locked` and `locked_by`.

**Postconditions:** Document metadata updated in PostgreSQL.

---

## UC-07: Link Document to Entity

**Actor:** PM, Editor
**Trigger:** User clicks "Link to entity" on a document, or "Link document" from an entity's Documents tab

**Main Flow:**
1. System opens entity picker modal showing project entities (WBEs, cost elements, change orders)
2. User selects one or more entities
3. User optionally adds a note for each link (e.g., "Foundation drawing for structural review")
4. System creates `DocumentEntityLink` records (document_id, entity_type, entity_id, note)
5. Frontend refreshes the linked entities list

**Alternates:**
- **A1: Link from entity side** — In a WBE's Documents tab, user clicks "Link existing document" → picks from project document list
- **A2: Unlink** — User removes a link. System deletes the `DocumentEntityLink` record. Document itself is not affected.

**Postconditions:** M:N link records created in `document_entity_links`. Document and entity remain independent — linking is an association, not ownership.

---

## UC-08: Delete Document

**Actor:** PM (with `project-documents-delete`)
**Trigger:** User clicks "Delete" on a document

**Main Flow:**
1. System prompts for confirmation
2. System checks: no locks by other users
3. System deletes all `DocumentEntityLink` records for this document
4. System deletes all `DocumentVersion` records for this document
5. System deletes the `Document` record
6. System schedules async cleanup of RustFS objects (all version storage keys)
7. Frontend removes document from the list

**Alternates:**
- **A1: Document is locked** — System rejects. User must unlock first.
- **A2: Folder delete** — User deletes a folder. System deletes all child documents (cascade).

**Postconditions:** Metadata removed from PostgreSQL, binaries cleaned up from RustFS.

---

## UC-09: Folder Management

**Actor:** PM, Editor
**Trigger:** User interacts with the folder tree

**Operations:**

| Operation | Flow |
|-----------|------|
| **Create folder** | User clicks "+", enters name. System creates `DocumentFolder` with computed `path`. |
| **Rename folder** | User right-clicks → Rename. System updates `name` and recomputes `path` for folder and all descendants. |
| **Move folder** | User drags folder to new parent. System updates `parent_id` and recomputes `path`. |
| **Delete folder** | User clicks delete. System confirms. Cascades delete to all child documents (UC-08). |

**Postconditions:** Folder tree updated in PostgreSQL.

---

## UC-10: Cost Registration Attachment (Refactored)

**Actor:** PM, Editor
**Trigger:** User uploads an attachment to a cost registration

**Main Flow (refactored):**
1. User opens cost registration edit modal, clicks "Add attachment"
2. System validates: size ≤ 10 MB
3. System uploads file binary to RustFS via `StorageService.upload_file()` (same service as documents)
4. System creates `CostRegistrationAttachment` record with `storage_key` instead of `content` BYTEA
5. Frontend shows attachment with download link (presigned URL)

**Migration from existing BYTEA data:**
1. Alembic migration adds `storage_key` column (nullable)
2. Backfill script: reads BYTEA content, uploads to RustFS, sets `storage_key`
3. Subsequent migration drops `content` BYTEA column

**Postconditions:** Attachments use RustFS storage, same as documents. Single storage backend for all files.
