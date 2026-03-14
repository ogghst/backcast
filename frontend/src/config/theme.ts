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

export const theme: ThemeConfig & { token: CustomTokenConfig } = {
  token: {
    // === Existing Tokens ===
    colorPrimary: "#1677ff",
    borderRadius: 6,
    fontFamily:
      'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',

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

    // === Status Colors ===
    colorSuccess: "#52c41a",
    colorWarning: "#faad14",
    colorError: "#ff4d4f",
    colorInfo: "#1677ff",

    // === Semantic Colors ===
    colorTextSecondary: "#8c8c8c",
    colorTextTertiary: "#bfbfbf",
    colorBorderSecondary: "#d9d9d9",

    // === Chart Colors ===
    // Used for EVM and other data visualizations
    colorChartPV: "#5b8ff9", // Blue - Planned Value
    colorChartEV: "#5ad8a6", // Green - Earned Value
    colorChartAC: "#5d7092", // Gray - Actual Cost
    colorChartForecast: "#faad14", // Orange - Forecast
    colorChartActual: "#ff4d4f", // Red - Actual

    // === Border Radius Variants ===
    borderRadiusSM: 4,
    borderRadiusLG: 8,
    borderRadiusXL: 12,
  },
};
