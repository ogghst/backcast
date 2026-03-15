# Dashboard Implementation Plan

**Date:** 2026-03-15
**Iteration:** Main Dashboard Implementation
**Status:** Planning Complete
**Related Analysis:** `00-analysis.md`

## Overview

This plan details the implementation of the main dashboard page for the Backcast Project Budget Management & EVMS system. The dashboard will display recent activity across all business entities (projects, WBEs, cost elements, change orders) and provide quick navigation to entity detail pages.

## Implementation Strategy

We'll implement this as a coordinated full-stack feature with backend API development followed by frontend component development. The implementation is divided into 5 phases to ensure proper testing and integration at each step.

## Phase 1: Backend API Development

### 1.1 Create Dashboard Service
**File:** `backend/app/services/dashboard_service.py`

**Responsibilities:**
- Aggregate recent activity from all entity types
- Calculate last edited project with metrics
- Format data for frontend consumption
- Implement caching for performance

**Key Functions:**
```python
class DashboardService:
    def get_recent_activity(self, user_id: str, limit: int = 10) -> DashboardActivityResponse
    def get_last_edited_project(self, user_id: str) -> ProjectSpotlight
    def get_dashboard_data(self, user_id: str) -> DashboardData
```

**Dependencies:**
- ProjectsService
- WBEService
- CostElementService
- ChangeOrderService
- SQLAlchemy for transaction date queries

### 1.2 Create Dashboard API Endpoint
**File:** `backend/app/api/routes/dashboard.py`

**Endpoint:** `GET /api/v1/dashboard/recent-activity`

**Response Schema:**
```python
class DashboardActivity(BaseModel):
    entity_type: Literal["project", "wbe", "cost_element", "change_order"]
    entity_id: str
    entity_name: str
    activity_type: Literal["created", "updated", "deleted", "merged"]
    timestamp: datetime
    context: Optional[Dict[str, Any]]

class ProjectSpotlight(BaseModel):
    project: ProjectRead
    last_activity: datetime
    metrics: Dict[str, Any]

class DashboardData(BaseModel):
    last_edited_project: ProjectSpotlight
    recent_activity: Dict[str, List[DashboardActivity]]
```

**Authentication:** Required (JWT Bearer token)

**Query Parameters:**
- `activity_limit`: Number of activities per entity type (default: 10)

### 1.3 Add Transaction Date Queries
**Files:**
- `backend/app/services/project_service.py`
- `backend/app/services/wbe_service.py`
- `backend/app/services/cost_element_service.py`
- `backend/app/services/change_order_service.py`

**Changes:**
- Add methods to query most recently updated entities
- Filter by user permissions
- Include transaction metadata

### 1.4 Backend Testing
**File:** `backend/tests/integration/test_dashboard_api.py`

**Test Coverage:**
- API endpoint returns correct data structure
- User permissions are respected
- Empty data handled gracefully
- Caching works correctly
- Performance under load

## Phase 2: Frontend Data Layer

### 2.1 Generate API Types
**Action:** Run `npm run generate-client` after backend changes

**Verify:** Dashboard types are generated in `frontend/src/api/generated/`

### 2.2 Create Dashboard Data Hook
**File:** `frontend/src/features/dashboard/hooks/useDashboardData.ts`

**Hook Signature:**
```typescript
export const useDashboardData = (options?: {
  activityLimit?: number;
  enabled?: boolean;
}) => {
  return useQuery<DashboardData>({
    queryKey: ["dashboard", "recent-activity"],
    queryFn: async () => {
      // API call implementation
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
};
```

**Features:**
- TanStack Query integration
- Automatic caching and refetching
- Error handling with toast notifications
- Loading state management

### 2.3 Add Query Keys
**File:** `frontend/src/api/queryKeys.ts`

**Add:**
```typescript
export const queryKeys = {
  // ... existing keys
  dashboard: {
    all: ["dashboard"] as const,
    recentActivity: (params?: any) =>
      ["dashboard", "recent-activity", params] as const,
  },
};
```

### 2.4 Frontend Testing (Data Layer)
**File:** `frontend/src/features/dashboard/hooks/useDashboardData.test.ts`

**Test Coverage:**
- Hook fetches data correctly
- Error handling works
- Cache keys are consistent
- Loading states are accurate

## Phase 3: Frontend Components

### 3.1 Create Component Structure
**Directory:** `frontend/src/features/dashboard/`

**Structure:**
```
features/dashboard/
├── components/
│   ├── DashboardHeader.tsx
│   ├── ProjectSpotlight.tsx
│   ├── ActivityGrid.tsx
│   ├── ActivitySection.tsx
│   ├── ActivityItem.tsx
│   └── RelativeTime.tsx
├── hooks/
│   └── useDashboardData.ts
├── types.ts
└── index.ts
```

### 3.2 Implement Base Components

#### 3.2.1 DashboardHeader
**File:** `frontend/src/features/dashboard/components/DashboardHeader.tsx`

**Features:**
- Welcome message with user name
- Current date/time display
- Responsive typography

**Props:**
```typescript
interface DashboardHeaderProps {
  userName: string;
}
```

#### 3.2.2 ProjectSpotlight
**File:** `frontend/src/features/dashboard/components/ProjectSpotlight.tsx`

**Features:**
- Display last edited project
- Key metrics (budget, EVM status, change orders)
- Navigation to project detail
- Visual progress indicator

**Props:**
```typescript
interface ProjectSpotlightProps {
  project: ProjectRead;
  lastActivity: string;
  metrics: ProjectMetrics;
}
```

#### 3.2.3 ActivityItem
**File:** `frontend/src/features/dashboard/components/ActivityItem.tsx`

**Features:**
- Entity name (clickable link)
- Activity type badge
- Relative timestamp
- Context information
- Hover states

**Props:**
```typescript
interface ActivityItemProps {
  activity: DashboardActivity;
  entityType: "project" | "wbe" | "cost_element" | "change_order";
}
```

#### 3.2.4 ActivitySection
**File:** `frontend/src/features/dashboard/components/ActivitySection.tsx`

**Features:**
- Section header with icon
- Activity list
- "View All" link
- Empty state handling
- Loading skeleton

**Props:**
```typescript
interface ActivitySectionProps {
  title: string;
  icon: React.ReactNode;
  activities: DashboardActivity[];
  entityType: "project" | "wbe" | "cost_element" | "change_order";
  viewAllPath: string;
  loading?: boolean;
}
```

#### 3.2.5 ActivityGrid
**File:** `frontend/src/features/dashboard/components/ActivityGrid.tsx`

**Features:**
- 2x2 responsive grid
- Stacks to single column on mobile
- Gap and padding using design tokens

**Props:**
```typescript
interface ActivityGridProps {
  activities: {
    projects: DashboardActivity[];
    wbes: DashboardActivity[];
    costElements: DashboardActivity[];
    changeOrders: DashboardActivity[];
  };
  loading?: boolean;
}
```

#### 3.2.6 RelativeTime
**File:** `frontend/src/features/dashboard/components/RelativeTime.tsx`

**Features:**
- Format timestamps as relative time
- Handle various time ranges
- Internationalization support

**Props:**
```typescript
interface RelativeTimeProps {
  timestamp: string;
}
```

### 3.3 Update Home Page
**File:** `frontend/src/pages/Home.tsx`

**Implementation:**
```typescript
import { DashboardHeader } from "@/features/dashboard/components/DashboardHeader";
import { ProjectSpotlight } from "@/features/dashboard/components/ProjectSpotlight";
import { ActivityGrid } from "@/features/dashboard/components/ActivityGrid";
import { useDashboardData } from "@/features/dashboard/hooks/useDashboardData";
import { Alert, Skeleton } from "antd";

const Home: React.FC = () => {
  const { data, isLoading, error } = useDashboardData();
  const { token } = theme.useToken();
  const { user } = useAuthStore();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState error={error} />;
  }

  return (
    <div style={{ padding: token.paddingXL }}>
      <DashboardHeader userName={user?.name || "User"} />
      {data?.last_edited_project && (
        <ProjectSpotlight {...data.last_edited_project} />
      )}
      <ActivityGrid activities={data?.recent_activity} />
    </div>
  );
};
```

## Phase 4: Styling & Polish

### 4.1 Apply Design Tokens
**Files:** All dashboard components

**Ensure:**
- All spacing uses `token.padding*` or `token.margin*`
- All colors use semantic tokens
- All typography uses `token.fontSize*` and `token.fontWeight*`
- All border radius uses `token.borderRadius*`

### 4.2 Responsive Design
**Files:**
- `frontend/src/features/dashboard/components/ActivityGrid.tsx`
- `frontend/src/features/dashboard/components/ProjectSpotlight.tsx`

**Breakpoints:**
- Desktop: Grid display, full metrics
- Tablet: Grid display, reduced metrics
- Mobile: Stack layout, essential metrics only

**Implementation:**
- Use Ant Design Grid system
- CSS Grid for component layouts
- Media queries for component-specific adjustments

### 4.3 Loading States
**File:** `frontend/src/features/dashboard/components/DashboardSkeleton.tsx`

**Components:**
- Page-level skeleton matching final layout
- Shimmer effect using Ant Design Skeleton
- Maintain layout structure during loading

### 4.4 Error States
**File:** `frontend/src/features/dashboard/components/ErrorState.tsx`

**Scenarios:**
- Network error
- Permission denied
- Server error

**Features:**
- Clear error message
- Retry button
- Support contact link

### 4.5 Empty States
**File:** `frontend/src/features/dashboard/components/EmptyState.tsx`

**Scenarios:**
- No recent activity
- No projects (new user)
- No accessible entities

**Features:**
- Friendly message
- Call to action (create first project)
- Illustration or icon

## Phase 5: Integration & Testing

### 5.1 Navigation Integration
**Verify:**
- All entity links route correctly
- Browser back button works
- TimeMachine context not affected
- Permissions respected

### 5.2 Component Testing
**Files:**
- `frontend/src/features/dashboard/components/*.test.tsx`

**Coverage:**
- All components rendered correctly
- Props handled properly
- User interactions work
- Edge cases handled

### 5.3 Integration Testing
**File:** `frontend/src/pages/Home.test.tsx`

**Scenarios:**
- Complete user flow from landing to entity navigation
- Loading states transition to data
- Error states handled
- Permissions respected

### 5.4 Accessibility Testing
**Tools:**
- axe DevTools
- Keyboard navigation
- Screen reader testing

**Verify:**
- Semantic HTML structure
- ARIA labels present
- Keyboard navigation works
- Focus indicators visible
- Color contrast meets WCAG AA

### 5.5 Performance Testing
**Metrics:**
- Page load time < 2s on 3G
- Bundle size impact < 30KB
- API response time < 500ms
- No memory leaks

**Tools:**
- Lighthouse
- Chrome DevTools Performance
- Bundle analyzer

## Implementation Order

### Sprint 1: Backend Foundation
1. ✅ Create dashboard service
2. ✅ Implement API endpoint
3. ✅ Add transaction date queries
4. ✅ Write backend tests
5. ✅ Generate frontend types

### Sprint 2: Frontend Data Layer
1. ✅ Create useDashboardData hook
2. ✅ Add query keys
3. ✅ Test data fetching
4. ✅ Test error handling

### Sprint 3: Core Components
1. ✅ DashboardHeader component
2. ✅ ProjectSpotlight component
3. ✅ ActivityItem component
4. ✅ RelativeTime component

### Sprint 4: Layout Components
1. ✅ ActivitySection component
2. ✅ ActivityGrid component
3. ✅ Update Home page
4. ✅ Responsive design

### Sprint 5: Polish & Testing
1. ✅ Loading states
2. ✅ Error states
3. ✅ Empty states
4. ✅ Component tests
5. ✅ Integration tests
6. ✅ Accessibility audit
7. ✅ Performance optimization

## Dependencies & Blockers

### External Dependencies
- ✅ Backend API must be deployed first
- ✅ OpenAPI spec must be regenerated
- ✅ Design tokens already available

### Internal Dependencies
- ✅ ProjectsService methods available
- ✅ WBEService methods available
- ✅ CostElementService methods available
- ✅ ChangeOrderService methods available

### Potential Blockers
- ⚠️ Transaction date queries may need database indexes
- ⚠️ Performance issues with large datasets
- ⚠️ Permission complexity may slow queries

## Risk Mitigation

### Performance Risks
**Risk:** Dashboard queries are slow with large datasets
**Mitigation:**
- Add database indexes on transaction date columns
- Implement result caching (10-minute TTL)
- Limit activity items per entity type
- Use pagination for activity lists

### Data Quality Risks
**Risk:** Missing or inconsistent transaction dates
**Mitigation:**
- Add default values for missing dates
- Validate data in service layer
- Log data quality issues
- Show warning to users if data is incomplete

### UX Risks
**Risk:** Dashboard feels overwhelming
**Mitigation:**
- Limit to 5-10 items per section
- Use progressive disclosure
- Provide empty states for new users
- A/B test different layouts

## Success Criteria

### Functional Requirements
- ✅ Dashboard displays recent activity for all entity types
- ✅ Users can click entities to navigate to detail pages
- ✅ Last edited project shown with key metrics
- ✅ Data sourced from entity transaction dates
- ✅ Responsive on all screen sizes

### Non-Functional Requirements
- ✅ Page loads in < 2 seconds on 3G
- ✅ All components unit tested (80%+ coverage)
- ✅ Accessibility audit passed
- ✅ No console errors or warnings
- ✅ Consistent with design system

### User Acceptance Criteria
- ✅ User can find last activity within 5 seconds
- ✅ User can navigate to any entity in < 3 clicks
- ✅ Visual hierarchy is clear and intuitive
- ✅ Loading states are smooth
- ✅ Error states are helpful

## Next Actions

1. **Backend Team:** Begin implementation of `/api/v1/dashboard/recent-activity` endpoint
2. **Frontend Team:** Create component structure and base components
3. **Design Team:** Create detailed mockups for each breakpoint (if needed)
4. **QA Team:** Prepare test plan for dashboard functionality

---

**Planning Complete.** Ready to proceed to implementation phase.
