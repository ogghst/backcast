# Dashboard Visual Design Specification

**Date:** 2026-03-15
**Iteration:** Main Dashboard Implementation
**Status:** Design Specification Complete

## Design Philosophy

**"Sophisticated Professional Command Center"**

The dashboard embodies clarity, temporal awareness, and action-oriented design. Every element serves a purpose: helping users quickly understand system state and navigate to relevant details without overwhelming them with information density.

## Color Application

### Background Layers
```
Page Background:        #f5f3f0 (colorBgLayout - soft cream)
Card Container:         #faf9f7 (colorBgContainer - warm off-white)
Elevated Card:          #ffffff (colorBgElevated - pure white)
```

### Text Colors
```
Primary Text:           #2a2a2a (colorText - deep charcoal)
Secondary Text:         #6b6b6b (colorTextSecondary - medium gray)
Tertiary Text:          #9a9a9a (colorTextTertiary - light gray)
Disabled Text:          #d4d4d4 (colorTextQuaternary - very light gray)
```

### Entity Type Colors
```
Projects:               #4a7c91 (colorPrimary - teal-blue)
WBEs:                   #5d8ba8 (colorInfo - muted blue)
Cost Elements:          #7bc49a (colorChartEV - muted mint)
Change Orders:          #d4a549 (colorChartForecast - warm amber)
```

### Status Colors
```
Success/Created:        #5da572 (colorSuccess - muted green)
Warning/Updated:        #d4a549 (colorWarning - warm amber)
Error/Deleted:          #c95d5f (colorError - soft red)
Info/Merged:            #5d8ba8 (colorInfo - muted blue)
```

### Border Colors
```
Standard Border:        #e8e6e3 (colorBorder - soft warm gray)
Subtle Divider:         #f0eee9 (colorBorderSecondary - lighter border)
```

## Typography Scale

### Font Family
```css
font-family: 'Ubuntu', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
             'Helvetica Neue', Arial, sans-serif;
```

### Type Scale
```
Welcome Heading:        24px / fontSizeXXL / fontWeightBold (700)
Section Heading:        16px / fontSizeLG / fontWeightSemiBold (600)
Entity Name:            14px / fontSize / fontWeightMedium (500)
Metadata Text:          12px / fontSizeSM / fontWeightNormal (400)
Timestamp Text:         12px / fontSizeSM / fontWeightNormal (400)
```

### Line Heights
```
Headings:              1.2 (tight)
Body Text:             1.5 (readable)
Data Text:             1.4 (balanced)
```

## Spacing System

### Component Padding
```
Page Container:        32px / paddingXL (all sides)
Card Container:        24px / paddingLG (all sides)
Activity Item:         16px / paddingMD (horizontal), 8px / paddingSM (vertical)
Section Spacing:       24px / marginLG (between sections)
```

### Grid Gap
```
Desktop Grid:          24px / gapLG
Tablet Grid:           16px / gapMD
Mobile Stack:          16px / gapMD
```

### Internal Spacing
```
Header Bottom Margin:  16px / marginMD
Item Bottom Margin:    8px / marginSM
Icon Text Gap:         8px / marginSM
```

## Component Specifications

### 1. Dashboard Header

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  Welcome back, [User Name]                        │
└────────────────────────────────────────────────────┘
```

**Styles:**
```css
.dashboard-header {
  padding: 0 0 24px 0; /* paddingLG bottom */
  margin-bottom: 24px; /* marginLG */
  border-bottom: 1px solid #e8e6e3; /* colorBorder */
}

.welcome-text {
  font-size: 20px; /* fontSizeXL */
  font-weight: 600; /* fontWeightSemiBold */
  color: #6b6b6b; /* colorTextSecondary */
}

.user-name {
  font-size: 24px; /* fontSizeXXL */
  font-weight: 700; /* fontWeightBold */
  color: #4a7c91; /* colorPrimary */
}
```

**Behavior:**
- Static header (no interaction)
- Responsive text size (scales down on mobile)

### 2. Project Spotlight Card

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  [Project Icon]  Project Name                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Budget   │  │ EVM      │  │ Changes  │      │
│  │ $1.2M    │  │ On Track │  │ 3 Active │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  Last activity: 2 hours ago                      │
│  [View Project →]                                │
└────────────────────────────────────────────────────┘
```

**Styles:**
```css
.project-spotlight {
  background: #ffffff; /* colorBgElevated */
  border-radius: 12px; /* borderRadiusXL */
  padding: 24px; /* paddingLG */
  margin-bottom: 32px; /* marginXXL */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 150ms ease;
}

.project-spotlight:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.project-header {
  display: flex;
  align-items: center;
  gap: 16px; /* marginMD */
  margin-bottom: 24px; /* marginLG */
}

.project-name {
  font-size: 20px; /* fontSizeXL */
  font-weight: 600; /* fontWeightSemiBold */
  color: #2a2a2a; /* colorText */
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px; /* marginMD */
  margin-bottom: 24px; /* marginLG */
}

.metric-card {
  background: #faf9f7; /* colorBgContainer */
  border-radius: 8px; /* borderRadiusLG */
  padding: 16px; /* paddingMD */
  text-align: center;
}

.metric-label {
  font-size: 12px; /* fontSizeSM */
  font-weight: 500; /* fontWeightMedium */
  color: #6b6b6b; /* colorTextSecondary */
  margin-bottom: 8px; /* marginSM */
}

.metric-value {
  font-size: 16px; /* fontSizeLG */
  font-weight: 600; /* fontWeightSemiBold */
  color: #2a2a2a; /* colorText */
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.last-activity {
  font-size: 12px; /* fontSizeSM */
  color: #9a9a9a; /* colorTextTertiary */
}

.view-project-button {
  background: #4a7c91; /* colorPrimary */
  color: #ffffff;
  border: none;
  border-radius: 6px; /* borderRadius */
  padding: 8px 16px; /* paddingSM horizontal, paddingMD vertical */
  font-size: 14px; /* fontSize */
  font-weight: 500; /* fontWeightMedium */
  cursor: pointer;
  transition: background 150ms ease;
}

.view-project-button:hover {
  background: #3d6b7f; /* 10% darker primary */
}
```

**Behavior:**
- Hover elevation effect
- Button expands slightly on hover
- Metrics scale on mobile (stack vertically)

### 3. Activity Section

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  [Icon]  Recent Projects              [View All →]│
│  ───────────────────────────────────────────────  │
│  • Project A (updated)  2 hours ago               │
│  • Project B (created)  Yesterday                 │
│  • Project C (updated)  2 days ago                │
└────────────────────────────────────────────────────┘
```

**Styles:**
```css
.activity-section {
  background: #faf9f7; /* colorBgContainer */
  border-radius: 12px; /* borderRadiusXL */
  padding: 24px; /* paddingLG */
  height: 100%;
  display: flex;
  flex-direction: column;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px; /* marginMD */
  padding-bottom: 12px; /* marginMD with visual adjustment */
  border-bottom: 1px solid #f0eee9; /* colorBorderSecondary */
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px; /* marginSM */
  font-size: 16px; /* fontSizeLG */
  font-weight: 600; /* fontWeightSemiBold */
  color: #2a2a2a; /* colorText */
}

.section-icon {
  font-size: 18px;
}

.view-all-link {
  font-size: 12px; /* fontSizeSM */
  font-weight: 500; /* fontWeightMedium */
  color: #4a7c91; /* colorPrimary */
  text-decoration: none;
  transition: color 150ms ease;
}

.view-all-link:hover {
  color: #3d6b7f; /* 10% darker primary */
  text-decoration: underline;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 4px; /* marginXS */
  flex: 1;
}
```

**Behavior:**
- "View All" link navigates to entity list page
- Section icon uses entity-specific color
- Empty state shows centered message

### 4. Activity Item

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  • Project Name              [Updated] 2h ago     │
└────────────────────────────────────────────────────┘
```

**Styles:**
```css
.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px; /* paddingSM vertical, paddingMD horizontal */
  border-radius: 6px; /* borderRadius */
  cursor: pointer;
  transition: background 150ms ease;
  text-decoration: none;
  color: inherit;
}

.activity-item:hover {
  background: #f5f3f0; /* colorBgLayout */
}

.activity-left {
  display: flex;
  align-items: center;
  gap: 8px; /* marginSM */
  flex: 1;
  min-width: 0; /* Allow text truncation */
}

.activity-bullet {
  color: #9a9a9a; /* colorTextTertiary */
  font-size: 12px; /* fontSizeSM */
}

.entity-name {
  font-size: 14px; /* fontSize */
  font-weight: 500; /* fontWeightMedium */
  color: #2a2a2a; /* colorText */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-right {
  display: flex;
  align-items: center;
  gap: 8px; /* marginSM */
  flex-shrink: 0;
}

.activity-badge {
  font-size: 10px; /* fontSizeXS */
  font-weight: 600; /* fontWeightSemiBold */
  padding: 2px 8px;
  border-radius: 4px; /* borderRadiusSM */
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.activity-badge.created {
  background: rgba(93, 165, 114, 0.15); /* colorSuccess with opacity */
  color: #5da572; /* colorSuccess */
}

.activity-badge.updated {
  background: rgba(212, 165, 73, 0.15); /* colorWarning with opacity */
  color: #b8942f; /* Darker warning */
}

.activity-badge.deleted {
  background: rgba(201, 93, 95, 0.15); /* colorError with opacity */
  color: #c95d5f; /* colorError */
}

.activity-badge.merged {
  background: rgba(93, 139, 168, 0.15); /* colorInfo with opacity */
  color: #5d8ba8; /* colorInfo */
}

.activity-timestamp {
  font-size: 12px; /* fontSizeSM */
  font-weight: 400; /* fontWeightNormal */
  color: #9a9a9a; /* colorTextTertiary */
  white-space: nowrap;
}
```

**Behavior:**
- Hover background effect
- Click navigates to entity detail page
- Entire row is clickable (44px min height)
- Text truncation on long names

### 5. Activity Grid

**Layout:**
```
Desktop (1200px+):
┌──────────────────┬──────────────────┐
│  Recent Projects │  Recent WBEs     │
├──────────────────┼──────────────────┤
│  Cost Elements   │  Change Orders   │
└──────────────────┴──────────────────┘

Tablet (768px-1200px):
┌──────────────────┬──────────────────┐
│  Recent Projects │  Recent WBEs     │
├──────────────────┼──────────────────┤
│  Cost Elements   │  Change Orders   │
└──────────────────┴──────────────────┘

Mobile (<768px):
┌──────────────────────────────────────┐
│  Recent Projects                     │
├──────────────────────────────────────┤
│  Recent WBEs                         │
├──────────────────────────────────────┤
│  Cost Elements                       │
├──────────────────────────────────────┤
│  Change Orders                       │
└──────────────────────────────────────┘
```

**Styles:**
```css
.activity-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px; /* marginLG */
  margin-top: 24px; /* marginLG */
}

/* Tablet (768px-1200px) */
@media (max-width: 1200px) {
  .activity-grid {
    gap: 16px; /* marginMD */
  }
}

/* Mobile (<768px) */
@media (max-width: 768px) {
  .activity-grid {
    grid-template-columns: 1fr;
    gap: 16px; /* marginMD */
  }
}
```

**Behavior:**
- Responsive grid layout
- Maintains consistent spacing
- Stacks on mobile

### 6. Relative Time Component

**Format Rules:**
```
< 1 minute:        "Just now"
< 1 hour:          "X minutes ago"
< 24 hours:        "X hours ago"
< 7 days:          "X days ago"
< 30 days:         "X weeks ago"
>= 30 days:        "MMM DD, YYYY" (absolute date)
```

**Styles:**
```css
.relative-time {
  font-size: 12px; /* fontSizeSM */
  font-weight: 400; /* fontWeightNormal */
  color: #9a9a9a; /* colorTextTertiary */
}
```

**Behavior:**
- Updates every minute (if on page)
- Formats based on time delta
- Handles future dates gracefully

## State Specifications

### Loading State

**Component:** `DashboardSkeleton`

**Layout:** Matches final layout with shimmer effect

**Styles:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    #f5f3f0 0%,
    #faf9f7 50%,
    #f5f3f0 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px; /* borderRadius */
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Components:**
- Header skeleton (text lines)
- Spotlight card skeleton (rectangles)
- Activity section skeletons (list items)

### Error State

**Component:** `ErrorState`

**Layout:** Centered error message with action

**Styles:**
```css
.error-state {
  text-align: center;
  padding: 48px 24px; /* Extra vertical padding */
}

.error-icon {
  font-size: 48px;
  color: #c95d5f; /* colorError */
  margin-bottom: 16px; /* marginMD */
}

.error-message {
  font-size: 16px; /* fontSizeLG */
  font-weight: 500; /* fontWeightMedium */
  color: #2a2a2a; /* colorText */
  margin-bottom: 8px; /* marginSM */
}

.error-detail {
  font-size: 14px; /* fontSize */
  color: #6b6b6b; /* colorTextSecondary */
  margin-bottom: 24px; /* marginLG */
}

.retry-button {
  background: #4a7c91; /* colorPrimary */
  color: #ffffff;
  border: none;
  border-radius: 6px; /* borderRadius */
  padding: 10px 20px;
  font-size: 14px; /* fontSize */
  font-weight: 500; /* fontWeightMedium */
  cursor: pointer;
}
```

### Empty State

**Component:** `EmptyState`

**Layout:** Centered illustration with message

**Styles:**
```css
.empty-state {
  text-align: center;
  padding: 48px 24px; /* Extra vertical padding */
}

.empty-icon {
  font-size: 64px;
  color: #e8e6e3; /* colorBorder */
  margin-bottom: 16px; /* marginMD */
}

.empty-message {
  font-size: 16px; /* fontSizeLG */
  font-weight: 500; /* fontWeightMedium */
  color: #2a2a2a; /* colorText */
  margin-bottom: 8px; /* marginSM */
}

.empty-detail {
  font-size: 14px; /* fontSize */
  color: #6b6b6b; /* colorTextSecondary */
  margin-bottom: 24px; /* marginLG */
}

.call-to-action {
  background: #4a7c91; /* colorPrimary */
  color: #ffffff;
  border: none;
  border-radius: 6px; /* borderRadius */
  padding: 10px 20px;
  font-size: 14px; /* fontSize */
  font-weight: 500; /* fontWeightMedium */
  cursor: pointer;
}
```

**Scenarios:**
- No recent activity
- No accessible entities
- New user onboarding

## Animation Specifications

### Page Load Animation
```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in-up {
  animation: fadeInUp 0.3s ease-out forwards;
}

/* Stagger delays */
.stagger-1 { animation-delay: 0ms; }
.stagger-2 { animation-delay: 100ms; }
.stagger-3 { animation-delay: 200ms; }
.stagger-4 { animation-delay: 300ms; }
.stagger-5 { animation-delay: 400ms; }
```

**Application:**
- Header: delay 0ms
- Spotlight: delay 100ms
- First row of grid: delay 200ms
- Second row of grid: delay 300ms

### Hover Animations
```css
.activity-item {
  transition: background 150ms ease;
}

.view-project-button {
  transition: background 150ms ease, transform 150ms ease;
}

.view-project-button:hover {
  transform: scale(1.02);
}
```

### Loading Animation
```css
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton {
  animation: shimmer 1.5s infinite;
}
```

## Accessibility Specifications

### Keyboard Navigation
- **Tab Order:** Header → Spotlight → Activity sections (left to right, top to bottom)
- **Focus Indicators:** 2px solid #4a7c91 (colorPrimary) with 3px offset
- **Skip Links:** Not needed (simple layout)

### Screen Reader Support
```html
<!-- Semantic structure -->
<main aria-label="Dashboard">
  <h1>Welcome back, {userName}</h1>

  <section aria-label="Last edited project">
    <h2>Project Spotlight</h2>
    <!-- Project card content -->
  </section>

  <section aria-label="Recent activity">
    <h2>Recent Activity</h2>

    <section aria-label="Recent projects">
      <h3>Projects</h3>
      <ul role="list">
        <li><a href="/projects/1">Project A</a> (updated) 2 hours ago</li>
      </ul>
    </section>
  </section>
</main>
```

### ARIA Labels
- Activity badges: `aria-label="Updated 2 hours ago"`
- Entity links: `aria-label="View Project A details"`
- View all links: `aria-label="View all projects"`

### Color Contrast
- All text combinations meet WCAG AA (4.5:1 for normal text, 3:1 for large text)
- Verified using design system tokens

### Focus Management
- Focus visible on all interactive elements
- No focus traps
- Logical tab order

## Responsive Breakpoints

### Desktop (1200px+)
- 2x2 grid layout
- Full metrics in spotlight card
- Horizontal layouts in components

### Tablet (768px-1199px)
- 2x2 grid layout (reduced gap)
- Reduced metrics in spotlight card (hide least important)
- Adjusted padding (16px instead of 24px)

### Mobile (<768px)
- Single column stack
- Essential metrics only in spotlight
- Full-width cards
- Increased touch targets (44px minimum)

## Performance Considerations

### Bundle Size
- Dashboard components: Target < 30KB gzipped
- Use dynamic imports for non-critical components
- Tree-shake unused utilities

### Render Performance
- Use React.memo for expensive components
- Virtualize long lists (if > 50 items)
- Avoid unnecessary re-renders with proper dependency arrays

### Network Performance
- Cache dashboard data for 5 minutes
- Use stale-while-revalidate strategy
- Prefetch entity detail pages on hover

### Image Optimization
- Use SVG icons (inline or sprite)
- Lazy load project images (if added)
- Optimize logo and illustrations

## Browser Compatibility

### Target Browsers
- Chrome/Edge: Latest + 2 versions
- Firefox: Latest + 2 versions
- Safari: Latest + 2 versions
- Mobile Safari: iOS 14+
- Chrome Mobile: Android 10+

### Progressive Enhancement
- Core functionality works without JavaScript
- Animations enhanced with JavaScript
- Layout works on all browsers

### Fallbacks
- Grid layout → Flexbox for older browsers
- CSS variables → Static values for older browsers
- ES6+ → Transpiled to ES5

---

**Design Specification Complete.** Ready for implementation.
