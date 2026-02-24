// Checked AGENTS.md - implementing directly, pure test file
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VehicleForm, { parseDtcInput } from '../components/VehicleForm';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({
    api: {
        fetchVehicles: vi.fn().mockResolvedValue(null),
        fetchVehicleYears: vi.fn().mockResolvedValue(null), // null → fall back to static YEARS
    },
}));

vi.mock('../../lib/vehicles', () => ({
    MAKES: ['CHEVROLET', 'FORD', 'GMC'],
    getModelsForMake: (make: string) =>
        make === 'FORD' ? ['F-150', 'MUSTANG'] :
        make === 'CHEVROLET' ? ['SILVERADO', 'TAHOE'] :
        [],
}));

// ────────────────────────────────────────────────
// parseDtcInput
// ────────────────────────────────────────────────
describe('parseDtcInput', () => {
    it('parses comma-separated codes', () => {
        expect(parseDtcInput('P0300, P0301')).toEqual(['P0300', 'P0301']);
    });

    it('parses space-separated codes', () => {
        expect(parseDtcInput('C1234 B0100')).toEqual(['C1234', 'B0100']);
    });

    it('normalizes lowercase to uppercase', () => {
        expect(parseDtcInput('p0300')).toEqual(['P0300']);
    });

    it('filters out invalid codes', () => {
        expect(parseDtcInput('P0300 NOTACODE HELLO')).toEqual(['P0300']);
    });

    it('returns [] for empty string', () => {
        expect(parseDtcInput('')).toEqual([]);
    });

    it('handles semicolons and mixed separators', () => {
        expect(parseDtcInput('P0300;P0301; B0100')).toEqual(['P0300', 'P0301', 'B0100']);
        expect(parseDtcInput('P0300,P0301;B0100 C1234')).toEqual(['P0300', 'P0301', 'B0100', 'C1234']);
    });
});

// ────────────────────────────────────────────────
// VehicleForm component
// ────────────────────────────────────────────────
describe('VehicleForm', () => {
    const mockOnDiagnose = vi.fn();

    beforeEach(() => {
        mockOnDiagnose.mockClear();
    });

    it('renders YEAR, MAKE, MODEL selects and SYMPTOMS textarea', () => {
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        expect(screen.getByRole('combobox', { name: 'YEAR' })).toBeInTheDocument();
        expect(screen.getByRole('combobox', { name: 'MAKE' })).toBeInTheDocument();
        expect(screen.getByRole('combobox', { name: 'MODEL' })).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/engine shaking at idle/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/P0300, P0301/i)).toBeInTheDocument();
    });

    it('MODEL select is disabled when no make selected', () => {
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        expect(screen.getByRole('combobox', { name: 'MODEL' })).toBeDisabled();
    });

    it('MODEL select is enabled after a make is selected', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        expect(screen.getByRole('combobox', { name: 'MODEL' })).not.toBeDisabled();
    });

    it('MODEL resets to empty when make changes', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        expect(screen.getByRole('combobox', { name: 'MODEL' })).toHaveValue('F-150');

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'CHEVROLET');
        expect(screen.getByRole('combobox', { name: 'MODEL' })).toHaveValue('');
    });

    it('submit button is disabled when fields are empty', () => {
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        expect(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i })).toBeDisabled();
    });

    it('submit button is enabled when all required fields are filled', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        // Select make → model first; year is disabled until both are chosen
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2023');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Engine light on');

        expect(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i })).toBeEnabled();
    });

    it('submit button is disabled when isProcessing is true', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={true} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2023');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Engine light on');

        expect(screen.getByRole('button', { name: /ANALYZING/i })).toBeDisabled();
    });

    it('calls onDiagnose with correct args on submit', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2020');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Transmission slip');
        await user.type(screen.getByPlaceholderText(/P0300, P0301/i), 'P0700');
        await user.click(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i }));

        expect(mockOnDiagnose).toHaveBeenCalledOnce();
        expect(mockOnDiagnose).toHaveBeenCalledWith(
            { make: 'FORD', model: 'F-150', year: 2020 },
            'Transmission slip',
            ['P0700'],
        );
    });

    it('clears symptoms and DTC input after submit', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2020');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Stalling');
        await user.type(screen.getByPlaceholderText(/P0300, P0301/i), 'P0300');
        await user.click(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i }));

        expect(screen.getByPlaceholderText(/engine shaking at idle/i)).toHaveValue('');
        expect(screen.getByPlaceholderText(/P0300, P0301/i)).toHaveValue('');
    });
});

// ────────────────────────────────────────────────
// VehicleForm — dynamic year loading
// ────────────────────────────────────────────────
describe('VehicleForm — dynamic year loading', () => {
    const mockOnDiagnose = vi.fn();

    beforeEach(() => {
        mockOnDiagnose.mockClear();
        vi.mocked(api.fetchVehicles).mockResolvedValue(null);
        vi.mocked(api.fetchVehicleYears).mockResolvedValue(null);
    });

    function yearOptions(select: HTMLElement): string[] {
        return Array.from((select as HTMLSelectElement).options).map((o) => o.value).filter(Boolean);
    }

    it('YEAR select is disabled until make AND model are both chosen', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        expect(screen.getByRole('combobox', { name: 'YEAR' })).toBeDisabled();

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        expect(screen.getByRole('combobox', { name: 'YEAR' })).toBeDisabled();

        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
    });

    it('shows static YEARS when fetchVehicleYears returns null', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(vi.mocked(api.fetchVehicleYears)).toHaveBeenCalledWith('FORD', 'F-150'));

        const opts = yearOptions(screen.getByRole('combobox', { name: 'YEAR' }));
        expect(opts).toContain('2025');
        expect(opts).toContain('1990');
    });

    it('replaces static years with API years when fetchVehicleYears returns data', async () => {
        vi.mocked(api.fetchVehicleYears).mockResolvedValueOnce([2008, 2007, 2006, 2005]);
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(yearOptions(screen.getByRole('combobox', { name: 'YEAR' }))).toContain('2005'));

        const opts = yearOptions(screen.getByRole('combobox', { name: 'YEAR' }));
        expect(opts).toEqual(['2008', '2007', '2006', '2005']);
        // Years outside the API list should NOT appear
        expect(opts).not.toContain('2025');
    });

    it('resets year when make changes', async () => {
        vi.mocked(api.fetchVehicleYears).mockResolvedValueOnce([2009, 2008, 2007]);
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await waitFor(() => expect(screen.getByRole('combobox', { name: 'YEAR' })).not.toBeDisabled());
        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2009');
        expect(screen.getByRole('combobox', { name: 'YEAR' })).toHaveValue('2009');

        // Changing make should reset year and disable it again (model also resets)
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'CHEVROLET');
        expect(screen.getByRole('combobox', { name: 'YEAR' })).toHaveValue('');
        expect(screen.getByRole('combobox', { name: 'YEAR' })).toBeDisabled();
    });
});

// ────────────────────────────────────────────────
// VehicleForm — dynamic vehicle loading
// ────────────────────────────────────────────────
describe('VehicleForm — dynamic vehicle loading', () => {
    const mockOnDiagnose = vi.fn();

    beforeEach(() => {
        mockOnDiagnose.mockClear();
        vi.mocked(api.fetchVehicles).mockResolvedValue(null);
        vi.mocked(api.fetchVehicleYears).mockResolvedValue(null);
    });

    function makeOptions(select: HTMLElement): string[] {
        return Array.from((select as HTMLSelectElement).options).map((o) => o.value).filter(Boolean);
    }

    it('falls back to static MAKES when fetchVehicles returns null', async () => {
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        await waitFor(() => expect(vi.mocked(api.fetchVehicles)).toHaveBeenCalled());
        const opts = makeOptions(screen.getByRole('combobox', { name: 'MAKE' }));
        expect(opts).toContain('FORD');
        expect(opts).toContain('CHEVROLET');
    });

    it('replaces static makes with API makes when fetchVehicles succeeds', async () => {
        vi.mocked(api.fetchVehicles).mockResolvedValueOnce({
            makes: ['HONDA', 'HYUNDAI'],
            models_by_make: { HONDA: ['CIVIC', 'ACCORD'], HYUNDAI: ['ELANTRA', 'SONATA'] },
        });
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        const makeSelect = screen.getByRole('combobox', { name: 'MAKE' });
        await waitFor(() => expect(makeOptions(makeSelect)).toContain('HONDA'));
        expect(makeOptions(makeSelect)).toContain('HYUNDAI');
        expect(makeOptions(makeSelect)).not.toContain('FORD');
    });

    it('shows API models for selected make after dynamic load', async () => {
        vi.mocked(api.fetchVehicles).mockResolvedValueOnce({
            makes: ['HONDA'],
            models_by_make: { HONDA: ['ACCORD', 'CIVIC', 'PILOT'] },
        });
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);
        await waitFor(() => expect(makeOptions(screen.getByRole('combobox', { name: 'MAKE' }))).toContain('HONDA'));
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'HONDA');
        const modelOpts = makeOptions(screen.getByRole('combobox', { name: 'MODEL' }));
        expect(modelOpts).toContain('ACCORD');
        expect(modelOpts).toContain('CIVIC');
        expect(modelOpts).toContain('PILOT');
    });
});
