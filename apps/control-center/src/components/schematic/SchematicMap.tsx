'use client';

import React, { useMemo } from 'react';
import type { RailwaySection, Station } from '@/types/network';
import {
  layoutSection,
  layoutBlocks,
  layoutDependencies,
  timeScale,
  type SectionLayout,
  type ScheduledBlock,
  type Assignment,
} from './topology';
import {
  StationMark,
  TrackLine,
  BlockRect,
  TrainMark,
  DependencyLink as DependencyLinkMark,
  SchematicDefs,
  type TrainClass,
} from './marks';

export interface TrainMovement {
  trainId: string;
  sectionId: string;
  track: 'UP' | 'DOWN';
  entry: number;
  exit: number;
  trainClass: TrainClass;
  priority: number;
  delayMinutes?: number;
}

export interface Dependency {
  predecessorTaskId: string;
  successorTaskId: string;
  lagMinutes?: number;
  reason?: string;
}

export interface SchematicMapProps {
  section: RailwaySection;
  stations: Station[];
  blocks: ScheduledBlock[];
  assignments?: Assignment[];
  trains?: TrainMovement[];
  dependencies?: Dependency[];
  horizonMinutes: number;
  selection?: { type: 'block' | 'train' | 'station'; id: string } | null;
  onSelect?: (type: string, id: string) => void;
  width?: number;
  height?: number;
}

const SVG_PADDING = 40;
const BLOCK_HEIGHT = 24;
const TRACK_SPACING_FACTOR = 1.5;

export const SchematicMap: React.FC<SchematicMapProps> = ({
  section,
  stations,
  blocks,
  assignments = [],
  trains = [],
  dependencies = [],
  horizonMinutes,
  selection,
  onSelect,
  width = 1200,
  height = 300,
}) => {
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const sectionLayout = useMemo<SectionLayout>(() => {
    return layoutSection({
      section,
      stations,
      width,
      height: height * 0.4,
      padding: SVG_PADDING,
    });
  }, [section, stations, width, height]);

  const timeScaleFn = useMemo(() => {
    return timeScale({ horizonMinutes, width, padding: SVG_PADDING });
  }, [horizonMinutes, width]);

  const blockLayouts = useMemo(() => {
    return layoutBlocks({ blocks, scale: timeScaleFn });
  }, [blocks, timeScaleFn]);

  const blockMap = useMemo(() => {
    const map = new Map<string, (typeof blockLayouts)[0]>();
    blockLayouts.forEach(bl => map.set(bl.blockId, bl));
    return map;
  }, [blockLayouts]);

  // Position of each assigned task = centre of the block it is scheduled into.
  const taskPositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    assignments.forEach(a => {
      const bl = blockMap.get(a.blockId);
      if (bl) map.set(a.taskId, { x: bl.x + bl.width / 2, y: BLOCK_HEIGHT / 2 });
    });
    return map;
  }, [assignments, blockMap]);

  const dependencyLinks = useMemo(() => {
    return layoutDependencies({ assignments, positions: taskPositions, dependencies });
  }, [assignments, taskPositions, dependencies]);

  const sectionStations = useMemo(() => {
    return sectionLayout.stations;
  }, [sectionLayout]);

  const handleBlockSelect = (blockId: string) => {
    onSelect?.('block', blockId);
  };

  const handleTrainSelect = (trainId: string) => {
    onSelect?.('train', trainId);
  };

  const handleStationSelect = (stationId: string) => {
    onSelect?.('station', stationId);
  };

  const contentHeight = height * 0.4;
  const blockRowY = contentHeight + SVG_PADDING + 20;
  const trainRowY = blockRowY + BLOCK_HEIGHT + 20;

  const svgStyle: React.CSSProperties = prefersReducedMotion
    ? {}
    : { transition: 'opacity 150ms ease-out' };

  return (
    <div
      className="w-full border border-slate-800 bg-slate-950/80 rounded overflow-auto"
      role="region"
      aria-label={`Schematic view of ${section.code} – ${section.name}`}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="block border-b border-slate-800/50"
        style={svgStyle}
      >
        <SchematicDefs />

        {/* Title & Legend */}
        <text
          x={SVG_PADDING}
          y="20"
          className="text-xs font-mono font-bold"
          fill="#cbd5e1"
        >
          {section.code} – {section.name}
        </text>

        <text
          x={SVG_PADDING}
          y="35"
          className="text-[10px] font-mono"
          fill="#64748b"
        >
          Station Topology • {sectionStations.length} stations • {blocks.length} blocks • {trains.length} trains
        </text>

        {/* Legend */}
        <g>
          <text
            x={width - SVG_PADDING - 150}
            y="20"
            className="text-[9px] font-mono"
            fill="#94a3b8"
          >
            ◼ Traffic ◼ Maint. ◼ Possession ◼ Eng.
          </text>
        </g>

        {/* Track Section */}
        <g transform={`translate(0, ${SVG_PADDING + 20})`}>
          {/* Up Track */}
          <TrackLine
            pathD={sectionLayout.upTrackPath}
            track="UP"
            isHighlighted={false}
          />

          {/* Down Track */}
          <TrackLine
            pathD={sectionLayout.downTrackPath}
            track="DOWN"
            isHighlighted={false}
          />

          {/* Station Marks */}
          {sectionStations.map((st, idx) => (
            <StationMark
              key={st.stationId}
              code={st.code}
              x={st.x}
              upY={st.upY}
              downY={st.downY}
              isSelected={selection?.type === 'station' && selection?.id === st.stationId}
              onSelect={() => handleStationSelect(st.stationId)}
              tabIndex={idx === 0 ? 0 : -1}
            />
          ))}
        </g>

        {/* Block Row */}
        <g transform={`translate(0, ${blockRowY})`}>
          <text
            x={SVG_PADDING}
            y="-8"
            className="text-[10px] font-mono"
            fill="#94a3b8"
          >
            Blocks
          </text>

          {blockLayouts.map((bl, idx) => (
            <BlockRect
              key={bl.blockId}
              x={bl.x}
              y={0}
              width={bl.width}
              height={BLOCK_HEIGHT}
              blockId={bl.blockId}
              blockType={blocks.find(b => b.blockId === bl.blockId)?.blockType || 'TRAFFIC'}
              departments={blocks.find(b => b.blockId === bl.blockId)?.departments || []}
              leadInX={bl.leadInX}
              leadInWidth={bl.leadInWidth}
              handbackX={bl.handbackX}
              handbackWidth={bl.handbackWidth}
              isSelected={selection?.type === 'block' && selection?.id === bl.blockId}
              onSelect={() => handleBlockSelect(bl.blockId)}
              tabIndex={idx === 0 ? 0 : -1}
            />
          ))}

          {dependencyLinks.map((link, idx) => (
            <DependencyLinkMark key={`dep-${idx}`} path={link.path} />
          ))}
        </g>

        {/* Train Row */}
        <g transform={`translate(0, ${trainRowY})`}>
          <text
            x={SVG_PADDING}
            y="-8"
            className="text-[10px] font-mono"
            fill="#94a3b8"
          >
            Trains
          </text>

          {trains.map((train, idx) => {
            const x = timeScaleFn(train.entry);
            const y = train.track === 'UP' ? 8 : 20;
            return (
              <TrainMark
                key={train.trainId}
                x={x}
                y={y}
                trainId={train.trainId}
                trainClass={train.trainClass}
                isSelected={selection?.type === 'train' && selection?.id === train.trainId}
                onSelect={() => handleTrainSelect(train.trainId)}
                tabIndex={idx === 0 ? 0 : -1}
              />
            );
          })}
        </g>

        {/* Time Ruler */}
        <g transform={`translate(0, ${height - 30})`} opacity="0.5">
          <line
            x1={SVG_PADDING}
            y1="0"
            x2={width - SVG_PADDING}
            y2="0"
            stroke="#475569"
            strokeWidth="1"
          />
          {[0, 360, 720, 1440, 2160, 2880, 3600, 4320].map(min => {
            if (min > horizonMinutes) return null;
            const x = timeScaleFn(min);
            const hours = Math.floor(min / 60);
            return (
              <g key={min}>
                <line
                  x1={x}
                  y1="0"
                  x2={x}
                  y2="4"
                  stroke="#64748b"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y="16"
                  textAnchor="middle"
                  className="text-[8px] font-mono"
                  fill="#94a3b8"
                >
                  +{hours}h
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Info Panel */}
      <div className="p-3 bg-slate-900/50 border-t border-slate-800 text-xs font-mono text-slate-400 space-y-1">
        <div>
          <span className="text-slate-300 font-bold">Section:</span> {section.code} ({section.fromStation} → {section.toStation})
        </div>
        <div>
          <span className="text-slate-300 font-bold">Horizon:</span> {horizonMinutes} minutes • <span className="text-slate-300 font-bold">Blocks:</span> {blocks.length} • <span className="text-slate-300 font-bold">Trains:</span> {trains.length}
        </div>
        {selection && (
          <div>
            <span className="text-slate-300 font-bold">Selected:</span> {selection.type} {selection.id}
          </div>
        )}
      </div>
    </div>
  );
};
