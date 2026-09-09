'use client';

import React from 'react';
import { useRailOSStore } from '@/store/railosStore';
import {
  usePossession,
  usePlanDetail,
  useSection,
  useMaintenanceTasks,
  useEventsSince,
  useBlockPlans,
} from '@/lib/queries';
import { pickActivePlan } from '@/lib/adapters';
import {
  X,
  Shield,
  Clock,
  AlertTriangle,
  FileText,
  Layers,
  MapPin,
  CheckCircle2,
  Activity,
} from 'lucide-react';
import Link from 'next/link';

export function ContextRail() {
  const {
    activeDrawer,
    setActiveDrawer,
    selectedBlockId,
    selectedTaskId,
    selectedSectionId,
  } = useRailOSStore();

  const plansQuery = useBlockPlans();
  const activePlan = pickActivePlan(plansQuery.data?.plans || []);
  const activePlanId = activePlan?.planId || 'plan-baseline';

  const possessionQuery = usePossession(selectedBlockId || '', {
    enabled: activeDrawer === 'block' && Boolean(selectedBlockId),
  });

  const planDetailQuery = usePlanDetail(activePlanId, {
    enabled: activeDrawer === 'plan' && Boolean(activePlanId),
  });

  const sectionQuery = useSection(selectedSectionId || '', {
    enabled: activeDrawer === 'section' && Boolean(selectedSectionId),
  });

  const maintenanceTasksQuery = useMaintenanceTasks();
  const eventsQuery = useEventsSince(0);

  if (!activeDrawer) {
    return null;
  }

  // Find task in maintenance tasks
  const rawTasks = (maintenanceTasksQuery.data?.tasks || []) as Array<Record<string, unknown>>;
  const selectedTask = selectedTaskId
    ? rawTasks.find((t) => String(t.taskId || t.id) === selectedTaskId)
    : null;

  return (
    <aside
      aria-label="Context panel"
      className="pointer-events-auto hidden lg:flex flex-col w-80 border-l border-[var(--border-default)] bg-[var(--bg-surface)] overflow-y-auto max-h-[calc(100dvh-7rem)] shadow-lg"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--border-default)] sticky top-0 bg-[var(--bg-surface)] z-10">
        <div className="flex items-center gap-2">
          {activeDrawer === 'block' && <Shield className="w-4 h-4 text-[var(--accent)]" />}
          {activeDrawer === 'task' && <FileText className="w-4 h-4 text-[var(--accent)]" />}
          {activeDrawer === 'section' && <MapPin className="w-4 h-4 text-[var(--accent)]" />}
          {activeDrawer === 'plan' && <Layers className="w-4 h-4 text-[var(--accent)]" />}
          {activeDrawer === 'alerts' && <Activity className="w-4 h-4 text-[var(--accent)]" />}
          <h2 className="text-xs font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider">
            {activeDrawer === 'block' && 'Block Possession'}
            {activeDrawer === 'task' && 'Task Inspector'}
            {activeDrawer === 'section' && 'Section Profile'}
            {activeDrawer === 'plan' && 'Plan Analysis'}
            {activeDrawer === 'alerts' && 'Live Alerts & Events'}
          </h2>
        </div>
        <button
          onClick={() => setActiveDrawer(null)}
          className="p-1 rounded hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all cursor-pointer"
          aria-label="Close context panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4 text-xs font-mono">
        {/* Drawer 1: Block Details */}
        {activeDrawer === 'block' && (
          <>
            {selectedBlockId ? (
              possessionQuery.isLoading ? (
                <div className="py-6 text-center text-[var(--text-muted)]">
                  Loading possession details…
                </div>
              ) : possessionQuery.isError ? (
                <div className="p-3 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] text-[var(--status-critical-text)]">
                  <div className="flex items-center gap-1.5 font-bold">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Error loading block</span>
                  </div>
                  <p className="mt-1 text-[11px]">{possessionIdErrorText(possessionQuery.error)}</p>
                </div>
              ) : possessionQuery.data ? (
                <div className="space-y-3">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Possession ID</span>
                    <div className="text-sm font-bold text-[var(--text-primary)]">{possessionQuery.data.possessionId}</div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">State:</span>
                    <span className="px-2 py-0.5 rounded border border-[var(--status-caution-border)] bg-[var(--status-caution-bg)] text-[var(--status-caution-text)] font-bold text-[11px]">
                      {possessionQuery.data.state}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-subtle)]">
                    <div>
                      <span className="text-[10px] uppercase text-[var(--text-muted)]">Section</span>
                      <div className="text-[var(--text-primary)]">{possessionQuery.data.sectionId}</div>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-[var(--text-muted)]">Track</span>
                      <div className="text-[var(--text-primary)]">{possessionQuery.data.track}</div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[var(--border-subtle)] space-y-1">
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Planned Window</span>
                    <div className="text-[var(--text-primary)] flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-[var(--accent)]" />
                      <span>{formatTime(possessionQuery.data.plannedStartUtc)} → {formatTime(possessionQuery.data.plannedEndUtc)}</span>
                    </div>
                  </div>

                  {possessionQuery.data.assignedTaskIds?.length > 0 && (
                    <div className="pt-2 border-t border-[var(--border-subtle)] space-y-1">
                      <span className="text-[10px] uppercase text-[var(--text-muted)]">Linked Tasks</span>
                      <div className="space-y-1">
                        {possessionQuery.data.assignedTaskIds.map((tid) => (
                          <div key={tid} className="p-1.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-secondary)]">
                            {tid}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t border-[var(--border-subtle)]">
                    <Link
                      href={`/possessions/${possessionQuery.data.possessionId}`}
                      className="block text-center w-full py-1.5 rounded bg-[var(--accent)] text-[var(--bg-canvas)] font-bold hover:opacity-90 transition-opacity"
                    >
                      Open in Possession Authority
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-[var(--text-muted)]">Block ID: {selectedBlockId}</div>
                  <div className="p-2 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-secondary)]">
                    Planned possession record. Click &quot;Possession Board&quot; for live control.
                  </div>
                </div>
              )
            ) : (
              <div className="text-center py-6 text-[var(--text-muted)]">
                Select a block on the map or timeline to inspect authority details.
              </div>
            )}
          </>
        )}

        {/* Drawer 2: Task Inspector */}
        {activeDrawer === 'task' && (
          <>
            {selectedTask ? (
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Task ID</span>
                  <div className="text-sm font-bold text-[var(--text-primary)]">{String(selectedTask.taskId || selectedTask.id)}</div>
                </div>

                <div>
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Title</span>
                  <div className="text-[var(--text-secondary)]">{String(selectedTask.title || selectedTask.taskType || 'Maintenance Task')}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-subtle)]">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Department</span>
                    <div className="text-[var(--accent)] font-bold">{String(selectedTask.department || 'ENGG')}</div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Severity</span>
                    <div className="text-[var(--text-primary)] font-bold">{String(selectedTask.severity ?? 5)} / 10</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-subtle)]">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Duration</span>
                    <div className="text-[var(--text-primary)]">{String(selectedTask.estimatedDuration || 120)} min</div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Block Type</span>
                    <div className="text-[var(--text-primary)]">{String(selectedTask.blockType || 'TRAFFIC')}</div>
                  </div>
                </div>

                <div className="pt-2 border-t border-[var(--border-subtle)]">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Section / Track</span>
                  <div className="text-[var(--text-secondary)]">
                    {String(selectedTask.sectionId || '—')} · {String(selectedTask.track || '—')}
                  </div>
                </div>

                <div className="pt-2 border-t border-[var(--border-subtle)]">
                  <Link
                    href="/maintenance"
                    className="block text-center w-full py-1.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-strong)] text-[var(--text-primary)] font-bold hover:border-[var(--accent)]"
                  >
                    View in Maintenance Intelligence
                  </Link>
                </div>
              </div>
            ) : selectedTaskId ? (
              <div className="space-y-2">
                <span className="text-[10px] uppercase text-[var(--text-muted)]">Task ID</span>
                <div className="text-sm font-bold text-[var(--text-primary)]">{selectedTaskId}</div>
                <p className="text-[var(--text-muted)]">Full task attributes loading or task outside active query filter.</p>
              </div>
            ) : (
              <div className="text-center py-6 text-[var(--text-muted)]">
                Select a task from Maintenance Intelligence to view inspection details.
              </div>
            )}
          </>
        )}

        {/* Drawer 3: Section Profile */}
        {activeDrawer === 'section' && (
          <>
            {selectedSectionId ? (
              sectionQuery.isLoading ? (
                <div className="py-6 text-center text-[var(--text-muted)]">Loading section profile…</div>
              ) : sectionQuery.data ? (
                <div className="space-y-3">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Section</span>
                    <div className="text-sm font-bold text-[var(--text-primary)]">{sectionQuery.data.name}</div>
                    <div className="text-[11px] text-[var(--text-muted)]">{sectionQuery.data.code} ({sectionQuery.data.sectionId})</div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-subtle)]">
                    <div>
                      <span className="text-[10px] uppercase text-[var(--text-muted)]">From Station</span>
                      <div className="text-[var(--accent)] font-bold">{sectionQuery.data.fromStation}</div>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-[var(--text-muted)]">To Station</span>
                      <div className="text-[var(--text-primary)] font-bold">{sectionQuery.data.toStation}</div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[var(--border-subtle)]">
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Tracks & Metrics</span>
                    <div className="text-[var(--text-secondary)] mt-0.5">
                      Tracks: {Array.isArray(sectionQuery.data.tracks) ? sectionQuery.data.tracks.join(', ') : 'UP, DOWN'}
                    </div>
                    <div className="text-[var(--text-muted)] text-[11px] mt-1 flex justify-between">
                      <span>Debt: {sectionQuery.data.metrics?.maintenanceDebt ?? 0}</span>
                      <span>Defects: {sectionQuery.data.metrics?.criticalDefectCount ?? 0}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[var(--border-subtle)]">
                    <Link
                      href="/network"
                      className="block text-center w-full py-1.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-strong)] text-[var(--text-primary)] font-bold hover:border-[var(--accent)]"
                    >
                      Open in Network Digital Twin
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="text-[var(--text-muted)]">Section ID: {selectedSectionId}</div>
                  <div className="p-2 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-secondary)]">
                    Section profile details will appear here.
                  </div>
                </div>
              )
            ) : (
              <div className="text-center py-6 text-[var(--text-muted)]">
                Select a section to inspect corridor topology and limits.
              </div>
            )}
          </>
        )}

        {/* Drawer 4: Plan Analysis */}
        {activeDrawer === 'plan' && (
          <>
            {planDetailQuery.isLoading ? (
              <div className="py-6 text-center text-[var(--text-muted)]">Loading plan metrics…</div>
            ) : (
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Active Optimization Plan</span>
                  <div className="text-sm font-bold text-[var(--text-primary)]">
                    {planDetailQuery.data?.planId || activePlan?.planId || 'plan-baseline'}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Status:</span>
                  <span className="px-2 py-0.5 rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] text-[var(--status-ok-text)] font-bold text-[11px]">
                    {planDetailQuery.data?.status || activePlan?.status || 'APPROVED'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border-subtle)]">
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Objective</span>
                    <div className="text-[var(--accent)] font-bold">
                      {planDetailQuery.data?.objectiveProfile || activePlan?.objectiveProfile || 'BALANCED'}
                    </div>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-[var(--text-muted)]">Horizon</span>
                    <div className="text-[var(--text-primary)] font-bold">
                      {planDetailQuery.data?.horizonMinutes ? `${planDetailQuery.data.horizonMinutes}m` : '360m'}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-[var(--border-subtle)] space-y-1">
                  <span className="text-[10px] uppercase text-[var(--text-muted)]">Plan Metrics</span>
                  <div className="p-2 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] space-y-1">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Scheduled Blocks:</span>
                      <span className="font-bold text-[var(--text-primary)]">
                        {planDetailQuery.data?.blocks?.length ?? activePlan?.blocks?.length ?? 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Task Assignments:</span>
                      <span className="font-bold text-[var(--text-primary)]">
                        {planDetailQuery.data?.assignments?.length ?? activePlan?.assignments?.length ?? 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Unassigned Tasks:</span>
                      <span className="font-bold text-[var(--text-primary)]">
                        {planDetailQuery.data?.unassigned?.length ?? activePlan?.unassigned?.length ?? 0}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-[var(--border-subtle)]">
                  <Link
                    href="/plans"
                    className="block text-center w-full py-1.5 rounded bg-[var(--accent)] text-[var(--bg-canvas)] font-bold hover:opacity-90 transition-opacity"
                  >
                    Open Plan Sanctions
                  </Link>
                </div>
              </div>
            )}
          </>
        )}

        {/* Drawer 5: Alerts & Events */}
        {activeDrawer === 'alerts' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase text-[var(--text-muted)]">Recent Events</span>
              <span className="text-[10px] text-[var(--accent)]">Live Socket</span>
            </div>

            {eventsQuery.isLoading ? (
              <div className="py-4 text-center text-[var(--text-muted)]">Loading event log…</div>
            ) : (eventsQuery.data?.events || []).length > 0 ? (
              <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                {(eventsQuery.data?.events as Array<Record<string, unknown>>).slice(0, 15).map((ev, i) => (
                  <div key={i} className="p-2 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] space-y-0.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-bold text-[var(--text-primary)]">{String(ev.type || 'EVENT')}</span>
                      <span className="text-[var(--text-muted)]">{String(ev.timestamp || 'Just now').slice(-8)}</span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] break-words">
                      {String(ev.description || ev.message || JSON.stringify(ev))}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-secondary)]">
                <div className="flex items-center gap-1.5 font-bold text-[var(--status-ok-fg)]">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>No active critical alerts</span>
                </div>
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                  Corridor signaling, power grids, and train movements operating within nominal safety thresholds.
                </p>
              </div>
            )}

            <div className="pt-2 border-t border-[var(--border-subtle)]">
              <Link
                href="/timeline"
                className="block text-center w-full py-1.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-strong)] text-[var(--text-primary)] font-bold hover:border-[var(--accent)]"
              >
                Inspect Operational Gantt
              </Link>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return Number.isNaN(d.valueOf()) ? iso : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

function possessionIdErrorText(err: unknown): string {
  if (err && typeof err === 'object' && 'message' in err) {
    return String((err as { message: unknown }).message);
  }
  return 'Could not retrieve possession authority state.';
}
