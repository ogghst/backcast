# EVCS Core Code Locations

**Last Updated:** 2026-01-01  
**Context:** [EVCS Core Architecture](architecture.md)

This document provides a reference to all code files implementing the EVCS Core functionality.

> [!IMPORTANT] > **Target Architecture:** This document describes the planned file structure for the new versioning system.
> Some files may not exist yet and will be created during the migration from the current dual-table pattern.
> See [ADR-005](../../decisions/ADR-005-bitemporal-versioning.md) for migration notes.

---

## Core Framework

### Base Model

| File                                                                                    | Description                                                        |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`app/core/base/base.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/base/base.py) | `EntityBase` and `SimpleEntityBase` abstract classes |
| [`app/models/mixins.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/mixins.py) | `VersionableMixin` and `BranchableMixin` for temporal composition |

**Key Classes:**

- `EntityBase` - Abstract base for all entities (provides ID)
- `SimpleEntityBase` - Non-versioned entities with `created_at`/`updated_at`
- `VersionableMixin` - Adds bitemporal fields (`valid_time`, `transaction_time`, `deleted_at`)
- `BranchableMixin` - Adds branching fields (`branch`, `parent_id`, `merge_from_branch`)

---

### Generic Commands

| File                                                                                                              | Description                                       |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [`app/core/versioning/commands.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/versioning/commands.py) | Generic command classes for versioning operations |

**Key Classes:**

- `CreateVersionCommand[T]` - Create new entity version
- `UpdateVersionCommand[T]` - Update entity (creates new version)
- `SoftDeleteCommand[T]` - Soft delete entity
- `CommandMetadata` - Metadata dataclass for audit

---

### Generic Service

| File                                                                                                            | Description                              |
| --------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/versioning/service.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/versioning/service.py) | Base service class for temporal entities |

**Key Classes:**

- `TemporalService[T]` - Generic service with all CRUD/branch operations

---

## Branching Framework

### Branching Commands

| File                                                                                                            | Description                             |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| [`app/core/branching/commands.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/branching/commands.py) | Command classes for branchable entities |

**Key Classes:**

- `CreateBranchCommand[T]` - Create new branch
- `UpdateCommand[T]` - Update entity on branch
- `MergeBranchCommand[T]` - Merge branches
- `RevertCommand[T]` - Revert to previous version

### Branching Service

| File                                                                                                          | Description                           |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| [`app/core/branching/service.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/branching/service.py) | Service class for branchable entities |

**Key Classes:**

- `BranchableService[T]` - Service for full EVCS operations

---

## Non-Versioned Entity Framework

### Simple Base Model

| File                                                                                           | Description                              |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/base/base.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/base/base.py) | `SimpleEntityBase` for non-versioned entities |

**Key Classes:**

- `SimpleEntityBase` - Abstract base with `id`, `created_at`, `updated_at`

---

### Simple Commands

| File                                                                                                      | Description                         |
| --------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| [`app/core/simple/commands.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/simple/commands.py) | Commands for non-versioned entities |

**Key Classes:**

- `SimpleCreateCommand[T]` - Create entity
- `SimpleUpdateCommand[T]` - Update entity in place
- `SimpleDeleteCommand[T]` - Hard delete entity

---

### Simple Service

| File                                                                                                  | Description                              |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/core/simple/service.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/simple/service.py) | Base service for non-versioned entities |

**Key Classes:**

- `SimpleService[T]` - Generic service with CRUD operations

---

### Non-Versioned Entity Examples

| File                                                                                                                          | Description              |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| [`app/models/domain/user_preferences.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/user_preferences.py) | `UserPreferences` model  |
| [`app/models/domain/system_config.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/system_config.py)       | `SystemConfig` model     |
| [`app/services/user_preferences.py`](file:///home/nicola/dev/backcast_evs/backend/app/services/user_preferences.py)           | `UserPreferencesService` |
| [`app/services/system_config.py`](file:///home/nicola/dev/backcast_evs/backend/app/services/system_config.py)                 | `SystemConfigService`    |

---

## Entity Implementations

### Project

| File                                                                                                        | Description                                  |
| ----------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [`app/models/domain/project.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/project.py) | `ProjectVersion` model                       |
| [`app/services/project.py`](file:///home/nicola/dev/backcast_evs/backend/app/services/project.py)           | `ProjectService` (extends `TemporalService`) |
| [`app/api/routes/projects.py`](file:///home/nicola/dev/backcast_evs/backend/app/api/routes/projects.py)     | Project API endpoints                        |

---

### WBE (Work Breakdown Element)

| File                                                                                                | Description                              |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [`app/models/domain/wbe.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/wbe.py) | `WBEVersion` model                       |
| [`app/services/wbe.py`](file:///home/nicola/dev/backcast_evs/backend/app/services/wbe.py)           | `WBEService` (extends `TemporalService`) |
| [`app/api/routes/wbes.py`](file:///home/nicola/dev/backcast_evs/backend/app/api/routes/wbes.py)     | WBE API endpoints                        |

---

### Cost Element

| File                                                                                                                  | Description                                      |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [`app/models/domain/cost_element.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/domain/cost_element.py) | `CostElementVersion` model                       |
| [`app/services/cost_element.py`](file:///home/nicola/dev/backcast_evs/backend/app/services/cost_element.py)           | `CostElementService` (extends `TemporalService`) |
| [`app/api/routes/cost_elements.py`](file:///home/nicola/dev/backcast_evs/backend/app/api/routes/cost_elements.py)     | Cost Element API endpoints                       |

---

## Pydantic Schemas

### Base Schemas

| File                                                                                                            | Description                                 |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [`app/models/schemas/temporal.py`](file:///home/nicola/dev/backcast_evs/backend/app/models/schemas/temporal.py) | Base Pydantic schemas for temporal entities |

**Key Schemas:**

- `TemporalCreate` - Base create schema
- `TemporalUpdate` - Base update schema
- `TemporalRead` - Base read schema with temporal fields

---

## Database Migrations

| File                                                                                  | Description         |
| ------------------------------------------------------------------------------------- | ------------------- |
| [`alembic/versions/`](file:///home/nicola/dev/backcast_evs/backend/alembic/versions/) | All migration files |

**Key Migration Patterns:**

- Create version tables with TSTZRANGE columns
- Add GIST indexes for temporal queries
- Create partial unique indexes for current versions

---

## Tests

### Unit Tests

| File                                                                                                                                | Description               |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| [`tests/unit/core/test_temporal_base.py`](file:///home/nicola/dev/backcast_evs/backend/tests/unit/core/test_temporal_base.py)       | TemporalBase method tests |
| [`tests/unit/core/test_commands.py`](file:///home/nicola/dev/backcast_evs/backend/tests/unit/core/test_commands.py)                 | Generic command tests     |
| [`tests/unit/core/test_temporal_service.py`](file:///home/nicola/dev/backcast_evs/backend/tests/unit/core/test_temporal_service.py) | TemporalService tests     |

### Integration Tests

| File                                                                                                                              | Description             |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| [`tests/integration/test_temporal_crud.py`](file:///home/nicola/dev/backcast_evs/backend/tests/integration/test_temporal_crud.py) | CRUD integration tests  |
| [`tests/integration/test_branching.py`](file:///home/nicola/dev/backcast_evs/backend/tests/integration/test_branching.py)         | Branch operation tests  |
| [`tests/integration/test_time_travel.py`](file:///home/nicola/dev/backcast_evs/backend/tests/integration/test_time_travel.py)     | Time travel query tests |

### API Tests

| File                                                                                                    | Description                |
| ------------------------------------------------------------------------------------------------------- | -------------------------- |
| [`tests/api/test_projects.py`](file:///home/nicola/dev/backcast_evs/backend/tests/api/test_projects.py) | Project API endpoint tests |
| [`tests/api/test_wbes.py`](file:///home/nicola/dev/backcast_evs/backend/tests/api/test_wbes.py)         | WBE API endpoint tests     |

---

## Configuration

| File                                                                                    | Description              |
| --------------------------------------------------------------------------------------- | ------------------------ |
| [`app/core/config.py`](file:///home/nicola/dev/backcast_evs/backend/app/core/config.py) | Application settings     |
| [`app/db/session.py`](file:///home/nicola/dev/backcast_evs/backend/app/db/session.py)   | Database session factory |

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
│   │   ├── project.py           # Project (EntityBase + mixins)
│   │   ├── wbe.py               # WBE (EntityBase + mixins)
│   │   ├── cost_element.py      # CostElement (EntityBase + mixins)
│   │   ├── cost_element_type.py # CostElementType (EntityBase + mixins)
│   │   ├── department.py        # Department (EntityBase + mixins)
│   │   └── user.py              # User (EntityBase + mixins)
│   └── schemas/
│       └── ...                  # Pydantic schemas
├── services/
│   ├── project.py               # ProjectService (extends TemporalService)
│   ├── wbe.py                   # WBEService (extends TemporalService)
│   ├── cost_element.py          # CostElementService (extends TemporalService)
│   ├── cost_element_type.py     # CostElementTypeService
│   ├── department.py            # DepartmentService
│   └── user.py                  # UserService
└── api/
    └── routes/
        ├── projects.py          # /api/v1/projects
        ├── wbes.py              # /api/v1/wbes
        └── cost_elements.py     # /api/v1/cost-elements
```

---

## See Also

- [EVCS Core Architecture](architecture.md)
- [EVCS Implementation Guide](evcs-implementation-guide.md) - Code patterns and recipes
- [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md) - Bitemporal queries and time travel
