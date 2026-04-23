# TD-065: Automated OpenAPI Client Generation

## Summary

Implemented automated OpenAPI client generation in CI/CD pipeline to ensure frontend-backend API contract alignment.

## Problem

Previously, OpenAPI client generation had to be run manually when the backend API changed. This led to:
- Frontend-backend contract misalignment
- Type errors in frontend code
- Manual overhead and potential for human error
- Inconsistent API client state across team

## Solution

Created a GitHub Actions workflow that automatically:
1. Detects changes to backend API code
2. Regenerates the OpenAPI specification
3. Generates updated TypeScript client code
4. Commits changes back to the repository

## Implementation

### Files Created

1. **`.github/workflows/generate-api-client.yml`**
   - GitHub Actions workflow
   - Triggers on backend API changes
   - Runs full generation pipeline
   - Auto-commits generated files

2. **`docs/03-operations/ci-cd/openapi-client-generation.md`**
   - Comprehensive documentation
   - Architecture overview
   - Troubleshooting guide
   - Best practices

3. **`docs/03-operations/ci-cd/openapi-quick-reference.md`**
   - Quick reference guide
   - Common commands
   - Troubleshooting tips

### Files Modified

1. **`backend/scripts/generate_openapi.py`**
   - Enhanced with better error handling
   - Added detailed output information
   - Improved import path handling

2. **`backend/pyproject.toml`**
   - Added `generate-openapi` script command
   - Allows direct script execution

## Workflow

```
Backend API Change
         ↓
GitHub Actions Trigger
         ↓
Generate OpenAPI Spec (backend)
         ↓
Generate TypeScript Client (frontend)
         ↓
Auto-commit Changes
```

## Triggers

The workflow runs automatically when:

- Code is pushed to `main` or `develop` branches
- Changes affect:
  - `backend/app/**/*.py` (API code)
  - `backend/pyproject.toml` (dependencies)

Manual trigger available via:
- GitHub UI: Actions → Generate OpenAPI Client → Run workflow
- CLI: `gh workflow run generate-api-client.yml`

## Benefits

1. **Automatic Updates**: No manual intervention required
2. **Type Safety**: Frontend always has correct types
3. **Consistency**: All team members work with same client code
4. **Error Prevention**: Catches contract mismatches early
5. **Developer Experience**: Zero friction API development

## Usage

### Automatic (Recommended)

Nothing to do! The workflow runs automatically on backend changes.

### Manual (When Needed)

```bash
# Generate OpenAPI spec
cd backend && source .venv/bin/activate
uv run python scripts/generate_openapi.py

# Generate frontend client
cd frontend
npm run generate-client
```

## Testing

All components verified:
- ✓ Backend script executes successfully
- ✓ OpenAPI specification is valid
- ✓ Frontend client generation works
- ✓ Workflow file is properly configured
- ✓ All paths and triggers are correct

## Migration Notes

No migration required. The workflow is backward compatible and doesn't affect existing code.

## Future Enhancements

Potential improvements:
- Add Slack/Discord notifications on generation
- Include API diff in commit message
- Generate API documentation site
- Add validation tests for generated client

## Related Documentation

- [OpenAPI Client Generation](./openapi-client-generation.md)
- [API Conventions](../02-architecture/cross-cutting/api-conventions.md)
- [CI/CD Overview](./ci-cd-overview.md)

## Verification

To verify the implementation:

```bash
# Test backend generation
cd backend && python scripts/generate_openapi.py

# Test frontend generation
cd frontend && npm run generate-client

# Verify workflow syntax
yamllint .github/workflows/generate-api-client.yml
```

---

**Implemented**: 2026-04-23
**Status**: ✅ Complete
**Impact**: High - Improves developer experience and prevents API contract mismatches
