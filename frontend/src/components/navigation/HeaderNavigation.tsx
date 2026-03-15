import React, { useState, useEffect } from "react";
import { Menu, MenuProps } from "antd";
import {
  HomeOutlined,
  AppstoreOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { usePermission } from "@/hooks/usePermission";
import { useAuth } from "@/hooks/useAuth";

interface HeaderNavigationProps {
  className?: string;
  style?: React.CSSProperties;
}

// Breakpoint for switching to icon-only mode
const ICON_ONLY_BREAKPOINT = 900;

export const HeaderNavigation: React.FC<HeaderNavigationProps> = ({
  className,
  style,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { can } = usePermission();
  const { isLoadingUser } = useAuth();
  const [iconOnly, setIconOnly] = useState(false);

  // Check screen width and update icon-only mode
  useEffect(() => {
    const checkWidth = () => {
      setIconOnly(window.innerWidth < ICON_ONLY_BREAKPOINT);
    };

    // Initial check
    checkWidth();

    // Add resize listener
    window.addEventListener("resize", checkWidth);

    return () => window.removeEventListener("resize", checkWidth);
  }, []);

  // Don't render menu items until user data is loaded
  if (isLoadingUser) {
    return null;
  }

  // Build menu items based on permissions and screen size
  const menuItems: MenuProps["items"] = [
    {
      key: "/",
      label: iconOnly ? undefined : "Dashboard",
      icon: <HomeOutlined />,
    },
    {
      key: "/projects",
      label: iconOnly ? undefined : "Projects",
      icon: <AppstoreOutlined />,
    },
    ...(can("ai-chat")
      ? [
          {
            key: "/chat",
            label: iconOnly ? undefined : "AI Chat",
            icon: <MessageOutlined />,
          },
        ]
      : []),
  ];

  return (
    <Menu
      mode="horizontal"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={({ key }) => navigate(key)}
      overflowedIndicator={null} // Disable ellipsis overflow menu
      className={`header-navigation-menu ${className || ""}`}
      style={style}
    />
  );
};
