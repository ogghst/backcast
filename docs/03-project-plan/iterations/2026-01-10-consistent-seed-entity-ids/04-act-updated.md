# Act Phase (Updated): Consistent Seed Entity IDs

## Completed Work

### 1. Seed JSON Files Updated with UUIDv5 ✅

All seed files now contain deterministic UUIDv5 values:

**projects.json**:
- Added `project_id` with UUIDv5 values
- PRJ-DEMO-001 → `d54fbbe6-f3df-51db-9c3e-9408700442be`
- PRJ-DEMO-002 → `877c4cba-b30e-54c1-b25d-c73fb364019d`

**departments.json**:
- Added `department_id` with UUIDv5 values
- ADMIN → `1c47969b-d568-5f34-bb9d-4e11cae84745`
- PM → `23b5b365-b8ab-5cf8-8ed8-76362d5e2b0b`
- ENG → `e498f139-05b6-5da8-9008-31a8d760bcdc`
- CONST → `c985679f-d9c0-5a03-b51f-0f8aab0d0732`

**cost_element_types.json**:
- Added `cost_element_type_id` with UUIDv5 values
- Replaced `department_code` with `department_id` (ID-based relationship)

**users.json**:
- Added `user_id` with UUIDv5 values (email-based)
- admin@backcast.org → `e03556f3-4385-5d68-a685-af307fc8af5c`

**wbes.json**:
- Added `wbe_id` with UUIDv5 values (code-based)
- Replaced `project_code` with `project_id` (ID-based relationship)
- Replaced `parent_wbe_code` with `parent_wbe_id` (ID-based relationship)

**cost_elements.json**:
- Added `cost_element_id` with UUIDv5 values (code-based)
- Replaced `wbe_code` with `wbe_id` (ID-based relationship)
- Replaced `cost_element_type_code` with `cost_element_type_id` (ID-based relationship)

### 2. Seeder Updated ✅

All seed methods now:
- Use `with seed_operation():` context to allow explicit root IDs
- Directly use IDs from JSON instead of resolving codes
- Are simplified (less lookup logic required)

Updated methods:
- `seed_users()` - Uses `user_id` from JSON
- `seed_departments()` - Uses `department_id` from JSON
- `seed_cost_element_types()` - Uses `cost_element_type_id` and `department_id` from JSON
- `seed_projects()` - Uses `project_id` from JSON
- `seed_wbes()` - Uses `wbe_id`, `project_id`, and `parent_wbe_id` from JSON
- `seed_cost_elements()` - Uses `cost_element_id`, `wbe_id`, and `cost_element_type_id` from JSON

### 3. Code Quality ✅
- Ruff: All checks passed
- MyPy: No errors

## Benefits of ID-Based Relationships

1. **Simpler Seeder**: No need to lookup entities by code during seeding
2. **Explicit Dependencies**: Relationships are directly visible in JSON
3. **Faster Seeding**: No database queries to resolve relationships
4. **Type Safety**: UUIDs provide type-safe foreign keys
5. **Consistency**: Same structure as database schema

## Example: Before vs After

### Before (Code-Based)
```json
{
  "project_code": "PRJ-DEMO-001",
  "code": "PRJ-DEMO-001-L1-1",
  "parent_wbe_code": null
}
```

### After (ID-Based)
```json
{
  "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
  "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
  "code": "PRJ-DEMO-001-L1-1",
  "parent_wbe_id": null
}
```

## Next Steps

1. **Test Seeding**: Run the seeder to verify all entities are created correctly
2. **Verify Determinism**: Run seeder twice and verify identical database state
3. **Integration Tests**: Add tests to verify seeding produces expected results
4. **Documentation**: Update architecture documentation with new seeding approach
