# Dashboard Design Analysis - Main Dashboard Page

**Date:** 2026-03-15
**Iteration:** Main Dashboard Implementation
**Status:** Analysis Complete

## Executive Summary

This analysis defines the design direction for the main dashboard page of the Backcast Project Budget Management & Earned Value Management System. The dashboard will serve as the central hub for users to quickly understand recent activity across all business entities and access the most relevant project information.

## Current State Assessment

### Existing Design System
The Backcast application uses a sophisticated, refined design system with:
- **Color Palette:** Soft, warm tones with a primary teal-blue (#4a7c91)
- **Typography:** Ubuntu font family with clear hierarchy (10px-24px scale)
- **Spacing:** 4px-based grid system with consistent tokens
- **Aesthetic:** Professional, polished, comfort-oriented for extended use
- **Components:** Ant Design with custom theming and design tokens

### Current Home Page
The current `/` route renders a minimal placeholder:
```tsx
<Title level={2}>Welcome to Backcast</Title>
<Paragraph>This is the dashboard for Backcast.</Paragraph>
```

### Navigation Structure
- **Header Navigation:** Dashboard (Home), Projects, AI Chat (permission-based)
- **Layout:** Consistent AppLayout with HeaderNavigation, TimeMachine context, and UserProfile
- **Routing:** React Router v6 with protected routes

## User Requirements Analysis

### Functional Requirements
1. **Last Activity Display:** Show recent activity on business entities:
   - Projects
   - Work Breakdown Elements (WBEs)
   - Cost Elements
   - Change Orders

2. **Entity Navigation:** Users must be able to click on entities to navigate to their detail pages

3. **Last Edited Project:** Overview of the most recently edited project with key details

4. **Data Source:** Entity transaction dates from the backend

### User Context
- **Primary Users:** Project managers, financial controllers, engineers
- **Use Case:** Quick overview of system state and recent changes
- **Frequency:** Multiple times per day
- **Session Duration:** Extended periods (comfort-focused design is appropriate)

## Design Direction

### Aesthetic Philosophy
**"Sophisticated Professional Command Center"**

The dashboard should embody:
- **Clarity over density:** Information-rich but not overwhelming
- **Temporal awareness:** Emphasize recency and activity patterns
- **Action-oriented:** Clear paths to detailed views
- **Visual hierarchy:** Guide attention to the most important information

### Visual Strategy

#### 1. Layout Architecture
```
┌─────────────────────────────────────────────────────────┐
│  Welcome back, [User]                     [Profile]      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Last Edited Project Spotlight                   │   │
│  │  [Project Card with key metrics]                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  ┌───────────────────────┐  ┌───────────────────────┐ │
│  │  Recent Projects      │  │  Recent WBEs          │ │
│  │  [Activity List]      │  │  [Activity List]      │ │
│  └───────────────────────┘  └───────────────────────┘ │
│                                                           │
│  ┌───────────────────────┐  ┌───────────────────────┐ │
│  │  Recent Cost Elements │  │  Recent Change Orders │ │
│  │  [Activity List]      │  │  [Activity List]      │ │
│  └───────────────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

#### 2. Component Hierarchy

**Primary Section (Top):**
- Welcome message with user context
- Last Edited Project Spotlight (largest, most detailed)

**Secondary Sections (Grid):**
- 2x2 grid of entity activity lists
- Each section: Title + activity list + "View All" link

**Tertiary Elements:**
- Subtle timestamps showing relative time ("2 hours ago")
- Entity type indicators (icons or badges)
- Activity type indicators (created, updated, merged, etc.)

#### 3. Typography & Spacing

**Welcome Section:**
- Greeting: `fontSizeXL` (20px), `fontWeightSemiBold` (600)
- User name: `fontSizeXXL` (24px), `fontWeightBold` (700)
- Color: `colorText` (primary) + `colorPrimary` accent

**Section Headers:**
- Title: `fontSizeLG` (16px), `fontWeightSemiBold` (600)
- Margin bottom: `marginMD` (16px)
- Color: `colorText` with subtle bottom border

**Activity Items:**
- Entity name: `fontSize` (14px), `fontWeightMedium` (500)
- Metadata: `fontSizeSM` (12px), `colorTextSecondary`
- Timestamp: `fontSizeSM` (12px), `colorTextTertiary`
- Padding: `paddingSM` (8px) vertical, `paddingMD` (16px) horizontal

#### 4. Color Application

**Background Layers:**
- Page background: `colorBgLayout` (#f5f3f0 - soft cream)
- Card containers: `colorBgContainer` (#faf9f7 - warm off-white)
- Spotlight card: `colorBgElevated` (#ffffff - pure white)

**Text Colors:**
- Primary text: `colorText` (#2a2a2a - deep charcoal)
- Secondary text: `colorTextSecondary` (#6b6b6b - medium gray)
- Tertiary text: `colorTextTertiary` (#9a9a9a - light gray)

**Accent Colors:**
- Entity type indicators: Use semantic colors appropriately
  - Projects: `colorPrimary` (#4a7c91 - teal-blue)
  - WBEs: `colorInfo` (#5d8ba8 - muted blue)
  - Cost Elements: `colorChartEV` (#7bc49a - muted mint)
  - Change Orders: `colorChartForecast` (#d4a549 - warm amber)

**Borders:**
- Card borders: `colorBorder` (#e8e6e3 - soft warm gray)
- Subtle dividers: `colorBorderSecondary` (#f0eee9 - lighter border)

#### 5. Interactive Elements

**Hover States:**
- Activity items: Subtle background shift using `colorBgLayout`
- Entity cards: Slight elevation with shadow
- Links: Color shift to `colorPrimary` with underline

**Click Targets:**
- Minimum touch target: 44px height (accessibility)
- Clear visual feedback on active/hover states
- Smooth transitions (150-200ms)

**Loading States:**
- Skeleton screens matching final layout
- Shimmer effect using Ant Design's Skeleton component
- Maintain layout structure during loading

#### 6. Data Visualization

**Last Edited Project Spotlight:**
- Project name (large, bold)
- Key metrics in small cards:
  - Total budget
  - Current EVM status
  - Active change orders count
  - Last activity timestamp
- Visual progress indicator (subtle progress bar)
- "View Project" button (primary action)

**Activity Lists:**
- Entity name (clickable, primary link)
- Brief context (parent project for WBEs, etc.)
- Relative timestamp
- Activity type badge (created/updated/deleted)
- Truncate long names with ellipsis

## Technical Considerations

### Backend API Requirements
**New Endpoint Needed:** `/api/v1/dashboard/recent-activity`
```typescript
interface DashboardActivity {
  entity_type: 'project' | 'wbe' | 'cost_element' | 'change_order';
  entity_id: string;
  entity_name: string;
  activity_type: 'created' | 'updated' | 'deleted' | 'merged';
  timestamp: string; // ISO 8601
  context?: {
    project_id?: string;
    project_name?: string;
    parent_id?: string;
    // Additional context as needed
  };
}

interface DashboardData {
  last_edited_project: {
    project: ProjectRead;
    last_activity: string;
    metrics: {
      total_budget: number;
      evm_status: string;
      active_change_orders: number;
    };
  };
  recent_activity: {
    projects: DashboardActivity[];
    wbes: DashboardActivity[];
    cost_elements: DashboardActivity[];
    change_orders: DashboardActivity[];
  };
}
```

### Frontend Implementation Strategy

**Component Structure:**
```
Home/
├── DashboardHeader.tsx          # Welcome + user context
├── ProjectSpotlight.tsx         # Last edited project card
├── ActivityGrid.tsx             # 2x2 grid layout
│   ├── ActivitySection.tsx      # Entity-specific activity list
│   │   ├── ActivityHeader.tsx
│   │   ├── ActivityList.tsx
│   │   │   └── ActivityItem.tsx
│   │   └── ViewAllLink.tsx
└── hooks/
    └── useDashboardData.ts      # Custom hook for data fetching
```

**Data Fetching:**
- Custom hook: `useDashboardData()`
- TanStack Query for caching and invalidation
- Stale time: 5 minutes (activity updates are not real-time)
- Refetch on window focus (optional)

**State Management:**
- No global state needed (dashboard data is transient)
- Local component state for loading/error states
- TimeMachine context not needed on dashboard (no entity context)

### Responsive Design

**Breakpoints:**
- Desktop (>1200px): 2x2 grid, full spotlight card
- Tablet (768px-1200px): 2x2 grid, compact spotlight
- Mobile (<768px): Single column, stacked sections

**Adaptations:**
- Hide less critical metrics on smaller screens
- Reduce card padding on mobile
- Simplify spotlight card to essential info
- Ensure touch targets remain 44px minimum

## Accessibility Requirements

- **Semantic HTML:** Proper heading hierarchy (h1 → h2 → h3)
- **Keyboard Navigation:** All interactive elements accessible via Tab
- **Screen Readers:** ARIA labels for activity type indicators
- **Color Contrast:** WCAG AA compliant (already met by design system)
- **Focus Indicators:** Clear focus rings using `colorPrimary`
- **Error States:** Clear error messages with recovery options

## Performance Considerations

- **Lazy Loading:** Load activity lists in parallel, independently
- **Pagination:** Limit each activity list to 5-10 items
- **Caching:** Aggressive caching (5-10 minutes) for dashboard data
- **Optimistic UI:** Not needed (read-only dashboard)
- **Bundle Size:** Keep dashboard components under 50KB gzipped

## Success Metrics

### User Experience
- **Time to Value:** User can see last activity within 2 seconds of page load
- **Navigation Efficiency:** < 3 clicks to reach any entity from dashboard
- **Visual Clarity:** User can identify most recent activity in < 5 seconds

### Technical Performance
- **Page Load:** Dashboard fully rendered in < 2 seconds on 3G
- **API Response:** Dashboard data API responds in < 500ms
- **Bundle Impact:** Dashboard adds < 30KB to initial bundle

### Business Value
- **Engagement:** Dashboard used in > 80% of sessions
- **Navigation Reduction:** Direct navigation to entities reduced by 40%
- **User Satisfaction:** Dashboard rated 4+ out of 5 in user feedback

## Design Artifacts Needed

### Phase 1: Design System Extension
1. **Dashboard Component Library:**
   - ActivityItem component (with variants for each entity type)
   - ProjectSpotlight component (with metrics cards)
   - ActivitySection component (reusable section wrapper)
   - RelativeTime component (formatted timestamps)

### Phase 2: Page Layout
1. **Responsive Layout Mockups:**
   - Desktop (1200px+)
   - Tablet (768px-1200px)
   - Mobile (<768px)

2. **State Mockups:**
   - Loading state
   - Empty state (no activity)
   - Error state
   - Populated state

### Phase 3: Interaction Design
1. **Hover State Specifications:**
   - Activity item hover
   - Card elevation on hover
   - Button states

2. **Animation Specifications:**
   - Page load stagger (100ms delays)
   - List item entrance (slide-up fade)
   - Loading shimmer animation

## Implementation Phases

### Phase 1: Foundation (Analysis Complete ✓)
- ✅ Design system analysis
- ✅ User requirements documentation
- ✅ Technical architecture definition
- ⏳ Backend API specification
- ⏳ Component structure design

### Phase 2: Backend Implementation
- Create `/api/v1/dashboard/recent-activity` endpoint
- Implement activity aggregation logic
- Add transaction date queries for all entity types
- Write API tests

### Phase 3: Frontend Foundation
- Create dashboard component structure
- Implement `useDashboardData` hook
- Build base components (ActivityItem, ActivitySection)
- Set up routing and navigation

### Phase 4: Visual Polish
- Implement ProjectSpotlight component
- Add responsive layout logic
- Apply design tokens consistently
- Add loading states and error handling

### Phase 5: Integration & Testing
- Integrate with existing navigation
- Add unit tests for components
- Add integration tests for user flows
- Performance optimization

### Phase 6: Validation
- Accessibility audit
- Cross-browser testing
- User acceptance testing
- Performance validation

## Open Questions

1. **Activity Retention:** How far back should we show activity? (Suggestion: 30 days)
2. **Empty States:** What should we show for users with no activity? (Suggestion: Onboarding prompt)
3. **Real-time Updates:** Should we implement real-time updates? (Suggestion: No, manual refresh is sufficient)
4. **Activity Filtering:** Should users be able to filter by entity type? (Suggestion: Not in MVP)

## Next Steps

1. **Immediate:** Get approval on design direction and API specification
2. **Backend:** Begin implementation of `/api/v1/dashboard/recent-activity` endpoint
3. **Frontend:** Create component structure and base components
4. **Design:** Create detailed mockups for each breakpoint

---

**Analysis Complete.** Ready to proceed to planning phase.
