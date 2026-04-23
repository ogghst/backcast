# Automated OpenAPI Client Generation

## Overview

This document describes the automated OpenAPI client generation system that ensures frontend-backend API contract alignment.

## Architecture

The system consists of three main components:

1. **Backend OpenAPI Generation** (`backend/scripts/generate_openapi.py`)
   - Extracts OpenAPI specification from FastAPI application
   - Outputs to `backend/openapi.json`

2. **Frontend Client Generation** (`npm run generate-client`)
   - Uses `openapi-typescript-codegen` to generate TypeScript client
   - Outputs to `frontend/src/api/generated/`

3. **CI/CD Automation** (`.github/workflows/generate-api-client.yml`)
   - Triggers on backend API changes
   - Automatically generates and commits updated client code

## Workflow

### Automatic Trigger

The GitHub Actions workflow triggers automatically when:

- Code is pushed to `main` or `develop` branches
- Changes are made to:
  - `backend/app/**/*.py` (any backend API code)
  - `backend/pyproject.toml` (dependency changes)

### Manual Trigger

The workflow can be manually triggered via:

1. GitHub UI: Actions → Generate OpenAPI Client → Run workflow
2. CLI: `gh workflow run generate-api-client.yml`

### Process Flow

```
┌─────────────────────────┐
│ Backend API Changed     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ CI Workflow Triggers    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Generate OpenAPI Spec   │
│ (generate_openapi.py)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Generate Frontend Client│
│ (npm run generate-client)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Auto-commit Changes     │
└─────────────────────────┘
```

## Local Development

### Generating OpenAPI Spec

```bash
cd backend
source .venv/bin/activate
uv run python scripts/generate_openapi.py
```

Or using the installed script:

```bash
cd backend
source .venv/bin/activate
generate-openapi
```

### Generating Frontend Client

```bash
cd frontend
npm run generate-client
```

### Full Update Workflow

```bash
# 1. Update backend API
cd backend
uv run python scripts/generate_openapi.py

# 2. Update frontend client
cd ../frontend
npm run generate-client

# 3. Commit changes
git add backend/openapi.json frontend/src/api/generated/
git commit -m "chore: update OpenAPI client"
```

## Generated Files

### Backend

- `backend/openapi.json` - OpenAPI 3.1.0 specification

### Frontend

- `frontend/src/api/generated/index.ts` - Main exports
- `frontend/src/api/generated/core/` - Core API functionality
- `frontend/src/api/generated/models/` - TypeScript models
- `frontend/src/api/generated/services/` - API service methods

## CI/CD Configuration

### Workflow File

`.github/workflows/generate-api-client.yml`

### Permissions

The workflow requires `contents: write` permission to auto-commit changes.

### Caching

The workflow uses GitHub Actions caching for:

- Python dependencies (uv cache)
- Node.js dependencies (node_modules)

## Troubleshooting

### Workflow Not Triggering

**Issue**: Workflow doesn't run after backend changes

**Solution**:
1. Verify file paths match workflow triggers
2. Check workflow is enabled in repository settings
3. Review GitHub Actions logs for errors

### Generation Failures

**Issue**: OpenAPI generation fails

**Solution**:
1. Check backend imports are working correctly
2. Verify FastAPI application can be imported
3. Run locally first: `cd backend && uv run python scripts/generate_openapi.py`

### Client Type Errors

**Issue**: Generated TypeScript has errors

**Solution**:
1. Ensure backend OpenAPI spec is valid
2. Check for naming conflicts in models
3. Regenerate with clean state: `rm -rf frontend/src/api/generated/ && npm run generate-client`

### Merge Conflicts

**Issue**: Conflicts in `frontend/src/api/generated/`

**Solution**:
1. Regenerate client from latest backend
2. Let automated updates handle future changes
3. Don't manually edit generated files

## Best Practices

### Backend Development

1. **Add proper type hints** - FastAPI uses these for OpenAPI schema
2. **Document endpoints** - Use docstrings for better generated documentation
3. **Version breaking changes** - Update API version when introducing breaking changes

### Frontend Development

1. **Don't edit generated files** - Changes will be overwritten
2. **Use generated types** - Import from `@/api/generated` for type safety
3. **Report schema issues** - Fix in backend, not frontend

### CI/CD Management

1. **Monitor workflow runs** - Check for failures in Actions tab
2. **Review auto-commits** - Verify generated changes are correct
3. **Keep workflow updated** - Update when adding new dependencies

## Related Documentation

- [Backend API Conventions](../02-architecture/cross-cutting/api-conventions.md)
- [Frontend State Management](../02-architecture/frontend/state-management.md)
- [CI/CD Pipeline](./ci-cd-overview.md)

## Technical Details

### OpenAPI Specification

- **Version**: OpenAPI 3.1.0
- **Format**: JSON
- **Source**: FastAPI's `app.openapi()`

### Code Generator

- **Tool**: `openapi-typescript-codegen`
- **Client**: Axios
- **Output**: TypeScript with strict typing

### Automation

- **Platform**: GitHub Actions
- **Trigger**: Path-based push events
- **Commit**: Bot account with `github-actions[bot]` identity
