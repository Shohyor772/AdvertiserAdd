import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:8002",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "../tmp/playwright-report" }],
  ],
  outputDir: "../tmp/playwright-results",
  webServer: {
    command: process.platform==='win32' ? "..\\venv\\Scripts\\python.exe -u ..\\manage.py runserver 127.0.0.1:8002 --noreload --settings=config.e2e_settings" : '../venv/bin/python -u ../manage.py runserver 127.0.0.1:8002 --noreload --settings=config.e2e_settings',
    url: "http://127.0.0.1:8002/api/options/",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
