"""System admin API routes for database dump and reseed operations.

All endpoints require the ``system-dump-reseed`` permission.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker
from app.db.session import get_db
from app.services.system_admin_service import SystemAdminService

logger = logging.getLogger(__name__)

router = APIRouter()

_guard = Depends(RoleChecker(required_permission="system-dump-reseed"))

SEED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "seed"
SEED_FILE = SEED_DIR / "seed_data.json"
SEED_SYSTEM_CONFIG_FILE = SEED_DIR / "seed_system_config.json"
SEED_PROJECTS_FILE = SEED_DIR / "seed_projects.json"


@router.get(
    "/dump",
    dependencies=[_guard],
    operation_id="dump_database",
)
async def dump_database(
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Dump all database tables to a seed_data.json-compatible JSON structure."""
    service = SystemAdminService(session)
    try:
        data = await service.dump_database()
        return JSONResponse(content=data)
    except Exception as e:
        logger.exception("Database dump failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database dump failed: {e}",
        ) from e


@router.post(
    "/reseed",
    dependencies=[_guard],
    operation_id="reseed_database",
)
async def reseed_database(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Upload a seed_data.json file and reseed the database.

    This will DELETE ALL DATA and reseed from the uploaded file.
    """

    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .json files are accepted",
        )

    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {e}",
        ) from e

    service = SystemAdminService(session)
    try:
        result = await service.reseed_from_upload(data)
    except Exception as e:
        logger.exception("Reseed from upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reseed failed: {e}",
        ) from e

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": result.get("errors", [])},
        )

    return JSONResponse(content=result, status_code=status.HTTP_200_OK)


@router.get(
    "/seed-file",
    dependencies=[_guard],
    operation_id="download_seed_file",
)
async def download_seed_file() -> FileResponse:
    """Download the current seed_data.json file (backward compatibility)."""
    if not SEED_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="seed_data.json not found",
        )
    return FileResponse(
        path=str(SEED_FILE),
        media_type="application/json",
        filename="seed_data.json",
    )


@router.get(
    "/seed-file/system-config",
    dependencies=[_guard],
    operation_id="download_seed_file_system_config",
)
async def download_seed_file_system_config() -> FileResponse:
    """Download the seed_system_config.json file."""
    if not SEED_SYSTEM_CONFIG_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="seed_system_config.json not found",
        )
    return FileResponse(
        path=str(SEED_SYSTEM_CONFIG_FILE),
        media_type="application/json",
        filename="seed_system_config.json",
    )


@router.get(
    "/seed-file/projects",
    dependencies=[_guard],
    operation_id="download_seed_file_projects",
)
async def download_seed_file_projects() -> FileResponse:
    """Download the seed_projects.json file."""
    if not SEED_PROJECTS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="seed_projects.json not found",
        )
    return FileResponse(
        path=str(SEED_PROJECTS_FILE),
        media_type="application/json",
        filename="seed_projects.json",
    )
