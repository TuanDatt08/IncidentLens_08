import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure",
    launchOptions: process.env.UI_TEST_BROWSER ? { channel: process.env.UI_TEST_BROWSER } : undefined },
  webServer: process.env.AUTH_E2E_EXTERNAL ? undefined : [
    { command: ".\\.venv\\Scripts\\python.exe -m tests.auth_smoke_server", cwd: "..", url: "http://127.0.0.1:8100/api/v1/health", reuseExistingServer: false },
    { command: "npm.cmd run dev -- --port 3100", url: "http://127.0.0.1:3100/incidents", reuseExistingServer: false,
      env: { BACKEND_INTERNAL_URL: "http://127.0.0.1:8100", NEXT_PUBLIC_USE_MOCK_API: "false", NEXT_DIST_DIR: ".next/ui-e2e" } },
  ],
});
