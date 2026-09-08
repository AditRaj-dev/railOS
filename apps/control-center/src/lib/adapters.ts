/**
 * Adapters from real RailOS API payloads (railos_model, camelCase-serialized) to the
 * lightweight display shapes the control-center views render.
 *
 * The API's domain vocabulary (severity 1-10, minute-of-day offsets, ENGG/SNT/TRD
 * department codes) differs from the older synthetic UI types in `types/railos.ts`.
 * These functions do the (lossy, honest) conversion — they never invent narrative
 * content the backend doesn't provide.
 */

import type { Department } from '../types/railos';
import type { RailOSPlan } from './api';

const DEPARTMENT_LABELS: Record<string, Department> = {
  ENGG: 'CIVIL',
  SNT: 'S_AND_T',
  TRD: 'TRD',
};

export function toDisplayDepartment(dept: string): Department {
  return DEPARTMENT_LABELS[dept] ?? 'OPERATING';
}

/** Convert a minute-of-day offset (as used by the optimizer) to an HH:MM clock string. */
export function minuteToClock(minute: number): string {
  const normalized = ((Math.round(minute) % 1440) + 1440) % 1440;
  const h = Math.floor(normalized / 60);
  const m = normalized % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export type SeverityBand = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

/** Map the API's 1-10 severity scale to the badge bands the UI already understands. */
export function severityToBand(severity: number): SeverityBand {
  if (severity >= 9) return 'CRITICAL';
  if (severity >= 7) return 'HIGH';
  if (severity >= 4) return 'MEDIUM';
  return 'LOW';
}

/** Map the API's 1-10 severity scale to RiskBadge's 0-100 score scale. */
export function severityToScore(severity: number): number {
  return Math.round(severity * 10);
}

export interface DisplayTask {
  id: string;
  department: Department;
  title: string;
  sectionId: string;
  sectionName: string;
  severity: SeverityBand;
  riskScore: number;
  estimatedMinutes: number;
  blockRequirement: string;
  status: string;
  assetId: string;
}

export function toDisplayTask(task: Record<string, unknown>, sectionNames: Map<string, string>): DisplayTask {
  const severity = Number(task.severity ?? 0);
  const sectionId = String(task.sectionId ?? '');
  const assetId = String(task.assetId ?? '');
  const taskType = String(task.taskType ?? 'MAINTENANCE').replaceAll('_', ' ');
  return {
    id: String(task.taskId ?? ''),
    department: toDisplayDepartment(String(task.department ?? '')),
    title: `${taskType}${assetId ? ` — ${assetId}` : ''}`,
    sectionId,
    sectionName: sectionNames.get(sectionId) ?? sectionId,
    severity: severityToBand(severity),
    riskScore: severityToScore(severity),
    estimatedMinutes: Number(task.estimatedDuration ?? 0),
    blockRequirement: task.blockRequired ? String(task.blockType ?? 'TRAFFIC') : 'NONE',
    status: String(task.status ?? 'PENDING'),
    assetId,
  };
}

export interface DisplayBlock {
  id: string;
  blockCode: string;
  sectionId: string;
  sectionName: string;
  track: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  type: string;
  departments: Department[];
  taskIds: string[];
}

export function toDisplayBlock(
  block: RailOSPlan['blocks'][number],
  sectionNames: Map<string, string>
): DisplayBlock {
  return {
    id: block.blockId,
    blockCode: block.blockId,
    sectionId: block.sectionId,
    sectionName: sectionNames.get(block.sectionId) ?? block.sectionId,
    track: block.track,
    startTime: minuteToClock(block.start),
    endTime: minuteToClock(block.end),
    durationMinutes: Math.max(0, block.end - block.start),
    type: block.blockType,
    departments: (block.departments || []).map(toDisplayDepartment),
    taskIds: block.taskIds || [],
  };
}

export interface DisplayTrain {
  id: string;
  sectionId: string;
  track: string;
  entryClock: string;
  exitClock: string;
  delayMinutes: number;
  priority: number;
}

export function toDisplayTrain(train: Record<string, unknown>): DisplayTrain {
  return {
    id: String(train.trainId ?? ''),
    sectionId: String(train.sectionId ?? ''),
    track: String(train.track ?? 'UP'),
    entryClock: minuteToClock(Number(train.entry ?? 0)),
    exitClock: minuteToClock(Number(train.exit ?? 0)),
    delayMinutes: Number(train.delayMinutes ?? 0),
    priority: Number(train.priority ?? 0),
  };
}

/** Pick the plan a dashboard should treat as "the active plan": prefer APPROVED, else the newest version. */
export function pickActivePlan(plans: RailOSPlan[]): RailOSPlan | null {
  if (plans.length === 0) return null;
  const ranked = [...plans].sort((a, b) => {
    const statusRank = (p: RailOSPlan) => (p.status === 'APPROVED' ? 1 : 0);
    const byStatus = statusRank(b) - statusRank(a);
    if (byStatus !== 0) return byStatus;
    return b.planVersion - a.planVersion;
  });
  return ranked[0];
}

export function buildSectionNameMap(sections: Array<{ sectionId: string; name: string }>): Map<string, string> {
  return new Map(sections.map((s) => [s.sectionId, s.name]));
}
