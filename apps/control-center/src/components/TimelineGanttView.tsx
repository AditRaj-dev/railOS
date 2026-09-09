'use client';

import React, { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { useBlockPlans, useTrains, useNetworkCatalog, useBlockRequests } from '@/lib/queries';
import Link from 'next/link';
import { DEMO_EPOCH_ISO, formatMinute } from '@/lib/time';
import { toDisplayBlock, toDisplayTrain, pickActivePlan, buildSectionNameMap } from '@/lib/adapters';
import { DepartmentBadge } from './RailwayComponents';
import { Clock, Train, Shield, Ticket } from 'lucide-react';

export const TimelineGanttView: React.FC = () => {
  const router = useRouter();
  const { setSelectedBlockId } = useRailOSStore();
  const { data: catalog } = useNetworkCatalog();
  const { data: plansData } = useBlockPlans();
  const { data: trainsData } = useTrains();
  const { data: ticketsData } = useBlockRequests({ status: 'REQUESTED' });

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

  // Requested demand is not a possession: it is drawn in its own lane, dashed,
  // and labelled REQUESTED in words so the pattern is never the only carrier.
  const demands = useMemo(
    () => (ticketsData?.items || [])
      .filter((request) => request.requestedStart != null && request.requestedEnd != null)
      .map((request) => {
        const start = Number(request.requestedStart);
        const end = Number(request.requestedEnd);
        return {
          requestId: request.requestId,
          department: request.department,
          taskType: request.taskType,
          taskId: request.linkedTaskId || null,
          startMinute: start,
          endMinute: end,
          leftPct: Math.max(0, Math.min(100, (((start % 1440) - startHour * 60) / totalMinutes) * 100)),
          widthPct: Math.max(1, Math.min(100, ((end - start) / totalMinutes) * 100)),
          windowLabel: `${formatMinute(DEMO_EPOCH_ISO, start)} → ${formatMinute(DEMO_EPOCH_ISO, end)}`,
        };
      }),
    [ticketsData, startHour, totalMinutes]
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
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Ticket className="w-3.5 h-3.5" style={{ color: `var(--status-warning-fg)` }} /> Requested Demand (tickets, not sanctioned)
            </div>

            {demands.length === 0 ? (
              <div className="h-10 rounded bg-slate-900/60 border border-dashed border-slate-700 flex items-center justify-center text-[11px] font-mono text-slate-500 italic">
                No open ticket requests.
              </div>
            ) : (
              // One row per request: requested windows overlap freely (nothing
              // has been sanctioned yet), so stacking them in a single track
              // would hide all but the last one drawn.
              <div className="space-y-1.5">
                {demands.map((demand) => (
                  <div key={demand.requestId} className="relative h-8 rounded bg-slate-900/60 border border-dashed border-slate-700">
                    <div
                      style={{
                        left: `${demand.leftPct}%`,
                        width: `${demand.widthPct}%`,
                        borderColor: `var(--status-warning-fg)`,
                        backgroundColor: `var(--status-warning-bg)`,
                        color: `var(--status-warning-text)`,
                      }}
                      className="absolute top-1 bottom-1 rounded border border-dashed px-1.5 text-[10px] font-mono leading-6 truncate"
                    >
                      {demand.department} · {demand.taskType.replace(/_/g, ' ')} · REQUESTED
                    </div>
                  </div>
                ))}
              </div>
            )}

            {demands.length > 0 && (
              <ul className="grid gap-1.5 sm:grid-cols-2 text-[11px] font-mono text-slate-400">
                {demands.map((demand) => (
                  <li key={demand.requestId} className="rounded border border-slate-800 bg-slate-950 px-2 py-1.5">
                    <Link href="/tickets" className="font-bold text-slate-200 underline underline-offset-4">{demand.requestId}</Link>
                    {' '}· {demand.department} · {demand.taskType.replace(/_/g, ' ')} · REQUESTED · {demand.windowLabel}
                    {demand.taskId && <> · task {demand.taskId}</>}
                  </li>
                ))}
              </ul>
            )}
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
                  // A real button, not a clickable div (DP-002): the bar is
                  // keyboard reachable, announces itself, and carries the whole
                  // window in its accessible name because the visible label is
                  // clipped to the bar's width.
                  <button
                    key={b.id}
                    type="button"
                    aria-label={`Possession ${b.blockCode}, ${b.sectionName}, ${b.startTime} to ${b.endTime}, ${b.durationMinutes} minutes. Open in Block Opportunity Planner.`}
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
                    className="absolute top-1.5 bottom-1.5 rounded border p-2 flex flex-col justify-between text-left transition-all hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    <span className="flex items-center justify-between text-[10px] font-mono font-bold" style={{ color: `var(--status-ok-text)` }}>
                      <span>{b.blockCode}</span>
                      <span>{b.durationMinutes}m</span>
                    </span>
                    <span className="flex items-center gap-1">
                      {b.departments.map((d, i) => (
                        <span key={`${d}-${i}`} className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-900 text-slate-300">
                          {d}
                        </span>
                      ))}
                    </span>
                  </button>
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
