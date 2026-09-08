/**
 * Topology layout functions for schematic railway view.
 * Pure functions, no React or DOM manipulation.
 * D3 used only for scales and path math, never for DOM.
 */

import { scaleLinear } from 'd3-scale';
import { line as d3Line, curveBasis } from 'd3-shape';
import type { Station, RailwaySection } from '@/types/network';

export type BlockType = 'TRAFFIC' | 'MAINTENANCE' | 'POSSESSION' | 'ENGINEERING';
export type Track = 'UP' | 'DOWN';
export type Department = 'CIVIL' | 'S_AND_T' | 'TRD' | 'OPERATING';

export interface ScheduledBlock {
  blockId: string;
  sectionId: string;
  track: Track;
  blockType: BlockType;
  start: number;
  end: number;
  taskIds: string[];
  departments: Department[];
  opportunityId?: string;
}

export interface Assignment {
  taskId: string;
  blockId: string;
  start: number;
  end: number;
}

export interface LayoutSectionParams {
  section: RailwaySection;
  stations: Station[];
  width: number;
  height: number;
  padding: number;
}

export interface StationLayout {
  stationId: string;
  code: string;
  x: number;
  upY: number;
  downY: number;
}

export interface SectionLayout {
  stations: StationLayout[];
  upTrackPath: string;
  downTrackPath: string;
  baselineY: number;
}

export interface BlockLayoutItem {
  blockId: string;
  x: number;
  width: number;
  leadInX: number;
  leadInWidth: number;
  handbackX: number;
  handbackWidth: number;
}

export interface DependencyLink {
  source: { x: number; y: number };
  target: { x: number; y: number };
  path: string;
}

const MINIMUM_STATION_GAP_PX = 60;
const LEAD_IN_MARGIN_MINUTES = 5;
const HANDBACK_MARGIN_MINUTES = 5;

/**
 * Layout stations along section with chainage-based spacing.
 * Ensures minimum gap for legibility in dense sections.
 */
export function layoutSection(params: LayoutSectionParams): SectionLayout {
  const { section, stations, width, height, padding } = params;

  const sectionStations = stations.filter(
    s => s.sectionIds?.includes(section.sectionId)
  );

  if (sectionStations.length === 0) {
    return {
      stations: [],
      upTrackPath: '',
      downTrackPath: '',
      baselineY: height / 2,
    };
  }

  const contentWidth = width - 2 * padding;
  const contentHeight = height - 2 * padding;
  const trackSpacing = contentHeight / 4;
  const baselineY = height / 2;
  const upTrackY = baselineY - trackSpacing;
  const downTrackY = baselineY + trackSpacing;

  // Calculate natural x positions from geometry chainage
  const coordsToM = (coords: [number, number]): number => {
    const geomCoords = section.geometry.coordinates as number[][];
    if (geomCoords.length === 0) return 0;
    const dx = coords[0] - geomCoords[0][0];
    const dy = coords[1] - geomCoords[0][1];
    return Math.sqrt(dx * dx + dy * dy) * 111000; // ~111km per degree
  };

  const positions = sectionStations.map((stn) => ({
    stationId: stn.stationId,
    code: stn.code,
    chainage: coordsToM(stn.geometry.coordinates as [number, number]),
  }));

  positions.sort((a, b) => a.chainage - b.chainage);

  const minChainage = Math.min(...positions.map(p => p.chainage));
  const maxChainage = Math.max(...positions.map(p => p.chainage));
  const chainageSpan = maxChainage - minChainage || 1;

  // First pass: chainage-based linear scale
  const chainageScale = scaleLinear()
    .domain([minChainage, maxChainage])
    .range([padding, padding + contentWidth]);

  let stationLayouts = positions.map(p => ({
    stationId: p.stationId,
    code: p.code,
    x: chainageScale(p.chainage),
    upY: upTrackY,
    downY: downTrackY,
  }));

  // Second pass: enforce minimum gap
  for (let i = 1; i < stationLayouts.length; i++) {
    const prev = stationLayouts[i - 1];
    const curr = stationLayouts[i];
    const gap = curr.x - prev.x;

    if (gap < MINIMUM_STATION_GAP_PX) {
      const deficit = MINIMUM_STATION_GAP_PX - gap;
      // Shift current and all following stations right
      for (let j = i; j < stationLayouts.length; j++) {
        stationLayouts[j].x += deficit;
      }
    }
  }

  // Clip to bounds
  const rightBound = padding + contentWidth;
  const overflow = Math.max(0, stationLayouts[stationLayouts.length - 1].x - rightBound);
  if (overflow > 0) {
    stationLayouts = stationLayouts.map(s => ({
      ...s,
      x: Math.max(padding, s.x - overflow),
    }));
  }

  // Generate track paths as SVG line paths
  const upPoints: [number, number][] = stationLayouts.map(s => [s.x, s.upY]);
  const downPoints: [number, number][] = stationLayouts.map(s => [s.x, s.downY]);

  const pathGen = d3Line<[number, number]>();
  const upTrackPath = pathGen(upPoints) || '';
  const downTrackPath = pathGen(downPoints) || '';

  return {
    stations: stationLayouts,
    upTrackPath,
    downTrackPath,
    baselineY,
  };
}

/**
 * Layout blocks with visible lead-in and handback margins.
 * Lead-in and handback are drawn as separate extents outside the block body.
 */
export interface LayoutBlocksParams {
  blocks: ScheduledBlock[];
  scale: (minutes: number) => number;
}

export function layoutBlocks(params: LayoutBlocksParams): BlockLayoutItem[] {
  const { blocks, scale } = params;

  return blocks.map(block => {
    const bodyX = scale(block.start);
    const bodyEnd = scale(block.end);
    const bodyWidth = bodyEnd - bodyX;

    const leadInX = scale(block.start - LEAD_IN_MARGIN_MINUTES);
    const leadInEnd = bodyX;
    const leadInWidth = leadInEnd - leadInX;

    const handbackX = bodyEnd;
    const handbackEnd = scale(block.end + HANDBACK_MARGIN_MINUTES);
    const handbackWidth = handbackEnd - handbackX;

    return {
      blockId: block.blockId,
      x: bodyX,
      width: bodyWidth,
      leadInX,
      leadInWidth,
      handbackX,
      handbackWidth,
    };
  });
}

/**
 * Layout dependency links between assignments using d3-shape link generators.
 */
/** Mirrors railos_model.Dependency: a predecessor/successor task-id edge. */
export interface Dependency {
  predecessorTaskId: string;
  successorTaskId: string;
}

export interface LayoutDependenciesParams {
  assignments: Assignment[];
  positions: Map<string, { x: number; y: number }>;
  dependencies: Dependency[];
}

/**
 * Builds one curved SVG path per dependency edge whose predecessor and
 * successor are both scheduled (assigned to a block with a known position).
 * Dependencies referencing an unscheduled task are silently skipped — the
 * caller renders unassigned/unscheduled work through a different affordance.
 */
export function layoutDependencies(params: LayoutDependenciesParams): DependencyLink[] {
  const { assignments, positions, dependencies } = params;

  // Build a map of taskId → assignment position
  const taskPositions = new Map<string, { x: number; y: number }>();
  assignments.forEach(a => {
    const pos = positions.get(a.taskId);
    if (pos) taskPositions.set(a.taskId, pos);
  });

  const pathGen = d3Line<[number, number]>().curve(curveBasis);

  const links: DependencyLink[] = [];
  dependencies.forEach(dep => {
    const source = taskPositions.get(dep.predecessorTaskId);
    const target = taskPositions.get(dep.successorTaskId);
    if (!source || !target) return;

    const midX = (source.x + target.x) / 2;
    const path =
      pathGen([
        [source.x, source.y],
        [midX, source.y],
        [midX, target.y],
        [target.x, target.y],
      ]) || '';

    links.push({ source, target, path });
  });

  return links;
}

/**
 * Create a d3 linear scale from horizon-relative minutes to pixels.
 */
export interface TimeScaleParams {
  horizonMinutes: number;
  width: number;
  padding?: number;
}

export function timeScale(params: TimeScaleParams): (minutes: number) => number {
  const { horizonMinutes, width, padding = 0 } = params;
  const contentWidth = width - 2 * padding;

  return scaleLinear()
    .domain([0, horizonMinutes])
    .range([padding, padding + contentWidth]);
}
