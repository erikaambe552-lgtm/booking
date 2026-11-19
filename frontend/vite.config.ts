import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to Django so the browser talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Allow public tunnel addresses (Cloudflare Quick Tunnel) to reach the dev server.
    allowedHosts: [".trycloudflare.com", ".app.github.dev"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/media": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  preview: {
    port: 4173,
    allowedHosts: [".trycloudflare.com", ".app.github.dev"],
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/media": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
