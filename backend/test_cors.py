#!/usr/bin/env python3
"""Test CORS configuration."""

from app.core.config import settings

print("=== CORS Configuration ===")
print(f"BACKEND_CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
print(f"Type: {type(settings.BACKEND_CORS_ORIGINS)}")
print(f"Length: {len(settings.BACKEND_CORS_ORIGINS)}")
print()
print("Origins:")
for i, origin in enumerate(settings.BACKEND_CORS_ORIGINS, 1):
    print(f"  {i}. {repr(origin)}")
print()
print(f"'http://localhost:5173' in origins: {'http://localhost:5173' in settings.BACKEND_CORS_ORIGINS}")
print()
print(f"BACKEND_CORS_METHODS: {settings.BACKEND_CORS_METHODS}")
print(f"BACKEND_CORS_HEADERS: {settings.BACKEND_CORS_HEADERS}")
