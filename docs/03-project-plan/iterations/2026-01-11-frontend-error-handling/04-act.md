# ACT Phase: Standardization & Improvements

**Iteration:** 2026-01-11-frontend-error-handling  
**Date:** 2026-01-11

---

## 2. Pattern Standardization

| Pattern                  | Description                                                                              | Benefits                                                      | Risks                                          | Standardize?       |
| :----------------------- | :--------------------------------------------------------------------------------------- | :------------------------------------------------------------ | :--------------------------------------------- | :----------------- |
| **Global Axios Config**  | Configure `axios.defaults` instead of custom instances for generated code compatibility. | 100% interceptor coverage, fixes auth bugs in generated code. | Global state mutation (low risk if localized). | **Yes** (Option A) |
| **Global Error Toaster** | Catch-all interceptor for non-2xx responses.                                             | Consistent UI, less boilerplate in components.                | Might be too noisy if not tuned.               | **Yes** (Option A) |

### Actions

- [x] Implemented in `src/api/client.ts`.
- [ ] Update `docs/02-architecture/cross-cutting/api-response-evcs-implementation-guide.md` to reflect that global error handling is now the standard (removed need for manual error handling in many cases).

---

## 3. Documentation Updates Required

| Document                                                      | Update Needed                                                       | Priority |
| :------------------------------------------------------------ | :------------------------------------------------------------------ | :------- |
| `docs/02-architecture/cross-cutting/api-response-evcs-implementation-guide.md` | Add section on "Global Error Handling" and the Toaster pattern.     | Medium   |
| `docs/02-architecture/coding-standards.md`                    | Update "Frontend Error Handling" to mention the global interceptor. | Low      |

---

## 4. Technical Debt Ledger

### Debt Created

None.

### Debt Resolved

| Item                     | Resolution                                        | Time |
| :----------------------- | :------------------------------------------------ | :--- |
| **Auth Interceptor Bug** | Fixed by switching to global axios configuration. | 15m  |
| **Missing Error UI**     | Fixed by implementing global toaster.             | 15m  |

---

## 10. Concrete Action Items

- [ ] Update `docs/02-architecture/cross-cutting/api-response-evcs-implementation-guide.md` with Global Error Handling patterns.
- [ ] Monitor user feedback for "toaster noise" (too many errors shown).

---

## Conclusion

The **Global Axios Configuration** pattern is now the standard for this project. It ensures that all auto-generated API clients automatically inherit authentication and error handling logic, significantly improving robustness and maintainability.
