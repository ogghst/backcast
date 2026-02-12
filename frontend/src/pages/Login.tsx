import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Form, Input, Button, Alert, Typography } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useAuth } from "@/hooks/useAuth";
import { AuthLayout } from "@/layouts/AuthLayout";
import type { UserLogin } from "@/types/auth";
import { getErrorMessage } from "@/utils/apiError";

const { Text } = Typography;

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoggingIn, loginError } = useAuth();
  const [errorMessage, setErrorMessage] = useState<string>("");

  // Get the intended destination from location state, or default to home
  const from = (location.state as { from?: string })?.from || "/";

  const onFinish = async (values: UserLogin) => {
    try {
      setErrorMessage("");
      await login(values);
      // Redirect to intended destination after successful login
      navigate(from, { replace: true });
    } catch (error: unknown) {
      // Handle login errors
      const message = getErrorMessage(error);
      setErrorMessage(message);
    }
  };

  return (
    <AuthLayout>
      <Form
        name="login"
        onFinish={onFinish}
        autoComplete="off"
        size="large"
        layout="vertical"
      >
        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: "Please enter your email" },
            { type: "email", message: "Please enter a valid email" },
          ]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder="email@example.com"
            autoComplete="email"
          />
        </Form.Item>

        <Form.Item
          name="password"
          label="Password"
          rules={[{ required: true, message: "Please enter your password" }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Password"
            autoComplete="current-password"
          />
        </Form.Item>

        {errorMessage && (
          <Form.Item>
            <Alert title={errorMessage} type="error" showIcon closable />
          </Form.Item>
        )}

        {loginError && !errorMessage && (
          <Form.Item>
            <Alert
              message="Login failed. Please try again."
              type="error"
              showIcon
            />
          </Form.Item>
        )}

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={isLoggingIn}
            block
            style={{ marginTop: "8px" }}
          >
            {isLoggingIn ? "Logging in..." : "Log In"}
          </Button>
        </Form.Item>
      </Form>
    </AuthLayout>
  );
}
