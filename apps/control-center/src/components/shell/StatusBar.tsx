'use client';

import React from 'react';
import { useAnalyticsSummary } from '@/lib/queries';
import { CheckCircle2, Clock } from 'lucide-react';

export function StatusBar() {
  const { data: analytics, dataUpdatedAt } = useAnalyticsSummary();
  const lastSync = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : '—';

  return (
    <footer className="border-t border-slate-800 bg-[var(--bg-surface)] px-3 md:px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-300">
      {/* Left: Sync Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>{analytics?.tasks !== undefined ? `${analytics.tasks} open tasks` : 'Synthetic API'}</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500 border-l border-slate-800 pl-4">
          <Clock className="w-3.5 h-3.5" />
          <span>Last sync: {lastSync}</span>
        </div>
      </div>

      {/* Right: Environment Label */}
      <div className="flex items-center gap-2 px-2 py-1 rounded bg-slate-900/80 border border-slate-800 text-slate-400 hidden md:flex">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        <span>SYNTHETIC API</span>
      </div>
    </footer>
  );
}
