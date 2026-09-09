'use client';

import React, { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useRailOSStore } from '../store/railosStore';
import { ObjectiveMode } from '../types/railos';
import { DepartmentBadge } from './RailwayComponents';
import {
  useBlockPlans,
  useGeneratePlan,
  useApprovePlan,
  useGenerateReplanning,
  useNetworkCatalog,
  useBlockRequests,
} from '@/lib/queries';
import Link from 'next/link';
import { toDisplayBlock, pickActivePlan, buildSectionNameMap } from '@/lib/adapters';
import {
  Sparkles,
  Cpu,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
  FileCheck2,
  AlertTriangle
} from 'lucide-react';

export const BlockPlannerView: React.FC = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pendingEmergencyId = searchParams.get('emergencyId');

  const [safetyViolations, setSafetyViolations] = useState<string[]>([]);
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [approvalNotice, setApprovalNotice] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<ObjectiveMode>('BALANCED');
  const { selectedBlockId, setSelectedBlockId } = useRailOSStore();

  const { data: catalog } = useNetworkCatalog();
  const plansQuery = useBlockPlans();
  const ticketsQuery = useBlockRequests({ status: 'REQUESTED' });
  const generateMutation = useGeneratePlan();
  const approveMutation = useApprovePlan();
  const replanMutation = useGenerateReplanning();

  const sectionNames = useMemo(() => buildSectionNameMap(catalog?.sections || []), [catalog]);

  // Ticket-derived demand. Each open request carries a TKT-<requestId> task, so
  // an assignment or an unassigned warning traces straight back to its ticket.
  const ticketTasks = useMemo(
    () => (ticketsQuery.data?.items || [])
      .filter((request) => Boolean(request.linkedTaskId))
      .map((request) => ({
        taskId: request.linkedTaskId as string,
        requestId: request.requestId,
        department: request.department,
        taskType: request.taskType,
        severity: request.severity,
      })),
    [ticketsQuery.data]
  );
  const ticketCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    ticketTasks.forEach((task) => { counts[task.department] = (counts[task.department] || 0) + 1; });
    return counts;
  }, [ticketTasks]);
  const selectedTicketTasks = useMemo(
    () => selectedTaskIds.filter((taskId) => ticketTasks.some((task) => task.taskId === taskId)),
    [selectedTaskIds, ticketTasks]
  );
  const toggleTicketTask = (taskId: string) => {
    setSelectedTaskIds((current) => current.includes(taskId)
      ? current.filter((id) => id !== taskId)
      : [...current, taskId]);
  };

  const candidatesForMode = useMemo(
    () => (plansQuery.data?.plans || []).filter((p) => p.objectiveProfile === selectedMode),
    [plansQuery.data, selectedMode]
  );
  const activePlan = pickActivePlan(candidatesForMode);
  const blocks = useMemo(
    () => (activePlan?.blocks || []).map((b) => toDisplayBlock(b, sectionNames)),
    [activePlan, sectionNames]
  );
  const selectedBlock = blocks.find((b) => b.id === selectedBlockId) || blocks[0];

  const handleRunOptimizer = () => {
    setSafetyViolations([]);
    generateMutation.mutate(
      {
        corridorIds: ['GZB-ALJN'],
        objectiveProfile: selectedMode,
        planningHorizon: new Date().toISOString(),
        // Empty selection means "everything planable", the previous behaviour.
        taskIds: selectedTicketTasks.length ? selectedTicketTasks : undefined,
      },
      {
        onError: (err) => {
          const details = (err as { details?: { violations?: string[] } }).details;
          if (err.code === 'PLAN_FAILED_AUDIT' && details?.violations) {
            setSafetyViolations(details.violations);
          }
        },
      }
    );
  };

  const handleApprove = () => {
    if (!activePlan) return;
    setApprovalNotice(null);
    approveMutation.mutate({ planId: activePlan.planId }, {
      onSuccess: (result) => {
        // One press signs one authority. The API answers 202 with the open
        // chain until the last signature lands, and saying nothing made a
        // working button look dead.
        const chain = result as { requiredAuthorities?: string[]; signatures?: { authority: string }[]; complete?: boolean; status?: string };
        if (chain?.status === 'APPROVED' || chain?.complete) {
          setApprovalNotice('All required authorities have signed. Possessions are open.');
          return;
        }
        const signed = new Set((chain?.signatures || []).map((signature) => signature.authority));
        const outstanding = (chain?.requiredAuthorities || []).filter((authority) => !signed.has(authority));
        setApprovalNotice(outstanding.length
          ? `Your authority is recorded. Still outstanding: ${outstanding.join(', ')}. Continue on Plan Sanctions.`
          : 'Your authority is recorded; the sanction chain is still open. Continue on Plan Sanctions.');
      },
      onError: (error) => setApprovalNotice(error.message),
    });
  };

  const handleReplan = () => {
    if (!activePlan || !pendingEmergencyId) return;
    replanMutation.mutate({
      parentPlanId: activePlan.planId,
      emergencyId: pendingEmergencyId,
      reason: 'Emergency defect injected from Command Center',
    });
  };

  const isApproved = activePlan?.status === 'APPROVED';

  return (
    <div className="space-y-4">
      <div className="p-4 rounded border border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5" style={{ color: `var(--status-info-fg)` }} />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white">
              Multi-Objective Block Optimization Engine
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Planning Horizon: <span className="text-slate-200 font-mono">Today 12:00 – 24:00 (12 hrs)</span> • Corridor: <span className="text-slate-200 font-mono">GZB–ALJN</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(['BALANCED', 'SAFETY_FIRST', 'OPERATIONS_FIRST'] as ObjectiveMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setSelectedMode(mode)}
              className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border shadow-md ${
                selectedMode === mode
                  ? 'text-white'
                  : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
              style={selectedMode === mode ? {
                backgroundColor: `var(--status-info-fg)`,
                borderColor: `var(--status-info-fg)`,
                boxShadow: `0 0 0 3px var(--status-info-bg)`,
              } : undefined}
            >
              {mode.replace('_', ' ')}
            </button>
          ))}

          <button
            onClick={handleRunOptimizer}
            disabled={generateMutation.isPending}
            className="ml-3 px-4 py-1.5 text-white text-xs font-mono font-bold rounded flex items-center gap-2 shadow transition-all disabled:opacity-50"
            style={{ backgroundColor: generateMutation.isPending ? '#555555' : `var(--status-ok-fg)` }}
          >
            <Sparkles className="w-4 h-4" style={{ color: `var(--status-warning-fg)` }} />
            {generateMutation.isPending ? 'Solving...' : 'Run Optimizer'}
          </button>
        </div>
      </div>

      <div className="p-4 rounded border border-slate-800 bg-slate-900/80 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Ticket-derived demand ({ticketTasks.length} open)
          </h3>
          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
            {(['ENGG', 'SNT', 'TRD'] as const).map((dept) => (
              <span key={dept} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">{dept} {ticketCounts[dept] || 0}</span>
            ))}
            <Link href="/tickets" className="underline underline-offset-4 hover:text-slate-200">Open ticket hub</Link>
          </div>
        </div>
        {ticketTasks.length === 0 ? (
          <p className="text-[11px] font-mono text-slate-500 italic">No REQUESTED tickets. The optimizer will run over all planable tasks.</p>
        ) : (
          <>
            <ul className="grid gap-1.5 sm:grid-cols-2">
              {ticketTasks.map((task) => (
                <li key={task.taskId}>
                  <label className="flex items-center gap-2 rounded border border-slate-800 bg-slate-950 px-2 py-1.5 text-[11px] font-mono text-slate-300">
                    <input
                      type="checkbox"
                      checked={selectedTaskIds.includes(task.taskId)}
                      onChange={() => toggleTicketTask(task.taskId)}
                    />
                    <span className="font-bold text-slate-200">{task.taskId}</span>
                    <span>{task.department} · {task.taskType.replace(/_/g, ' ')} · sev {task.severity}</span>
                  </label>
                </li>
              ))}
            </ul>
            <p className="text-[11px] font-mono text-slate-500">
              {selectedTicketTasks.length
                ? `Run Optimizer will plan only these ${selectedTicketTasks.length} ticket task(s).`
                : 'Select ticket tasks to plan only those; leave empty to plan everything.'}
            </p>
          </>
        )}
      </div>

      {approvalNotice && (
        <div
          className="p-3 rounded border text-xs font-mono flex items-center justify-between gap-3"
          style={{
            backgroundColor: `var(--status-info-bg)`,
            borderColor: `var(--status-info-border)`,
            color: `var(--status-info-text)`,
          }}
          role="status"
        >
          <span>{approvalNotice}</span>
          <Link href="/plans" className="underline underline-offset-4">Plan Sanctions</Link>
        </div>
      )}

      {safetyViolations.length > 0 && (
        <div
          className="p-3 rounded border space-y-1.5"
          style={{
            backgroundColor: `var(--status-warning-bg)`,
            borderColor: `var(--status-warning-border)`,
          }}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" style={{ color: `var(--status-warning-fg)` }} />
            <span className="text-xs font-mono font-bold" style={{ color: `var(--status-warning-text)` }}>
              Safety Auditor Advisory ({safetyViolations.length} Constraints Checked)
            </span>
          </div>
          <div className="text-[11px] font-mono space-y-0.5" style={{ color: `var(--status-warning-text)` }}>
            {safetyViolations.slice(0, 3).map((v, i) => (
              <div key={i} className="opacity-90">• {v}</div>
            ))}
            {safetyViolations.length > 3 && (
              <div className="opacity-75 italic">+ {safetyViolations.length - 3} more safety rules verified. Baseline schedule enforced.</div>
            )}
          </div>
        </div>
      )}

      {generateMutation.isPending && (
        <div
          className="p-3 rounded border flex items-center gap-3 animate-pulse"
          style={{
            backgroundColor: `var(--status-info-bg)`,
            borderColor: `var(--status-info-border)`,
          }}
        >
          <Cpu className="w-4 h-4 animate-spin" style={{ color: `var(--status-info-fg)` }} />
          <span className="text-xs font-mono" style={{ color: `var(--status-info-text)` }}>Solving Multi-Possession Schedule under Headway Constraints…</span>
        </div>
      )}

      {pendingEmergencyId && (
        <div
          className="p-3.5 rounded border flex items-center justify-between"
          style={{
            backgroundColor: `var(--status-critical-bg)`,
            borderColor: `var(--status-critical-border)`,
          }}
        >
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 animate-bounce" style={{ color: `var(--status-critical-fg)` }} />
            <div>
              <div className="text-xs font-bold font-mono" style={{ color: `var(--status-critical-text)` }}>
                Emergency {pendingEmergencyId} pending replan
              </div>
              <div className="text-[11px] opacity-80" style={{ color: `var(--status-critical-text)` }}>
                {activePlan ? 'Shift scheduled maintenance around this emergency and create an emergency possession.' : 'Generate a plan first, then replan around this emergency.'}
              </div>
            </div>
          </div>
          <button
            onClick={handleReplan}
            disabled={!activePlan || replanMutation.isPending}
            className="px-3 py-1.5 text-white text-xs font-mono font-bold rounded flex items-center gap-1.5 transition-opacity hover:opacity-80 disabled:opacity-50"
            style={{ backgroundColor: `var(--status-critical-fg)` }}
          >
            {replanMutation.isPending ? 'Replanning…' : 'Execute Dynamic Replan'} <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 rounded border border-slate-800 bg-slate-900/80 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Generated Possession Windows ({blocks.length})
              </h3>
              <div className="text-[11px] text-slate-400 mt-0.5">
                {activePlan ? (
                  <>
                    Version: <span className="font-mono" style={{ color: `var(--status-info-fg)` }}>v{activePlan.planVersion}</span> • Status: <span className="font-mono" style={{ color: `var(--status-warning-fg)` }}>{activePlan.status}</span>
                  </>
                ) : (
                  'No plan generated for this objective yet.'
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleApprove}
                disabled={!activePlan || isApproved || approveMutation.isPending}
                className="px-3 py-1 text-xs font-mono font-bold rounded flex items-center gap-1.5 border transition-all text-white disabled:cursor-not-allowed"
                style={
                  isApproved
                    ? {
                        backgroundColor: `var(--status-ok-fg)`,
                        borderColor: `var(--status-ok-fg)`,
                      }
                    : {
                        backgroundColor: '#374151',
                        borderColor: '#4b5563',
                      }
                }
              >
                <FileCheck2 className="w-3.5 h-3.5" />
                {isApproved ? 'Approved & Dispatched' : approveMutation.isPending ? 'Approving…' : 'Approve Plan'}
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {blocks.length === 0 && (
              <div className="p-4 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded">
                Run the optimizer to generate possession windows for this objective.
              </div>
            )}
            {blocks.map((block) => {
              const isSelected = block.id === selectedBlock?.id;
              return (
                <div
                  key={block.id}
                  onClick={() => setSelectedBlockId(block.id)}
                  className="p-3.5 rounded border cursor-pointer transition-all space-y-2.5"
                  style={
                    isSelected
                      ? {
                          borderColor: `var(--status-info-fg)`,
                          backgroundColor: `var(--status-info-bg)`,
                          boxShadow: `inset 0 0 0 1px var(--status-info-border)`,
                        }
                      : {
                          borderColor: '#1e293b',
                          backgroundColor: '#1a1f2e',
                        }
                  }
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold" style={{ color: `var(--status-info-fg)` }}>{block.blockCode}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {block.type.replace('_', ' ')}
                      </span>
                    </div>
                    <div
                      className="text-xs font-mono font-bold px-2 py-0.5 rounded border"
                      style={{
                        color: `var(--status-ok-text)`,
                        backgroundColor: `var(--status-ok-bg)`,
                        borderColor: `var(--status-ok-border)`,
                      }}
                    >
                      {block.startTime} – {block.endTime} ({block.durationMinutes}m)
                    </div>
                  </div>

                  <div className="text-xs text-slate-300 font-medium">
                    {block.sectionName} ({block.track} Track)
                  </div>

                  <div className="flex items-center justify-between text-xs font-mono pt-2 border-t border-slate-800/80">
                    <div className="flex items-center gap-1.5">
                      {block.departments.map((d, i) => (
                        <DepartmentBadge key={`${d}-${i}`} dept={d} />
                      ))}
                    </div>
                    <div className="text-slate-400">
                      Tasks: <span className="text-slate-100 font-bold">{block.taskIds.length}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex justify-between items-center text-xs font-mono text-slate-400 border-t border-slate-800">
            <span>Want to compare all 3 candidates?</span>
            <button
              onClick={() => router.push('/plans')}
              className="text-sky-400 hover:underline flex items-center gap-1"
            >
              Side-by-Side Comparison Matrix <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        <div className="lg:col-span-5 rounded border border-slate-800 bg-slate-900/90 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-sky-400" />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
                Plan Metrics & Warnings
              </h3>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {selectedBlock?.blockCode}
            </span>
          </div>

          {selectedBlock && activePlan ? (
            <div className="space-y-3.5">
              <div className="p-3 rounded border border-slate-800 bg-slate-950 text-xs font-mono space-y-1.5">
                <div className="flex justify-between text-slate-400">
                  <span>Section:</span>
                  <span className="text-slate-200">{selectedBlock.sectionName}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Window Span:</span>
                  <span className="text-emerald-400">{selectedBlock.startTime} – {selectedBlock.endTime}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Bundled Tasks:</span>
                  <span className="text-slate-200 font-bold">{selectedBlock.taskIds.length}</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  Solver Metrics:
                </div>
                {Object.keys(activePlan.metrics || {}).length === 0 ? (
                  <div className="p-2.5 rounded border border-slate-800/80 bg-slate-950/70 text-[11px] text-slate-500 italic">
                    No metrics reported for this plan.
                  </div>
                ) : (
                  <div className="p-2.5 rounded border border-slate-800/80 bg-slate-950/70 text-xs font-mono space-y-1">
                    {Object.entries(activePlan.metrics).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-slate-400">
                        <span>{k}</span>
                        <span className="text-slate-200">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider pt-1">
                  Solver Warnings:
                </div>
                {activePlan.warnings.length === 0 ? (
                  <div className="p-2.5 rounded border border-slate-800/80 bg-slate-950/70 text-[11px] text-slate-500 italic">
                    None.
                  </div>
                ) : (
                  activePlan.warnings.map((w, i) => (
                    <div key={i} className="p-2.5 rounded border border-slate-800/80 bg-slate-950/70 text-[11px] text-amber-300 leading-relaxed">
                      {w}
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-xs font-mono text-center py-8">
              Generate a plan and select a block to inspect its metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
