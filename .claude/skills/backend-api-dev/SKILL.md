---
name: backend-api-dev
description: Develop FastAPI REST API routes following project conventions. Creates route files with CRUD endpoints, RBAC via RoleChecker, branch/context parameters, pagination, and time-travel support. Use when creating API endpoints, REST routes, or when user mentions "API", "endpoint", "route".
allowed-tools: [Read, Write, Edit, Glob, Grep, AskUserQuestion]
---

# Backend API Development

Develop FastAPI routes following project conventions.

## Reference

- API Conventions: [docs/02-architecture/cross-cutting/api-conventions.md](../../docs/02-architecture/cross-cutting/api-conventions.md)
- Auth Dependencies: [backend/app/api/dependencies/auth.py](../../backend/app/api/dependencies/auth.py)
- Route Examples: [backend/app/api/routes/projects.py](../../backend/app/api/routes/projects.py), [backend/app/api/routes/schedule_baselines.py](../../backend/app/api/routes/schedule_baselines.py)
- Common Schemas: [backend/app/models/schemas/common.py](../../backend/app/models/schemas/common.py)

## Route File Template

```python
"""{Entity} API routes with RBAC."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.{entity} import {Entity}Create, {Entity}Public, {Entity}Update
from app.services.{entity} import {Entity}Service

router = APIRouter()

def get_{entity}_service(session: AsyncSession = Depends(get_db)) -> {Entity}Service:
    return {Entity}Service(session)
```

## Standard Endpoints

### List (GET /)
```python
@router.get(
    "",
    response_model=None,  # PaginatedResponse[{Entity}Public]
    operation_id="get_{entities}",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-read"))],
)
async def read_{entities}(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    mode: str = Query("merged", pattern="^(merged|isolated)$", description="Branch mode"),
    as_of: datetime | None = Query(None, description="Time travel (ISO 8601)"),
    service: {Entity}Service = Depends(get_{entity}_service),
) -> dict[str, Any]:
    """Retrieve {entities} with pagination, filtering, and time-travel."""
    from app.models.schemas.common import PaginatedResponse
    skip = (page - 1) * per_page
    items, total = await service.get_{entities}(skip, limit=per_page, branch=branch, as_of=as_of)
    response = PaginatedResponse[{Entity}Public](items=items, total=total, page=page, per_page=per_page)
    return response.model_dump()
```

### Create (POST /)
```python
@router.post(
    "",
    response_model={Entity}Public,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_{entity}",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-create"))],
)
async def create_{entity}(
    {entity}_in: {Entity}Create,
    current_user: User = Depends(get_current_active_user),
    service: {Entity}Service = Depends(get_{entity}_service),
) -> {Entity}:
    """Create a new {entity}. branch and control_date in request body."""
    return await service.create({entity}_in, actor_id=current_user.user_id, branch={entity}_in.branch, control_date={entity}_in.control_date)
```

### Get One (GET /{id})
```python
@router.get(
    "/{{entity_id}}",
    response_model={Entity}Public,
    operation_id="get_{entity}",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-read"))],
)
async def read_{entity}(
    entity_id: UUID,
    branch: str = Query("main"),
    as_of: datetime | None = Query(None, description="Time travel (ISO 8601)"),
    service: {Entity}Service = Depends(get_{entity}_service),
) -> {Entity}:
    """Get a specific {entity} by id. Supports time-travel via as_of."""
    if as_of:
        entity = await service.get_as_of(entity_id, as_of, branch)
    else:
        entity = await service.get_by_id(entity_id, branch)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="{Entity} not found")
    return entity
```

### Update (PUT /{id})
```python
@router.put(
    "/{{entity_id}}",
    response_model={Entity}Public,
    operation_id="update_{entity}",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-update"))],
)
async def update_{entity}(
    entity_id: UUID,
    {entity}_in: {Entity}Update,
    current_user: User = Depends(get_current_active_user),
    service: {Entity}Service = Depends(get_{entity}_service),
) -> {Entity}:
    """Update a {entity}. branch and control_date in request body."""
    update_data = {entity}_in.model_dump(exclude_unset=True, exclude={"branch", "control_date"})
    return await service.update(entity_id, actor_id=current_user.user_id, branch={entity}_in.branch, control_date={entity}_in.control_date, **update_data)
```

### Delete (DELETE /{id})
```python
@router.delete(
    "/{{entity_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_{entity}",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-delete"))],
)
async def delete_{entity}(
    entity_id: UUID,
    branch: str = Query("main"),
    control_date: datetime | None = Query(None, description="Optional control date"),
    current_user: User = Depends(get_current_active_user),
    service: {Entity}Service = Depends(get_{entity}_service),
) -> None:
    """Soft delete a {entity}. branch and control_date in query params (HTTP/1.1 exception)."""
    await service.soft_delete(entity_id, actor_id=current_user.user_id, branch=branch, control_date=control_date)
```

### History (GET /{id}/history)
```python
@router.get(
    "/{{entity_id}}/history",
    response_model=list[{Entity}Public],
    operation_id="get_{entity}_history",
    dependencies=[Depends(RoleChecker(required_permission="{entity}-read"))],
)
async def read_{entity}_history(
    entity_id: UUID,
    service: {Entity}Service = Depends(get_{entity}_service),
) -> Sequence[{Entity}]:
    """Get version history for a {entity}."""
    return await service.get_history(entity_id)
```

## Context Parameters Summary

| Operation | Location | Params |
|-----------|----------|--------|
| GET (read) | Query | `branch`, `as_of`, `mode` |
| POST/PUT/PATCH | Body | `branch`, `control_date` |
| DELETE | Query | `branch`, `control_date` |

## Registration

Add to `backend/app/api/routes/__init__.py`:
```python
from app.api.routes.{entity} import router as {entity}_router
api_router.include_router({entity}_router, prefix="/{entities}", tags=["{Entities}"])
```

## Quality Checks

```bash
cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest tests/api/
```
