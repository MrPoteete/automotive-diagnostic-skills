// Checked AGENTS.md - Gemini Flash generated test setup
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock Next.js navigation for tests
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  })),
}));

// Mock Next.js fonts (they don't work in test environment)
vi.mock('next/font/google', () => ({
  Rajdhani: vi.fn(() => ({
    variable: '--font-rajdhani',
    className: 'font-rajdhani',
  })),
  Orbitron: vi.fn(() => ({
    variable: '--font-orbitron',
    className: 'font-orbitron',
  })),
  Roboto_Mono: vi.fn(() => ({
    variable: '--font-roboto-mono',
    className: 'font-roboto-mono',
  })),
}));
