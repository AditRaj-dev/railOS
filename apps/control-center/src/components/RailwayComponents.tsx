import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  status?: 'normal' | 'caution' | 'critical' | 'highlight';
  icon?: LucideIcon;
  trend?: string;
}

/**
 * MetricCard: Displays a metric with semantic status styling.
 * Colors use CSS custom properties from globals.css via inline styles.
 * Status indicator dot + label ensure color is not the only signal.
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  status = 'normal',
  icon: Icon,
  trend
}) => {
  // Map status to CSS variable groups
  const statusVars: Record<string, { bg: string; border: string; fg: string; text: string }> = {
    normal: { bg: '--status-ok-bg', border: '--status-ok-border', fg: '--status-ok-fg', text: '--status-ok-text' },
    caution: { bg: '--status-caution-bg', border: '--status-caution-border', fg: '--status-caution-fg', text: '--status-caution-text' },
    critical: { bg: '--status-critical-bg', border: '--status-critical-border', fg: '--status-critical-fg', text: '--status-critical-text' },
    highlight: { bg: '--status-info-bg', border: '--status-info-border', fg: '--status-info-fg', text: '--status-info-text' }
  };

  const vars = statusVars[status];

  return (
    <div
      className="p-3.5 rounded border flex flex-col justify-between transition-all duration-150 relative overflow-hidden"
      style={{
        backgroundColor: `var(${vars.bg})`,
        borderColor: `var(${vars.border})`,
        color: `var(${vars.text})`,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-mono tracking-wider uppercase text-slate-400 font-medium">
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: `var(${vars.fg})` }}
          />
          {Icon && <Icon className="w-3.5 h-3.5 text-slate-400" />}
        </div>
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-white">
          {value}
        </span>
        {trend && (
          <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700">
            {trend}
          </span>
        )}
      </div>

      {subValue && (
        <div className="mt-1 text-[11px] text-slate-400 font-sans truncate">
          {subValue}
        </div>
      )}
    </div>
  );
};

/**
 * DepartmentBadge: Displays department with semantic styling.
 * Colors use CSS custom properties from globals.css.
 */
export const DepartmentBadge: React.FC<{ dept: 'CIVIL' | 'S_AND_T' | 'TRD' | 'OPERATING' }> = ({ dept }) => {
  const configs: Record<string, { label: string; vars: { bg: string; border: string; text: string } }> = {
    CIVIL: { label: 'ENG / TRACK', vars: { bg: '--dept-engg-bg', border: '--dept-engg-border', text: '--dept-engg-text' } },
    S_AND_T: { label: 'S&T / SIGNAL', vars: { bg: '--dept-snt-bg', border: '--dept-snt-border', text: '--dept-snt-text' } },
    TRD: { label: 'TRD / OHE', vars: { bg: '--dept-trd-bg', border: '--dept-trd-border', text: '--dept-trd-text' } },
    OPERATING: { label: 'OPERATIONS', vars: { bg: '--status-unknown-bg', border: '--status-unknown-border', text: '--status-unknown-text' } }
  };
  const conf = configs[dept] || configs.CIVIL;
  return (
    <span
      className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded border uppercase tracking-wide"
      style={{
        backgroundColor: `var(${conf.vars.bg})`,
        borderColor: `var(${conf.vars.border})`,
        color: `var(${conf.vars.text})`,
      }}
    >
      {conf.label}
    </span>
  );
};

/**
 * RiskBadge: Displays risk score with semantic status color.
 * Maps score to severity band then uses semantic tokens.
 * Icon and text together ensure redundancy—color alone is not the signal.
 */
export const RiskBadge: React.FC<{ score: number; severity?: string }> = ({ score, severity }) => {
  // Determine severity band from score
  let bandVars = { bg: '--status-ok-bg', border: '--status-ok-border', fg: '--status-ok-fg', text: '--status-ok-text' };
  if (score >= 85 || severity === 'CRITICAL') {
    bandVars = { bg: '--status-critical-bg', border: '--status-critical-border', fg: '--status-critical-fg', text: '--status-critical-text' };
  } else if (score >= 60 || severity === 'HIGH') {
    bandVars = { bg: '--status-caution-bg', border: '--status-caution-border', fg: '--status-caution-fg', text: '--status-caution-text' };
  }
  return (
    <span
      className="px-2 py-0.5 text-[11px] font-mono font-bold rounded border"
      style={{
        backgroundColor: `var(${bandVars.bg})`,
        borderColor: `var(${bandVars.border})`,
        color: `var(${bandVars.text})`,
      }}
    >
      {severity ? `${severity} (${score})` : `RISK ${score}`}
    </span>
  );
};
