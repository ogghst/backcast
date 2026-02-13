# ImpactAnalysisService - Phase 5 API Reference

**Service:** `app/services.impact_analysis_service.ImpactAnalysisService`
**Phase:** 5 - Advanced Impact Analysis
**Date:** 2026-02-05

---

## New Methods

### 1. `_compare_schedule_baselines()`

Compare schedule baselines between main and change branches.

```python
def _compare_schedule_baselines(
    self,
    main_start_date: datetime,
    main_end_date: datetime,
    main_duration: int,
    main_progression_type: str,
    change_start_date: datetime,
    change_end_date: datetime,
    change_duration: int,
    change_progression_type: str,
) -> ScheduleBaselineComparison
```

**Parameters:**

- `main_start_date`: Schedule start date in main branch
- `main_end_date`: Schedule end date in main branch
- `main_duration`: Schedule duration in days (main branch)
- `main_progression_type`: Progression type in main branch (LINEAR/GAUSSIAN/LOGARITHMIC)
- `change_start_date`: Schedule start date in change branch
- `change_end_date`: Schedule end date in change branch
- `change_duration`: Schedule duration in days (change branch)
- `change_progression_type`: Progression type in change branch

**Returns:** `ScheduleBaselineComparison` TypedDict

```python
{
    "start_delta_days": int,        # Days difference (change - main)
    "end_delta_days": int,          # Days difference (change - main)
    "duration_delta_days": int,     # Days difference (change - main)
    "progression_changed": bool,    # Whether progression type changed
    "main_progression_type": str,   # Progression type in main branch
    "change_progression_type": str, # Progression type in change branch
}
```

**Example:**

```python
result = service._compare_schedule_baselines(
    main_start_date=datetime(2026, 1, 1, tzinfo=UTC),
    main_end_date=datetime(2026, 6, 30, tzinfo=UTC),
    main_duration=180,
    main_progression_type="LINEAR",
    change_start_date=datetime(2026, 1, 15, tzinfo=UTC),
    change_end_date=datetime(2026, 7, 31, tzinfo=UTC),
    change_duration=197,
    change_progression_type="GAUSSIAN",
)

print(result["duration_delta_days"])  # 17 (schedule extended by 17 days)
print(result["progression_changed"])  # True
```

---

### 2. `_compare_evm_metrics()`

Compare EVM performance metrics between main and change branches.

```python
def _compare_evm_metrics(
    self,
    main_cpi: Decimal,
    change_cpi: Decimal,
    main_spi: Decimal,
    change_spi: Decimal,
    main_tcpi: Decimal,
    change_tcpi: Decimal,
    main_eac: Decimal,
    change_eac: Decimal,
) -> EVMMetricsComparison
```

**Parameters:**

- `main_cpi`: Cost Performance Index in main branch (EV/AC)
- `change_cpi`: Cost Performance Index in change branch
- `main_spi`: Schedule Performance Index in main branch (EV/PV)
- `change_spi`: Schedule Performance Index in change branch
- `main_tcpi`: To-Complete Performance Index in main branch
- `change_tcpi`: To-Complete Performance Index in change branch
- `main_eac`: Estimate at Completion in main branch
- `change_eac`: Estimate at Completion in change branch

**Returns:** `EVMMetricsComparison` TypedDict

```python
{
    "cpi_delta": Decimal,  # Cost Performance Index delta (change - main)
    "spi_delta": Decimal,  # Schedule Performance Index delta (change - main)
    "tcpi_delta": Decimal, # To-Complete Performance Index delta (change - main)
    "eac_delta": Decimal,  # Estimate at Completion delta (change - main)
}
```

**EVM Metrics Reference:**

| Metric | Formula | Target | Interpretation |
|--------|---------|--------|----------------|
| **CPI** | EV / AC | ≥ 1.0 | < 1.0 = Cost overrun, > 1.0 = Under budget |
| **SPI** | EV / PV | ≥ 1.0 | < 1.0 = Behind schedule, > 1.0 = Ahead of schedule |
| **TCPI** | (BAC - EV) / (EAC - AC) | ≤ 1.0 | > 1.0 = Harder to complete, < 1.0 = Easier to complete |
| **EAC** | BAC / CPI (forecast) | - | Estimate of final cost |

**Example:**

```python
result = service._compare_evm_metrics(
    main_cpi=Decimal("1.0"),
    change_cpi=Decimal("0.85"),  # Cost overrun
    main_spi=Decimal("1.0"),
    change_spi=Decimal("0.90"),  # Schedule delay
    main_tcpi=Decimal("1.0"),
    change_tcpi=Decimal("1.15"), # Harder to complete
    main_eac=Decimal("100000.00"),
    change_eac=Decimal("120000.00"),  # $20k higher
)

print(result["cpi_delta"])  # Decimal("-0.15") (degraded)
print(result["eac_delta"])  # Decimal("20000.00") (increased cost)
```

---

### 3. `_compare_vac()`

Compare Variance at Completion (VAC) between main and change branches.

```python
def _compare_vac(
    self,
    main_vac: Decimal,
    change_vac: Decimal,
) -> VACComparison
```

**Parameters:**

- `main_vac`: Variance at Completion in main branch (BAC - EAC)
- `change_vac`: Variance at Completion in change branch (BAC - EAC)

**Returns:** `VACComparison` TypedDict

```python
{
    "vac_delta": Decimal,  # Variance at Completion delta (change - main)
    "main_vac": Decimal,   # Variance at Completion in main branch
    "change_vac": Decimal, # Variance at Completion in change branch
}
```

**VAC Reference:**

| VAC Value | Interpretation |
|-----------|----------------|
| **VAC > 0** | Under budget (favorable) |
| **VAC = 0** | On budget |
| **VAC < 0** | Over budget (unfavorable) |

**Example:**

```python
result = service._compare_vac(
    main_vac=Decimal("0"),          # On budget
    change_vac=Decimal("-10000"),  # $10k over budget
)

print(result["vac_delta"])   # Decimal("-10000.00") (worse by $10k)
print(result["main_vac"])    # Decimal("0")
print(result["change_vac"])  # Decimal("-10000.00")
```

---

## Usage Example: Full Impact Analysis with Phase 5 Metrics

```python
from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.impact_analysis_service import ImpactAnalysisService

async def analyze_change_order_impact(
    db: AsyncSession,
    change_order_id: UUID,
) -> None:
    """Analyze change order impact with Phase 5 metrics."""
    service = ImpactAnalysisService(db)

    # 1. Get change order details
    change_order = await service._get_change_order(change_order_id)
    branch_name = f"BR-{change_order.change_order_number}"

    # 2. Fetch schedule baselines
    main_schedule = await service._fetch_schedule_baseline(
        change_order.project_id,
        branch="main"
    )
    change_schedule = await service._fetch_schedule_baseline(
        change_order.project_id,
        branch=branch_name
    )

    # 3. Compare schedules
    schedule_comparison = service._compare_schedule_baselines(
        main_start_date=main_schedule.start_date,
        main_end_date=main_schedule.end_date,
        main_duration=(main_schedule.end_date - main_schedule.start_date).days,
        main_progression_type=main_schedule.progression_type,
        change_start_date=change_schedule.start_date,
        change_end_date=change_schedule.end_date,
        change_duration=(change_schedule.end_date - change_schedule.start_date).days,
        change_progression_type=change_schedule.progression_type,
    )

    # 4. Fetch EVM metrics (using EVMService)
    main_evm = await evm_service.calculate_evm_metrics(
        cost_element_id,
        control_date=datetime.now(UTC),
        branch="main"
    )
    change_evm = await evm_service.calculate_evm_metrics(
        cost_element_id,
        control_date=datetime.now(UTC),
        branch=branch_name
    )

    # 5. Compare EVM metrics
    evm_comparison = service._compare_evm_metrics(
        main_cpi=main_evm.cpi,
        change_cpi=change_evm.cpi,
        main_spi=main_evm.spi,
        change_spi=change_evm.spi,
        main_tcpi=main_evm.tcpi,
        change_tcpi=change_evm.tcpi,
        main_eac=main_evm.eac or Decimal("0"),
        change_eac=change_evm.eac or Decimal("0"),
    )

    # 6. Compare VAC
    vac_comparison = service._compare_vac(
        main_vac=main_evm.vac or Decimal("0"),
        change_vac=change_evm.vac or Decimal("0"),
    )

    # 7. Populate KPIScorecard with Phase 5 metrics
    kpi_scorecard.schedule_start_date = KPIMetric(
        main_value=Decimal(main_schedule.start_date.timestamp()),
        change_value=Decimal(change_schedule.start_date.timestamp()),
        delta=Decimal(schedule_comparison["start_delta_days"]),
    )
    kpi_scorecard.schedule_duration = KPIMetric(
        main_value=Decimal(schedule_comparison["duration_delta_days"]),
        change_value=Decimal(change_comparison["duration_delta_days"]),
        delta=Decimal(schedule_comparison["duration_delta_days"]),
    )
    kpi_scorecard.cpi = KPIMetric(
        main_value=main_evm.cpi,
        change_value=change_evm.cpi,
        delta=evm_comparison["cpi_delta"],
    )
    kpi_scorecard.vac = KPIMetric(
        main_value=vac_comparison["main_vac"],
        change_value=vac_comparison["change_vac"],
        delta=vac_comparison["vac_delta"],
    )

    return kpi_scorecard
```

---

## Integration Notes

### Data Requirements

All comparison methods require the following data to be available:

1. **Schedule Baselines:**
   - Must exist for both main and change branches
   - Fields: `start_date`, `end_date`, `progression_type`
   - Retrieved from: `schedule_baselines` table via ScheduleBaselineService

2. **EVM Metrics:**
   - Calculated by EVMService for each cost element
   - Aggregated to project level (sum/average as appropriate)
   - Fields: `cpi`, `spi`, `tcpi`, `eac`, `vac`
   - Requires: Progress entries, cost registrations, forecasts

### Edge Cases

All methods handle edge cases gracefully:

1. **Missing Schedule Baseline:**
   - Return None for schedule fields in KPIScorecard
   - Log warning for debugging

2. **Missing EVM Metrics:**
   - Return None for EVM fields in KPIScorecard
   - Occurs when no progress entries or forecasts exist yet

3. **Division by Zero:**
   - CPI/SPI/TCPI calculations handled by EVMService
   - Returns None when AC/PV/EAC are zero

### Performance Considerations

- All comparison methods are **O(1)** - no database queries
- EVMService has caching for repeated calculations
- Schedule baseline queries use indexed fields
- No N+1 query issues in the comparison layer

---

## Testing

Unit tests are located in:

```
backend/tests/unit/services/test_impact_analysis_service.py
```

Test classes:

- `TestImpactAnalysisServiceScheduleBaselineComparison` (4 tests)
- `TestImpactAnalysisServiceEVMComparison` (3 tests)
- `TestImpactAnalysisServiceVACProjections` (3 tests)

Run tests:

```bash
cd backend
uv run pytest tests/unit/services/test_impact_analysis_service.py -v
```

---

**End of API Reference**
