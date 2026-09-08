/**
 * deck.gl layer factories overlaid on MapLibre via @deck.gl/maplibre MapLibreOverlay.
 * Railway paths (PathLayer), risk/maintenance styling, defects, active blocks, opportunities, stations.
 * Layer visibility is zoom-dependent.
 */

import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type {
  RailwaySection,
  RailwaySegment,
  RailwayZone,
  RailwayDivision,
  Station,
  NetworkFeatureProperties,
  ReportedArea,
} from '@/types/network';
import { type MapMode, getModeConfig } from './mapModes';
import {
  divisionFeature,
  sectionFeature,
  segmentFeature,
  stationFeature,
  zoneFeature,
} from './featureAdapters';
import { buildReportedAreaLayer } from './reportedAreaLayer';

type MapPickInfo = { object?: NetworkFeatureProperties };
type HoverHandler = (info: MapPickInfo | null) => void;
type ClickHandler = (info: MapPickInfo) => void;

export interface LayerBuildOptions {
  mode: MapMode;
  zoom: number;
  data: {
    sections: RailwaySection[];
    segments: RailwaySegment[];
    zones: RailwayZone[];
    divisions: RailwayDivision[];
    stations: Station[];
  };
  reports?: ReportedArea[];
  selection?: {
    zoneId?: string;
    divisionId?: string;
    sectionId?: string;
    segmentId?: string;
    stationId?: string;
    reportId?: string;
  };
  onHover?: HoverHandler;
  onClick?: ClickHandler;
  reduceMotion?: boolean;
}

const ZOOM_LEVELS = {
  ZONES: { min: 0, max: 7 },
  DIVISIONS: { min: 5, max: 10 },
  SECTIONS: { min: 0, max: 20 },
  SEGMENTS: { min: 0, max: 20 },
  STATIONS: { min: 0, max: 20 },
};

function getSegmentMetric(segment: RailwaySegment, mode: MapMode): number {
  switch (mode) {
    case 'MAINTENANCE':
      return segment.maintenancePressure || 0;
    case 'RISK':
      return segment.riskScore || 0;
    case 'OPERATIONS':
      return segment.trafficPressure || 0;
    case 'OPPORTUNITY':
      return segment.activeBlock ? 1 : 0;
    default:
      return 0;
  }
}

function buildSegmentLayers(
  segments: RailwaySegment[],
  mode: MapMode,
  selection?: LayerBuildOptions['selection'],
  onHover?: HoverHandler,
  onClick?: ClickHandler,
  reduceMotion = false
): Layer[] {
  const config = getModeConfig(mode);

  return [
    new PathLayer<RailwaySegment>({
      id: 'segments-casing',
      data: segments,
      getPath: (d: RailwaySegment) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          return d.geometry.coordinates as [number, number][];
        }
        return [];
      },
      getColor: () => [15, 23, 42, 230],
      getWidth: (d: RailwaySegment) => {
        const isSelected = selection?.sectionId === d.sectionId;
        return isSelected ? 8 : 6;
      },
      widthUnits: 'pixels',
      widthMinPixels: 4,
      pickable: false,
    }),
    new PathLayer<RailwaySegment>({
      id: 'segments-paths',
      data: segments,
      getPath: (d: RailwaySegment) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          return d.geometry.coordinates as [number, number][];
        }
        return [];
      },
      getColor: (d: RailwaySegment): [number, number, number, number] => {
        const metric = getSegmentMetric(d, mode);
        const hexColor = config.getColor(metric);
        const rgb = hexColor.match(/\w\w/g)?.map((x) => parseInt(x, 16)) || [0, 0, 0];
        const isSelected = selection?.sectionId === d.sectionId;
        return [rgb[0], rgb[1], rgb[2], isSelected ? 255 : 220];
      },
      getWidth: (d: RailwaySegment) => {
        const metric = getSegmentMetric(d, mode);
        const baseWidth = config.getWidth(metric);
        const isSelected = selection?.sectionId === d.sectionId;
        return isSelected ? baseWidth + 3 : baseWidth;
      },
      widthUnits: 'pixels',
      widthMinPixels: 3,
      pickable: true,
      onHover: (info: PickingInfo<RailwaySegment>) =>
        onHover?.(info.object ? { object: segmentFeature(info.object) } : null),
      onClick: (info: PickingInfo<RailwaySegment>) => {
        if (info.object) onClick?.({ object: segmentFeature(info.object) });
      },
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
      transitions: reduceMotion ? undefined : { getColor: 300, getWidth: 300 },
    }),
  ];
}

function buildSectionLayers(
  sections: RailwaySection[],
  mode: MapMode,
  selection?: LayerBuildOptions['selection'],
  onHover?: HoverHandler,
  onClick?: ClickHandler,
  reduceMotion = false
): Layer[] {
  const config = getModeConfig(mode);

  return [
    new PathLayer<RailwaySection>({
      id: 'sections-casing',
      data: sections,
      getPath: (d: RailwaySection) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          return d.geometry.coordinates as [number, number][];
        }
        return [];
      },
      getColor: () => [15, 23, 42, 220],
      getWidth: (d: RailwaySection) => {
        const isSelected = selection?.sectionId === d.sectionId;
        return isSelected ? 7 : 5;
      },
      widthUnits: 'pixels',
      widthMinPixels: 3.5,
      pickable: false,
    }),
    new PathLayer<RailwaySection>({
      id: 'sections-paths',
      data: sections,
      getPath: (d: RailwaySection) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          return d.geometry.coordinates as [number, number][];
        }
        return [];
      },
      getColor: (d: RailwaySection): [number, number, number, number] => {
        const metric = getMetricFromSection(d, mode);
        const hexColor = config.getColor(metric);
        const rgb = hexColor.match(/\w\w/g)?.map((x) => parseInt(x, 16)) || [0, 0, 0];
        const isSelected = selection?.sectionId === d.sectionId;
        return [rgb[0], rgb[1], rgb[2], isSelected ? 255 : 200];
      },
      getWidth: (d: RailwaySection) => {
        const metric = getMetricFromSection(d, mode);
        const baseWidth = config.getWidth(metric);
        const isSelected = selection?.sectionId === d.sectionId;
        return isSelected ? baseWidth + 2 : baseWidth;
      },
      widthUnits: 'pixels',
      widthMinPixels: 2.5,
      pickable: true,
      onHover: (info: PickingInfo<RailwaySection>) =>
        onHover?.(info.object ? { object: sectionFeature(info.object) } : null),
      onClick: (info: PickingInfo<RailwaySection>) => {
        if (info.object) onClick?.({ object: sectionFeature(info.object) });
      },
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
      transitions: reduceMotion ? undefined : { getColor: 300, getWidth: 300 },
    }),
  ];
}

function buildStationLayers(
  stations: Station[],
  sections: RailwaySection[],
  selection?: LayerBuildOptions['selection'],
  onHover?: HoverHandler,
  onClick?: ClickHandler
): Layer[] {
  return [
    new ScatterplotLayer<Station>({
      id: 'stations-halo',
      data: stations,
      getPosition: (d: Station) =>
        d.geometry.type === 'Point' ? (d.geometry.coordinates as [number, number]) : [0, 0],
      getRadius: () => 300,
      radiusUnits: 'meters',
      radiusMinPixels: 7,
      radiusMaxPixels: 24,
      getLineColor: (d: Station) => {
        const isSelected = selection?.stationId === d.stationId;
        return isSelected ? [245, 158, 11, 255] : [56, 189, 248, 200];
      },
      getFillColor: (d: Station) => {
        const isSelected = selection?.stationId === d.stationId;
        return isSelected ? [245, 158, 11, 80] : [56, 189, 248, 50];
      },
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer<Station>({
      id: 'stations',
      data: stations,
      getPosition: (d: Station) =>
        d.geometry.type === 'Point' ? (d.geometry.coordinates as [number, number]) : [0, 0],
      getRadius: () => 150,
      radiusUnits: 'meters',
      radiusMinPixels: 4.5,
      radiusMaxPixels: 16,
      getLineColor: [255, 255, 255, 255],
      getFillColor: (d: Station) => {
        const isSelected = selection?.stationId === d.stationId;
        return isSelected ? [245, 158, 11, 255] : [34, 211, 238, 255];
      },
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: true,
      onHover: (info: PickingInfo<Station>) =>
        onHover?.(info.object ? { object: stationFeature(info.object, sections) } : null),
      onClick: (info: PickingInfo<Station>) => {
        if (info.object) onClick?.({ object: stationFeature(info.object, sections) });
      },
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
    }),
    new TextLayer<Station>({
      id: 'station-labels',
      data: stations,
      getPosition: (d: Station) =>
        d.geometry.type === 'Point' ? (d.geometry.coordinates as [number, number]) : [0, 0],
      getText: (d: Station) => d.code,
      getSize: 10,
      getColor: [248, 250, 252, 255],
      getAngle: 0,
      getTextAnchor: 'start',
      getAlignmentBaseline: 'center',
      getPixelOffset: [9, -1],
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      fontWeight: 'bold',
      background: true,
      getBackgroundColor: [15, 23, 42, 220],
      backgroundPadding: [3, 2],
      pickable: false,
    }),
  ];
}

function buildDefectLayer(segments: RailwaySegment[]): Layer[] {
  const defects = segments.filter((s) => s.maintenancePressure > 60);

  return [
    new ScatterplotLayer({
      id: 'defects',
      data: defects,
      getPosition: (d: RailwaySegment) => {
        if (d.geometry.type === 'LineString' && d.geometry.coordinates.length > 0) {
          const mid = Math.floor(d.geometry.coordinates.length / 2);
          return d.geometry.coordinates[mid] as [number, number];
        }
        return [0, 0];
      },
      getRadius: () => 120,
      radiusUnits: 'meters',
      radiusMinPixels: 5,
      radiusMaxPixels: 40,
      getFillColor: [239, 68, 68, 200],
      getLineColor: [255, 255, 255, 255],
      getLineWidth: 1.5,
      lineWidthUnits: 'pixels',
      pickable: true,
      autoHighlight: true,
    }),
  ];
}

function buildActiveBlockLayer(segments: RailwaySegment[]): Layer[] {
  const activeBlocks = segments.filter((s) => s.activeBlock);

  return [
    new PathLayer<RailwaySegment>({
      id: 'active-blocks',
      data: activeBlocks,
      getPath: (d: RailwaySegment) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          return d.geometry.coordinates as [number, number][];
        }
        return [];
      },
      getColor: () => [255, 193, 7, 220] as [number, number, number, number],
      getWidth: () => 3,
      widthUnits: 'pixels',
      widthMinPixels: 2,
      pickable: false,
      transitions: {
        getWidth: 200,
      },
    }),
  ];
}

function buildOpportunitiesLayer(sections: RailwaySection[]): Layer[] {
  const opportunities = sections.filter((s) => s.metrics.openOpportunityCount > 0);

  return [
    new ScatterplotLayer<RailwaySection>({
      id: 'opportunities',
      data: opportunities,
      getPosition: (d: RailwaySection) => {
        if (d.geometry.type === 'LineString' && Array.isArray(d.geometry.coordinates)) {
          const coords = d.geometry.coordinates as [number, number][];
          const mid = Math.floor(coords.length / 2);
          return coords[mid] || [0, 0];
        }
        return [0, 0];
      },
      getRadius: (d: RailwaySection) => 100 + d.metrics.openOpportunityCount * 20,
      radiusUnits: 'meters',
      radiusMinPixels: 5,
      radiusMaxPixels: 40,
      getFillColor: [34, 197, 94, 100],
      getLineColor: [34, 197, 94, 220],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: true,
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
    }),
  ];
}

function buildZoneLayers(
  zones: RailwayZone[],
  onHover?: HoverHandler,
  onClick?: ClickHandler
): Layer[] {
  return [
    new ScatterplotLayer<RailwayZone>({
      id: 'zones',
      data: zones,
      getPosition: (d: RailwayZone) => d.centroid,
      getRadius: () => 500,
      radiusUnits: 'meters',
      radiusMinPixels: 5,
      radiusMaxPixels: 40,
      getFillColor: [71, 85, 105, 80],
      getLineColor: [148, 163, 184, 200],
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      pickable: true,
      onHover: (info: PickingInfo<RailwayZone>) =>
        onHover?.(info.object ? { object: zoneFeature(info.object) } : null),
      onClick: (info: PickingInfo<RailwayZone>) => {
        if (info.object) onClick?.({ object: zoneFeature(info.object) });
      },
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
    }),
  ];
}

function buildDivisionLayers(
  divisions: RailwayDivision[],
  onHover?: HoverHandler,
  onClick?: ClickHandler
): Layer[] {
  return [
    new ScatterplotLayer<RailwayDivision>({
      id: 'divisions',
      data: divisions,
      getPosition: (d: RailwayDivision) => d.centroid,
      getRadius: () => 300,
      radiusUnits: 'meters',
      radiusMinPixels: 5,
      radiusMaxPixels: 40,
      getFillColor: [100, 116, 139, 100],
      getLineColor: [226, 232, 240, 220],
      getLineWidth: 1.5,
      lineWidthUnits: 'pixels',
      pickable: true,
      onHover: (info: PickingInfo<RailwayDivision>) =>
        onHover?.(info.object ? { object: divisionFeature(info.object) } : null),
      onClick: (info: PickingInfo<RailwayDivision>) => {
        if (info.object) onClick?.({ object: divisionFeature(info.object) });
      },
      autoHighlight: true,
      highlightColor: [100, 200, 255, 255],
    }),
  ];
}

function getMetricFromSection(section: RailwaySection, mode: MapMode): number {
  switch (mode) {
    case 'MAINTENANCE':
      return section.metrics.maintenanceDebt || 0;
    case 'RISK':
      return section.metrics.criticalDefectCount * 10 || 0;
    case 'OPERATIONS':
      return section.metrics.trafficPressure || 0;
    case 'OPPORTUNITY':
      return section.metrics.openOpportunityCount || 0;
    default:
      return 0;
  }
}

export function buildLayers(options: LayerBuildOptions): Layer[] {
  const { mode, zoom, data, selection, onHover, onClick, reduceMotion = false } = options;
  const layers: Layer[] = [];

  if (zoom < ZOOM_LEVELS.ZONES.max) {
    layers.push(...buildZoneLayers(data.zones, onHover, onClick));
  }

  if (zoom >= ZOOM_LEVELS.DIVISIONS.min && zoom < ZOOM_LEVELS.DIVISIONS.max) {
    layers.push(...buildDivisionLayers(data.divisions, onHover, onClick));
  }

  if (zoom >= ZOOM_LEVELS.SECTIONS.min) {
    layers.push(...buildSectionLayers(data.sections, mode, selection, onHover, onClick, reduceMotion));
  }

  if (zoom >= ZOOM_LEVELS.SEGMENTS.min) {
    layers.push(...buildSegmentLayers(data.segments, mode, selection, onHover, onClick, reduceMotion));
    layers.push(...buildDefectLayer(data.segments));
    layers.push(...buildActiveBlockLayer(data.segments));
  }

  if (zoom >= ZOOM_LEVELS.STATIONS.min) {
    layers.push(...buildStationLayers(data.stations, data.sections, selection, onHover, onClick));
  }

  if (zoom >= ZOOM_LEVELS.SECTIONS.min) {
    layers.push(...buildOpportunitiesLayer(data.sections));
  }

  layers.push(buildReportedAreaLayer(
    options.reports ?? [],
    options.selection?.reportId,
    onHover,
    onClick
  ));

  return layers;
}
