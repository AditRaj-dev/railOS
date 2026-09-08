import { describe, expect, it } from 'vitest';
import { buildReportedAreaLayer } from '../reportedAreaLayer';
import type { ReportedArea } from '@/types/network';

const report = {
  reportId: 'SIM-0001', segmentId: 'SEG_TEST', sectionId: 'SEC_TEST',
  coordinates: [77, 28], bearingDegrees: 91,
  uncertaintyMetersBefore: 2, uncertaintyMetersAfter: 3,
  severity: 'CRITICAL', status: 'NEW',
  reportedAt: '2026-09-08T12:00:00.000Z', synthetic: true,
} satisfies ReportedArea;

describe('buildReportedAreaLayer', () => {
  it('creates a pickable layer and filters cleared reports', () => {
    const layer = buildReportedAreaLayer([report, { ...report, reportId: 'SIM-0002', status: 'CLEARED' }], 'SIM-0001');
    const getAngle = layer.props.getAngle as (item: ReportedArea) => number;
    const getSize = layer.props.getSize as (item: ReportedArea) => number;
    expect(layer.id).toBe('reported-areas');
    expect(layer.props.data).toHaveLength(1);
    expect(layer.props.pickable).toBe(true);
    expect(getAngle(report)).toBe(91);
    expect(getSize(report)).toBe(26);
  });
});
