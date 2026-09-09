'use client';

import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

interface ErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ShellError({ error, reset }: ErrorBoundaryProps) {
  React.useEffect(() => {
    console.error('Unhandled route error in Railblock Shell:', error);
  }, [error]);

  return (
    <div
      role="alert"
      className="max-w-xl mx-auto my-12 p-6 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] text-[var(--status-critical-text)] font-mono space-y-4 shadow-xl"
    >
      <div className="flex items-center gap-3">
        <AlertCircle className="w-6 h-6 text-[var(--status-critical-fg)] shrink-0" />
        <div>
          <h2 className="text-base font-bold text-[var(--text-primary)]">Operational View Disruption</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            An unhandled runtime exception occurred within this workspace screen.
          </p>
        </div>
      </div>

      <div className="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)] text-xs text-[var(--text-secondary)] break-words">
        {error.message || 'Unknown view render error'}
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex min-h-11 items-center gap-2 px-4 rounded border border-[var(--status-critical-border)] bg-[var(--accent)] text-[var(--bg-canvas)] font-bold text-xs hover:opacity-90 transition-opacity cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Recover View</span>
        </button>
      </div>
    </div>
  );
}
