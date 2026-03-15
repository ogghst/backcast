import { ReactNode } from "react";
import { Layout, Typography, theme } from "antd";

const { Content } = Layout;
const { Title } = Typography;

interface AuthLayoutProps {
  children: ReactNode;
}

/**
 * Layout for authentication pages (login, register)
 * Simple centered design without sidebar/header
 * Updated: 2026-02-07
 */
export const AuthLayout = ({ children }: AuthLayoutProps) => {
  const { token } = theme.useToken();

  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <Content
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: token.paddingXL,
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "400px",
            background: "#fff",
            padding: 40,
            borderRadius: token.borderRadiusLG,
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          }}
        >
          <div
            style={{
              textAlign: "center",
              marginBottom: 40,
            }}
          >
            <img
              src="/assets/images/backcast-logo.svg"
              alt="Backcast"
              style={{
                width: "120px",
                height: "auto",
                marginBottom: token.paddingMD,
              }}
            />
            <Title
              level={2}
              style={{ marginBottom: token.marginXS, marginTop: token.marginSM }}
            >
              Backcast
            </Title>
            <Typography.Text type="secondary">
              Entity Version Control System
            </Typography.Text>
          </div>
          {children}
        </div>
      </Content>
    </Layout>
  );
};
