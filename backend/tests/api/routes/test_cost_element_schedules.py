import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import WBE, BaselineLog, Project
from tests.utils.cost_element import create_random_cost_element
from tests.utils.cost_element_schedule import create_schedule_for_cost_element
from tests.utils.user import set_time_machine_date


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
        registration_date=date(2024, 11, 15),
        description="Initial rollout plan",
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
    assert content["registration_date"] == "2024-11-15"
    assert content["description"] == "Initial rollout plan"


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
        "registration_date": "2024-10-01",
        "description": "Initial schedule submission",
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
    assert content["registration_date"] == "2024-10-01"
    assert content["description"] == "Initial schedule submission"


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
        "registration_date": "2024-10-01",
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
        "registration_date": "2025-01-10",
        "description": "Adjusted for supplier change",
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
    assert content["registration_date"] == "2025-01-10"
    assert content["description"] == "Adjusted for supplier change"


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
        "registration_date": "2024-10-01",
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


def test_get_schedule_returns_latest_registration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """The GET endpoint should surface the latest registration by registration_date."""
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 11, 1),
        description="Initial",
    )
    create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2025, 2, 1),
        end_date=date(2025, 6, 30),
        progression_type="gaussian",
        registration_date=date(2025, 1, 20),
        description="Rebaseline",
    )

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["registration_date"] == "2025-01-20"
    assert content["description"] == "Rebaseline"
    assert content["progression_type"] == "gaussian"


def test_create_schedule_defaults_registration_date_to_today(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Registration date defaults to today's date when omitted."""
    cost_element = create_random_cost_element(db)

    payload = {
        "start_date": "2025-04-01",
        "end_date": "2025-09-30",
        "progression_type": "logarithmic",
    }
    response = client.post(
        f"{settings.API_V1_STR}/cost-element-schedules/?cost_element_id={cost_element.cost_element_id}",
        headers=superuser_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["registration_date"] == date.today().isoformat()


def test_list_schedule_history_orders_by_registration_date(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """History endpoint should order registrations newest first."""
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 10),
        description="Initial",
    )
    second = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 4, 1),
        end_date=date(2024, 6, 30),
        progression_type="gaussian",
        registration_date=date(2024, 3, 5),
        description="Spring replan",
    )
    latest = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 7, 1),
        end_date=date(2024, 9, 30),
        progression_type="logarithmic",
        registration_date=date(2024, 5, 20),
        description="Summer acceleration",
    )

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/history",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    registration_dates = [entry["registration_date"] for entry in content]
    assert registration_dates == [
        latest.registration_date.isoformat(),
        second.registration_date.isoformat(),
        "2024-01-10",
    ]
    descriptions = [entry["description"] for entry in content]
    assert descriptions == ["Summer acceleration", "Spring replan", "Initial"]


def test_get_schedule_respects_control_date_created_at_filter(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Latest registration created after the control date should be hidden."""
    cost_element = create_random_cost_element(db)
    earlier = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 10),
        description="Initial",
    )
    earlier.created_at = datetime(2024, 1, 25, tzinfo=timezone.utc)
    db.add(earlier)
    db.commit()
    db.refresh(earlier)
    future_created = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 5, 31),
        progression_type="gaussian",
        registration_date=date(2024, 1, 20),
        description="Backdated but late entry",
    )
    future_created.created_at = datetime(2024, 3, 10, tzinfo=timezone.utc)
    db.add(future_created)
    db.commit()
    db.refresh(future_created)

    control_date = date(2024, 2, 1)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["schedule_id"] == str(earlier.schedule_id)
    assert content["description"] == "Initial"


def test_schedule_history_respects_control_date_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """History endpoint should exclude entries created after the control date even if registration date is backdated."""
    cost_element = create_random_cost_element(db)
    retained = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 10),
        description="Historical",
    )
    retained.created_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
    db.add(retained)
    db.commit()
    db.refresh(retained)
    hidden = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 2, 1),
        end_date=date(2024, 5, 1),
        progression_type="logarithmic",
        registration_date=date(2024, 1, 15),
        description="Late data entry",
    )
    hidden.created_at = datetime(2024, 3, 5, tzinfo=timezone.utc)
    db.add(hidden)
    db.commit()
    db.refresh(hidden)

    control_date = date(2024, 2, 1)
    set_time_machine_date(client, superuser_token_headers, control_date)

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/history",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 1
    assert content[0]["schedule_id"] == str(retained.schedule_id)
    assert content[0]["description"] == "Historical"


def test_history_excludes_baseline_snapshots(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Baseline-linked schedules should not appear in the operational history."""
    cost_element = create_random_cost_element(db)
    create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 10),
        description="Operational",
    )
    baseline_schedule = create_schedule_for_cost_element(
        db,
        cost_element.cost_element_id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        progression_type="linear",
        registration_date=date(2024, 1, 10),
        description="Baseline copy",
    )
    wbe = db.get(WBE, cost_element.wbe_id)
    assert wbe is not None
    project = db.get(Project, wbe.project_id)
    assert project is not None
    baseline_log = BaselineLog(
        baseline_type="schedule",
        baseline_date=date(2024, 1, 1),
        milestone_type="kickoff",
        project_id=project.project_id,
        created_by_id=project.project_manager_id,
    )
    db.add(baseline_log)
    db.commit()
    db.refresh(baseline_log)

    baseline_schedule.baseline_id = baseline_log.baseline_id
    db.add(baseline_schedule)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/cost-element-schedules/history",
        headers=superuser_token_headers,
        params={"cost_element_id": str(cost_element.cost_element_id)},
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 1
    assert content[0]["description"] == "Operational"
