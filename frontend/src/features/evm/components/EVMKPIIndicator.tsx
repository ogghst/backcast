import { theme, Typography } from "antd";

import { formatValue } from "../utils/formatters";

const { Text } = Typography;

interface EVMKPIIndicatorProps {
  label: string;
  value: number | null;
  format: "currency" | "percentage" | "number";
  status: "good" | "warning" | "bad";
  neutral?: boolean;
}

export const EVMKPIIndicator: React.FC<EVMKPIIndicatorProps> = ({
  label,
  value,
  format,
  status,
  neutral = false,
}) => {
  const { token } = theme.useToken();

  const dotColor = neutral
    ? token.colorPrimary
    : status === "good"
      ? token.colorSuccess
      : status === "warning"
        ? token.colorWarning
        : token.colorError;

  const displayValue =
    value === null ? "N/A" : formatValue(value, format);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: token.paddingXXS,
        flex: 1,
        minWidth: 120,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      <Text
        type="secondary"
        style={{ fontSize: 12, fontWeight: 500, whiteSpace: "nowrap" }}
      >
        {label}
      </Text>
      <Text
        strong
        style={{ fontSize: 16, fontWeight: 600, whiteSpace: "nowrap" }}
      >
        {displayValue}
      </Text>
    </div>
  );
};
