import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [
      react(),
      VitePWA({
        registerType: "autoUpdate",
        injectRegister: "auto",
        includeAssets: [
          "assets/images/backcast.svg",
          "assets/images/backcast.png",
          "assets/images/backcast-192.png",
        ],
        manifest: {
          name: "Backcast",
          short_name: "Backcast",
          description: "Project Budget Management & Earned Value Management System",
          theme_color: "#1a1a2e",
          background_color: "#ffffff",
          display: "standalone",
          scope: "/",
          start_url: "/",
          icons: [
            {
              src: "assets/images/backcast-192.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "any",
            },
            {
              src: "assets/images/backcast.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "maskable",
            },
          ],
        },
        workbox: {
          maximumFileSizeToCacheInBytes: 8 * 1024 * 1024, // 8 MB
          globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "google-fonts-cache",
                expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "gstatic-fonts-cache",
                expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
              },
            },
          ],
        },
        devOptions: { enabled: false },
      }),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      // 3000 kB: vendor bundles (antd ~2.8 MB, echarts ~1.1 MB) are single cached/
      // immutable libraries that load once and can't be meaningfully split further.
      chunkSizeWarningLimit: 3000,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return;
            if (id.includes("/mermaid/")) return; // preserve mermaid's own dynamic splitting
            // antd core + @ant-design/* kept as one chunk: splitting sub-packages
            // (icons/x/charts) only shaved ~200 kB and introduced circular-chunk warnings.
            if (id.includes("/antd/") || id.includes("@ant-design/")) return "vendor-antd";
            // --- other heavy vendors ---
            if (id.includes("/echarts/") || id.includes("echarts-for-react") || id.includes("/zrender/")) return "vendor-echarts";
            if (id.includes("/recharts/") || id.includes("/victory-vendor/")) return "vendor-recharts";
            if (id.includes("/@mui/") || id.includes("/@emotion/")) return "vendor-mui";
            if (id.includes("react-syntax-highlighter") || id.includes("/refractor/") || id.includes("/lowlight/") || id.includes("/prismjs/")) return "vendor-syntax";
            if (id.includes("react-markdown") || id.includes("/remark-") || id.includes("/rehype-") || id.includes("/micromark") || id.includes("/mdast-") || id.includes("/unified/") || id.includes("/hast/") || id.includes("/katex/")) return "vendor-markdown";
            if (id.includes("/react/") || id.includes("/react-dom/") || id.includes("/react-router") || id.includes("/scheduler/")) return "vendor-react";
            if (id.includes("/@tanstack/")) return "vendor-query";
          },
        },
      },
    },
    server: {
      host: "::",
      proxy: {
        "/api": {
          target: env.VITE_API_URL,
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
        exclude: [
          "node_modules/**",
          "dist/**",
          "**/*.d.ts",
          "**/*.config.*",
          "**/stories/**",  // Storybook stories and assets
          "**/*.test.ts",    // Test files themselves
          "**/*.test.tsx",   // Test files themselves
          "src/setupTests.ts",  // Test setup file
        ],
      },
    },
  };
});
