import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryState } from '../ui/QueryState';

describe('QueryState component', () => {
  it('renders loading indicator when isLoading is true', () => {
    render(
      <QueryState isLoading loadingMessage="Loading test data…">
        <div>Content</div>
      </QueryState>
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Loading test data…')).toBeInTheDocument();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('renders error state and retry button when isError is true', () => {
    const onRetry = vi.fn();
    render(
      <QueryState
        isError
        error={new Error('Connection lost')}
        onRetry={onRetry}
      >
        <div>Content</div>
      </QueryState>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Connection lost')).toBeInTheDocument();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('renders empty state when isEmpty is true', () => {
    render(
      <QueryState isEmpty emptyMessage="No records available.">
        <div>Content</div>
      </QueryState>
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('No records available.')).toBeInTheDocument();
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('renders children when not loading, not error, and not empty', () => {
    render(
      <QueryState>
        <div data-testid="child-content">Operational content loaded</div>
      </QueryState>
    );

    expect(screen.getByTestId('child-content')).toHaveTextContent('Operational content loaded');
  });
});
