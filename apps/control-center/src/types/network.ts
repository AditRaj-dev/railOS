/**
 * TypeScript types for RailOS network contracts.
 * Mirrors the canonical API serialization (camelCase) from railos_model.
 */

export type Track = 'UP' | 'DOWN';

export interface DataProvenance {
  synthetic: boolean;
  label: string;
  source: string;
  generatedAt?: string;
}

export interface NetworkMetrics {
  pendingMaintenanceCount: number;
  criticalDefectCount: number;
  maintenanceDebt: number;
  activeBlocks: number;
  assetAvailability: number;
  trafficPressure: number;
  openOpportunityCount: number;
}

export interface GeoJSONGeometry {
  type: 'Point' | 'LineString' | 'MultiLineString' | 'Polygon' | 'MultiPolygon';
  coordinates: number[] | number[][] | number[][][];
}

export interface RailwayZone {
  zoneId: string;
  code: string;
  name: string;
  centroid: [number, number];
  metrics: NetworkMetrics;
  planningEnabled: boolean;
  provenance: DataProvenance;
}

export interface RailwayDivision {
  divisionId: string;
  zoneId: string;
  code: string;
  name: string;
  centroid: [number, number];
  metrics: NetworkMetrics;
  planningEnabled: boolean;
  provenance: DataProvenance;
}

export interface RailwaySection {
  sectionId: string;
  divisionId: string;
  zoneId: string;
  corridorId?: string;
  code: string;
  name: string;
  fromStation: string;
  toStation: string;
  tracks: Track[];
  geometry: GeoJSONGeometry;
  metrics: NetworkMetrics;
  planningEnabled: boolean;
  /** Planable chainage bounds, joined from the corridor's block section by the
   * API. Absent for overview-only sections that no corridor plans. */
  minKm?: number;
  maxKm?: number;
  provenance: DataProvenance;
}

export interface RailwaySegment {
  segmentId: string;
  sectionId: string;
  divisionId: string;
  zoneId: string;
  geometry: GeoJSONGeometry;
  riskScore: number;
  maintenancePressure: number;
  trafficPressure: number;
  activeBlock: boolean;
  planningEnabled: boolean;
  provenance: DataProvenance;
}

export interface Station {
  stationId: string;
  code: string;
  name: string;
  sectionIds: string[];
  geometry: GeoJSONGeometry;
  planningEnabled: boolean;
  provenance: DataProvenance;
}

export interface NetworkCatalog {
  zones: RailwayZone[];
  divisions: RailwayDivision[];
  sections: RailwaySection[];
  segments: RailwaySegment[];
  stations: Station[];
  provenance: DataProvenance;
}

export type ReportSeverity = 'INFO' | 'WARNING' | 'CRITICAL';
export type ReportedAreaStatus = 'NEW' | 'ACKNOWLEDGED' | 'CLEARED';

export interface ReportedArea {
  reportId: string;
  segmentId: string;
  sectionId: string;
  coordinates: [number, number];
  bearingDegrees: number;
  uncertaintyMetersBefore: number;
  uncertaintyMetersAfter: number;
  severity: ReportSeverity;
  status: ReportedAreaStatus;
  reportedAt: string;
  acknowledgedAt?: string;
  clearedAt?: string;
  synthetic: true;
}

/**
 * Properties for a GeoJSON feature representing a network entity.
 * Used when rendering features on maps (zones, divisions, sections, segments, stations).
 */
export interface NetworkFeatureProperties {
  id: string;
  entityType: 'zone' | 'division' | 'section' | 'segment' | 'station' | 'report';
  zoneId?: string;
  divisionId?: string;
  sectionId?: string;
  segmentId?: string;
  stationId?: string;
  reportId?: string;
  severity?: ReportSeverity;
  reportStatus?: ReportedAreaStatus;
  reportedAt?: string;
  coordinates?: [number, number];
  uncertaintyMetersBefore?: number;
  uncertaintyMetersAfter?: number;
  name: string;
  code: string;
  metrics: NetworkMetrics;
  planningEnabled: boolean;
  synthetic: boolean;
  riskScore?: number;
  maintenancePressure?: number;
  trafficPressure?: number;
  activeBlock?: boolean;
}

