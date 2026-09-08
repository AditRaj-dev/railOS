'use client';

import React, { useMemo, useState } from 'react';
import { useRailOSStore } from '../store/railosStore';
import { useNetworkCatalog, useMaintenanceTasks, useBlockPlans } from '@/lib/queries';
import { toDisplayTask, toDisplayBlock, pickActivePlan, buildSectionNameMap } from '@/lib/adapters';
import { DepartmentBadge, RiskBadge } from './RailwayComponents';
import {
  Layers,
  Wrench,
  Zap,
  Radio,
  Train
} from 'lucide-react';

type SectionStatus = 'NORMAL' | 'CAUTION' | 'RESTRICTED';

function deriveSectionStatus(criticalDefectCount: number, pendingMaintenanceCount: number): SectionStatus {
  if (criticalDefectCount > 0) return 'RESTRICTED';
  if (pendingMaintenanceCount > 3) return 'CAUTION';
  return 'NORMAL';
}

export const DigitalTwinView: React.FC = () => {
  const { selectedSectionId, setSelectedSectionId } = useRailOSStore();
  const { data: catalog } = useNetworkCatalog();
  const { data: plansData } = useBlockPlans();

  const [activeLayer, setActiveLayer] = useState<'ALL' | 'CIVIL' | 'S_AND_T' | 'TRD' | 'TRAFFIC'>('ALL');

  const sections = catalog?.sections || [];
  const selectedSection = sections.find((s) => s.sectionId === selectedSectionId) || sections[0];

  const { data: tasksData } = useMaintenanceTasks(selectedSection ? { sectionId: selectedSection.sectionId } : undefined);
  const sectionNames = useMemo(() => buildSectionNameMap(catalog?.sections || []), [catalog]);
  const sectionTasks = useMemo(() => {
    const rawTasks = (tasksData?.tasks || []) as Record<string, unknown>[];
    return rawTasks.map((t) => toDisplayTask(t, sectionNames));
  }, [tasksData, sectionNames]);

  const activePlan = useMemo(() => pickActivePlan(plansData?.plans || []), [plansData]);
  const sectionBlocks = useMemo(
    () =>
      (activePlan?.blocks || [])
        .filter((b) => b.sectionId === selectedSection?.sectionId)
        .map((b) => toDisplayBlock(b, sectionNames)),
    [activePlan, selectedSection, sectionNames]
  );

  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = { CIVIL: 0, S_AND_T: 0, TRD: 0 };
    sectionTasks.forEach((t) => {
      counts[t.department] = (counts[t.department] || 0) + 1;
    });
    return counts;
  }, [sectionTasks]);

  if (!selectedSection) {
    return (
      <div className="p-6 rounded border border-dashed border-slate-800 text-center text-xs font-mono text-slate-500">
        No network sections available from the API yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Filter Bar & Multi-Department Layers */}
      <div className="p-3 rounded border border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wide">
            Digital Twin Layers:
          </span>
          <div className="flex items-center gap-1.5 ml-2">
            {(['ALL', 'CIVIL', 'S_AND_T', 'TRD', 'TRAFFIC'] as const).map((layer) => (
              <button
                key={layer}
                onClick={() => setActiveLayer(layer)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold transition-all border ${
                  activeLayer === layer
                    ? 'bg-sky-600 text-white border-sky-500 shadow-sm'
                    : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                {layer}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span>SECTIONS LOADED:</span>
          <span className="text-slate-100 font-bold">{sections.length}</span>
        </div>
      </div>

      {/* Main Interactive Schematic Trunk Line */}
      <div className="p-6 rounded border border-slate-800 bg-slate-950 relative overflow-x-auto">
        <div className="min-w-[760px]">

          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-6 flex items-center justify-between">
            <span>Network Section Overview (Click Section to Inspect)</span>
            <span className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 bg-emerald-500 rounded-sm" /> Normal
              <span className="inline-block w-2.5 h-2.5 bg-amber-500 rounded-sm ml-2" /> Caution
              <span className="inline-block w-2.5 h-2.5 bg-red-500 rounded-sm ml-2" /> Restricted / Flaw
            </span>
          </div>

          <div className="flex items-center justify-between relative py-6 flex-wrap gap-y-8">
            <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-1.5 bg-slate-800 z-0" />
            <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-0.5 bg-slate-700 z-0" />

            {sections.map((sec) => {
              const isSelected = sec.sectionId === selectedSection.sectionId;
              const status = deriveSectionStatus(sec.metrics.criticalDefectCount, sec.metrics.pendingMaintenanceCount);

              let statusBorder = 'border-emerald-500/80 text-emerald-400';
              let statusDot = 'bg-emerald-400';
              if (status === 'RESTRICTED') {
                statusBorder = 'border-red-500 text-red-400 animate-pulse';
                statusDot = 'bg-red-500';
              } else if (status === 'CAUTION') {
                statusBorder = 'border-amber-500 text-amber-400';
                statusDot = 'bg-amber-400';
              }

              return (
                <div
                  key={sec.sectionId}
                  onClick={() => setSelectedSectionId(sec.sectionId)}
                  className="relative z-10 flex flex-col items-center cursor-pointer transition-all duration-200 group"
                >
                  <div className={`px-3 py-1.5 rounded-md border text-xs font-mono font-bold bg-slate-900 shadow-lg flex items-center gap-2 ${
                    isSelected ? 'ring-2 ring-sky-400 border-sky-400 scale-105' : statusBorder
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${statusDot}`} />
                    <span>{sec.fromStation}</span>
                  </div>

                  <div className={`mt-4 p-2.5 rounded border text-[11px] font-mono w-44 bg-slate-900/90 text-slate-300 transition-all ${
                    isSelected ? 'border-sky-500 bg-sky-950/30' : 'border-slate-800 group-hover:border-slate-700'
                  }`}>
                    <div className="flex items-center justify-between font-bold text-slate-200 mb-1">
                      <span>{sec.code}</span>
                      <span className={sec.metrics.trafficPressure > 100 ? 'text-amber-400' : 'text-slate-300'}>
                        {Math.round(sec.metrics.trafficPressure)}% Traffic
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-1 pt-1.5 border-t border-slate-800 text-[10px] text-center">
                      <div className="bg-amber-950/30 p-0.5 rounded border border-amber-800/30">
                        <span className="block text-amber-400 font-bold">{sec.metrics.pendingMaintenanceCount}</span>
                        <span className="text-[9px] text-slate-400">PENDING</span>
                      </div>
                      <div className="bg-red-950/30 p-0.5 rounded border border-red-800/30">
                        <span className="block text-red-400 font-bold">{sec.metrics.criticalDefectCount}</span>
                        <span className="text-[9px] text-slate-400">CRITICAL</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

          </div>

        </div>
      </div>

      {/* Section Detailed Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

        <div className="lg:col-span-7 rounded border border-slate-800 bg-slate-900/80 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <span>{selectedSection.name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-normal">
                  {selectedSection.tracks.length} Track{selectedSection.tracks.length === 1 ? '' : 's'} ({selectedSection.tracks.join('/')})
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {selectedSection.fromStation} – {selectedSection.toStation}
              </div>
            </div>

            <div className="text-right font-mono">
              <div className="text-xs text-slate-400">Asset Availability</div>
              <div className={`text-lg font-bold ${selectedSection.metrics.assetAvailability < 70 ? 'text-red-400' : 'text-emerald-400'}`}>
                {Math.round(selectedSection.metrics.assetAvailability)} / 100
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-2.5 rounded border border-amber-900/40 bg-amber-950/20 text-xs font-mono">
              <div className="text-amber-400 font-bold flex items-center justify-between">
                <span>Civil / Track</span>
                <Wrench className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{deptCounts.CIVIL} Open Tasks</div>
              <div className="text-[10px] text-slate-400">Rail & Track Maintenance</div>
            </div>

            <div className="p-2.5 rounded border border-sky-900/40 bg-sky-950/20 text-xs font-mono">
              <div className="text-sky-400 font-bold flex items-center justify-between">
                <span>S&T Interlocking</span>
                <Radio className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{deptCounts.S_AND_T} Open Tasks</div>
              <div className="text-[10px] text-slate-400">Signal & Telecom</div>
            </div>

            <div className="p-2.5 rounded border border-emerald-900/40 bg-emerald-950/20 text-xs font-mono">
              <div className="text-emerald-400 font-bold flex items-center justify-between">
                <span>TRD / Traction</span>
                <Zap className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{deptCounts.TRD} Open Tasks</div>
              <div className="text-[10px] text-slate-400">Catenary & Isolators</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
              Active Tasks in this Section ({sectionTasks.length}):
            </div>
            {sectionTasks.length === 0 ? (
              <div className="p-3 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
                No open maintenance tasks logged in this section.
              </div>
            ) : (
              sectionTasks
                .filter((t) => activeLayer === 'ALL' || activeLayer === 'TRAFFIC' || t.department === activeLayer)
                .map((t) => (
                  <div key={t.id} className="p-2.5 rounded border border-slate-800 bg-slate-950 flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <DepartmentBadge dept={t.department} />
                        <span className="text-xs font-semibold text-slate-200">{t.title}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Req: {t.blockRequirement} Block ({t.estimatedMinutes}m)
                      </div>
                    </div>
                    <RiskBadge score={t.riskScore} severity={t.severity} />
                  </div>
                ))
            )}
          </div>
        </div>

        <div className="lg:col-span-5 rounded border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <Train className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
                  Possession Blocks in Section
                </h3>
              </div>
            </div>

            {sectionBlocks.length === 0 ? (
              <div className="mt-3 p-3 rounded border border-slate-800 bg-slate-950 font-mono text-xs text-slate-500 leading-relaxed min-h-[120px] flex items-center justify-center text-center italic">
                No possession blocks in the active plan for this section.
              </div>
            ) : (
              <div className="mt-3 space-y-2">
                {sectionBlocks.map((b) => (
                  <div key={b.id} className="p-2.5 rounded border border-slate-800 bg-slate-950 text-xs font-mono flex items-center justify-between">
                    <span className="font-bold text-slate-200">{b.blockCode}</span>
                    <span className="text-slate-400">{b.startTime} – {b.endTime}</span>
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
