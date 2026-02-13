# Act Phase: Consistent Seed Entity IDs

## Next Steps

### Step 1: Update Seed JSON Files

Run the UUID generation script and update all seed files with the generated UUIDs.

**Reference UUIDs (from generate_seed_uuids.py output):**

#### Projects
```json
{
  "project_id": "d54fbbe6-f3df-51db-9c3e-9408700442be",
  "code": "PRJ-DEMO-001",
  ...
}
```

#### WBEs
```json
{
  "wbe_id": "3a42f62c-96f8-5392-bff1-2e16f97734f0",
  "project_code": "PRJ-DEMO-001",
  "code": "PRJ-DEMO-001-L1-1",
  ...
}
```

#### Cost Elements
```json
{
  "cost_element_id": "18c26d12-9789-5004-b766-3b099405e884",
  "wbe_code": "PRJ-DEMO-001-L1-1",
  "code": "PRJ-DEMO-001-L1-1-CE-1",
  ...
}
```

#### Departments
```json
{
  "department_id": "1c47969b-d568-5f34-bb9d-4e11cae84745",
  "code": "ADMIN",
  ...
}
```

#### Cost Element Types
```json
{
  "cost_element_type_id": "6a483c4e-893c-5a92-8db9-6f5ac937c63f",
  "code": "LAB",
  ...
}
```

#### Users
```json
{
  "user_id": "e03556f3-4385-5d68-a685-af307fc8af5c",
  "email": "admin@backcast.org",
  ...
}
```

### Step 2: Update Seeder

Modify `backend/app/db/seeder.py`:

1. Import the seed context:
```python
from app.db.seed_context import seed_operation
```

2. Wrap each seed method:
```python
async def seed_wbes(self, session: AsyncSession) -> None:
    with seed_operation():  # Allow explicit IDs
        # ... existing logic
```

3. For temporal entities (WBE, CostElement):
   - IDs already in JSON → schema accepts them → service uses them

### Step 3: Update Seed JSON Files

Execute the following updates to each seed file:

**Files to update:**
- `backend/seed/projects.json`
- `backend/seed/wbes.json`
- `backend/seed/cost_elements.json`
- `backend/seed/departments.json`
- `backend/seed/cost_element_types.json`
- `backend/seed/users.json`

**Use the generated UUIDs from** `backend/scripts/generate_seed_uuids.py` output.

### Step 4: Test Seeding

After updating files:
1. Drop and recreate database
2. Run seeder: `uv run python -m app.db.seeder`
3. Verify all entities have expected UUIDs
4. Run seeder again and verify no duplicates created

### Step 5: Integration Tests

Create `backend/tests/api/test_seeding.py`:
- Test seeding is idempotent
- Test all entity IDs match expected UUIDv5 values
- Test relationships resolve correctly

### Step 6: Documentation

Update:
1. `docs/02-architecture/00-system-map.md` - Add UUID strategy section
2. `docs/02-architecture/seeding-guide.md` - New document
3. OpenAPI spec - Verify ID fields are hidden (should be with `exclude=True`)

## Rollback Plan

If issues arise:
1. Revert schema changes (remove optional root ID fields)
2. Revert service changes (remove ID override logic)
3. Keep seed JSON files with IDs (harmless, will be ignored)
4. Revert seeder changes
5. Re-enable auto-generation in services

No database migration required - changes are code-only.

## Completion Checklist

- [ ] All seed JSON files updated with UUIDv5 values
- [ ] Seeder updated to use `seed_operation()` context
- [ ] Integration tests written and passing
- [ ] Documentation updated
- [ ] Full test suite passing (pytest)
- [ ] Code quality checks passing (ruff, mypy)
