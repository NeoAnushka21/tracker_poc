import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { APP_DEV_HOST, APP_NAME } from "./src/brand";

/** Fills %APP_NAME% in index.html from src/brand.ts, so a rename is one edit. */
function brandHtml(): Plugin {
  return { name: "brand-html", transformIndexHtml: (html) => html.replaceAll("%APP_NAME%", APP_NAME) };
}

// In dev, /api is proxied to FastAPI so the session cookie is same-origin.
// Open the app at http://<APP_DEV_HOST>:5173 (e.g. http://omniai.localhost:5173).
export default defineConfig({
  plugins: [react(), brandHtml()],
  server: {
    port: 5173,
    allowedHosts: [APP_DEV_HOST],
    // Native file events were missed on Windows (stale modules after edits); polling is reliable.
    watch: { usePolling: true, interval: 300 },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: { allowedHosts: [APP_DEV_HOST] },
  // Two pages: the app (index.html) and the always-on launcher that waits for the free server
  // to wake (launcher.html, served by the Render static site; see src/launcher.tsx).
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("index.html", import.meta.url)),
        launcher: fileURLToPath(new URL("launcher.html", import.meta.url)),
      },
    },
  },
});
