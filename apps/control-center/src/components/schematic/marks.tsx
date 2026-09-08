'use client';

import React from 'react';
import type { BlockType, Track, Department } from './topology';

export type TrainClass = 'PASSENGER_PREMIUM' | 'PASSENGER' | 'GOODS';

export interface StationMarkProps {
  code: string;
  x: number;
  upY: number;
  downY: number;
  isSelected?: boolean;
  onSelect?: () => void;
  tabIndex?: number;
}

export const StationMark: React.FC<StationMarkProps> = ({
  code,
  x,
  upY,
  downY,
  isSelected,
  onSelect,
  tabIndex = -1,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault();
      onSelect();
    }
  };

  const cy = (upY + downY) / 2;

  return (
    <g
      role="button"
      tabIndex={tabIndex}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className={`cursor-pointer transition-opacity ${isSelected ? 'opacity-100' : 'opacity-75 hover:opacity-100'}`}
    >
      <circle
        cx={x}
        cy={cy}
        r="5"
        fill={isSelected ? 'url(#stationSelectGradient)' : '#334155'}
        stroke={isSelected ? '#38bdf8' : '#64748b'}
        strokeWidth="1.5"
      />
      <text
        x={x}
        y={cy - 12}
        textAnchor="middle"
        className="text-[10px] font-mono font-bold"
        fill={isSelected ? '#38bdf8' : '#cbd5e1'}
      >
        {code}
      </text>
    </g>
  );
};

export interface TrackLineProps {
  pathD: string;
  track: Track;
  isHighlighted?: boolean;
}

export const TrackLine: React.FC<TrackLineProps> = ({
  pathD,
  track,
  isHighlighted = false,
}) => {
  const strokeColor = isHighlighted ? '#38bdf8' : '#475569';
  const strokeWidth = isHighlighted ? 2 : 1.5;

  return (
    <path
      d={pathD}
      fill="none"
      stroke={strokeColor}
      strokeWidth={strokeWidth}
      className="transition-colors"
      vectorEffect="non-scaling-stroke"
    />
  );
};

export interface SafetyMarginProps {
  x: number;
  y: number;
  width: number;
  height: number;
  type: 'lead-in' | 'handback';
  tabIndex?: number;
  onSelect?: () => void;
}

export const SafetyMargin: React.FC<SafetyMarginProps> = ({
  x,
  y,
  width,
  height,
  type,
  tabIndex = -1,
  onSelect,
}) => {
  const fillColor = type === 'lead-in' ? '#1e293b' : '#0f172a';
  const strokeColor = '#64748b';
  const hoverColor = '#94a3b8';

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault();
      onSelect();
    }
  };

  const label = type === 'lead-in' ? 'IN' : 'OUT';

  return (
    <g
      role="button"
      tabIndex={tabIndex}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className="cursor-pointer transition-opacity hover:opacity-100 opacity-60"
    >
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth="1"
        strokeDasharray="4,2"
        rx="2"
      />
      <text
        x={x + width / 2}
        y={y + height / 2 + 3}
        textAnchor="middle"
        dominantBaseline="middle"
        className="text-[8px] font-mono font-bold"
        fill="#94a3b8"
      >
        {label}
      </text>
    </g>
  );
};

export interface BlockRectProps {
  x: number;
  y: number;
  width: number;
  height: number;
  blockId: string;
  blockType: BlockType;
  departments: Department[];
  leadInX?: number;
  leadInWidth?: number;
  handbackX?: number;
  handbackWidth?: number;
  isSelected?: boolean;
  onSelect?: () => void;
  tabIndex?: number;
}

const blockTypeColors: Record<BlockType, { bg: string; border: string; text: string }> = {
  TRAFFIC: { bg: '#064e3b', border: '#10b981', text: '#6ee7b7' },
  MAINTENANCE: { bg: '#7c2d12', border: '#ea580c', text: '#fdba74' },
  POSSESSION: { bg: '#3f0f5c', border: '#a855f7', text: '#d8b4fe' },
  ENGINEERING: { bg: '#1e3a8a', border: '#3b82f6', text: '#93c5fd' },
};

export const BlockRect: React.FC<BlockRectProps> = ({
  x,
  y,
  width,
  height,
  blockId,
  blockType,
  departments,
  leadInX,
  leadInWidth,
  handbackX,
  handbackWidth,
  isSelected,
  onSelect,
  tabIndex = -1,
}) => {
  const colors = blockTypeColors[blockType];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault();
      onSelect();
    }
  };

  return (
    <g
      role="button"
      tabIndex={tabIndex}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className="cursor-pointer transition-opacity"
    >
      {leadInX !== undefined && leadInWidth !== undefined && (
        <SafetyMargin
          x={leadInX}
          y={y}
          width={leadInWidth}
          height={height}
          type="lead-in"
        />
      )}

      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={colors.bg}
        stroke={isSelected ? '#38bdf8' : colors.border}
        strokeWidth={isSelected ? 2 : 1.5}
        rx="3"
        className="transition-colors"
      />

      <text
        x={x + 4}
        y={y + 10}
        className="text-[9px] font-mono font-bold"
        fill={colors.text}
      >
        {blockId.substring(0, 8)}
      </text>

      {departments.length > 0 && (
        <text
          x={x + 4}
          y={y + height - 4}
          className="text-[8px] font-mono font-semibold"
          fill="#cbd5e1"
        >
          {departments.slice(0, 2).join(',')}
        </text>
      )}

      {handbackX !== undefined && handbackWidth !== undefined && (
        <SafetyMargin
          x={handbackX}
          y={y}
          width={handbackWidth}
          height={height}
          type="handback"
        />
      )}
    </g>
  );
};

export interface DependencyLinkProps {
  path: string;
  reason?: string;
}

export const DependencyLink: React.FC<DependencyLinkProps> = ({
  path,
  reason = 'dependency',
}) => {
  return (
    <g role="img" aria-label={`Dependency: ${reason}`}>
      <path
        d={path}
        fill="none"
        stroke="#94a3b8"
        strokeWidth="1.5"
        strokeDasharray="5,3"
        markerEnd="url(#arrowhead)"
        opacity="0.6"
        vectorEffect="non-scaling-stroke"
      />
    </g>
  );
};

export interface AssignmentMarkProps {
  x: number;
  y: number;
  taskId: string;
  isSelected?: boolean;
  onSelect?: () => void;
  tabIndex?: number;
}

export const AssignmentMark: React.FC<AssignmentMarkProps> = ({
  x,
  y,
  taskId,
  isSelected,
  onSelect,
  tabIndex = -1,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault();
      onSelect();
    }
  };

  return (
    <g
      role="button"
      tabIndex={tabIndex}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className="cursor-pointer transition-opacity"
    >
      <rect
        x={x - 3}
        y={y - 3}
        width="6"
        height="6"
        fill={isSelected ? '#38bdf8' : '#f59e0b'}
        stroke={isSelected ? '#0284c7' : '#d97706'}
        strokeWidth="1"
        rx="1"
      />
      <title>{taskId}</title>
    </g>
  );
};

export interface TrainMarkProps {
  x: number;
  y: number;
  trainId: string;
  trainClass: TrainClass;
  isSelected?: boolean;
  onSelect?: () => void;
  tabIndex?: number;
}

const trainClassColors: Record<TrainClass, { bg: string; border: string; text: string }> = {
  PASSENGER_PREMIUM: { bg: '#b45309', border: '#d97706', text: '#fef08a' },
  PASSENGER: { bg: '#0c4a6e', border: '#0284c7', text: '#7dd3fc' },
  GOODS: { bg: '#3f0f5c', border: '#a855f7', text: '#d8b4fe' },
};

export const TrainMark: React.FC<TrainMarkProps> = ({
  x,
  y,
  trainId,
  trainClass,
  isSelected,
  onSelect,
  tabIndex = -1,
}) => {
  const colors = trainClassColors[trainClass];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault();
      onSelect();
    }
  };

  return (
    <g
      role="button"
      tabIndex={tabIndex}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className="cursor-pointer transition-opacity"
    >
      <rect
        x={x - 8}
        y={y - 6}
        width="16"
        height="12"
        fill={colors.bg}
        stroke={isSelected ? '#38bdf8' : colors.border}
        strokeWidth={isSelected ? 1.5 : 1}
        rx="2"
        className="transition-colors"
      />
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="middle"
        className="text-[8px] font-mono font-bold"
        fill={colors.text}
      >
        {trainId.substring(0, 3)}
      </text>
    </g>
  );
};

export const SchematicDefs: React.FC = () => (
  <defs>
    <linearGradient id="stationSelectGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
      <stop offset="100%" stopColor="#0284c7" stopOpacity="1" />
    </linearGradient>
    <marker
      id="arrowhead"
      markerWidth="10"
      markerHeight="10"
      refX="8"
      refY="3"
      orient="auto"
    >
      <polygon points="0 0, 10 3, 0 6" fill="#64748b" />
    </marker>
  </defs>
);
