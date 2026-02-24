// Checked AGENTS.md - implementing directly, pure test file
// Generated via Gemini 2.5 Flash (GEMINI_WORKFLOW.md — boilerplate delegation), reviewed by Claude.

// IMPORTANT ESBUILD RULE: Type/interface declarations must come BEFORE vi.mock() calls
// to avoid forward reference issues with esbuild's top-to-bottom processing.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from '../page';
import type { DiagnoseResponse, VehicleInfo } from '../../lib/api';

type OnDiagnose = (vehicle: VehicleInfo, symptoms: string, dtcCodes: string[]) => void;

// Mock TypewriterText to render text immediately (bypasses setInterval delay)
vi.mock('../components/TypewriterText', () => ({
    TypewriterText: ({ text }: { text: string }) => <div>{text}</div>,
}));

// CRITICAL — VehicleForm mock captures the onDiagnose callback via stored reference
// so individual tests can invoke handleDiagnose without needing real dropdown interactions.
let capturedOnDiagnose!: OnDiagnose;

vi.mock('../components/VehicleForm', () => ({
    default: ({ onDiagnose, isProcessing }: { onDiagnose: OnDiagnose; isProcessing: boolean }) => {
        capturedOnDiagnose = onDiagnose;
        return (
            <button
                data-testid="trigger-diagnose"
                disabled={isProcessing}
                onClick={() => capturedOnDiagnose(
                    { make: 'FORD', model: 'F-150', year: 2020 },
                    'engine shaking at idle',
                    []
                )}
            >
                DIAGNOSE
            </button>
        );
    },
    parseDtcInput: (_raw: string) => [],
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
    },
}));

import { api } from '../../lib/api';

// ────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────

/** Create a manually-resolvable promise for testing loading states. */
function makeDeferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
}

const MOCK_VEHICLE: VehicleInfo = { make: 'FORD', model: 'F-150', year: 2020 };
const MOCK_SYMPTOMS = 'engine shaking at idle';

const DIAG_RESPONSE: DiagnoseResponse = {
    vehicle: MOCK_VEHICLE,
    symptoms: MOCK_SYMPTOMS,
    dtc_codes: [],
    candidates: [],
    warnings: [],
    data_sources: {},
};

// ────────────────────────────────────────────────────────────────
describe('handleDiagnose — routing and behavior', () => {
    let user: ReturnType<typeof userEvent.setup>;

    beforeEach(() => {
        vi.clearAllMocks();
        user = userEvent.setup();
        // healthCheck resolves by default (fires in useEffect on mount)
        vi.mocked(api.healthCheck).mockResolvedValue({ status: 'ok', message: 'Online' });
        vi.mocked(api.diagnose).mockResolvedValue(DIAG_RESPONSE);
        vi.mocked(api.formatDiagnosis).mockReturnValue('DIAGNOSIS: Engine misfire');
        vi.mocked(api.formatError).mockReturnValue('ERROR: network error');
        // fetchVehicles is called inside real VehicleForm useEffect — our mock
        // doesn't run that hook, but define the method to prevent undefined errors.
        vi.mocked(api.fetchVehicles).mockResolvedValue(null);
    });

    // ────────────────────────────────────────────────────────────
    describe('api call arguments', () => {
        it('calls api.diagnose with correct vehicle, symptoms, dtc_codes args (no DTCs)', async () => {
            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            expect(vi.mocked(api.diagnose)).toHaveBeenCalledWith({
                vehicle: MOCK_VEHICLE,
                symptoms: MOCK_SYMPTOMS,
                dtc_codes: [],
            });
        });

        it('passes DTC codes through to api.diagnose and includes them in user message', async () => {
            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, ['P0300', 'P0301']);
            });

            expect(vi.mocked(api.diagnose)).toHaveBeenCalledWith({
                vehicle: MOCK_VEHICLE,
                symptoms: MOCK_SYMPTOMS,
                dtc_codes: ['P0300', 'P0301'],
            });

            // User message includes DTC label
            expect(screen.getByText(
                `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${MOCK_SYMPTOMS} [P0300, P0301]`
            )).toBeInTheDocument();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('success path', () => {
        it('appends user query message before API resolves', async () => {
            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            expect(screen.getByText(
                `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${MOCK_SYMPTOMS}`
            )).toBeInTheDocument();
        });

        it('calls formatDiagnosis with API response and displays result', async () => {
            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            await waitFor(() => {
                expect(vi.mocked(api.formatDiagnosis)).toHaveBeenCalledWith(DIAG_RESPONSE);
                expect(screen.getByText('DIAGNOSIS: Engine misfire')).toBeInTheDocument();
            });
        });

        it('shows both user messages after two sequential diagnoses', async () => {
            const symptoms2 = 'car pulls to the left';
            vi.mocked(api.diagnose)
                .mockResolvedValueOnce(DIAG_RESPONSE)
                .mockResolvedValueOnce({ ...DIAG_RESPONSE, symptoms: symptoms2 });
            vi.mocked(api.formatDiagnosis)
                .mockReturnValueOnce('DIAGNOSIS: Engine misfire')
                .mockReturnValueOnce('DIAGNOSIS: Alignment issue');

            render(<Home />);

            // First diagnosis
            await act(async () => { capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []); });
            await waitFor(() => expect(screen.getByText('DIAGNOSIS: Engine misfire')).toBeInTheDocument());

            // Second diagnosis
            await act(async () => { capturedOnDiagnose(MOCK_VEHICLE, symptoms2, []); });
            await waitFor(() => {
                expect(screen.getByText(
                    `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${symptoms2}`
                )).toBeInTheDocument();
                expect(screen.getByText('DIAGNOSIS: Alignment issue')).toBeInTheDocument();
            });

            // Original messages still present
            expect(screen.getByText(
                `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${MOCK_SYMPTOMS}`
            )).toBeInTheDocument();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('error path', () => {
        it('calls formatError when api.diagnose rejects', async () => {
            vi.mocked(api.diagnose).mockRejectedValue(new Error('network error'));

            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            await waitFor(() => {
                expect(vi.mocked(api.formatError)).toHaveBeenCalledWith(
                    expect.objectContaining({ message: 'network error' })
                );
            });
        });

        it('displays formatted error message in chat when api.diagnose rejects', async () => {
            vi.mocked(api.diagnose).mockRejectedValue(new Error('network error'));

            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            await waitFor(() => {
                expect(screen.getByText('ERROR: network error')).toBeInTheDocument();
            });
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('loading state', () => {
        it('shows LoadingState while diagnosis is in progress, hides it after', async () => {
            const { promise, resolve } = makeDeferred<DiagnoseResponse>();
            vi.mocked(api.diagnose).mockReturnValue(promise);

            render(<Home />);
            await act(async () => {
                capturedOnDiagnose(MOCK_VEHICLE, MOCK_SYMPTOMS, []);
            });

            // isProcessing=true → LoadingState visible
            expect(screen.getByText(/ANALYZING_DATA_STREAMS/i)).toBeInTheDocument();

            // Resolve → isProcessing=false → LoadingState gone
            await act(async () => { resolve(DIAG_RESPONSE); });
            await waitFor(() =>
                expect(screen.queryByText(/ANALYZING_DATA_STREAMS/i)).not.toBeInTheDocument()
            );
        });

        it('disables the trigger button while isProcessing is true', async () => {
            const { promise, resolve } = makeDeferred<DiagnoseResponse>();
            vi.mocked(api.diagnose).mockReturnValue(promise);

            render(<Home />);
            const btn = screen.getByTestId('trigger-diagnose');

            // Initially enabled
            expect(btn).not.toBeDisabled();

            await user.click(btn);

            // isProcessing=true → button disabled
            expect(btn).toBeDisabled();

            await act(async () => { resolve(DIAG_RESPONSE); });
            await waitFor(() => expect(btn).not.toBeDisabled());
        });
    });
});
