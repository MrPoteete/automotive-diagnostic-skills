// Checked AGENTS.md - Test suite for ChecklistPanel component (pre-purchase tab).
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import type { ChecklistResponse } from '../../../lib/api';
import ChecklistPanel from '../ChecklistPanel';

vi.mock('../../../lib/api', () => ({
    generateChecklist: vi.fn(),
}));

vi.mock('../../../lib/vehicles', () => ({
    MAKES: ['FORD', 'CHEVROLET', 'HONDA'],
    YEARS: [2005, 2010, 2015, 2018, 2019, 2020, 2021, 2022, 2025],
    getModelsForMake: (make: string) => {
        if (make === 'FORD') return ['ESCAPE', 'F-150', 'EXPLORER'];
        if (make === 'CHEVROLET') return ['EQUINOX', 'SILVERADO'];
        return ['CR-V', 'CIVIC'];
    },
}));

import { generateChecklist } from '../../../lib/api';

const MOCK_CHECKLIST: ChecklistResponse = {
    content: '# Pre-Purchase Inspection Checklist\n## 2018-2022 Ford Escape\nSome checks.',
    filename: 'checklist_FORD_ESCAPE_2018_2022.md',
    make: 'FORD',
    model: 'ESCAPE',
    year_start: 2018,
    year_end: 2022,
    data: {
        make: 'FORD',
        model: 'ESCAPE',
        year_start: 2018,
        year_end: 2022,
        generated_at: '2026-03-18',
        has_park_it: false,
        recalls: [
            {
                campaign_no: '20V123000',
                component: 'AIR BAGS',
                summary: 'Airbag may not deploy.',
                park_it: false,
                year_from: 2018,
                year_to: 2022,
            },
        ],
        sections: [
            {
                component: 'ENGINE',
                complaint_count: 1234,
                checks: [
                    'Check for oil leaks.',
                    'Inspect oil condition.',
                    'Listen for abnormal noises.',
                ],
            },
            {
                component: 'BRAKES',
                complaint_count: 567,
                checks: [
                    'Measure brake pad thickness.',
                    'Inspect rotors.',
                ],
            },
        ],
        tsbs: [
            {
                bulletin_no: 'SSM-50123',
                component: 'ENGINE',
                summary: 'Engine may exhibit rough idle.',
            },
        ],
        standard_checks: [
            'VIN matches title and door jamb sticker',
            'CarFax/AutoCheck report reviewed',
        ],
    },
};

const MOCK_CHECKLIST_WITH_PARK_IT: ChecklistResponse = {
    ...MOCK_CHECKLIST,
    data: {
        ...MOCK_CHECKLIST.data,
        has_park_it: true,
        recalls: [
            {
                campaign_no: '21V456000',
                component: 'FUEL SYSTEM',
                summary: 'Fuel leak fire risk.',
                park_it: true,
                year_from: 2019,
                year_to: 2021,
            },
        ],
    },
};

describe('ChecklistPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the panel with vehicle selector', () => {
        render(<ChecklistPanel />);
        expect(screen.getByTestId('checklist-panel')).toBeInTheDocument();
        expect(screen.getByLabelText('Make')).toBeInTheDocument();
        expect(screen.getByLabelText('Model')).toBeInTheDocument();
        expect(screen.getByLabelText('Year — Start')).toBeInTheDocument();
        expect(screen.getByLabelText('Year — End')).toBeInTheDocument();
    });

    it('disables Generate button until make and model are selected', () => {
        render(<ChecklistPanel />);
        expect(screen.getByTestId('generate-checklist-btn')).toBeDisabled();
    });

    it('enables Generate button after make and model are selected', () => {
        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        expect(screen.getByTestId('generate-checklist-btn')).toBeEnabled();
    });

    it('shows loading state while generating', async () => {
        let resolve!: (v: ChecklistResponse) => void;
        vi.mocked(generateChecklist).mockReturnValue(new Promise((r) => { resolve = r; }));

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        expect(screen.getByTestId('checklist-loading')).toBeInTheDocument();

        await act(async () => { resolve(MOCK_CHECKLIST); });
        await waitFor(() => {
            expect(screen.queryByTestId('checklist-loading')).not.toBeInTheDocument();
        });
    });

    it('renders checklist sections after successful generation', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('checklist-rendered')).toBeInTheDocument();
        });

        // Recalls section
        expect(screen.getByText('20V123000')).toBeInTheDocument();
        expect(screen.getByText('AIR BAGS')).toBeInTheDocument();

        // Inspection priorities — "Engine" appears in multiple places; check count badge
        expect(screen.getByText('1,234 complaints')).toBeInTheDocument();
        expect(screen.getByText('Check for oil leaks.')).toBeInTheDocument();
        expect(screen.getByText('Measure brake pad thickness.')).toBeInTheDocument();

        // TSBs
        expect(screen.getByText('SSM-50123')).toBeInTheDocument();

        // Standard checks
        expect(screen.getByText('VIN matches title and door jamb sticker')).toBeInTheDocument();
    });

    it('shows download buttons after generation', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('download-md-btn')).toBeInTheDocument();
            expect(screen.getByTestId('download-pdf-btn')).toBeInTheDocument();
        });
    });

    it('shows park-it DO NOT DRIVE banner when recall has park_it flag', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST_WITH_PARK_IT);

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        await waitFor(() => {
            expect(screen.getByTestId('park-it-banner')).toBeInTheDocument();
        });
    });

    it('shows error message when generation fails', async () => {
        vi.mocked(generateChecklist).mockRejectedValue(new Error('Backend offline'));

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        await act(async () => {
            fireEvent.click(screen.getByTestId('generate-checklist-btn'));
        });

        await waitFor(() => {
            expect(screen.getByText('Backend offline')).toBeInTheDocument();
        });
    });

    it('clears result when Clear button is clicked', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        await waitFor(() => screen.getByTestId('checklist-rendered'));

        fireEvent.click(screen.getByRole('button', { name: /clear/i }));
        expect(screen.queryByTestId('checklist-rendered')).not.toBeInTheDocument();
    });

    it('resets model when make changes', () => {
        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'HONDA' } });

        // Model select should reset to empty
        expect((screen.getByLabelText('Model') as HTMLSelectElement).value).toBe('');
    });

    it('calls generateChecklist with correct params', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistPanel />);
        fireEvent.change(screen.getByLabelText('Make'), { target: { value: 'FORD' } });
        fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'ESCAPE' } });
        fireEvent.change(screen.getByLabelText('Year — Start'), { target: { value: '2018' } });
        fireEvent.change(screen.getByLabelText('Year — End'), { target: { value: '2022' } });
        fireEvent.click(screen.getByTestId('generate-checklist-btn'));

        await waitFor(() => {
            expect(vi.mocked(generateChecklist)).toHaveBeenCalledWith({
                make: 'FORD',
                model: 'ESCAPE',
                year_start: 2018,
                year_end: 2022,
            });
        });
    });
});
