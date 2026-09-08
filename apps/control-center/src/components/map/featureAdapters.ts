import type {
  NetworkFeatureProperties,
  NetworkMetrics,
  RailwayDivision,
  RailwaySection,
  RailwaySegment,
  RailwayZone,
  ReportedArea,
  Station,
} from '@/types/network';

const EMPTY_METRICS: NetworkMetrics = {
  pendingMaintenanceCount: 0,
  criticalDefectCount: 0,
  maintenanceDebt: 0,
  activeBlocks: 0,
  assetAvailability: 0,
  trafficPressure: 0,
  openOpportunityCount: 0,
};

export function zoneFeature(zone: RailwayZone): NetworkFeatureProperties {
  return {
    id: zone.zoneId,
    entityType: 'zone',
    zoneId: zone.zoneId,
    name: zone.name,
    code: zone.code,
    metrics: zone.metrics,
    planningEnabled: zone.planningEnabled,
    synthetic: zone.provenance.synthetic,
  };
}

export function divisionFeature(division: RailwayDivision): NetworkFeatureProperties {
  return {
    id: division.divisionId,
    entityType: 'division',
    zoneId: division.zoneId,
    divisionId: division.divisionId,
    name: division.name,
    code: division.code,
    metrics: division.metrics,
    planningEnabled: division.planningEnabled,
    synthetic: division.provenance.synthetic,
  };
}

export function sectionFeature(section: RailwaySection): NetworkFeatureProperties {
  return {
    id: section.sectionId,
    entityType: 'section',
    zoneId: section.zoneId,
    divisionId: section.divisionId,
    sectionId: section.sectionId,
    name: section.name,
    code: section.code,
    metrics: section.metrics,
    planningEnabled: section.planningEnabled,
    synthetic: section.provenance.synthetic,
  };
}

export function segmentFeature(segment: RailwaySegment): NetworkFeatureProperties {
  return {
    id: segment.segmentId,
    entityType: 'segment',
    zoneId: segment.zoneId,
    divisionId: segment.divisionId,
    sectionId: segment.sectionId,
    segmentId: segment.segmentId,
    name: `Track segment ${segment.segmentId}`,
    code: segment.segmentId,
    metrics: {
      ...EMPTY_METRICS,
      activeBlocks: segment.activeBlock ? 1 : 0,
      trafficPressure: segment.trafficPressure,
    },
    planningEnabled: segment.planningEnabled,
    synthetic: segment.provenance.synthetic,
    riskScore: segment.riskScore,
    maintenancePressure: segment.maintenancePressure,
    trafficPressure: segment.trafficPressure,
    activeBlock: segment.activeBlock,
  };
}

export function stationFeature(
  station: Station,
  sections: RailwaySection[] = []
): NetworkFeatureProperties {
  const section = sections.find((candidate) => station.sectionIds.includes(candidate.sectionId));
  return {
    id: station.stationId,
    entityType: 'station',
    zoneId: section?.zoneId,
    divisionId: section?.divisionId,
    sectionId: section?.sectionId,
    stationId: station.stationId,
    name: station.name,
    code: station.code,
    metrics: section?.metrics ?? EMPTY_METRICS,
    planningEnabled: station.planningEnabled,
    synthetic: station.provenance.synthetic,
  };
}

export function reportedAreaFeature(report: ReportedArea): NetworkFeatureProperties {
  return {
    id: report.reportId,
    entityType: 'report',
    sectionId: report.sectionId,
    segmentId: report.segmentId,
    reportId: report.reportId,
    name: `Reported area ${report.reportId}`,
    code: report.reportId,
    metrics: EMPTY_METRICS,
    planningEnabled: false,
    synthetic: report.synthetic,
    severity: report.severity,
    reportStatus: report.status,
    reportedAt: report.reportedAt,
    coordinates: report.coordinates,
    uncertaintyMetersBefore: report.uncertaintyMetersBefore,
    uncertaintyMetersAfter: report.uncertaintyMetersAfter,
  };
}


