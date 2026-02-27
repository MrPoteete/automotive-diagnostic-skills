// Checked AGENTS.md - implementing directly, pure test file
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from '../page';
import type { TSBSearchResponse } from '../../lib/api';

// Mock TypewriterText to render text immediately (bypasses setInterval delay)
vi.mock('../components/TypewriterText', () => ({
    TypewriterText: ({ text }: { text: string }) => <div>{text}</div>,
}));

// Mock VehicleForm — not under test here
vi.mock('../components/VehicleForm', () => ({
    default: () => <div data-testid="mock-vehicle-form" />,
    parseDtcInput: () => [],
}));

// Mock full api module — every method is a vi.fn()
vi.mock('../../lib/api', () => ({
    api: {
        healthCheck: vi.fn(),
        searchComplaints: vi.fn(),
        searchTSBs: vi.fn(),
        formatResults: vi.fn(),
        formatError: vi.fn(),
        diagnose: vi.fn(),
        formatDiagnosis: vi.fn(),
        fetchVehicles: vi.fn(),
        fetchVehicleYears: vi.fn(),
    },
}));

// Mock vehicles module with minimal test data
vi.mock('../../lib/vehicles', () => ({
    MAKES: ['CHEVROLET', 'FORD'],
    YEARS: [2025, 2024, 2019, 2018],
    getModelsForMake: (m: string) =>
        m === 'FORD' ? ['F-150', 'MUSTANG'] : m === 'CHEVROLET' ? ['SILVERADO'] : [],
}));

import { api } from '../../lib/api';

// ─────────────────────────────────────────────────────────────────
// Test helpers
// ─────────────────────────────────────────────────────────────────

const TSB_RESPONSE: TSBSearchResponse = {
    query: '', sanitized_query: '', results: [], source: 'TSB',
    total_count: 0, page: 1, total_pages: 1,
};

async function switchToTSBTab(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: /TSB Search/i }));
}

// ─────────────────────────────────────────────────────────────────
describe('TSB vehicle filter', () => {
    let user: ReturnType<typeof userEvent.setup>;

    beforeEach(() => {
        vi.clearAllMocks();
        user = userEvent.setup();
        vi.mocked(api.healthCheck).mockResolvedValue({ status: 'ok', message: 'Online' });
        vi.mocked(api.searchTSBs).mockResolvedValue(TSB_RESPONSE);
        vi.mocked(api.searchComplaints).mockResolvedValue({
            query: '', sanitized_query: '', results: [], source: 'NHTSA',
            total_count: 0, page: 1, total_pages: 1,
        });
        vi.mocked(api.formatResults).mockReturnValue('TSB RESULTS');
        vi.mocked(api.formatError).mockReturnValue('ERROR');
    });

    // ─────────────────────────────────────────────────────────────
    describe('Filter UI renders', () => {
        it('shows MAKE, MODEL, YEAR selects on TSB Search tab', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            expect(screen.getByRole('combobox', { name: /TSB MAKE/i })).toBeInTheDocument();
            expect(screen.getByRole('combobox', { name: /TSB MODEL/i })).toBeInTheDocument();
            expect(screen.getByRole('combobox', { name: /TSB YEAR/i })).toBeInTheDocument();
        });

        it('MODEL select is disabled until MAKE is chosen', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            expect(screen.getByRole('combobox', { name: /TSB MODEL/i })).toBeDisabled();
        });

        it('YEAR select is disabled until MODEL is chosen', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');
            expect(screen.getByRole('combobox', { name: /TSB YEAR/i })).toBeDisabled();
        });
    });

    // ─────────────────────────────────────────────────────────────
    describe('Make/model/year cascade resets', () => {
        it('changing MAKE resets MODEL and YEAR selections', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            const makeSelect = screen.getByRole('combobox', { name: /TSB MAKE/i });
            await user.selectOptions(makeSelect, 'FORD');

            const modelSelect = screen.getByRole('combobox', { name: /TSB MODEL/i });
            await user.selectOptions(modelSelect, 'F-150');

            const yearSelect = screen.getByRole('combobox', { name: /TSB YEAR/i });
            await user.selectOptions(yearSelect, '2019');

            // Change make → model and year should reset to ''
            await user.selectOptions(makeSelect, 'CHEVROLET');
            expect(modelSelect).toHaveValue('');
            expect(yearSelect).toHaveValue('');
        });

        it('changing MODEL resets YEAR selection', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');
            const modelSelect = screen.getByRole('combobox', { name: /TSB MODEL/i });
            await user.selectOptions(modelSelect, 'F-150');
            await user.selectOptions(screen.getByRole('combobox', { name: /TSB YEAR/i }), '2019');

            // Change model → year should reset
            await user.selectOptions(modelSelect, 'MUSTANG');
            expect(screen.getByRole('combobox', { name: /TSB YEAR/i })).toHaveValue('');
        });
    });

    // ─────────────────────────────────────────────────────────────
    describe('API args with vehicle filters', () => {
        it('calls searchTSBs with keyword + make only', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'brake{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('brake', 10, 1, 'FORD', undefined, undefined)
            );
        });

        it('calls searchTSBs with keyword + make + model', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');
            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MODEL/i }), 'F-150');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'brake{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('brake', 10, 1, 'FORD', 'F-150', undefined)
            );
        });

        it('calls searchTSBs with keyword + make + model + year', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');
            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MODEL/i }), 'F-150');
            await user.selectOptions(screen.getByRole('combobox', { name: /TSB YEAR/i }), '2019');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'brake{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('brake', 10, 1, 'FORD', 'F-150', 2019)
            );
        });

        it('calls searchTSBs with make only and empty query (vehicle-only search)', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');

            // Submit with empty text via Enter key
            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.click(input);
            await user.keyboard('{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('', 10, 1, 'FORD', undefined, undefined)
            );
        });
    });

    // ─────────────────────────────────────────────────────────────
    describe('Guard behavior', () => {
        it('does NOT call searchTSBs when no keyword and no make selected', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.click(input);
            await user.keyboard('{Enter}');

            expect(api.searchTSBs).not.toHaveBeenCalled();
        });
    });

    // ─────────────────────────────────────────────────────────────
    describe('Routing', () => {
        it('always routes to searchTSBs on TSB tab even without tsb keyword', async () => {
            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'brake noise{Enter}');

            await waitFor(() => expect(api.searchTSBs).toHaveBeenCalled());
            expect(api.searchComplaints).not.toHaveBeenCalled();
        });
    });

    // ─────────────────────────────────────────────────────────────
    describe('Pagination reset on filter change', () => {
        it('resets to page 1 (hides pagination controls) when tsbMake changes', async () => {
            vi.mocked(api.searchTSBs).mockResolvedValueOnce({
                ...TSB_RESPONSE, total_count: 50, page: 1, total_pages: 5,
            });

            render(<Home />);
            await switchToTSBTab(user);

            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'FORD');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'brake{Enter}');

            // Pagination controls appear after multi-page response
            await waitFor(() => expect(screen.getByText(/PAGE/i)).toBeInTheDocument());

            // Change make → pagination resets → controls disappear
            await user.selectOptions(screen.getByRole('combobox', { name: /TSB MAKE/i }), 'CHEVROLET');

            await waitFor(() =>
                expect(screen.queryByText(/PAGE/i)).not.toBeInTheDocument()
            );
        });
    });
});
