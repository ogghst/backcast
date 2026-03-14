/**
 * Design Token Type Declarations
 *
 * Extends Ant Design's theme types with custom design tokens.
 * This file augments the `GlobalToken` interface to include our custom tokens.
 *
 * Note: Due to Ant Design's ES module structure, we extend the interface here.
 * TypeScript may not always pick up these extensions when checking individual files.
 */

declare module "antd" {
  export interface GlobalToken {
    // === Spacing Scale ===
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

    // === Typography Scale ===
    fontSizeXS: number;
    fontSizeSM: number;
    fontSizeLG: number;
    fontSizeXL: number;
    fontSizeXXL: number;
    fontWeightNormal: number;
    fontWeightMedium: number;
    fontWeightSemiBold: number;
    fontWeightBold: number;

    // === Status Colors ===
    colorSuccess: string;
    colorWarning: string;
    colorError: string;
    colorInfo: string;

    // === Semantic Colors ===
    colorTextSecondary: string;
    colorTextTertiary: string;
    colorBorderSecondary: string;

    // === Chart Colors ===
    colorChartPV: string;
    colorChartEV: string;
    colorChartAC: string;
    colorChartForecast: string;
    colorChartActual: string;

    // === Border Radius Variants ===
    borderRadiusSM: number;
    borderRadiusLG: number;
    borderRadiusXL: number;
  }
}
