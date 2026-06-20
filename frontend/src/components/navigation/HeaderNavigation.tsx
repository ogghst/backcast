import React, { useState, useEffect } from "react";
import { Button, theme } from "antd";
import type { ButtonProps } from "antd";
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
const ICON_ONLY_BREAKPOINT = 1024; // Switch to icons on tablet and smaller

type NavItem = {
  key: string;
  label: string;
  icon: React.ReactNode;
};

export const HeaderNavigation: React.FC<HeaderNavigationProps> = ({
  className,
  style,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { can } = usePermission();
  const { isLoadingUser } = useAuth();
  const { token } = theme.useToken();
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

  // Build nav items based on permissions
  const items: NavItem[] = [
    { key: "/", label: "Dashboard", icon: <HomeOutlined /> },
    { key: "/projects", label: "Projects", icon: <AppstoreOutlined /> },
    ...(can("ai-chat")
      ? [{ key: "/chat", label: "AI Chat", icon: <MessageOutlined /> }]
      : []),
  ];

  // NOTE: Rendered as a plain flex row of buttons instead of AntD's
  // `<Menu mode="horizontal">`. The horizontal Menu uses rc-overflow, which
  // collapses nav items it thinks won't fit into a hidden "rest" indicator.
  // When the third item (AI Chat) was added, the flex layout could starve the
  // menu width and rc-overflow would hide it (opacity:0, position:absolute) —
  // even with `overflowedIndicator={null}`, which only suppresses the "..."
  // indicator without preventing the collapse.
  return (
    <nav
      className={`header-navigation-menu ${className || ""}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: token.paddingXXS,
        height: "100%",
        ...style,
      }}
    >
      {items.map((item) => {
        const active = location.pathname === item.key;
        const buttonStyle: ButtonProps["style"] = {
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          height: "100%",
          padding: iconOnly ? `0 ${token.padding}px` : `0 ${token.paddingLG}px`,
          color: active ? token.colorPrimary : token.colorText,
          fontWeight: active ? 500 : 400,
          borderBottom: `2px solid ${
            active ? token.colorPrimary : "transparent"
          }`,
          borderRadius: 0,
          whiteSpace: "nowrap",
        };
        return (
          <Button
            key={item.key}
            type="text"
            style={buttonStyle}
            title={iconOnly ? item.label : undefined}
            onClick={() => {
              // AI Chat is a separate app-like experience: navigate to the
              // unified /chat route and pass the current path as `returnTo`
              // so the Back button returns here. Other items navigate as-is.
              if (item.key === "/chat") {
                navigate("/chat", {
                  state: { returnTo: location.pathname + location.search },
                });
              } else {
                navigate(item.key);
              }
            }}
          >
            {item.icon}
            {!iconOnly && <span>{item.label}</span>}
          </Button>
        );
      })}
    </nav>
  );
};
