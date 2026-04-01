import { theme } from "antd";
import React, { useCallback } from "react";

interface EntityCardProps {
  /** Primary title (entity name) */
  title: string;
  /** Subtitle line (code or identifier) */
  subtitle?: string;
  /** Badge element (Tag) for status/level/type */
  badge?: React.ReactNode;
  /** Click handler for the whole card */
  onClick?: () => void;
  /** Metrics zone: 2-3 key numbers/stat blocks */
  metrics?: React.ReactNode;
  /** Meta zone: secondary information (dates, parent, branch) */
  meta?: React.ReactNode;
  /** Actions zone: buttons in footer */
  actions?: React.ReactNode;
  /** Additional style overrides */
  style?: React.CSSProperties;
  /** Additional class */
  className?: string;
}

export const EntityCard: React.FC<EntityCardProps> = ({
  title,
  subtitle,
  badge,
  onClick,
  metrics,
  meta,
  actions,
  style,
  className,
}) => {
  const { token } = theme.useToken();

  const handleMouseEnter = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.borderColor = token.colorPrimary;
      e.currentTarget.style.boxShadow = `0 2px 8px ${token.colorPrimary}20`;
    },
    [token.colorPrimary],
  );

  const handleMouseLeave = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      e.currentTarget.style.borderColor = token.colorBorderSecondary;
      e.currentTarget.style.boxShadow = "none";
    },
    [token.colorBorderSecondary],
  );

  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        display: "flex",
        flexDirection: "column",
        background: token.colorBgContainer,
        border: `1px solid ${token.colorBorderSecondary}`,
        borderRadius: token.borderRadiusLG,
        padding: token.paddingMD,
        cursor: onClick ? "pointer" : undefined,
        transition: "all 150ms ease",
        ...style,
      }}
      onMouseEnter={onClick ? handleMouseEnter : undefined}
      onMouseLeave={onClick ? handleMouseLeave : undefined}
    >
      {/* Header zone */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: token.marginSM,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: token.fontSizeLG,
              fontWeight: token.fontWeightSemiBold ?? 600,
              color: token.colorText,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{
                fontSize: token.fontSizeSM,
                color: token.colorTextSecondary,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                marginTop: token.marginXS,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
        {badge && <div style={{ flexShrink: 0 }}>{badge}</div>}
      </div>

      {/* Metrics zone */}
      {metrics && (
        <div
          style={{
            borderTop: `1px solid ${token.colorBorderSecondary}`,
            marginTop: token.marginSM,
            paddingTop: token.marginSM,
            flexGrow: 1,
          }}
        >
          {metrics}
        </div>
      )}

      {/* Meta zone */}
      {meta && (
        <div
          style={{
            marginTop: token.marginSM,
            flexGrow: metrics ? undefined : 1,
          }}
        >
          {meta}
        </div>
      )}

      {/* Grow spacer: push actions to bottom when neither metrics nor meta fills space */}
      {!metrics && !meta && <div style={{ flexGrow: 1 }} />}

      {/* Actions footer */}
      {actions && (
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            borderTop: `1px solid ${token.colorBorderSecondary}`,
            paddingTop: token.marginSM,
            marginTop: token.marginSM,
          }}
        >
          {actions}
        </div>
      )}
    </div>
  );
};
