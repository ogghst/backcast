"""API routes for AI chat file and image uploads.

Provides endpoints for:
- Image uploads for AI chat messages (stored as base64)
- File attachments (documents, spreadsheets, etc.) with text extraction
"""

import base64
import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.ai.file_extractors import extract_text
from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.models.domain.user import User
from app.models.schemas.ai import FileUploadResponse, ImageUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["AI Upload"])

# Upload configuration
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/json": "json",
    "text/markdown": "md",
}


@router.post(
    "/upload-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_ai_image",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def upload_image(
    file: Annotated[UploadFile, File(description="Image file (PNG, JPG, JPEG, max 5MB)")],
    current_user: User = Depends(get_current_active_user),
) -> ImageUploadResponse:
    """Upload an image for AI chat.

    Reads the image bytes, base64-encodes them, and returns the encoded
    content for inline use in chat messages. No disk storage is used.

    Args:
        file: Image file to upload (PNG, JPG, JPEG)
        current_user: Authenticated user

    Returns:
        ImageUploadResponse with base64-encoded content and metadata

    Raises:
        HTTPException 400: Invalid file type or size
    """
    # Validate content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES.keys())}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE / (1024*1024):.0f}MB",
        )

    # Base64-encode image content
    file_id = str(uuid.uuid4())
    encoded = base64.b64encode(content).decode("ascii")

    logger.info(f"Image uploaded: {file_id} by user {current_user.user_id}")

    return ImageUploadResponse(
        file_id=file_id,
        filename=file.filename or "image",
        content=encoded,
        file_size=len(content),
        content_type=file.content_type,
        uploaded_at=datetime.utcnow(),
    )


@router.post(
    "/upload-file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_ai_file",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def upload_file(
    file: Annotated[
        UploadFile,
        File(
            description="Document file (PDF, DOCX, XLSX, PPTX, TXT, CSV, JSON, MD, max 10MB)"
        ),
    ],
    current_user: User = Depends(get_current_active_user),
) -> FileUploadResponse:
    """Upload a file attachment for AI chat.

    Reads the file bytes, extracts text content using the appropriate
    extractor, and returns it for inline use in chat messages.
    No disk storage is used.

    Args:
        file: Document file to upload
        current_user: Authenticated user

    Returns:
        FileUploadResponse with extracted text content and metadata

    Raises:
        HTTPException 400: Invalid file type, size, or extraction failure
    """
    # Validate content type
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_DOCUMENT_TYPES.keys())}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB",
        )

    # Determine file category
    extension = ALLOWED_DOCUMENT_TYPES[file.content_type]
    if extension in ("pdf", "docx", "txt", "md"):
        file_type = "document"
    elif extension in ("xlsx", "csv"):
        file_type = "spreadsheet"
    elif extension == "json":
        file_type = "data"
    else:
        file_type = "other"

    # Extract text content
    file_id = str(uuid.uuid4())
    try:
        extracted = extract_text(content, file.content_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if extracted is None and extension not in ("txt", "csv", "json", "md"):
        # Extraction failed for a binary type that should have worked
        logger.warning(
            "Text extraction returned None for content_type=%s, file_id=%s",
            file.content_type,
            file_id,
        )

    logger.info(
        "File uploaded: %s (%s) by user %s",
        file_id,
        file_type,
        current_user.user_id,
    )

    return FileUploadResponse(
        file_id=file_id,
        filename=file.filename or "document",
        content=extracted,
        file_size=len(content),
        content_type=file.content_type,
        file_type=file_type,
        uploaded_at=datetime.utcnow(),
    )
