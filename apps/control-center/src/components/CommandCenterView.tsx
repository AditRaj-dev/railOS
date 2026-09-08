'use client';

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { useAnalyticsSummary, useMaintenanceTasks, useBlockPlans, useNetworkCatalog, useCreateEmergency } from '@/lib/queries';
import { toDisplayTask, toDisplayBlock, pickActivePlan, buildSectionNameMap } from '@/lib/adapters';
import { MetricCard, RiskBadge, DepartmentBadge } from './RailwayComponents';
import {
  AlertTriangle,
  Clock,
  ShieldAlert,
  CheckCircle2,
  Activity,
  ArrowRight,
  TrendingUp,
  Cpu
} from 'lucide-react';

export const CommandCenterView: React.FC = () => {
  const router = useRouter();
  const { data: liveAnalytics } = useAnalyticsSummary();
  const { data: tasksData } = useMaintenanceTasks();
  const { data: plansData } = useBlockPlans();
  const { data: catalog } = useNetworkCatalog();
  const { setSelectedTaskId, setSelectedBlockId } = useRailOSStore();
  const createEmergency = useCreateEmergency();
  const [emergencyId, setEmergencyId] = useState<string | null>(null);

  const sectionNames = useMemo(() => buildSectionNameMap(catalog?.sections || []), [catalog]);
  const tasks = useMemo(() => {
    const rawTasks = (tasksData?.tasks || []) as Record<string, unknown>[];
    return rawTasks.map((t) => toDisplayTask(t, sectionNames));
  }, [tasksData, sectionNames]);
  const activePlan = useMemo(() => pickActivePlan(plansData?.plans || []), [plansData]);
  const activeBlocks = useMemo(
    () => (activePlan?.blocks || []).map((b) => toDisplayBlock(b, sectionNames)),
    [activePlan, sectionNames]
  );

  const criticalTasks = tasks.filter((t) => t.severity === 'CRITICAL');
  const overdueTasks = tasks.filter((t) => t.severity === 'CRITICAL' && t.status === 'PENDING');

  const displayCritical = liveAnalytics?.criticalDefects !== undefined ? liveAnalytics.criticalDefects : criticalTasks.length;
  const displayDebt = liveAnalytics?.maintenanceDebt ? `${liveAnalytics.maintenanceDebt} hrs` : `${tasks.length} open`;

  const handleInjectEmergency = () => {
    createEmergency.mutate(
      {
        title: 'USFD ultrasonic crack detection — immediate rail fracture risk',
        corridorId: 'GZB-ALJN',
        severity: 'CRITICAL',
        durationMinutes: 55,
      },
      { onSuccess: (data) => setEmergencyId(data.id) }
    );
  };

  return (
    <div className="space-y-4">
      {/* 5-Second Situation Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6 gap-2.5" aria-label="Situation summary">
        <MetricCard
          label="Critical Defects"
          value={displayCritical}
          subValue="Immediate Action Required"
          status={displayCritical > 0 ? "critical" : "normal"}
          icon={AlertTriangle}
        />
        <MetricCard
          label="Overdue Backlog"
          value={overdueTasks.length}
          subValue="Highest-Priority Pending"
          status={overdueTasks.length > 0 ? "caution" : "normal"}
          icon={Clock}
        />
        <MetricCard
          label="Active & Planned Blocks"
          value={activeBlocks.length}
          subValue={activePlan ? `Plan ${activePlan.planId} v${activePlan.planVersion}` : 'No plan generated yet'}
          status="highlight"
          icon={ShieldAlert}
        />
        <MetricCard
          label="Corridor Pressure"
          value={liveAnalytics?.trafficPressure ? `${liveAnalytics.trafficPressure}%` : '—'}
          subValue="Network Traffic Pressure"
          status="caution"
          icon={Activity}
        />
        <MetricCard
          label="Maintenance Debt"
          value={displayDebt}
          subValue="Open Maintenance Load"
          status="normal"
          icon={TrendingUp}
        />
        <MetricCard
          label="Open Tasks"
          value={liveAnalytics?.tasks ?? tasks.length}
          subValue="Across All Departments"
          status="normal"
          icon={CheckCircle2}
        />
      </div>

      {/* Emergency Injection */}
      {emergencyId ? (
        <div
          className="p-3.5 rounded border flex items-center justify-between animate-pulse"
          style={{
            backgroundColor: `var(--status-critical-bg)`,
            borderColor: `var(--status-critical-border)`,
          }}
        >
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5" style={{ color: `var(--status-critical-fg)` }} />
            <div>
              <div className="text-sm font-bold font-mono" style={{ color: `var(--status-critical-text)` }}>
                Emergency recorded — dynamic replanning required
              </div>
              <div className="text-xs opacity-80" style={{ color: `var(--status-critical-text)` }}>
                Recorded against the live API. Open the planner to generate a replan around it.
              </div>
            </div>
          </div>
          <button
            onClick={() => router.push(`/planner?emergencyId=${encodeURIComponent(emergencyId)}`)}
            className="min-h-11 px-3 py-1.5 text-slate-950 text-xs font-mono font-bold rounded flex items-center gap-1.5 transition-colors cursor-pointer"
            style={{ backgroundColor: `var(--status-critical-fg)` }}
          >
            Open Replanner <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="p-2.5 rounded border border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-slate-300">
            <span className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: `var(--status-ok-fg)` }} />
            <span className="text-slate-400">EMERGENCY INJECTION:</span>
            <span>Record a sudden USFD ultrasonic crack detection against the live API to trigger replanning.</span>
          </div>
          <button
            onClick={handleInjectEmergency}
            disabled={createEmergency.isPending}
            className="min-h-11 px-2.5 py-1 text-slate-950 rounded text-[11px] font-mono font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
            style={{ backgroundColor: `var(--status-warning-fg)` }}
          >
            <AlertTriangle className="w-3 h-3" /> {createEmergency.isPending ? 'Recording…' : 'Inject Emergency Defect'}
          </button>
        </div>
      )}

      {/* Operational Hierarchy */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Immediate Risk Column */}
        <div className="rounded border border-slate-800 bg-slate-900/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                1. Immediate Risk & Defects
              </h2>
            </div>
            <button
              onClick={() => router.push('/maintenance')}
              className="text-[11px] font-mono text-sky-400 hover:underline flex items-center gap-1 cursor-pointer"
            >
              All Tasks <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {tasks.length === 0 && (
              <div className="p-3 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
                No open maintenance tasks.
              </div>
            )}
            {tasks.slice(0, 3).map((task) => (
              <button type="button"
                key={task.id}
                onClick={() => {
                  setSelectedTaskId(task.id);
                  router.push('/maintenance');
                }}
                aria-label={`Open task ${task.title}`}
                className="w-full min-h-11 text-left p-3 rounded border border-slate-800 bg-slate-950/60 hover:border-slate-700 cursor-pointer transition-all space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <DepartmentBadge dept={task.department} />
                  <RiskBadge score={task.riskScore} severity={task.severity} />
                </div>
                <div className="text-xs font-semibold text-slate-200 line-clamp-1">
                  {task.title}
                </div>
                <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between">
                  <span>Loc: {task.sectionName}</span>
                  <span className="text-amber-400">Est: {task.estimatedMinutes}m</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Today's Possession Blocks Column */}
        <div className="rounded border border-slate-800 bg-slate-900/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                2. Possessions & Corridors
              </h2>
            </div>
            <button
              onClick={() => router.push('/timeline')}
              className="text-[11px] font-mono text-sky-400 hover:underline flex items-center gap-1 cursor-pointer"
            >
              Gantt View <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {activeBlocks.length === 0 && (
              <div className="p-3 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
                No possession blocks in the active plan.
              </div>
            )}
            {activeBlocks.map((block) => (
              <button type="button"
                key={block.id}
                onClick={() => {
                  setSelectedBlockId(block.id);
                  router.push('/planner');
                }}
                aria-label={`Open possession block ${block.blockCode}`}
                className="w-full min-h-11 text-left p-3 rounded border border-slate-800 bg-slate-950/60 hover:border-emerald-500/40 cursor-pointer transition-all space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-bold" style={{ color: `var(--status-ok-fg)` }}>
                    {block.blockCode}
                  </span>
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
                    style={{
                      backgroundColor: `var(--status-ok-bg)`,
                      color: `var(--status-ok-text)`,
                      borderColor: `var(--status-ok-border)`,
                    }}
                  >
                    {block.startTime} – {block.endTime} ({block.durationMinutes}m)
                  </span>
                </div>

                <div className="text-xs font-medium text-slate-300">
                  {block.sectionName}
                </div>

                <div className="flex items-center gap-1.5 flex-wrap">
                  {block.departments.map((d, i) => (
                    <DepartmentBadge key={`${d}-${i}`} dept={d} />
                  ))}
                  <span className="text-[10px] font-mono text-slate-400 ml-auto">
                    {block.taskIds.length} Tasks Bundled
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Plan Warnings & Actions Column */}
        <div className="rounded border border-slate-800 bg-slate-900/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                3. Plan Warnings & Actions
              </h2>
            </div>
            {activePlan && (
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
                style={{
                  backgroundColor: `var(--status-info-bg)`,
                  color: `var(--status-info-text)`,
                  borderColor: `var(--status-info-border)`,
                }}
              >
                {activePlan.objectiveProfile}
              </span>
            )}
          </div>

          {!activePlan ? (
            <div className="p-3 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
              No plan generated yet. Run the optimizer from the Block Planner.
            </div>
          ) : activePlan.warnings.length === 0 ? (
            <div className="p-3 rounded border border-slate-800 bg-slate-950/70 text-xs font-mono text-slate-400">
              No solver warnings on the active plan.
            </div>
          ) : (
            <div className="space-y-2">
              {activePlan.warnings.slice(0, 5).map((w, i) => (
                <div key={i} className="p-2.5 rounded border border-slate-800/80 bg-slate-950/70 text-[11px] font-mono text-amber-300 leading-relaxed">
                  {w}
                </div>
              ))}
            </div>
          )}

          <button
            onClick={() => router.push('/planner')}
            className="w-full min-h-11 mt-2 py-1.5 text-slate-950 font-mono text-xs font-bold rounded flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            style={{ backgroundColor: `var(--status-info-fg)` }}
          >
            Review in Block Planner <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </div>
  );
};
