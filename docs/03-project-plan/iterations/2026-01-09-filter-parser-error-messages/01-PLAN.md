# PLAN Phase: FilterParser Error Messages

**Iteration:** 2026-01-09-filter-parser-error-messages  
**Status:** 📝 Draft  
**Date:** 2026-01-09

---

## Phase 1: Context Analysis

### Documentation Review

- **Coding Standards:** "Zero Tolerance for any types" implies strong preference for strict typing and validation. "Backend as Source of Truth" supports enforcing strict filtering rules on the backend.
- **Technical Debt Register:** TD-013 explicitly calls for this improvement to aid debugging.

### Codebase Analysis

- **`app/core/filtering.py`:** Contains `FilterParser` class. Current error handling is minimal (generic `ValueError` or silent suppression).
- **`tests/unit/core/test_filtering.py`:** Existing comprehensive test suite to extend.

---

## Phase 2: Problem Definition

### 1. Problem Statement

The current `FilterParser` fails silently when invalid types are provided (e.g., string for integer) or raises generic `ValueError`s for invalid fields. This results in either confusing 500 errors or unexpected empty results, making frontend integration and debugging difficult.

### 2. Success Criteria

**Functional Criteria:**

- [ ] `FilterParser` raises specific exception for invalid field names.
- [ ] `FilterParser` raises specific exception for value type mismatches (strict mode).
- [ ] API returns **400 Bad Request** with clear, actionable error messages for these cases.
- [ ] Valid requests continue to work unchanged.

**Technical Criteria:**

- [ ] Custom exception hierarchy implemented (`FilterError` base).
- [ ] 100% test coverage for new exceptions and handlers.
- [ ] Zero regression for valid query parameters.

### 3. Scope Definition

**In Scope:**

- Creating `app/core/exceptions/filtering.py` (or similar).
- Refactoring `app/core/filtering.py` to use new exceptions.
- Adding global exception handler in `app/main.py`.
- Updating `tests/unit/core/test_filtering.py`.

**Out of Scope:**

- Changing the URL filter syntax (`key:val;key2:val2`).
- Pydantic model integration (deferred to future major refactor).

---

## Phase 3: Implementation Options

### Selected Approach: Custom Exception Hierarchy & Strict Typing (Option 1)

This option represents a focused, high-impact fix with minimal complexity and risk.

| Aspect         | Details                                                                  |
| :------------- | :----------------------------------------------------------------------- |
| **Exceptions** | `FilterError`, `FilterFieldNotAllowedError`, `FilterValueTypeError`      |
| **Logic**      | Add `strict=True` to parser; explicit type checks instead of `try/pass`. |
| **API**        | Map `FilterError` -> HTTP 400                                            |

---

## Phase 4: Technical Design

### TDD Test Blueprint

#### Unit Tests (`tests/unit/core/test_filtering.py`)

1.  **`test_strict_type_validation_failure`**:
    - Input: `level:abc` (where level is Int)
    - Expect: `raises FilterValueTypeError`
2.  **`test_invalid_field_failure`**:
    - Input: `invalid_col:val`
    - Expect: `raises FilterFieldNotAllowedError` (checking message content)
3.  **`test_boolean_strict_parsing`**:
    - Input: `active:notbool`
    - Expect: `raises FilterValueTypeError`

#### Integration Tests (`tests/api/test_filtering_integration.py` - New/Modified)

1.  **`test_api_returns_400_on_filter_error`**:
    - Request: `GET /projects?filters=budget:invalid`
    - Expect: `400 Bad Request`
    - Body: `{"detail": "Invalid filter value..."}`

### Implementation Strategy

1.  **Define Exceptions**: Create `FilterError` hierarchy.
2.  **Implement Handlers**: Add `exception_handler` for `FilterError` in `main.py`.
3.  **Refactor Parser**:
    - Remove `try...except` silent fallback.
    - Implement explicit type casting checks.
    - Raise new exceptions.
4.  **Update Tests**: Verify new behavior.

---

## Phase 5: Risk Assessment

| Risk Type       | Description                                            | Probability | Impact | Mitigation Strategy                                   |
| :-------------- | :----------------------------------------------------- | :---------- | :----- | :---------------------------------------------------- |
| **Integration** | Strict validation breaks existing loose frontend calls | Low         | Med    | Frontend recently typed (TD-014), so risk is minimal. |
| **API**         | 500 -> 400 change affects error monitoring             | Low         | Low    | Document change; 400 is correct status code.          |

---

## Phase 6: Effort Estimation

- **Development:** 1.5 hours
- **Testing:** 0.5 hours
- **Total Estimated Effort:** 2 hours

---

**Approval:** Approved by User (via Chat)  
**Date:** 2026-01-09
