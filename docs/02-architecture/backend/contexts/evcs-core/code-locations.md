# EVCS Core Code Locations

**Last Updated:** 2026-04-14
**Context:** [EVCS Core Architecture](architecture.md)

This document provides a reference to all code files implementing the EVCS Core functionality.

---

## Core Framework

### Base Model

| File                                                            | Description                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`app/core/base/base.py`](../../../../../backend/app/core/base/base.py) | `EntityBase` and `SimpleEntityBase` abstract classes |
| [`app/models/mixins.py`](../../../../../backend/app/models/mixins.py) | `VersionableMixin` and `BranchableMixin` for temporal composition |

**Key Classes:**

- `EntityBase` - Abstract base for all entities (provides UUID primary key)
- `SimpleEntityBase` - Non-versioned entities with `created_at`/`updated_at` (extends `EntityBase`)
- `VersionableMixin` - Adds bitemporal fields (`valid_time`, `transaction_time`, `deleted_at`)
- `BranchableMixin` - Adds branching fields (`branch`, `parent_id`, `merge_from_branch`)

---

### Generic Commands

| File                                                                                                              | Description                                       |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [`app/core/versioning/commands.py`](../../../../../../backend/app/core/versioning/commands.py) | Generic command classes for versioning operations |

**Key Classes:**

- `CreateVersionCommand[T]` - Create new entity version
- `UpdateVersionCommand[T]` - Update entity (creates new version)
- `SoftDeleteCommand[T]` - Soft delete entity
- `CommandMetadata` - Metadata dataclass for audit

---

### Generic Service

| File                                                                                                            | Description                              |
| --------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/versioning/service.py`](../../../../../../backend/app/core/versioning/service.py) | Base service class for temporal entities |

**Key Classes:**

- `TemporalService[T]` - Generic service with all CRUD/branch operations

---

## Branching Framework

### Branching Commands

| File                                                                                                            | Description                             |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| [`app/core/branching/commands.py`](../../../../../../backend/app/core/branching/commands.py) | Command classes for branchable entities |

**Key Classes:**

- `CreateBranchCommand[T]` - Create new branch
- `UpdateCommand[T]` - Update entity on branch
- `MergeBranchCommand[T]` - Merge branches
- `RevertCommand[T]` - Revert to previous version

### Branching Service

| File                                                                                                          | Description                           |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| [`app/core/branching/service.py`](../../../../../../backend/app/core/branching/service.py) | Service class for branchable entities |

**Key Classes:**

- `BranchableService[T]` - Combines `TemporalService` with branch operations (create, merge, revert)

---

## Non-Versioned Entity Framework

### Simple Base Model

| File                                                                                           | Description                              |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/base/base.py`](../../../../../../backend/app/core/base/base.py) | `SimpleEntityBase` for non-versioned entities |

**Key Classes:**

- `SimpleEntityBase` - Abstract base with `id`, `created_at`, `updated_at`

---

### Simple Commands

| File                                                                                                      | Description                         |
| --------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| [`app/core/simple/commands.py`](../../../../../../backend/app/core/simple/commands.py) | Commands for non-versioned entities |

**Key Classes:**

- `SimpleCreateCommand[T]` - Create entity
- `SimpleUpdateCommand[T]` - Update entity in place
- `SimpleDeleteCommand[T]` - Hard delete entity

---

### Simple Service

| File                                                                                                  | Description                              |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/simple/service.py`](../../../../../../backend/app/core/simple/service.py) | Base service for non-versioned entities |

**Key Classes:**

- `SimpleService[T]` - Generic service with CRUD operations

---

### Non-Versioned Entity Examples

| File                                                                                                                          | Description              |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| [`app/models/domain/user_preferences.py`](../../../../../../backend/app/models/domain/user_preferences.py) | `UserPreferences` model  |
| [`app/models/domain/system_config.py`](../../../../../../backend/app/models/domain/system_config.py)       | `SystemConfig` model     |
| [`app/services/user_preferences.py`](../../../../../../backend/app/services/user_preferences.py)           | `UserPreferencesService` |
| [`app/services/system_config.py`](../../../../../../backend/app/services/system_config.py)                 | `SystemConfigService`    |

---

## Entity Implementations

### Project

| File                                                                                                        | Description                                  |
| ----------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [`app/models/domain/project.py`](../../../../../../backend/app/models/domain/project.py) | `ProjectVersion` model                       |
| [`app/services/project.py`](../../../../../../backend/app/services/project.py)           | `ProjectService` (extends `TemporalService`) |
| [`app/api/routes/projects.py`](../../../../../../backend/app/api/routes/projects.py)     | Project API endpoints                        |

---

### WBE (Work Breakdown Element)

| File                                                                                                | Description                              |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/models/domain/wbe.py`](../../../../../../backend/app/models/domain/wbe.py) | `WBEVersion` model                       |
| [`app/services/wbe.py`](../../../../../../backend/app/services/wbe.py)           | `WBEService` (extends `TemporalService`) |
| [`app/api/routes/wbes.py`](../../../../../../backend/app/api/routes/wbes.py)     | WBE API endpoints                        |

---

### Cost Element

| File                                                                                                                  | Description                                      |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [`app/models/domain/cost_element.py`](../../../../../../backend/app/models/domain/cost_element.py) | `CostElementVersion` model                       |
| [`app/services/cost_element.py`](../../../../../../backend/app/services/cost_element.py)           | `CostElementService` (extends `TemporalService`) |
| [`app/api/routes/cost_elements.py`](../../../../../../backend/app/api/routes/cost_elements.py)     | Cost Element API endpoints                       |

---

### AI (Non-Versioned)

| File                                                                                              | Description                        |
| ------------------------------------------------------------------------------------------------- | ---------------------------------- |
| [`app/models/domain/ai.py`](../../../../../../backend/app/models/domain/ai.py)                    | AI-related models                  |
| [`app/services/ai_config_service.py`](../../../../../../backend/app/services/ai_config_service.py) | AI configuration service           |

**Key Entities:**

- `AIProvider` - AI provider configuration (OpenAI, Anthropic, etc.)
- `AIProviderConfig` - Provider-specific configuration (API keys, endpoints)
- `AIModel` - AI model definitions
- `AIAssistantConfig` - Assistant system prompts and settings
- `AIConversationSession` - Chat session management
- `AIConversationMessage` - Individual messages within sessions
- `AIConversationAttachment` - File attachments (images, documents)
- `AIAgentExecution` - Agent execution tracking

---

## Pydantic Schemas

### Base Schemas

| File                                                                                                            | Description                                 |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [`app/models/schemas/temporal.py`](../../../../../../backend/app/models/schemas/temporal.py) | Base Pydantic schemas for temporal entities |

**Key Schemas:**

- `TemporalCreate` - Base create schema
- `TemporalUpdate` - Base update schema
- `TemporalRead` - Base read schema with temporal fields

---

## Database Migrations

| File                                                                                  | Description         |
| ------------------------------------------------------------------------------------- | ------------------- |
| [`alembic/versions/`](../../../../../../backend/alembic/versions/) | All migration files |

**Key Migration Patterns:**

- Create version tables with TSTZRANGE columns
- Add GIST indexes for temporal queries
- Create partial unique indexes for current versions

---

## Configuration

| File                                                                                    | Description              |
| --------------------------------------------------------------------------------------- | ------------------------ |
| [`app/core/config.py`](../../../../../../backend/app/core/config.py) | Application settings     |
| [`app/db/session.py`](../../../../../../backend/app/db/session.py)   | Database session factory |

---

## Directory Structure

```
backend/app/
├── core/
│   ├── base/
│   │   └── base.py              # EntityBase, SimpleEntityBase
│   ├── versioning/              # Temporal versioning framework
│   │   ├── __init__.py
│   │   ├── commands.py          # Create/Update/SoftDelete commands
│   │   └── service.py           # TemporalService[T]
│   ├── branching/               # Branching framework
│   │   ├── __init__.py
│   │   ├── commands.py          # CreateBranch/Merge/Revert commands
│   │   └── service.py           # BranchableService[T]
│   └── simple/                  # Non-versioned entity framework
│       ├── __init__.py
│       ├── commands.py          # Simple commands
│       └── service.py           # SimpleService[T]
├── models/
│   ├── mixins.py                # VersionableMixin, BranchableMixin
│   ├── protocols.py             # EntityProtocol, VersionableProtocol, etc.
│   ├── domain/
│   │   ├── project.py               # Project (versioned)
│   │   ├── wbe.py                   # WBE (versioned)
│   │   ├── cost_element.py          # CostElement (versioned)
│   │   ├── cost_element_type.py     # CostElementType (versioned)
│   │   ├── department.py            # Department (versioned)
│   │   ├── user.py                  # User (versioned)
│   │   ├── change_order.py          # ChangeOrder (versioned, branchable)
│   │   ├── change_order_audit_log.py # ChangeOrderAuditLog (non-versioned)
│   │   ├── schedule_baseline.py     # ScheduleBaseline (versioned, 1:1 with project)
│   │   ├── forecast.py              # Forecast (versioned)
│   │   ├── branch.py                # Branch (non-versioned)
│   │   ├── progress_entry.py        # ProgressEntry (versioned)
│   │   ├── cost_registration.py     # CostRegistration (versioned)
│   │   ├── project_member.py        # ProjectMember (non-versioned)
│   │   ├── refresh_token.py         # RefreshToken (non-versioned)
│   │   ├── dashboard_layout.py      # DashboardLayout (non-versioned)
│   │   └── ai.py                    # AI entities (all non-versioned)
│   └── schemas/
│       └── ...                      # Pydantic schemas
├── services/
│   ├── project.py                   # ProjectService
│   ├── wbe.py                       # WBEService
│   ├── cost_element.py              # CostElementService
│   ├── cost_element_type.py         # CostElementTypeService
│   ├── department.py                # DepartmentService
│   ├── user.py                      # UserService
│   ├── change_order_service.py      # ChangeOrderService
│   ├── change_order_workflow_service.py # ChangeOrderWorkflowService
│   ├── change_order_reporting_service.py # ChangeOrderReportingService
│   ├── schedule_baseline_service.py # ScheduleBaselineService
│   ├── forecast_service.py          # ForecastService
│   ├── gantt_service.py             # GanttService
│   ├── dashboard_service.py         # DashboardService
│   ├── dashboard_layout_service.py  # DashboardLayoutService
│   ├── cost_registration_service.py # CostRegistrationService
│   ├── progress_entry_service.py    # ProgressEntryService
│   ├── impact_analysis_service.py   # ImpactAnalysisService
│   ├── financial_impact_service.py  # FinancialImpactService
│   ├── approval_matrix_service.py   # ApprovalMatrixService
│   ├── sla_service.py               # SLAService
│   ├── branch_service.py            # BranchService
│   ├── entity_discovery_service.py  # EntityDiscoveryService
│   ├── evm_service.py               # EVM calculations
│   └── ai_config_service.py         # AIConfigService
└── api/
    └── routes/
        ├── projects.py              # /api/v1/projects
        ├── wbes.py                  # /api/v1/wbes
        └── cost_elements.py         # /api/v1/cost-elements
```

---

## See Also

- [EVCS Core Architecture](architecture.md)
- [EVCS Implementation Guide](evcs-implementation-guide.md) - Code patterns and recipes
- [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md) - Bitemporal queries and time travel
