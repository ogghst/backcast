# Date Formatting Guide

Frontend guide for displaying dates, timestamps, and temporal ranges consistently across the application.

## Core Principle

**Always use backend-formatted dates when available.** The backend provides pre-formatted temporal data via `*_formatted` fields. Only use frontend formatters for raw datetime values.

## Backend Temporal Fields

Entities with temporal ranges (Project, WBE) provide these computed fields:

```typescript
interface TemporalData {
  // Raw ISO timestamps
  lower: string | null;
  upper: string | null;

  // Pre-formatted display strings
  lower_formatted: string;      // "January 15, 2026"
  upper_formatted: string;      // "Present" or formatted date
  is_currently_valid: boolean;
}
```

**Example API response:**
```json
{
  "valid_time": {
    "lower": "2026-01-15T10:00:00+00:00",
    "upper": null,
    "lower_formatted": "January 15, 2026",
    "upper_formatted": "Present",
    "is_currently_valid": true
  }
}
```

## Frontend Utilities

### Simple Date Formatting

Use `@/utils/formatters` for raw datetime values (not pre-formatted by backend):

```tsx
import { formatDate, formatDateTime } from '@/utils/formatters';

// Date only
formatDate(date)                           // "Jan 15, 2026" (browser locale)
formatDate(date, { style: 'short' })       // "1/15/26"
formatDate(null, { fallback: '-' })        // "-"

// Date and time
formatDateTime(timestamp)                  // "Jan 15, 2026, 10:30 AM"
```

### Temporal Range Formatting

For entities with backend-formatted temporal data:

```tsx
import { formatTemporalRange } from '@/utils/formatters';

<Tooltip title={formatTemporalRange(project.valid_time_formatted)}>
  {project.valid_time_formatted.lower_formatted}
</Tooltip>
```

**Result:** `"Jan 15, 2026 – Present"`

### Table Columns

In Ant Design tables, use the `formatDate` utility:

```tsx
{
  title: "Date",
  dataIndex: "registration_date",
  key: "registration_date",
  render: (date) => formatDate(date, { style: 'short', fallback: '-' }),
}
```

### Performance-Sensitive Components

For components rendering many dates, use the hook-based formatter:

```tsx
import { useDateFormatter } from '@/utils/formatters';

function MyComponent({ dates }) {
  const formatDate = useDateFormatter({ style: 'short' });
  return (
    <>
      {dates.map(d => <span key={d}>{formatDate(d)}</span>)}
    </>
  );
}
```

## Common Patterns

### Displaying Temporal Validity

```tsx
// Show validity period with "Present" for currently valid
<div>
  {project.valid_time_formatted.lower_formatted} – {
    project.valid_time_formatted.is_currently_valid
      ? "Present"
      : project.valid_time_formatted.upper_formatted
  }
</div>

// Or use the utility
<div>{formatTemporalRange(project.valid_time_formatted)}</div>
```

### Transaction Time Display

```tsx
// Show when a version was created
<small>Created: {wbe.transaction_time_formatted.lower_formatted}</small>
```

### Currency with Date

```tsx
import { formatCurrency, formatDate } from '@/utils/formatters';

<div>
  {formatCurrency(registration.amount)} – {
    formatDate(registration.registration_date)
  }
</div>
```

## Anti-Patterns to Avoid

### ❌ Don't: Manual dayjs formatting

```tsx
// DON'T DO THIS - use centralized utilities instead
import dayjs from 'dayjs';
render: (date) => dayjs(date).format("YYYY-MM-DD")
```

### ❌ Don't: Re-parse backend formatted dates

```tsx
// DON'T DO THIS - backend already formatted it
{new Date(project.valid_time_formatted.lower).toLocaleDateString()}

// DO THIS - use the pre-formatted value
{project.valid_time_formatted.lower_formatted}
```

### ❌ Don't: Direct toLocaleDateString calls

```tsx
// DON'T DO THIS - inconsistent across app
{new Date(date).toLocaleDateString()}

// DO THIS - centralized, locale-aware
{formatDate(date)}
```

## Entity-Specific Fields

| Entity | Formatted Field | Usage |
|--------|----------------|-------|
| Project | `valid_time_formatted` | Project validity period |
| Project | `transaction_time_formatted` | When project version was created |
| WBE | `valid_time_formatted` | WBE validity period |
| WBE | `transaction_time_formatted` | When WBE version was created |
| CostRegistration | `registration_date_formatted` | Date cost was incurred |

## Adding Formatted Fields to New Entities

Backend: Add computed field to schema:

```python
@computed_field
@property
def date_field_formatted(self) -> dict[str, str | None]:
    if not self.date_field:
        return {"iso": None, "formatted": "Unknown"}
    return {
        "iso": self.date_field.isoformat(),
        "formatted": self.date_field.strftime("%B %d, %Y"),
    }
```

Frontend: Regenerate API types, then use:

```tsx
{entity.date_field_formatted.formatted}
```

## References

- Backend temporal utilities: `backend/app/core/temporal.py`
- Frontend formatters: `frontend/src/utils/formatters.ts`
- History version mapping: `frontend/src/utils/versionHistory.ts`
