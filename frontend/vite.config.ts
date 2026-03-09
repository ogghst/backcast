import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "::",
      proxy: {
        "/api": {
          target: env.VITE_API_URL || "http://192.168.1.23:8020",
          changeOrigin: true,
          ws: true, // Enable WebSocket proxying
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/setupTests.ts",
      exclude: ["**/node_modules/**", "**/dist/**", "tests/e2e/**"],
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
      },
    },
  };
});
