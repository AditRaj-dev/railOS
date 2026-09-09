import { describe, expect, it } from 'vitest';
import { buildLayers } from '../layers';
import { INDIA_BOUNDS, INDIA_MAX_BOUNDS } from '../GeographicMap';
import type { RailwaySection, RailwaySegment, Station } from '@/types/network';

describe('Map layer configuration and Indian bounds', () => {
  const dummyProvenance = {
    synthetic: true,
    label: 'Test pilot data',
    source: 'Railblock unit test',
    generatedAt: '2026-09-08',
  };

  const dummyStation: Station = {
    stationId: 'STN_NDLS',
    code: 'NDLS',
    name: 'New Delhi',
    sectionIds: ['SEC_GZB_DER'],
    geometry: { type: 'Point', coordinates: [77.22, 28.64] },
    planningEnabled: true,
    provenance: dummyProvenance,
  };

  const dummySegment: RailwaySegment = {
    segmentId: 'SEG_GZB_DER',
    sectionId: 'SEC_GZB_DER',
    divisionId: 'DIV_DLI',
    zoneId: 'ZONE_NR',
    geometry: { type: 'LineString', coordinates: [[77.45, 28.66], [77.55, 28.59]] },
    riskScore: 60,
    maintenancePressure: 50,
    trafficPressure: 80,
    activeBlock: false,
    planningEnabled: true,
    provenance: dummyProvenance,
  };

  const dummySection: RailwaySection = {
    sectionId: 'SEC_GZB_DER',
    divisionId: 'DIV_DLI',
    zoneId: 'ZONE_NR',
    corridorId: 'GZB-ALJN',
    code: 'GZB-DER',
    name: 'Ghaziabad-Dadri',
    fromStation: 'GZB',
    toStation: 'DER',
    tracks: ['UP', 'DOWN'],
    geometry: { type: 'LineString', coordinates: [[77.45, 28.66], [77.55, 28.59]] },
    planningEnabled: true,
    provenance: dummyProvenance,
    metrics: {
      pendingMaintenanceCount: 2,
      criticalDefectCount: 0,
      maintenanceDebt: 40,
      activeBlocks: 0,
      assetAvailability: 95,
      trafficPressure: 80,
      openOpportunityCount: 1,
    },
  };

  it('renders station markers, labels, and segment casing layers at India overview zoom (level 5)', () => {
    const layers = buildLayers({
      mode: 'MAINTENANCE',
      zoom: 5,
      data: {
        zones: [],
        divisions: [],
        sections: [dummySection],
        segments: [dummySegment],
        stations: [dummyStation],
      },
    });

    const layerIds = layers.map((l) => l.id);
    expect(layerIds).toContain('segments-casing');
    expect(layerIds).toContain('segments-paths');
    expect(layerIds).toContain('sections-casing');
    expect(layerIds).toContain('sections-paths');
    expect(layerIds).toContain('stations-halo');
    expect(layerIds).toContain('stations');
    expect(layerIds).toContain('station-labels');
  });

  it('confines viewport to the Indian subcontinent region', () => {
    expect(INDIA_BOUNDS[0][0]).toBeGreaterThanOrEqual(65); // West: Longitude >= 65E
    expect(INDIA_BOUNDS[0][1]).toBeGreaterThanOrEqual(6);  // South: Latitude >= 6N
    expect(INDIA_BOUNDS[1][0]).toBeLessThanOrEqual(100);   // East: Longitude <= 100E
    expect(INDIA_BOUNDS[1][1]).toBeLessThanOrEqual(40);    // North: Latitude <= 40N

    expect(INDIA_MAX_BOUNDS[0][0]).toBeLessThanOrEqual(INDIA_BOUNDS[0][0]);
    expect(INDIA_MAX_BOUNDS[1][0]).toBeGreaterThanOrEqual(INDIA_BOUNDS[1][0]);
  });
});
