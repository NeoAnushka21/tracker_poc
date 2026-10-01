import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer, defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { APP_DEV_HOST, APP_NAME, APP_TAGLINE } from "./src/brand";

/** Fills %APP_NAME% in the HTML pages from src/brand.ts, so a rename is one edit. %APP_URL% is the app's
 *  address on the always-on welcome site (VITE_APP_URL), empty when the app serves the page itself. */
function brandHtml(): Plugin {
  const appUrl = (process.env.VITE_APP_URL ?? "").replace(/\/$/, "");
  return {
    name: "brand-html",
    transformIndexHtml: (html) =>
      html.replaceAll("%APP_NAME%", APP_NAME).replaceAll("%APP_TAGLINE%", APP_TAGLINE).replaceAll("%APP_URL%", appUrl),
  };
}

/** After the build, saves /privacy and /terms as dist/privacy.html and dist/terms.html: the app's page
 *  with the text already inside #root, for readers that don't run JavaScript (Google's brand check reads
 *  the privacy policy that way). In the browser main.tsx renders over it as usual. */
function prerenderPages(): Plugin {
  const pages = [
    { file: "privacy", module: "/src/components/PrivacyPage.tsx", title: "Privacy" },
    { file: "terms", module: "/src/components/TermsPage.tsx", title: "Terms" },
  ];
  let root = "";
  let outDir = "";
  return {
    name: "prerender-pages",
    apply: "build",
    configResolved(c) {
      root = c.root;
      outDir = resolve(c.root, c.build.outDir);
    },
    async closeBundle() {
      const server = await createServer({
        root, configFile: false, logLevel: "error", appType: "custom",
        server: { middlewareMode: true, hmr: false }, esbuild: { jsx: "automatic" },
      });
      try {
        const shell = readFileSync(resolve(outDir, "index.html"), "utf8");
        for (const p of pages) {
          const { default: Page } = await server.ssrLoadModule(p.module);
          const html = shell
            .replace('<div id="root"></div>', `<div id="root">${renderToStaticMarkup(createElement(Page))}</div>`)
            .replace(/<title>([^<]*)<\/title>/, `<title>${p.title} · $1</title>`);
          if (!html.includes('<div id="root"><')) throw new Error(`prerender ${p.file}: #root not found in index.html`);
          writeFileSync(resolve(outDir, `${p.file}.html`), html);
        }
      } finally {
        await server.close();
      }
    },
  };
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
// Open the app at http://<APP_DEV_HOST>:5173 (e.g. http://tandurust.localhost:5173).
export default defineConfig({
  plugins: [react(), brandHtml(), welcomeRoute(), prerenderPages()],
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
