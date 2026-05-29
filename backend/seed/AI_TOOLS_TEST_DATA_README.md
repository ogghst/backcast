# AI Tools Test Data - Summary

## Overview

Comprehensive test dataset for AI tools testing has been successfully loaded into the database. This data demonstrates all 13 AI tools with realistic project scenarios.

## Project Details

**Project:** AI Test Project 2026 (AI-TEST-001)
- **Budget:** $500,000
- **Contract Value:** $550,000
- **Dates:** January 1, 2026 - December 31, 2026

## WBE Hierarchy (7 WBEs)

### Level 1 (2 WBEs)
1. **AI-TEST-001-L1** - Mechanical Systems
2. **AI-TEST-001-L2** - Electrical Systems

### Level 2 (2 WBEs)
1. **AI-TEST-001-L1-1** - Conveyor System (parent: Mechanical Systems)
2. **AI-TEST-001-L2-1** - Power Distribution (parent: Electrical Systems)

### Level 3 (3 WBEs - where cost elements are attached)
1. **AI-TEST-001-L1-1-1** - Main Conveyor (parent: Conveyor System)
2. **AI-TEST-001-L1-1-2** - Secondary Conveyor (parent: Conveyor System)
3. **AI-TEST-001-L2-1-1** - Main Panel (parent: Power Distribution)

## Cost Elements (4 total)

| Code | Name | Budget | EAC | Variance | WBE | Status |
|------|------|--------|-----|----------|-----|--------|
| **CE-CONV-MAIN** | Main Conveyor Installation | $100,000 | $110,000 | +$10,000 | Main Conveyor | Over budget |
| **CE-CONV-SEC** | Secondary Conveyor Installation | $75,000 | $75,000 | $0 | Secondary Conveyor | On budget |
| **CE-PANEL-MAIN** | Main Panel Installation | $50,000 | $48,000 | -$2,000 | Main Panel | Under budget |
| **CE-CTRL-SYS** | Control System Programming | $40,000 | $45,000 | +$5,000 | Main Conveyor | Over budget |

## Cost Registrations (8 total)

### CE-CONV-MAIN (3 registrations, $60,000 total)
- $15,000 on 2026-01-15 - "Initial materials - conveyor framing steel and supports"
- $25,000 on 2026-02-15 - "Conveyor frame fabrication and motor installation"
- $20,000 on 2026-03-15 - "Motor installation and belt assembly"

### CE-CONV-SEC (2 registrations, $25,000 total)
- $10,000 on 2026-02-01 - "Materials for secondary conveyor"
- $15,000 on 2026-03-01 - "Secondary conveyor installation labor"

### CE-PANEL-MAIN (2 registrations, $30,000 total)
- $20,000 on 2026-01-20 - "Main panel purchase with volume discount"
- $10,000 on 2026-02-20 - "Panel wiring and breaker installation"

### CE-CTRL-SYS (1 registration, $5,000 total)
- $5,000 on 2026-03-01 - "Control system programming setup and initial configuration"

## Progress Entries (9 total)

### CE-CONV-MAIN (3 entries)
- 25% on 2026-01-31 - "Frame fabrication complete, motor installation in progress"
- 50% on 2026-02-28 - "Motors installed, belt assembly in progress"
- 75% on 2026-03-31 - "Belt assembly complete, testing and commissioning in progress"

### CE-CONV-SEC (2 entries)
- 20% on 2026-02-28 - "Materials delivered, installation started"
- 40% on 2026-03-31 - "Installation progressing well, on schedule"

### CE-PANEL-MAIN (2 entries)
- 50% on 2026-01-31 - "Panel installed, wiring 50% complete"
- 80% on 2026-02-28 - "Installation complete, final testing in progress"

### CE-CTRL-SYS (2 entries)
- 10% on 2026-03-15 - "Initial setup and configuration started"
- 30% on 2026-03-31 - "Basic logic programming complete, working on safety interlocks"

## Forecasts (4 total)

All cost elements have associated forecasts with detailed basis of estimates:

1. **CE-CONV-MAIN:** $110,000 EAC
   - "Due to steel price increases in Q1 2026, material costs are running 10% above budget. Labor remains on track."

2. **CE-CONV-SEC:** $75,000 EAC
   - "As planned. Installation progressing according to schedule with no cost overruns expected."

3. **CE-PANEL-MAIN:** $48,000 EAC
   - "Volume discount achieved on panel purchase. Coming in under budget by $2,000."

4. **CE-CTRL-SYS:** $45,000 EAC
   - "Additional programming required for safety interlocks and emergency stop functionality. $5,000 over budget."

## Expected AI Tool Query Results

### 1. Forecast Query
**Query:** "What's the forecast for Main Conveyor Installation?"

**Expected Result:**
```json
{
  "cost_element": "CE-CONV-MAIN",
  "budget": 100000.0,
  "eac": 110000.0,
  "variance": 10000.0,
  "basis": "Due to steel price increases in Q1 2026, material costs are running 10% above budget. Labor remains on track."
}
```

### 2. Budget Status Query
**Query:** "What's the budget status for CE-CONV-MAIN?"

**Expected Result:**
```json
{
  "cost_element": "CE-CONV-MAIN",
  "budget": 100000.0,
  "used": 60000.0,
  "remaining": 40000.0,
  "registrations_count": 3
}
```

### 3. Progress Query
**Query:** "What's the latest progress for Control System Programming?"

**Expected Result:**
```json
{
  "cost_element": "CE-CTRL-SYS",
  "latest_progress": 30.0,
  "entry_date": "2026-03-31",
  "notes": "Basic logic programming complete, working on safety interlocks"
}
```

### 4. Cost Registrations Query
**Query:** "Show me all cost registrations for CE-PANEL-MAIN"

**Expected Result:**
```json
{
  "cost_element": "CE-PANEL-MAIN",
  "registrations": [
    {"date": "2026-01-20", "amount": 20000.0, "description": "Main panel purchase with volume discount"},
    {"date": "2026-02-20", "amount": 10000.0, "description": "Panel wiring and breaker installation"}
  ],
  "total": 30000.0
}
```

### 5. WBE Hierarchy Query
**Query:** "What WBEs are under Mechanical Systems?"

**Expected Result:**
```json
{
  "parent_wbe": "Mechanical Systems (AI-TEST-001-L1)",
  "children": [
    "Conveyor System (AI-TEST-001-L1-1)",
    "Main Conveyor (AI-TEST-001-L1-1-1)",
    "Secondary Conveyor (AI-TEST-001-L1-1-2)"
  ]
}
```

## How to Re-Seed

If you need to re-seed this data:

```bash
cd backend
source .venv/bin/activate
python seed/scripts/seed_ai_tools_test_data.py
```

**Note:** The seeder is idempotent - it will skip entities that already exist.

## Data Files

- **Source Data:** `/backend/seed/ai_tools_test_data.json`
- **Seeder Script:** `/backend/app/db/ai_tools_seeder.py`
- **Runner Script:** `/backend/seed/scripts/seed_ai_tools_test_data.py`

## Key Features

1. **Realistic Project Structure:** 3-level WBE hierarchy with proper parent-child relationships
2. **Complete Cost Tracking:** Budget vs EAC vs Actuals with detailed explanations
3. **Progress Over Time:** Multiple progress entries showing evolution over 3 months
4. **Forecast Scenarios:** All three scenarios represented (over, on, under budget)
5. **Proper Foreign Keys:** All entities properly linked to their parent WBEs/Projects

## AI Tools Supported

This dataset supports testing of all 13 AI tools:
- Project read/list tools
- WBE hierarchy navigation
- Cost element CRUD operations
- Forecast creation and querying
- Cost registration tracking
- Progress entry management
- Budget status calculations
- Variance analysis
