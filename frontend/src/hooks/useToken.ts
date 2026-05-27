/**
 * Extended token hook that includes custom theme tokens.
 *
 * Ant Design v6 changed how GlobalToken is composed (via @ant-design/cssinjs-utils),
 * which breaks the module augmentation pattern from theme.d.ts.
 * This hook provides a typed cast that works regardless.
 */

import { theme } from "antd";

/** Custom tokens defined in theme.ts but not in Ant Design's default types */
interface CustomTokens {
  // Typography Scale (custom)
  fontSizeXS: number;
  fontSizeSM: number;
  fontSizeXL: number;
  fontSizeXXL: number;
  fontWeightNormal: number;
  fontWeightMedium: number;
  fontWeightSemiBold: number;
  fontWeightBold: number;

  // Chart Colors (custom)
  colorChartPV: string;
  colorChartEV: string;
  colorChartAC: string;
  colorChartForecast: string;
  colorChartActual: string;
}

export type ExtendedToken = ReturnType<typeof theme.useToken>["token"] & CustomTokens;

/**
 * Drop-in replacement for theme.useToken() that includes custom theme tokens.
 *
 * @example
 * ```tsx
 * const { token } = useExtendedToken();
 * // token.fontSizeXXL is now typed
 * ```
 */
export function useExtendedToken(): {
  token: ExtendedToken;
  hashId: string;
  theme: ReturnType<typeof theme.useToken>["theme"];
  cssVar: ReturnType<typeof theme.useToken>["cssVar"];
  realToken: ExtendedToken;
} {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = theme.useToken() as any;
  return {
    token: result.token as ExtendedToken,
    hashId: result.hashId as string,
    theme: result.theme,
    cssVar: result.cssVar,
    realToken: result.realToken as ExtendedToken,
  };
}
