"""Unit tests for StorageService presigned-URL host selection.

Presigning is pure local SigV4 computation (no network I/O), so these tests
need no live RustFS connection. They verify that the presigned URL is signed
over the public host when ``RUSTFS_PUBLIC_URL`` is set, and falls back to
``RUSTFS_ENDPOINT_URL`` when it is empty.
"""

import pytest

from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_presigned_url_uses_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Presigned URL must be signed over RUSTFS_PUBLIC_URL when set."""
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_PUBLIC_URL",
        "https://storage.example.com",
    )
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_ENDPOINT_URL",
        "http://rustfs:9000",
    )

    svc = StorageService()
    url = await svc.generate_presigned_url("some/key")

    assert url.startswith("https://storage.example.com/")
    assert "some/key" in url
    # SigV4 query params present (signature covers the public Host header).
    assert "X-Amz-Signature=" in url
    assert "X-Amz-" in url


@pytest.mark.asyncio
async def test_presigned_url_falls_back_to_endpoint_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty RUSTFS_PUBLIC_URL falls back to RUSTFS_ENDPOINT_URL."""
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_PUBLIC_URL",
        "",
    )
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_ENDPOINT_URL",
        "http://localhost:9000",
    )

    svc = StorageService()
    url = await svc.generate_presigned_url("another/key")

    assert url.startswith("http://localhost:9000/")
    assert "another/key" in url


@pytest.mark.asyncio
async def test_presigned_url_with_filename_sets_content_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passing ``filename`` injects a ResponseContentDisposition presign param."""
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_PUBLIC_URL",
        "https://storage.example.com",
    )

    svc = StorageService()
    url = await svc.generate_presigned_url("some/key", filename='weird".md')

    assert "response-content-disposition" in url
    assert "attachment" in url
    assert "filename%3D%22weird_.md%22" in url or 'filename="weird_.md"' in url


@pytest.mark.asyncio
async def test_presigned_url_without_filename_omits_content_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitting ``filename`` leaves existing behavior unchanged."""
    monkeypatch.setattr(
        "app.services.storage_service.settings.RUSTFS_PUBLIC_URL",
        "https://storage.example.com",
    )

    svc = StorageService()
    url = await svc.generate_presigned_url("some/key")

    assert "response-content-disposition" not in url
