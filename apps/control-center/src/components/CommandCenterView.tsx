'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { useAnalyticsSummary } from '@/lib/queries';
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
  const { 
    tasks,
    activePlan, 
    setActiveScreen, 
    setSelectedTaskId,
    setSelectedBlockId,
    triggerEmergencyFlaw,
    isEmergencyActive
  } = useRailOSStore();

  const criticalTasks = tasks.filter(t => t.severity === 'CRITICAL' || t.riskScore >= 85);
  const overdueTasks = tasks.filter(t => t.priorityBand === 'P0_EMERGENCY');
  const activeBlocks = activePlan.blocks.filter(b => b.status === 'ACTIVE' || b.status === 'PLANNED');

  const displayCritical = liveAnalytics?.criticalDefects !== undefined ? liveAnalytics.criticalDefects : criticalTasks.length;
  const displayDebt = liveAnalytics?.maintenanceDebt ? `${liveAnalytics.maintenanceDebt} hrs` : "76.5%";

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
          trend="+1 in 2 hrs"
        />
        <MetricCard 
          label="Overdue Backlog" 
          value={overdueTasks.length} 
          subValue="Safety Violations Pending" 
          status={overdueTasks.length > 0 ? "caution" : "normal"}
          icon={Clock}
          trend="30 km/h TSR"
        />
        <MetricCard 
          label="Active & Planned Blocks" 
          value={activeBlocks.length} 
          subValue="2 Possession Windows" 
          status="highlight"
          icon={ShieldAlert}
          trend="88.4% Utilization"
        />
        <MetricCard 
          label="Corridor Pressure" 
          value="148%" 
          subValue="NDLS-ALJN Quad-Track" 
          status="caution"
          icon={Activity}
          trend="Line Saturation"
        />
        <MetricCard 
          label="Maintenance Debt" 
          value={displayDebt} 
          subValue="Reduction Target Achieved" 
          status="normal"
          icon={TrendingUp}
          trend="-24.5 hrs"
        />
        <MetricCard 
          label="Fleet Availability" 
          value="94.2%" 
          subValue="Power & Signal Online" 
          status="normal"
          icon={CheckCircle2}
          trend="Nominal"
        />
      </div>

      {/* Emergency Simulation Trigger Banner */}
      {isEmergencyActive ? (
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
                CRITICAL EMERGENCY FLAW DETECTED: Rail Fracture at Km 1332/08 (Down Line)
              </div>
              <div className="text-xs opacity-80" style={{ color: `var(--status-critical-text)` }}>
                Acoustic vibration threshold breached. Caution Order 0 km/h (Stop Dead). Dynamic Replanning required immediately.
              </div>
            </div>
          </div>
          <button
            onClick={() => router.push('/planner')}
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
            <span className="text-slate-400">DEMO INJECTION:</span>
            <span>Simulate sudden USFD ultrasonic crack detection to trigger live replanning workflow.</span>
          </div>
          <button
            onClick={triggerEmergencyFlaw}
            className="min-h-11 px-2.5 py-1 text-slate-950 rounded text-[11px] font-mono font-bold flex items-center gap-1 transition-colors"
            style={{ backgroundColor: `var(--status-warning-fg)` }}
          >
            <AlertTriangle className="w-3 h-3" /> Inject Emergency Defect
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
            {activePlan.blocks.map((block) => (
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
                  {block.departments.map(d => (
                    <DepartmentBadge key={d} dept={d} />
                  ))}
                  <span className="text-[10px] font-mono text-slate-400 ml-auto">
                    {block.tasks.length} Tasks Bundled
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Recommended Actions & Optimizer Column */}
        <div className="rounded border border-slate-800 bg-slate-900/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                3. Coordinated Actions
              </h2>
            </div>
            <span
              className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
              style={{
                backgroundColor: `var(--status-info-bg)`,
                color: `var(--status-info-text)`,
                borderColor: `var(--status-info-border)`,
              }}
            >
              Active: {activePlan.mode}
            </span>
          </div>

          <div className="p-3 rounded border border-slate-800 bg-slate-950/70 space-y-2">
            <div className="text-xs font-mono text-slate-300 font-bold flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: `var(--status-info-fg)` }} />
              Coordinated Shadow Block Recommendation
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Combine S&T Point Machine Overhaul (Pt 204B) into the TRD 25kV Catenary Isolation window between 13:45 and 15:00 on the GZB Up Line.
            </p>
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono">
              <span style={{ color: `var(--status-ok-fg)` }}>Headway Lull: 85m</span>
              <span className="text-slate-400">Saved: 60m duplicate line hold</span>
            </div>
          </div>

          <div className="p-3 rounded border border-slate-800 bg-slate-950/70 space-y-2">
            <div className="text-xs font-mono text-slate-300 font-bold flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: `var(--status-warning-fg)` }} />
              Emergency Weld Clamping (Km 1324)
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Pre-approved 90-minute traffic possession required before 16:55 to avoid delaying Howrah Rajdhani Express (12302).
            </p>
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
    </div>
  );
};
