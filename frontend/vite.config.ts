import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { APP_DEV_HOST, APP_NAME, APP_TAGLINE } from "./src/brand";

/** Fills %APP_NAME% in the HTML pages from src/brand.ts, so a rename is one edit. */
function brandHtml(): Plugin {
  return { name: "brand-html", transformIndexHtml: (html) => html.replaceAll("%APP_NAME%", APP_NAME).replaceAll("%APP_TAGLINE%", APP_TAGLINE) };
}

/** Dev server: /welcome is the welcome page, as the backend serves it in production. */
function welcomeRoute(): Plugin {
  return {
    name: "welcome-route",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.url === "/welcome" || req.url?.startsWith("/welcome?")) req.url = req.url.replace("/welcome", "/welcome.html");
        next();
      });
    },
  };
}

// In dev, /api is proxied to FastAPI so the session cookie is same-origin.
// Open the app at http://<APP_DEV_HOST>:5173 (e.g. http://omniai.localhost:5173).
export default defineConfig({
  plugins: [react(), brandHtml(), welcomeRoute()],
  server: {
    port: 5173,
    allowedHosts: [APP_DEV_HOST],
    // Native file events were missed on Windows (stale modules after edits); polling is reliable.
    watch: { usePolling: true, interval: 300 },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: { allowedHosts: [APP_DEV_HOST] },
  // Two pages: the app (index.html) and the welcome page (welcome.html: served at /welcome by the
  // backend, and as the start page of the always-on Render static site; see src/welcome.ts).
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("index.html", import.meta.url)),
        welcome: fileURLToPath(new URL("welcome.html", import.meta.url)),
      },
    },
  },
});
