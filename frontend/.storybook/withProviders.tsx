import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme as antTheme } from "antd";
import { MemoryRouter } from "react-router-dom";
import { theme } from "../src/config/theme";

// Create a new QueryClient for each story to ensure isolation
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

export const withProviders = (Story: React.ComponentType) => (
  <QueryClientProvider client={queryClient}>
    <ConfigProvider
      theme={{
        ...theme,
        algorithm: antTheme.defaultAlgorithm,
      }}
    >
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    </ConfigProvider>
  </QueryClientProvider>
);
