import React from "react";
import { Tag } from "antd";
import { useExtendedToken } from "@/hooks/useToken";

export interface StatusTagProps {
  /** Tag label text */
  children: React.ReactNode;
  /** Ant Design Tag color (e.g. "blue", "green") */
  color?: string;
}

/**
 * Styled status/badge tag for use in header cards.
 * Centralizes the repeated Tag styling pattern (font, padding, border-radius).
 */
export const StatusTag: React.FC<StatusTagProps> = ({ children, color }) => {
  const { token } = useExtendedToken();

  return (
    <Tag
      color={color}
      style={{
        fontSize: token.fontSize,
        padding: `${token.paddingXS}px ${token.paddingMD}px`,
        borderRadius: token.borderRadius,
        fontWeight: token.fontWeightMedium,
        margin: 0,
      }}
    >
      {children}
    </Tag>
  );
};
