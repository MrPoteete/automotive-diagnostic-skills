// Checked AGENTS.md - Test suite for ChecklistModal component.
// Tests open/close, year range, generate flow, download, and error states.
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import type { ChecklistResponse } from '../../../lib/api';
import ChecklistModal from '../ChecklistModal';

vi.mock('../../../lib/api', () => ({
    generateChecklist: vi.fn(),
}));

import { generateChecklist } from '../../../lib/api';

const DEFAULT_PROPS = {
    make: 'FORD',
    model: 'F-150',
    year: 2020,
    isOpen: true,
    onClose: vi.fn(),
};

const MOCK_CHECKLIST: ChecklistResponse = {
    content: '# Pre-Purchase Inspection Checklist\n## 2018-2022 Ford F-150\nSome checks here.',
    filename: 'checklist_FORD_F-150_2018_2022.md',
    make: 'FORD',
    model: 'F-150',
    year_start: 2018,
    year_end: 2022,
};

describe('ChecklistModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        DEFAULT_PROPS.onClose = vi.fn();
    });

    it('renders nothing when isOpen is false', () => {
        render(<ChecklistModal {...DEFAULT_PROPS} isOpen={false} />);
        expect(screen.queryByTestId('checklist-modal')).not.toBeInTheDocument();
    });

    it('renders modal when isOpen is true', () => {
        render(<ChecklistModal {...DEFAULT_PROPS} />);
        expect(screen.getByTestId('checklist-modal')).toBeInTheDocument();
        expect(screen.getByText(/Pre-Purchase Checklist/i)).toBeInTheDocument();
        expect(screen.getByText(/FORD/)).toBeInTheDocument();
        expect(screen.getByText(/F-150/)).toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
        render(<ChecklistModal {...DEFAULT_PROPS} />);
        fireEvent.click(screen.getByTestId('close-checklist-modal'));
        expect(DEFAULT_PROPS.onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when backdrop is clicked', () => {
        const { container } = render(<ChecklistModal {...DEFAULT_PROPS} />);
        const backdrop = container.firstChild as HTMLElement;
        fireEvent.click(backdrop);
        expect(DEFAULT_PROPS.onClose).toHaveBeenCalledTimes(1);
    });

    it('shows year range selects', () => {
        render(<ChecklistModal {...DEFAULT_PROPS} />);
        expect(screen.getByLabelText(/Year Range — Start/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Year Range — End/i)).toBeInTheDocument();
    });

    it('generates checklist on button click', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistModal {...DEFAULT_PROPS} />);
        fireEvent.click(screen.getByRole('button', { name: /Generate Checklist/i }));

        expect(screen.getByRole('button', { name: /Generating checklist/i })).toBeDisabled();

        await waitFor(() => {
            expect(screen.getByText(/Pre-Purchase Inspection Checklist/)).toBeInTheDocument();
        });

        expect(vi.mocked(generateChecklist)).toHaveBeenCalledWith({
            make: 'FORD',
            model: 'F-150',
            year_start: expect.any(Number),
            year_end: expect.any(Number),
        });
    });

    it('shows error when generation fails', async () => {
        vi.mocked(generateChecklist).mockRejectedValue(new Error('Backend offline'));

        render(<ChecklistModal {...DEFAULT_PROPS} />);
        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: /Generate Checklist/i }));
        });

        await waitFor(() => {
            expect(screen.getByText('Backend offline')).toBeInTheDocument();
        });
    });

    it('shows download button after successful generation', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        render(<ChecklistModal {...DEFAULT_PROPS} />);
        fireEvent.click(screen.getByRole('button', { name: /Generate Checklist/i }));

        await waitFor(() => {
            expect(screen.getByText(`Download ${MOCK_CHECKLIST.filename}`)).toBeInTheDocument();
        });
    });

    it('resets state when reopened', async () => {
        vi.mocked(generateChecklist).mockResolvedValue(MOCK_CHECKLIST);

        const { rerender } = render(<ChecklistModal {...DEFAULT_PROPS} />);
        fireEvent.click(screen.getByRole('button', { name: /Generate Checklist/i }));
        await waitFor(() => screen.getByText(/Pre-Purchase Inspection Checklist/));

        // Close and reopen with different year
        rerender(<ChecklistModal {...DEFAULT_PROPS} isOpen={false} />);
        rerender(<ChecklistModal {...DEFAULT_PROPS} isOpen={true} year={2021} />);

        expect(screen.queryByText(/Pre-Purchase Inspection Checklist/)).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Generate Checklist/i })).toBeInTheDocument();
    });
});
