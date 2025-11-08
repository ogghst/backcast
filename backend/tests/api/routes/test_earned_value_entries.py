"""Tests for Earned Value Entries API routes."""
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.cost_element import create_random_cost_element
from tests.utils.cost_element_schedule import create_schedule_for_cost_element
from tests.utils.earned_value_entry import create_earned_value_entry


def _post_earned_value_entry(
    client: TestClient,
    headers: dict[str, str],
    payload: dict[str, str],
):
    return client.post(
        f"{settings.API_V1_STR}/earned-value-entries/",
        headers=headers,
        json=payload,
    )


def test_create_earned_value_entry_success(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test creating an earned value entry derives earned value from BAC."""
    cost_element = create_random_cost_element(db)

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-03-15",
        "percent_complete": "55.00",
        "deliverables": "Phase 1 deliverables",
        "description": "Completed initial phase",
    }

    response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert response.status_code == 200
    content = response.json()
    assert content["cost_element_id"] == str(cost_element.cost_element_id)
    assert content["percent_complete"] == "55.00"
    assert content["earned_value"] == "5500.00"
    assert content["deliverables"] == "Phase 1 deliverables"
    assert content["description"] == "Completed initial phase"
    assert "warning" not in content


def test_create_earned_value_entry_requires_deliverables(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Deliverables description must be provided."""
    cost_element = create_random_cost_element(db)

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-03-20",
        "percent_complete": "25.00",
        "deliverables": "",
        "description": "Partial progress",
    }

    response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Deliverables description is required"


def test_create_earned_value_entry_percent_out_of_range(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Percent complete must be between 0 and 100."""
    cost_element = create_random_cost_element(db)

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-04-01",
        "percent_complete": "150.00",
        "deliverables": "Invalid percent",
        "description": "Should fail",
    }

    response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "percent_complete must be between 0 and 100"


def test_create_earned_value_entry_duplicate_completion_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Only one entry per cost element per completion date is allowed."""
    cost_element = create_random_cost_element(db)

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-05-01",
        "percent_complete": "30.00",
        "deliverables": "First milestone",
        "description": "Baseline entry",
    }

    first_response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert first_response.status_code == 200

    duplicate_response = _post_earned_value_entry(
        client, superuser_token_headers, payload
    )
    assert duplicate_response.status_code == 400
    content = duplicate_response.json()
    assert (
        content["detail"]
        == "An earned value entry for this date already exists for the cost element"
    )


def test_create_earned_value_entry_before_schedule_start(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Completion date cannot be before schedule start date."""
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=date(2025, 3, 1),
        end_date=date(2025, 9, 30),
    )

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-02-01",
        "percent_complete": "10.00",
        "deliverables": "Pre-start work",
        "description": "Should be blocked",
    }

    response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert response.status_code == 400
    content = response.json()
    assert (
        content["detail"]
        == "Completion date (2025-02-01) cannot be before schedule start date (2025-03-01)"
    )


def test_create_earned_value_entry_after_schedule_end_warning(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Completion date after schedule end returns warning but succeeds."""
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element_id=cost_element.cost_element_id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )

    payload = {
        "cost_element_id": str(cost_element.cost_element_id),
        "completion_date": "2025-02-15",
        "percent_complete": "20.00",
        "deliverables": "Late milestone",
        "description": "Should warn",
    }

    response = _post_earned_value_entry(client, superuser_token_headers, payload)
    assert response.status_code == 200
    content = response.json()
    assert content["earned_value"] == "2000.00"
    assert "warning" in content
    assert "after schedule end date" in content["warning"]


def test_read_earned_value_entry(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test reading a single earned value entry."""
    cost_element = create_random_cost_element(db)
    entry = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2025, 6, 1),
        percent_complete=Decimal("40.00"),
    )

    response = client.get(
        f"{settings.API_V1_STR}/earned-value-entries/{entry.earned_value_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["earned_value_id"] == str(entry.earned_value_id)
    assert content["percent_complete"] == "40.00"
    assert content["earned_value"] == "4000.00"


def test_list_earned_value_entries_filtered_by_cost_element(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """List endpoint filters by cost element ID."""
    cost_element1 = create_random_cost_element(db)
    cost_element2 = create_random_cost_element(db)

    entry1 = create_earned_value_entry(
        db,
        cost_element_id=cost_element1.cost_element_id,
        completion_date=date(2025, 7, 1),
        percent_complete=Decimal("30.00"),
    )
    entry2 = create_earned_value_entry(
        db,
        cost_element_id=cost_element1.cost_element_id,
        completion_date=date(2025, 8, 1),
        percent_complete=Decimal("60.00"),
    )
    create_earned_value_entry(
        db,
        cost_element_id=cost_element2.cost_element_id,
        completion_date=date(2025, 7, 1),
        percent_complete=Decimal("20.00"),
    )

    response = client.get(
        f"{settings.API_V1_STR}/earned-value-entries/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element1.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2
    returned_ids = {item["earned_value_id"] for item in content["data"]}
    assert str(entry1.earned_value_id) in returned_ids
    assert str(entry2.earned_value_id) in returned_ids


def test_update_earned_value_entry(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Updating percent_complete recalculates earned value."""
    cost_element = create_random_cost_element(db)
    entry = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2025, 9, 1),
        percent_complete=Decimal("25.00"),
    )

    payload = {
        "percent_complete": "80.00",
        "description": "Updated progress",
        "deliverables": "Updated deliverables",
    }

    response = client.put(
        f"{settings.API_V1_STR}/earned-value-entries/{entry.earned_value_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["percent_complete"] == "80.00"
    assert content["earned_value"] == "8000.00"
    assert content["description"] == "Updated progress"
    assert content["deliverables"] == "Updated deliverables"


def test_update_earned_value_entry_duplicate_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Updating to an existing completion date should fail."""
    cost_element = create_random_cost_element(db)
    # first_entry = create_earned_value_entry(
    #    db,
    #    cost_element_id=cost_element.cost_element_id,
    #    completion_date=date(2025, 10, 1),
    #    percent_complete=Decimal("40.00"),
    # )
    second_entry = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2025, 11, 1),
        percent_complete=Decimal("60.00"),
    )

    payload = {
        "completion_date": "2025-10-01",
    }

    response = client.put(
        f"{settings.API_V1_STR}/earned-value-entries/{second_entry.earned_value_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 400
    content = response.json()
    assert (
        content["detail"]
        == "An earned value entry for this date already exists for the cost element"
    )


def test_delete_earned_value_entry(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test deleting an earned value entry."""
    cost_element = create_random_cost_element(db)
    entry = create_earned_value_entry(
        db,
        cost_element_id=cost_element.cost_element_id,
        completion_date=date(2025, 12, 1),
        percent_complete=Decimal("50.00"),
    )

    response = client.delete(
        f"{settings.API_V1_STR}/earned-value-entries/{entry.earned_value_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Earned value entry deleted successfully"

    # Verify entry no longer exists
    get_response = client.get(
        f"{settings.API_V1_STR}/earned-value-entries/{entry.earned_value_id}",
        headers=superuser_token_headers,
    )
    assert get_response.status_code == 404
