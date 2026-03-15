// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helper — select vehicle manually (FORD F-150 2020)
// ---------------------------------------------------------------------------
async function selectFordF150(page: import('@playwright/test').Page) {
    await page.selectOption('#manual-make', 'FORD');
    // Wait for model options to populate
    await page.waitForSelector('#manual-model option[value="F-150"]', { timeout: 5000 });
    await page.selectOption('#manual-model', 'F-150');
    await page.selectOption('#manual-year', '2020');
    await page.locator('button:has-text("Select Vehicle")').click();
    // Wait for summary bar
    await expect(page.locator('text=FORD')).toBeVisible({ timeout: 8000 });
}

// ---------------------------------------------------------------------------
// Suite 1: Page load and navigation
// ---------------------------------------------------------------------------
test.describe('Page load and navigation', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('loads page and shows Diagnose tab by default', async ({ page }) => {
        await expect(page.locator('h1:has-text("Vehicle Diagnostic")')).toBeVisible();
        await expect(page.locator('#vin-input')).toBeVisible();
    });

    test('shows system status in header', async ({ page }) => {
        await expect(
            page.locator('header').filter({ hasText: /Online|Offline|Checking/ })
        ).toBeVisible({ timeout: 8000 });
    });

    test('switches to TSB Search tab', async ({ page }) => {
        await page.locator('nav button:has-text("TSB Search")').click();
        await expect(page.locator('h1:has-text("TSB Search")')).toBeVisible();
    });

    test('switches to Database tab', async ({ page }) => {
        await page.locator('nav button:has-text("Database")').click();
        await expect(page.locator('h1:has-text("Complaints Database")')).toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 2: Manual vehicle selection
// ---------------------------------------------------------------------------
test.describe('Manual vehicle selection', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('selects a vehicle and shows dashboard', async ({ page }) => {
        await selectFordF150(page);
        // Dashboard should load with complaint stats
        await expect(page.locator('text=Complaints').first()).toBeVisible({ timeout: 15000 });
        await expect(page.locator('text=TSBs').first()).toBeVisible({ timeout: 5000 });
    });

    test('shows symptoms form and disabled Run Diagnostic after selection', async ({ page }) => {
        await selectFordF150(page);
        await expect(page.locator('text=Complaints').first()).toBeVisible({ timeout: 15000 });

        await expect(page.locator('#symptoms-input')).toBeVisible();
        // Run Diagnostic is disabled until symptoms are typed
        await expect(page.locator('button:has-text("Run Diagnostic")')).toBeDisabled();
    });

    test('enables Run Diagnostic after typing symptoms', async ({ page }) => {
        await selectFordF150(page);
        await expect(page.locator('#symptoms-input')).toBeVisible({ timeout: 15000 });

        await page.fill('#symptoms-input', 'rough idle at cold start');
        await expect(page.locator('button:has-text("Run Diagnostic")')).toBeEnabled();
    });

    test('Change button resets vehicle selection', async ({ page }) => {
        await selectFordF150(page);
        await expect(page.locator('text=Complaints').first()).toBeVisible({ timeout: 15000 });

        await page.locator('button:has-text("Change")').click();
        // Summary bar should disappear
        await expect(page.locator('#symptoms-input')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 3: Report modal
// ---------------------------------------------------------------------------
test.describe('Report modal', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectFordF150(page);
        // Wait for dashboard to load
        await expect(page.locator('text=Complaints').first()).toBeVisible({ timeout: 15000 });
    });

    test('opens report modal when Generate Report tile is clicked', async ({ page }) => {
        await page.locator('button:has-text("Generate Report")').click();

        await expect(page.locator('[data-testid="report-modal"]')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('[data-testid="report-modal"]').locator('text=/Generate Report —/')).toBeVisible();
        await expect(page.locator('#report-year-start')).toBeVisible();
        await expect(page.locator('#report-year-end')).toBeVisible();
    });

    test('modal Generate Report button is enabled on open', async ({ page }) => {
        await page.locator('button:has-text("Generate Report")').click();
        await expect(page.locator('[data-testid="report-modal"]')).toBeVisible({ timeout: 5000 });

        // The Generate Report button inside the modal should be enabled
        await expect(
            page.locator('[data-testid="report-modal"] button:has-text("Generate Report")')
        ).toBeEnabled();
    });

    test('modal closes when X button is clicked', async ({ page }) => {
        await page.locator('button:has-text("Generate Report")').click();
        await expect(page.locator('[data-testid="report-modal"]')).toBeVisible({ timeout: 5000 });

        // Click the close button (aria-label or title "Close")
        await page.locator('[data-testid="report-modal"] button[aria-label="Close"]').click();
        await expect(page.locator('[data-testid="report-modal"]')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 4: VIN entry UI
// ---------------------------------------------------------------------------
test.describe('VIN entry UI', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('Decode button is disabled for short input and enabled at 17 chars', async ({ page }) => {
        const vinInput = page.locator('#vin-input');
        const decodeButton = page.locator('button:has-text("Decode")');

        await vinInput.fill('ABC123');
        await expect(decodeButton).toBeDisabled();

        await vinInput.fill('AAAAAAAAAAAAAAAAA'); // exactly 17
        await expect(decodeButton).toBeEnabled();
    });

    test('VIN input uppercases typed characters', async ({ page }) => {
        const vinInput = page.locator('#vin-input');

        await vinInput.fill('abc123defghi4567j');
        // React onChange uppercases input
        await expect(vinInput).toHaveValue('ABC123DEFGHI4567J');
    });

    test('VIN input truncates to 17 characters', async ({ page }) => {
        const vinInput = page.locator('#vin-input');

        await vinInput.fill('BBBBBBBBBBBBBBBBBB'); // 18 chars
        const value = await vinInput.inputValue();
        expect(value.length).toBeLessThanOrEqual(17);
    });
});
