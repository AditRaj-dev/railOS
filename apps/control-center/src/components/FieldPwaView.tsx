'use client';

import React from 'react';
import Link from 'next/link';
import { AlertCircle, Eye, RefreshCw, Smartphone } from 'lucide-react';
import { useMyPossessions } from '../lib/queries';
import { useRailOSEventStream } from '../lib/useRailOSEventStream';
import { StatusChip } from './StatusChip';
import { getTokenDef, POSSESSION_STATE_TOKENS } from './tokens';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

function formatUtc(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

/**
 * Desk-side, read-only mirror of the field possession state. Field crews use
 * the operational PWA; control staff can observe the same server state here.
 */
export const FieldPwaView: React.FC = () => {
  useRailOSEventStream();
  const possessions = useMyPossessions();

  return (
    <div className="space-y-4" aria-labelledby="field-monitor-title">
      <header className="flex flex-wrap items-start justify-between gap-3 rounded border border-slate-800 bg-slate-900/80 p-4">
        <div className="flex items-start gap-3">
          <span className="rounded border border-amber-700/70 bg-amber-950/30 p-2 text-amber-300" aria-hidden="true"><Smartphone className="h-5 w-5" /></span>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-amber-300">Field operations</p>
            <h1 id="field-monitor-title" className="mt-1 text-lg font-semibold text-white">Read-only field monitor</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-400">
              Observe possession windows, safety state, and handback readiness. Field updates are made in the Field Crew app and arrive here from the RailOS API.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void possessions.refetch()}
          className="inline-flex min-h-11 items-center gap-2 rounded border border-slate-700 px-3 text-sm text-slate-200 hover:border-amber-400 hover:text-amber-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300"
          aria-label="Refresh field monitor"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-2 rounded border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400" role="status">
        <Eye className="h-4 w-4 text-emerald-300" aria-hidden="true" />
        <span>Read-only mirror · Live event stream enabled</span>
        <span className="ml-auto font-mono text-slate-500">{possessions.data?.count ?? 0} possessions</span>
      </div>

      {possessions.isLoading && <p className="rounded border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300" role="status">Loading field state…</p>}
      {possessions.isError && (
        <div className="flex items-start gap-2 rounded border border-red-900/80 bg-red-950/40 p-4 text-sm text-red-200" role="alert">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Field state could not be loaded. {possessions.error?.message || 'Try again.'}</span>
        </div>
      )}

      {possessions.data && (
        <section className="rounded border border-slate-800 bg-slate-950 p-4" aria-labelledby="field-possession-title">
          <div className="mb-3">
            <h2 id="field-possession-title" className="text-sm font-semibold text-white">Possession windows visible to this role</h2>
            <p className="mt-1 text-xs text-slate-500">Actions are intentionally unavailable in this monitor.</p>
          </div>
          <Table caption="Field possession monitor">
            <TableHeader><tr>
              <TableHeaderCell>Possession</TableHeaderCell>
              <TableHeaderCell>Section / track</TableHeaderCell>
              <TableHeaderCell>Department</TableHeaderCell>
              <TableHeaderCell>State</TableHeaderCell>
              <TableHeaderCell>Window</TableHeaderCell>
              <TableHeaderCell>Handback</TableHeaderCell>
            </tr></TableHeader>
            <TableBody>
              {possessions.data.items.map((possession) => {
                const token = getTokenDef(POSSESSION_STATE_TOKENS, possession.state);
                const pending = possession.handbackChecklist.filter((item) => !item.satisfied).length;
                return (
                  <tr key={possession.possessionId} className="border-b border-slate-800/70 last:border-0">
                    <TableCell className="font-mono text-amber-200"><Link href={`/possessions/${encodeURIComponent(possession.possessionId)}`} className="underline decoration-slate-700 underline-offset-2 hover:text-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300">{possession.possessionId}</Link></TableCell>
                    <TableCell>{possession.sectionId} · {possession.track}</TableCell>
                    <TableCell>{possession.department || '—'}</TableCell>
                    <TableCell><StatusChip def={token} compact /></TableCell>
                    <TableCell className="whitespace-nowrap text-xs">{formatUtc(possession.plannedStartUtc)}<br />→ {formatUtc(possession.plannedEndUtc)}</TableCell>
                    <TableCell>{pending ? `${pending} item${pending === 1 ? '' : 's'} pending` : 'Ready'}</TableCell>
                  </tr>
                );
              })}
            </TableBody>
          </Table>
          {!possessions.data.items.length && <p className="p-4 text-sm text-slate-500">No possessions are visible to this role.</p>}
        </section>
      )}
    </div>
  );
};

export default FieldPwaView;
