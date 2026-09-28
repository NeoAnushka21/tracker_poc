import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api is proxied to FastAPI so the session cookie is same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Native file events were missed on Windows (stale modules after edits); polling is reliable.
    watch: { usePolling: true, interval: 300 },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
