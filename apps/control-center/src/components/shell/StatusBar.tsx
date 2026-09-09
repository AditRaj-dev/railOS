'use client';

import React from 'react';
import { useAnalyticsSummary, useBlockPlans, useBlockRequests } from '@/lib/queries';
import { CheckCircle2, Clock, Layers, Zap, AlertTriangle } from 'lucide-react';
import { pickActivePlan } from '@/lib/adapters';

export function StatusBar() {
  const { data: analytics, dataUpdatedAt } = useAnalyticsSummary();
  const { data: plansData } = useBlockPlans();
  const { data: requestsData } = useBlockRequests();

  const lastSync = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : '—';
  const activePlan = pickActivePlan(plansData?.plans || []);
  const planVersion = activePlan ? `v${activePlan.planVersion || 1} (${activePlan.planId})` : 'Baseline';
  const pendingRequests = requestsData?.items?.filter((r) => r.status === 'REQUESTED').length || 0;
  const criticalDefects = analytics?.defects !== undefined ? analytics.defects : 0;

  return (
    <footer className="border-t border-[var(--border-default)] bg-[var(--bg-surface)] px-3 md:px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-[var(--text-secondary)]">
      {/* Left: Operational Metrics */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Current Plan Version */}
        <div className="flex items-center gap-1.5 text-[var(--text-primary)]">
          <Layers className="w-3.5 h-3.5 text-[var(--accent)]" />
          <span className="text-[var(--text-muted)]">Plan:</span>
          <span className="font-bold">{planVersion}</span>
        </div>

        {/* Sync / Task count */}
        <div className="flex items-center gap-1.5 border-l border-[var(--border-default)] pl-4">
          <CheckCircle2 className="w-3.5 h-3.5 text-[var(--status-ok-fg)]" />
          <span>{analytics?.tasks !== undefined ? `${analytics.tasks} open tasks` : 'Syncing'}</span>
        </div>

        {/* Optimization Status */}
        <div className="flex items-center gap-1.5 border-l border-[var(--border-default)] pl-4">
          <Zap className="w-3.5 h-3.5 text-[var(--accent)]" />
          <span>Opt: <strong className="text-[var(--text-primary)]">{activePlan?.objectiveProfile || 'BALANCED'}</strong></span>
        </div>

        {/* Last Refresh */}
        <div className="flex items-center gap-1.5 border-l border-[var(--border-default)] pl-4 text-[var(--text-muted)]">
          <Clock className="w-3.5 h-3.5" />
          <span>Refreshed: {lastSync}</span>
        </div>
      </div>

      {/* Right: Active Incidents / Status & Environment */}
      <div className="flex items-center gap-3">
        {pendingRequests > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--status-caution-bg)] border border-[var(--status-caution-border)] text-[var(--status-caution-text)] text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-caution-fg)]" />
            <span>{pendingRequests} pending demand</span>
          </div>
        )}

        {criticalDefects > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--status-critical-bg)] border border-[var(--status-critical-border)] text-[var(--status-critical-text)] text-[11px]">
            <AlertTriangle className="w-3 h-3 text-[var(--status-critical-fg)]" />
            <span>{criticalDefects} track defects</span>
          </div>
        )}

        <div className="flex items-center gap-2 px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-muted)] hidden md:flex">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-ok-fg)]" />
          <span className="text-[11px] font-bold">SYNTHETIC API</span>
        </div>
      </div>
    </footer>
  );
}
