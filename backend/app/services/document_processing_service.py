"""Document processing service - text extraction, checksums, and validation."""

import hashlib
import logging

from app.ai.file_extractors import extract_text
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Utility service for document content processing.

    Stateless methods only -- no database or storage dependency.
    """

    @staticmethod
    def extract_text(content: bytes, content_type: str) -> str | None:
        """Extract text from file content.

        Args:
            content: Raw file bytes.
            content_type: MIME type of the file.

        Returns:
            Extracted text string, or None if the type is unsupported
            or extraction fails.
        """
        try:
            return extract_text(content, content_type)
        except (ValueError, Exception):
            logger.warning("Text extraction failed for content_type=%s", content_type)
            return None

    @staticmethod
    def compute_checksum(content: bytes) -> str:
        """Compute SHA-256 hex digest of the given content.

        Args:
            content: Raw file bytes.

        Returns:
            64-character lowercase hex string.
        """
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def validate_file(filename: str, size_bytes: int) -> None:
        """Validate file extension and size against project limits.

        Args:
            filename: Original filename with extension.
            size_bytes: Size of the file in bytes.

        Raises:
            ValueError: If the extension is not allowed or the file exceeds
                the maximum size.
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in set(settings.DOCUMENT_ALLOWED_EXTENSIONS):
            raise ValueError(f"File extension '.{ext}' is not allowed")

        max_bytes = settings.DOCUMENT_MAX_FILE_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"File size {size_bytes / 1024 / 1024:.1f} MB exceeds "
                f"maximum {settings.DOCUMENT_MAX_FILE_SIZE_MB} MB"
            )
