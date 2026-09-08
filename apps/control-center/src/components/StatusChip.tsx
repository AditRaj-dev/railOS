/**
 * StatusChip: Semantic status rendering with icon + label.
 * Implements WCAG AA contrast and text/icon redundancy—color is never the only signal.
 * Uses CSS custom property tokens from globals.css.
 */

import React from 'react';
import type { TokenDef } from './tokens';

interface StatusChipProps {
  /** Token definition from the token map */
  def: TokenDef;
  /** Optional additional CSS classes */
  className?: string;
  /** Whether to use subtle styling (reduced padding/size) */
  compact?: boolean;
}

/**
 * StatusChip: Displays status with semantic icon and label.
 * - Icon and label are always rendered (WCAG AA redundancy).
 * - Colors from CSS custom properties (--status-*-bg, --status-*-border, etc.).
 * - Border provides clear visual hierarchy and contrast.
 */
export const StatusChip: React.FC<StatusChipProps> = ({
  def,
  className = '',
  compact = false,
}) => {
  const Icon = def.icon;
  const baseClasses = compact
    ? 'px-1.5 py-0.5 text-xs'
    : 'px-2 py-1 text-sm';

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded border font-medium
        transition-colors duration-150
        ${baseClasses}
        ${className}
      `}
      style={{
        backgroundColor: `var(${def.bgVar})`,
        borderColor: `var(${def.borderVar})`,
        color: `var(${def.textVar})`,
      }}
    >
      <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: `var(${def.fgVar})` }} />
      <span className="font-sans font-semibold">{def.label}</span>
    </span>
  );
};

interface SeverityDotProps {
  /** Token definition from the token map */
  def: TokenDef;
  /** Accessible label (required for screen readers since dot is visual-only) */
  label?: string;
  /** Optional additional CSS classes */
  className?: string;
  /** Size in pixels */
  size?: number;
}

/**
 * SeverityDot: Small colored dot with accessible label.
 * - Always includes aria-label or visually-hidden text (WCAG AA).
 * - Used in dense tables, timelines, and list items where space is constrained.
 * - Icon color from token's foreground variable.
 */
export const SeverityDot: React.FC<SeverityDotProps> = ({
  def,
  label,
  className = '',
  size = 12,
}) => {
  const accessibleLabel = label || def.label;

  return (
    <div className={`relative inline-block ${className}`}>
      <div
        className="rounded-full"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          backgroundColor: `var(${def.fgVar})`,
        }}
        aria-label={accessibleLabel}
        role="img"
      />
      {/* Visually-hidden text for redundancy */}
      <span className="sr-only">{accessibleLabel}</span>
    </div>
  );
};

interface StatusBadgeProps {
  /** Token definition from the token map */
  def: TokenDef;
  /** Secondary text (e.g., "Score: 85") */
  secondary?: string;
  /** Optional additional CSS classes */
  className?: string;
}

/**
 * StatusBadge: Enhanced chip with optional secondary value.
 * Used in metric cards, summary panels, and high-visibility contexts.
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  def,
  secondary,
  className = '',
}) => {
  const Icon = def.icon;

  return (
    <div
      className={`
        px-3 py-2 rounded border flex items-center gap-2
        transition-colors duration-150
        ${className}
      `}
      style={{
        backgroundColor: `var(${def.bgVar})`,
        borderColor: `var(${def.borderVar})`,
        color: `var(${def.textVar})`,
      }}
    >
      <Icon className="w-4 h-4 flex-shrink-0" style={{ color: `var(${def.fgVar})` }} />
      <div className="flex flex-col">
        <span className="font-semibold text-sm">{def.label}</span>
        {secondary && <span className="text-xs opacity-80">{secondary}</span>}
      </div>
    </div>
  );
};
