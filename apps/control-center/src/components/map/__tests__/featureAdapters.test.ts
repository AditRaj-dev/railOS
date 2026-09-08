import { describe, expect, it } from 'vitest';
import { reportedAreaFeature } from '../featureAdapters';
import type { ReportedArea } from '@/types/network';

const report: ReportedArea = {
  reportId: 'SIM-0001', segmentId: 'SEG_GZB_DER', sectionId: 'SEC_GZB_DER',
  coordinates: [77.5, 28.63], bearingDegrees: 132,
  uncertaintyMetersBefore: 2.2, uncertaintyMetersAfter: 2.8,
  severity: 'WARNING', status: 'NEW',
  reportedAt: '2026-09-08T12:00:00.000Z', synthetic: true,
};

describe('reportedAreaFeature', () => {
  it('creates a selectable report feature without losing provenance', () => {
    expect(reportedAreaFeature(report)).toMatchObject({
      id: 'SIM-0001', entityType: 'report', sectionId: 'SEC_GZB_DER',
      segmentId: 'SEG_GZB_DER', reportId: 'SIM-0001', severity: 'WARNING',
      reportStatus: 'NEW', synthetic: true,
    });
  });
});
