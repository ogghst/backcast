import { ThemeConfig } from "antd";

/**
 * Design Token System
 *
 * This configuration extends Ant Design's theme with a comprehensive set of design tokens.
 * These tokens serve as the single source of truth for styling across the application.
 *
 * ## Usage in Components
 *
 * ```tsx
 * import { theme } from 'antd';
 *
 * function MyComponent() {
 *   const { token } = theme.useToken();
 *
 *   return (
 *     <div style={{
 *       padding: token.marginLG,
 *       fontSize: token.fontSizeLG,
 *       color: token.colorTextSecondary,
 *       borderRadius: token.borderRadiusLG
 *     }}>
 *       Content
 *     </div>
 *   );
 * }
 * ```
 *
 * ## Token Categories
 *
 * ### Spacing
 * - `marginXS` (4px), `marginSM` (8px), `marginMD` (16px), `marginLG` (24px), `marginXL` (32px), `marginXXL` (40px)
 * - `paddingXS` (4px), `paddingSM` (8px), `paddingMD` (16px), `paddingLG` (24px), `paddingXL` (32px)
 *
 * ### Typography
 * - `fontSizeXS` (10px) - Small labels, badges
 * - `fontSizeSM` (12px) - Secondary text, captions
 * - `fontSize` (14px) - Body text (default)
 * - `fontSizeLG` (16px) - Subheadings
 * - `fontSizeXL` (20px) - Headings
 * - `fontSizeXXL` (24px) - Large headings
 * - `fontWeightNormal` (400), `fontWeightMedium` (500), `fontWeightSemiBold` (600), `fontWeightBold` (700)
 *
 * ### Colors
 * - Status: `colorSuccess`, `colorWarning`, `colorError`, `colorInfo`
 * - Semantic: `colorTextSecondary`, `colorTextTertiary`, `colorBorderSecondary`
 * - Chart: `colorChartPV`, `colorChartEV`, `colorChartAC`, `colorChartForecast`, `colorChartActual`
 *
 * ### Border Radius
 * - `borderRadiusSM` (4px), `borderRadius` (6px), `borderRadiusLG` (8px), `borderRadiusXL` (12px)
 *
 * ## Migration Guide
 *
 * When updating existing components:
 * 1. Replace hardcoded colors with semantic tokens (e.g., `#52c41a` → `token.colorSuccess`)
 * 2. Replace magic spacing numbers with spacing tokens (e.g., `padding: 16` → `padding: token.paddingMD`)
 * 3. Replace arbitrary font sizes with typography scale (e.g., `fontSize: 12` → `fontSize: token.fontSizeSM`)
 */
// Custom token type that extends Ant Design's default token configuration
type CustomTokenConfig = {
  colorPrimary?: string;
  borderRadius?: number;
  fontFamily?: string;
  marginXS?: number;
  marginSM?: number;
  marginMD?: number;
  marginLG?: number;
  marginXL?: number;
  marginXXL?: number;
  paddingXS?: number;
  paddingSM?: number;
  paddingMD?: number;
  paddingLG?: number;
  paddingXL?: number;
  fontSizeXS?: number;
  fontSizeSM?: number;
  fontSize?: number;
  fontSizeLG?: number;
  fontSizeXL?: number;
  fontSizeXXL?: number;
  fontWeightNormal?: number;
  fontWeightMedium?: number;
  fontWeightSemiBold?: number;
  fontWeightBold?: number;
  colorSuccess?: string;
  colorWarning?: string;
  colorError?: string;
  colorInfo?: string;
  colorTextSecondary?: string;
  colorTextTertiary?: string;
  colorBorderSecondary?: string;
  colorChartPV?: string;
  colorChartEV?: string;
  colorChartAC?: string;
  colorChartForecast?: string;
  colorChartActual?: string;
  borderRadiusSM?: number;
  borderRadiusLG?: number;
  borderRadiusXL?: number;
};

// Dark mode token overrides
type DarkModeTokens = {
  colorBgContainer?: string;
  colorBgElevated?: string;
  colorBgLayout?: string;
  colorText?: string;
  colorTextSecondary?: string;
  colorTextTertiary?: string;
  colorTextQuaternary?: string;
  colorBorder?: string;
  colorBorderSecondary?: string;
  colorSuccess?: string;
  colorWarning?: string;
  colorError?: string;
  colorInfo?: string;
  colorChartPV?: string;
  colorChartEV?: string;
  colorChartAC?: string;
  colorChartForecast?: string;
  colorChartActual?: string;
};

/**
 * Soft Light Color Scheme
 *
 * A refined, polished palette with soft backgrounds and easy-to-read typography.
 * Designed for comfort and clarity in extended use sessions.
 *
 * Color Philosophy:
 * - Warm undertones for reduced eye strain
 * - High contrast ratios (WCAG AA compliant)
 * - Sophisticated accent colors that guide attention
 * - Harmonious relationships between elements
 */
export const theme: ThemeConfig & { token: CustomTokenConfig; darkModeTokens?: DarkModeTokens } = {
  token: {
    // === Brand & Typography ===
    colorPrimary: "#4a7c91", // Soft teal-blue - sophisticated primary
    borderRadius: 8,
    fontFamily:
      'Ubuntu, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',

    // === Background Colors (Soft Light) ===
    colorBgContainer: "#faf9f7", // Warm off-white for cards/containers
    colorBgElevated: "#ffffff", // Pure white for elevated elements
    colorBgLayout: "#f5f3f0", // Soft cream for layout background

    // === Text Colors (High Contrast) ===
    colorText: "#2a2a2a", // Deep charcoal for primary text
    colorTextSecondary: "#6b6b6b", // Medium gray for secondary text
    colorTextTertiary: "#9a9a9a", // Light gray for tertiary text
    colorTextQuaternary: "#d4d4d4", // Very light gray for disabled text

    // === Border Colors (Subtle) ===
    colorBorder: "#e8e6e3", // Soft warm gray
    colorBorderSecondary: "#f0eee9", // Lighter border for subtle separation

    // === Spacing Scale ===
    marginXS: 4,
    marginSM: 8,
    marginMD: 16,
    marginLG: 24,
    marginXL: 32,
    marginXXL: 40,

    paddingXS: 4,
    paddingSM: 8,
    paddingMD: 16,
    paddingLG: 24,
    paddingXL: 32,

    // === Typography Scale ===
    fontSizeXS: 10, // Small labels, badges
    fontSizeSM: 12, // Secondary text, captions
    fontSize: 14, // Body text (Ant Design default)
    fontSizeLG: 16, // Subheadings
    fontSizeXL: 20, // Headings
    fontSizeXXL: 24, // Large headings

    fontWeightNormal: 400,
    fontWeightMedium: 500,
    fontWeightSemiBold: 600,
    fontWeightBold: 700,

    // === Status Colors (Softened) ===
    colorSuccess: "#5da572", // Muted green
    colorWarning: "#d4a549", // Warm amber
    colorError: "#c95d5f", // Soft red
    colorInfo: "#5d8ba8", // Muted blue

    // === Chart Colors (Refined) ===
    // Used for EVM and other data visualizations
    colorChartPV: "#6b9ac4", // Soft blue - Planned Value
    colorChartEV: "#7bc49a", // Muted mint - Earned Value
    colorChartAC: "#8b7b94", // Soft lavender-gray - Actual Cost
    colorChartForecast: "#d4a549", // Warm amber - Forecast
    colorChartActual: "#c95d5f", // Soft red - Actual

    // === Border Radius Variants ===
    borderRadiusSM: 4,
    borderRadiusLG: 12,
    borderRadiusXL: 16,
  },
  /**
   * Dark Mode Tokens
   *
   * These tokens override the light mode values when dark mode is enabled.
   * Applied via the ConfigProvider's darkAlgorithm combined with these overrides.
   *
   * Color Philosophy for Dark Mode:
   * - Backgrounds: Deep grays (#141414 - #262626) instead of pure black for reduced eye strain
   * - Text: High contrast light grays (#e8e8e8) meeting WCAG AA standards
   * - Borders: Subtle medium grays (#404040) for visible but not distracting separation
   * - Status Colors: Brighter versions of light mode colors to maintain visibility on dark backgrounds
   * - Chart Colors: Same as light mode - designed to work on both backgrounds
   */
  darkModeTokens: {
    // === Background Colors (Dark) ===
    colorBgContainer: "#1f1f1f", // Dark gray for cards/containers
    colorBgElevated: "#262626", // Elevated dark
    colorBgLayout: "#141414", // Nearly black for layout

    // === Text Colors (Inverted for dark) ===
    colorText: "#e8e8e8", // Light gray for primary text
    colorTextSecondary: "#a6a6a6", // Muted light gray
    colorTextTertiary: "#737373", // Even more muted
    colorTextQuaternary: "#525252", // Very muted (disabled)

    // === Border Colors (Dark) ===
    colorBorder: "#404040", // Medium gray border
    colorBorderSecondary: "#262626", // Darker border

    // === Status Colors (Adjusted for dark backgrounds) ===
    colorSuccess: "#73d13d", // Brighter green for visibility
    colorWarning: "#ffc53d", // Brighter amber
    colorError: "#ff7875", // Brighter red
    colorInfo: "#69b1ff", // Brighter blue

    // === Chart Colors (Slightly adjusted for dark mode) ===
    // Same as light mode - these work on both backgrounds
    colorChartPV: "#6b9ac4", // Soft blue - Planned Value
    colorChartEV: "#7bc49a", // Muted mint - Earned Value
    colorChartAC: "#8b7b94", // Soft lavender-gray - Actual Cost
    colorChartForecast: "#d4a549", // Warm amber - Forecast
    colorChartActual: "#c95d5f", // Soft red - Actual
  },
};
