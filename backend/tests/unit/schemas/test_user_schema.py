from datetime import UTC, datetime
from uuid import uuid4

from app.models.schemas.user import UserHistory, convert_range_to_list


# Mock Range object since we might not have psycopg2 installed in test env
class MockRange:
    def __init__(self, lower: datetime | None, upper: datetime | None):
        self.lower = lower
        self.upper = upper


def test_convert_range_to_list_valid():
    """Test converting a valid range with bounds."""
    start = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(2023, 1, 2, 12, 0, 0, tzinfo=UTC)

    range_obj = MockRange(start, end)
    result = convert_range_to_list(range_obj)

    assert result == [start, end]


def test_convert_range_to_list_open_ended():
    """Test converting a range with null upper bound."""
    start = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

    range_obj = MockRange(start, None)
    result = convert_range_to_list(range_obj)

    assert result == [start, None]


def test_convert_range_to_list_none():
    """Test converting None input."""
    assert convert_range_to_list(None) is None


def test_user_history_serialization():
    """Test UserHistory Pydantic model serialization."""
    start = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    range_obj = MockRange(start, None)
    id_val = uuid4()
    actor_id = uuid4()

    user_data = {
        "id": id_val,
        "user_id": id_val,
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "role": "viewer",
        "valid_time": range_obj,
        "transaction_time": range_obj,
        "created_by": actor_id,
    }

    history_item = UserHistory.model_validate(user_data)

    # Check that it kept the data (BeforeValidator converts it)
    assert history_item.valid_time == [start, None]
    assert history_item.transaction_time == [start, None]
    assert history_item.email == "test@example.com"
