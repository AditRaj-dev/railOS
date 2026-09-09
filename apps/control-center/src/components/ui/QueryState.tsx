'use client';

import React from 'react';
import { AlertCircle, RefreshCw, Inbox } from 'lucide-react';

export interface QueryStateProps {
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | { message?: string } | null;
  isEmpty?: boolean;
  onRetry?: () => void;
  loadingMessage?: string;
  errorMessage?: string;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Shared state boundary primitive across the RailOS desk interface.
 * Implements the loading / error+retry / empty triad.
 *
 * CRITICAL SAFETY REQUIREMENT (DESIGN_SYSTEM.md §12-17):
 * A failed fetch must never render as an empty success state.
 */
export function QueryState({
  isLoading,
  isError,
  error,
  isEmpty,
  onRetry,
  loadingMessage = 'Loading data from Railblock…',
  errorMessage,
  emptyMessage = 'No operational records found.',
  emptyIcon,
  children,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex flex-col items-center justify-center p-8 text-center rounded border border-[var(--border-default)] bg-[var(--bg-panel)] text-[var(--text-secondary)] space-y-3 min-h-[160px]"
      >
        <div className="w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-mono">{loadingMessage}</p>
      </div>
    );
  }

  if (isError) {
    const message =
      errorMessage ||
      (error && typeof error === 'object' && 'message' in error ? String(error.message) : null) ||
      'Failed to load operational data from server.';

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] text-[var(--status-critical-text)]"
      >
        <div className="flex items-start gap-2.5">
          <AlertCircle className="w-5 h-5 mt-0.5 shrink-0 text-[var(--status-critical-fg)]" aria-hidden="true" />
          <div className="text-xs font-mono">
            <span className="font-bold block uppercase tracking-wide">Data Fetch Failure</span>
            <span className="text-[var(--text-primary)] mt-0.5 block">{message}</span>
          </div>
        </div>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex min-h-9 items-center gap-1.5 px-3 rounded border border-[var(--status-critical-border)] bg-[var(--bg-surface)] text-xs font-mono font-bold text-[var(--status-critical-text)] hover:border-[var(--accent)] hover:text-[var(--text-primary)] cursor-pointer shrink-0 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        )}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div
        role="status"
        className="flex flex-col items-center justify-center p-8 text-center rounded border border-[var(--border-subtle)] bg-[var(--bg-panel)] text-[var(--text-muted)] space-y-2 min-h-[140px]"
      >
        {emptyIcon || <Inbox className="w-8 h-8 text-[var(--text-muted)]" aria-hidden="true" />}
        <p className="text-xs font-mono text-[var(--text-secondary)]">{emptyMessage}</p>
      </div>
    );
  }

  return <>{children}</>;
}
