/**
 * useThemeTokens Hook
 *
 * Provides a structured, categorized way to access design tokens from Ant Design's theme.
 * This hook wraps `theme.useToken()` and organizes tokens into logical groups:
 * spacing, typography, colors, and border radius.
 *
 * ## Usage
 *
 * ```tsx
 * import { useThemeTokens } from '@/hooks/useThemeTokens';
 *
 * function MyComponent() {
 *   const { spacing, typography, colors, borderRadius } = useThemeTokens();
 *
 *   return (
 *     <div style={{
 *       padding: spacing.md,
 *       fontSize: typography.lg,
 *       color: colors.textSecondary,
 *       borderRadius: borderRadius.lg
 *     }}>
 *       Content
 *     </div>
 *   );
 * }
 * ```
 *
 * ## Why Use This Hook?
 *
 * - **Better DX**: Intellisense-friendly with categorized tokens
 * - **Consistency**: Encourages using semantic token names
 * - **Type Safety**: Full TypeScript support with proper types
 * - **Migration Helper**: Makes it easier to migrate from hardcoded values
 *
 * ## Token Categories
 *
 * ### Spacing
 * - `xs`: 4px, `sm`: 8px, `md`: 16px, `lg`: 24px, `xl`: 32px, `xxl`: 40px
 *
 * ### Typography
 * - Font sizes: `xs`: 10px, `sm`: 12px, `md`: 14px, `lg`: 16px, `xl`: 20px, `xxl`: 24px
 * - Font weights: `normal`: 400, `medium`: 500, `semiBold`: 600, `bold`: 700
 *
 * ### Colors
 * - Status: `primary`, `success`, `warning`, `error`, `info`
 * - Semantic: `text`, `textSecondary`, `textTertiary`, `border`, `borderSecondary`
 * - Chart: `chartPV`, `chartEV`, `chartAC`, `chartForecast`, `chartActual`
 *
 * ### Border Radius
 * - `sm`: 4px, `md`: 6px, `lg`: 8px, `xl`: 12px
 */

import { theme } from "antd";
import { useMemo } from "react";

/**
 * Spacing tokens from the theme.
 * Organized by size categories for easy access.
 */
export interface SpacingTokens {
  /** 4px - Extra small spacing */
  xs: number;
  /** 8px - Small spacing */
  sm: number;
  /** 16px - Medium spacing */
  md: number;
  /** 24px - Large spacing */
  lg: number;
  /** 32px - Extra large spacing */
  xl: number;
  /** 40px - Extra extra large spacing */
  xxl: number;
}

/**
 * Typography tokens from the theme.
 * Includes font sizes and weights.
 */
export interface TypographyTokens {
  sizes: {
    /** 10px - Extra small (labels, badges) */
    xs: number;
    /** 12px - Small (secondary text, captions) */
    sm: number;
    /** 14px - Medium (body text) */
    md: number;
    /** 16px - Large (subheadings) */
    lg: number;
    /** 20px - Extra large (headings) */
    xl: number;
    /** 24px - Extra extra large (large headings) */
    xxl: number;
  };
  weights: {
    /** 400 - Normal */
    normal: number;
    /** 500 - Medium */
    medium: number;
    /** 600 - Semi Bold */
    semiBold: number;
    /** 700 - Bold */
    bold: number;
  };
}

/**
 * Color tokens from the theme.
 * Includes status, semantic, and chart colors.
 */
export interface ColorTokens {
  /** Primary brand color (#1677ff) */
  primary: string;
  /** Success state (#52c41a) */
  success: string;
  /** Warning state (#faad14) */
  warning: string;
  /** Error state (#ff4d4f) */
  error: string;
  /** Info state (#1677ff) */
  info: string;

  /** Primary text color */
  text: string;
  /** Secondary text color (#8c8c8c) */
  textSecondary: string;
  /** Tertiary text color (#bfbfbf) */
  textTertiary: string;
  /** Border color */
  border: string;
  /** Secondary border color (#d9d9d9) */
  borderSecondary: string;

  /** Background container color (respects dark mode) */
  bgContainer: string;
  /** Background elevated color for cards (respects dark mode) */
  bgElevated: string;
  /** Background layout color (respects dark mode) */
  bgLayout: string;

  /** Chart: Planned Value (Blue) */
  chartPV: string;
  /** Chart: Earned Value (Green) */
  chartEV: string;
  /** Chart: Actual Cost (Gray) */
  chartAC: string;
  /** Chart: Forecast (Orange) */
  chartForecast: string;
  /** Chart: Actual (Red) */
  chartActual: string;
}

/**
 * Border radius tokens from the theme.
 */
export interface BorderRadiusTokens {
  /** 4px - Small radius */
  sm: number;
  /** 6px - Medium radius (default) */
  md: number;
  /** 8px - Large radius */
  lg: number;
  /** 12px - Extra large radius */
  xl: number;
}

/**
 * Structured design tokens from the theme.
 * Provides categorized access to all design tokens.
 */
export interface ThemeTokens {
  /** Spacing tokens for margins and padding */
  spacing: SpacingTokens;
  /** Typography tokens for fonts and text */
  typography: TypographyTokens;
  /** Color tokens for colors */
  colors: ColorTokens;
  /** Border radius tokens */
  borderRadius: BorderRadiusTokens;
}

/**
 * Hook to access design tokens in a structured, categorized way.
 *
 * This hook wraps Ant Design's `theme.useToken()` and organizes tokens
 * into logical groups for better developer experience.
 *
 * @returns Structured design tokens organized by category
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { spacing, typography, colors, borderRadius } = useThemeTokens();
 *
 *   return (
 *     <div style={{
 *       padding: spacing.md,
 *       fontSize: typography.lg,
 *       color: colors.textSecondary,
 *       borderRadius: borderRadius.lg
 *     }}>
 *       Content with consistent styling
 *     </div>
 *   );
 * }
 * ```
 */
export function useThemeTokens(): ThemeTokens {
  const { token } = theme.useToken();

  // Type cast for custom tokens that are defined in theme.ts but not in Ant Design's default types
  const customToken = token as typeof token & {
    marginXS: number;
    marginSM: number;
    marginMD: number;
    marginLG: number;
    marginXL: number;
    marginXXL: number;
    paddingXS: number;
    paddingSM: number;
    paddingMD: number;
    paddingLG: number;
    paddingXL: number;
    fontSizeXS: number;
    fontSizeSM: number;
    fontSizeLG: number;
    fontSizeXL: number;
    fontSizeXXL: number;
    fontWeightNormal: number;
    fontWeightMedium: number;
    fontWeightSemiBold: number;
    fontWeightBold: number;
    colorSuccess: string;
    colorWarning: string;
    colorError: string;
    colorInfo: string;
    colorTextSecondary: string;
    colorTextTertiary: string;
    colorBorderSecondary: string;
    colorBgContainer: string;
    colorBgElevated: string;
    colorBgLayout: string;
    colorChartPV: string;
    colorChartEV: string;
    colorChartAC: string;
    colorChartForecast: string;
    colorChartActual: string;
    borderRadiusSM: number;
    borderRadiusLG: number;
    borderRadiusXL: number;
  };

  return useMemo(
    () => ({
      spacing: {
        xs: customToken.marginXS,
        sm: customToken.marginSM,
        md: customToken.marginMD,
        lg: customToken.marginLG,
        xl: customToken.marginXL,
        xxl: customToken.marginXXL,
      },
      typography: {
        sizes: {
          xs: customToken.fontSizeXS,
          sm: customToken.fontSizeSM,
          md: customToken.fontSize,
          lg: customToken.fontSizeLG,
          xl: customToken.fontSizeXL,
          xxl: customToken.fontSizeXXL,
        },
        weights: {
          normal: customToken.fontWeightNormal,
          medium: customToken.fontWeightMedium,
          semiBold: customToken.fontWeightSemiBold,
          bold: customToken.fontWeightBold,
        },
      },
      colors: {
        primary: customToken.colorPrimary,
        success: customToken.colorSuccess,
        warning: customToken.colorWarning,
        error: customToken.colorError,
        info: customToken.colorInfo,
        text: customToken.colorText,
        textSecondary: customToken.colorTextSecondary,
        textTertiary: customToken.colorTextTertiary,
        border: customToken.colorBorder,
        borderSecondary: customToken.colorBorderSecondary,
        bgContainer: customToken.colorBgContainer,
        bgElevated: customToken.colorBgElevated,
        bgLayout: customToken.colorBgLayout,
        chartPV: customToken.colorChartPV,
        chartEV: customToken.colorChartEV,
        chartAC: customToken.colorChartAC,
        chartForecast: customToken.colorChartForecast,
        chartActual: customToken.colorChartActual,
      },
      borderRadius: {
        sm: customToken.borderRadiusSM,
        md: customToken.borderRadius,
        lg: customToken.borderRadiusLG,
        xl: customToken.borderRadiusXL,
      },
    }),
    [
      customToken.marginXS,
      customToken.marginSM,
      customToken.marginMD,
      customToken.marginLG,
      customToken.marginXL,
      customToken.marginXXL,
      customToken.fontSizeXS,
      customToken.fontSizeSM,
      customToken.fontSize,
      customToken.fontSizeLG,
      customToken.fontSizeXL,
      customToken.fontSizeXXL,
      customToken.fontWeightNormal,
      customToken.fontWeightMedium,
      customToken.fontWeightSemiBold,
      customToken.fontWeightBold,
      customToken.colorPrimary,
      customToken.colorSuccess,
      customToken.colorWarning,
      customToken.colorError,
      customToken.colorInfo,
      customToken.colorText,
      customToken.colorTextSecondary,
      customToken.colorTextTertiary,
      customToken.colorBorder,
      customToken.colorBorderSecondary,
      customToken.colorBgContainer,
      customToken.colorBgElevated,
      customToken.colorBgLayout,
      customToken.colorChartPV,
      customToken.colorChartEV,
      customToken.colorChartAC,
      customToken.colorChartForecast,
      customToken.colorChartActual,
      customToken.borderRadiusSM,
      customToken.borderRadius,
      customToken.borderRadiusLG,
      customToken.borderRadiusXL,
    ]
  );
}
