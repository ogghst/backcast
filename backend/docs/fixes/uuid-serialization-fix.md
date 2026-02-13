# UUID Serialization Fix for Impact Analysis

## Problem Summary

When submitting a change order for approval, the system failed with a UUID serialization error:

```
TypeError: Object of type UUID is not JSON serializable
[SQL: UPDATE change_orders SET impact_level=$1::VARCHAR, assigned_approver_id=$2::UUID,
impact_analysis_status=$3::VARCHAR, impact_analysis_results=$4::JSONB, ...]
```

## Root Cause

The `ImpactAnalysisResponse` Pydantic model contains a `change_order_id` field of type `UUID`. When storing impact analysis results to the database's `impact_analysis_results` JSONB column, the code was using:

```python
impact_analysis_results=impact_analysis.model_dump()
```

The default `model_dump()` mode returns UUID objects as-is (not strings), which cannot be serialized to JSON for database storage.

## Solution

Changed line 1114 in `/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py` from:

```python
impact_analysis_results=impact_analysis.model_dump(),
```

to:

```python
impact_analysis_results=impact_analysis.model_dump(mode='json'),
```

The `mode='json'` parameter instructs Pydantic to convert all non-JSON-serializable types (including UUIDs) to their JSON-compatible string representation.

## Technical Details

### Before (Broken)

```python
# impact_analysis.model_dump() returns:
{
    "change_order_id": UUID('12345678-1234-5678-1234-567812345678'),  # UUID object
    "branch_name": "BR-test-001",
    ...
}

# This fails when JSON.stringify() is called by SQLAlchemy for JSONB storage
```

### After (Fixed)

```python
# impact_analysis.model_dump(mode='json') returns:
{
    "change_order_id": "12345678-1234-5678-1234-567812345678",  # String
    "branch_name": "BR-test-001",
    ...
}

# This can be successfully stored in JSONB column
```

## Files Modified

1. **`/home/nicola/dev/backcast_evs/backend/app/services/change_order_service.py`**
   - Line 1114: Changed `model_dump()` to `model_dump(mode='json')`
   - Added explanatory comment about UUID serialization

## Tests Added

### Unit Tests

Created comprehensive unit tests in `/home/nicola/dev/backcast_evs/backend/tests/test_uuid_serialization_fix.py`:

1. `test_impact_analysis_response_model_dump_json_mode` - Verifies UUIDs are converted to strings
2. `test_impact_analysis_response_model_dump_default_mode_fails` - Demonstrates the bug with default mode
3. `test_uuid_serialization_roundtrip` - Verifies UUID → JSON → UUID preservation

### Integration Tests

Created integration test in `/home/nicola/dev/backcast_evs/backend/tests/integration/test_change_order_impact_analysis_serialization.py`:

1. `test_impact_analysis_stores_with_uuid_serialization` - Tests complete storage workflow
2. `test_change_order_service_serialization_in_run_impact_analysis` - Tests service-level serialization

## Test Results

All tests pass successfully:

```bash
$ uv run pytest tests/test_uuid_serialization_fix.py -v
======================== 3 passed, 2 warnings in 28.08s ========================

$ uv run pytest tests/integration/test_change_order_impact_analysis_serialization.py -v
======================== 2 passed, 2 warnings in 26.69s ========================
```

## Quality Checks

### Ruff Linting

```bash
$ uv run ruff check app/services/change_order_service.py app/services/impact_analysis_service.py --fix
All checks passed!
```

### MyPy Type Checking

Pre-existing MyPy errors are unrelated to this fix. The fix itself doesn't introduce any new type errors.

## Impact Analysis

### What This Fixes

- Change orders can now be successfully submitted for approval
- Impact analysis results with UUIDs are properly stored in JSONB columns
- The workflow transition Draft → Submitted for Approval → Approved/Rejected works correctly

### What This Doesn't Break

- All existing functionality remains intact
- UUIDs can still be retrieved and converted back from JSON
- No migration required (data format is compatible)

### Backward Compatibility

- Existing impact analysis results in the database are unaffected
- The JSON serialization format is standard and compatible
- UUID strings can be converted back to UUID objects when needed

## Future Considerations

1. **Standardize Serialization Pattern**: Consider using `mode='json'` consistently for all Pydantic models that are stored in JSONB columns
2. **Custom Serializer**: If more complex serialization is needed, implement a custom serializer using Pydantic's `@field_serializer` decorator
3. **Validation**: Add validation to ensure impact analysis results can be serialized before database operations

## Related Documentation

- [Pydantic Serialization Modes](https://docs.pydantic.dev/latest/concepts/serialization/#modeldump)
- [PostgreSQL JSONB Type](https://www.postgresql.org/docs/current/datatype-json.html)
- [Backend Coding Standards](/home/nicola/dev/backcast_evs/docs/02-architecture/backend/coding-standards.md)

## Verification Steps

To verify the fix works:

1. Create a change order
2. Submit it for approval
3. Verify impact analysis results are stored in the database
4. Check that the `impact_analysis_results` JSONB column contains string UUIDs
5. Verify the workflow transitions work correctly

```python
# Example verification query
SELECT
    change_order_id,
    impact_analysis_status,
    impact_analysis_results->>'change_order_id' as co_id,
    impact_analysis_results->>'kpi_scorecard' as kpi
FROM change_orders
WHERE impact_analysis_status = 'completed';
```

## Success Criteria Met

✅ Change orders can be submitted for approval without UUID serialization errors
✅ The workflow transitions work correctly (Draft → Submitted for Approval → Approved/Rejected)
✅ The impact analysis results are properly stored in the database as JSONB
✅ All existing tests still pass
✅ New tests added to prevent regression
✅ Code quality checks (Ruff) pass
