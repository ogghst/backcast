# PDCA Prompts

## Cycle Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│  ANALYSIS     →    PLAN      →     DO       →    CHECK     →    ACT      │
│  (Pre-PDCA)        (P)              (D)           (C)           (A)       │
├───────────────────────────────────────────────────────────────────────────┤
│  WHAT/WHY?      WHAT/WHEN?      HOW?          DID IT WORK?   LOCK IT IN  │
│  • Requirements • Tasks         • RED: Test   • Verify       • Standardize│
│  • Options      • Acceptance    • GREEN: Code • Metrics      • Document   │
│  • Decision     • Dependencies  • REFACTOR    • Root Cause   • Close      │
├───────────────────────────────────────────────────────────────────────────┤
│  00-analysis    01-plan         02-do         03-check       04-act       │
└───────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

| I need to...              | Use this prompt                            | Output           |
| ------------------------- | ------------------------------------------ | ---------------- |
| **Analyze a requirement** | [`analysis-prompt.md`](analysis-prompt.md) | `00-analysis.md` |
| **Plan implementation**   | [`plan-prompt.md`](plan-prompt.md)         | `01-plan.md`     |
| **Execute with TDD**      | [`do-prompt.md`](do-prompt.md)             | `02-do.md`       |
| **Verify & retrospect**   | [`check-prompt.md`](check-prompt.md)       | `03-check.md`    |
| **Improve & close**       | [`act-prompt.md`](act-prompt.md)           | `04-act.md`      |
| **Find next work**        | [`next-iteration.md`](next-iteration.md)   | New iteration    |

## Phase Responsibilities

| Phase        | Owns                         | Does NOT Own            |
| ------------ | ---------------------------- | ----------------------- |
| **Analysis** | Requirements, options        | Task breakdown          |
| **Plan**     | WHAT to test, acceptance     | HOW to implement (code) |
| **Do**       | HOW (test + production code) | Retrospective           |
| **Check**    | Verification, root cause     | Standardization         |
| **Act**      | Improvements, documentation  | Analysis of issues      |

## TDD Integration

```
PLAN defines test specifications (WHAT)
         ↓
DO implements tests (RED → GREEN → REFACTOR)
         ↓
CHECK verifies all tests pass + coverage
         ↓
ACT standardizes successful test patterns
```

## Supporting Files

| File                                         | Purpose                    |
| -------------------------------------------- | -------------------------- |
| [`_templates/`](_templates/)                 | Reusable output templates  |
| [`_references.md`](_references.md)           | Common documentation links |
| [`prompt-changelog.md`](prompt-changelog.md) | Version history            |

## Output Location

All iteration outputs go to:

```
docs/03-project-plan/iterations/YYYY-MM-DD-{title}/
├── 00-analysis.md    # Analysis phase output
├── 01-plan.md        # Plan phase output
├── 02-do.md          # Do phase log
├── 03-check.md       # Check phase output
└── 04-act.md         # Act phase output
```
