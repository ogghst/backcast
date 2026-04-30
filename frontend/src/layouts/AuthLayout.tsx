import { ReactNode } from "react";
import { Layout, Typography, theme } from "antd";
import { WaveBackground } from "@/components/common/WaveBackground";

const { Content } = Layout;
const { Title } = Typography;

interface AuthLayoutProps {
  children: ReactNode;
}

export const AuthLayout = ({ children }: AuthLayoutProps) => {
  const { token } = theme.useToken();

  return (
    <Layout style={{ minHeight: "100vh", background: token.colorBgLayout }}>
      <WaveBackground />
      <Content
        style={{
          position: "relative",
          zIndex: 1,
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
            background: token.colorBgElevated,
            padding: 40,
            borderRadius: token.borderRadiusLG,
            boxShadow: token.boxShadow ||
              "0 2px 8px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.1)",
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
              Agentic warping your project dimensions
            </Typography.Text>
          </div>
          {children}
        </div>
      </Content>
    </Layout>
  );
};
