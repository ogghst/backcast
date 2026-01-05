import React from "react";
import { Typography } from "antd";

const { Title, Paragraph } = Typography;

const Home: React.FC = () => {
  return (
    <div>
      <Title level={2}>Welcome to Backcast</Title>
      <Paragraph>This is the dashboard for Backcast.</Paragraph>
    </div>
  );
};

export default Home;
