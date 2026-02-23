// Checked AGENTS.md - implementing directly, pure test file
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VehicleForm, { parseDtcInput } from '../components/VehicleForm';

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

        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2023');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Engine light on');

        expect(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i })).toBeEnabled();
    });

    it('submit button is disabled when isProcessing is true', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={true} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2023');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Engine light on');

        expect(screen.getByRole('button', { name: /ANALYZING/i })).toBeDisabled();
    });

    it('calls onDiagnose with correct args on submit', async () => {
        const user = userEvent.setup();
        render(<VehicleForm onDiagnose={mockOnDiagnose} isProcessing={false} />);

        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2020');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
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

        await user.selectOptions(screen.getByRole('combobox', { name: 'YEAR' }), '2020');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MAKE' }), 'FORD');
        await user.selectOptions(screen.getByRole('combobox', { name: 'MODEL' }), 'F-150');
        await user.type(screen.getByPlaceholderText(/engine shaking at idle/i), 'Stalling');
        await user.type(screen.getByPlaceholderText(/P0300, P0301/i), 'P0300');
        await user.click(screen.getByRole('button', { name: /INITIATE DIAGNOSTIC SCAN/i }));

        expect(screen.getByPlaceholderText(/engine shaking at idle/i)).toHaveValue('');
        expect(screen.getByPlaceholderText(/P0300, P0301/i)).toHaveValue('');
    });
});
