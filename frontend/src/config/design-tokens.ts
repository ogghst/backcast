/**
 * Design Token Constants
 *
 * This file contains style constants for patterns that cannot directly use
 * Ant Design theme tokens (e.g., in utility functions, non-React contexts, or
 * during gradual migration from inline styles).
 *
 * ## Usage Guidelines
 *
 * **Prefer theme tokens** in React components:
 * ```tsx
 * import { theme } from 'antd';
 * const { token } = theme.useToken();
 * const style = { padding: token.paddingMD };
 * ```
 *
 * **Use constants from this file** when:
 * - Working in non-React contexts (utilities, helpers)
 * - Creating reusable style objects
 * - Gradually migrating from hardcoded values
 * - Need for TypeScript const assertions
 *
 * ## Token Categories
 *
 * ### Spacing
 * Use for consistent margins and padding throughout the app.
 * Follows a 4px base scale: 4, 8, 16, 24, 32, 40, 48
 *
 * ### Font Sizes
 * Use for consistent typography scaling.
 * Matches the theme.ts fontSize tokens.
 *
 * ### Style Presets
 * Pre-defined style objects for common patterns.
 * Use these to reduce repetition in inline styles.
 */

// ============================================================================
// SPACING
// ============================================================================

/**
 * Spacing scale in pixels.
 * Based on a 4px grid system for consistent spacing.
 *
 * @example
 * ```tsx
 * <div style={{ padding: SPACING.MD }}>Content</div>
 * ```
 */
export const SPACING = {
  /** 4px - Extra small spacing */
  XS: 4,
  /** 8px - Small spacing */
  SM: 8,
  /** 16px - Medium spacing (default) */
  MD: 16,
  /** 24px - Large spacing */
  LG: 24,
  /** 32px - Extra large spacing */
  XL: 32,
  /** 40px - Extra extra large spacing */
  XXL: 40,
  /** 48px - Huge spacing */
  HUGE: 48,
} as const;

// ============================================================================
// TYPOGRAPHY
// ============================================================================

/**
 * Font size scale in pixels.
 * Matches the theme.ts fontSize tokens for consistency.
 *
 * @example
 * ```tsx
 * <span style={{ fontSize: FONT_SIZES.SM }}>Small text</span>
 * ```
 */
export const FONT_SIZES = {
  /** 10px - Extra small (labels, badges) */
  XS: 10,
  /** 12px - Small (secondary text, captions) */
  SM: 12,
  /** 14px - Medium (body text, default) */
  MD: 14,
  /** 16px - Large (subheadings) */
  LG: 16,
  /** 20px - Extra large (headings) */
  XL: 20,
  /** 24px - Extra extra large (large headings) */
  XXL: 24,
} as const;

/**
 * Font weight values.
 *
 * @example
 * ```tsx
 * <h3 style={{ fontWeight: FONT_WEIGHT.SEMIBOLD }}>Heading</h3>
 * ```
 */
export const FONT_WEIGHT = {
  /** 400 - Normal */
  NORMAL: 400,
  /** 500 - Medium */
  MEDIUM: 500,
  /** 600 - Semi Bold */
  SEMIBOLD: 600,
  /** 700 - Bold */
  BOLD: 700,
} as const;

// ============================================================================
// BORDER RADIUS
// ============================================================================

/**
 * Border radius scale in pixels.
 * Matches the theme.ts borderRadius tokens.
 *
 * @example
 * ```tsx
 * <div style={{ borderRadius: BORDER_RADIUS.LG }}>Rounded</div>
 * ```
 */
export const BORDER_RADIUS = {
  /** 4px - Small radius */
  SM: 4,
  /** 6px - Medium radius (default) */
  MD: 6,
  /** 8px - Large radius */
  LG: 8,
  /** 12px - Extra large radius */
  XL: 12,
} as const;

// ============================================================================
// COLORS
// ============================================================================

/**
 * Common color values for non-React contexts.
 * These match the theme.ts color tokens.
 *
 * **Note:** In React components, prefer using theme tokens:
 * ```tsx
 * const { token } = theme.useToken();
 * const color = token.colorSuccess;
 * ```
 *
 * @example
 * ```tsx
 * // In utility functions or config objects
 * const config = { color: COLORS.SUCCESS };
 * ```
 */
export const COLORS = {
  /** #1677ff - Primary brand color */
  PRIMARY: "#1677ff",
  /** #52c41a - Success state */
  SUCCESS: "#52c41a",
  /** #faad14 - Warning state */
  WARNING: "#faad14",
  /** #ff4d4f - Error state */
  ERROR: "#ff4d4f",
  /** #1677ff - Info state */
  INFO: "#1677ff",

  /** #8c8c8c - Secondary text */
  TEXT_SECONDARY: "#8c8c8c",
  /** #bfbfbf - Tertiary text */
  TEXT_TERTIARY: "#bfbfbf",

  /** #d9d9d9 - Secondary border */
  BORDER_SECONDARY: "#d9d9d9",

  /** #5b8ff9 - Chart: Planned Value (Blue) */
  CHART_PV: "#5b8ff9",
  /** #5ad8a6 - Chart: Earned Value (Green) */
  CHART_EV: "#5ad8a6",
  /** #5d7092 - Chart: Actual Cost (Gray) */
  CHART_AC: "#5d7092",
  /** #faad14 - Chart: Forecast (Orange) */
  CHART_FORECAST: "#faad14",
  /** #ff4d4f - Chart: Actual (Red) */
  CHART_ACTUAL: "#ff4d4f",
} as const;

// ============================================================================
// STYLE PRESETS
// ============================================================================

/**
 * Common style object presets for reusable patterns.
 * Use these to reduce repetition in inline styles.
 *
 * @example
 * ```tsx
 * <div style={CARD_STYLES}>Card content</div>
 * ```
 */

/**
 * Standard card container styling.
 * Provides consistent spacing for card components.
 */
export const CARD_STYLES = {
  marginBottom: SPACING.MD,
  padding: SPACING.LG,
} as const;

/**
 * Horizontal flex layout with consistent gap.
 *
 * @example
 * ```tsx
 * <div style={FLEX_ROW}>
 *   <span>Item 1</span>
 *   <span>Item 2</span>
 * </div>
 * ```
 */
export const FLEX_ROW = {
  display: "flex",
  gap: SPACING.MD,
} as const;

/**
 * Vertical flex layout with consistent gap.
 *
 * @example
 * ```tsx
 * <div style={FLEX_COLUMN}>
 *   <div>Row 1</div>
 *   <div>Row 2</div>
 * </div>
 * ```
 */
export const FLEX_COLUMN = {
  display: "flex",
  flexDirection: "column",
  gap: SPACING.MD,
} as const;

/**
 * Center content (horizontally and vertically).
 *
 * @example
 * ```tsx
 * <div style={CENTER}>Centered content</div>
 * ```
 */
export const CENTER = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
} as const;

/**
 * Full width and height.
 * Useful for containers that should fill their parent.
 *
 * @example
 * ```tsx
 * <div style={FULL_SIZE}>Full size container</div>
 * ```
 */
export const FULL_SIZE = {
  width: "100%",
  height: "100%",
} as const;

// ============================================================================
// TYPE EXPORTS
// ============================================================================

/**
 * Spacing values type.
 */
export type SpacingValue = (typeof SPACING)[keyof typeof SPACING];

/**
 * Font size values type.
 */
export type FontSizeValue = (typeof FONT_SIZES)[keyof typeof FONT_SIZES];

/**
 * Font weight values type.
 */
export type FontWeightValue = (typeof FONT_WEIGHT)[keyof typeof FONT_WEIGHT];

/**
 * Border radius values type.
 */
export type BorderRadiusValue = (typeof BORDER_RADIUS)[keyof typeof BORDER_RADIUS];
