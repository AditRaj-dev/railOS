import { describe, expect, it } from 'vitest';
import { advanceReportLifecycle, createSeededRandom, createSimulatedReport, pointAlongLine } from '../reportSimulation';
import type { RailwaySegment } from '@/types/network';

const segment = {
  segmentId: 'SEG_TEST', sectionId: 'SEC_TEST', divisionId: 'DIV_TEST', zoneId: 'ZONE_TEST',
  geometry: { type: 'LineString', coordinates: [[77, 28], [77.01, 28], [77.02, 28.01]] },
  riskScore: 50, maintenancePressure: 50, trafficPressure: 50,
  activeBlock: false, planningEnabled: false,
  provenance: { synthetic: true, label: 'Test', source: 'test' },
} satisfies RailwaySegment;

describe('reportSimulation', () => {
  it('repeats output for the same seed', () => {
    const a = createSimulatedReport([segment], createSeededRandom(1234), 1, 1_788_868_800_000);
    const b = createSimulatedReport([segment], createSeededRandom(1234), 1, 1_788_868_800_000);
    expect(a).toEqual(b);
  });
  it('interpolates on the line with normalized bearing', () => {
    const placed = pointAlongLine([[77, 28], [77.01, 28]], 0.5)!;
    expect(placed.coordinates).toEqual([77.005, 28]);
    expect(placed.bearingDegrees).toBeGreaterThanOrEqual(0);
    expect(placed.bearingDegrees).toBeLessThan(360);
  });
  it('keeps both uncertainty values within two and three metres', () => {
    const report = createSimulatedReport([segment], createSeededRandom(99), 2, 1_788_868_800_000)!;
    expect(report.uncertaintyMetersBefore).toBeGreaterThanOrEqual(2);
    expect(report.uncertaintyMetersBefore).toBeLessThanOrEqual(3);
    expect(report.uncertaintyMetersAfter).toBeGreaterThanOrEqual(2);
    expect(report.uncertaintyMetersAfter).toBeLessThanOrEqual(3);
  });
  it('returns null without valid geometry', () => {
    expect(createSimulatedReport([], createSeededRandom(1), 1, 0)).toBeNull();
  });
  it('advances NEW to ACKNOWLEDGED and CLEARED', () => {
    const report = createSimulatedReport([segment], createSeededRandom(7), 1, 0)!;
    expect(advanceReportLifecycle(report, 9_000).status).toBe('ACKNOWLEDGED');
    expect(advanceReportLifecycle(report, 18_000).status).toBe('CLEARED');
  });
});
