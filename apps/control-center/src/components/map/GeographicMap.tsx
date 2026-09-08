'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as maplibre from 'maplibre-gl';
import { MapLibreOverlay } from '@deck.gl/maplibre';
import { Activity, AlertCircle, Check, CloudOff, Compass, Database, Lock } from 'lucide-react';
import type { MapMode } from './mapModes';
import { getModeConfig } from './mapModes';
import { buildLayers } from './layers';
import { divisionFeature, sectionFeature, segmentFeature, stationFeature, zoneFeature, reportedAreaFeature } from './featureAdapters';
import type { DataProvenance, NetworkFeatureProperties, RailwayDivision, RailwaySection, RailwaySegment, RailwayZone, Station } from '@/types/network';
import { ReportSimulationControls } from './ReportSimulationControls';
import { useReportSimulation } from './useReportSimulation';
import { OPEN_RAILWAY_MAP_SOURCE_ID, OPEN_RAILWAY_MAP_LAYER_ID, ensureOpenRailwayMapOverlay, isOpenRailwayMapError } from './railwayOverlay';

import 'maplibre-gl/dist/maplibre-gl.css';

export const INDIA_BOUNDS: [[number, number], [number, number]] = [
  [68.0, 7.0],
  [97.5, 37.5],
];

export const INDIA_MAX_BOUNDS: [[number, number], [number, number]] = [
  [64.0, 6.0],
  [102.0, 38.5],
];

interface SelectionState {
  zoneId?: string;
  divisionId?: string;
  sectionId?: string;
  segmentId?: string;
  stationId?: string;
  reportId?: string;
}

interface MapData {
  zones: RailwayZone[];
  divisions: RailwayDivision[];
  sections: RailwaySection[];
  segments: RailwaySegment[];
  stations: Station[];
  provenance?: DataProvenance;
}

interface GeographicMapProps {
  mode: MapMode;
  selection?: SelectionState;
  onSelect?: (entity: NetworkFeatureProperties) => void;
  data?: MapData;
  horizon?: number;
  styleUrl: string | maplibre.StyleSpecification;
  showRailwayOverlay?: boolean;
}

type MapRuntimeState = 'initializing' | 'ready' | 'style-error' | 'offline';
type RailwayRuntimeState = 'loading' | 'ready' | 'error';

const EMPTY_DATA: MapData = { zones: [], divisions: [], sections: [], segments: [], stations: [] };
const FALLBACK_MAP_STYLE: maplibre.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#121313' } }],
};

/** Return whether this browser can create the WebGL2 context MapLibre needs. */
export function isWebGL2Supported(): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false;
  if (!window.WebGL2RenderingContext) return false;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2'));
  } catch {
    return false;
  }
}

function runtimeMessage(state: MapRuntimeState): string {
  if (state === 'initializing') return 'Initializing geographic context…';
  if (state === 'offline') return 'Offline: basemap unavailable. Railway overlays remain active.';
  if (state === 'style-error') return 'Basemap unavailable. Railway overlays remain active.';
  return 'Map ready. Railway overlays active.';
}

export const GeographicMap: React.FC<GeographicMapProps> = ({
  mode,
  selection,
  onSelect,
  data = EMPTY_DATA,
  styleUrl = FALLBACK_MAP_STYLE,
  showRailwayOverlay = true,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibre.Map | null>(null);
  const overlayRef = useRef<MapLibreOverlay | null>(null);
  const primaryStyleLoadedRef = useRef(false);
  const [zoom, setZoom] = useState(5);
  const [hoveredEntity, setHoveredEntity] = useState<NetworkFeatureProperties | null>(null);
  const [runtimeState, setRuntimeState] = useState<MapRuntimeState>('initializing');
  const [railwayState, setRailwayState] = useState<RailwayRuntimeState>('loading');
  const [reduceMotion, setReduceMotion] = useState(false);

  const [gpuError, setGpuError] = useState<string | null>(() => isWebGL2Supported()
    ? null
    : 'WebGL2 is required to render the 3D accelerated geographic map, but is not supported or enabled in this browser environment.');

  const simulation = useReportSimulation(data.segments);
  const { acknowledge } = simulation;
  const selectedReport = simulation.reports.find((report) => report.reportId === selection?.reportId);

  const provenance = data.provenance ?? data.zones[0]?.provenance ?? data.sections[0]?.provenance ?? data.stations[0]?.provenance;
  const selectedSection = data.sections.find((section) => section.sectionId === selection?.sectionId);
  const canPlan = selectedSection?.planningEnabled ?? false;
  const modeLabel = getModeConfig(mode).label;
  const keyboardFeatures = useMemo(() => [
    ...data.zones.map(zoneFeature),
    ...data.divisions.map(divisionFeature),
    ...data.sections.map(sectionFeature),
    ...data.segments.map(segmentFeature),
    ...data.stations.map((station) => stationFeature(station, data.sections)),
    ...simulation.activeReports.map(reportedAreaFeature),
  ], [data, simulation.activeReports]);

  const handleHover = useCallback((info: { object?: NetworkFeatureProperties } | null) => setHoveredEntity(info?.object ?? null), []);
  const handleClick = useCallback((info: { object?: NetworkFeatureProperties }) => {
    if (!info.object) return;
    if (info.object.entityType === 'report' && info.object.reportId) {
      acknowledge(info.object.reportId);
    }
    onSelect?.(info.object);
  }, [acknowledge, onSelect]);

  const handleFitIndia = useCallback(() => {
    mapRef.current?.fitBounds(INDIA_BOUNDS, { padding: 24, duration: 600 });
  }, []);

  useEffect(() => {
    const mediaQuery = typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : null;
    if (!mediaQuery) return;
    const updateMotionPreference = () => setReduceMotion(mediaQuery.matches);
    updateMotionPreference();
    mediaQuery.addEventListener('change', updateMotionPreference);
    return () => mediaQuery.removeEventListener('change', updateMotionPreference);
  }, []);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;
    if (!isWebGL2Supported()) {
      return;
    }
    let fallbackApplied = !navigator.onLine;
    primaryStyleLoadedRef.current = false;

    let map: maplibre.Map;
    try {
      map = new maplibre.Map({
        container,
        style: fallbackApplied ? FALLBACK_MAP_STYLE : styleUrl,
        bounds: INDIA_BOUNDS,
        fitBoundsOptions: { padding: 24 },
        maxBounds: INDIA_MAX_BOUNDS,
        minZoom: 4,
        maxZoom: 18,
        pitch: 0,
        bearing: 0,
        attributionControl: false,
        canvasContextAttributes: {
          powerPreference: 'default',
          failIfMajorPerformanceCaveat: false,
          preserveDrawingBuffer: false,
          antialias: true,
        },
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn('[map] WebGL2/GPU initialization failed:', msg);
      queueMicrotask(() => setGpuError(msg));
      return;
    }
    mapRef.current = map;
    (window as unknown as { _map: unknown })._map = map;

    try {
      const overlay = new MapLibreOverlay({ layers: [], interleaved: false });
      map.addControl(overlay);
      overlayRef.current = overlay;
    } catch (err) {
      console.warn('[map] deck.gl overlay initialization error:', err);
    }

    const installRailwayOverlay = () => {
      try {
        ensureOpenRailwayMapOverlay(map);
        setRailwayState('loading');
      } catch (error) {
        console.warn('[map] railway overlay installation failed', error);
        setRailwayState('error');
      }
    };

    const handleSourceData = (event: maplibre.MapSourceDataEvent) => {
      if (event.sourceId === OPEN_RAILWAY_MAP_SOURCE_ID && event.isSourceLoaded) {
        setRailwayState('ready');
      }
    };

    const handleStyleLoad = () => {
      primaryStyleLoadedRef.current = true;
      setRuntimeState('ready');
      installRailwayOverlay();
      map.resize();
    };

    const handleZoom = () => setZoom(map.getZoom());
    const handleError = (event: maplibre.ErrorEvent) => {
      if (isOpenRailwayMapError(event)) {
        setRailwayState('error');
        return;
      }
      console.warn('[map] basemap error', event.error?.message ?? event.error);
      const isStyleFailure = (event as { dataType?: string }).dataType === 'style' ||
        (event.error as { status?: number })?.status === 404;
      if (!primaryStyleLoadedRef.current && !fallbackApplied && isStyleFailure) {
        fallbackApplied = true;
        setRuntimeState(navigator.onLine ? 'style-error' : 'offline');
        try {
          map.setStyle(FALLBACK_MAP_STYLE);
        } catch (styleErr) {
          console.warn('[map] failed applying fallback style', styleErr);
        }
      }
    };
    const handleOffline = () => setRuntimeState('offline');
    const handleOnline = () => {
      if (primaryStyleLoadedRef.current) setRuntimeState('ready');
    };
    const resizeObserver = new ResizeObserver(() => {
      map.resize();
    });
    resizeObserver.observe(container);

    map.on('style.load', handleStyleLoad);
    map.on('load', () => {
      primaryStyleLoadedRef.current = true;
      setRuntimeState('ready');
      installRailwayOverlay();
      map.resize();
    });
    map.on('sourcedata', handleSourceData);
    map.on('zoom', handleZoom);
    map.on('error', handleError);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
      map.off('style.load', handleStyleLoad);
      map.off('sourcedata', handleSourceData);
      map.off('zoom', handleZoom);
      map.off('error', handleError);
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, [styleUrl]);

  useEffect(() => {
    if (mapRef.current && primaryStyleLoadedRef.current) {
      mapRef.current.setStyle(styleUrl);
    }
  }, [styleUrl]);

  // Reactively toggle railway overlay visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !primaryStyleLoadedRef.current) return;
    if (map.getLayer(OPEN_RAILWAY_MAP_LAYER_ID)) {
      map.setLayoutProperty(
        OPEN_RAILWAY_MAP_LAYER_ID,
        'visibility',
        showRailwayOverlay ? 'visible' : 'none'
      );
    } else if (showRailwayOverlay) {
      try {
        ensureOpenRailwayMapOverlay(map);
      } catch (e) {
        console.warn('[map] failed to add railway overlay', e);
      }
    }
  }, [showRailwayOverlay]);

  useEffect(() => {
    overlayRef.current?.setProps({
      layers: buildLayers({
        mode,
        zoom,
        data,
        reports: simulation.activeReports,
        selection,
        onHover: handleHover,
        onClick: handleClick,
        reduceMotion,
      }),
    });
  }, [mode, zoom, data, simulation.activeReports, selection, handleHover, handleClick, reduceMotion, styleUrl]);

  return (
    <section className="relative flex h-full w-full flex-col overflow-hidden rounded border border-[var(--border-default)] bg-[var(--bg-canvas)]">
      <div
        ref={mapContainerRef}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
        role="img"
        aria-label={`Geographic railway map of India in ${modeLabel} mode. ${selection?.sectionId ? `Selected section: ${selectedSection?.name ?? selection.sectionId}.` : 'No section selected.'} Use Browse map features for keyboard selection.`}
      />

      <div className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-col gap-2">
        {gpuError ? (
          <div role="alert" className="pointer-events-auto flex max-w-lg items-start gap-2.5 rounded border border-amber-500/50 bg-[var(--bg-overlay)]/95 p-3 text-xs font-mono text-[var(--text-primary)] shadow-lg backdrop-blur">
            <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
            <div className="space-y-1">
              <div className="font-bold text-amber-400">WebGL2 Acceleration Unavailable</div>
              <p className="text-[11px] leading-relaxed text-[var(--text-secondary)]">
                WebGL2 is required to render the 3D accelerated geographic map. ({gpuError})
              </p>
              <p className="text-[11px] leading-relaxed text-[var(--text-secondary)]">
                <strong>If using Brave Browser:</strong> Click the <strong>Brave Lion Shield</strong> icon in your URL bar and toggle Shields <strong>OFF</strong> for localhost (or change Fingerprinting to &ldquo;Allow&rdquo;).
              </p>
              <p className="text-[11px] leading-relaxed text-[var(--text-secondary)]">
                Also ensure <em>Hardware Acceleration</em> is enabled in browser Settings.
              </p>
            </div>
          </div>
        ) : (
          <div role="status" aria-live="polite" className="flex items-start gap-2 rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[11px] font-mono text-[var(--text-secondary)]">
            {runtimeState === 'initializing' ? <Activity aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 motion-safe:animate-spin" /> : runtimeState === 'offline' ? <CloudOff aria-hidden="true" className="mt-0.5 h-3.5 w-3.5" /> : runtimeState === 'style-error' ? <AlertCircle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5" /> : <Check aria-hidden="true" className="mt-0.5 h-3.5 w-3.5" />}
            <span>{runtimeMessage(runtimeState)}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <div role="status" aria-live="polite" className="rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[10px] font-mono text-[var(--text-secondary)]">
            Railway tracks: {railwayState === 'ready' ? 'ready' : railwayState === 'error' ? 'unavailable' : 'loading…'}
          </div>
          <button
            type="button"
            onClick={handleFitIndia}
            title="Reset frame to Indian subcontinent"
            className="pointer-events-auto flex items-center gap-1.5 rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-2.5 py-1.5 text-[10px] font-mono font-bold text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-elevated)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--status-info)]"
          >
            <Compass aria-hidden="true" className="h-3 w-3 text-sky-400" />
            <span>Fit India View</span>
          </button>
        </div>
        <ReportSimulationControls
          running={simulation.running}
          hasTrackGeometry={simulation.hasTrackGeometry}
          activeCount={simulation.activeReports.length}
          onPause={simulation.pause}
          onResume={simulation.resume}
          onReset={simulation.reset}
        />
        {provenance && (
          <div className="flex items-start gap-2 rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[10px] font-mono text-[var(--text-secondary)]">
            <Database aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span><strong className="uppercase text-[var(--text-primary)]">{provenance.synthetic ? 'Synthetic demo data' : 'Reference railway data'}</strong> — {provenance.label || provenance.source}</span>
          </div>
        )}
      </div>

      <details className="absolute right-3 top-3 z-20 max-h-[60%] w-64 overflow-auto rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 text-xs text-[var(--text-secondary)] open:p-2">
        <summary className="cursor-pointer rounded px-2 py-1.5 font-mono font-bold text-[var(--text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info)]">Browse map features ({keyboardFeatures.length})</summary>
        <p className="px-2 py-1 text-[10px] text-[var(--text-muted)]">Keyboard alternative to selecting features on the canvas.</p>
        <div className="space-y-1">
          {keyboardFeatures.map((feature) => (
            <button key={`${feature.entityType}-${feature.id}`} type="button" onClick={() => onSelect?.(feature)} className="block w-full rounded border border-transparent px-2 py-1.5 text-left font-mono hover:border-[var(--border-strong)] hover:bg-[var(--bg-elevated)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--status-info)]">
              <span className="font-bold text-[var(--text-primary)]">{feature.code}</span> {feature.name} · {feature.entityType}{feature.activeBlock ? ' · Active block' : ''}
            </button>
          ))}
          {keyboardFeatures.length === 0 && <p className="px-2 py-2">No railway features in this dataset.</p>}
        </div>
      </details>

      {hoveredEntity && <div className="pointer-events-none absolute left-3 top-48 z-20 max-w-xs rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2"><div className="text-xs font-mono font-bold text-[var(--status-info)]">{hoveredEntity.name}</div><div className="mt-0.5 text-[10px] text-[var(--text-secondary)]">{hoveredEntity.code} · {hoveredEntity.entityType}</div></div>}

      {selection?.sectionId && (
        <div className="absolute bottom-10 left-3 z-10">
          <button type="button" onClick={() => selectedSection && onSelect?.(sectionFeature(selectedSection))} disabled={!canPlan} className="flex items-center gap-2 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-4 py-2 text-xs font-mono font-bold text-[var(--text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info)] disabled:cursor-not-allowed disabled:text-[var(--text-muted)]">
            {canPlan ? <Check aria-hidden="true" className="h-3.5 w-3.5" /> : <Lock aria-hidden="true" className="h-3.5 w-3.5" />}{canPlan ? 'Plan for this Section' : 'Planning Disabled'}
          </button>
        </div>
      )}

      {selectedReport && (
        <aside aria-label={`Details for ${selectedReport.reportId}`} className="absolute bottom-10 right-3 z-20 w-72 rounded border border-[var(--border-strong)] bg-[var(--bg-overlay)]/95 p-3 text-xs text-[var(--text-secondary)]">
          <div className="font-mono font-bold text-[var(--text-primary)]">▲ {selectedReport.reportId}</div>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt>Severity</dt><dd>{selectedReport.severity}</dd>
            <dt>Status</dt><dd>{selectedReport.status}</dd>
            <dt>Section</dt><dd>{selectedReport.sectionId}</dd>
            <dt>Segment</dt><dd>{selectedReport.segmentId}</dd>
            <dt>Position</dt><dd>{selectedReport.coordinates[1].toFixed(6)}, {selectedReport.coordinates[0].toFixed(6)}</dd>
            <dt>Accuracy</dt><dd>Approx. ±2–3 m</dd>
            <dt>Source</dt><dd>Synthetic simulation</dd>
          </dl>
        </aside>
      )}

      <div className="absolute bottom-2 right-3 z-10 text-[10px] font-mono text-[var(--text-muted)]">© <a className="underline" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>{' · '}<a className="underline" href="https://openrailwaymap.org/" target="_blank" rel="noopener noreferrer">OpenRailwayMap</a>{' · '}<a className="underline" href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a>{' · '}<a className="underline" href="https://maplibre.org/" target="_blank" rel="noopener noreferrer">MapLibre</a></div>
    </section>
  );
};
