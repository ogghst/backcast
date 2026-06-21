"""Storage service for S3-compatible binary operations (RustFS)."""

import asyncio
import logging
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.config import Config as BotoConfig  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage service for document binary operations."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.RUSTFS_ENDPOINT_URL,
            aws_access_key_id=settings.RUSTFS_ACCESS_KEY,
            aws_secret_access_key=settings.RUSTFS_SECRET_KEY,
            config=BotoConfig(signature_version="s3v4"),
        )
        self._bucket = settings.RUSTFS_BUCKET_NAME
        # Presigning client: signs SigV4 over the PUBLIC host (browser-facing).
        # S3 signatures cover the Host header, so the URL must be presigned against
        # the same host the browser will request — you cannot string-replace the
        # host afterwards (the signature would break → 403). Presigning is pure
        # local computation (no network I/O), so this client never needs to reach
        # RustFS directly. Path-style addressing avoids wildcard cert/DNS for
        # `bucket.host`.
        self._presign_client = boto3.client(
            "s3",
            endpoint_url=settings.RUSTFS_PUBLIC_URL or settings.RUSTFS_ENDPOINT_URL,
            aws_access_key_id=settings.RUSTFS_ACCESS_KEY,
            aws_secret_access_key=settings.RUSTFS_SECRET_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    async def ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist. Call on app startup."""
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            logger.info("Bucket '%s' already exists", self._bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                await asyncio.to_thread(self._client.create_bucket, Bucket=self._bucket)
                logger.info("Bucket '%s' created", self._bucket)
            else:
                raise

    async def upload_file(
        self, key: str, content: bytes, content_type: str
    ) -> dict[str, Any]:
        """Upload binary content to S3."""
        return await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def download_file(self, key: str) -> bytes:
        """Download binary content from S3."""
        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete_file(self, key: str) -> None:
        """Delete an object from S3."""
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=key,
            )
        except ClientError:
            logger.warning("Failed to delete object '%s'", key)
            raise

    async def generate_presigned_url(
        self,
        key: str,
        expiry_seconds: int | None = None,
        filename: str | None = None,
    ) -> str:
        """Generate a presigned download URL.

        Args:
            key: Object key in the bucket.
            expiry_seconds: URL lifetime; falls back to settings default.
            filename: If provided, forces a ``Content-Disposition:
                attachment; filename="<escaped>"`` response header via the S3
                ``ResponseContentDisposition`` presign param. ``"`` and ``\\``
                are replaced with ``_`` to keep the header value valid. When
                ``None``, behavior is unchanged (no attachment header).
        """
        expiry = expiry_seconds or settings.RUSTFS_PRESIGNED_URL_EXPIRY_SECONDS
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
        if filename:
            escaped = filename.replace('"', "_").replace("\\", "_")
            params["ResponseContentDisposition"] = (
                f'attachment; filename="{escaped}"'
            )
        return await asyncio.to_thread(
            self._presign_client.generate_presigned_url,
            "get_object",
            Params=params,
            ExpiresIn=expiry,
        )

    async def file_exists(self, key: str) -> bool:
        """Check if an object exists in S3."""
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise
