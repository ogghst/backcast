import React from "react";
import "./index.css"; // Global styles
import "./i18n/config"; // Initialize i18n
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { persistQueryClient } from "@tanstack/react-query-persist-client";
import "antd/dist/reset.css";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import "@/api/client"; // Initialize API client configuration
import { createIDBPersister, shouldDehydrateQuery, setAppPersister } from "@/api/queryPersister";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
    },
  },
});

const persister = createIDBPersister();
setAppPersister(persister);

persistQueryClient({
  queryClient,
  persister,
  maxAge: 24 * 60 * 60 * 1000,
  dehydrateOptions: {
    shouldDehydrateQuery,
  },
});

import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TimeMachineProvider>
          <App />
        </TimeMachineProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
