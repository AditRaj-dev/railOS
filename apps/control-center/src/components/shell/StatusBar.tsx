'use client';

import React from 'react';
import { useRailOSStore } from '@/store/railosStore';
import { CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export function StatusBar() {
  const { isEmergencyActive, emergencyState } = useRailOSStore();

  return (
    <footer className="border-t border-slate-800 bg-[var(--bg-surface)] px-3 md:px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-300">
      {/* Left: Plan Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>Plan v2.4 (BALANCED)</span>
        </div>
        <div className="flex items-center gap-2 text-slate-500 border-l border-slate-800 pl-4">
          <Clock className="w-3.5 h-3.5" />
          <span>Last sync: 14:58:32</span>
        </div>
      </div>

      {/* Center: Sync & Optimization Status */}
      <div className="flex items-center gap-3 hidden sm:flex">
        {isEmergencyActive && (
          <div className="flex items-center gap-2 px-2 py-1 rounded bg-red-950/80 border border-red-500/50 text-red-300 animate-pulse">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Emergency: {emergencyState?.defect.title.substring(0, 40)}</span>
          </div>
        )}
        {!isEmergencyActive && (
          <div className="flex items-center gap-2 text-slate-500">
            <span>Sync: OK</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </div>
        )}
      </div>

      {/* Right: Environment Label */}
      <div className="flex items-center gap-2 px-2 py-1 rounded bg-slate-900/80 border border-slate-800 text-slate-400 hidden md:flex">
        <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
        <span>SYNTHETIC MODE</span>
      </div>
    </footer>
  );
}
