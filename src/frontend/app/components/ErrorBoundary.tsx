// Checked AGENTS.md - Gemini Flash generated, Claude reviewing for quality
// Error Boundary component for graceful error handling
'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Rajdhani } from 'next/font/google';

const rajdhani = Rajdhani({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-rajdhani',
  display: 'swap',
});

interface ErrorBoundaryProps {
  children: ReactNode;
  resetRouter?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Class Component acting as an Error Boundary.
 * Catches JavaScript errors anywhere in its child component tree,
 * logs those errors, and displays a fallback UI.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  resetErrorBoundary = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.resetRouter) {
      this.props.resetRouter();
    } else {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className={`${rajdhani.variable} font-rajdhani min-h-screen flex items-center justify-center bg-cyber-dark text-white p-4`}
        >
          <div
            className="text-center border-2 border-cyber-pink p-8 rounded-lg shadow-neon shadow-cyber-pink max-w-md w-full animate-pulse-border"
          >
            <h1 className="text-5xl font-bold text-cyber-pink mb-4 tracking-wider uppercase">
              SYSTEM_CRITICAL_FAILURE
            </h1>
            <p className="text-xl mb-6 text-gray-300">
              A critical system malfunction has occurred.
            </p>
            <p className="text-lg mb-8 text-gray-400">
              Please initiate a system reboot or contact your local netrunner.
            </p>
            {this.state.error && (
              <details className="text-left bg-gray-900 p-4 rounded-md mb-6 text-sm text-gray-500">
                <summary className="cursor-pointer text-cyber-pink hover:text-white">
                  Error Details (for debugging)
                </summary>
                <pre className="whitespace-pre-wrap break-words mt-2">
                  {this.state.error.message}
                  {this.state.error.stack && `\n\n${this.state.error.stack}`}
                </pre>
              </details>
            )}
            <button
              onClick={this.resetErrorBoundary}
              className="bg-cyber-pink text-cyber-dark font-bold py-3 px-6 rounded-md text-lg uppercase tracking-wider
                         hover:bg-white hover:text-cyber-pink transition-all duration-300 transform hover:scale-105
                         shadow-neon-button shadow-cyber-pink"
            >
              Initiate System Reset
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Functional wrapper component to provide Next.js `useRouter` hook
 * functionality to the class-based ErrorBoundary.
 */
export default function ErrorBoundaryWrapper({ children }: { children: ReactNode }) {
  const router = useRouter();

  return <ErrorBoundary resetRouter={router.refresh}>{children}</ErrorBoundary>;
}
