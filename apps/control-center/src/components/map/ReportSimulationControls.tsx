'use client';

import { Pause, Play, RotateCcw, TriangleAlert } from 'lucide-react';

interface Props {
  running: boolean; hasTrackGeometry: boolean; activeCount: number;
  onPause: () => void; onResume: () => void; onReset: () => void;
}

export function ReportSimulationControls(props: Props) {
  const message = props.hasTrackGeometry
    ? `${props.activeCount} active simulated reports · ${props.running ? 'running' : 'paused'}`
    : 'Simulation waiting for track geometry';
  return (
    <div className="flex items-center gap-2 rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[10px] font-mono text-[var(--text-secondary)]">
      <TriangleAlert aria-hidden="true" className="h-3.5 w-3.5 text-[var(--status-warning-fg)]" />
      <span role="status" aria-live="polite">{message}</span>
      <button type="button" onClick={props.running ? props.onPause : props.onResume} disabled={!props.hasTrackGeometry} aria-label={props.running ? 'Pause report simulation' : 'Resume report simulation'} className="rounded p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info-fg)] disabled:opacity-50">
        {props.running ? <Pause aria-hidden="true" className="h-3.5 w-3.5" /> : <Play aria-hidden="true" className="h-3.5 w-3.5" />}
      </button>
      <button type="button" onClick={props.onReset} aria-label="Reset report simulation" className="rounded p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info-fg)]">
        <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
