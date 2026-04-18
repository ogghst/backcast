import { Typography, theme } from "antd";

const { Text } = Typography;

interface FieldItemProps {
  label: string;
  children: React.ReactNode;
}

/**
 * FieldItem - Tiny label+value pair with consistent styling.
 *
 * Renders a secondary label above arbitrary content. Parent controls
 * layout (typically via Ant Design Col).
 */
export const FieldItem = ({ label, children }: FieldItemProps) => {
  const { token } = theme.useToken();

  return (
    <div>
      <Text
        type="secondary"
        style={{
          fontSize: token.fontSizeSM,
          display: "block",
          marginBottom: token.paddingXS,
          fontWeight: token.fontWeightMedium,
        }}
      >
        {label}
      </Text>
      {children}
    </div>
  );
};
