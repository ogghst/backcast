"""API routes for AI chat file and image uploads.

Provides endpoints for:
- Image uploads for AI chat messages
- File attachments (documents, spreadsheets, etc.)
- Static file serving for uploaded content
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.config import settings
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
}

# Base upload directory
UPLOAD_BASE_DIR = Path(__file__).parent.parent.parent.parent / "uploads" / "ai"
IMAGES_DIR = UPLOAD_BASE_DIR / "images"
DOCUMENTS_DIR = UPLOAD_BASE_DIR / "documents"

# Ensure directories exist
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename using UUID prefix.

    Args:
        original_filename: Original filename from upload

    Returns:
        Unique filename with UUID prefix
    """
    file_extension = Path(original_filename).suffix
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_extension}"


def get_file_url(file_id: str, file_type: str) -> str:
    """Generate URL for accessing an uploaded file.

    Args:
        file_id: Unique file identifier
        file_type: Type of file ('image' or 'document')

    Returns:
        URL to access the file
    """
    if file_type == "image":
        return f"{settings.API_V1_STR}/ai/chat/images/{file_id}"
    else:
        return f"{settings.API_V1_STR}/ai/chat/documents/{file_id}"


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

    Validates the image file, stores it in the uploads directory,
    and returns a URL that can be included in chat messages.

    Args:
        file: Image file to upload (PNG, JPG, JPEG)
        current_user: Authenticated user

    Returns:
        ImageUploadResponse with file URL and metadata

    Raises:
        HTTPException 400: Invalid file type or size
        HTTPException 500: Failed to save file
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

    # Generate unique filename
    file_id = generate_unique_filename(file.filename or "image")
    file_path = IMAGES_DIR / file_id

    try:
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Image uploaded: {file_id} by user {current_user.user_id}")

        return ImageUploadResponse(
            file_id=file_id,
            filename=file.filename or "image",
            url=get_file_url(file_id, "image"),
            file_size=len(content),
            content_type=file.content_type,
            uploaded_at=datetime.utcnow(),
        )
    except Exception as err:
        logger.error(f"Failed to save image: {err}", exc_info=True)
        # Clean up partial file if it exists
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image",
        ) from err


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
            description="Document file (PDF, DOCX, XLSX, TXT, CSV, JSON, max 10MB)"
        ),
    ],
    current_user: User = Depends(get_current_active_user),
) -> FileUploadResponse:
    """Upload a file attachment for AI chat.

    Validates the document file, stores it in the uploads directory,
    and returns a URL that can be included in chat messages.

    Args:
        file: Document file to upload
        current_user: Authenticated user

    Returns:
        FileUploadResponse with file URL and metadata

    Raises:
        HTTPException 400: Invalid file type or size
        HTTPException 500: Failed to save file
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

    # Generate unique filename
    file_id = generate_unique_filename(file.filename or "document")
    file_path = DOCUMENTS_DIR / file_id

    # Determine file category
    extension = ALLOWED_DOCUMENT_TYPES[file.content_type]
    if extension in ["pdf", "docx", "txt"]:
        file_type = "document"
    elif extension in ["xlsx", "csv"]:
        file_type = "spreadsheet"
    elif extension == "json":
        file_type = "data"
    else:
        file_type = "other"

    try:
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(
            f"File uploaded: {file_id} ({file_type}) by user {current_user.user_id}"
        )

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename or "document",
            url=get_file_url(file_id, "document"),
            file_size=len(content),
            content_type=file.content_type,
            file_type=file_type,
            uploaded_at=datetime.utcnow(),
        )
    except Exception as err:
        logger.error(f"Failed to save file: {err}", exc_info=True)
        # Clean up partial file if it exists
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        ) from err


@router.get(
    "/images/{file_id}",
    operation_id="get_ai_image",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def get_image(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Retrieve an uploaded image by file ID.

    Args:
        file_id: Unique file identifier
        current_user: Authenticated user

    Returns:
        The image file

    Raises:
        HTTPException 404: File not found
    """
    file_path = IMAGES_DIR / file_id

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Determine content type from file extension
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        content_type = "image/png"
    elif suffix in [".jpg", ".jpeg"]:
        content_type = "image/jpeg"
    else:
        content_type = "image/png"

    from fastapi.responses import FileResponse

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=file_id,
    )


@router.get(
    "/documents/{file_id}",
    operation_id="get_ai_document",
    dependencies=[Depends(RoleChecker(required_permission="ai-chat"))],
)
async def get_document(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Retrieve an uploaded document by file ID.

    Args:
        file_id: Unique file identifier
        current_user: Authenticated user

    Returns:
        The document file

    Raises:
        HTTPException 404: File not found
    """
    file_path = DOCUMENTS_DIR / file_id

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Determine content type from file extension
    suffix = file_path.suffix.lower()
    content_type_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }
    content_type = content_type_map.get(suffix, "application/octet-stream")

    from fastapi.responses import FileResponse

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=file_id,
    )
