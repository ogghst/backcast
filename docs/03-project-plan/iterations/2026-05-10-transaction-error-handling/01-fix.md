# Database Transaction Error Handling Fix

## Date
2026-05-10

## Problem
Multiple API endpoints were failing with `InFailedSQLTransactionError: current transaction is aborted, commands ignored until end of transaction block`. This caused frontend requests to fail with `net::ERR_FAILED` (generic network error).

## Root Cause
When a database query fails within a transaction, the transaction enters an aborted state. Subsequent queries in that transaction fail until the transaction is rolled back. The service layer methods had no error handling, so:

1. A query would fail (e.g., due to invalid data, constraints)
2. The transaction would enter an aborted state
3. Subsequent queries in the same request would fail with `InFailedSQLTransactionError`
4. The `get_db()` dependency would rollback at the END of the request, but by then the damage was done

## Affected Endpoints
- `/api/v1/dashboard/recent-activity`
- `/api/v1/projects`
- `/api/v1/users/me/preferences`
- Any endpoint with chained database operations

## Solution Implemented

### 1. Created `app/core/db_utils.py`
New utility module with:
- `safe_db_execute()`: Wrapper for database operations with automatic error handling and rollback
- `is_transaction_aborted()`: Helper to detect transaction error states

**Key features:**
- Wraps database operations in try-catch blocks
- Automatically rolls back transactions on errors
- Provides detailed error messages
- Returns properly typed results

### 2. Updated Service Methods
Modified service methods to use `safe_db_execute()`:

**`app/services/project.py`:**
- `get_projects()`: Added error handling for count and main queries

**`app/services/dashboard_service.py`:**
- `get_dashboard_data()`: Added comprehensive error handling wrapper
- `_calculate_project_metrics()`: Added error handling for all metric queries

### 3. Enhanced Exception Handling
**`app/main.py`:**
- Updated generic exception handler to detect and handle transaction errors specifically
- Returns standardized error response for transaction errors
- Better error messages for debugging

### 4. Session Health Middleware (Foundation)
**`app/api/middleware/session_health.py`:**
- Created framework for session health checking
- Functions for detecting and recovering from failed transaction states
- Ready for future enhancement to proactive session management

## Code Changes

### New Files
- `/home/nicola/dev/backcast/backend/app/core/db_utils.py`
- `/home/nicola/dev/backcast/backend/app/api/middleware/session_health.py`
- `/home/nicola/dev/backcast/backend/app/api/middleware/__init__.py`
- `/home/nicola/dev/backcast/backend/tests/unit/core/test_db_utils.py`

### Modified Files
- `/home/nicola/dev/backcast/backend/app/services/project.py`
- `/home/nicola/dev/backcast/backend/app/services/dashboard_service.py`
- `/home/nicola/dev/backcast/backend/app/main.py`

## Testing
- Created unit tests for `safe_db_execute()` utility
- Verified code quality with `ruff` and `mypy`
- All new code passes strict type checking

## Expected Behavior After Fix
1. Failed queries roll back the transaction immediately
2. Subsequent requests use fresh transactions
3. API returns proper error responses instead of connection failures
4. Better error messages for debugging

## Future Improvements
1. **Proactive session health checks**: Implement middleware to check session health before each request
2. **Service layer patterns**: Apply `safe_db_execute()` pattern to all service methods
3. **Metrics and monitoring**: Track transaction errors for observability
4. **Automatic retry**: Implement retry logic for transient transaction errors

## Migration Notes
No database migrations required. This is a code-level fix only.

## Related Issues
- Fixes errors in dashboard recent activity API
- Fixes errors in projects list API
- Prevents cascade failures in multi-query operations
