"""Budget Timeline model and related schemas."""


from app.models.cost_element import CostElementPublic
from app.models.cost_element_schedule import CostElementSchedulePublic


class CostElementWithSchedulePublic(CostElementPublic):
    """Public cost element schema with nested schedule for API responses."""

    schedule: CostElementSchedulePublic | None = None
