/* global __dirname */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: true,
    proxy: {
      "/auth": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/users": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/expenses": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/budgets": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/analytics": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/income": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/savings": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/goals": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/recurring": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/notifications": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/payments": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/meta": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
      "/health": { target: process.env.VITE_PROXY_TARGET || "http://localhost:9000", changeOrigin: false },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
