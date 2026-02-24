// Checked AGENTS.md - implementing directly, pure test file
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from '../page';
import type { SearchResponse, TSBSearchResponse } from '../../lib/api';

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
    },
}));

import { api } from '../../lib/api';

// ────────────────────────────────────────────────────────────────
// Test helpers
// ────────────────────────────────────────────────────────────────

const COMPLAINT_RESPONSE: SearchResponse = {
    query: 'q', sanitized_query: 'q', results: [], source: 'NHTSA',
    total_count: 0, page: 1, total_pages: 1,
};
const TSB_RESPONSE: TSBSearchResponse = {
    query: 'q', sanitized_query: 'q', results: [], source: 'TSB',
    total_count: 0, page: 1, total_pages: 1,
};

/** Click a sidebar nav tab and wait for the CyberInput to appear. */
async function switchTab(user: ReturnType<typeof userEvent.setup>, tabLabel: string) {
    await user.click(screen.getByRole('button', { name: new RegExp(tabLabel, 'i') }));
}

// ────────────────────────────────────────────────────────────────
describe('handleSearch — routing and behavior', () => {
    let user: ReturnType<typeof userEvent.setup>;

    beforeEach(() => {
        vi.clearAllMocks();
        user = userEvent.setup();
        // healthCheck resolves by default (fires in useEffect on mount)
        vi.mocked(api.healthCheck).mockResolvedValue({ status: 'ok', message: 'Online' });
        vi.mocked(api.searchComplaints).mockResolvedValue(COMPLAINT_RESPONSE);
        vi.mocked(api.searchTSBs).mockResolvedValue(TSB_RESPONSE);
        vi.mocked(api.formatResults).mockReturnValue('FORMATTED_RESULTS');
        vi.mocked(api.formatError).mockReturnValue('FORMATTED_ERROR');
    });

    // ────────────────────────────────────────────────────────────
    describe('empty input guard', () => {
        it('returns early without API calls when input is blank', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            // Focus input then press Enter with no text
            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.click(input);
            await user.keyboard('{Enter}');

            expect(api.searchComplaints).not.toHaveBeenCalled();
            expect(api.searchTSBs).not.toHaveBeenCalled();
        });

        it('returns early when input is only whitespace', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, '   {Enter}');

            expect(api.searchComplaints).not.toHaveBeenCalled();
            expect(api.searchTSBs).not.toHaveBeenCalled();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('TSB / complaint routing', () => {
        it('routes to searchTSBs when query contains "tsb"', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'tsb brake recall{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('tsb brake recall', 10, 1)
            );
            expect(api.searchComplaints).not.toHaveBeenCalled();
        });

        it('routes to searchTSBs when query contains "bulletin"', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'service bulletin airbag{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('service bulletin airbag', 10, 1)
            );
            expect(api.searchComplaints).not.toHaveBeenCalled();
        });

        it('routes to searchComplaints for generic queries', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'engine knocking at idle{Enter}');

            await waitFor(() =>
                expect(api.searchComplaints).toHaveBeenCalledWith('engine knocking at idle', 10, 1)
            );
            expect(api.searchTSBs).not.toHaveBeenCalled();
        });

        it('is case-insensitive — uppercase TSB routes to searchTSBs', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'TSB Ford F-150 transmission{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('TSB Ford F-150 transmission', 10, 1)
            );
            expect(api.searchComplaints).not.toHaveBeenCalled();
        });

        it('is case-insensitive — mixed-case Bulletin routes to searchTSBs', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'Recall Bulletin 2022{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('Recall Bulletin 2022', 10, 1)
            );
            expect(api.searchComplaints).not.toHaveBeenCalled();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('success path', () => {
        it('passes API response to formatResults and displays the result', async () => {
            const mockTSBResponse: TSBSearchResponse = {
                query: 'tsb engine',
                sanitized_query: 'tsb engine',
                results: [{ nhtsa_id: '1', make: 'FORD', model: 'F-150', year: 2020, component: 'Engine', summary: 'Oil leak' }],
                source: 'TSB',
                total_count: 1, page: 1, total_pages: 1,
            };
            vi.mocked(api.searchTSBs).mockResolvedValue(mockTSBResponse);
            vi.mocked(api.formatResults).mockReturnValue('TSB FOUND: FORD F-150');

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'tsb engine{Enter}');

            await waitFor(() => {
                expect(api.formatResults).toHaveBeenCalledWith(mockTSBResponse);
                expect(screen.getByText('TSB FOUND: FORD F-150')).toBeInTheDocument();
            });
        });

        it('adds the user query as a message immediately after submit', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'check engine light on{Enter}');

            // User message appears synchronously before API resolves
            expect(screen.getByText('check engine light on')).toBeInTheDocument();
        });

        it('clears inputText after submit', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'stalling issue{Enter}');

            // inputText cleared synchronously in handleSearch before await
            expect(input).toHaveValue('');
        });

        it('displays formatted complaint result on searchComplaints success', async () => {
            const complaintResponse: SearchResponse = {
                query: 'brake noise',
                sanitized_query: 'brake noise',
                results: [{ make: 'FORD', model: 'F-150', year: 2019, component: 'Brakes', summary: 'Squealing brakes' }],
                source: 'NHTSA',
                total_count: 1, page: 1, total_pages: 1,
            };
            vi.mocked(api.searchComplaints).mockResolvedValue(complaintResponse);
            vi.mocked(api.formatResults).mockReturnValue('COMPLAINT: Brake squealing');

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'brake noise{Enter}');

            await waitFor(() => {
                expect(api.formatResults).toHaveBeenCalledWith(complaintResponse);
                expect(screen.getByText('COMPLAINT: Brake squealing')).toBeInTheDocument();
            });
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('error path', () => {
        it('calls formatError and displays error when searchComplaints throws', async () => {
            vi.mocked(api.searchComplaints).mockRejectedValue(new Error('Network timeout'));
            vi.mocked(api.formatError).mockReturnValue('ERROR: Network timeout');

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'random failure{Enter}');

            await waitFor(() => {
                expect(api.formatError).toHaveBeenCalledWith(
                    expect.objectContaining({ message: 'Network timeout' })
                );
                expect(screen.getByText('ERROR: Network timeout')).toBeInTheDocument();
            });
        });

        it('calls formatError when searchTSBs throws', async () => {
            vi.mocked(api.searchTSBs).mockRejectedValue(new Error('TSB service down'));
            vi.mocked(api.formatError).mockReturnValue('TSB ERROR: service down');

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'tsb oil change{Enter}');

            await waitFor(() => {
                expect(screen.getByText('TSB ERROR: service down')).toBeInTheDocument();
            });
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('loading state', () => {
        it('shows LoadingState while search is in progress, hides it after', async () => {
            let resolve!: (v: SearchResponse) => void;
            const deferred = new Promise<SearchResponse>((r) => { resolve = r; });
            vi.mocked(api.searchComplaints).mockReturnValueOnce(deferred);

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'brake noise{Enter}');

            // isProcessing=true → LoadingState visible
            expect(screen.getByText(/ANALYZING_DATA_STREAMS/i)).toBeInTheDocument();

            // Resolve promise → isProcessing=false
            act(() => { resolve(COMPLAINT_RESPONSE); });
            await waitFor(() =>
                expect(screen.queryByText(/ANALYZING_DATA_STREAMS/i)).not.toBeInTheDocument()
            );
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('pagination controls', () => {
        it('does not show pagination controls when total_pages is 1', async () => {
            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'brake noise{Enter}');

            await waitFor(() => expect(api.searchComplaints).toHaveBeenCalled());
            expect(screen.queryByRole('button', { name: /NEXT/i })).not.toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /PREV/i })).not.toBeInTheDocument();
        });

        it('shows PREV/NEXT controls when total_pages > 1', async () => {
            vi.mocked(api.searchComplaints).mockResolvedValueOnce({
                ...COMPLAINT_RESPONSE, total_count: 50, page: 1, total_pages: 5,
            });

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'engine knock{Enter}');

            await waitFor(() => expect(screen.getByText(/PAGE/i)).toBeInTheDocument());
            expect(screen.getByRole('button', { name: /NEXT/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /PREV/i })).toBeInTheDocument();
        });

        it('NEXT button calls searchComplaints with page 2', async () => {
            vi.mocked(api.searchComplaints)
                .mockResolvedValueOnce({ ...COMPLAINT_RESPONSE, total_count: 50, page: 1, total_pages: 5 })
                .mockResolvedValueOnce({ ...COMPLAINT_RESPONSE, total_count: 50, page: 2, total_pages: 5 });

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'engine knock{Enter}');

            await waitFor(() => expect(screen.getByRole('button', { name: /NEXT/i })).toBeInTheDocument());
            await user.click(screen.getByRole('button', { name: /NEXT/i }));

            await waitFor(() =>
                expect(api.searchComplaints).toHaveBeenCalledWith('engine knock', 10, 2)
            );
        });

        it('PREV button is disabled on page 1', async () => {
            vi.mocked(api.searchComplaints).mockResolvedValueOnce({
                ...COMPLAINT_RESPONSE, total_count: 50, page: 1, total_pages: 5,
            });

            render(<Home />);
            await switchTab(user, 'Database');

            const input = screen.getByPlaceholderText(/ENTER COMMAND OR SYMPTOMS/i);
            await user.type(input, 'engine knock{Enter}');

            await waitFor(() => expect(screen.getByRole('button', { name: /PREV/i })).toBeInTheDocument());
            expect(screen.getByRole('button', { name: /PREV/i })).toBeDisabled();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('TSB Search tab', () => {
        it('shows TSB-specific placeholder on tsbsearch tab', async () => {
            render(<Home />);
            await switchTab(user, 'TSB Search');

            expect(screen.getByPlaceholderText(/SEARCH TSBs/i)).toBeInTheDocument();
        });

        it('routes queries through searchTSBs from the TSB Search tab when query contains tsb', async () => {
            render(<Home />);
            await switchTab(user, 'TSB Search');

            const input = screen.getByPlaceholderText(/SEARCH TSBs/i);
            await user.type(input, 'tsb power steering{Enter}');

            await waitFor(() =>
                expect(api.searchTSBs).toHaveBeenCalledWith('tsb power steering', 10, 1)
            );
        });
    });
});
