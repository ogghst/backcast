# Analysis: Model Configuration Parameter

**Analysis Code:** 000001
**Date:** 2025-01-17
**Feature:** Make AI chat model a configurable parameter (like base_url and api_key)

## USER STORY

As a **user or administrator**, I want to **configure the AI model name** (e.g., "deepseek-chat", "gpt-4o-mini", "deepseek-reasoner") as a separate configuration parameter, so that I can **explicitly control which model is used** without relying on auto-detection from the base URL.

## BUSINESS PROBLEM

Currently, the AI model is auto-detected from the base URL (e.g., "deepseek" in URL → "deepseek-chat" model). This approach:
- Lacks flexibility for users who want to use different models with the same provider
- Makes it impossible to use alternative models (e.g., "deepseek-reasoner" vs "deepseek-chat")
- Creates implicit coupling between base URL and model selection
- Doesn't allow administrators to set default models via app configuration

The solution should follow the same pattern as `openai_base_url` and `openai_api_key`, allowing both user-level and app-level (default) configuration.

## CODEBASE PATTERN ANALYSIS

### Existing Implementation Patterns

**1. User Model Configuration Pattern** (`backend/app/models/user.py`)
- Fields: `openai_base_url: str | None`, `openai_api_key_encrypted: str | None`
- Stored directly on User model (UserBase schema)
- Optional fields with `Field(default=None)`
- Max length constraints where appropriate (`max_length=500` for URLs)
- API key is encrypted before storage

**2. App Configuration Pattern** (`backend/app/models/app_configuration.py`)
- Default values stored in `AppConfiguration` table
- Config keys follow pattern: `ai_default_openai_base_url`, `ai_default_openai_api_key_encrypted`
- Retrieved via `get_openai_config()` with priority: user config → default app config → error
- Seeded in `backend/app/core/seeds.py` via `_seed_ai_default_config()`

**3. Frontend Configuration UI Pattern**
- **Admin UI:** `frontend/src/components/Admin/UserAIConfigurationManager.tsx`
  - Table view showing all users with AI config status
  - Edit dialog with form fields for `openai_base_url` and `openai_api_key`
  - Uses react-hook-form for validation
  - Updates via `UsersService.updateUser()`
- **App Config UI:** `frontend/src/components/Admin/AppConfigurationManager.tsx`
  - Manages default app-level configurations
  - Recognizes AI config keys via `isAIConfig()` helper
  - Special handling for URL and API key fields

**4. Backend API Pattern** (`backend/app/api/routes/users.py`)
- `UserUpdate` and `UserUpdateMe` schemas include OpenAI fields
- API key encryption handled in `crud.update_user()` and route handlers
- Plain text `openai_api_key` received, encrypted to `openai_api_key_encrypted` before storage
- Response models exclude encrypted fields from public API

**5. Service Layer Pattern** (`backend/app/services/ai_chat.py`)
- `get_openai_config()` retrieves config with fallback logic
- Returns dict with `base_url`, `api_key`, `model`, `source`
- Currently auto-detects model via `_detect_model_from_base_url()`
- `create_chat_model()` uses config to instantiate ChatOpenAI

**6. Migration Pattern** (`backend/app/alembic/versions/`)
- Alembic migrations for schema changes
- Example: `1fd92ccf32fd_add_openai_config_fields_to_user_table.py`
- Adds nullable columns to `user` table
- Includes both `upgrade()` and `downgrade()` functions

### Namespaces and Interfaces

- **Models:** `app.models.user.User`, `app.models.app_configuration.AppConfiguration`
- **Schemas:** `UserBase`, `UserUpdate`, `UserUpdateMe`, `UserPublic`, `AppConfigurationBase`
- **Services:** `app.services.ai_chat.get_openai_config()`, `app.services.ai_chat.create_chat_model()`
- **CRUD:** `app.crud.update_user()`
- **Routes:** `app.api.routes.users.update_user_me()`, `app.api.routes.users.update_user()`
- **Frontend:** `@/client` (generated OpenAPI client), `UsersService`, `UserPublic`, `UserUpdate`

## INTEGRATION TOUCHPOINT MAPPING

### Backend Touchpoints

1. **Database Schema** (`backend/app/models/user.py`)
   - Add `openai_model: str | None` to `UserBase` schema
   - Add field to `User` table model
   - Update `UserUpdate` and `UserUpdateMe` schemas

2. **Database Migration** (`backend/app/alembic/versions/`)
   - Create new migration: `XXXX_add_openai_model_to_user_table.py`
   - Add nullable `openai_model` column to `user` table

3. **App Configuration** (`backend/app/core/seeds.py`)
   - Add `ai_default_openai_model` to default configs in `_seed_ai_default_config()`

4. **Service Layer** (`backend/app/services/ai_chat.py`)
   - Update `get_openai_config()` to:
     - Retrieve user `openai_model` field
     - Retrieve default `ai_default_openai_model` from AppConfiguration
     - Apply fallback logic: user model → default model → auto-detect from base_url
     - Return `model` in config dict
   - Remove or deprecate `_detect_model_from_base_url()` (keep as fallback)
   - Update `create_chat_model()` to use model from config (already done)

5. **CRUD Layer** (`backend/app/crud.py`)
   - No changes needed (handles all UserBase fields generically)

6. **API Routes** (`backend/app/api/routes/users.py`)
   - `UserUpdate` and `UserUpdateMe` schemas automatically include new field (inherited from UserBase)
   - No route handler changes needed (uses generic update logic)

### Frontend Touchpoints

1. **Type Definitions** (`frontend/src/client/`)
   - Regenerate OpenAPI client after backend schema changes
   - `UserPublic`, `UserUpdate`, `UserUpdateMe` types will include `openai_model`

2. **Admin UI - User Configuration** (`frontend/src/components/Admin/UserAIConfigurationManager.tsx`)
   - Add `openai_model` to `UserAIConfigFormData` interface
   - Add form field in `EditUserAIConfigDialog`:
     - Input field with placeholder (e.g., "deepseek-chat", "gpt-4o-mini")
     - Optional validation (model name format)
     - Pre-populate from `user.openai_model`
   - Update form submission to include `openai_model`

3. **Admin UI - App Configuration** (`frontend/src/components/Admin/AppConfigurationManager.tsx`)
   - Add `ai_default_openai_model` to recognized AI config keys
   - Add helper function `isModelField()` if needed for special rendering
   - Update `getConfigLabel()` to return "Default AI Model" for model config key

4. **User Settings** (`frontend/src/components/UserSettings/`)
   - If user settings page exists for OpenAI config, add model field there
   - Currently no dedicated user settings page found (only admin UI)

### Configuration Storage

- **User-level:** `user.openai_model` (nullable string, max_length ~100)
- **App-level default:** `app_configuration.config_key = "ai_default_openai_model"` (nullable string)
- **Fallback:** Auto-detect from base_url if neither user nor default is set

## ABSTRACTION INVENTORY

### Existing Abstractions to Leverage

1. **SQLModel Base Classes**
   - `UserBase` - All OpenAI config fields inherit from here
   - `AppConfigurationBase` - Default configs follow same pattern

2. **Encryption Utilities** (`app.core.encryption`)
   - Not needed for model (plain text field, unlike API key)

3. **Configuration Retrieval** (`app.services.ai_chat.get_openai_config()`)
   - Existing fallback pattern: user → default → error
   - Can extend to: user model → default model → auto-detect → error

4. **Form Validation** (react-hook-form)
   - Existing URL and API key validation patterns
   - Can add model name validation (optional, format check)

5. **Test Utilities**
   - `backend/tests/services/test_ai_chat_config.py` - Config retrieval tests
   - `backend/tests/services/test_ai_chat_model.py` - Model creation tests
   - `backend/tests/api/routes/test_users_openai.py` - User update tests
   - `frontend/src/components/Admin/__tests__/UserAIConfigurationManager.test.tsx` - UI tests

### Patterns for Reuse

- **Migration Pattern:** Follow `1fd92ccf32fd_add_openai_config_fields_to_user_table.py`
- **Seed Pattern:** Follow `_seed_ai_default_config()` in `backend/app/core/seeds.py`
- **Service Pattern:** Follow `get_openai_config()` fallback logic
- **Frontend Form Pattern:** Follow `EditUserAIConfigDialog` in `UserAIConfigurationManager.tsx`

## ALTERNATIVE APPROACHES

### Approach 1: Add Model Field to User + App Config (Recommended)

**Description:** Add `openai_model` field to User model and `ai_default_openai_model` to AppConfiguration, following exact same pattern as base_url and api_key.

**Implementation:**
- Add `openai_model: str | None` to `UserBase`
- Add migration for `user.openai_model` column
- Add `ai_default_openai_model` to AppConfiguration seeds
- Update `get_openai_config()` with fallback: user model → default model → auto-detect
- Update frontend forms to include model field

**Pros:**
- ✅ Consistent with existing architecture
- ✅ Minimal code changes (follows established patterns)
- ✅ Supports both user-level and app-level defaults
- ✅ Backward compatible (auto-detect as fallback)
- ✅ No breaking changes to API

**Cons:**
- ⚠️ Requires database migration
- ⚠️ Requires frontend form updates
- ⚠️ Model validation needed (what are valid model names?)

**Complexity:** Low-Medium (straightforward extension of existing pattern)
**Risk:** Low (well-established pattern, backward compatible)
**Alignment:** Perfect (follows exact same pattern as base_url/api_key)

---

### Approach 2: Model as Part of Base URL Configuration

**Description:** Store model as part of base URL or derive from a more structured config object.

**Implementation:**
- Store model in a JSON field or as part of base URL parsing
- Or create a unified `ai_config` JSON field containing base_url, api_key, model

**Pros:**
- ✅ Single field for all AI config
- ✅ Easier to add future config options

**Cons:**
- ❌ Breaks existing pattern (base_url and api_key are separate fields)
- ❌ Requires significant refactoring
- ❌ JSON parsing adds complexity
- ❌ Harder to query/filter by model
- ❌ Inconsistent with current architecture

**Complexity:** High (requires refactoring existing code)
**Risk:** High (breaking changes, architectural inconsistency)
**Alignment:** Poor (deviates from established pattern)

---

### Approach 3: Model Selection UI with Provider Detection

**Description:** Keep auto-detection but add UI dropdown to override, storing override in separate field.

**Implementation:**
- Auto-detect model from base URL (current behavior)
- Add UI dropdown showing detected model with option to override
- Store override in `openai_model_override` field
- Use override if set, otherwise use auto-detected

**Pros:**
- ✅ Better UX (shows detected model, allows override)
- ✅ Backward compatible

**Cons:**
- ❌ More complex logic (detection + override)
- ❌ Still requires model field (just named differently)
- ❌ Doesn't solve the core problem (model should be explicit config)

**Complexity:** Medium (adds UI complexity)
**Risk:** Medium (more moving parts)
**Alignment:** Medium (adds complexity without clear benefit)

---

### Approach 4: Model Registry/Enum

**Description:** Define allowed models as enum/constants, validate against registry.

**Implementation:**
- Create `AIModel` enum with known models
- Validate model name against enum
- Store as string but validate on input

**Pros:**
- ✅ Type safety
- ✅ Prevents invalid model names
- ✅ Can provide UI dropdown with known models

**Cons:**
- ⚠️ Requires maintenance when new models are added
- ⚠️ Less flexible for custom/unknown models
- ⚠️ May need to support both enum and free-form string

**Complexity:** Low-Medium (adds validation layer)
**Risk:** Low-Medium (flexibility vs. safety trade-off)
**Alignment:** Good (can be added to Approach 1)

**Recommendation:** Use Approach 1 (add model field) with optional Approach 4 (model validation/enum) for enhanced type safety.

## ARCHITECTURAL IMPACT ASSESSMENT

### Principles Followed

✅ **Consistency:** Follows exact same pattern as `openai_base_url` and `openai_api_key`
✅ **Separation of Concerns:** Model selection is configuration, not business logic
✅ **Backward Compatibility:** Auto-detection remains as fallback
✅ **User Control:** Allows explicit user preference over defaults
✅ **Administrative Control:** Supports app-level defaults

### Potential Maintenance Burden

1. **Model Name Validation**
   - Need to decide: strict enum vs. free-form string
   - If free-form: risk of typos/invalid models
   - If enum: requires updates when new models available
   - **Mitigation:** Start with free-form, add validation later if needed

2. **Migration Path**
   - Existing users without model config will use auto-detection
   - No data migration needed (backward compatible)
   - **Mitigation:** Auto-detection fallback handles this

3. **Frontend Form Complexity**
   - Adding third field to form (base_url, api_key, model)
   - May need model suggestions/autocomplete
   - **Mitigation:** Keep simple text input initially, enhance later

### Testing Challenges

1. **Model Validation Tests**
   - Test valid/invalid model names
   - Test fallback logic (user → default → auto-detect)
   - Test with various base URLs and model combinations

2. **Frontend Form Tests**
   - Test model field in UserAIConfigurationManager
   - Test model field in AppConfigurationManager
   - Test form validation

3. **Integration Tests**
   - Test end-to-end: user sets model → chat uses that model
   - Test default model from app config
   - Test auto-detection fallback

**Mitigation:** Follow existing test patterns, add tests for new fallback logic

## RISKS AND UNKNOWNS

### Identified Risks

1. **Model Name Format**
   - Unknown: What format should model names follow?
   - Unknown: Should we validate against known models?
   - **Mitigation:** Start with free-form string, add validation if issues arise

2. **Migration Timing**
   - Risk: Migration applied before code deployment
   - **Mitigation:** Migration adds nullable column (safe), code handles None

3. **Frontend Type Generation**
   - Risk: OpenAPI client not regenerated after backend changes
   - **Mitigation:** Document regeneration step in implementation

4. **Backward Compatibility**
   - Risk: Existing auto-detection logic might break
   - **Mitigation:** Keep auto-detection as fallback, thoroughly test

### Missing Information

1. **Model Name Constraints**
   - What are valid model names? (e.g., "deepseek-chat", "gpt-4o-mini", "deepseek-reasoner")
   - Should we support provider-specific models or generic names?
   - **Action:** Start with free-form, document common models

2. **UI/UX Preferences**
   - Should model field be dropdown or text input?
   - Should we show suggestions based on base URL?
   - **Action:** Start with simple text input, enhance based on feedback

3. **Default Model Strategy**
   - What should default model be if not configured?
   - Should it vary by provider (DeepSeek vs OpenAI)?
   - **Action:** Use auto-detection as fallback (current behavior)

## SUMMARY

This feature extends the existing OpenAI configuration pattern to include model selection as an explicit parameter. The implementation follows the established architecture exactly, requiring:

- **Backend:** Add `openai_model` field to User model, `ai_default_openai_model` to AppConfiguration, update service layer fallback logic
- **Frontend:** Add model field to admin configuration UIs
- **Database:** Single migration adding nullable column
- **Testing:** Extend existing test patterns for new field and fallback logic

The solution is low-risk, backward-compatible, and maintains architectural consistency. The main decision point is whether to use strict model validation (enum) or free-form strings, which can be decided during implementation.

**Estimated Complexity:** Low-Medium
**Estimated Effort:** 4-6 hours (backend: 2-3h, frontend: 1-2h, testing: 1h)
**Risk Level:** Low
**Architectural Alignment:** Excellent
