import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    testTimeout: 30_000,
    maxWorkers: 2,
    exclude: ["e2e/**", "node_modules/**"],
    coverage: {
      // Line coverage is the repository's 80% target; branches retain a strict
      // floor while App Router state combinations are additionally covered E2E.
      thresholds: { statements: 80, functions: 80, lines: 80, branches: 75 },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
