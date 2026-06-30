import React from "react";
import { Card, Space, theme } from "antd";

type CardStyles = React.ComponentProps<typeof Card>["styles"];

export interface PanelCardProps {
  /** Optional leading icon rendered in the primary color. */
  icon?: React.ReactNode;
  /** Panel title text. */
  title: string;
  /** Extra content rendered in the card header (e.g. action buttons, status tag). */
  extra?: React.ReactNode;
  /** Inline style for the underlying Card. */
  style?: React.CSSProperties;
  /** Pass-through for antd Card `styles` (e.g. body padding overrides). */
  styles?: CardStyles;
  /** className for the underlying Card. */
  className?: string;
  children: React.ReactNode;
}

/**
 * PanelCard - Shared content panel with a standardized title style.
 *
 * Wraps antd `Card` (size="small") with a canonical title formatting
 * (fontSizeLG + fontWeightStrong) and a primary-colored icon, matching
 * the title style used by `EntityInfoCard` and the entity overview pages.
 *
 * The underlying Card's `ref` (HTMLDivElement), `styles`, and `className`
 * are passed through, so callers can attach scroll-to-section refs and
 * override body padding exactly as they would on a raw `Card`.
 *
 * @example
 * ```tsx
 * <PanelCard icon={<DollarOutlined />} title="Budget Summary" extra={<Tag>Healthy</Tag>}>
 *   <Row>...</Row>
 * </PanelCard>
 * ```
 */
export const PanelCard = React.forwardRef<HTMLDivElement, PanelCardProps>(
  ({ icon, title, extra, style, styles, className, children }, ref) => {
    const { token } = theme.useToken();

    return (
      <Card
        ref={ref}
        size="small"
        className={className}
        style={style}
        styles={{
          header: { paddingBlock: token.paddingSM, paddingInline: token.paddingLG },
          ...styles,
        }}
        title={
          <Space>
            {icon && (
              <span style={{ color: token.colorPrimary, display: "inline-flex" }}>
                {icon}
              </span>
            )}
            <span
              style={{
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightStrong,
                color: token.colorText,
              }}
            >
              {title}
            </span>
          </Space>
        }
        extra={extra}
      >
        {children}
      </Card>
    );
  },
);
PanelCard.displayName = "PanelCard";
