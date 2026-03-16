import asyncio
import httpx
import pytest
import pytest_asyncio
from typing import Any
from uuid import UUID, uuid4

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.user import User

# --- Mocks for Auth ---
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
)

def mock_get_current_user() -> User:
    return mock_admin_user

def mock_get_current_active_user() -> User:
    return mock_admin_user

class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return [
            "project-read",
            "change-order-read",
            "change-order-create",
            "change-order-update",
            "change-order-delete",
        ]

def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
app.dependency_overrides[get_rbac_service] = mock_get_rbac_service

async def main():
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        project_data = {
            "name": "CO Test Project",
            "code": "CO-PROJ",
            "budget": 500000,
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["project_id"]
        
        # Create first CO
        co1 = {
            "project_id": project_id,
            "code": "CO-SEARCH-1",
            "title": "Alpha Change",
            "status": "Draft",
            "description": "First CO",
        }
        resp1 = await client.post("/api/v1/change-orders", json=co1)
        print(f"CO1 Status: {resp1.status_code}")
        print(f"CO1 Response: {resp1.text}")
        
        # Create second CO
        co2 = {
            "project_id": project_id,
            "code": "CO-SEARCH-2",
            "title": "Beta Change",
            "status": "Submitted",
            "description": "Second CO",
        }
        resp2 = await client.post("/api/v1/change-orders", json=co2)
        print(f"\nCO2 Status: {resp2.status_code}")
        print(f"CO2 Response: {resp2.text}")

if __name__ == "__main__":
    asyncio.run(main())
