# EVCS Core Code Locations

**Last Updated:** 2026-07-01
**Context:** [EVCS Core Architecture](architecture.md)

This document is a navigation index to the code implementing EVCS Core (the
versioning / branching framework) and the domain entities built on top of it.
Every file listed below was verified against the live `backend/app/` tree.

> **Convention:** API route modules live under `app/api/routes/` (there is no
> `app/api/v1/` package on disk — the `/api/v1` URL prefix is applied by the
> router, not by the directory layout).

---

## Core Framework

### Base Model

| File | Description |
| ---- | ----------- |
| [`app/core/base/base.py`](../../../../../backend/app/core/base/base.py) | `EntityBase` and `SimpleEntityBase` abstract classes |
| [`app/models/mixins.py`](../../../../../backend/app/models/mixins.py) | `VersionableMixin` and `BranchableMixin` for temporal composition |
| [`app/models/protocols.py`](../../../../../backend/app/models/protocols.py) | `EntityProtocol`, `VersionableProtocol`, etc. (structural typing) |

**Key Classes:**

- `EntityBase` - Abstract base for all entities (provides UUID primary key)
- `SimpleEntityBase` - Non-versioned entities with `created_at`/`updated_at` (extends `EntityBase`)
- `VersionableMixin` - Adds bitemporal fields (`valid_time`, `transaction_time`, `deleted_at`)
- `BranchableMixin` - Adds branching fields (`branch`, `parent_id`, `merge_from_branch`)

---

### Generic Commands & Service (Versioning)

| File | Description |
| ---- | ----------- |
| [`app/core/versioning/commands.py`](../../../../../backend/app/core/versioning/commands.py) | Generic command classes for versioning operations |
| [`app/core/versioning/service.py`](../../../../../backend/app/core/versioning/service.py) | `TemporalService[T]` — base service for temporal entities |
| [`app/core/versioning/enums.py`](../../../../../backend/app/core/versioning/enums.py) | Versioning enums |
| [`app/core/versioning/exceptions.py`](../../../../../backend/app/core/versioning/exceptions.py) | Versioning-domain exceptions |
| [`app/core/versioning/creator_resolver.py`](../../../../../backend/app/core/versioning/creator_resolver.py) | Resolves the creator/actor for audit attribution |

**Key Classes:**

- `CreateVersionCommand[T]` - Create new entity version
- `UpdateVersionCommand[T]` - Update entity (creates new version)
- `SoftDeleteCommand[T]` - Soft delete entity
- `CommandMetadata` - Metadata dataclass for audit
- `TemporalService[T]` - Generic service with all CRUD/temporal operations

---

## Branching Framework

### Branching Commands & Service

| File | Description |
| ---- | ----------- |
| [`app/core/branching/commands.py`](../../../../../backend/app/core/branching/commands.py) | Command classes for branchable entities |
| [`app/core/branching/service.py`](../../../../../backend/app/core/branching/service.py) | `BranchableService[T]` for branchable entities |
| [`app/core/branching/exceptions.py`](../../../../../backend/app/core/branching/exceptions.py) | Branching-domain exceptions |

**Key Classes:**

- `CreateBranchCommand[T]` - Create new branch
- `UpdateCommand[T]` - Update entity on branch
- `MergeBranchCommand[T]` - Merge branches
- `RevertCommand[T]` - Revert to previous version
- `BranchableService[T]` - Combines `TemporalService` with branch operations (create, merge, revert)

---

## Non-Versioned (Simple) Entity Framework

| File | Description |
| ---- | ----------- |
| [`app/core/base/base.py`](../../../../../backend/app/core/base/base.py) | `SimpleEntityBase` for non-versioned entities |
| [`app/core/simple/commands.py`](../../../../../backend/app/core/simple/commands.py) | `SimpleCreateCommand[T]`, `SimpleUpdateCommand[T]`, `SimpleDeleteCommand[T]` |
| [`app/core/simple/service.py`](../../../../../backend/app/core/simple/service.py) | `SimpleService[T]` — generic CRUD for non-versioned entities |

**Key Classes:**

- `SimpleEntityBase` - Abstract base with `id`, `created_at`, `updated_at`
- `SimpleCreateCommand[T]` / `SimpleUpdateCommand[T]` / `SimpleDeleteCommand[T]`
- `SimpleService[T]` - Generic service with CRUD operations

> **Note:** Earlier revisions of this doc listed `user_preferences.py` and
> `system_config.py` as simple-entity examples. Neither file exists in the
> codebase. Real simple-entity examples include the AI entities, `RefreshToken`,
> `Branch`, `DashboardLayout`, and the notification models (see tables below).

---

## Entity Implementations (Versioned)

Each versioned entity exposes a model under `app/models/domain/`, a service
under `app/services/`, and (where applicable) an API router under
`app/api/routes/`. The three versioned + branchable entities are `Project`,
`WBSElement`, and `CostElement`; the remainder are versioned-only or simple.

### Project (versioned + branchable)

| File | Description |
| ---- | ----------- |
| [`app/models/domain/project.py`](../../../../../backend/app/models/domain/project.py) | `ProjectVersion` model |
| [`app/services/project.py`](../../../../../backend/app/services/project.py) | `ProjectService` (extends `BranchableService`) |
| [`app/api/routes/projects.py`](../../../../../backend/app/api/routes/projects.py) | Project API endpoints |

### WBS Element (versioned + branchable)

| File | Description |
| ---- | ----------- |
| [`app/models/domain/wbs_element.py`](../../../../../backend/app/models/domain/wbs_element.py) | `WBSElementVersion` model |
| [`app/services/wbs_element_service.py`](../../../../../backend/app/services/wbs_element_service.py) | `WBSElementService` (extends `BranchableService`) |
| [`app/api/routes/wbs_elements.py`](../../../../../backend/app/api/routes/wbs_elements.py) | WBS Element API endpoints |

### Cost Element (versioned + branchable)

| File | Description |
| ---- | ----------- |
| [`app/models/domain/cost_element.py`](../../../../../backend/app/models/domain/cost_element.py) | `CostElementVersion` model |
| [`app/services/cost_element_service.py`](../../../../../backend/app/services/cost_element_service.py) | `CostElementService` (extends `BranchableService`) |
| [`app/api/routes/cost_elements.py`](../../../../../backend/app/api/routes/cost_elements.py) | Cost Element API endpoints |

### Other Domain Entities (models + services + routes)

These share the same model → service → route layout. Listed by domain file.

| Domain model (`app/models/domain/`) | Service (`app/services/`) | Route (`app/api/routes/`) |
| ------------------------------------ | ------------------------- | ------------------------- |
| `cost_element_type.py` | `cost_element_type_service.py` | `cost_element_types.py` |
| `control_account.py` | `control_account_service.py` | `control_accounts.py` |
| `work_package.py` | `work_package_service.py` | `work_packages.py` |
| `cost_event.py` | `cost_event_service.py` | `cost_events.py` |
| `cost_event_type.py` | `cost_event_type_service.py` | `cost_event_types.py` |
| `cost_registration.py` | `cost_registration_service.py` | `cost_registrations.py` |
| `cost_registration_attachment.py` | `cost_registration_attachment_service.py` | `cost_registration_attachments.py` |
| `progress_entry.py` | `progress_entry_service.py` | `progress_entries.py` |
| `forecast.py` | `forecast_service.py` | `forecasts.py` |
| `schedule_baseline.py` | `schedule_baseline_service.py` | `schedule_baselines.py` |
| `schedule_dependency.py` | `schedule_dependency_service.py` | `schedule_dependencies.py` |
| `change_order.py` | `change_order_service.py` | `change_orders.py` |
| `change_order_config.py` | `change_order_config_service.py` | `change_order_config.py` |
| `change_order_audit_log.py` | `change_order_reporting_service.py` / `change_order_workflow_service.py` / `change_order_workflow_validation.py` | `change_orders.py` |
| `organizational_unit.py` | `organizational_unit_service.py` | `organizational_units.py` |
| `customer.py` | `customer_service.py` | `customers.py` |
| `currency_rate.py` | `currency_rate_service.py` | `currency_rates.py` |
| `user.py` | `user.py` | `users.py` |
| `user_role_assignment.py` | `rbac_admin_service.py` | `user_role_assignments.py` / `rbac_admin.py` |
| `project_budget_settings.py` | `project_budget_settings_service.py` | `project_budget_settings.py` |
| `branch.py` (non-versioned) | `branch_service.py` | — (via change-order routes) |

**Supporting services** (no direct 1:1 model/route, or shared):

| File | Description |
| ---- | ----------- |
| `impact_analysis_service.py`, `financial_impact_service.py` | CO impact analysis |
| `gantt_service.py` | Schedule/Gantt aggregation (route: `gantt.py`) |
| `evm_service.py` | Earned Value Management calculations (route: `evm.py`) |
| `dashboard_service.py` | Dashboard widget data (route: `dashboard.py`) |
| `dashboard_layout_service.py` | Dashboard layout persistence (route: `dashboard_layouts.py`) |
| `entity_discovery_service.py` | Dynamic entity/schema discovery (used by AI + search) |
| `global_search_service.py` | Cross-entity search (route: `search.py`) |
| `sla_service.py` | SLA / approval-timeout enforcement |
| `system_admin_service.py` | System-admin configuration (route: `system_admin.py`) |
| `auth.py` / `storage_service.py` | Auth flow + file storage |

---

## Custom Fields

The custom-fields initiative introduced an OO field-definitions package plus a
service and template entity.

| File | Description |
| ---- | ----------- |
| [`app/models/custom_fields/base.py`](../../../../../backend/app/models/custom_fields/base.py) | `FieldDefinition` abstract base |
| [`app/models/custom_fields/fields.py`](../../../../../backend/app/models/custom_fields/fields.py) | Concrete field types (text, number, select, date, …) |
| [`app/models/custom_fields/registry.py`](../../../../../backend/app/models/custom_fields/registry.py) | Field-type registry (name → class) |
| [`app/models/custom_fields/__init__.py`](../../../../../backend/app/models/custom_fields/__init__.py) | Package exports |
| [`app/models/domain/custom_entity_template.py`](../../../../../backend/app/models/domain/custom_entity_template.py) | `CustomEntityTemplate` model (admin-defined templates) |
| [`app/services/custom_field_service.py`](../../../../../backend/app/services/custom_field_service.py) | Custom-field value read/write (rides EVCS `custom_fields` JSONB column) |
| [`app/services/custom_entity_template_service.py`](../../../../../backend/app/services/custom_entity_template_service.py) | Template CRUD |
| [`app/api/routes/custom_entity_templates.py`](../../../../../backend/app/api/routes/custom_entity_templates.py) | Template admin endpoints |

Custom-field values are stored on each versioned entity's `custom_fields`
JSONB column (no EAV); they flow through `clone()` / `UpdateCommand` for free.
See memory `44-custom-fields-functional-analysis.md` for the design.

---

## Notifications

| File | Description |
| ---- | ----------- |
| [`app/models/domain/notification.py`](../../../../../backend/app/models/domain/notification.py) | `Notification` model |
| [`app/models/domain/notification_delivery.py`](../../../../../backend/app/models/domain/notification_delivery.py) | Per-channel delivery record |
| [`app/models/domain/notification_preference.py`](../../../../../backend/app/models/domain/notification_preference.py) | User channel preferences |
| [`app/models/domain/telegram_account.py`](../../../../../backend/app/models/domain/telegram_account.py) | Telegram account linking |
| [`app/services/notification_service.py`](../../../../../backend/app/services/notification_service.py) | Notification dispatch service |
| [`app/services/notification_preference_service.py`](../../../../../backend/app/services/notification_preference_service.py) | Preference CRUD |
| [`app/services/telegram_link_service.py`](../../../../../backend/app/services/telegram_link_service.py) | Telegram bot deep-link linking |
| [`app/api/routes/notifications.py`](../../../../../backend/app/api/routes/notifications.py) | Notification endpoints |
| [`app/core/notifications/dispatcher.py`](../../../../../backend/app/core/notifications/dispatcher.py) | `NotificationDispatcher` — single publish funnel |
| [`app/core/notifications/emitter.py`](../../../../../backend/app/core/notifications/emitter.py) | Domain event emitters |
| [`app/core/notifications/event.py`](../../../../../backend/app/core/notifications/event.py) | Notification event types |
| [`app/core/notifications/registry.py`](../../../../../backend/app/core/notifications/registry.py) | Channel registry |
| [`app/core/notifications/connection_manager.py`](../../../../../backend/app/core/notifications/connection_manager.py) | WS connection tracking |
| [`app/core/notifications/channels/`](../../../../../backend/app/core/notifications/channels/) | Pluggable channels (in-app WS, Telegram) |

---

## AI Subsystem (all entities non-versioned)

| File | Description |
| ---- | ----------- |
| [`app/models/domain/ai.py`](../../../../../backend/app/models/domain/ai.py) | AI entities (see below) |
| [`app/models/domain/ai_agent_schedule.py`](../../../../../backend/app/models/domain/ai_agent_schedule.py) | `AIAgentSchedule` (cron scheduling) |
| [`app/models/domain/mcp_server.py`](../../../../../backend/app/models/domain/mcp_server.py) | `MCPServer` config |
| [`app/models/domain/document.py`](../../../../../backend/app/models/domain/document.py) + `document_version.py`, `document_folder.py`, `document_entity_link.py` | Document management entities |
| [`app/services/ai_config_service.py`](../../../../../backend/app/services/ai_config_service.py) | AI provider/model/assistant config |
| [`app/services/agent_schedule_service.py`](../../../../../backend/app/services/agent_schedule_service.py) | Agent schedule CRUD + run triggering |
| [`app/services/mcp_server_service.py`](../../../../../backend/app/services/mcp_server_service.py) | MCP server CRUD |
| [`app/services/document_service.py`](../../../../../backend/app/services/document_service.py) + `document_folder_service.py`, `document_processing_service.py` | Document upload/processing |
| [`app/api/routes/ai_chat.py`](../../../../../backend/app/api/routes/ai_chat.py) + `ai_config.py`, `ai_upload.py`, `agent_schedules.py`, `mcp_servers.py`, `documents.py` | AI endpoints |

**Key AI entities** (in `models/domain/ai.py`, all `SimpleEntityBase`):

- `AIProvider` - AI provider configuration (OpenAI, Anthropic, etc.)
- `AIProviderConfig` - Provider-specific configuration (API keys, endpoints)
- `AIModel` - AI model definitions
- `AIAssistantConfig` - Assistant system prompts and settings
- `AIConversationSession` - Chat session management
- `AIConversationMessage` - Individual messages within sessions
- `AIConversationAttachment` - File attachments (images, documents)
- `AIAgentExecution` - Agent execution tracking

The agent runtime itself lives under [`app/ai/`](../../../../../backend/app/ai/)
(graph, supervisor, planner, tools, telemetry, MCP client) — outside the EVCS
core scope but listed here for navigation.

---

## Cross-Cutting / Core Utilities

| File / Dir | Description |
| ---------- | ----------- |
| [`app/core/rbac_unified.py`](../../../../../backend/app/core/rbac_unified.py) | Unified RBAC enforcement (replaces the old `rbac.py` / `rbac_database.py`) |
| [`app/core/filtering.py`](../../../../../backend/app/core/filtering.py) | `FilterParser` (eq/IN + JSONB custom-field filter/sort) |
| [`app/core/temporal_queries.py`](../../../../../backend/app/core/temporal_queries.py) | Bitemporal query helpers |
| [`app/core/temporal.py`](../../../../../backend/app/core/temporal.py) | Temporal types/constants |
| [`app/core/exceptions/`](../../../../../backend/app/core/exceptions/) | `filtering.py`, `hierarchy.py` exception modules |
| [`app/core/providers/`](../../../../../backend/app/core/providers/) | `auth.py`, `user.py` context providers |
| [`app/core/security.py`](../../../../../backend/app/core/security.py) | JWT/password hashing |
| [`app/core/jwt_utils.py`](../../../../../backend/app/core/jwt_utils.py) | JWT helpers |
| [`app/core/cache.py`](../../../../../backend/app/core/cache.py) | Caching utilities |
| [`app/core/config.py`](../../../../../backend/app/core/config.py) | Application settings (`Settings`) |
| [`app/core/enums.py`](../../../../../backend/app/core/enums.py) | Shared enums |
| [`app/core/logging.py`](../../../../../backend/app/core/logging.py) | Logging config (Europe/Rome formatter) |

---

## Pydantic Schemas

Base temporal schemas and per-domain schemas live under `app/models/schemas/`.

| File | Description |
| ---- | ----------- |
| [`app/models/schemas/mixins.py`](../../../../../backend/app/models/schemas/mixins.py) | Shared schema mixins |
| [`app/models/schemas/common.py`](../../../../../backend/app/models/schemas/common.py) | Common request/response schemas |
| [`app/models/schemas/temporal_validators.py`](../../../../../backend/app/models/schemas/temporal_validators.py) | Temporal field validators |
| `app/models/schemas/<domain>.py` | One schema module per domain entity (project, wbs/cost_element, change_order, evm, dashboard, notification, …) |

**Key base schemas** (historically in a `temporal.py` — now folded into the
mixin/common modules): `TemporalCreate`, `TemporalUpdate`, `TemporalRead`.

---

## Database Migrations

| File | Description |
| ---- | ----------- |
| [`alembic/versions/`](../../../../../../backend/alembic/versions/) | All migration files |

**Key Migration Patterns:**

- Create version tables with TSTZRANGE columns
- Add GIST indexes for temporal queries
- Create partial unique indexes for current versions
- Custom-fields: unique partial index `ON (root_id, branch) WHERE upper(valid_time) IS NULL AND deleted_at IS NULL`

---

## Configuration

| File | Description |
| ---- | ----------- |
| [`app/core/config.py`](../../../../../backend/app/core/config.py) | Application settings (`Settings`) |
| [`app/db/session.py`](../../../../../backend/app/db/session.py) | Database session factory |

---

## Directory Structure

Verified against the live `backend/app/` tree (2026-07-01). Only files
relevant to EVCS Core + its domain consumers are shown; `__pycache__` omitted.

```
backend/app/
├── core/
│   ├── base/
│   │   └── base.py                    # EntityBase, SimpleEntityBase
│   ├── versioning/                    # Temporal versioning framework
│   │   ├── commands.py                # Create/Update/SoftDelete commands
│   │   ├── service.py                 # TemporalService[T]
│   │   ├── creator_resolver.py        # audit creator resolution
│   │   ├── enums.py
│   │   └── exceptions.py
│   ├── branching/                     # Branching framework
│   │   ├── commands.py                # CreateBranch/Merge/Revert commands
│   │   ├── service.py                 # BranchableService[T]
│   │   └── exceptions.py
│   ├── simple/                        # Non-versioned entity framework
│   │   ├── commands.py                # SimpleCreate/Update/Delete commands
│   │   └── service.py                 # SimpleService[T]
│   ├── notifications/                 # Unified notification system
│   │   ├── dispatcher.py              # NotificationDispatcher (single funnel)
│   │   ├── emitter.py
│   │   ├── event.py
│   │   ├── registry.py
│   │   ├── connection_manager.py
│   │   └── channels/                  # in-app WS, Telegram
│   ├── exceptions/                    # filtering.py, hierarchy.py
│   ├── providers/                     # auth.py, user.py
│   ├── rbac_unified.py                # unified RBAC (old rbac*.py retired)
│   ├── filtering.py                   # FilterParser (eq/IN + JSONB)
│   ├── temporal_queries.py            # bitemporal query helpers
│   ├── temporal.py
│   ├── security.py / jwt_utils.py
│   ├── cache.py / config.py / enums.py / logging.py
│   └── ...
├── models/
│   ├── mixins.py                      # VersionableMixin, BranchableMixin
│   ├── mixins.pyi
│   ├── protocols.py                   # EntityProtocol, VersionableProtocol
│   ├── domain/
│   │   ├── project.py                 # ProjectVersion (versioned + branchable)
│   │   ├── wbs_element.py             # WBSElementVersion (versioned + branchable)
│   │   ├── cost_element.py            # CostElementVersion (versioned + branchable)
│   │   ├── cost_element_type.py
│   │   ├── control_account.py
│   │   ├── work_package.py
│   │   ├── cost_event.py / cost_event_type.py
│   │   ├── cost_registration.py / cost_registration_attachment.py
│   │   ├── progress_entry.py
│   │   ├── forecast.py
│   │   ├── schedule_baseline.py / schedule_dependency.py
│   │   ├── change_order.py / change_order_config.py / change_order_audit_log.py
│   │   ├── organizational_unit.py / customer.py / currency_rate.py
│   │   ├── user.py / user_role_assignment.py / refresh_token.py
│   │   ├── project_budget_settings.py
│   │   ├── branch.py                  # non-versioned
│   │   ├── dashboard_layout.py        # non-versioned
│   │   ├── custom_entity_template.py  # admin custom-field templates
│   │   ├── ai.py                      # AI entities (all non-versioned)
│   │   ├── ai_agent_schedule.py
│   │   ├── mcp_server.py
│   │   ├── document.py / document_version.py / document_folder.py / document_entity_link.py
│   │   ├── notification.py / notification_delivery.py / notification_preference.py
│   │   ├── telegram_account.py
│   │   └── rbac.py
│   ├── custom_fields/                 # OO field-definitions package
│   │   ├── base.py                    # FieldDefinition base
│   │   ├── fields.py                  # concrete field types
│   │   ├── registry.py                # type registry
│   │   └── __init__.py
│   └── schemas/                       # Pydantic schemas (one per domain + mixins/common)
├── services/
│   ├── project.py                     # ProjectService (BranchableService)
│   ├── wbs_element_service.py         # WBSElementService (BranchableService)
│   ├── cost_element_service.py        # CostElementService (BranchableService)
│   ├── cost_element_type_service.py
│   ├── control_account_service.py
│   ├── work_package_service.py
│   ├── cost_event_service.py / cost_event_type_service.py
│   ├── cost_registration_service.py / cost_registration_attachment_service.py
│   ├── progress_entry_service.py
│   ├── forecast_service.py
│   ├── schedule_baseline_service.py / schedule_dependency_service.py
│   ├── change_order_service.py / change_order_config_service.py
│   ├── change_order_workflow_service.py / change_order_workflow_validation.py
│   ├── change_order_reporting_service.py
│   ├── organizational_unit_service.py
│   ├── customer_service.py / currency_rate_service.py
│   ├── user.py / rbac_admin_service.py
│   ├── project_budget_settings_service.py
│   ├── branch_service.py
│   ├── impact_analysis_service.py / financial_impact_service.py
│   ├── gantt_service.py / evm_service.py
│   ├── dashboard_service.py / dashboard_layout_service.py
│   ├── entity_discovery_service.py / global_search_service.py
│   ├── custom_field_service.py / custom_entity_template_service.py
│   ├── notification_service.py / notification_preference_service.py / telegram_link_service.py
│   ├── ai_config_service.py / agent_schedule_service.py / mcp_server_service.py
│   ├── document_service.py / document_folder_service.py / document_processing_service.py
│   ├── sla_service.py / system_admin_service.py / auth.py / storage_service.py
│   └── progression/                   # progression curves (base, linear, gaussian, logarithmic)
├── ai/                                # agent runtime (graph, supervisor, planner, tools, telemetry, mcp)
└── api/
    ├── dependencies/
    ├── middleware/
    ├── errors.py / websocket_utils.py
    └── routes/                        # /api/v1/* — prefix applied by router, not directory
        ├── projects.py / wbs_elements.py / cost_elements.py / cost_element_types.py
        ├── control_accounts.py / work_packages.py
        ├── cost_events.py / cost_event_types.py
        ├── cost_registrations.py / cost_registration_attachments.py
        ├── progress_entries.py / forecasts.py
        ├── schedule_baselines.py / schedule_dependencies.py / gantt.py
        ├── change_orders.py / change_order_config.py
        ├── organizational_units.py / customers.py / currency_rates.py
        ├── users.py / user_role_assignments.py / rbac_admin.py
        ├── project_budget_settings.py
        ├── evm.py / dashboard.py / dashboard_layouts.py / search.py
        ├── custom_entity_templates.py
        ├── notifications.py
        ├── ai_chat.py / ai_config.py / ai_upload.py / agent_schedules.py / mcp_servers.py / documents.py
        ├── system_admin.py / auth.py
        └── ...
```

---

## See Also

- [EVCS Core Architecture](architecture.md)
- [EVCS Implementation Guide](evcs-implementation-guide.md) - Code patterns and recipes
- [Temporal Query Reference](../../../cross-cutting/temporal-query-reference.md) - Bitemporal queries and time travel
- [Entity Classification Guide](entity-classification.md) - Simple / Versionable / Branchable tiers
