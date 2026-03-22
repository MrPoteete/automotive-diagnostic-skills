// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helper — select HONDA ACCORD 2015 manually
// ---------------------------------------------------------------------------
async function selectHondaAccord2015(page: Page) {
    await page.selectOption('#manual-make', 'HONDA');
    await page.waitForSelector('#manual-model option[value="ACCORD"]', { state: 'attached', timeout: 5000 });
    await page.selectOption('#manual-model', 'ACCORD');
    await page.selectOption('#manual-year', '2015');
    await page.locator('button:has-text("Select Vehicle")').click();
    await expect(page.locator('button:has-text("Change")')).toBeVisible({ timeout: 8000 });
}

// ---------------------------------------------------------------------------
// Seed data — posted once in beforeAll for each suite that needs history
// ---------------------------------------------------------------------------
const ENTRY_1 = {
    year: 2015,
    make: 'HONDA',
    model: 'ACCORD',
    symptoms: 'rough idle at cold start, hesitation on acceleration',
    dtc_codes: ['P0300', 'P0171'],
    findings: 'Vacuum leak at intake manifold gasket. Random misfire correlates with lean condition.',
    candidate_count: 3,
    has_warnings: false,
};

const ENTRY_2 = {
    year: 2015,
    make: 'HONDA',
    model: 'ACCORD',
    symptoms: 'brake pedal soft, ABS light on',
    dtc_codes: ['C0035'],
    findings: 'Left front wheel speed sensor intermittent signal. ABS module fault code confirmed.',
    candidate_count: 2,
    has_warnings: true,
};

// ---------------------------------------------------------------------------
// Suite 1: Panel visibility
// ---------------------------------------------------------------------------
test.describe('Panel visibility', () => {
    test.beforeAll(async ({ request }) => {
        await request.post('http://localhost:3000/api/history', { data: ENTRY_1 });
        await request.post('http://localhost:3000/api/history', { data: ENTRY_2 });
    });

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('history panel appears after selecting HONDA ACCORD 2015', async ({ page }) => {
        await selectHondaAccord2015(page);
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).toBeVisible({ timeout: 8000 });
    });

    test('history panel is not visible for a vehicle with no seeded history', async ({ page }) => {
        // F-150 2020 has no seeded history entries in this test suite
        await page.selectOption('#manual-make', 'FORD');
        await page.waitForSelector('#manual-model option[value="F-150"]', { state: 'attached', timeout: 5000 });
        await page.selectOption('#manual-model', 'F-150');
        await page.selectOption('#manual-year', '2020');
        await page.locator('button:has-text("Select Vehicle")').click();
        await expect(page.locator('button:has-text("Change")')).toBeVisible({ timeout: 8000 });

        // Panel should not appear — loading completes with 0 entries
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).not.toBeVisible({ timeout: 2000 });
    });
});

// ---------------------------------------------------------------------------
// Suite 2: Panel toggle
// ---------------------------------------------------------------------------
test.describe('Panel toggle', () => {
    test.beforeAll(async ({ request }) => {
        await request.post('http://localhost:3000/api/history', { data: ENTRY_1 });
        await request.post('http://localhost:3000/api/history', { data: ENTRY_2 });
    });

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectHondaAccord2015(page);
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).toBeVisible({ timeout: 8000 });
    });

    test('panel is collapsed by default — entry list not visible', async ({ page }) => {
        // Panel header is visible but entry rows should not be rendered yet
        await expect(page.locator('[data-testid="history-toggle"]')).toBeVisible();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).not.toBeVisible();
    });

    test('clicking toggle opens entries; clicking again hides them', async ({ page }) => {
        const toggle = page.locator('[data-testid="history-toggle"]');

        // Open
        await toggle.click();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).toBeVisible({ timeout: 5000 });

        // Close
        await toggle.click();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 3: Entry content
// ---------------------------------------------------------------------------
test.describe('Entry content', () => {
    test.beforeAll(async ({ request }) => {
        await request.post('http://localhost:3000/api/history', { data: ENTRY_1 });
        await request.post('http://localhost:3000/api/history', { data: ENTRY_2 });
    });

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectHondaAccord2015(page);
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).toBeVisible({ timeout: 8000 });
        // Open the panel so entries are rendered
        await page.locator('[data-testid="history-toggle"]').click();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).toBeVisible({ timeout: 5000 });
    });

    test('entries show truncated symptoms text', async ({ page }) => {
        const headers = page.locator('[data-testid="history-entry-header"]');
        const count = await headers.count();
        expect(count).toBeGreaterThan(0);

        // At least one entry header should contain recognisable symptom text
        const allText = await headers.allInnerTexts();
        const hasSymptomsText = allText.some(
            (t) => t.includes('rough idle') || t.includes('brake pedal')
        );
        expect(hasSymptomsText).toBe(true);
    });

    test('entry with DTC codes shows gray tags', async ({ page }) => {
        // P0300 and P0171 belong to ENTRY_1
        const grayTags = page.locator('[data-testid="history-entry-header"]').locator('.cds--tag--gray');
        await expect(grayTags.first()).toBeVisible({ timeout: 5000 });
    });

    test('entry with has_warnings=true shows red warning tag', async ({ page }) => {
        // ENTRY_2 has has_warnings: true
        const redTag = page.locator('[data-testid="history-entry-header"]').locator('.cds--tag--red');
        await expect(redTag.first()).toBeVisible({ timeout: 5000 });
        await expect(redTag.first()).toContainText('Warnings');
    });

    test('entry without warnings does NOT show a red warning tag among its own tags', async ({ page }) => {
        // ENTRY_1 has has_warnings: false — find the entry row containing "rough idle"
        // .first() — multiple identical entries accumulate across runs; any one is sufficient
        const entry1Row = page.locator('[data-testid="history-entry"]').filter({ hasText: 'rough idle' }).first();
        await expect(entry1Row).toBeVisible({ timeout: 5000 });
        await expect(entry1Row.locator('.cds--tag--red')).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 4: Entry expansion
// ---------------------------------------------------------------------------
test.describe('Entry expansion', () => {
    test.beforeAll(async ({ request }) => {
        await request.post('http://localhost:3000/api/history', { data: ENTRY_1 });
        await request.post('http://localhost:3000/api/history', { data: ENTRY_2 });
    });

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectHondaAccord2015(page);
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).toBeVisible({ timeout: 8000 });
        await page.locator('[data-testid="history-toggle"]').click();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).toBeVisible({ timeout: 5000 });
    });

    test('clicking an entry header reveals the findings section', async ({ page }) => {
        await page.locator('[data-testid="history-entry-header"]').first().click();
        await expect(page.locator('[data-testid="history-findings"]').first()).toBeVisible({ timeout: 5000 });
    });

    test('expanded findings shows the findings text', async ({ page }) => {
        // Expand first entry (ENTRY_1 — vacuum leak findings)
        const firstHeader = page.locator('[data-testid="history-entry-header"]').first();
        await firstHeader.click();

        const findings = page.locator('[data-testid="history-findings"]').first();
        await expect(findings).toBeVisible({ timeout: 5000 });
        // The pre block inside findings should contain the stored findings text
        const findingsText = await findings.innerText();
        expect(findingsText).toMatch(/vacuum leak|wheel speed sensor/i);
    });

    test('clicking entry header again collapses the findings section', async ({ page }) => {
        const firstHeader = page.locator('[data-testid="history-entry-header"]').first();

        // Expand
        await firstHeader.click();
        await expect(page.locator('[data-testid="history-findings"]').first()).toBeVisible({ timeout: 5000 });

        // Collapse
        await firstHeader.click();
        await expect(page.locator('[data-testid="history-findings"]').first()).not.toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// Suite 5: Multiple entries
// ---------------------------------------------------------------------------
test.describe('Multiple entries', () => {
    test.beforeAll(async ({ request }) => {
        await request.post('http://localhost:3000/api/history', { data: ENTRY_1 });
        await request.post('http://localhost:3000/api/history', { data: ENTRY_2 });
    });

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await selectHondaAccord2015(page);
        await expect(page.locator('[data-testid="diagnosis-history-panel"]')).toBeVisible({ timeout: 8000 });
        await page.locator('[data-testid="history-toggle"]').click();
        await expect(page.locator('[data-testid="history-entry-header"]').first()).toBeVisible({ timeout: 5000 });
    });

    test('both seeded entries appear in the expanded panel', async ({ page }) => {
        const headers = page.locator('[data-testid="history-entry-header"]');
        const count = await headers.count();
        expect(count).toBeGreaterThanOrEqual(2);

        const allText = await headers.allInnerTexts();
        const hasEntry1 = allText.some((t) => t.includes('rough idle'));
        const hasEntry2 = allText.some((t) => t.includes('brake pedal'));
        expect(hasEntry1).toBe(true);
        expect(hasEntry2).toBe(true);
    });

    test('both entries can be expanded simultaneously', async ({ page }) => {
        const headers = page.locator('[data-testid="history-entry-header"]');

        // Expand first entry
        await headers.first().click();
        await expect(page.locator('[data-testid="history-findings"]').first()).toBeVisible({ timeout: 5000 });

        // Expand second entry
        await headers.nth(1).click();
        const findingsSections = page.locator('[data-testid="history-findings"]');
        await expect(findingsSections.nth(0)).toBeVisible({ timeout: 5000 });
        await expect(findingsSections.nth(1)).toBeVisible({ timeout: 5000 });
    });
});
