# Analysis: Project Document Repository with RustFS

**Created:** 2026-05-25
**Request:** Add document management to projects -- upload, organize, search, and AI-access project documents with full RBAC compliance. Uses RustFS for binary storage, PostgreSQL for metadata/search/RBAC.

---

## Clarified Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Upload documents to a project (drag-and-drop, multi-file) | Must |
| FR-02 | Organize documents in a folder hierarchy (create, rename, move, delete) | Must |
| FR-03 | Download documents with original filename and format | Must |
| FR-04 | Version tracking -- upload new version of an existing document, view history | Must |
| FR-05 | Full-text search across document content and metadata | Must |
| FR-06 | Document metadata: name, description, tags, size, dates, uploader | Must |
| FR-07 | Project-scoped access control -- documents inherit project membership | Must |
| FR-08 | M:N entity linking: documents linkable to WBEs, cost elements, change orders with notes | Should |
| FR-09 | AI tools: search_documents, read_document, list_documents | Must |
| FR-10 | Document tab in project, WBE, and cost element detail views | Must |
| FR-11 | Refactor CostRegistrationAttachment to use same StorageService + RustFS | Must |
| FR-12 | Tag documents with custom labels for categorization | Should |
| FR-13 | Inline preview for images and PDFs | Could |
| FR-14 | Thumbnail generation for visual file types | Could |

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Upload latency (50 MB file) | < 5 seconds |
| Search response time | < 500ms |
| Concurrent uploads per project | 10+ |
| Storage per project | 10 GB+ |
| Total storage | 500 GB+ |
| Presigned URL expiry | 15 minutes |

### Constraints

- **Storage backend:** RustFS (S3-compatible object storage in Rust, Apache 2.0)
- **S3 client:** boto3 (synchronous, per requirement)
- **Entity model:** SimpleEntityBase (no EVCS temporal versioning)
- **3 tables:** document_folders, documents, document_versions
- **Deployment:** Docker Compose, self-hosted, single-server
- **RBAC:** 3 new permissions (project-documents-read/write/delete)

---

## Context Discovery

### Product Scope

- Functional requirements document (Section 18.2) identifies "Document management systems (WebDAV)" as a future integration point -- this feature brings document management into the application natively
- Section 12.6 (AI Integration) requires AI-assisted read operations on all entity types -- documents are a natural extension
- Section 13.3 (Custom Reporting) requires data export -- documents attached to entities support richer reporting context

### Architecture Context

**Bounded contexts involved:**

- **Project Management** -- documents are project-scoped resources
- **Cost Management** -- CostRegistrationAttachment refactoring
- **AI/ML Integration** -- new AI tools for document search/read
- **EVCS Core** -- entity linking pattern (root IDs, not version PKs)

**Existing patterns to follow:**

- `SimpleEntityBase` + `SimpleService` for non-versioned entities (same as `CostRegistrationAttachment`)
- `ProjectRoleChecker` dependency for RBAC on API routes
- `@ai_tool` decorator with `ToolContext` injection for AI tools
- `PageNavigation` + `Outlet` pattern for entity detail tabs (seen in `WBELayout.tsx`, `CostElementLayout.tsx`)

**Architectural constraints:**

- No repository pattern -- services access the database directly via `AsyncSession`
- All versioned entities use root IDs for relationships (not version PKs)
- EVCS entity tiers: Simple / Versionable / Branchable -- documents are Simple

### Codebase Analysis

**Backend:**

Key files examined:

- `/backend/app/core/base/base.py` -- `SimpleEntityBase` provides `id`, `created_at`, `updated_at`
- `/backend/app/models/domain/cost_registration_attachment.py` -- existing BYTEA attachment model, `SimpleEntityBase` pattern
- `/backend/app/services/cost_registration_attachment_service.py` -- standard AsyncSession CRUD service
- `/backend/app/core/config.py` -- `COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB` setting (10 MB)
- `/backend/app/ai/file_extractors.py` -- PDF, DOCX, XLSX, PPTX text extraction (reusable for document indexing)
- `/backend/app/ai/tools/decorator.py` -- `@ai_tool` with `ToolContext`, `RiskLevel`, permission metadata
- `/backend/app/core/enums.py` -- `ProjectRole` enum with wildcard permission patterns (e.g., `project-*`)
- `/backend/app/core/simple/service.py` -- `SimpleService` generic CRUD base
- `/backend/seed/rbac_roles.json` -- global role definitions (admin, manager, viewer, ai-viewer, ai-manager, ai-admin, change_order_approver)

**Frontend:**

Key files examined:

- `/frontend/src/pages/projects/ProjectLayout.tsx` -- 11 tabs using `PageNavigation` + `Outlet` pattern
- `/frontend/src/pages/wbes/WBELayout.tsx` -- WBE detail with 4 tabs (Overview, EVM Analysis, Cost History, AI Chat) using `PageNavigation`
- `/frontend/src/pages/cost-elements/CostElementLayout.tsx` -- Cost element detail with 5 tabs (Overview, Cost Registrations, Cost History, EVM Analysis, AI Chat) using `PageNavigation`
- All entity layouts follow identical pattern: `navItems` array passed to `PageNavigation`, content rendered via `<Outlet />`

**Deployment:**

- `/docker-compose.dev.yml` -- PostgreSQL 15-alpine, backend, frontend, adminer on dev_network
- `/docker-compose.yml` -- PostgreSQL, backend (with Traefik), adminer
- Neither compose file includes any object storage service

---

## Critical Analysis Areas

### 1. RustFS Beta Status -- Risk Assessment

**Finding:** RustFS is explicitly **not production-ready** as stated on its Docker Hub page and README. It is under rapid development and features/APIs may change.

| Risk Factor | Assessment |
|-------------|------------|
| API stability | Beta -- S3 API may have gaps or changes |
| Data durability | Unproven at scale; no production track record |
| Community support | Small, growing; limited troubleshooting resources |
| Migration path | S3-compatible -- can switch to MinIO or another S3 backend later |
| Docker support | Single-node Docker deployment documented and working |

**Mitigation:** The S3 abstraction layer (`StorageService`) decouples the application from RustFS specifically. If RustFS proves unstable, the `StorageService` implementation can be swapped to MinIO, Garage, or any S3-compatible backend without changing business logic. The PostgreSQL metadata layer (folders, documents, versions, entity links) remains backend-agnostic.

**Recommendation:** Accept RustFS for development/evaluation. Design the `StorageService` with a clean interface so the storage backend is pluggable. Document the S3 API surface used so migration is straightforward if needed.

### 2. M:N Document-Entity Linking vs. EVCS Versioning

**Problem:** WBEs and cost elements are Branchable entities. They use root IDs (e.g., `wbe_id`, `cost_element_id`) as stable identifiers, not version PKs. Document links must reference these root IDs.

**Analysis:** The existing pattern throughout the codebase is clear -- relationships between versioned entities use root IDs. `CostRegistrationAttachment.cost_registration_id` references the root ID, with a comment: "References the stable root identity, not a specific version's PK. Integrity enforced at application level." Document links should follow the identical pattern.

**Design decision:**

```
document_entity_links
  document_id (FK -> documents.id)
  entity_type (VARCHAR: 'wbe', 'cost_element', 'change_order', 'project')
  entity_id (UUID: the root ID of the linked entity)
  note (TEXT, nullable)
```

- `entity_type` + `entity_id` form a polymorphic reference (no DB-level FK, integrity at application level -- same as existing patterns)
- Links reference root IDs, not version PKs
- A document linked to a WBE remains linked regardless of which version of the WBE is active
- Change orders are `SimpleEntityBase` (not versioned), so `entity_id` for change orders is the PK

**Implication for branch isolation:** If a change order creates a new WBE version, documents linked to that WBE root ID are visible on all branches where the WBE exists. If branch-scoped document visibility is needed (e.g., a document only visible within a CO branch), that would require adding `branch` to `document_entity_links` -- but this adds significant complexity and should be deferred unless there is a clear business requirement.

### 3. CostRegistrationAttachment Refactoring Strategy

**Current state:** `CostRegistrationAttachment` stores file content as BYTEA (raw bytes) in PostgreSQL. Max size 10 MB. Service does standard CRUD with `content` deferred in list queries.

**Target state:** `CostRegistrationAttachment` continues to exist as a domain model but delegates binary storage to `StorageService` backed by RustFS. The `content` BYTEA column is replaced by a `storage_key` string column.

**Migration strategy:**

| Phase | Action | Risk |
|-------|--------|------|
| Phase 1 | Add `storage_key` column (nullable) to `cost_registration_attachments` | Low |
| Phase 2 | Implement `StorageService` with RustFS backend | Low |
| Phase 3 | Modify `CostRegistrationAttachmentService` to use `StorageService` for new uploads | Medium |
| Phase 4 | Backfill migration: read BYTEA content, upload to RustFS, set `storage_key`, drop `content` column | Medium |
| Phase 5 | Remove BYTEA column in a subsequent migration | Low (after verification) |

**Key consideration:** The backfill (Phase 4) must be idempotent and resumable. For environments with no existing attachments, Phases 1-3 suffice and Phase 4 is a no-op. The migration script should be a separate Alembic migration that can be run independently.

**Alternative:** Keep `CostRegistrationAttachment` as-is (BYTEA) and only use RustFS for the new document repository. This avoids migration risk but perpetuates two storage patterns. Given the requirement explicitly asks for refactoring, the phased approach above is recommended.

### 4. Document Tab Placement in Entity Views

**Pattern established by codebase:** All entity detail layouts use `PageNavigation` with an array of `{ key, label, path }` items and render content via `<Outlet />`. Adding a "Documents" tab follows the exact same pattern.

**Tab placements:**

| Entity | Current Tabs | New Tab Position | Route |
|--------|-------------|-----------------|-------|
| Project | 11 tabs (Dashboard, Overview, Structure, Schedule, CO, Members, EVM, COQ, Work Packages, AI Chat, Admin) | After Work Packages, before AI Chat | `/projects/:projectId/documents` |
| WBE | 4 tabs (Overview, EVM Analysis, Cost History, AI Chat) | After Cost History, before AI Chat | `/projects/:projectId/wbes/:wbeId/documents` |
| Cost Element | 5 tabs (Overview, Cost Registrations, Cost History, EVM Analysis, AI Chat) | After EVM Analysis, before AI Chat | `/cost-elements/:id/documents` |

The document tab would be a shared component (`DocumentsTab`) that accepts a `projectId` and optional `entityType`/`entityId` filters. When rendered within an entity context (WBE, cost element), it filters documents linked to that entity. When rendered at the project level, it shows all project documents.

### 5. Data Model Validation Against SimpleEntityBase

**Proposed schema (3 tables + 1 join table):**

```
document_folders (SimpleEntityBase)
  id (PK, UUID)           -- inherited
  project_id (UUID, FK)   -- project scope
  parent_id (UUID, self FK, nullable)  -- hierarchy
  name (VARCHAR 255)
  path (VARCHAR 1024)     -- materialized path for fast lookups
  created_by (UUID)       -- user who created
  created_at (timestamp)  -- inherited
  updated_at (timestamp)  -- inherited

documents (SimpleEntityBase)
  id (PK, UUID)           -- inherited
  project_id (UUID, FK)   -- project scope
  folder_id (UUID, FK nullable)  -- folder membership
  name (VARCHAR 255)
  extension (VARCHAR 20)
  description (TEXT, nullable)
  tags (JSONB, default [])
  current_version_id (UUID, FK nullable)  -- convenience pointer
  is_locked (BOOLEAN, default false)
  locked_by (UUID, nullable)
  created_by (UUID)
  created_at (timestamp)  -- inherited
  updated_at (timestamp)  -- inherited

document_versions (SimpleEntityBase)
  id (PK, UUID)           -- inherited
  document_id (UUID, FK)  -- parent document
  version_number (INTEGER)
  storage_key (VARCHAR 512)  -- RustFS object key
  content_type (VARCHAR 100)
  size_bytes (INTEGER)
  checksum_sha256 (VARCHAR 64)
  extracted_text (TEXT, nullable)  -- for full-text search
  thumbnail_key (VARCHAR 512, nullable)
  uploaded_by (UUID)
  created_at (timestamp)  -- inherited
  updated_at (timestamp)  -- inherited

document_entity_links (SimpleEntityBase)
  id (PK, UUID)           -- inherited
  document_id (UUID, FK)
  entity_type (VARCHAR 50)  -- 'wbe', 'cost_element', 'change_order', 'project'
  entity_id (UUID)          -- root ID of the linked entity
  note (TEXT, nullable)
  created_at (timestamp)    -- inherited
  updated_at (timestamp)    -- inherited
```

**Validation:**

- All 4 tables use `SimpleEntityBase` -- consistent with the pattern
- No EVCS temporal fields (`valid_time`, `transaction_time`, `branch`) -- document versions are application-level numbered rows, not EVCS versions
- `document_versions.version_number` is an explicit counter, not the EVCS versioning mechanism
- No DB-level FK constraints on `entity_id` in `document_entity_links` -- matches the existing pattern for root ID references
- `document_folders.path` is a materialized path for efficient tree queries (e.g., `WHERE path LIKE '/project-uuid/folder-uuid/%'`)
- `extracted_text` on `document_versions` enables `pg_trgm` or `tsvector` full-text search without external search infrastructure

**Potential concern:** Storing `extracted_text` directly in PostgreSQL could cause table bloat for documents with large extracted text. Mitigation: use `TOAST` (PostgreSQL handles this automatically for TEXT columns > 2KB).

### 6. RBAC Permission Integration

**Current permission patterns:**

From `backend/app/core/enums.py`, project roles use wildcard patterns:

- `project_admin` gets `project-*` (all project permissions)
- `project_manager` gets `project-read`, `project-update` (specific permissions)

New permissions needed:

```
project-documents-read
project-documents-write
project-documents-delete
```

**Integration with `ProjectRole` enum (`backend/app/core/enums.py`):**

| Role | documents-read | documents-write | documents-delete |
|------|---------------|----------------|-----------------|
| project_admin | Y (via `project-*`) | Y (via `project-*`) | Y (via `project-*`) |
| project_manager | Explicit grant | Explicit grant | Explicit grant |
| project_editor | Explicit grant | Explicit grant | No |
| project_viewer | Explicit grant | No | No |

**Integration with global roles (`backend/seed/rbac_roles.json`):**

| Role | documents-read | documents-write | documents-delete |
|------|---------------|----------------|-----------------|
| admin | Y | Y | Y |
| manager | Y | Y | Y |
| viewer | Y | No | No |
| ai-viewer | Y | No | No |
| ai-manager | Y | Y | Y |
| ai-admin | Y | No | No |
| change_order_approver | Y | No | No |

**No conflicts identified** -- the new permissions slot cleanly into existing role structures. The `project_admin` wildcard pattern (`project-*`) already covers `project-documents-*` without code changes to the enum.

### 7. AI Tool Integration

Three new AI tools, following the established `@ai_tool` pattern:

| Tool | Permission | Risk Level | Category |
|------|-----------|------------|----------|
| `search_documents` | project-documents-read | LOW | documents |
| `read_document` | project-documents-read | LOW | documents |
| `list_documents` | project-documents-read | LOW | documents |

These tools use `ToolContext` injection (provides `session`, `user_id`, `project_id`) and follow the existing pattern in `backend/app/ai/tools/project_tools.py`. No conflicts with existing tool categories.

### 8. boto3 vs. aiobotocore

**Requirement specifies boto3.** Analysis of trade-offs:

| Aspect | boto3 (sync) | aiobotocore (async) |
|--------|-------------|-------------------|
| Async support | No -- requires `run_in_executor` | Native async |
| Maintenance | AWS-maintained, excellent | Community, less frequent updates |
| Compatibility | Full S3 API | Subset of S3 API |
| Performance in FastAPI | Blocking if not in executor | Non-blocking |
| Complexity | Lower | Higher (dependency on specific aiobotocore + boto3 version pairing) |

**Recommendation:** Use `boto3` as specified. Wrap S3 calls in `asyncio.to_thread()` to avoid blocking the event loop. This is the simpler approach and avoids the version-pairing headaches of `aiobotocore`. For a single-server deployment with moderate upload concurrency, `boto3` + `asyncio.to_thread()` is sufficient.

---

## Solution Options

### Option 1: RustFS with Phased CostRegistrationAttachment Migration

**Architecture and Design:**

- RustFS container added to both `docker-compose.dev.yml` and `docker-compose.yml`
- `StorageService` abstraction layer with RustFS implementation via `boto3`
- PostgreSQL metadata: 4 tables (`document_folders`, `documents`, `document_versions`, `document_entity_links`)
- Full-text search via PostgreSQL `pg_trgm` on `document_versions.extracted_text`
- `CostRegistrationAttachment` refactored in Phase 2 (BYTEA -> RustFS) with backfill migration

**User Experience:**

- New "Documents" tab in Project, WBE, and Cost Element layouts
- Folder tree sidebar + document grid in the main area
- Upload via drag-and-drop with progress indicators
- Version history accessible via document detail drawer
- Entity linking via modal (select entities to link, add optional note)

**Implementation:**

Backend:
- New `backend/app/services/storage_service.py` -- S3 abstraction with `upload`, `download`, `delete`, `generate_presigned_url`
- New `backend/app/models/domain/document_folder.py`, `document.py`, `document_version.py`, `document_entity_link.py`
- New `backend/app/services/document_service.py`, `document_version_service.py`
- New `backend/app/api/routes/documents.py` -- REST endpoints
- New `backend/app/ai/tools/document_tools.py` -- AI tools
- Modify `backend/app/core/config.py` -- add `RUSTFS_ENDPOINT`, `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY`, `RUSTFS_BUCKET_NAME`
- Modify `backend/app/core/enums.py` -- add `project-documents-*` permissions to `ProjectRole`
- Modify `backend/seed/rbac_roles.json` -- add `project-documents-*` to global roles
- Modify `backend/app/services/cost_registration_attachment_service.py` -- delegate to `StorageService`
- Alembic migration for 4 new tables + `storage_key` column on `cost_registration_attachments`

Frontend:
- New `frontend/src/features/documents/` feature folder
- New `DocumentsTab` component (shared across Project, WBE, Cost Element)
- New routes in router config
- TanStack Query hooks for document CRUD

Docker:
- Add `rustfs` service to both compose files

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | Single storage backend for all files; RustFS Apache 2.0 license avoids AGPL concerns; S3-compatible interface future-proofs the choice; CostRegistrationAttachment gets the same modern treatment |
| Cons | RustFS is beta -- risk of encountering bugs; adds operational complexity (one more container); backfill migration has risk for existing data |
| Complexity | High -- new infrastructure component + data migration + feature development |
| Maintainability | Good -- clean `StorageService` abstraction makes backend swappable |
| Performance | Good -- presigned URLs offload download traffic from backend; RustFS claims 2.3x faster than MinIO |

---

### Option 2: MinIO Hybrid (Proven S3 Backend)

**Architecture and Design:**

- Same architecture as Option 1 but uses MinIO instead of RustFS
- MinIO is the de facto standard for self-hosted S3-compatible storage
- AGPL v3.0 license -- using MinIO via API does not trigger copyleft (only modifying MinIO source would)
- All other aspects (PostgreSQL metadata, `StorageService`, entity linking, RBAC) are identical to Option 1

**User Experience:**

- Identical to Option 1

**Implementation:**

- Same backend/frontend code as Option 1 -- only the Docker service and config differ
- `StorageService` implementation uses MinIO endpoint instead of RustFS endpoint
- Config variable names change from `RUSTFS_*` to `S3_*` or `MINIO_*`

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | Production-proven with years of stable releases; massive community and documentation; mature web console for debugging; identical S3 API means zero code changes if switching later |
| Cons | AGPL v3.0 license (not a concern for API usage, but some organizations have policy restrictions); heavier container image than RustFS; separate web console is another thing to secure |
| Complexity | Medium -- MinIO is well-documented and straightforward to deploy |
| Maintainability | Good -- same `StorageService` abstraction |
| Performance | Good -- MinIO is battle-tested and performant at the scale Backcast needs |

---

### Option 3: Filesystem Storage with Future S3 Migration Path

**Architecture and Design:**

- Files stored on server filesystem (Docker volume mount) in a structured directory layout
- `StorageService` abstraction still implemented, but with a `FilesystemStorageBackend` instead of `S3StorageBackend`
- PostgreSQL metadata identical to Options 1 and 2
- No additional container needed -- files go into a named Docker volume
- `CostRegistrationAttachment` refactoring deferred (BYTEA stays for now)

**User Experience:**

- Identical to Options 1 and 2 from the user perspective

**Implementation:**

- `StorageService` with `FilesystemStorageBackend` using `aiofiles` for async file I/O
- No presigned URLs (not applicable to filesystem) -- download goes through the backend API
- All other backend/frontend code is the same

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | Zero infrastructure additions; simplest deployment; no beta software risk; no AGPL concerns; fastest to implement |
| Cons | No presigned URLs (all downloads proxied through backend); backup must be coordinated between DB and filesystem; no S3 ecosystem compatibility; migration to S3 later requires data movement |
| Complexity | Low |
| Maintainability | Fair -- filesystem storage is simpler but less portable |
| Performance | Fair -- no presigned URL offloading; backend handles all file streaming |

---

## Comparison Summary

| Criteria | Option 1: RustFS | Option 2: MinIO | Option 3: Filesystem |
|----------|-----------------|-----------------|---------------------|
| Development Effort | High (8-12 days) | High (8-12 days) | Medium (5-8 days) |
| Operational Complexity | High (beta software) | Low (proven) | Lowest |
| S3 Compatibility | Yes | Yes | No |
| Presigned URLs | Yes | Yes | No |
| License Risk | None (Apache 2.0) | Low (AGPL, API usage OK) | None |
| Production Readiness | Low (beta) | High | Medium |
| CostRegistration Refactor | Included | Included | Deferred |
| Future-Proofing | Good (S3 API) | Good (S3 API) | Poor (needs migration) |

---

## Recommendation

**I recommend Option 2 (MinIO Hybrid)** because:

1. **Production safety:** MinIO is battle-tested with years of stable releases. Backcast is a business-critical application for project budget management -- it cannot afford data loss or downtime from beta storage software.
2. **S3 compatibility:** Full S3 API support means the `StorageService` abstraction is genuinely portable. If RustFS matures or another S3 backend becomes preferable, the swap is a config change.
3. **AGPL is not a concern:** Using MinIO as an external service via its S3 API does not trigger AGPL copyleft obligations. The application does not embed, link to, or modify MinIO source code.
4. **Same feature set:** The user gets presigned URLs, multipart uploads, versioning, lifecycle policies -- everything RustFS promises but proven.
5. **CostRegistrationAttachment migration** proceeds as planned.

**Alternative consideration:** If the team has a firm organizational policy against AGPL software (even as an API client), Option 3 (Filesystem) delivers the document management feature without any licensing concerns, at the cost of presigned URLs and S3 ecosystem compatibility. The `StorageService` abstraction ensures migration to an S3 backend later is straightforward.

**Regarding the user's RustFS preference:** The `StorageService` abstraction means the application is decoupled from the specific S3 backend. If RustFS reaches production readiness in a future release cycle, the migration from MinIO to RustFS is a deployment change (swap the container, update the endpoint config) with zero application code changes. The analysis strongly advises against using beta storage software for business-critical data at this time.

---

## Decision Questions

1. **Storage backend:** Is the team comfortable with MinIO (AGPL, API usage only) as the production storage backend, or is there an organizational policy that requires Apache 2.0-only dependencies?

2. **Branch-scoped documents:** Do change orders need to isolate their own document changes (e.g., a revised drawing visible only within a CO branch), or is it sufficient that documents are linked at the root entity level and visible across all branches?

3. **CostRegistrationAttachment migration scope:** Should the BYTEA-to-S3 migration be included in the first iteration, or should the document repository be shipped first with the attachment migration as a follow-up iteration?

4. **Full-text search depth:** Should `pg_trgm` (trigram matching, simple setup, handles typos) be used, or is `tsvector` (word-level indexing, better for large corpora, requires language configuration) preferred?

5. **First iteration scope:** The "Could" priority items (inline preview, thumbnails, storage quotas, bulk upload/download) -- should any of these be included in v1?

---

## References

- `/backend/app/core/base/base.py` -- SimpleEntityBase, EntityBase definitions
- `/backend/app/models/domain/cost_registration_attachment.py` -- existing BYTEA attachment model
- `/backend/app/services/cost_registration_attachment_service.py` -- existing attachment service
- `/backend/app/ai/file_extractors.py` -- text extraction for PDF, DOCX, XLSX, PPTX
- `/backend/app/ai/tools/decorator.py` -- @ai_tool decorator pattern
- `/backend/app/core/enums.py` -- ProjectRole enum with permission patterns
- `/backend/seed/rbac_roles.json` -- global role definitions
- `/frontend/src/pages/projects/ProjectLayout.tsx` -- project tab navigation (11 tabs)
- `/frontend/src/pages/wbes/WBELayout.tsx` -- WBE detail layout with tabs
- `/frontend/src/pages/cost-elements/CostElementLayout.tsx` -- cost element detail layout with tabs
- `/docker-compose.dev.yml` -- development Docker Compose
- `/docker-compose.yml` -- production Docker Compose
- `/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md` -- EVCS entity tier guide
- `/docs/01-product-scope/functional-requirements.md` -- product functional requirements
- Existing analysis: `docs/03-project-plan/iterations/2026-05-25-document-repository/00-analysis.md`
