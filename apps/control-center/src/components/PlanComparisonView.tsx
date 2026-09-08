'use client';

import { useState } from 'react';
import { FileText, RefreshCw } from 'lucide-react';
import { useBlockPlans, usePlanDetail } from '@/lib/queries';
import { useRailOSStore } from '@/store/railosStore';
import { getTokenDef, PLAN_STATUS_TOKENS } from './tokens';
import { StatusChip } from './StatusChip';
import { SanctionChainPanel } from './SanctionChainPanel';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

export function PlanComparisonView() {
  const plansQuery = useBlockPlans();
  const [selectedPlanId, setSelectedPlanId] = useState('');
  const syntheticCandidates = useRailOSStore((state) => state.candidates);
  const plans = plansQuery.data?.plans || [];
  const activePlanId = selectedPlanId || plans[0]?.planId || '';
  const selectedPlanQuery = usePlanDetail(activePlanId, { enabled: Boolean(activePlanId) });
  const selectedPlan = selectedPlanQuery.data || plans.find((plan) => plan.planId === activePlanId) || null;

  return (
    <div className="space-y-5">
      <header className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Stage 3 · authority gate</p>
            <h1 className="mt-1 text-xl font-bold text-[var(--text-primary)]">Plan candidates & sanction chain</h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--text-secondary)]">Review the server-generated candidate, then collect every required authority before assignments or possessions are opened.</p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]" role="status" aria-live="polite">
            <FileText className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" />
            {plansQuery.isFetching ? 'Refreshing plans…' : `${plans.length} API-backed plan${plans.length === 1 ? '' : 's'}`}
          </div>
        </div>
      </header>

      {plansQuery.isLoading && (
        <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5 text-sm text-[var(--text-secondary)]" role="status">Loading plan candidates…</div>
      )}

      {plansQuery.isError && (
        <div className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-4 text-sm text-[var(--status-critical-text)]" role="alert">
          <p className="font-semibold">Plan API unavailable</p>
          <p className="mt-1">{plansQuery.error.message}. The local comparison fixtures remain visible below; sanctioning requires an API-backed plan.</p>
        </div>
      )}

      {plans.length > 0 ? (
        <section aria-labelledby="api-plan-list-title" className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 id="api-plan-list-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">API candidates</h2>
            <button type="button" onClick={() => plansQuery.refetch()} disabled={plansQuery.isFetching} className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--accent)] disabled:opacity-50">
              <RefreshCw className={`h-3.5 w-3.5 ${plansQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" /> Refresh
            </button>
          </div>
          <Table caption="API-generated plan candidates">
            <TableHeader><tr><TableHeaderCell>Plan</TableHeaderCell><TableHeaderCell>Profile</TableHeaderCell><TableHeaderCell>Version</TableHeaderCell><TableHeaderCell>Blocks</TableHeaderCell><TableHeaderCell>Status</TableHeaderCell><TableHeaderCell><span className="sr-only">Review</span></TableHeaderCell></tr></TableHeader>
            <TableBody>
              {plans.map((plan) => (
                <tr key={plan.planId} className={plan.planId === activePlanId ? 'bg-[var(--bg-elevated)]' : undefined}>
                  <TableCell><span className="font-mono font-semibold text-[var(--text-primary)]">{plan.planId}</span></TableCell>
                  <TableCell>{plan.objectiveProfile.replaceAll('_', ' ')}</TableCell>
                  <TableCell className="font-mono">v{plan.planVersion}</TableCell>
                  <TableCell>{plan.blocks.length}</TableCell>
                  <TableCell><StatusChip def={getTokenDef(PLAN_STATUS_TOKENS, plan.status)} compact /></TableCell>
                  <TableCell className="text-right"><button type="button" onClick={() => setSelectedPlanId(plan.planId)} aria-pressed={plan.planId === activePlanId} className="min-h-11 rounded border border-[var(--border-strong)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--accent)]">{plan.planId === activePlanId ? 'Reviewing' : 'Review chain'}</button></TableCell>
                </tr>
              ))}
            </TableBody>
          </Table>
        </section>
      ) : (
        <section className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5" aria-labelledby="fixture-title">
          <h2 id="fixture-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Local comparison fixtures</h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Generate a plan from the planner to create API-backed candidates and an auditable sanction chain.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {syntheticCandidates.map((candidate) => (
              <article key={candidate.mode} className="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4">
                <div className="flex items-center justify-between gap-2"><h3 className="font-mono text-sm font-bold text-[var(--text-primary)]">{candidate.mode.replaceAll('_', ' ')}</h3><span className="font-mono text-xs text-[var(--text-muted)]">{candidate.version}</span></div>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{candidate.recommendationNote}</p>
                <dl className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]"><div className="flex justify-between"><dt>Blocks</dt><dd className="font-mono text-[var(--text-primary)]">{candidate.blocks.length}</dd></div><div className="flex justify-between"><dt>Train disruption</dt><dd className="font-mono text-[var(--text-primary)]">{candidate.trainDisruptionMinutes} min</dd></div></dl>
              </article>
            ))}
          </div>
        </section>
      )}

      <SanctionChainPanel planId={activePlanId || undefined} plan={selectedPlan} />
    </div>
  );
}
