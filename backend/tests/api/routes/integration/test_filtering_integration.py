from typing import Any

from fastapi.testclient import TestClient

from app.main import app


class TestFilteringIntegration:
    """Integration tests for filter error handling in API."""

    def test_api_returns_400_on_filter_value_error(self) -> None:
        """Test that invalid filter value returns 400."""
        client = TestClient(app)
        # Note: We need a route that uses filtering.
        # /projects endpoint usually requires auth, but the filter parsing might happen
        # before auth or we can use a dependency override to bypass auth if needed.
        # However, looking at the 401 response earlier, auth check comes first.
        # So we should rely on unit tests or mock auth.
        # But wait, we can just check if we can get past auth or simply trust the unit tests + exception handler registration.
        # Let's try to verify the exception handler logic specifically.
        # We can define a dummy route for testing purposes in this test file to avoid auth issues.

        from fastapi import APIRouter

        from app.core.filtering import FilterParser
        from app.models.domain.project import Project

        router = APIRouter()

        @router.get("/test-filter-error")
        def test_route(filters: str | None = None) -> dict[str, Any]:
            parsed = FilterParser.parse_filters(filters)
            # This triggers the build logic which raises the error
            FilterParser.build_sqlalchemy_filters(Project, parsed)
            return {"ok": True}

        app.include_router(router)

        # Now hit this test route
        response = client.get("/test-filter-error?filters=budget:invalid_number")

        # Should be 400 Bad Request due to global exception handler
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid filter value" in data["detail"]
        # Allow Decimal or float since both are reasonable numeric expectations
        msg = data["detail"]
        assert any(
            t in msg
            for t in [
                "expected float",
                "expected int",
                "expected Numeric",
                "expected Decimal",
            ]
        )
