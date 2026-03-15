// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: false,   // Run sequentially — both servers are shared
    forbidOnly: !!process.env.CI,
    retries: 1,
    workers: 1,
    reporter: [['list']],
    timeout: 30000,

    use: {
        baseURL: 'http://localhost:3000',
        headless: true,
        screenshot: 'only-on-failure',
        video: 'off',
        trace: 'on-first-retry',
    },

    projects: [
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                launchOptions: {
                    args: ['--no-sandbox', '--disable-setuid-sandbox'],
                },
            },
        },
    ],
});
