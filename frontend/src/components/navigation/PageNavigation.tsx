import React from "react";
import { Tabs } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

export interface NavigationItem {
  key: string;
  label: string;
  path: string;
  icon?: React.ReactNode;
}

export interface PageNavigationProps {
  items: NavigationItem[];
  variant?: "horizontal" | "sidebar";
}

export const PageNavigation: React.FC<PageNavigationProps> = ({ items, variant = "horizontal" }) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Find active key based on current path
  const activeKey = items.find((item) => location.pathname === item.path)?.key || items[0]?.key;

  const handleTabChange = (key: string) => {
    const item = items.find((i) => i.key === key);
    if (item) {
      navigate(item.path);
    }
  };

  return (
    <Tabs
      activeKey={activeKey}
      items={items.map((item) => ({ key: item.key, label: item.label, icon: item.icon }))}
      onChange={handleTabChange}
      {...(variant === "sidebar" && { tabPosition: "left" })}
    />
  );
};
