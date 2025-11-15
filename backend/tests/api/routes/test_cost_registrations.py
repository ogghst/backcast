"""Tests for Cost Registrations API routes."""
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.cost_element import create_random_cost_element
from tests.utils.cost_element_schedule import create_schedule_for_cost_element
from tests.utils.cost_registration import create_random_cost_registration
from tests.utils.user import set_time_machine_date


def test_create_cost_registration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration."""
    cost_element = create_random_cost_element(db)

    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": "2024-02-15",
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["amount"] == "1500.00"
    assert content["cost_category"] == "labor"
    assert content["description"] == "Test cost registration"
    assert content["cost_element_id"] == str(cost_element.cost_element_id)
    assert "cost_registration_id" in content
    assert "created_by_id" in content


def test_create_cost_registration_invalid_cost_element(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,  # noqa: ARG001
) -> None:
    """Test creating a cost registration with invalid cost_element_id."""
    data = {
        "cost_element_id": str(uuid.uuid4()),
        "registration_date": "2024-02-15",
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Cost element not found"


def test_create_cost_registration_invalid_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration with invalid cost category."""
    cost_element = create_random_cost_element(db)

    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": "2024-02-15",
        "amount": "1500.00",
        "cost_category": "invalid_category",
        "description": "Test cost registration",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "Invalid cost category" in content["detail"]


def test_create_cost_registration_invalid_amount(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration with invalid amount."""
    cost_element = create_random_cost_element(db)

    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": "2024-02-15",
        "amount": "0.00",
        "cost_category": "labor",
        "description": "Test cost registration",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Amount must be greater than zero"


def test_read_cost_registration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading a single cost registration."""
    cost_registration = create_random_cost_registration(db)
    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["cost_registration_id"] == str(
        cost_registration.cost_registration_id
    )
    assert content["amount"] == str(cost_registration.amount)


def test_read_cost_registrations_list(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading list of cost registrations."""
    cost_element = create_random_cost_element(db)
    cr1 = create_random_cost_registration(
        db, cost_element_id=cost_element.cost_element_id
    )
    cr2 = create_random_cost_registration(
        db, cost_element_id=cost_element.cost_element_id
    )

    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/",
        params={"cost_element_id": str(cost_element.cost_element_id)},
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert "count" in content
    assert content["count"] == 2

    # Verify the created registrations are in the response
    registration_ids = [cr["cost_registration_id"] for cr in content["data"]]
    assert str(cr1.cost_registration_id) in registration_ids
    assert str(cr2.cost_registration_id) in registration_ids


def test_read_cost_registrations_filtered_by_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading cost registrations filtered by cost element ID."""
    cost_element1 = create_random_cost_element(db)
    cost_element2 = create_random_cost_element(db)

    cr1 = create_random_cost_registration(
        db, cost_element_id=cost_element1.cost_element_id
    )
    cr2 = create_random_cost_registration(
        db, cost_element_id=cost_element1.cost_element_id
    )
    cr3 = create_random_cost_registration(
        db, cost_element_id=cost_element2.cost_element_id
    )

    # Filter by cost_element1
    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/",
        params={"cost_element_id": str(cost_element1.cost_element_id)},
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2

    registration_ids = [cr["cost_registration_id"] for cr in content["data"]]
    assert str(cr1.cost_registration_id) in registration_ids
    assert str(cr2.cost_registration_id) in registration_ids
    assert str(cr3.cost_registration_id) not in registration_ids


def test_read_cost_registrations_respect_time_machine(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Time machine date should hide registrations after the control date."""
    cost_element = create_random_cost_element(db)
    control_date = date.today()
    earlier = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=control_date,
    )
    later = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=control_date + timedelta(days=10),
    )

    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    ids = [item["cost_registration_id"] for item in content["data"]]
    assert str(earlier.cost_registration_id) in ids
    assert str(later.cost_registration_id) not in ids


def test_read_cost_registrations_time_machine_future_includes(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Setting time machine to future date should include later registrations."""
    cost_element = create_random_cost_element(db)
    control_date = date.today()
    future_date = control_date + timedelta(days=30)
    earlier = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=control_date,
    )
    later = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=future_date,
    )

    set_time_machine_date(client, superuser_token_headers, future_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    ids = [item["cost_registration_id"] for item in content["data"]]
    assert str(earlier.cost_registration_id) in ids
    assert str(later.cost_registration_id) in ids


def test_read_cost_registrations_excludes_late_created_entries(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Registrations created after the control date should stay hidden."""
    cost_element = create_random_cost_element(db)
    control_date = date(2024, 2, 20)

    visible = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=control_date,
        created_at=datetime(2024, 2, 20, tzinfo=timezone.utc),
    )

    hidden = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=control_date,
    )
    hidden.created_at = datetime(2024, 3, 5, tzinfo=timezone.utc)
    db.add(hidden)
    db.commit()
    db.refresh(hidden)

    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/",
        params={"cost_element_id": str(cost_element.cost_element_id)},
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    ids = [item["cost_registration_id"] for item in data]
    assert str(visible.cost_registration_id) in ids
    assert str(hidden.cost_registration_id) not in ids


def test_update_cost_registration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a cost registration."""
    cost_registration = create_random_cost_registration(db)

    data = {
        "amount": "2000.00",
        "description": "Updated description",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["amount"] == "2000.00"
    assert content["description"] == "Updated description"
    assert content["cost_category"] == cost_registration.cost_category  # Unchanged


def test_update_cost_registration_invalid_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a cost registration with invalid category."""
    cost_registration = create_random_cost_registration(db)

    data = {
        "cost_category": "invalid_category",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "Invalid cost category" in content["detail"]


def test_update_cost_registration_invalid_amount(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a cost registration with invalid amount."""
    cost_registration = create_random_cost_registration(db)

    data = {
        "amount": "-100.00",
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "Amount must be greater than zero" in content["detail"]


def test_delete_cost_registration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting a cost registration."""
    cost_registration = create_random_cost_registration(db)

    response = client.delete(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Cost registration deleted successfully"

    # Verify it's deleted
    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_read_cost_registration_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Test reading a non-existent cost registration."""
    response = client.get(
        f"{settings.API_V1_STR}/cost-registrations/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404


def test_create_cost_registration_all_categories(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating cost registrations with all valid categories."""
    cost_element = create_random_cost_element(db)
    valid_categories = ["labor", "materials", "subcontractors"]

    for category in valid_categories:
        data = {
            "cost_element_id": str(cost_element.cost_element_id),
            "registration_date": "2024-02-15",
            "amount": "1000.00",
            "cost_category": category,
            "description": f"Test {category} cost",
            "is_quality_cost": False,
        }
        response = client.post(
            f"{settings.API_V1_STR}/cost-registrations/",
            headers=superuser_token_headers,
            json=data,
        )
        assert response.status_code == 200
        content = response.json()
        assert content["cost_category"] == category


def test_create_cost_registration_before_schedule_start_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration with date before schedule start_date should fail."""
    cost_element = create_random_cost_element(db)

    # Create schedule with start_date = today, end_date = today + 30 days
    schedule_start = date.today()
    schedule_end = date.today() + timedelta(days=30)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=schedule_start,
        end_date=schedule_end,
    )

    # Try to create registration with date before start_date
    registration_date = schedule_start - timedelta(days=1)
    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": registration_date.isoformat(),
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration before start",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "registration date" in content["detail"].lower()
    assert "before" in content["detail"].lower() or "start" in content["detail"].lower()


def test_create_cost_registration_after_schedule_end_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration with date after schedule end_date should succeed with warning."""
    cost_element = create_random_cost_element(db)

    # Create schedule with start_date = today, end_date = today + 30 days
    schedule_start = date.today()
    schedule_end = date.today() + timedelta(days=30)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=schedule_start,
        end_date=schedule_end,
    )

    # Create registration with date after end_date (should succeed with warning)
    registration_date = schedule_end + timedelta(days=1)
    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": registration_date.isoformat(),
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration after end",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["amount"] == "1500.00"
    # Check that warning is included in response
    assert "warning" in content
    assert "after" in content["warning"].lower() or "end" in content["warning"].lower()


def test_create_cost_registration_within_schedule_bounds(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration with date within schedule bounds should succeed without warning."""
    cost_element = create_random_cost_element(db)

    # Create schedule with start_date = today, end_date = today + 30 days
    schedule_start = date.today()
    schedule_end = date.today() + timedelta(days=30)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=schedule_start,
        end_date=schedule_end,
    )

    # Create registration with date within bounds
    registration_date = schedule_start + timedelta(days=15)  # Middle of schedule
    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": registration_date.isoformat(),
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration within bounds",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["amount"] == "1500.00"
    # Check that no warning is included in response
    assert "warning" not in content or content.get("warning") is None


def test_create_cost_registration_without_schedule(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating a cost registration when cost element has no schedule should succeed."""
    cost_element = create_random_cost_element(db)
    # No schedule created

    # Create registration (should succeed - no schedule means no validation)
    registration_date = date.today()
    data = {
        "cost_element_id": str(cost_element.cost_element_id),
        "registration_date": registration_date.isoformat(),
        "amount": "1500.00",
        "cost_category": "labor",
        "description": "Test cost registration without schedule",
        "is_quality_cost": False,
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-registrations/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["amount"] == "1500.00"
    # No warning should be present
    assert "warning" not in content or content.get("warning") is None


def test_update_cost_registration_date_before_start(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating a cost registration date to before schedule start_date should fail."""
    cost_element = create_random_cost_element(db)

    # Create schedule with start_date = today, end_date = today + 30 days
    schedule_start = date.today()
    schedule_end = date.today() + timedelta(days=30)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=schedule_start,
        end_date=schedule_end,
    )

    # Create initial registration with valid date
    valid_date = schedule_start + timedelta(days=10)
    cost_registration = create_random_cost_registration(
        db,
        cost_element_id=cost_element.cost_element_id,
        registration_date=valid_date,
    )

    # Try to update registration date to before start_date
    invalid_date = schedule_start - timedelta(days=1)
    data = {
        "registration_date": invalid_date.isoformat(),
    }
    response = client.put(
        f"{settings.API_V1_STR}/cost-registrations/{cost_registration.cost_registration_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert "registration date" in content["detail"].lower()
    assert "before" in content["detail"].lower() or "start" in content["detail"].lower()
