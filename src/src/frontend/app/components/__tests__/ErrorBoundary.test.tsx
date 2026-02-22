// Checked AGENTS.md - Test suite for Error Boundary
// Tests error catching, fallback UI, and recovery
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundaryWrapper from '../ErrorBoundary';
import { useRouter } from 'next/navigation';

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  // Suppress console.error during tests (ErrorBoundary logs errors)
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it('should render children when no error occurs', () => {
    render(
      <ErrorBoundaryWrapper>
        <div>Test content</div>
      </ErrorBoundaryWrapper>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should catch errors and display fallback UI', () => {
    render(
      <ErrorBoundaryWrapper>
        <ThrowError shouldThrow={true} />
      </ErrorBoundaryWrapper>
    );

    expect(screen.getByText(/SYSTEM_CRITICAL_FAILURE/i)).toBeInTheDocument();
    expect(screen.getByText(/critical system malfunction/i)).toBeInTheDocument();
  });

  it('should display error details in fallback UI', () => {
    render(
      <ErrorBoundaryWrapper>
        <ThrowError shouldThrow={true} />
      </ErrorBoundaryWrapper>
    );

    // Error details should be in a collapsible section
    const details = screen.getByText(/Error Details/i);
    expect(details).toBeInTheDocument();
  });

  it('should call router.refresh() when reset button is clicked', () => {
    const mockRefresh = vi.fn();
    vi.mocked(useRouter).mockReturnValue({
      refresh: mockRefresh,
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
    } as any);

    render(
      <ErrorBoundaryWrapper>
        <ThrowError shouldThrow={true} />
      </ErrorBoundaryWrapper>
    );

    const resetButton = screen.getByRole('button', { name: /Initiate System Reset/i });
    fireEvent.click(resetButton);

    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it('should log errors to console', () => {
    const consoleSpy = vi.spyOn(console, 'error');

    render(
      <ErrorBoundaryWrapper>
        <ThrowError shouldThrow={true} />
      </ErrorBoundaryWrapper>
    );

    expect(consoleSpy).toHaveBeenCalled();
  });
});
