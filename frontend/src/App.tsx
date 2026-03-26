import { App as AntApp, ConfigProvider, theme as antTheme } from "antd";
import { Toaster } from "sonner";
import { RouterProvider } from "react-router-dom";
import { router } from "@/routes";
import { theme } from "@/config/theme";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";
import { useTokenRefreshTimer } from "@/utils/tokenRefresh";

export const App = () => {
  const { themeMode } = useUserPreferencesStore();

  // Initialize token refresh timer
  useTokenRefreshTimer();

  return (
    <ConfigProvider
      theme={{
        ...theme,
        algorithm:
          themeMode === "dark"
            ? antTheme.darkAlgorithm
            : antTheme.defaultAlgorithm,
        // Apply dark mode tokens when dark mode is enabled
        token:
          themeMode === "dark"
            ? { ...theme.token, ...theme.darkModeTokens }
            : theme.token,
      }}
    >
      <AntApp>
        <Toaster position="top-right" richColors />
        <RouterProvider router={router} />
      </AntApp>
    </ConfigProvider>
  );
};
