'use client';

import React, { useState } from 'react';
import { useRailOSStore } from '../store/railosStore';
import { CorridorSection } from '../types/railos';
import { DepartmentBadge, RiskBadge } from './RailwayComponents';
import { 
  Layers, 
  Activity, 
  Wrench, 
  Zap, 
  Radio, 
  AlertTriangle, 
  ShieldCheck, 
  Train,
  Clock,
  ArrowRight,
  Bot
} from 'lucide-react';

export const DigitalTwinView: React.FC = () => {
  const { 
    sections, 
    tasks, 
    trains, 
    selectedSectionId, 
    setSelectedSectionId, 
    activePlan
  } = useRailOSStore();

  const [activeLayer, setActiveLayer] = useState<'ALL' | 'CIVIL' | 'S_AND_T' | 'TRD' | 'TRAFFIC'>('ALL');

  const selectedSection = sections.find(s => s.id === selectedSectionId) || sections[0];
  const sectionTasks = tasks.filter(t => t.sectionId === selectedSection.id);
  const sectionBlocks = activePlan.blocks.filter(b => b.sectionId === selectedSection.id);

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
          <span>CORRIDOR:</span>
          <span className="text-slate-100 font-bold">New Delhi (NDLS) ━━ Tundla Jn (TDL) [204.9 km]</span>
        </div>
      </div>

      {/* Main Interactive Schematic Trunk Line */}
      <div className="p-6 rounded border border-slate-800 bg-slate-950 relative overflow-x-auto">
        <div className="min-w-[760px]">
          
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-6 flex items-center justify-between">
            <span>Interlocking & Corridor Schematic View (Click Section to Inspect)</span>
            <span className="flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 bg-emerald-500 rounded-sm" /> Normal
              <span className="inline-block w-2.5 h-2.5 bg-amber-500 rounded-sm ml-2" /> Caution
              <span className="inline-block w-2.5 h-2.5 bg-red-500 rounded-sm ml-2" /> Restricted / Flaw
            </span>
          </div>

          <div className="flex items-center justify-between relative py-6">
            <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-1.5 bg-slate-800 z-0" />
            <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-0.5 bg-slate-700 z-0" />

            {sections.map((sec) => {
              const isSelected = sec.id === selectedSection.id;
              
              let statusBorder = 'border-emerald-500/80 text-emerald-400';
              let statusDot = 'bg-emerald-400';
              if (sec.status === 'RESTRICTED') {
                statusBorder = 'border-red-500 text-red-400 animate-pulse';
                statusDot = 'bg-red-500';
              } else if (sec.status === 'CAUTION') {
                statusBorder = 'border-amber-500 text-amber-400';
                statusDot = 'bg-amber-400';
              }

              return (
                <div 
                  key={sec.id}
                  onClick={() => setSelectedSectionId(sec.id)}
                  className="relative z-10 flex flex-col items-center cursor-pointer transition-all duration-200 group"
                >
                  <div className={`px-3 py-1.5 rounded-md border text-xs font-mono font-bold bg-slate-900 shadow-lg flex items-center gap-2 ${
                    isSelected ? 'ring-2 ring-sky-400 border-sky-400 scale-105' : statusBorder
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${statusDot}`} />
                    <span>{sec.fromStation}</span>
                    <span className="text-[10px] text-slate-400 font-normal">Km {sec.distanceKm}</span>
                  </div>

                  <div className={`mt-4 p-2.5 rounded border text-[11px] font-mono w-44 bg-slate-900/90 text-slate-300 transition-all ${
                    isSelected ? 'border-sky-500 bg-sky-950/30' : 'border-slate-800 group-hover:border-slate-700'
                  }`}>
                    <div className="flex items-center justify-between font-bold text-slate-200 mb-1">
                      <span>{sec.code}</span>
                      <span className={sec.capacityUtilizationPct > 140 ? 'text-amber-400' : 'text-slate-300'}>
                        {sec.capacityUtilizationPct}% Cap
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-slate-800 text-[10px] text-center">
                      <div className="bg-amber-950/30 p-0.5 rounded border border-amber-800/30">
                        <span className="block text-amber-400 font-bold">{sec.civilDefects}</span>
                        <span className="text-[9px] text-slate-400">TRK</span>
                      </div>
                      <div className="bg-sky-950/30 p-0.5 rounded border border-sky-800/30">
                        <span className="block text-sky-400 font-bold">{sec.sandTDefects}</span>
                        <span className="text-[9px] text-slate-400">S&T</span>
                      </div>
                      <div className="bg-emerald-950/30 p-0.5 rounded border border-emerald-800/30">
                        <span className="block text-emerald-400 font-bold">{sec.trdDefects}</span>
                        <span className="text-[9px] text-slate-400">OHE</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            <div className="relative z-10 flex flex-col items-center">
              <div className="px-3 py-1.5 rounded-md border border-slate-700 text-xs font-mono font-bold bg-slate-900 text-slate-300">
                TDL (Tundla)
              </div>
            </div>

          </div>

        </div>
      </div>

      {/* Section Detailed Telemetry & Plan Rationale Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        <div className="lg:col-span-7 rounded border border-slate-800 bg-slate-900/80 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <div className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <span>{selectedSection.name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-normal">
                  {selectedSection.tracks} Tracks • {selectedSection.electrified ? '25kV Electrified' : 'Non-El'}
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {selectedSection.description}
              </div>
            </div>
            
            <div className="text-right font-mono">
              <div className="text-xs text-slate-400">Health Index</div>
              <div className={`text-lg font-bold ${selectedSection.healthScore < 70 ? 'text-red-400' : 'text-emerald-400'}`}>
                {selectedSection.healthScore} / 100
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-2.5 rounded border border-amber-900/40 bg-amber-950/20 text-xs font-mono">
              <div className="text-amber-400 font-bold flex items-center justify-between">
                <span>Civil / Track</span>
                <Wrench className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{selectedSection.civilDefects} Flaws / Tasks</div>
              <div className="text-[10px] text-slate-400">IMR Weld & Rail Flaws</div>
            </div>

            <div className="p-2.5 rounded border border-sky-900/40 bg-sky-950/20 text-xs font-mono">
              <div className="text-sky-400 font-bold flex items-center justify-between">
                <span>S&T Interlocking</span>
                <Radio className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{selectedSection.sandTDefects} Signal Issues</div>
              <div className="text-[10px] text-slate-400">Point Machine & DAC</div>
            </div>

            <div className="p-2.5 rounded border border-emerald-900/40 bg-emerald-950/20 text-xs font-mono">
              <div className="text-emerald-400 font-bold flex items-center justify-between">
                <span>TRD / Traction</span>
                <Zap className="w-3.5 h-3.5" />
              </div>
              <div className="text-slate-300 mt-1 font-bold">{selectedSection.trdDefects} OHE Issues</div>
              <div className="text-[10px] text-slate-400">Catenary & Isolators</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
              Active Tasks in this Section ({sectionTasks.length}):
            </div>
            {sectionTasks.length === 0 ? (
              <div className="p-3 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
                No open maintenance defects logged in this section.
              </div>
            ) : (
              sectionTasks.map(t => (
                <div key={t.id} className="p-2.5 rounded border border-slate-800 bg-slate-950 flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <DepartmentBadge dept={t.department} />
                      <span className="text-xs font-semibold text-slate-200">{t.title}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Asset: {t.assetName} • Req: {t.blockRequirement} Block ({t.estimatedMinutes}m)
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
                <Bot className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
                  Why This Plan?
                </h3>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Not Wired
              </span>
            </div>

            <p className="text-xs text-slate-400 mt-3 leading-relaxed">
              Renders optimizer factors, warnings and objective breakdown for the selected section. Explanation only &mdash; never generates or approves a schedule.
            </p>

            <div className="mt-3 p-3 rounded border border-slate-800 bg-slate-950 font-mono text-xs text-slate-500 leading-relaxed min-h-[160px] flex items-center justify-center text-center italic">
              Pending optimizer factor wiring. See docs/handoff/04-plan-rationale-panel.md
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
