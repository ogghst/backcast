# PLANNING PHASE: Execution Strategy

Based on our analysis and the approach we've selected, create a coherent implementation plan.

## EXECUTION CONTEXT

- This plan will be implemented using TDD discipline with human supervision
- Implementation will occur in steps within this conversation thread
- Each step must have clear stop/go criteria

## PLAN STRUCTURE REQUIREMENTS

1. IMPLEMENTATION STEPS (Numbered list with explicit acceptance criteria)
   For each step provide:
   - Step number and description
   - Acceptance criteria (what must be true when this step is complete)
   - Test-first requirement (which test must fail before this step begins)
   - Expected files to be modified or created
   - Dependencies on previous steps

2. TDD DISCIPLINE RULES
   - Failing test MUST exist before any production code changes
   - Maximum 3 iteration attempts per step before stopping to ask for help
   - Red-green-refactor cycle must be followed for each step
   - Tests must verify behavior, not just compilation

3. PROCESS CHECKPOINTS
   After steps [specify key milestones], pause and ask:
   - "Should we continue with the plan as-is?"
   - "Have any assumptions been invalidated?"
   - "Does the current state match our expectations?"

4. SCOPE BOUNDARIES
   You shall adhere on what the user is asking and avoid scope creep. If you find useful improvements or alternatives, ask the user for confirmation

5. ROLLBACK STRATEGY
   If we need to abandon this approach:
   - What's the safe rollback point?
   - What alternative do we try next?

## OUTPUT

Format your plan as a numbered checklist that can be tracked during implementation.

## CONFIRM

Confirm you understand the plan structure requirements before generating the plan.
