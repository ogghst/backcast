# OpenAPI Client Generation - Quick Reference

## TL;DR

When you change the backend API, **you don't need to manually update the frontend types**. The CI/CD pipeline handles it automatically.

## What Happens Automatically

1. You push backend API changes to `main` or `develop`
2. GitHub Actions workflow triggers
3. OpenAPI spec is regenerated
4. Frontend TypeScript client is regenerated
5. Changes are auto-committed back to the repository

## When You Need to Run Manually

### Local Development

After modifying backend API endpoints:

```bash
# From project root
cd backend && source .venv/bin/activate && python scripts/generate_openapi.py
cd ../frontend && npm run generate-client
```

### Force CI/CD Run

If auto-generation failed or you need to trigger it manually:

```bash
gh workflow run generate-api-client.yml
```

Or via GitHub UI:
- Go to Actions tab
- Select "Generate OpenAPI Client"
- Click "Run workflow"

## Generated Files

**Do NOT manually edit these files:**

- `backend/openapi.json` - OpenAPI specification
- `frontend/src/api/generated/` - TypeScript client code

## Troubleshooting

### Frontend type errors after backend change

```bash
cd frontend && npm run generate-client
```

### CI/CD workflow failed

Check the Actions tab for error details. Common issues:
- Backend import errors
- Missing dependencies
- Invalid OpenAPI schema

### Need to regenerate everything

```bash
rm -rf frontend/src/api/generated/
cd frontend && npm run generate-client
```

## Verification

After generation, verify the client works:

```bash
cd frontend
npm run build  # Should complete without type errors
```

## For More Details

See [OpenAPI Client Generation Documentation](./openapi-client-generation.md)
