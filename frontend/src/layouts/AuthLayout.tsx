import { ReactNode } from "react";
import { Layout, Typography } from "antd";

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
  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <Content
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "400px",
            background: "#fff",
            padding: "40px",
            borderRadius: "8px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ textAlign: "center", marginBottom: "40px" }}>
            <img
              src="/assets/images/backcast-logo.svg"
              alt="Backcast"
              style={{
                width: "120px",
                height: "auto",
                marginBottom: "16px",
              }}
            />
            <Title level={2} style={{ marginBottom: "4px", marginTop: "8px" }}>
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
