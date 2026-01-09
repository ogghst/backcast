## Request Analysis: FilterParser Error Messages (TD-013)

### Clarified Requirements

**User Intent**: The current `FilterParser` implementation handles errors inconsistently. Invalid fields raise `ValueError` (which likely results in 500 Internal Server Error if not caught), while type mismatches are silently ignored (falling back to strings). This makes debugging integration issues difficult for frontend developers.

**Requirements**:

1.  **Specific Exceptions**: throw distinct exceptions for different failure modes (e.g., `InvalidFilterField`, `InvalidFilterValue`).
2.  **Type Validation**: Explicitly handle type conversion failures instead of silently ignoring them (optional strict mode?).
3.  **User-Friendly Messages**: Ensure exceptions contain enough context (expected type, allowed fields) to be useful in API responses.
4.  **No 500s**: Ensure these validation errors map to 400 Bad Request in the API layer.

### Context Discovery Findings

**Architecture Context:**

- **Bounded Context**: Core / Cross-cutting (Filtering).
- **Existing Patterns**: Pydantic validation is used elsewhere. `FilterParser` is a custom utility for URL parameter parsing.

**Codebase Analysis (Backend):**

- **File**: `app/core/filtering.py`
- **Current Behavior**:
  - Invalid Field (Model): `raise ValueError(f"Invalid filter field '{field_name}'...")`
  - Invalid Field (Whitelist): `raise ValueError(f"Filter field '{field_name}' is not allowed...")`
  - Type Casting: `try...except (ValueError, TypeError): pass` (Silent Fallback)

---

## Solution Options

### Option 1: Custom Exception Hierarchy & Strict Typing

**Architecture & Design:**
Introduce a custom exception hierarchy inheriting from a base `FilterError`.

```python
class FilterError(Exception): pass
class FilterFieldNotAllowedError(FilterError): pass
class FilterValueTypeError(FilterError): pass
```

Modify `FilterParser.build_sqlalchemy_filters` to accept a `strict: bool = True` flag.

**UX Design (API Consumer):**

- **400 Bad Request** response with body:
  ```json
  {
    "detail": "Invalid filter value for field 'level': expected integer, got 'abc'"
  }
  ```

**Implementation:**

1.  Define exceptions in `app/core/exceptions.py` (or `filtering.py`).
2.  Update `build_sqlalchemy_filters` to raise `FilterValueTypeError` on casting failure if strict.
3.  Update `build_sqlalchemy_filters` to raise `FilterFieldNotAllowedError` instead of `ValueError`.
4.  Add exception handler in `app/main.py` (or router) to convert `FilterError` to 400.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Clear API feedback, easier debugging, better security (no unexpected queries). |
| Cons | Breaking change for existing loose clients (if any). |
| Complexity | Low. |
| Maintainability | High. |

---

### Option 2: Integration with FastAPI/Pydantic Validation

**Architecture & Design:**
Instead of custom parsing logic, define Pydantic models for filters.

**Implementation:**
This would require changing the API signature from `filters: str` to `filters: Json` or a custom `Depends` class that uses Pydantic.
Given the current `key:value;key2:val2` custom syntax, this is **complex** to map directly to Pydantic without a custom validator.

**Trade-offs:**
| Aspect | Assessment |
|--------|------------|
| Pros | Native FastAPI docs integration. |
| Cons | High effort to rewrite parsing logic; changes API contract significantly. |
| Complexity | High. |

---

## Comparison Summary

| Criteria      | Option 1 (Custom Exceptions) | Option 2 (Pydantic)  |
| ------------- | ---------------------------- | -------------------- |
| Effort        | 2 hours                      | 6 hours              |
| Compatibility | Backward compatible (mostly) | Breaking API changes |
| Debuggability | Good                         | Excellent            |

## Recommendation

**I recommend Option 1.** It directly addresses the technical debt without rewriting the entire filtering strategy. It improves debuggability significantly with low effort.

### Plan:

1.  Define `FilterValidationError` (base) and subclasses.
2.  Update `FilterParser` logic to use these exceptions.
3.  Add global exception handler to FastAPI app.
4.  Update tests.

## Questions for Decision

1.  Do we want to enforce **strict** type checking by default (raising error if `level=abc`), or keep the silent fallback for backward compatibility? (Recommendation: Strict, as "level"="abc" is almost certainly a bug).
