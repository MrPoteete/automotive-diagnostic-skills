// Checked AGENTS.md - e2e tests for Pre-Purchase Inspection tab.
// Requires both servers running (backend :8000, frontend :3000).
// Vehicle: FORD ESCAPE 2018-2022 — known to have complaints, TSBs, and recall data.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helper — navigate to Pre-Purchase tab
// ---------------------------------------------------------------------------
async function goToPrepurchase(page: import('@playwright/test').Page) {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.locator('nav button:has-text("Pre-Purchase")').click();
    await expect(page.locator('h1:has-text("Pre-Purchase Inspection")')).toBeVisible({ timeout: 5000 });
}

// ---------------------------------------------------------------------------
// Helper — select FORD ESCAPE and generate checklist
// ---------------------------------------------------------------------------
async function generateFordEscapeChecklist(page: import('@playwright/test').Page) {
    await page.selectOption('#checklist-panel-make', 'FORD');
    await page.waitForSelector('#checklist-panel-model option[value="ESCAPE"]', { state: 'attached', timeout: 5000 });
    await page.selectOption('#checklist-panel-model', 'ESCAPE');
    await page.selectOption('#checklist-panel-year-start', '2018');
    await page.selectOption('#checklist-panel-year-end', '2022');
    await page.locator('[data-testid="generate-checklist-btn"]').click();
    // Wait for loading then rendered result
    await expect(page.locator('[data-testid="checklist-rendered"]')).toBeVisible({ timeout: 30000 });
}

// ---------------------------------------------------------------------------
// Suite 1: Tab navigation
// ---------------------------------------------------------------------------
test.describe('Pre-Purchase tab navigation', () => {
    test('Pre-Purchase tab appears in navigation', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await expect(page.locator('nav button:has-text("Pre-Purchase")')).toBeVisible();
    });

    test('clicking Pre-Purchase tab shows the panel', async ({ page }) => {
        await goToPrepurchase(page);
        await expect(page.locator('[data-testid="checklist-panel"]')).toBeVisible();
        await expect(page.locator('h1:has-text("Pre-Purchase Inspection")')).toBeVisible();
    });

    test('panel shows vehicle selector fields', async ({ page }) => {
        await goToPrepurchase(page);
        await expect(page.locator('#checklist-panel-make')).toBeVisible();
        await expect(page.locator('#checklist-panel-model')).toBeVisible();
        await expect(page.locator('#checklist-panel-year-start')).toBeVisible();
        await expect(page.locator('#checklist-panel-year-end')).toBeVisible();
    });

    test('Generate Checklist button is disabled until make and model are selected', async ({ page }) => {
        await goToPrepurchase(page);
        await expect(page.locator('[data-testid="generate-checklist-btn"]')).toBeDisabled();

        await page.selectOption('#checklist-panel-make', 'FORD');
        await expect(page.locator('[data-testid="generate-checklist-btn"]')).toBeDisabled();

        await page.waitForSelector('#checklist-panel-model option[value="ESCAPE"]', { state: 'attached', timeout: 5000 });
        await page.selectOption('#checklist-panel-model', 'ESCAPE');
        await expect(page.locator('[data-testid="generate-checklist-btn"]')).toBeEnabled();
    });
});

// ---------------------------------------------------------------------------
// Suite 2: Checklist generation
// ---------------------------------------------------------------------------
test.describe('Checklist generation', () => {
    test('generates checklist for FORD ESCAPE 2018-2022', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        // Rendered result should be visible
        await expect(page.locator('[data-testid="checklist-rendered"]')).toBeVisible();
    });

    test('shows section headers in rendered checklist', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        // Recalls header
        await expect(page.locator('text=Active Safety Recalls').first()).toBeVisible();
        // Inspection priorities header
        await expect(page.locator('text=Top Inspection Priorities').first()).toBeVisible();
        // Standard checks header
        await expect(page.locator('text=Standard Checks').first()).toBeVisible();
    });

    test('shows download markdown button after generation', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        await expect(page.locator('[data-testid="download-md-btn"]')).toBeVisible();
    });

    test('shows download PDF button after generation', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        await expect(page.locator('[data-testid="download-pdf-btn"]')).toBeVisible();
    });

    test('shows inspection priority items with checkboxes', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        // At least one Carbon checkbox from inspection priorities should be visible
        const checkboxes = page.locator('[data-testid="checklist-rendered"] input[type="checkbox"]');
        await expect(checkboxes.first()).toBeVisible({ timeout: 5000 });
        const count = await checkboxes.count();
        expect(count).toBeGreaterThan(0);
    });

    test('shows standard checks section with checkboxes', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        await expect(page.locator('text=VIN matches title').first()).toBeVisible();
    });

    test('Clear button removes the checklist', async ({ page }) => {
        await goToPrepurchase(page);
        await generateFordEscapeChecklist(page);

        await page.locator('button:has-text("Clear")').click();
        await expect(page.locator('[data-testid="checklist-rendered"]')).not.toBeVisible();
        // Generate button should be re-enabled (vehicle still selected)
        await expect(page.locator('[data-testid="generate-checklist-btn"]')).toBeEnabled();
    });
});

// ---------------------------------------------------------------------------
// Suite 3: Model dropdown population
// ---------------------------------------------------------------------------
test.describe('Vehicle selector behaviour', () => {
    test('model dropdown populates after make selection', async ({ page }) => {
        await goToPrepurchase(page);
        await page.selectOption('#checklist-panel-make', 'FORD');
        await page.waitForSelector('#checklist-panel-model option[value="ESCAPE"]', { state: 'attached', timeout: 5000 });
        const modelOptions = await page.locator('#checklist-panel-model option').count();
        expect(modelOptions).toBeGreaterThan(1);
    });

    test('model resets to empty when make changes', async ({ page }) => {
        await goToPrepurchase(page);
        await page.selectOption('#checklist-panel-make', 'FORD');
        await page.waitForSelector('#checklist-panel-model option[value="ESCAPE"]', { state: 'attached', timeout: 5000 });
        await page.selectOption('#checklist-panel-model', 'ESCAPE');

        // Change make — model should reset
        await page.selectOption('#checklist-panel-make', 'CHEVROLET');
        const modelValue = await page.locator('#checklist-panel-model').inputValue();
        expect(modelValue).toBe('');
    });
});
