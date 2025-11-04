import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.cost_element import create_random_cost_element
from tests.utils.cost_element_schedule import create_schedule_for_cost_element


def test_get_schedule_by_cost_element_id(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting schedule for a cost element."""
    # Setup: Create project, WBE, cost element, schedule
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        progression_type="linear",
    )

    # Test: GET /cost-element-schedules/?cost_element_id={id}
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["cost_element_id"] == str(cost_element.cost_element_id)
    assert content["start_date"] == "2025-01-01"
    assert content["end_date"] == "2025-12-31"
    assert content["progression_type"] == "linear"


def test_get_schedule_not_found(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting schedule for cost element without schedule returns 404."""
    cost_element = create_random_cost_element(db)

    # Test: GET /cost-element-schedules/?cost_element_id={id}
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_get_schedule_invalid_cost_element_id(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test getting schedule with invalid cost_element_id."""
    invalid_id = uuid.uuid4()

    # Test: GET /cost-element-schedules/?cost_element_id={invalid_id}
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(invalid_id)},
    )
    assert response.status_code == 404


def test_create_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a new schedule."""
    # Setup
    cost_element = create_random_cost_element(db)

    # Test: POST /cost-element-schedules/?cost_element_id={id}
    schedule_data = {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "progression_type": "linear",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/?cost_element_id={cost_element.cost_element_id}",
        headers=superuser_token_headers,
        json=schedule_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["start_date"] == "2025-01-01"
    assert content["end_date"] == "2025-12-31"
    assert content["progression_type"] == "linear"
    assert content["cost_element_id"] == str(cost_element.cost_element_id)


def test_create_schedule_invalid_dates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating schedule with end_date < start_date should fail."""
    # Setup
    cost_element = create_random_cost_element(db)

    # Test: POST with invalid dates
    schedule_data = {
        "start_date": "2025-12-31",
        "end_date": "2025-01-01",  # End before start
        "progression_type": "linear",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/?cost_element_id={cost_element.cost_element_id}",
        headers=superuser_token_headers,
        json=schedule_data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "end_date must be greater than or equal to start_date" in content["detail"]


def test_create_schedule_invalid_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test creating schedule with invalid cost_element_id should fail."""
    invalid_id = uuid.uuid4()

    schedule_data = {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "progression_type": "linear",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/?cost_element_id={invalid_id}",
        headers=superuser_token_headers,
        json=schedule_data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_update_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a schedule."""
    # Setup: Create schedule
    cost_element = create_random_cost_element(db)
    schedule = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        progression_type="linear",
    )

    # Test: PUT /cost-element-schedules/{id}
    update_data = {
        "start_date": "2025-02-01",
        "end_date": "2025-11-30",
        "progression_type": "gaussian",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-element-schedules/{schedule.schedule_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["start_date"] == "2025-02-01"
    assert content["end_date"] == "2025-11-30"
    assert content["progression_type"] == "gaussian"
    assert content["schedule_id"] == str(schedule.schedule_id)


def test_update_schedule_invalid_dates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating schedule with end_date < start_date should fail."""
    # Setup
    cost_element = create_random_cost_element(db)
    schedule = create_schedule_for_cost_element(db, cost_element.cost_element_id)

    # Test: PUT with invalid dates
    update_data = {
        "start_date": "2025-12-31",
        "end_date": "2025-01-01",  # End before start
        "progression_type": "linear",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-element-schedules/{schedule.schedule_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "end_date must be greater than or equal to start_date" in content["detail"]


def test_update_schedule_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test updating a schedule that doesn't exist returns 404."""
    invalid_id = uuid.uuid4()

    update_data = {
        "start_date": "2025-02-01",
        "end_date": "2025-11-30",
        "progression_type": "gaussian",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-element-schedules/{invalid_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()


def test_delete_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a schedule."""
    # Setup
    cost_element = create_random_cost_element(db)
    schedule = create_schedule_for_cost_element(db, cost_element.cost_element_id)

    # Test: DELETE /cost-element-schedules/{id}
    response = client.delete(
        f"{settings.API_V1_STR}/cost-element-schedules/{schedule.schedule_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Schedule deleted successfully"

    # Verify deleted - GET should return 404
    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 404


def test_delete_schedule_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test deleting a schedule that doesn't exist returns 404."""
    invalid_id = uuid.uuid4()

    response = client.delete(
        f"{settings.API_V1_STR}/cost-element-schedules/{invalid_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert "not found" in content["detail"].lower()
