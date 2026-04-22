import { theme } from "antd";

/**
 * Shared Descriptions props for entity info cards.
 *
 * Pass the antd theme token to get consistent size, columns,
 * and label/content styling. Spread the result onto a `<Descriptions>`.
 *
 * @example
 * ```tsx
 * const { token } = theme.useToken();
 * <Descriptions {...entityInfoDescriptionsProps(token)}>
 *   ...
 * </Descriptions>
 * ```
 */
export const entityInfoDescriptionsProps = (
  token: ReturnType<typeof theme.useToken>["token"]
) => ({
  size: "middle" as const,
  column: { xs: 1, sm: 2 },
  colon: true,
  labelStyle: {
    fontWeight: token.fontWeightMedium,
    color: token.colorTextSecondary,
    fontSize: token.fontSize,
  },
  contentStyle: {
    color: token.colorText,
    fontSize: token.fontSize,
  },
});
