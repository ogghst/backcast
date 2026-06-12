# PWA Setup for Mobile Stability

**Date:** 2026-06-12
**Branch:** `llm_per_specialist`

## Problem

On mobile browsers, the Backcast tab is randomly reloaded due to OS-level memory management (tab eviction/BFCache discard). When the user returns to the tab, a full page reload occurs, losing all in-memory state (React context, TanStack Query cache, WebSocket connections).

## Solution

Install Backcast as a **Progressive Web App (PWA)** with a service worker. Mobile OS treats installed PWAs more like native apps — they get significantly better memory retention and are less aggressively evicted. If a reload does happen, the service worker serves all static assets from cache (near-instant).

### Implementation

Used `vite-plugin-pwa` with Workbox `generateSW` strategy (auto-generated service worker, no custom SW file).

**Key configuration decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Strategy | `generateSW` | No custom fetch logic needed — auto-generated SW handles precaching |
| Registration | `autoUpdate` | New SW activates automatically on deploy, no user prompt |
| API caching | None | TanStack Query + IndexedDB already handles API caching |
| File size limit | 8 MB | Main JS chunk is ~6 MB, exceeds Workbox default 2 MB limit |
| Dev mode | Disabled | SW only active in production builds |

### Files Changed

| File | Change |
|------|--------|
| `frontend/vite.config.ts` | Added `VitePWA` plugin with manifest, workbox config, font caching |
| `frontend/index.html` | Added PWA meta tags (theme-color, apple-mobile-web-app, touch icon) |
| `frontend/src/main.tsx` | Added `import "virtual:pwa-register"` |
| `frontend/src/vite-env.d.ts` | Added `vite-plugin-pwa` type reference |

### Workbox Configuration

- **Precache:** `**/*.{js,css,html,svg,png,woff2}` (62 entries, ~9 MB)
- **Runtime cache:** Google Fonts (CacheFirst, 1 year expiry)
- **No API caching:** `/api/**` requests go direct to network

### Installation (Mobile)

1. Deploy production build (`npm run build` → serve `dist/`)
2. Open app URL in mobile browser
3. Browser shows "Add to Home Screen" / "Install app" prompt
4. Install — app opens as standalone PWA (no browser chrome)

### Build Verification

```
PWA v1.3.0
mode      generateSW
precache  62 entries (9149.75 KiB)
files generated
  dist/sw.js
  dist/workbox-dcde9eb3.js
```
