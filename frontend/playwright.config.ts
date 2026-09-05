import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against a live instance of the app (frontend + backend +
 * Postgres/Redis, e.g. via `docker-compose up`). They are NOT part of the
 * `npm run test` (Vitest) unit-test command — run separately with
 * `npm run test:e2e`, typically in CI after the stack is up, or locally
 * during manual QA passes.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: "html",

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
