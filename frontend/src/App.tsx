import { App as AntApp, ConfigProvider, theme as antTheme } from "antd";
import { Toaster } from "sonner";
import { RouterProvider } from "react-router-dom";
import { router } from "@/routes";
import { theme } from "@/config/theme";
import { useUserPreferencesStore } from "@/stores/useUserPreferencesStore";

export const App = () => {
  const { themeMode } = useUserPreferencesStore();

  return (
    <ConfigProvider
      theme={{
        ...theme,
        algorithm:
          themeMode === "dark"
            ? antTheme.darkAlgorithm
            : antTheme.defaultAlgorithm,
      }}
    >
      <AntApp>
        <Toaster position="top-right" richColors />
        <RouterProvider router={router} />
      </AntApp>
    </ConfigProvider>
  );
};
