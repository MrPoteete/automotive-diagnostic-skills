// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helper — select vehicle manually (FORD F-150 2020)
// ---------------------------------------------------------------------------
async function selectFordF150(page: import('@playwright/test').Page) {
    await page.selectOption('#manual-make', 'FORD');
    // Wait for model options to populate
    await page.waitForSelector('#manual-model option[value="F-150"]', { state: 'attached', timeout: 5000 });
    await page.selectOption('#manual-model', 'F-150');
    await page.selectOption('#manual-year', '2020');
    await page.locator('button:has-text("Select Vehicle")').click();
    // "Change" button only appears in the summary bar after vehicle is selected
    await expect(page.locator('button:has-text("Change")')).toBeVisible({ timeout: 8000 });
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

        await page.locator('[data-testid="close-modal"]').click();
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

// Helper — select FORD ESCAPE 2020 (1,347 complaints — guaranteed top_components)
async function selectFordEscape2020(page: import('@playwright/test').Page) {
    await page.selectOption('#manual-make', 'FORD');
    await page.waitForSelector('#manual-model option[value="ESCAPE"]', { state: 'attached', timeout: 5000 });
    await page.selectOption('#manual-model', 'ESCAPE');
    await page.waitForSelector('#manual-year option[value="2020"]', { state: 'attached', timeout: 5000 });
    await page.selectOption('#manual-year', '2020');
    await page.locator('button:has-text("Select Vehicle")').click();
    await expect(page.locator('button:has-text("Change")')).toBeVisible({ timeout: 8000 });
}

// ---------------------------------------------------------------------------
// Suite 5: Component drill-down
// ---------------------------------------------------------------------------
test.describe('Component drill-down', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectFordEscape2020(page);
        // Wait for component bars to appear (dashboard fully loaded with complaint data)
        await expect(page.locator('[data-testid="component-bar"]').first()).toBeVisible({ timeout: 15000 });
    });

    test('clicking first component bar opens the drill-down panel', async ({ page }) => {
        await page.locator('[data-testid="component-bar"]').first().click();
        // Panel header is unique: "complaints — 2020 FORD ESCAPE"
        await expect(page.locator('text=complaints — 2020 FORD ESCAPE')).toBeVisible({ timeout: 10000 });
    });

    test('drill-down panel header contains vehicle info and complaints label', async ({ page }) => {
        await page.locator('[data-testid="component-bar"]').first().click();
        await expect(page.locator('text=complaints — 2020 FORD ESCAPE')).toBeVisible({ timeout: 10000 });
        // Close button is present when panel is open
        await expect(page.locator('[data-testid="close-drilldown-btn"]')).toBeVisible();
    });

    test('close button hides the drill-down panel', async ({ page }) => {
        await page.locator('[data-testid="component-bar"]').first().click();
        await expect(page.locator('[data-testid="close-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await page.locator('[data-testid="close-drilldown-btn"]').click();
        await expect(page.locator('[data-testid="close-drilldown-btn"]')).not.toBeVisible();
    });

    test('clicking same component bar again toggles panel closed', async ({ page }) => {
        const firstBar = page.locator('[data-testid="component-bar"]').first();
        await firstBar.click();
        await expect(page.locator('[data-testid="close-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await firstBar.click();
        await expect(page.locator('[data-testid="close-drilldown-btn"]')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 6: TSB drill-down
// ---------------------------------------------------------------------------
test.describe('TSB drill-down', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectFordF150(page);
        // Wait for TSB tile using data-testid
        await expect(page.locator('[data-testid="tsb-tile"]')).toBeVisible({ timeout: 15000 });
    });

    test('TSB tile shows "click to view" hint text', async ({ page }) => {
        await expect(page.locator('[data-testid="tsb-tile"]').locator('text=click to view')).toBeVisible();
    });

    test('clicking TSB tile opens TsbDrillDown panel', async ({ page }) => {
        await page.locator('[data-testid="tsb-tile"]').click();
        await expect(page.locator('text=Technical Service Bulletins')).toBeVisible({ timeout: 10000 });
    });

    test('close button hides the TSB panel', async ({ page }) => {
        await page.locator('[data-testid="tsb-tile"]').click();
        await expect(page.locator('[data-testid="close-tsb-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await page.locator('[data-testid="close-tsb-drilldown-btn"]').click();
        await expect(page.locator('[data-testid="close-tsb-drilldown-btn"]')).not.toBeVisible();
    });

    test('clicking TSB tile again toggles panel closed', async ({ page }) => {
        const tsbTile = page.locator('[data-testid="tsb-tile"]');
        await tsbTile.click();
        await expect(page.locator('[data-testid="close-tsb-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await tsbTile.click();
        await expect(page.locator('[data-testid="close-tsb-drilldown-btn"]')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 7: Safety Recalls drill-down
// ---------------------------------------------------------------------------
test.describe('Safety Recalls drill-down', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectFordF150(page);
        // Wait for the recall tile to appear — FORD F-150 2020 has 10 recalls
        await expect(page.locator('[data-testid="recalls-tile"]')).toBeVisible({ timeout: 15000 });
    });

    test('Safety Recalls tile shows recall count and click hint', async ({ page }) => {
        const tile = page.locator('[data-testid="recalls-tile"]');
        // Tile label is visible
        await expect(tile.locator('text=Safety Recalls')).toBeVisible();
        // A non-zero number is rendered inside the tile (recall_count > 0)
        const countText = await tile.innerText();
        const digits = countText.match(/\d+/);
        expect(digits).not.toBeNull();
        expect(parseInt(digits![0], 10)).toBeGreaterThan(0);
        // Click hint is present
        await expect(tile.locator('text=click to view')).toBeVisible();
    });

    test('clicking Safety Recalls tile opens RecallDrillDown panel', async ({ page }) => {
        await page.locator('[data-testid="recalls-tile"]').click();
        // Panel heading contains "Safety Recalls"
        await expect(page.locator('[data-testid="close-recall-drilldown-btn"]')).toBeVisible({ timeout: 10000 });
    });

    test('close button hides the Recalls panel', async ({ page }) => {
        await page.locator('[data-testid="recalls-tile"]').click();
        // Wait for recall data to load before interacting with panel controls
        await page.waitForLoadState('networkidle');
        await expect(page.locator('[data-testid="close-recall-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await page.locator('[data-testid="close-recall-drilldown-btn"]').click({ force: true });
        await expect(page.locator('[data-testid="close-recall-drilldown-btn"]')).not.toBeVisible();
    });

    test('clicking Safety Recalls tile again toggles panel closed', async ({ page }) => {
        await page.locator('[data-testid="recalls-tile"]').click();
        // Wait for recall data to load before clicking the tile again
        await page.waitForLoadState('networkidle');
        await expect(page.locator('[data-testid="close-recall-drilldown-btn"]')).toBeVisible({ timeout: 10000 });

        await page.locator('[data-testid="recalls-tile"]').click({ force: true });
        await expect(page.locator('[data-testid="close-recall-drilldown-btn"]')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 8: Clear / Reset buttons
// ---------------------------------------------------------------------------
test.describe('Clear buttons', () => {
    test('Diagnose tab — Clear button appears after typing symptoms and clears form', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectFordF150(page);

        // Clear button should not be visible before any input
        await expect(page.locator('[data-testid="clear-diagnose-btn"]')).not.toBeVisible();

        // Type symptoms
        await page.fill('#symptoms-input', 'rough idle at cold start');

        // Clear button should now appear
        await expect(page.locator('[data-testid="clear-diagnose-btn"]')).toBeVisible();

        // Click Clear
        await page.locator('[data-testid="clear-diagnose-btn"]').click();

        // Symptoms input should be empty
        await expect(page.locator('#symptoms-input')).toHaveValue('');

        // Clear button should disappear
        await expect(page.locator('[data-testid="clear-diagnose-btn"]')).not.toBeVisible();
    });

    test('Database tab — Clear button appears after typing and clears search', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.locator('button:has-text("Database")').click();
        await expect(page.locator('h1:has-text("Complaints Database")')).toBeVisible();

        // Clear button should not be visible initially
        await expect(page.locator('[data-testid="clear-search-btn"]')).not.toBeVisible();

        // Type in search
        await page.fill('#search-input', 'brake failure');

        // Clear button should appear
        await expect(page.locator('[data-testid="clear-search-btn"]')).toBeVisible();

        // Click Clear
        await page.locator('[data-testid="clear-search-btn"]').click();

        // Search input should be empty
        await expect(page.locator('#search-input')).toHaveValue('');

        // Clear button should disappear
        await expect(page.locator('[data-testid="clear-search-btn"]')).not.toBeVisible();
    });

    test('TSB Search tab — Clear button resets vehicle filters and search input', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.locator('button:has-text("TSB Search")').click();
        await expect(page.locator('h1:has-text("TSB Search")')).toBeVisible();

        // Select a make to trigger Clear button appearance
        await page.selectOption('#tsb-make', 'FORD');

        // Clear button should appear (tsbMake is set)
        await expect(page.locator('[data-testid="clear-search-btn"]')).toBeVisible();

        // Click Clear
        await page.locator('[data-testid="clear-search-btn"]').click();

        // Make select should reset to empty
        await expect(page.locator('#tsb-make')).toHaveValue('');

        // Clear button should disappear
        await expect(page.locator('[data-testid="clear-search-btn"]')).not.toBeVisible();
    });
});
