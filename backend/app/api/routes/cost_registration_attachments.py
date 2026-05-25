"""Cost Registration Attachment API routes - upload, list, download, delete."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.domain.cost_registration_attachment import CostRegistrationAttachment
from app.models.schemas.cost_registration_attachment import (
    CostRegistrationAttachmentRead,
)
from app.services.cost_registration_attachment_service import (
    CostRegistrationAttachmentService,
)

router = APIRouter()

# Max file size in bytes (from settings, default 10MB)
MAX_FILE_SIZE = settings.COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB * 1024 * 1024


def _get_attachment_service(
    session: AsyncSession = Depends(get_db),
) -> CostRegistrationAttachmentService:
    return CostRegistrationAttachmentService(session)


@router.get(
    "/{cost_registration_id}/attachments",
    response_model=list[CostRegistrationAttachmentRead],
    operation_id="list_cost_registration_attachments",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def list_attachments(
    cost_registration_id: UUID,
    service: CostRegistrationAttachmentService = Depends(_get_attachment_service),
) -> list[CostRegistrationAttachment]:
    """List all attachments for a cost registration."""
    return await service.list_attachments(cost_registration_id)


@router.post(
    "/{cost_registration_id}/attachments",
    response_model=CostRegistrationAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_cost_registration_attachment",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-update"))],
)
async def upload_attachment(
    cost_registration_id: UUID,
    file: Annotated[
        UploadFile, File(description="File to attach (max size configurable)")
    ],
    current_user: UserIdentity = Depends(get_current_user),
    service: CostRegistrationAttachmentService = Depends(_get_attachment_service),
) -> CostRegistrationAttachment:
    """Upload a file attachment to a cost registration.

    All file types are allowed. Maximum file size is configurable via
    COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB env variable (default 10MB).
    """
    # Pre-check file size before reading content
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File too large. Maximum size: "
                f"{settings.COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB}MB"
            ),
        )

    # Read file content
    content = await file.read()

    # Validate file size (fallback for chunked transfers without known size)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File too large. Maximum size: "
                f"{settings.COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB}MB"
            ),
        )

    # Store attachment
    return await service.add_attachment(
        cost_registration_id=cost_registration_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )


@router.get(
    "/{cost_registration_id}/attachments/{attachment_id}",
    response_class=Response,
    operation_id="download_cost_registration_attachment",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-read"))],
)
async def download_attachment(
    cost_registration_id: UUID,
    attachment_id: UUID,
    service: CostRegistrationAttachmentService = Depends(_get_attachment_service),
) -> Response:
    """Download an attachment (returns raw binary content)."""
    attachment = await service.get_attachment(attachment_id)
    if attachment is None or attachment.cost_registration_id != cost_registration_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    # Sanitize filename to prevent header injection (strip quotes, CR, LF)
    safe_filename = attachment.filename.replace('"', '').replace('\r', '').replace('\n', '')
    return Response(
        content=attachment.content,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


@router.delete(
    "/{cost_registration_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_registration_attachment",
    dependencies=[Depends(RoleChecker(required_permission="cost-registration-update"))],
)
async def delete_attachment(
    cost_registration_id: UUID,
    attachment_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostRegistrationAttachmentService = Depends(_get_attachment_service),
) -> None:
    """Delete an attachment from a cost registration."""
    # Verify attachment belongs to this cost registration
    attachment = await service.get_attachment(attachment_id)
    if attachment is None or attachment.cost_registration_id != cost_registration_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    await service.delete_attachment(attachment_id)
