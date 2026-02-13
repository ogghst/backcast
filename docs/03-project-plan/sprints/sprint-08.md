# Sprint 8: EVM Calculations & Baselines

**Goal:** Enable EVM reporting and baseline management
**Status:** Planned
**Story Points:** 27

**Stories:**
- [ ] E07-U01: Create baselines at milestones
- [ ] E07-U02: Snapshot all cost element data immutably
- [ ] E07-U03: Compare current state to any baseline
- [ ] E08-U01: Calculate PV using schedule baselines
- [ ] E08-U02: Calculate EV from % complete
- [ ] E08-U03: Calculate AC from cost registrations
- [ ] E08-U04: View performance indices (CPI/SPI/TCPI)
- [ ] E08-U06: Generate cost performance reports
- [ ] **E08-U07: Change Order Impact Analysis EVM Metrics** (NEW - from Phase 3)

**Tasks:**
- [ ] **S08-T01:** Implement Baseline management endpoints
- [ ] **S08-T02:** Create EVM calculation service
- [ ] **S08-T03:** Implement Schedule baseline logic
- [ ] **S08-T04:** Generate Performance reports
- [ ] **S08-T05:** Extend Impact Analysis with EVM metrics (NEW)

**Calculations:**
- PV (Planned Value) using schedule baselines + progression types
- EV (Earned Value) from % complete
- AC (Actual Cost) from cost registrations
- CPI, SPI, TCPI, CV, SV, VAC

---

## Phase 3 EVM Metrics Extension

**Context:** Sprint 7 Phase 3 (Impact Analysis) implemented basic financial comparison (BAC, Budget Delta, Margin). Sprint 8 extends this with full EVM metrics.

### EVM Metrics for Impact Analysis

| Metric | Description | Calculation | Use in Impact Analysis |
|--------|-------------|-------------|------------------------|
| **BAC** | Budget at Completion | Sum of all WBE `budget_allocation` | ✅ Phase 3 |
| **EAC** | Estimate at Completion | From forecasts | ⏸️ Sprint 8 |
| **CPI** | Cost Performance Index | `EV / AC` | ⏸️ Sprint 8 |
| **SPI** | Schedule Performance Index | `EV / PV` | ⏸️ Sprint 8 |
| **CV** | Cost Variance | `EV - AC` | ⏸️ Sprint 8 |
| **SV** | Schedule Variance | `EV - PV` | ⏸️ Sprint 8 |
| **VAC** | Variance at Completion | `BAC - EAC` | ⏸️ Sprint 8 |

### Enhancement Scope

**Backend:**

- Extend `KPIScorecard` schema with EVM fields (EAC, CPI, SPI, CV, SV)
- Extend `ImpactAnalysisService` to compute EVM metrics
- Add `calculate_eac()`, `calculate_cpi()`, `calculate_spi()` methods
- Leverage `EVMCalculationService` from Sprint 8

**Frontend:**

- Extend KPI Cards to display EAC, CPI, SPI
- Add performance indicator badges (favorable/unfavorable)
- Update `useImpactAnalysis` hook to include new fields

**API Changes:**

```python
# Extended KPIScorecard
class KPIScorecard(BaseModel):
    # Phase 3 fields
    bac: KPIMetric  # Budget at Completion
    budget_delta: KPIMetric
    gross_margin: KPIMetric

    # Sprint 8 additions
    eac: KPIMetric  # Estimate at Completion
    cpi: KPIMetric  # Cost Performance Index
    spi: KPIMetric  # Schedule Performance Index
    cv: KPIMetric   # Cost Variance
    sv: KPIMetric   # Schedule Variance
    vac: KPIMetric  # Variance at Completion
```

**Dependencies:**

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| EVMCalculationService | Required for EAC/CPI/SPI | Implement in Sprint 8 before extending Impact Analysis |
| Phase 3 Impact API | Must be backward compatible | Add optional EVM fields with defaults |

**Story Points:** 3 points (extension work, leveraging Sprint 8 EVM service)
