'use client';

import React, { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { useBlockPlans, useTrains, useNetworkCatalog } from '@/lib/queries';
import { toDisplayBlock, toDisplayTrain, pickActivePlan, buildSectionNameMap } from '@/lib/adapters';
import { DepartmentBadge } from './RailwayComponents';
import { Clock, Train, Shield } from 'lucide-react';

export const TimelineGanttView: React.FC = () => {
  const router = useRouter();
  const { setSelectedBlockId } = useRailOSStore();
  const { data: catalog } = useNetworkCatalog();
  const { data: plansData } = useBlockPlans();
  const { data: trainsData } = useTrains();

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

  const sectionNames = useMemo(() => buildSectionNameMap(catalog?.sections || []), [catalog]);
  const activePlan = useMemo(() => pickActivePlan(plansData?.plans || []), [plansData]);
  const blocks = useMemo(
    () => (activePlan?.blocks || []).map((b) => toDisplayBlock(b, sectionNames)),
    [activePlan, sectionNames]
  );
  const trains = useMemo(
    () => ((trainsData || []) as Record<string, unknown>[]).map(toDisplayTrain),
    [trainsData]
  );

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
          Horizon: <span className="text-slate-200">12:00 – 18:00</span>
          {activePlan && (
            <> • Active Plan: <span className="font-bold" style={{ color: `var(--status-info-fg)` }}>{activePlan.planId} v{activePlan.planVersion}</span></>
          )}
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
              <Train className="w-3.5 h-3.5" style={{ color: `var(--status-info-fg)` }} /> Train Movements
            </div>

            <div className="relative h-10 rounded bg-slate-900/60 border border-slate-800/80">
              <div className="absolute left-2 top-2 text-[10px] font-mono text-slate-500 uppercase">Down Line</div>
              {trains.filter((tr) => tr.track === 'DOWN').map((t) => {
                const left = getOffsetPct(t.entryClock);
                return (
                  <div
                    key={t.id}
                    style={{
                      left: `${left}%`,
                      backgroundColor: t.priority >= 8 ? `var(--status-warning-bg)` : `var(--status-info-bg)`,
                      borderColor: t.priority >= 8 ? `var(--status-warning-border)` : `var(--status-info-border)`,
                      color: t.priority >= 8 ? `var(--status-warning-text)` : `var(--status-info-text)`,
                    }}
                    className="absolute top-1.5 px-2 py-1 rounded border text-[10px] font-mono font-bold whitespace-nowrap shadow-sm"
                  >
                    {t.id} ({t.entryClock})
                  </div>
                );
              })}
            </div>

            <div className="relative h-10 rounded bg-slate-900/60 border border-slate-800/80">
              <div className="absolute left-2 top-2 text-[10px] font-mono text-slate-500 uppercase">Up Line</div>
              {trains.filter((tr) => tr.track === 'UP').map((t) => {
                const left = getOffsetPct(t.entryClock);
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
                    {t.id} ({t.entryClock})
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" style={{ color: `var(--status-ok-fg)` }} /> Possession Windows (Active Plan)
              </span>
            </div>

            <div className="relative h-16 rounded bg-slate-900/90 border border-slate-800">
              {blocks.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-[11px] font-mono text-slate-500 italic">
                  No possession blocks in the active plan.
                </div>
              )}
              {blocks.map((b) => {
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
                      {b.departments.map((d, i) => (
                        <span key={`${d}-${i}`} className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-900 text-slate-300">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {blocks.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-2 text-xs font-mono text-slate-400">
                {blocks.map((b) => (
                  <div key={b.id} className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center gap-2">
                    {b.departments[0] && <DepartmentBadge dept={b.departments[0]} />}
                    <span>{b.sectionName}</span>
                  </div>
                ))}
              </div>
            )}

          </div>

        </div>
      </div>
    </div>
  );
};
