/* global __dirname, process */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: true,
    watch: {
      usePolling: true,
    },
    proxy: [
      "/auth", "/users", "/expenses", "/budgets", "/analytics",
      "/income", "/money-in", "/savings", "/goals", "/projects", "/recurring", "/notifications",
      "/payments", "/meta", "/health", "/debts", "/installments", "/wallets", "/assets", "/expected-inflows",
      "/subcategories"
    ].reduce((acc, route) => {
      // These are paths where the frontend React Router UI uses the EXACT same 
      // root path as the backend API Python router.
      const collidingUiRoutes = ["/expenses", "/budgets", "/analytics", "/income", "/savings", "/debts", "/wallets", "/assets"];
      const isColliding = collidingUiRoutes.includes(route);

      acc[route] = {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:9000",
        changeOrigin: false,
        bypass: (req) => {
          // If this is a colliding route and the browser is explicitly asking for an HTML page 
          // (like a full page reload), we serve the React app so client-side routing takes over.
          if (isColliding && req.headers.accept?.includes("text/html")) {
            // Protect sub-routes that DO need to hit the backend directly via browser (like CSV exports)
            if (req.url.includes("/export")) return null;
            return "/index.html";
          }
          // All pure API routes (like /auth/google/login) safely bypass this and hit Python natively!
          return null; 
        }
      };
      return acc;
    }, {}),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
