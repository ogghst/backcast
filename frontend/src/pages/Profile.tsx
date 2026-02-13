import { Card, Typography, Descriptions, Tag } from "antd";
import { useAuth } from "@/hooks/useAuth";

const { Title } = Typography;

export const Profile = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div style={{ padding: "24px" }}>
      <Title level={2}>My Profile</Title>
      <Card variant="borderless">
        <Descriptions title="User Info" bordered>
          <Descriptions.Item label="Full Name">
            {user.full_name}
          </Descriptions.Item>
          <Descriptions.Item label="Email">{user.email}</Descriptions.Item>
          <Descriptions.Item label="Role">
            <Tag color="blue">{user.role.toUpperCase()}</Tag>
          </Descriptions.Item>
          {user.department && (
            <Descriptions.Item label="Department">
              {user.department}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>
    </div>
  );
};
