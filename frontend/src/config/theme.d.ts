/**
 * Design Token Type Declarations
 *
 * Extends Ant Design's AliasToken interface with custom design tokens.
 * We augment AliasToken (not GlobalToken) because GlobalToken is a type alias
 * (AliasToken & ComponentTokenMap), and module augmentation only works with interfaces.
 *
 * Since AliasToken is the base that feeds into GlobalToken, adding properties here
 * makes them available on the token object returned by theme.useToken().
 */

declare module "antd/es/theme/interface/alias" {
  export interface AliasToken {
    // === Typography Scale (custom) ===
    fontSizeXS: number;
    fontSizeSM: number;
    fontSizeXL: number;
    fontSizeXXL: number;
    fontWeightNormal: number;
    fontWeightMedium: number;
    fontWeightSemiBold: number;
    fontWeightBold: number;

    // === Chart Colors (custom) ===
    colorChartPV: string;
    colorChartEV: string;
    colorChartAC: string;
    colorChartForecast: string;
    colorChartActual: string;
  }
}
