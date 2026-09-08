import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ReportSimulationControls } from '../ReportSimulationControls';

describe('ReportSimulationControls', () => {
  it('exposes count, pause, and reset as text controls', () => {
    const pause = vi.fn(); const reset = vi.fn();
    render(<ReportSimulationControls running hasTrackGeometry activeCount={3} onPause={pause} onResume={vi.fn()} onReset={reset} />);
    expect(screen.getByRole('status')).toHaveTextContent('3 active simulated reports');
    fireEvent.click(screen.getByRole('button', { name: 'Pause report simulation' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reset report simulation' }));
    expect(pause).toHaveBeenCalledOnce(); expect(reset).toHaveBeenCalledOnce();
  });
  it('announces missing track geometry', () => {
    render(<ReportSimulationControls running hasTrackGeometry={false} activeCount={0} onPause={vi.fn()} onResume={vi.fn()} onReset={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent('waiting for track geometry');
  });
});
