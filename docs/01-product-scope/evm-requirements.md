# EVM Requirements

**Last Updated:** 2025-12-29  
**Compliance:** ANSI/EIA-748 Standard  
**Status:** Active

This document specifies Earned Value Management (EVM) requirements for the Backcast EVS system.

---

## 1. EVM Terminology and Compliance

The system shall fully implement EVM principles using standard terminology per ANSI/EIA-748 standard. All calculations, reports, and user interfaces must use proper EVM terminology consistently.

---

## 2. Core EVM Metrics

Calculations at cost element, WBE, and project levels:

### 2.1 Planned Value (PV)
**Also Known As:** Budgeted Cost of Work Scheduled (BCWS)

**Definition:** Authorized budget assigned to scheduled work

**Calculation:**
```
PV = BAC × % Planned Completion
```

**Example:**
- BAC = €100,000
- At month 2, planned completion = 40%
- PV = 100,000 × 0.40 = €40,000

**Progression Types:**
- **Linear:** Even distribution over duration
- **Gaussian:** Normal distribution curve, peak at midpoint
- **Logarithmic:** Slow start with accelerating completion

Progression type determines how % planned completion is calculated between start and end dates using cost element schedule baseline.

### 2.2 Earned Value (EV)
**Also Known As:** Budgeted Cost of Work Performed (BCWP)

**Definition:** Budgeted cost of work actually performed

**Calculation:**
```
EV = BAC × % Physical Completion
```

**Example:**
- BAC = €100,000
- Physical completion = 30%
- EV = 100,000 × 0.30 = €30,000

Physical completion from recorded earned value entries (baselined).

### 2.3 Actual Cost (AC)
**Definition:** Realized cost incurred for work performed

**Calculation:** Sum of all registered costs including quality event costs

### 2.4 Budget at Completion (BAC)
**Definition:** Total planned budget for work scope

**Calculation:** Sum of all allocated budgets adjusted for approved changes

### 2.5 Estimate at Completion (EAC)
**Definition:** Expected total cost at project completion

**Calculation:** From current forecasts

### 2.6 Estimate to Complete (ETC)
**Definition:** Expected cost to finish remaining work

**Calculation:**
```
ETC = EAC - AC
```

---

## 3. EVM Performance Indices

### 3.1 Cost Performance Index (CPI)
**Definition:** Cost efficiency indicator

**Calculation:**
```
CPI = EV / AC
```

**Interpretation:**
- CPI > 1: Under-budget (good)
- CPI < 1: Over-budget (concern)

### 3.2 Schedule Performance Index (SPI)
**Definition:** Schedule efficiency indicator

**Calculation:**
```
SPI = EV / PV
```

**Interpretation:**
- SPI > 1: Ahead of schedule (good)
- SPI < 1: Behind schedule (concern)

### 3.3 To Complete Performance Index (TCPI)
**Definition:** Cost performance required on remaining work to meet budget goals

**TCPI based on BAC:**
```
TCPI(BAC) = (BAC - EV) / (BAC - AC)
```

**TCPI based on EAC:**
```
TCPI(EAC) = (BAC - EV) / (EAC - AC)
```

---

## 4. EVM Variance Analysis

### 4.1 Cost Variance (CV)
**Calculation:**
```
CV = EV - AC
```

**Interpretation:**
- Negative: Over-budget
- Positive: Under-budget

### 4.2 Schedule Variance (SV)
**Calculation:**
```
SV = EV - PV
```

**Interpretation:**
- Negative: Behind schedule
- Positive: Ahead of schedule

### 4.3 Variance at Completion (VAC)
**Calculation:**
```
VAC = BAC - EAC
```

**Definition:** Expected final cost variance at project completion

**Format:** Must be calculable as both absolute values and percentages

---

## 5. Additional EVM Metrics

### 5.1 Percent Complete Calculations

**Method 1: Percent of Budget Spent**
```
% Complete (Cost) = AC / BAC
```

**Method 2: Percent of Work Earned**
```
% Complete (EV) = EV / BAC
```

**Method 3: Percent of Schedule Complete**
```
% Complete (Schedule) = (Current Date - Start Date) / Planned Duration
```

### 5.2 Estimate to Complete (ETC) Methods

**Method 1: Bottom-Up Detailed Estimates**
From forecasts (detailed estimation)

**Method 2: Performance-Based Projection**
```
ETC = (BAC - EV) / CPI
```

**Method 3: Management Judgment**
Using management judgment factors when appropriate

---

## 6. Project Assessment Report

### 6.1 AI-Powered Assessment
- Collect all project metrics at control date or from baseline
- Generate assessment using artificial intelligence endpoint
- Provide insights on project health, risks, trends

---

## 7. Standard EVM Reports

### 7.1 Cost Performance Report
- Cumulative and period performance
- All key EVM metrics
- Available at project/WBE/cost element levels
- Drill-down capabilities to supporting detail

### 7.2 Variance Analysis Report
- Cost and schedule variances
- Trend analysis
- Root cause identification support

### 7.3 Forecast Report
- Current EAC compared to BAC
- Variance explanations
- Forecast accuracy tracking

### 7.4 Baseline Comparison Report
- Performance against original baseline
- Performance against current baseline
- Historical variance trends

---

## 8. Trend Analysis and Dashboards

### 8.1 Performance Trends
Visual displays of:
- CPI and SPI trending over time
- Forecast EAC trending
- EV vs. PV vs. AC curves
- Variance trends
- Quality cost trends

### 8.2 Dashboard Configuration
- Selectable: projects, WBEs, departments, time periods
- Visual representations:
  - Line graphs: trend analysis
  - Bar charts: period comparisons
  - Gauge displays: current performance indices

---

## 9. Custom Reporting and Data Export

### 9.1 Custom Report Generation
Users can:
- Select specific data elements
- Define filters and groupings
- Specify calculation methods
- Determine output formats

### 9.2 Export Formats
- CSV: Data analysis
- Excel: Spreadsheet manipulation
- PDF: Presentations and sharing

---

## 10. Quality Cost Analysis

### 10.1 Quality-Specific Reporting
- Total quality costs by project/WBE/department
- Quality cost trends over time
- Root cause analysis summaries
- Cost of quality as % of total project costs
- Cross-project benchmarking

---

## 11. EVM Calculation Rules

### 11.1 Aggregation
- Cost element → WBE → Project
- All formulas apply at each level

### 11.2 Control Date
- All calculations based on selected control date
- Time machine control determines data snapshot

### 11.3 Branch Context
- EVM calculations filtered by selected branch
- Main branch for operational reporting
- Branch branches for change order impact analysis

---

## 12. Success Criteria

### 12.1 Accuracy
- EVM calculations must match manual calculation results
- Validation against industry-standard examples

### 12.2 Performance
- Real-time calculation for dashboards
- Batch calculation for historical analysis
- Responsive even with large data volumes

### 12.3 Training Support
- System supports training on EVM principles
- Real-world scenarios simulation
- What-if analysis capabilities

---

**See Also:**
- [Functional Requirements](functional-requirements.md) - System capabilities
- [Glossary](glossary.md) - EVM term definitions
