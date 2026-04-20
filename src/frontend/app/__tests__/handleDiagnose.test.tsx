// Checked AGENTS.md - implementing directly, pure test file
// Updated for new two-step VehicleIdentification + symptoms flow.
// Generated via Gemini 2.5 Flash (GEMINI_WORKFLOW.md), corrected by Claude.

// IMPORTANT ESBUILD RULE: Type/interface declarations must come BEFORE vi.mock() calls
// to avoid forward reference issues with esbuild's top-to-bottom processing.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Home from '../page';
import type { DiagnoseResponse, VehicleInfo } from '../../lib/api';

type VehicleIdentity = {
    vin?: string;
    year: number;
    make: string;
    model: string;
    engine?: string;
    engine_model?: string;
    drive_type?: string;
};

type OnVehicleSelected = (vehicle: VehicleIdentity) => void;

// Mock TypewriterText to render text immediately (bypasses setInterval delay)
vi.mock('../components/TypewriterText', () => ({
    TypewriterText: ({ text }: { text: string }) => <div>{text}</div>,
}));

// VehicleIdentification mock captures onVehicleSelected so tests can trigger vehicle selection directly
let capturedOnVehicleSelected!: OnVehicleSelected;

vi.mock('../components/VehicleIdentification', () => ({
    default: ({ onVehicleSelected }: { onVehicleSelected: OnVehicleSelected }) => {
        capturedOnVehicleSelected = onVehicleSelected;
        return <div data-testid="vehicle-identification-mock" />;
    },
}));

// VehicleForm — only parseDtcInput is used now; vi.fn() so tests can override return value
vi.mock('../components/VehicleForm', () => ({
    default: () => null,
    parseDtcInput: vi.fn((_raw: string) => [] as string[]),
}));

// Mock full api module
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
        fetchVin: vi.fn(),
    },
    fetchVin: vi.fn(),
    fetchDashboard: vi.fn().mockResolvedValue(null),
    fetchHistory: vi.fn().mockResolvedValue(null),
    saveHistory: vi.fn().mockResolvedValue(null),
}));

import { api } from '../../lib/api';

// ────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────

function makeDeferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
}

const MOCK_IDENTITY: VehicleIdentity = { make: 'FORD', model: 'F-150', year: 2020 };
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

/** Render Home, select vehicle, fill symptoms, return the Run Diagnostic button. */
async function setupWithVehicleAndSymptoms(symptomsText: string = MOCK_SYMPTOMS) {
    const user = userEvent.setup();
    render(<Home />);

    act(() => { capturedOnVehicleSelected(MOCK_IDENTITY); });

    const textarea = await screen.findByLabelText(/symptoms/i);
    await user.type(textarea, symptomsText);

    return { user, textarea, button: screen.getByRole('button', { name: /run diagnostic/i }) };
}

// ────────────────────────────────────────────────────────────────
describe('handleDiagnose — routing and behavior', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(api.healthCheck).mockResolvedValue({ status: 'ok', message: 'Online' });
        vi.mocked(api.diagnose).mockResolvedValue(DIAG_RESPONSE);
        vi.mocked(api.formatDiagnosis).mockReturnValue('DIAGNOSIS: Engine misfire');
        vi.mocked(api.formatError).mockReturnValue('ERROR: network error');
        vi.mocked(api.fetchVehicles).mockResolvedValue(null);
        vi.mocked(api.fetchVehicleYears).mockResolvedValue([]);
    });

    // ────────────────────────────────────────────────────────────
    describe('api call arguments', () => {
        it('calls api.diagnose with correct vehicle, symptoms, dtc_codes args (no DTCs)', async () => {
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

            expect(vi.mocked(api.diagnose)).toHaveBeenCalledWith({
                vehicle: MOCK_VEHICLE,
                symptoms: MOCK_SYMPTOMS,
                dtc_codes: [],
            });
        });

        it('passes engine_model from VehicleIdentity to api.diagnose vehicle payload', async () => {
            const identityWithEngine: VehicleIdentity = {
                make: 'CHEVROLET', model: 'TRAVERSE', year: 2017,
                engine_model: 'LFY',
            };
            const { user } = await setupWithVehicleAndSymptoms();

            // Re-select vehicle with engine_model
            act(() => { capturedOnVehicleSelected(identityWithEngine); });

            const textarea = screen.getByLabelText(/symptoms/i);
            await user.clear(textarea);
            await user.type(textarea, MOCK_SYMPTOMS);

            const button = screen.getByRole('button', { name: /run diagnostic/i });
            await user.click(button);

            await waitFor(() => {
                expect(vi.mocked(api.diagnose)).toHaveBeenCalledWith(
                    expect.objectContaining({
                        vehicle: expect.objectContaining({ engine_model: 'LFY' }),
                    })
                );
            });
        });

        it('omits engine_model from api.diagnose vehicle payload when not set', async () => {
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

            await waitFor(() => {
                const callArg = vi.mocked(api.diagnose).mock.calls[0][0];
                expect(callArg.vehicle).not.toHaveProperty('engine_model');
            });
        });

        it('passes DTC codes through to api.diagnose and includes them in user message', async () => {
            // Override parseDtcInput for this test to return real codes
            const { parseDtcInput } = vi.mocked(await import('../components/VehicleForm'));
            (parseDtcInput as ReturnType<typeof vi.fn>).mockReturnValueOnce(['P0300', 'P0301']);

            const { user, button } = await setupWithVehicleAndSymptoms();

            // Type DTC codes into the DTC input
            const dtcInput = screen.getByPlaceholderText(/P0300/i);
            await user.type(dtcInput, 'P0300,P0301');

            await user.click(button);

            expect(vi.mocked(api.diagnose)).toHaveBeenCalledWith({
                vehicle: MOCK_VEHICLE,
                symptoms: MOCK_SYMPTOMS,
                dtc_codes: ['P0300', 'P0301'],
            });
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('success path', () => {
        it('appends user query message before API resolves', async () => {
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

            expect(screen.getByText(
                `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${MOCK_SYMPTOMS}`
            )).toBeInTheDocument();
        });

        it('calls formatDiagnosis with API response and displays result', async () => {
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

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

            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);
            await waitFor(() => expect(screen.getByText('DIAGNOSIS: Engine misfire')).toBeInTheDocument());

            // Second diagnosis — type new symptoms
            const textarea = screen.getByLabelText(/symptoms/i);
            await user.clear(textarea);
            await user.type(textarea, symptoms2);
            await user.click(screen.getByRole('button', { name: /run diagnostic/i }));

            await waitFor(() => {
                expect(screen.getByText(
                    `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${symptoms2}`
                )).toBeInTheDocument();
                expect(screen.getByText('DIAGNOSIS: Alignment issue')).toBeInTheDocument();
            });

            expect(screen.getByText(
                `${MOCK_VEHICLE.year} ${MOCK_VEHICLE.make} ${MOCK_VEHICLE.model} — ${MOCK_SYMPTOMS}`
            )).toBeInTheDocument();
        });
    });

    // ────────────────────────────────────────────────────────────
    describe('error path', () => {
        it('calls formatError when api.diagnose rejects', async () => {
            vi.mocked(api.diagnose).mockRejectedValue(new Error('network error'));
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

            await waitFor(() => {
                expect(vi.mocked(api.formatError)).toHaveBeenCalledWith(
                    expect.objectContaining({ message: 'network error' })
                );
            });
        });

        it('displays formatted error message in chat when api.diagnose rejects', async () => {
            vi.mocked(api.diagnose).mockRejectedValue(new Error('network error'));
            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

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

            const { user, button } = await setupWithVehicleAndSymptoms();
            await user.click(button);

            expect(screen.getByText(/ANALYZING_DATA_STREAMS/i)).toBeInTheDocument();

            await act(async () => { resolve(DIAG_RESPONSE); });
            await waitFor(() =>
                expect(screen.queryByText(/ANALYZING_DATA_STREAMS/i)).not.toBeInTheDocument()
            );
        });

        it('disables the Run Diagnostic button while isProcessing is true', async () => {
            const { promise, resolve } = makeDeferred<DiagnoseResponse>();
            vi.mocked(api.diagnose).mockReturnValue(promise);

            const { user, button } = await setupWithVehicleAndSymptoms();
            expect(button).not.toBeDisabled();

            await user.click(button);
            expect(button).toBeDisabled();

            await act(async () => { resolve(DIAG_RESPONSE); });
            await waitFor(() => expect(button).not.toBeDisabled());
        });
    });
});
