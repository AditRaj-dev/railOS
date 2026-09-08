/**
 * Design system token mappings for domain enums.
 * Single source of truth for status/department/objective styling and icons.
 * All color tokens defined in globals.css as CSS custom properties.
 */

import type { LucideIcon } from 'lucide-react';
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Ban,
  HelpCircle,
  Zap,
  Info,
  Archive,
  Clipboard,
  RotateCcw,
  Wrench,
  Shield,
  ShieldCheck,
  Gauge,
} from 'lucide-react';

/** Semantic status token base (CSS custom property names, no # prefix) */
export type StatusToken =
  | 'ok'
  | 'info'
  | 'caution'
  | 'warning'
  | 'critical'
  | 'blocked'
  | 'unknown';

/** Token definition: CSS vars + label + icon */
export interface TokenDef {
  token: StatusToken;
  label: string;
  icon: LucideIcon;
  bgVar: string;  // CSS custom property for background
  borderVar: string;  // CSS custom property for border
  fgVar: string;  // CSS custom property for foreground color (icon/accent)
  textVar: string;  // CSS custom property for text
}

/** Task status -> token mapping (PENDING, PLANNED, STARTED, COMPLETED, DEFERRED) */
export const TASK_STATUS_TOKENS: Record<string, TokenDef> = {
  PENDING: {
    token: 'info',
    label: 'Pending',
    icon: Clock,
    bgVar: '--status-info-bg',
    borderVar: '--status-info-border',
    fgVar: '--status-info-fg',
    textVar: '--status-info-text',
  },
  PLANNED: {
    token: 'caution',
    label: 'Planned',
    icon: Clipboard,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  STARTED: {
    token: 'warning',
    label: 'In Progress',
    icon: Zap,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
  COMPLETED: {
    token: 'ok',
    label: 'Completed',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  DEFERRED: {
    token: 'blocked',
    label: 'Deferred',
    icon: Archive,
    bgVar: '--status-blocked-bg',
    borderVar: '--status-blocked-border',
    fgVar: '--status-blocked-fg',
    textVar: '--status-blocked-text',
  },
};

/** Plan status -> token mapping (GENERATED, PROPOSED, APPROVED, REJECTED, SUPERSEDED) */
export const PLAN_STATUS_TOKENS: Record<string, TokenDef> = {
  GENERATED: {
    token: 'info',
    label: 'Generated',
    icon: Zap,
    bgVar: '--status-info-bg',
    borderVar: '--status-info-border',
    fgVar: '--status-info-fg',
    textVar: '--status-info-text',
  },
  PROPOSED: {
    token: 'caution',
    label: 'Proposed',
    icon: AlertTriangle,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  APPROVED: {
    token: 'ok',
    label: 'Approved',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  REJECTED: {
    token: 'critical',
    label: 'Rejected',
    icon: Ban,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  SUPERSEDED: {
    token: 'unknown',
    label: 'Superseded',
    icon: RotateCcw,
    bgVar: '--status-unknown-bg',
    borderVar: '--status-unknown-border',
    fgVar: '--status-unknown-fg',
    textVar: '--status-unknown-text',
  },
};

/** Possession lifecycle -> semantic token mapping. */
export const POSSESSION_STATE_TOKENS: Record<string, TokenDef> = {
  SANCTIONED: {
    token: 'caution',
    label: 'Sanctioned',
    icon: Clipboard,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  CLEARANCE_REQUESTED: {
    token: 'info',
    label: 'Clearance requested',
    icon: Clock,
    bgVar: '--status-info-bg',
    borderVar: '--status-info-border',
    fgVar: '--status-info-fg',
    textVar: '--status-info-text',
  },
  DEFERRED: {
    token: 'blocked',
    label: 'Deferred',
    icon: Archive,
    bgVar: '--status-blocked-bg',
    borderVar: '--status-blocked-border',
    fgVar: '--status-blocked-fg',
    textVar: '--status-blocked-text',
  },
  CANCELLED: {
    token: 'critical',
    label: 'Cancelled',
    icon: Ban,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  CLEARANCE_GRANTED: {
    token: 'ok',
    label: 'Clearance granted',
    icon: Shield,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  ISOLATION_IN_PROGRESS: {
    token: 'warning',
    label: 'Isolation in progress',
    icon: RotateCcw,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
  PROTECTED: {
    token: 'ok',
    label: 'Protected',
    icon: ShieldCheck,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  LIVE: {
    token: 'warning',
    label: 'Live possession',
    icon: Zap,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
  OVERRUNNING: {
    token: 'critical',
    label: 'Overrunning',
    icon: AlertTriangle,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  TESTING: {
    token: 'info',
    label: 'Testing',
    icon: RotateCcw,
    bgVar: '--status-info-bg',
    borderVar: '--status-info-border',
    fgVar: '--status-info-fg',
    textVar: '--status-info-text',
  },
  HANDBACK_REQUESTED: {
    token: 'caution',
    label: 'Handback requested',
    icon: Clock,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  FIT_CERTIFIED: {
    token: 'ok',
    label: 'Fitness certified',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  CLEARED: {
    token: 'ok',
    label: 'Cleared',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  ABANDONED: {
    token: 'critical',
    label: 'Abandoned',
    icon: Ban,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
};

export const SIGNATURE_DECISION_TOKENS: Record<string, TokenDef> = {
  GRANTED: {
    token: 'ok',
    label: 'Granted',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  REFUSED: {
    token: 'critical',
    label: 'Refused',
    icon: Ban,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  DEFERRED: {
    token: 'caution',
    label: 'Deferred',
    icon: Clock,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  WITHDRAWN: {
    token: 'blocked',
    label: 'Withdrawn',
    icon: RotateCcw,
    bgVar: '--status-blocked-bg',
    borderVar: '--status-blocked-border',
    fgVar: '--status-blocked-fg',
    textVar: '--status-blocked-text',
  },
};

/** Severity (defect codes) -> token mapping */
export const SEVERITY_TOKENS: Record<string, TokenDef> = {
  IMR: {
    token: 'critical',
    label: 'Immediate Removal',
    icon: AlertTriangle,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  IMRW: {
    token: 'critical',
    label: 'Immediate Removal (Weld)',
    icon: AlertTriangle,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
  OBS: {
    token: 'info',
    label: 'Observation',
    icon: Info,
    bgVar: '--status-info-bg',
    borderVar: '--status-info-border',
    fgVar: '--status-info-fg',
    textVar: '--status-info-text',
  },
  OMS_PEAK_HIGH: {
    token: 'warning',
    label: 'OMS Peak High',
    icon: AlertCircle,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
  POINT_SLACK_DETECTION: {
    token: 'caution',
    label: 'Point Slack',
    icon: AlertTriangle,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  OHE_DROPPING_FAULT: {
    token: 'warning',
    label: 'OHE Dropping Fault',
    icon: AlertCircle,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
};

/** Severity band (risk score interpretation) -> token mapping */
export const SEVERITY_BAND_TOKENS: Record<string, TokenDef> = {
  LOW: {
    token: 'ok',
    label: 'Low',
    icon: CheckCircle2,
    bgVar: '--status-ok-bg',
    borderVar: '--status-ok-border',
    fgVar: '--status-ok-fg',
    textVar: '--status-ok-text',
  },
  MEDIUM: {
    token: 'caution',
    label: 'Medium',
    icon: AlertTriangle,
    bgVar: '--status-caution-bg',
    borderVar: '--status-caution-border',
    fgVar: '--status-caution-fg',
    textVar: '--status-caution-text',
  },
  HIGH: {
    token: 'warning',
    label: 'High',
    icon: AlertCircle,
    bgVar: '--status-warning-bg',
    borderVar: '--status-warning-border',
    fgVar: '--status-warning-fg',
    textVar: '--status-warning-text',
  },
  CRITICAL: {
    token: 'critical',
    label: 'Critical',
    icon: AlertTriangle,
    bgVar: '--status-critical-bg',
    borderVar: '--status-critical-border',
    fgVar: '--status-critical-fg',
    textVar: '--status-critical-text',
  },
};

/** Department -> token mapping (ENGG, SNT, TRD) */
export const DEPARTMENT_TOKENS: Record<string, TokenDef> = {
  ENGG: {
    token: 'caution',
    label: 'Engineering',
    icon: Wrench,
    bgVar: '--dept-engg-bg',
    borderVar: '--dept-engg-border',
    fgVar: '--dept-engg-fg',
    textVar: '--dept-engg-text',
  },
  SNT: {
    token: 'warning',
    label: 'Signal & Telecom',
    icon: Zap,
    bgVar: '--dept-snt-bg',
    borderVar: '--dept-snt-border',
    fgVar: '--dept-snt-fg',
    textVar: '--dept-snt-text',
  },
  TRD: {
    token: 'ok',
    label: 'Traction',
    icon: Gauge,
    bgVar: '--dept-trd-bg',
    borderVar: '--dept-trd-border',
    fgVar: '--dept-trd-fg',
    textVar: '--dept-trd-text',
  },
};

/** Objective profile -> token mapping (SAFETY_FIRST, BALANCED, OPERATIONS_FIRST) */
export const OBJECTIVE_TOKENS: Record<string, TokenDef> = {
  SAFETY_FIRST: {
    token: 'critical',
    label: 'Safety First',
    icon: Shield,
    bgVar: '--obj-safety-bg',
    borderVar: '--obj-safety-border',
    fgVar: '--obj-safety-fg',
    textVar: '--obj-safety-text',
  },
  BALANCED: {
    token: 'caution',
    label: 'Balanced',
    icon: Gauge,
    bgVar: '--obj-balanced-bg',
    borderVar: '--obj-balanced-border',
    fgVar: '--obj-balanced-fg',
    textVar: '--obj-balanced-text',
  },
  OPERATIONS_FIRST: {
    token: 'unknown',
    label: 'Operations First',
    icon: Zap,
    bgVar: '--obj-operations-bg',
    borderVar: '--obj-operations-border',
    fgVar: '--obj-operations-fg',
    textVar: '--obj-operations-text',
  },
};

/**
 * Resolve severity band by risk score.
 * Implements the semantic status bands from DESIGN_SYSTEM.md section 9.
 */
export function getSeverityBand(score: number): string {
  if (score < 33) return 'LOW';
  if (score < 60) return 'MEDIUM';
  if (score < 85) return 'HIGH';
  return 'CRITICAL';
}

/**
 * Generic token lookup with fallback to UNKNOWN.
 */
export function getTokenDef(
  tokenMap: Record<string, TokenDef>,
  value: string | undefined
): TokenDef {
  if (!value) {
    return {
      token: 'unknown',
      label: 'Unknown',
      icon: HelpCircle,
      bgVar: '--status-unknown-bg',
      borderVar: '--status-unknown-border',
      fgVar: '--status-unknown-fg',
      textVar: '--status-unknown-text',
    };
  }
  return tokenMap[value] || tokenMap[Object.keys(tokenMap)[0]] || {
    token: 'unknown',
    label: 'Unknown',
    icon: HelpCircle,
    bgVar: '--status-unknown-bg',
    borderVar: '--status-unknown-border',
    fgVar: '--status-unknown-fg',
    textVar: '--status-unknown-text',
  };
}
