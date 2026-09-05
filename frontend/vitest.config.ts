/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // e2e/ contains Playwright specs (run via `npm run test:e2e`), not
    // Vitest ones. Playwright's `test.describe` clashes with Vitest's own
    // test collector if these files are picked up here, so exclude them
    // explicitly alongside Vitest's normal default excludes.
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});
