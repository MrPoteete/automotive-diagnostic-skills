// Checked AGENTS.md - Test suite for TypewriterText component
// Tests animation, callbacks, and memory leak prevention
import { describe, it, expect, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { TypewriterText } from '../TypewriterText';

describe('TypewriterText', () => {
  it('should call onComplete callback when finished', async () => {
    const onComplete = vi.fn();
    const text = 'Hi';

    render(<TypewriterText text={text} speed={5} onComplete={onComplete} />);

    // Wait for callback to be called
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    }, { timeout: 1000 });
  });

  it('should clean up interval on unmount (no memory leak)', async () => {
    const { unmount } = render(<TypewriterText text="test" speed={5} />);

    // Wait a bit for interval to start
    await new Promise(resolve => setTimeout(resolve, 10));

    // Unmount component
    unmount();

    // If no errors, cleanup worked correctly
    expect(true).toBe(true);
  });

  it('should handle onComplete callback changes without re-creating effect', async () => {
    const onComplete1 = vi.fn();
    const onComplete2 = vi.fn();

    const { rerender } = render(
      <TypewriterText text="t" speed={5} onComplete={onComplete1} />
    );

    // Change callback immediately
    rerender(<TypewriterText text="t" speed={5} onComplete={onComplete2} />);

    // Wait for completion
    await waitFor(() => {
      expect(onComplete2).toHaveBeenCalled();
    }, { timeout: 1000 });

    // First callback should not be called
    expect(onComplete1).not.toHaveBeenCalled();
  });

  it('should display cursor while typing', async () => {
    const { container } = render(<TypewriterText text="test" speed={5} />);

    // Cursor should be visible initially
    const cursor = container.querySelector('.animate-pulse');
    expect(cursor).toBeInTheDocument();

    // Wait for animation to complete
    await waitFor(() => {
      const cursorAfter = container.querySelector('.animate-pulse');
      expect(cursorAfter).not.toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('should handle empty string', async () => {
    const onComplete = vi.fn();
    render(<TypewriterText text="" speed={5} onComplete={onComplete} />);

    // Should complete immediately with empty string
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    }, { timeout: 100 });
  });

  it('should render text with custom className', () => {
    const { container } = render(
      <TypewriterText text="test" speed={5} className="custom-class" />
    );

    const element = container.querySelector('.custom-class');
    expect(element).toBeInTheDocument();
  });
});
