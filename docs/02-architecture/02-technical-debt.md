# Technical Debt

## Backend

| ID              | Description                                                                                                                         | Impact            | Effort | Target        |
| :-------------- | :---------------------------------------------------------------------------------------------------------------------------------- | :---------------- | :----- | :------------ |
| **TD-AUDIT-01** | Inline `MockAuditEntity` in tests (`tests/unit/core/versioning/test_audit.py`). Should be refactored to a shared mock test utility. | Low (Duplication) | 0.5d   | Next Refactor |

## Frontend

| ID            | Description                                          | Impact                             | Effort | Target     |
| :------------ | :--------------------------------------------------- | :--------------------------------- | :----- | :--------- |
| **TD-FE-003** | Loose `as any` casting in `useCrud` hooks            | Type safety loss                   | 3h     | 2026-01-20 |
| **TD-FE-004** | `useWBEs` fetches full list (needs pagination)       | Slow load times for large datasets | 3h     | 2026-02-01 |
| **TD-FE-005** | Tree View needs visual improvement (currently table) | Sub-optimal UX                     | 2h     | 2026-02-01 |
