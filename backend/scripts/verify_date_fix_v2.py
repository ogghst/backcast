from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.change_order_service import ChangeOrderService

# Mock ChangeOrderService for testing _calculate_business_days_remaining if needed
# But better to use the real one to verify imports work
service = ChangeOrderService(None)

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
