import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.POKEAPP_E2E_BASE_URL || "http://127.0.0.1:5173",
    channel:
      process.env.POKEAPP_TEST_BROWSER ||
      (process.platform === "win32" ? "msedge" : undefined),
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: process.env.POKEAPP_E2E_BASE_URL
    ? undefined
    : {
        command: "npm run dev -- --port 5173 --strictPort",
        url: "http://127.0.0.1:5173",
        reuseExistingServer: !process.env.CI,
        env: { VITE_API_BASE_URL: "http://127.0.0.1:8000" },
      },
});
