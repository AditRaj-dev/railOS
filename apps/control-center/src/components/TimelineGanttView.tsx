'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { DepartmentBadge } from './RailwayComponents';
import { Clock, Train, Shield, Wrench, Zap, Radio } from 'lucide-react';

export const TimelineGanttView: React.FC = () => {
  const router = useRouter();
  const { activePlan, trains, tasks, setSelectedBlockId } = useRailOSStore();

  const hours = ['12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'];
  const startHour = 12;
  const totalMinutes = 6 * 60;

  const getOffsetPct = (timeStr: string) => {
    const [h, m] = timeStr.split(':').map(Number);
    const mins = (h - startHour) * 60 + m;
    return Math.max(0, Math.min(100, (mins / totalMinutes) * 100));
  };

  const getDurationPct = (durationMins: number) => {
    return (durationMins / totalMinutes) * 100;
  };

  return (
    <div className="space-y-4">
      <div className="p-3 rounded border border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" style={{ color: `var(--status-info-fg)` }} />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
            Operational Dual-Axis Timeline & Gantt (Train Movements vs Possessions)
          </h2>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Horizon: <span className="text-slate-200">12:00 – 18:00</span> • Active Plan: <span className="font-bold" style={{ color: `var(--status-info-fg)` }}>{activePlan.version}</span>
        </div>
      </div>

      <div className="p-4 rounded border border-slate-800 bg-slate-950 overflow-x-auto">
        <div className="min-w-[840px] space-y-4">
          
          <div className="grid grid-cols-6 border-b border-slate-800 pb-2 text-xs font-mono text-slate-400">
            {hours.slice(0, -1).map((h) => (
              <div key={h} className="border-l border-slate-800 pl-2">
                {h}
              </div>
            ))}
          </div>

          <div className="space-y-3 pt-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Train className="w-3.5 h-3.5" style={{ color: `var(--status-info-fg)` }} /> Passenger & Freight Running Slots (COA)
            </div>

            <div className="relative h-10 rounded bg-slate-900/60 border border-slate-800/80">
              <div className="absolute left-2 top-2 text-[10px] font-mono text-slate-500 uppercase">Down Line</div>
              {trains.filter(tr => tr.track === 'DOWN').map(t => {
                const left = getOffsetPct(t.scheduledEntry);
                return (
                  <div
                    key={t.id}
                    style={{
                      left: `${left}%`,
                      backgroundColor: t.type === 'PASSENGER_PREMIUM' ? `var(--status-warning-bg)` : `var(--status-info-bg)`,
                      borderColor: t.type === 'PASSENGER_PREMIUM' ? `var(--status-warning-border)` : `var(--status-info-border)`,
                      color: t.type === 'PASSENGER_PREMIUM' ? `var(--status-warning-text)` : `var(--status-info-text)`,
                    }}
                    className="absolute top-1.5 px-2 py-1 rounded border text-[10px] font-mono font-bold whitespace-nowrap shadow-sm"
                  >
                    {t.trainNumber} ({t.scheduledEntry})
                  </div>
                );
              })}
            </div>

            <div className="relative h-10 rounded bg-slate-900/60 border border-slate-800/80">
              <div className="absolute left-2 top-2 text-[10px] font-mono text-slate-500 uppercase">Up Line</div>
              {trains.filter(tr => tr.track === 'UP').map(t => {
                const left = getOffsetPct(t.scheduledEntry);
                return (
                  <div
                    key={t.id}
                    style={{
                      left: `${left}%`,
                      backgroundColor: `var(--status-info-bg)`,
                      borderColor: `var(--status-info-border)`,
                      color: `var(--status-info-text)`,
                    }}
                    className="absolute top-1.5 px-2 py-1 rounded border text-[10px] font-mono font-bold whitespace-nowrap"
                  >
                    {t.trainNumber} ({t.scheduledEntry})
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" style={{ color: `var(--status-ok-fg)` }} /> Integrated Line Possession Windows (RailOS Coordinated)
              </span>
              <span className="text-[10px]" style={{ color: `var(--status-ok-fg)` }}>Natural Headway Gap Exploitation</span>
            </div>

            <div className="relative h-16 rounded bg-slate-900/90 border border-slate-800">
              {activePlan.blocks.map(b => {
                const left = getOffsetPct(b.startTime);
                const width = getDurationPct(b.durationMinutes);
                return (
                  <div
                    key={b.id}
                    onClick={() => {
                      setSelectedBlockId(b.id);
                      router.push('/planner');
                    }}
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      backgroundColor: `var(--status-ok-bg)`,
                      borderColor: `var(--status-ok-fg)`,
                    }}
                    className="absolute top-1.5 bottom-1.5 rounded border cursor-pointer p-2 flex flex-col justify-between transition-all"
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono font-bold" style={{ color: `var(--status-ok-text)` }}>
                      <span>{b.blockCode}</span>
                      <span>{b.durationMinutes}m</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {b.departments.map(d => (
                        <span key={d} className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-900 text-slate-300">
                          {d}
                        </span>
                      ))}
                      <span className="text-[9px] font-mono ml-auto" style={{ color: `var(--status-ok-fg)` }}>
                        {b.utilizationRatePct}% Util
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 text-xs font-mono text-slate-400">
              <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center gap-2">
                <Wrench className="w-3.5 h-3.5" style={{ color: `var(--status-warning-fg)` }} />
                <span>Civil Track Window (Km 1324)</span>
              </div>
              <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center gap-2">
                <Radio className="w-3.5 h-3.5" style={{ color: `var(--status-info-fg)` }} />
                <span>S&T Interlocking Window (Pt 204B)</span>
              </div>
              <div className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5" style={{ color: `var(--status-ok-fg)` }} />
                <span>TRD Catenary Isolation (25kV Power Cut)</span>
              </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
};
