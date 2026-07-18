/// <reference types="vitest" />
import { defineConfig } from "vite";
import path from "node:path";

// Vitest config for the ASC frontend. jsdom provides window/localStorage/fetch
// globals the auth client relies on. The "@/..." alias mirrors tsconfig.json.
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
  esbuild: {
    jsx: "automatic",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
