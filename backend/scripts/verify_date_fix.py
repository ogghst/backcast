from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.change_order_service import ChangeOrderService


# Mock ChangeOrderService for testing _calculate_business_days_remaining
class MockService(ChangeOrderService):
    def __init__(self):
        pass


service = MockService()

# Test cases
utc = ZoneInfo("UTC")
naive_date = datetime(2026, 6, 1, 12, 0, 0)
aware_date = datetime(2026, 6, 5, 12, 0, 0, tzinfo=utc)

print("Testing naive vs aware...")
try:
    days = service._calculate_business_days_remaining(naive_date, aware_date)
    print(f"Result (naive vs aware): {days}")
except Exception as e:
    print(f"FAILED (naive vs aware): {e}")

print("\nTesting aware vs naive...")
try:
    days = service._calculate_business_days_remaining(aware_date, naive_date)
    print(f"Result (aware vs naive): {days}")
except Exception as e:
    print(f"FAILED (aware vs naive): {e}")

print("\nTesting naive vs naive...")
try:
    days = service._calculate_business_days_remaining(
        naive_date, naive_date.replace(day=5)
    )
    print(f"Result (naive vs naive): {days}")
except Exception as e:
    print(f"FAILED (naive vs naive): {e}")

print("\nTesting aware vs aware...")
try:
    days = service._calculate_business_days_remaining(
        aware_date, aware_date.replace(day=10)
    )
    print(f"Result (aware vs aware): {days}")
except Exception as e:
    print(f"FAILED (aware vs aware): {e}")
