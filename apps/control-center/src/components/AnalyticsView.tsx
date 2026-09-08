'use client';

import React from 'react';
import { AlertCircle, BarChart3, Clock3, RefreshCw, ShieldCheck } from 'lucide-react';
import { useAnalyticsSummary } from '../lib/queries';
import { useRailOSEventStream } from '../lib/useRailOSEventStream';
import { StatusChip } from './StatusChip';
import { POSSESSION_STATE_TOKENS } from './tokens';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

function formatUtc(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

function formatMinutes(value: number): string {
  return `${value > 0 ? '+' : ''}${value} min`;
}

export const AnalyticsView: React.FC = () => {
  useRailOSEventStream();
  const summary = useAnalyticsSummary();
  const bursts = summary.data?.blockBursts;

  return (
    <div className="space-y-4" aria-labelledby="analytics-title">
      <header className="flex flex-wrap items-start justify-between gap-3 rounded border border-slate-800 bg-slate-900/80 p-4">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-amber-300">Operational analytics</p>
          <h1 id="analytics-title" className="mt-1 text-lg font-semibold text-white">Block-burst variance</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Planned close versus actual close for completed possessions. Live updates arrive from the RailOS event stream.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void summary.refetch()}
          className="inline-flex min-h-11 items-center gap-2 rounded border border-slate-700 px-3 text-sm text-slate-200 hover:border-amber-400 hover:text-amber-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300"
          aria-label="Refresh block-burst analytics"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
        </button>
      </header>

      {summary.isLoading && (
        <p className="rounded border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300" role="status">Loading block-burst analytics…</p>
      )}
      {summary.isError && (
        <div className="flex items-start gap-2 rounded border border-red-900/80 bg-red-950/40 p-4 text-sm text-red-200" role="alert">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Analytics could not be loaded. {summary.error?.message || 'Try again.'}</span>
        </div>
      )}

      {summary.data && (
        <>
          <section aria-labelledby="burst-summary-title" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <h2 id="burst-summary-title" className="sr-only">Block-burst summary</h2>
            <article className="rounded border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-400">Block bursts</p>
              <p className="mt-2 flex items-center gap-2 text-2xl font-semibold text-white"><BarChart3 className="h-5 w-5 text-amber-300" aria-hidden="true" />{bursts?.totalBursts ?? 0}</p>
              <p className="mt-1 text-xs text-slate-500">Recorded close overruns</p>
            </article>
            <article className="rounded border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-400">Total overrun</p>
              <p className="mt-2 flex items-center gap-2 text-2xl font-semibold text-amber-200"><Clock3 className="h-5 w-5" aria-hidden="true" />{bursts?.totalOverrunMinutes ?? 0} min</p>
              <p className="mt-1 text-xs text-slate-500">Across recorded bursts</p>
            </article>
            <article className="rounded border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-400">Completed work</p>
              <p className="mt-2 text-2xl font-semibold text-white">{summary.data.completedTasks ?? '—'}</p>
              <p className="mt-1 text-xs text-slate-500">Tasks returned by analytics</p>
            </article>
            <article className="rounded border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs text-slate-400">Data source</p>
              <p className="mt-2 flex items-center gap-2 text-base font-semibold text-white"><ShieldCheck className="h-5 w-5 text-emerald-300" aria-hidden="true" />{summary.data.synthetic ? 'Synthetic fixture' : 'RailOS API'}</p>
              <p className="mt-1 text-xs text-slate-500">Server-provided values</p>
            </article>
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]" aria-labelledby="burst-detail-title">
            <div className="rounded border border-slate-800 bg-slate-950 p-4">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <div>
                  <h2 id="burst-detail-title" className="text-sm font-semibold text-white">Planned versus actual close</h2>
                  <p className="mt-1 text-xs text-slate-500">Variance is signed: positive means the possession closed late.</p>
                </div>
                <span className="text-xs text-slate-500">{bursts?.items.length ?? 0} rows</span>
              </div>
              <Table caption="Block-burst detail">
                <TableHeader><tr>
                  <TableHeaderCell>Possession</TableHeaderCell>
                  <TableHeaderCell>Section / track</TableHeaderCell>
                  <TableHeaderCell>Department</TableHeaderCell>
                  <TableHeaderCell>Planned close</TableHeaderCell>
                  <TableHeaderCell>Actual close</TableHeaderCell>
                  <TableHeaderCell>Variance</TableHeaderCell>
                  <TableHeaderCell>Cause</TableHeaderCell>
                </tr></TableHeader>
                <TableBody>
                  {(bursts?.items ?? []).map((burst) => (
                    <tr key={burst.burstId} className="border-b border-slate-800/70 last:border-0">
                      <TableCell className="font-mono text-amber-200">{burst.possessionId}</TableCell>
                      <TableCell>{burst.sectionId} · {burst.track}</TableCell>
                      <TableCell>{burst.department || '—'}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatUtc(burst.plannedEndUtc)}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatUtc(burst.actualCloseUtc)}</TableCell>
                      <TableCell>
                        <StatusChip def={POSSESSION_STATE_TOKENS.OVERRUNNING} compact />
                        <span className="ml-2 text-xs font-mono text-slate-300">{formatMinutes(burst.overrunMinutes)}</span>
                      </TableCell>
                      <TableCell>{burst.causeCategory || 'Uncategorised'}</TableCell>
                    </tr>
                  ))}
                </TableBody>
              </Table>
              {!bursts?.items.length && <p className="p-4 text-sm text-slate-500">No block bursts have been recorded.</p>}
            </div>

            <aside className="space-y-4" aria-label="Block-burst breakdowns">
              <BreakdownTable title="By department" values={bursts?.byDepartment ?? {}} />
              <BreakdownTable title="By cause" values={bursts?.byCause ?? {}} />
            </aside>
          </section>
        </>
      )}
    </div>
  );
};

function BreakdownTable({ title, values }: { title: string; values: Record<string, number> }) {
  const titleId = `${title.replace(/\s+/g, '-').toLowerCase()}-title`;
  return (
    <section className="rounded border border-slate-800 bg-slate-950 p-4" aria-labelledby={titleId}>
      <h2 id={titleId} className="mb-3 text-sm font-semibold text-white">{title}</h2>
      <Table caption={`${title} block-burst breakdown`}>
        <TableHeader><tr><TableHeaderCell>Category</TableHeaderCell><TableHeaderCell>Bursts</TableHeaderCell></tr></TableHeader>
        <TableBody>
          {Object.entries(values).map(([category, count]) => (
            <tr key={category} className="border-b border-slate-800/70 last:border-0">
              <TableCell>{category}</TableCell>
              <TableCell className="font-mono text-amber-200">{count}</TableCell>
            </tr>
          ))}
        </TableBody>
      </Table>
      {!Object.keys(values).length && <p className="text-sm text-slate-500">No breakdown available.</p>}
    </section>
  );
}
