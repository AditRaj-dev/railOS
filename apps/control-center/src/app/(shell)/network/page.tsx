'use client';

import React, { Suspense, useCallback, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import { HierarchyNav } from '@/components/map/HierarchyNav';
import { useNetworkCatalog } from '@/lib/queries';
import type { MapMode } from '@/components/map/mapModes';
import type { NetworkFeatureProperties } from '@/types/network';

import { BASEMAP_PRESETS } from '@/components/map/basemapStyles';

const GeographicMap = dynamic(
  () => import('@/components/map/GeographicMap').then((m) => m.GeographicMap),
  { ssr: false, loading: () => <div className="h-full grid place-items-center text-xs font-mono text-slate-500">Loading map…</div> }
);

const MODES: MapMode[] = ['MAINTENANCE', 'RISK', 'OPERATIONS', 'OPPORTUNITY'];

function NetworkWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const { data, isLoading, error } = useNetworkCatalog();

  const [basemapStyle, setBasemapStyle] = useState<string>('street');
  const [showRailwayOverlay, setShowRailwayOverlay] = useState<boolean>(true);
  const activePreset = BASEMAP_PRESETS.find((s) => s.id === basemapStyle) ?? BASEMAP_PRESETS[0];

  const selection = useMemo(
    () => ({
      zoneId: params.get('zone') ?? undefined,
      divisionId: params.get('division') ?? undefined,
      sectionId: params.get('section') ?? undefined,
      reportId: params.get('report') ?? undefined,
    }),
    [params]
  );
  const mode = (params.get('mode') as MapMode) || 'MAINTENANCE';

  const setParams = useCallback(
    (next: Record<string, string | undefined>) => {
      const query = new URLSearchParams(params.toString());
      for (const [key, value] of Object.entries(next)) {
        if (value) query.set(key, value);
        else query.delete(key);
      }
      router.replace(`?${query.toString()}`, { scroll: false });
    },
    [params, router]
  );

  const handleSelect = useCallback(
    (entity: NetworkFeatureProperties) => {
      setParams({
        zone: entity.zoneId,
        division: entity.divisionId,
        section: entity.sectionId,
        report: entity.reportId,
      });
    },
    [setParams]
  );

  const catalog = {
    zones: data?.zones ?? [],
    divisions: data?.divisions ?? [],
    sections: data?.sections ?? [],
    segments: data?.segments ?? [],
    stations: data?.stations ?? [],
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 p-3 rounded border border-slate-800 bg-slate-900/80">
        <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wide">Map Mode:</span>
        {MODES.map((m) => (
          <button
            key={m}
            onClick={() => setParams({ mode: m })}
            aria-pressed={mode === m}
            className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold border transition-colors ${
              mode === m
                ? 'bg-sky-600 text-white border-sky-500'
                : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
          >
            {m}
          </button>
        ))}

        <div className="flex items-center gap-1.5 border-l border-slate-700/80 pl-3 ml-1">
          <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wide">Basemap:</span>
          {BASEMAP_PRESETS.map((style) => (
            <button
              key={style.id}
              onClick={() => setBasemapStyle(style.id)}
              aria-pressed={basemapStyle === style.id}
              title={style.description}
              className={`px-2 py-1 rounded text-[11px] font-mono font-bold border transition-colors ${
                basemapStyle === style.id
                  ? 'bg-slate-700 text-sky-400 border-sky-500 shadow-sm'
                  : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
            >
              {style.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 border-l border-slate-700/80 pl-3 ml-1">
          <button
            onClick={() => setShowRailwayOverlay((prev) => !prev)}
            aria-pressed={showRailwayOverlay}
            title="Toggle national railway track network overlay (OpenRailwayMap)"
            className={`px-2 py-1 rounded text-[11px] font-mono font-bold border transition-colors ${
              showRailwayOverlay
                ? 'bg-amber-950/60 text-amber-300 border-amber-600/80'
                : 'bg-slate-800/80 text-slate-500 border-slate-700 hover:text-slate-300'
            }`}
          >
            Tracks Overlay: {showRailwayOverlay ? 'ON' : 'OFF'}
          </button>
        </div>

        {error && (
          <span className="ml-auto text-[11px] font-mono text-[var(--status-critical-text)]">
            Network catalogue unavailable — is the Railblock API running?
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <div className="lg:col-span-3 rounded border border-slate-800 bg-slate-900/90 p-3 max-h-[70vh] overflow-auto">
          {isLoading ? (
            <div className="text-xs font-mono text-slate-500 py-6 text-center">Loading hierarchy…</div>
          ) : (
            <HierarchyNav
              zones={catalog.zones}
              divisions={catalog.divisions}
              sections={catalog.sections}
              selection={selection}
              onSelect={handleSelect}
            />
          )}
        </div>

        <div className="lg:col-span-9 rounded border border-slate-800 bg-slate-900/90 overflow-hidden h-[70vh]">
          <GeographicMap
            mode={mode}
            selection={selection}
            onSelect={handleSelect}
            data={catalog}
            styleUrl={activePreset.style}
            showRailwayOverlay={showRailwayOverlay}
          />
        </div>
      </div>
    </div>
  );
}

export default function NetworkPage() {
  return (
    <Suspense fallback={<div className="text-xs font-mono text-slate-500 p-6">Loading network…</div>}>
      <NetworkWorkspace />
    </Suspense>
  );
}
