import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["lightweight-charts"],
          data: ["@tanstack/react-query", "@tanstack/react-table", "zustand"],
          router: ["@tanstack/react-router"],
          ui: [
            "motion",
            "lucide-react",
            "@base-ui/react/tooltip",
            "react-resizable-panels",
          ],
        },
      },
    },
  },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:5000" } },
  test: { environment: "jsdom", setupFiles: "./src/test/setup.ts" },
});
