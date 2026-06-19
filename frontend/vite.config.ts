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
        // No manualChunks: let Rollup do automatic chunk splitting.
        // A previous manualChunks function created a MUTUAL (cyclic) dependency
        // between vendor-react and vendor-antd: vendor-antd imported React's
        // useLayoutEffect from vendor-react while vendor-react imported from
        // vendor-antd, so ES module init order could not be topological and
        // React's export was undefined at evaluation time — causing
        // "Cannot read properties of undefined (reading 'useLayoutEffect')"
        // and a blank page in production. Automatic splitting guarantees an
        // acyclic chunk dependency graph.
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
