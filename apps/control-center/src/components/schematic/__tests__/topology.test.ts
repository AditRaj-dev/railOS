import { describe, it, expect } from 'vitest';
import {
  layoutSection,
  layoutBlocks,
  layoutDependencies,
  timeScale,
  type LayoutSectionParams,
  type ScheduledBlock,
  type BlockType,
} from '../topology';
import type { RailwaySection, Station } from '@/types/network';

const createMockSection = (overrides?: Partial<RailwaySection>): RailwaySection => {
  return {
    sectionId: 'SEC_TEST',
    divisionId: 'DIV_TEST',
    zoneId: 'ZONE_TEST',
    code: 'TST-TST',
    name: 'Test Section',
    fromStation: 'STN_A',
    toStation: 'STN_B',
    tracks: ['UP' as const, 'DOWN' as const],
    geometry: {
      type: 'LineString',
      coordinates: [
        [77.0, 28.0],
        [77.1, 27.95],
      ] as number[][],
    },
    metrics: {
      pendingMaintenanceCount: 0,
      criticalDefectCount: 0,
      maintenanceDebt: 0,
      activeBlocks: 0,
      assetAvailability: 100,
      trafficPressure: 0,
      openOpportunityCount: 0,
    },
    planningEnabled: true,
    provenance: {
      synthetic: true,
      label: 'Test',
      source: 'test',
    },
    ...overrides,
  };
};

const createMockStation = (
  overrides?: Partial<Station>
): Station => {
  return {
    stationId: 'STN_TEST',
    code: 'TST',
    name: 'Test Station',
    sectionIds: ['SEC_TEST'],
    geometry: {
      type: 'Point',
      coordinates: [77.05, 27.975],
    },
    planningEnabled: true,
    provenance: {
      synthetic: true,
      label: 'Test',
      source: 'test',
    },
    ...overrides,
  };
};

const createMockBlock = (
  blockId: string,
  start: number,
  end: number
): ScheduledBlock => {
  return {
    blockId,
    sectionId: 'SEC_TEST',
    track: 'UP',
    blockType: 'TRAFFIC' as BlockType,
    start,
    end,
    taskIds: [],
    departments: [],
  };
};

describe('topology', () => {
  describe('layoutSection', () => {
    it('should layout single station', () => {
      const section = createMockSection();
      const stations = [createMockStation()];

      const layout = layoutSection({
        section,
        stations,
        width: 800,
        height: 200,
        padding: 40,
      });

      expect(layout.stations).toHaveLength(1);
      expect(layout.stations[0].code).toBe('TST');
      expect(layout.stations[0].x).toBeGreaterThanOrEqual(40);
      expect(layout.stations[0].x).toBeLessThanOrEqual(760);
    });

    it('should enforce minimum station gap', () => {
      const section = createMockSection();
      const stations = [
        createMockStation({ stationId: 'STN_A', code: 'A' }),
        createMockStation({
          stationId: 'STN_B',
          code: 'B',
          geometry: { type: 'Point', coordinates: [77.0001, 27.9999] },
        }),
      ];

      const layout = layoutSection({
        section,
        stations,
        width: 800,
        height: 200,
        padding: 40,
      });

      expect(layout.stations).toHaveLength(2);
      const gap = layout.stations[1].x - layout.stations[0].x;
      expect(gap).toBeGreaterThanOrEqual(60);
    });

    it('should return up/down track paths for layout', () => {
      const section = createMockSection();
      const stations = [
        createMockStation({ stationId: 'STN_A', code: 'A' }),
        createMockStation({
          stationId: 'STN_B',
          code: 'B',
          geometry: { type: 'Point', coordinates: [77.1, 27.95] },
        }),
      ];

      const layout = layoutSection({
        section,
        stations,
        width: 800,
        height: 200,
        padding: 40,
      });

      expect(layout.upTrackPath).toContain('M');
      expect(layout.downTrackPath).toContain('M');
      expect(layout.baselineY).toBeGreaterThan(0);
    });

    it('should handle empty station list', () => {
      const section = createMockSection();

      const layout = layoutSection({
        section,
        stations: [],
        width: 800,
        height: 200,
        padding: 40,
      });

      expect(layout.stations).toHaveLength(0);
      expect(layout.upTrackPath).toBe('');
      expect(layout.downTrackPath).toBe('');
    });
  });

  describe('layoutBlocks', () => {
    it('should layout single block with lead-in and handback', () => {
      const scale = (min: number) => (min / 4320) * 1000;
      const blocks = [createMockBlock('BLK_1', 100, 200)];

      const layouts = layoutBlocks({ blocks, scale });

      expect(layouts).toHaveLength(1);
      const layout = layouts[0];

      expect(layout.x).toBeGreaterThan(layout.leadInX);
      expect(layout.handbackX).toBeGreaterThanOrEqual(layout.x + layout.width);
      expect(layout.leadInWidth).toBeGreaterThan(0);
      expect(layout.handbackWidth).toBeGreaterThan(0);
    });

    it('should keep lead-in and handback outside block body', () => {
      const scale = (min: number) => (min / 4320) * 1000;
      const blocks = [createMockBlock('BLK_1', 1000, 1200)];

      const layouts = layoutBlocks({ blocks, scale });
      const layout = layouts[0];

      const leadInEnd = layout.leadInX + layout.leadInWidth;
      const blockStart = layout.x;
      expect(leadInEnd).toBeLessThanOrEqual(blockStart);

      const blockEnd = layout.x + layout.width;
      const handbackStart = layout.handbackX;
      expect(handbackStart).toBeGreaterThanOrEqual(blockEnd);
    });

    it('should layout multiple blocks without overlap', () => {
      const scale = (min: number) => (min / 4320) * 1000;
      const blocks = [
        createMockBlock('BLK_1', 100, 200),
        createMockBlock('BLK_2', 300, 400),
      ];

      const layouts = layoutBlocks({ blocks, scale });

      expect(layouts).toHaveLength(2);
      const b1End = layouts[0].x + layouts[0].width;
      const b2Start = layouts[1].x;
      expect(b2Start).toBeGreaterThanOrEqual(b1End);
    });
  });

  describe('timeScale', () => {
    it('should create scale from 0 to horizonMinutes', () => {
      const scale = timeScale({ horizonMinutes: 4320, width: 1000, padding: 50 });

      expect(scale(0)).toBe(50);
      expect(scale(4320)).toBe(950);
    });

    it('should scale intermediate values linearly', () => {
      const scale = timeScale({ horizonMinutes: 4320, width: 1000, padding: 0 });

      const midpoint = scale(2160);
      expect(midpoint).toBeCloseTo(500, 0);
    });

    it('should respect padding', () => {
      const scale = timeScale({ horizonMinutes: 1440, width: 800, padding: 100 });

      expect(scale(0)).toBe(100);
      expect(scale(1440)).toBe(700);
    });

    it('should handle small horizon correctly', () => {
      const scale = timeScale({ horizonMinutes: 60, width: 1000, padding: 50 });

      expect(scale(0)).toBe(50);
      expect(scale(60)).toBe(950);
    });
  });

  describe('layoutDependencies', () => {
    const assignments = [
      { taskId: 'TASK-A', blockId: 'BLK-1', start: 0, end: 60 },
      { taskId: 'TASK-B', blockId: 'BLK-2', start: 60, end: 120 },
    ];
    const positions = new Map([
      ['TASK-A', { x: 10, y: 12 }],
      ['TASK-B', { x: 100, y: 12 }],
    ]);

    it('produces a link path for a dependency whose tasks are both positioned', () => {
      const links = layoutDependencies({
        assignments,
        positions,
        dependencies: [{ predecessorTaskId: 'TASK-A', successorTaskId: 'TASK-B' }],
      });

      expect(links).toHaveLength(1);
      expect(links[0].source).toEqual({ x: 10, y: 12 });
      expect(links[0].target).toEqual({ x: 100, y: 12 });
      expect(links[0].path).toEqual(expect.stringMatching(/^M/));
    });

    it('skips dependencies referencing an unpositioned task', () => {
      const links = layoutDependencies({
        assignments,
        positions,
        dependencies: [{ predecessorTaskId: 'TASK-A', successorTaskId: 'TASK-UNSCHEDULED' }],
      });

      expect(links).toHaveLength(0);
    });

    it('returns no links when there are no dependencies', () => {
      const links = layoutDependencies({ assignments, positions, dependencies: [] });
      expect(links).toHaveLength(0);
    });
  });
});
