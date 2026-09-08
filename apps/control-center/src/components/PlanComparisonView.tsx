'use client';

import { useState } from 'react';
import { FileText, RefreshCw } from 'lucide-react';
import { useBlockPlans, usePlanDetail } from '@/lib/queries';
import { getTokenDef, PLAN_STATUS_TOKENS } from './tokens';
import { StatusChip } from './StatusChip';
import { SanctionChainPanel } from './SanctionChainPanel';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

export function PlanComparisonView() {
  const plansQuery = useBlockPlans();
  const [selectedPlanId, setSelectedPlanId] = useState('');
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
          <p className="mt-1">{plansQuery.error.message}. Sanctioning requires an API-backed plan.</p>
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
        <section className="rounded border border-dashed border-[var(--border-default)] bg-[var(--bg-panel)] p-5 text-center" aria-labelledby="empty-title">
          <h2 id="empty-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">No plan candidates yet</h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Generate a plan from the Block Planner to create API-backed candidates and an auditable sanction chain.</p>
        </section>
      )}

      <SanctionChainPanel planId={activePlanId || undefined} plan={selectedPlan} />
    </div>
  );
}
