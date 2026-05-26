# Analysis: Project Document Repository

**Created:** 2026-05-25
**Status:** Scouting / Decision Pending
**Request:** Add document management to projects — upload, organize, search, and AI-access project documents with full RBAC compliance.

---

## 1. Problem Statement

Backcast currently has no document management capability. Project teams working on end-of-line automation projects produce and consume a significant volume of technical and contractual documents — engineering drawings, contracts, invoices, technical specs, quality records — that are stored and shared outside the system (email, shared drives, SharePoint). This creates:

- **Fragmented information**: Documents are disconnected from the project entities they relate to (WBEs, cost elements, change orders)
- **No access control**: Documents shared via email or drives bypass the project RBAC system
- **No audit trail**: No record of who uploaded what, when, or which version is current
- **No AI access**: The AI assistant cannot reference or analyze project documents
- **Duplicate work**: Cost registration attachments already store some files (invoices, receipts) as database blobs — a pattern that doesn't scale

---

## 2. Business Requirements

### 2.1 Users & Roles

| Role | Document Need |
|------|--------------|
| **Project Manager** | Upload, organize, review all project documents. Full CRUD. |
| **Department Manager** | Upload technical docs for their department's cost elements. Read others. |
| **Project Controller** | Read-only access to review documents for compliance and reporting. |
| **Executive** | Summary view — document counts, storage usage, no deep access needed. |
| **AI Assistant** | Search and read document content to answer project queries. |

### 2.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Upload documents to a project (drag-and-drop, multi-file) | Must |
| FR-02 | Organize documents in a folder hierarchy (create, rename, move, delete folders) | Must |
| FR-03 | Download documents with original filename and format | Must |
| FR-04 | Version tracking — upload new version of an existing document, view history | Must |
| FR-05 | Full-text search across document content and metadata | Must |
| FR-06 | Tag documents with custom labels for categorization | Should |
| FR-07 | Inline preview for images and PDFs | Should |
| FR-08 | Thumbnail generation for visual file types | Should |
| FR-09 | Document metadata: name, description, tags, size, dates, uploader | Must |
| FR-10 | Project-scoped access control — documents inherit project membership | Must |
| FR-11 | Lock/unlock documents to prevent concurrent editing conflicts | Could |
| FR-12 | Link documents to project entities (WBEs, cost elements, change orders) | Should |
| FR-13 | AI tools to search, read, and summarize document content | Must |
| FR-14 | Storage quota management per project | Could |
| FR-15 | Bulk upload/download (zip) | Could |

### 2.3 Supported File Types

| Category | Types | Max Size |
|----------|-------|----------|
| Documents | PDF, DOCX, XLSX, PPTX, TXT, CSV, MD | 50 MB |
| Images | PNG, JPG, JPEG, GIF, WEBP, SVG | 20 MB |
| Technical | DWG, DXF, STEP, IGS (metadata only, no preview) | 100 MB |
| Archives | ZIP, RAR (extract and catalog) | 200 MB |

### 2.4 Business Workflows

1. **Project Setup**: PM creates folder structure (Drawings, Contracts, Reports, Quality)
2. **Daily Operations**: Team uploads documents, tags them, links to relevant entities
3. **Change Orders**: Documents related to a CO are organized in a CO-specific folder
4. **Review/Approval**: Controller reviews documents for compliance (read-only)
5. **AI Queries**: PM asks AI "show me the latest foundation drawing" or "summarize the main contract"
6. **Audit Trail**: All uploads, downloads, deletions tracked with timestamps and user

---

## 3. Technical Requirements

### 3.1 Architecture Constraints

| Constraint | Detail |
|-----------|--------|
| **Backend** | Python 3.12+ / FastAPI, async throughout (asyncpg) |
| **Frontend** | React 18 / TypeScript / Vite, Ant Design UI library |
| **Database** | PostgreSQL 15+ with Alembic migrations |
| **Entity Model** | EVCS system — Simple / Versionable / Branchable tiers |
| **RBAC** | Project-scoped permissions via `ProjectRoleChecker` |
| **AI Tools** | `@ai_tool` decorator with `ToolContext` injection |
| **Deployment** | Docker Compose, self-hosted, single-server |
| **Auth** | JWT Bearer tokens |

### 3.2 Integration Points

| Integration | Current Pattern | Document Repository Must |
|-------------|----------------|--------------------------|
| **RBAC** | `ProjectRoleChecker("project-read")` on routes | New `project-documents-read/write/delete` permissions |
| **AI Tools** | `@ai_tool(name="list_projects", category="projects")` | New `search_documents`, `read_document`, `summarize_document` tools |
| **Project Layout** | Tab-based navigation in `ProjectLayout.tsx` (11 tabs) | New "Documents" tab |
| **File Extraction** | `file_extractors.py` — PDF, DOCX, XLSX, PPTX text extraction | Reuse for document full-text indexing |
| **Global Search** | `GlobalSearchService` searches projects, WBEs, cost elements | Extend to include documents |
| **Existing Attachments** | `CostRegistrationAttachment` stores BYTEA in PostgreSQL | No migration required — separate feature |

### 3.3 Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Upload latency (50 MB file) | < 5 seconds |
| Search response time | < 500ms |
| Concurrent uploads per project | 10+ |
| Storage per project | 10 GB+ |
| Total storage | 500 GB+ |
| Presigned URL expiry | 15 minutes |
| Thumbnail generation | < 3 seconds per file |
| Text extraction | < 2 seconds per file |

---

## 4. Current Architecture Findings

### 4.1 Existing File Handling

**CostRegistrationAttachment** (`backend/app/models/domain/cost_registration_attachment.py`):
- `SimpleEntityBase`, stores files as BYTEA in PostgreSQL
- Fields: `cost_registration_id`, `filename`, `content_type`, `content` (bytes), `size`
- Service: `cost_registration_attachment_service.py` — standard AsyncSession CRUD
- Max size: 10 MB (`COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB` in config)
- No folder hierarchy, no versioning, no search

**AI File Uploads** (`backend/app/api/routes/ai_upload.py`):
- Images: base64-encoded, max 5 MB, inline in chat
- Documents: text extracted via `file_extractors.py`, max 10 MB
- Stored as `AIConversationAttachment` — ephemeral, per-conversation
- Not a general-purpose document store

### 4.2 RBAC System

**12 predefined roles** with 80+ permissions. Project-scoped permissions enforced via `ProjectRoleChecker` dependency. Key project roles:

- `project_admin` — full access including member management
- `project_manager` — CRUD on projects, cost elements, WBEs, forecasts
- `project_editor` — create/update, no delete
- `project_viewer` — read-only
- `ai-viewer` — read + AI chat
- `ai-manager` — full AI features + project management
- `ai-admin` — AI configuration management

### 4.3 AI Tool System

- **Decorator**: `@ai_tool(name, description, permissions, category, risk_level)` in `backend/app/ai/tools/decorator.py`
- **Context injection**: `Annotated[ToolContext, InjectedToolArg]` provides `session`, `user_id`, `project_id`
- **Registry**: Auto-discovers all `@ai_tool` functions in `backend/app/ai/tools/`, converts to LangChain tools
- **Risk levels**: LOW (read), MEDIUM (create/update), HIGH (delete)

### 4.4 Frontend Patterns

- **Routing**: `ProjectLayout.tsx` with tab navigation (11 tabs: Dashboard, Overview, Structure, Schedule, Change Orders, Members, EVM Analysis, COQ Analysis, Work Packages, AI Chat, Admin)
- **State**: TanStack Query for server state, Zustand for client state
- **API hooks**: Feature-based in `src/features/{name}/api/` with query key factories
- **Components**: Ant Design library, feature-based in `src/features/{name}/components/`

### 4.5 Deployment

- **Docker Compose** (`docker-compose.dev.yml`) with PostgreSQL 15-alpine + Adminer
- **Production** (`docker-compose.yml`) with Traefik reverse proxy + SSL
- **Named volumes** for data persistence
- **No external file storage** currently — all data in PostgreSQL

---

## 5. Storage Backend Evaluation

### 5.1 Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Integration ease with FastAPI | High | Python SDK quality, async support |
| Self-hosted simplicity | High | Single binary vs multi-service deployment |
| S3 compatibility | High | Industry standard API, future portability |
| RBAC delegation | Medium | Can storage auth be delegated to app layer? |
| Full-text search | Medium | Built-in or requires external service? |
| License | Medium | Permissive (Apache/MIT) vs copyleft (GPL/AGPL) |
| Scalability | Medium | Beyond single-server needs? |
| Cost/complexity | High | Operational overhead, learning curve |

### 5.2 Candidate Solutions

#### Option A: MinIO

| Aspect | Assessment |
|--------|-----------|
| **What** | S3-compatible object storage, written in Go |
| **License** | AGPL v3.0 (self-hosted). Using MinIO as-is via API does not trigger AGPL copyleft — only modifying MinIO source would. |
| **Integration** | `boto3` (sync) or `aiobotocore` (async) — standard S3 SDK |
| **Self-hosting** | Single Docker container, minimal config |
| **Features** | Presigned URLs, versioning, lifecycle policies, multipart upload, web console |
| **RBAC** | Application-level — MinIO bucket policies can restrict, but RBAC managed in Backcast |
| **Search** | None built-in — PostgreSQL metadata + `pg_trgm` for text search |
| **Scalability** | Single-node to distributed cluster |
| **Pros** | De facto standard for self-hosted S3. Huge ecosystem. Easy local dev. |
| **Cons** | AGPL license concern if embedding/modifying. Separate service to manage. |
| **Fit** | **Strong** |

#### Option B: PostgreSQL BYTEA (Status Quo)

| Aspect | Assessment |
|--------|-----------|
| **What** | Store files as binary columns in PostgreSQL |
| **Integration** | Native — no external dependency |
| **Self-hosting** | Already deployed |
| **Pros** | Zero infra overhead. ACID consistency. Proven with CostRegistrationAttachment. |
| **Cons** | DB bloat (50 MB files × 1000s = GBs in WAL). Slow backups. No streaming. ~1 GB BYTEA practical limit. No presigned URLs. |
| **Fit** | **Weak** — works for small attachments, not for general-purpose document repository |

#### Option C: Filesystem

| Aspect | Assessment |
|--------|-----------|
| **What** | Store files on server disk, paths in database |
| **Integration** | Python `pathlib`/`aiofiles` — trivial |
| **Pros** | Simplest code. Fast local I/O. No container dependency. |
| **Cons** | No presigned URLs. Backup coordination with DB. Container volume management. No replication. |
| **Fit** | **Moderate** — simpler than MinIO but loses S3 benefits (presigned URLs, CDN, multipart) |

#### Option D: Nextcloud (External DMS)

| Aspect | Assessment |
|--------|-----------|
| **What** | Full document management platform with web UI, collaboration, sharing |
| **License** | AGPL v3.0 |
| **Integration** | WebDAV/REST API, Python wrapper libraries |
| **Pros** | Complete DMS out of the box. Rich plugin ecosystem. |
| **Cons** | Heavy deployment (LAMP stack). Separate user/auth — must sync RBAC. Dual UIs = fragmented UX. Complex SSO. |
| **Fit** | **Weak** — overkill, creates UX fragmentation and auth sync burden |

#### Option E: Paperless-ngx (Document Processing)

| Aspect | Assessment |
|--------|-----------|
| **What** | Document digitization with OCR, tagging, classification |
| **License** | GPL v3.0 |
| **Integration** | REST API with `pypaperless` async client |
| **Pros** | Excellent text extraction and search. Automated classification. |
| **Cons** | Designed for paper digitization, not project document management. Separate auth. Heavy stack. |
| **Fit** | **Weak** — wrong use case. Could serve as OCR backend in the future. |

#### Option F: Hybrid — MinIO + PostgreSQL metadata

| Aspect | Assessment |
|--------|-----------|
| **What** | MinIO for binary storage, PostgreSQL for metadata + search + RBAC |
| **Integration** | `boto3`/`aiobotocore` for S3, asyncpg for PostgreSQL |
| **Self-hosting** | One additional Docker container (MinIO) |
| **Features** | Presigned URLs (MinIO) + full-text search + RBAC joins (PostgreSQL) |
| **Pros** | Best of both worlds. PostgreSQL handles relations/text search/RBAC. MinIO handles binary storage/streaming. Presigned URLs offload download traffic. |
| **Cons** | Two sources of truth — must handle consistency (orphan cleanup). One more container. |
| **Fit** | **Strong** — recommended approach |

### 5.3 Comparison Matrix

| Criterion | MinIO (A) | BYTEA (B) | Filesystem (C) | Nextcloud (D) | Hybrid (F) |
|-----------|-----------|-----------|----------------|---------------|------------|
| Integration ease | High | Highest | High | Low | High |
| Self-hosted simplicity | High | Highest | Highest | Low | High |
| S3 compatibility | Yes | No | No | No | Yes |
| Presigned URLs | Yes | No | No | Via API | Yes |
| Full-text search | External (PG) | pg_trgm | External (PG) | Built-in | pg_trgm |
| License | AGPL (use OK) | N/A | N/A | AGPL | AGPL (use OK) |
| Scalability | Cluster | Limited | Single node | Cluster | Cluster |
| Operational overhead | Low | None | None | High | Low |
| File size support | TB+ | ~1 GB | Disk limit | TB+ | TB+ |
| **Overall** | Strong | Weak | Moderate | Weak | **Strong** |

---

## 6. Proposed Data Model

Regardless of storage backend, the PostgreSQL metadata schema:

```
┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ document_folders    │     │ documents             │     │ document_versions    │
├─────────────────────┤     ├──────────────────────┤     ├──────────────────────┤
│ id (PK, UUID)       │◄────┤ folder_id (FK, NULL)  │     │ id (PK, UUID)        │
│ project_id          │     │ id (PK, UUID)         │◄────┤ document_id (FK)     │
│ parent_id (self FK) │     │ project_id            │     │ version_number       │
│ name                │     │ name                  │     │ storage_key / blob   │
│ path                │     │ extension             │     │ content_type         │
│ created_by          │     │ description           │     │ size_bytes           │
│ created_at          │     │ tags (JSONB)          │     │ checksum_sha256      │
│ updated_at          │     │ current_version_id    │     │ extracted_text       │
└─────────────────────┘     │ is_locked             │     │ thumbnail_key        │
                            │ locked_by             │     │ uploaded_by          │
                            │ created_by            │     │ created_at           │
                            │ created_at            │     └──────────────────────┘
                            │ updated_at            │
                            └──────────────────────┘
```

All three use `SimpleEntityBase`. No EVCS temporal versioning — document versions are application-level (numbered rows).

### RBAC Permissions to Add

```
project-documents-read    — View/download documents
project-documents-write   — Upload, edit metadata, create folders
project-documents-delete  — Delete documents and folders
```

Role mapping:

| Permission | admin | manager | project_admin | project_manager | project_editor | project_viewer | ai-manager | ai-viewer |
|-----------|-------|---------|---------------|-----------------|---------------|---------------|------------|-----------|
| documents-read | Y | Y | Y | Y | Y | Y | Y | Y |
| documents-write | Y | Y | Y | Y | Y | - | Y | - |
| documents-delete | Y | Y | Y | Y | - | - | Y | - |

### AI Tools to Add

| Tool | Permission | Risk | Description |
|------|-----------|------|-------------|
| `search_documents` | project-documents-read | LOW | Search by filename, content, tags |
| `read_document` | project-documents-read | LOW | Get extracted text content |
| `summarize_document` | project-documents-read | LOW | Metadata + content summary |

---

## 7. Open Decisions

| # | Decision | Options | Notes |
|---|----------|---------|-------|
| D1 | **Storage backend** | MinIO hybrid (F) vs Filesystem (C) vs BYTEA (B) | MinIO hybrid is the technical recommendation. Organizational constraints? |
| D2 | **EVCS tier** | SimpleEntityBase (recommended) vs Branchable | SimpleEntityBase matches CostRegistrationAttachment pattern. Branch isolation can be added later. |
| D3 | **First iteration scope** | Full feature vs core-only vs MVP | What's the minimum viable set for initial deployment? |
| D4 | **Async S3 client** | `aiobotocore` vs `boto3` (sync in thread) | Depends on performance testing. `aiobotocore` is native async but less maintained. |
| D5 | **Full-text search** | `pg_trgm` vs PostgreSQL `tsvector` vs external (Meilisearch) | `pg_trgm` is simplest. `tsvector` is more performant for large corpora. |
| D6 | **Document-entity linking** | Dedicated join table vs tag-based | Join table is cleaner for typed relationships (document ↔ WBE, document ↔ CO). |
| D7 | **MinIO license risk** | AGPL when used as-is vs modifying source | Using MinIO as an external service via API does not trigger AGPL copyleft. Only modifying MinIO source would. |

---

## 8. Scoping Questions

1. **Storage backend** — MinIO hybrid is the technical recommendation. Are there organizational constraints (license, ops capacity, policy) that rule it out?

2. **EVCS tier** — Do change orders need to isolate document changes? (i.e., a CO adds a revised drawing that only appears when the CO branch is active)

3. **First iteration scope** — What's the minimum viable feature set for initial deployment?

4. **File size limits** — Are 50 MB per file and 10 GB per project reasonable limits for the first iteration?

5. **Document-entity linking** — Should documents be linkable to specific WBEs, cost elements, or change orders in v1?

6. **Existing attachment migration** — Should CostRegistrationAttachment files be migrated to the new document repository, or remain as-is?

---

## 9. Next Steps

1. **Review this document** with stakeholders
2. **Resolve open decisions** (D1–D7) based on organizational constraints
3. **Scout specific solutions** for chosen storage backend
4. **Create implementation plan** (`01-plan.md`) with phased delivery
5. **Build**
