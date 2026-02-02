# PDCA Prompt Changelog

**Purpose:** Track evolution of PDCA prompts to improve AI collaboration over time.

---

## 2026-01-17: Major Refactoring - Phase Deconfliction & Best Practices

**Changes:**

- Created `_templates/` folder with extracted output templates (5 files)
- Created `_references.md` with centralized documentation links
- Refactored `plan-prompt.md` from 555 to ~180 lines
  - Removed inline TDD tutorial (moved to DO)
  - Clarified PLAN owns WHAT, DO owns HOW
  - Added template reference
- Refactored `do-prompt.md` (~150 lines)
  - Added clear TDD ownership section
  - Streamlined for execution focus
- Refactored `check-prompt.md`
  - Added root cause analysis (moved from ACT)
  - Added improvement options as decision point
  - Added 5 Whys template
- Refactored `act-prompt.md`
  - Removed root cause analysis (now in CHECK)
  - Focused on execution of approved improvements
  - Added industry benchmarks
- Refactored `analysis-prompt.md`
  - Added UX patterns reference table
  - Added template reference
  - Improved transition to PLAN section
- Updated `README.md` with cycle overview diagram and phase responsibilities

**Rationale:**

- **Phase Deconfliction**: Each phase now has clear, non-overlapping responsibilities
- **TDD Alignment**: PLAN defines WHAT to test, DO implements HOW
- **Context Rot Prevention**: Shorter prompts for PLAN/DO, verbose for ANALYSIS/ACT
- **DRY Principle**: Templates and references extracted to separate files
- **Best Practices**: Based on Anthropic/OpenAI prompt engineering guidelines

**Effectiveness:** TBD (first iteration with refactored prompts)

---

## 2026-01-10: Analysis prompt

**Changes:**

- Included analysis prompt in cycle

**Rationale:**

- Need to analyze requirements before planning

**Effectiveness:**

- TBD (first iteration with analysis prompt)

---

## 2025-12-29: Initial Merge

**Changes:**

- Merged `.agent/rules/` prompts (TDD/implementation focus) with iteration tracking templates
- Created unified PLAN/DO/CHECK/ACT prompt structure
- Added cross-references to documentation structure

**Rationale:**

- Needed single source of truth for PDCA process
- Combined tactical (TDD) and strategic (iteration tracking) guidance
- Integrated with new bounded-context documentation structure

**Effectiveness:** TBD (first iteration with merged prompts)

---

## Template for Future Changes

### YYYY-MM-DD: [Change Description]

**Changes:**

- Bullet list of specific changes to prompts

**Rationale:**

- Why these changes were needed
- What problem they solve

**Effectiveness:**

- How well did the changes work?
- Metrics or observations
- Further improvements needed?

---

## Prompt Evaluation Criteria

When evolving prompts, assess:

1. **Clarity:** Are instructions unambiguous?
2. **Completeness:** Do they cover all necessary aspects?
3. **Practicality:** Can they be followed without excessive overhead?
4. **Effectiveness:** Do they produce desired outcomes?
5. **Consistency:** Do they align with other prompts in the PDCA cycle?
6. **Context Efficiency:** Do they minimize token usage while maintaining clarity?

---

## Meta-Learning Notes

**Common Issues Requiring Prompt Updates:**

- Phase overlap causing confusion (resolved 2026-01-17)
- TDD definition scattered across phases (resolved 2026-01-17)
- Root cause analysis duplicated in CHECK and ACT (resolved 2026-01-17)

**Patterns That Work Well:**

- Clear "Owns" vs "Does NOT Own" tables
- Human Decision Points with explicit questions
- Template references reducing inline verbosity
- Phase-specific responsibility matrices

**Anti-Patterns to Avoid:**

- Duplicating content across phases
- Long inline code examples (extract to templates)
- Implicit phase transitions (always explicit decision points)
- Assuming model capabilities (keep model-agnostic)
