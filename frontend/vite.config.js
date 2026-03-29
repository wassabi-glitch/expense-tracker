/* global __dirname */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/auth": "http://localhost:9000",
      "/users": "http://localhost:9000",
      "/expenses": "http://localhost:9000",
      "/budgets": "http://localhost:9000",
      "/analytics": "http://localhost:9000",
      "/income": "http://localhost:9000",
      "/savings": "http://localhost:9000",
      "/goals": "http://localhost:9000",
      "/recurring": "http://localhost:9000",
      "/notifications": "http://localhost:9000",
      "/meta": "http://localhost:9000",
      "/health": "http://localhost:9000",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
