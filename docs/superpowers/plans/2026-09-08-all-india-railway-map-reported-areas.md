# All-India Railway Map and Reported Areas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the RailOS Network page render hosted railway tracks across India and show deterministic, code-generated reported areas as directional triangles placed on RailOS vector segments.

**Architecture:** MapLibre retains the hosted basemap and gains an idempotent OpenRailwayMap raster overlay. A framework-independent seeded simulator generates typed `ReportedArea` records from existing vector segments; a React hook owns timers and deck.gl renders the records through an `IconLayer`. A later report API can emit the same contract without changing rendering.

**Tech Stack:** Next.js 16, React 19, TypeScript, MapLibre GL JS 6, deck.gl 9, Vitest 4, Testing Library.

**Design references:** `docs/designpowers/briefs/2026-09-08-all-india-railway-map-reported-areas.md`, `docs/superpowers/specs/2026-09-08-all-india-railway-map-reported-areas-design.md`, and `DESIGN_SYSTEM.md`.

---

## File map

| Path | Responsibility |
|---|---|
| `apps/control-center/src/types/network.ts` | Reported-area and selection contracts |
| `apps/control-center/src/components/map/featureAdapters.ts` | Report-to-selection conversion |
| `apps/control-center/src/components/map/reportSimulation.ts` | Seeded generation, interpolation, bearing, lifecycle |
| `apps/control-center/src/components/map/useReportSimulation.ts` | Timers and simulation commands |
| `apps/control-center/src/components/map/railwayOverlay.ts` | Hosted railway source/layer and error classification |
| `apps/control-center/src/components/map/reportedAreaLayer.ts` | Triangle `IconLayer` factory |
| `apps/control-center/src/components/map/ReportSimulationControls.tsx` | Accessible simulator controls |
| `apps/control-center/src/components/map/layers.ts` | Operational layer composition |
| `apps/control-center/src/components/map/GeographicMap.tsx` | Map lifecycle and report UI integration |
| `apps/control-center/src/app/(shell)/network/page.tsx` | Report URL selection |

No API, database, ingestion, or optimizer file changes in this increment.

---

### Task 1: Add the reported-area contract and adapter

**Files:**
- Modify: `apps/control-center/src/types/network.ts`
- Modify: `apps/control-center/src/components/map/featureAdapters.ts`
- Create: `apps/control-center/src/components/map/__tests__/featureAdapters.test.ts`

- [ ] **Step 1: Write the failing adapter test**

```ts
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
```

- [ ] **Step 2: Run the test and verify it fails**

From `apps/control-center`, run:

```powershell
npm test -- src/components/map/__tests__/featureAdapters.test.ts
```

Expected: FAIL because `ReportedArea` and `reportedAreaFeature` do not exist.

- [ ] **Step 3: Add the canonical types**

Add before `NetworkFeatureProperties` in `src/types/network.ts`:

```ts
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
```

Extend `NetworkFeatureProperties.entityType` with `'report'` and add:

```ts
reportId?: string;
severity?: ReportSeverity;
reportStatus?: ReportedAreaStatus;
reportedAt?: string;
coordinates?: [number, number];
uncertaintyMetersBefore?: number;
uncertaintyMetersAfter?: number;
```

- [ ] **Step 4: Add the adapter**

Import `ReportedArea` in `featureAdapters.ts` and append:

```ts
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
```

- [ ] **Step 5: Run the test and commit**

```powershell
npm test -- src/components/map/__tests__/featureAdapters.test.ts
git add src/types/network.ts src/components/map/featureAdapters.ts src/components/map/__tests__/featureAdapters.test.ts
git commit -m "feat(map): add reported area contract"
```

Expected: one passing test and a commit containing only the three listed files.

---

### Task 2: Build the deterministic track-placement engine

**Files:**
- Create: `apps/control-center/src/components/map/reportSimulation.ts`
- Create: `apps/control-center/src/components/map/__tests__/reportSimulation.test.ts`

- [ ] **Step 1: Write failing geometry and lifecycle tests**

```ts
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
```

- [ ] **Step 2: Run the test and verify the module is missing**

```powershell
npm test -- src/components/map/__tests__/reportSimulation.test.ts
```

Expected: FAIL because `reportSimulation.ts` does not exist.

- [ ] **Step 3: Implement the pure simulator**

Create `reportSimulation.ts` with these exported functions and constants:

```ts
import type { RailwaySegment, ReportedArea, ReportSeverity } from '@/types/network';

export type RandomSource = () => number;
const EARTH_RADIUS_METERS = 6_371_000;
const AUTO_ACKNOWLEDGE_MS = 8_000;
const AUTO_CLEAR_MS = 18_000;
const rad = (value: number) => value * Math.PI / 180;

function distanceMeters(a: [number, number], b: [number, number]): number {
  const lat1 = rad(a[1]); const lat2 = rad(b[1]);
  const dLat = lat2 - lat1; const dLon = rad(b[0] - a[0]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.sqrt(h));
}

function bearing(a: [number, number], b: [number, number]): number {
  const lat1 = rad(a[1]); const lat2 = rad(b[1]); const dLon = rad(b[0] - a[0]);
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

export function createSeededRandom(seed: number): RandomSource {
  let state = seed >>> 0 || 1;
  return () => {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    return (state >>> 0) / 4_294_967_296;
  };
}

export function pointAlongLine(coordinates: [number, number][], fraction: number) {
  if (coordinates.length < 2) return null;
  const lengths = coordinates.slice(1).map((point, index) => distanceMeters(coordinates[index], point));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  if (total <= 0) return null;
  let remaining = Math.min(1, Math.max(0, fraction)) * total;
  for (let index = 0; index < lengths.length; index += 1) {
    if (remaining <= lengths[index] || index === lengths.length - 1) {
      const local = lengths[index] === 0 ? 0 : remaining / lengths[index];
      const start = coordinates[index]; const end = coordinates[index + 1];
      return {
        coordinates: [start[0] + (end[0] - start[0]) * local, start[1] + (end[1] - start[1]) * local] as [number, number],
        bearingDegrees: bearing(start, end),
      };
    }
    remaining -= lengths[index];
  }
  return null;
}

function severity(random: RandomSource): ReportSeverity {
  const value = random();
  return value >= 0.85 ? 'CRITICAL' : value >= 0.45 ? 'WARNING' : 'INFO';
}

export function createSimulatedReport(segments: RailwaySegment[], random: RandomSource, sequence: number, nowMs: number): ReportedArea | null {
  const eligible = segments.filter((item) => item.geometry.type === 'LineString' && item.geometry.coordinates.length >= 2);
  if (eligible.length === 0) return null;
  const segment = eligible[Math.floor(random() * eligible.length)];
  const placement = pointAlongLine(segment.geometry.coordinates as [number, number][], 0.1 + random() * 0.8);
  if (!placement) return null;
  return {
    reportId: `SIM-${String(sequence).padStart(4, '0')}`,
    segmentId: segment.segmentId, sectionId: segment.sectionId,
    coordinates: placement.coordinates, bearingDegrees: placement.bearingDegrees,
    uncertaintyMetersBefore: 2 + random(), uncertaintyMetersAfter: 2 + random(),
    severity: severity(random), status: 'NEW', reportedAt: new Date(nowMs).toISOString(), synthetic: true,
  };
}

export function advanceReportLifecycle(report: ReportedArea, nowMs: number): ReportedArea {
  const age = nowMs - Date.parse(report.reportedAt);
  if (age >= AUTO_CLEAR_MS && report.status !== 'CLEARED') return { ...report, status: 'CLEARED', clearedAt: new Date(nowMs).toISOString() };
  if (age >= AUTO_ACKNOWLEDGE_MS && report.status === 'NEW') return { ...report, status: 'ACKNOWLEDGED', acknowledgedAt: new Date(nowMs).toISOString() };
  return report;
}
```

- [ ] **Step 4: Run the focused test and commit**

```powershell
npm test -- src/components/map/__tests__/reportSimulation.test.ts
git add src/components/map/reportSimulation.ts src/components/map/__tests__/reportSimulation.test.ts
git commit -m "feat(map): generate deterministic track reports"
```

Expected: five passing tests.

---

### Task 3: Add the timer-owning simulation hook

**Files:**
- Create: `apps/control-center/src/components/map/useReportSimulation.ts`
- Create: `apps/control-center/src/components/map/__tests__/useReportSimulation.test.tsx`

- [ ] **Step 1: Write failing hook tests with fake timers**

Use the `RailwaySegment` fixture from Task 2 in this test:

```tsx
import { act, renderHook } from '@testing-library/react';
import { StrictMode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useReportSimulation } from '../useReportSimulation';
import type { RailwaySegment } from '@/types/network';

const segment = {
  segmentId: 'SEG_TEST', sectionId: 'SEC_TEST', divisionId: 'DIV_TEST', zoneId: 'ZONE_TEST',
  geometry: { type: 'LineString', coordinates: [[77, 28], [77.01, 28.01]] },
  riskScore: 50, maintenancePressure: 50, trafficPressure: 50,
  activeBlock: false, planningEnabled: false,
  provenance: { synthetic: true, label: 'Test', source: 'test' },
} satisfies RailwaySegment;

describe('useReportSimulation', () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(new Date('2026-09-08T12:00:00Z')); });
  afterEach(() => vi.useRealTimers());

  it('generates reports over time and pauses cleanly', () => {
    const { result } = renderHook(
      () => useReportSimulation([segment], { seed: 42, spawnIntervalMs: 2_000 }),
      { wrapper: StrictMode }
    );
    act(() => vi.advanceTimersByTime(2_000));
    expect(result.current.reports).toHaveLength(1);
    act(() => result.current.pause());
    act(() => vi.advanceTimersByTime(4_000));
    expect(result.current.reports).toHaveLength(1);
  });

  it('reset reproduces the first report', () => {
    const { result } = renderHook(() => useReportSimulation([segment], { seed: 42, spawnIntervalMs: 2_000 }));
    act(() => vi.advanceTimersByTime(2_000));
    const coordinates = result.current.reports[0].coordinates;
    act(() => result.current.reset());
    act(() => vi.advanceTimersByTime(2_000));
    expect(result.current.reports[0].coordinates).toEqual(coordinates);
  });
});
```

- [ ] **Step 2: Run the test and verify the hook is missing**

```powershell
npm test -- src/components/map/__tests__/useReportSimulation.test.tsx
```

Expected: FAIL because `useReportSimulation.ts` does not exist.

- [ ] **Step 3: Implement the hook**

```ts
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { RailwaySegment, ReportedArea } from '@/types/network';
import { advanceReportLifecycle, createSeededRandom, createSimulatedReport } from './reportSimulation';

interface SimulationOptions {
  seed?: number;
  spawnIntervalMs?: number;
  lifecycleIntervalMs?: number;
  maxReports?: number;
}

export function useReportSimulation(segments: RailwaySegment[], options: SimulationOptions = {}) {
  const seed = options.seed ?? 0x5241494c;
  const spawnIntervalMs = options.spawnIntervalMs ?? 6_000;
  const lifecycleIntervalMs = options.lifecycleIntervalMs ?? 1_000;
  const maxReports = options.maxReports ?? 12;
  const [reports, setReports] = useState<ReportedArea[]>([]);
  const [running, setRunning] = useState(true);
  const randomRef = useRef(createSeededRandom(seed));
  const sequenceRef = useRef(0);

  useEffect(() => {
    if (!running || segments.length === 0) return;
    const timer = window.setInterval(() => {
      sequenceRef.current += 1;
      const next = createSimulatedReport(segments, randomRef.current, sequenceRef.current, Date.now());
      if (next) setReports((current) => [...current, next].slice(-maxReports));
    }, spawnIntervalMs);
    return () => window.clearInterval(timer);
  }, [maxReports, running, segments, spawnIntervalMs]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      setReports((current) => current.map((report) => advanceReportLifecycle(report, Date.now())));
    }, lifecycleIntervalMs);
    return () => window.clearInterval(timer);
  }, [lifecycleIntervalMs, running]);

  const acknowledge = useCallback((reportId: string) => {
    const acknowledgedAt = new Date(Date.now()).toISOString();
    setReports((current) => current.map((report) =>
      report.reportId === reportId && report.status === 'NEW'
        ? { ...report, status: 'ACKNOWLEDGED', acknowledgedAt }
        : report
    ));
  }, []);
  const reset = useCallback(() => {
    randomRef.current = createSeededRandom(seed);
    sequenceRef.current = 0;
    setReports([]);
    setRunning(true);
  }, [seed]);

  return {
    reports,
    activeReports: reports.filter((report) => report.status !== 'CLEARED'),
    running,
    hasTrackGeometry: segments.some((segment) => segment.geometry.type === 'LineString'),
    pause: useCallback(() => setRunning(false), []),
    resume: useCallback(() => setRunning(true), []),
    acknowledge,
    reset,
  };
}
```

- [ ] **Step 4: Run the test and commit**

```powershell
npm test -- src/components/map/__tests__/useReportSimulation.test.tsx
git add src/components/map/useReportSimulation.ts src/components/map/__tests__/useReportSimulation.test.tsx
git commit -m "feat(map): add report simulation lifecycle"
```

Expected: two passing tests and no timer warning.

---

### Task 4: Install OpenRailwayMap idempotently

**Files:**
- Create: `apps/control-center/src/components/map/railwayOverlay.ts`
- Create: `apps/control-center/src/components/map/__tests__/railwayOverlay.test.ts`

- [ ] **Step 1: Write failing overlay tests**

```ts
import { describe, expect, it, vi } from 'vitest';
import { OPEN_RAILWAY_MAP_LAYER_ID, OPEN_RAILWAY_MAP_SOURCE_ID, ensureOpenRailwayMapOverlay, isOpenRailwayMapError } from '../railwayOverlay';

describe('OpenRailwayMap overlay', () => {
  it('adds the source and layer only once', () => {
    const sources = new Set<string>(); const layers = new Set<string>();
    const map = {
      getSource: vi.fn((id: string) => sources.has(id) ? {} : undefined),
      addSource: vi.fn((id: string) => sources.add(id)),
      getLayer: vi.fn((id: string) => layers.has(id) ? {} : undefined),
      addLayer: vi.fn((layer: { id: string }) => layers.add(layer.id)),
    };
    ensureOpenRailwayMapOverlay(map as never);
    ensureOpenRailwayMapOverlay(map as never);
    expect(map.addSource).toHaveBeenCalledTimes(1);
    expect(map.addLayer).toHaveBeenCalledTimes(1);
    expect(sources.has(OPEN_RAILWAY_MAP_SOURCE_ID)).toBe(true);
    expect(layers.has(OPEN_RAILWAY_MAP_LAYER_ID)).toBe(true);
  });
  it('classifies railway tile errors', () => {
    expect(isOpenRailwayMapError({ sourceId: OPEN_RAILWAY_MAP_SOURCE_ID })).toBe(true);
    expect(isOpenRailwayMapError({ error: { message: '403 from tiles.openrailwaymap.org' } })).toBe(true);
    expect(isOpenRailwayMapError({ error: { message: 'unrelated' } })).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test and verify the helper is missing**

```powershell
npm test -- src/components/map/__tests__/railwayOverlay.test.ts
```

Expected: FAIL because `railwayOverlay.ts` does not exist.

- [ ] **Step 3: Implement source, layer, and error classification**

```ts
import type { Map, RasterSourceSpecification } from 'maplibre-gl';

export const OPEN_RAILWAY_MAP_SOURCE_ID = 'openrailwaymap-standard';
export const OPEN_RAILWAY_MAP_LAYER_ID = 'openrailwaymap-standard-raster';

const source: RasterSourceSpecification = {
  type: 'raster',
  tiles: [
    'https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
    'https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
    'https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
  ],
  tileSize: 256, minzoom: 2, maxzoom: 19,
  attribution: 'Railway data © OpenStreetMap contributors, rendering © OpenRailwayMap',
};

export function ensureOpenRailwayMapOverlay(map: Pick<Map, 'getSource' | 'addSource' | 'getLayer' | 'addLayer'>): void {
  if (!map.getSource(OPEN_RAILWAY_MAP_SOURCE_ID)) map.addSource(OPEN_RAILWAY_MAP_SOURCE_ID, source);
  if (!map.getLayer(OPEN_RAILWAY_MAP_LAYER_ID)) {
    map.addLayer({
      id: OPEN_RAILWAY_MAP_LAYER_ID,
      type: 'raster', source: OPEN_RAILWAY_MAP_SOURCE_ID,
      paint: { 'raster-opacity': 0.92, 'raster-fade-duration': 150 },
    });
  }
}

export function isOpenRailwayMapError(event: unknown): boolean {
  const candidate = event as { sourceId?: string; error?: { message?: string } };
  return candidate?.sourceId === OPEN_RAILWAY_MAP_SOURCE_ID
    || candidate?.error?.message?.includes('tiles.openrailwaymap.org') === true;
}
```

- [ ] **Step 4: Run the test and commit**

```powershell
npm test -- src/components/map/__tests__/railwayOverlay.test.ts
git add src/components/map/railwayOverlay.ts src/components/map/__tests__/railwayOverlay.test.ts
git commit -m "feat(map): add hosted railway tile overlay"
```

Expected: two passing tests.

---

### Task 5: Render reports as directional triangle markers

**Files:**
- Create: `apps/control-center/src/components/map/reportedAreaLayer.ts`
- Create: `apps/control-center/src/components/map/__tests__/reportedAreaLayer.test.ts`
- Modify: `apps/control-center/src/components/map/layers.ts`

- [ ] **Step 1: Write the failing layer test**

```ts
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
```

- [ ] **Step 2: Run the test and verify the layer factory is missing**

```powershell
npm test -- src/components/map/__tests__/reportedAreaLayer.test.ts
```

Expected: FAIL because `reportedAreaLayer.ts` does not exist.

- [ ] **Step 3: Implement the triangle `IconLayer`**

```ts
import { IconLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import type { NetworkFeatureProperties, ReportedArea } from '@/types/network';
import { reportedAreaFeature } from './featureAdapters';

const triangleSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path fill="white" stroke="white" stroke-width="4" d="M32 5 59 57H5Z"/></svg>';
const triangleAtlas = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(triangleSvg)}`;
const triangleMapping = { triangle: { x: 0, y: 0, width: 64, height: 64, anchorX: 32, anchorY: 32, mask: true } };
type PickHandler = (info: { object?: NetworkFeatureProperties } | null) => void;

function severityColor(report: ReportedArea): [number, number, number, number] {
  if (report.severity === 'CRITICAL') return [239, 68, 68, 255];
  if (report.severity === 'WARNING') return [245, 158, 11, 255];
  return [56, 189, 248, 255];
}

export function buildReportedAreaLayer(reports: ReportedArea[], selectedReportId?: string, onHover?: PickHandler, onClick?: PickHandler) {
  return new IconLayer<ReportedArea>({
    id: 'reported-areas',
    data: reports.filter((report) => report.status !== 'CLEARED'),
    iconAtlas: triangleAtlas, iconMapping: triangleMapping,
    getIcon: () => 'triangle', getPosition: (report) => report.coordinates,
    getAngle: (report) => report.bearingDegrees, getColor: severityColor,
    getSize: (report) => report.reportId === selectedReportId ? 26 : 20,
    sizeUnits: 'pixels', billboard: true, pickable: true, autoHighlight: true,
    highlightColor: [255, 255, 255, 255],
    onHover: (info: PickingInfo<ReportedArea>) => onHover?.(info.object ? { object: reportedAreaFeature(info.object) } : null),
    onClick: (info: PickingInfo<ReportedArea>) => {
      if (info.object) onClick?.({ object: reportedAreaFeature(info.object) });
    },
  });
}
```

- [ ] **Step 4: Compose the report layer last**

In `layers.ts`, import `ReportedArea` and `buildReportedAreaLayer`. Add `reports: ReportedArea[]` plus `reportId?: string` under `selection` in `LayerBuildOptions`. Append this before `return layers`:

```ts
layers.push(buildReportedAreaLayer(
  options.reports,
  options.selection?.reportId,
  onHover,
  onClick
));
```

Keeping it last places reports above paths, blocks, opportunities, and stations.

- [ ] **Step 5: Run the test and commit**

```powershell
npm test -- src/components/map/__tests__/reportedAreaLayer.test.ts
git add src/components/map/reportedAreaLayer.ts src/components/map/layers.ts src/components/map/__tests__/reportedAreaLayer.test.ts
git commit -m "feat(map): render track-aligned report triangles"
```

Expected: one passing layer test.

---

### Task 6: Add accessible simulation controls

**Files:**
- Create: `apps/control-center/src/components/map/ReportSimulationControls.tsx`
- Create: `apps/control-center/src/components/map/__tests__/ReportSimulationControls.test.tsx`

- [ ] **Step 1: Write failing accessible-control tests**

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ReportSimulationControls } from '../ReportSimulationControls';

describe('ReportSimulationControls', () => {
  it('exposes count, pause, and reset as text controls', () => {
    const pause = vi.fn(); const reset = vi.fn();
    render(<ReportSimulationControls running hasTrackGeometry activeCount={3} onPause={pause} onResume={vi.fn()} onReset={reset} />);
    expect(screen.getByRole('status')).toHaveTextContent('3 active simulated reports');
    fireEvent.click(screen.getByRole('button', { name: 'Pause report simulation' }));
    fireEvent.click(screen.getByRole('button', { name: 'Reset report simulation' }));
    expect(pause).toHaveBeenCalledOnce(); expect(reset).toHaveBeenCalledOnce();
  });
  it('announces missing track geometry', () => {
    render(<ReportSimulationControls running hasTrackGeometry={false} activeCount={0} onPause={vi.fn()} onResume={vi.fn()} onReset={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent('waiting for track geometry');
  });
});
```

- [ ] **Step 2: Run the test and verify the component is missing**

```powershell
npm test -- src/components/map/__tests__/ReportSimulationControls.test.tsx
```

Expected: FAIL because `ReportSimulationControls.tsx` does not exist.

- [ ] **Step 3: Implement token-based controls**

```tsx
'use client';

import { Pause, Play, RotateCcw, TriangleAlert } from 'lucide-react';

interface Props {
  running: boolean; hasTrackGeometry: boolean; activeCount: number;
  onPause: () => void; onResume: () => void; onReset: () => void;
}

export function ReportSimulationControls(props: Props) {
  const message = props.hasTrackGeometry
    ? `${props.activeCount} active simulated reports · ${props.running ? 'running' : 'paused'}`
    : 'Simulation waiting for track geometry';
  return (
    <div className="flex items-center gap-2 rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[10px] font-mono text-[var(--text-secondary)]">
      <TriangleAlert aria-hidden="true" className="h-3.5 w-3.5 text-[var(--status-warning-fg)]" />
      <span role="status" aria-live="polite">{message}</span>
      <button type="button" onClick={props.running ? props.onPause : props.onResume} disabled={!props.hasTrackGeometry} aria-label={props.running ? 'Pause report simulation' : 'Resume report simulation'} className="rounded p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info-fg)] disabled:opacity-50">
        {props.running ? <Pause aria-hidden="true" className="h-3.5 w-3.5" /> : <Play aria-hidden="true" className="h-3.5 w-3.5" />}
      </button>
      <button type="button" onClick={props.onReset} aria-label="Reset report simulation" className="rounded p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--status-info-fg)]">
        <RotateCcw aria-hidden="true" className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run the test and commit**

```powershell
npm test -- src/components/map/__tests__/ReportSimulationControls.test.tsx
git add src/components/map/ReportSimulationControls.tsx src/components/map/__tests__/ReportSimulationControls.test.tsx
git commit -m "feat(map): add accessible report controls"
```

Expected: two passing component tests.

---

### Task 7: Integrate railway tiles and simulated reports into `GeographicMap`

**Files:**
- Modify: `apps/control-center/src/components/map/GeographicMap.tsx`
- Modify: `apps/control-center/src/app/(shell)/network/page.tsx`

- [ ] **Step 1: Extend map selection and instantiate simulation**

Add imports in `GeographicMap.tsx`:

```ts
import { ReportSimulationControls } from './ReportSimulationControls';
import { reportedAreaFeature } from './featureAdapters';
import { useReportSimulation } from './useReportSimulation';
import { OPEN_RAILWAY_MAP_SOURCE_ID, ensureOpenRailwayMapOverlay, isOpenRailwayMapError } from './railwayOverlay';
```

Add `reportId?: string` to `SelectionState`, then add inside the component:

```ts
type RailwayRuntimeState = 'loading' | 'ready' | 'error';

const simulation = useReportSimulation(data.segments);
const { acknowledge } = simulation;
const [railwayState, setRailwayState] = useState<RailwayRuntimeState>('loading');
const selectedReport = simulation.reports.find((report) => report.reportId === selection?.reportId);
```

Add `styleUrl: string` to `GeographicMapProps`, accept it in the component arguments, and replace `MAP_STYLE_URL` in the MapLibre constructor with `styleUrl`. Add `styleUrl` to the map lifecycle effect dependency list. This moves the environment-derived value out of the dynamically imported component and ensures a missing value cannot silently produce a style-less map.

Add report features to `keyboardFeatures` and include `simulation.activeReports` in the memo dependency list:

```ts
...simulation.activeReports.map(reportedAreaFeature),
```

- [ ] **Step 2: Install and observe the railway overlay**

Inside the existing MapLibre lifecycle effect, add:

```ts
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
```

Call `installRailwayOverlay()` at the end of `handleStyleLoad`. Register `map.on('sourcedata', handleSourceData)` and remove it in cleanup. Add this at the beginning of `handleError`:

```ts
if (isOpenRailwayMapError(event)) {
  setRailwayState('error');
  return;
}
```

This keeps railway tile failures from replacing the basemap style. Because fallback `map.setStyle` emits `style.load`, the overlay is reinstalled after fallback without duplication.

- [ ] **Step 3: Acknowledge report clicks and pass reports to deck.gl**

Replace `handleClick` with:

```ts
const handleClick = useCallback((info: { object?: NetworkFeatureProperties }) => {
  if (!info.object) return;
  if (info.object.entityType === 'report' && info.object.reportId) {
    acknowledge(info.object.reportId);
  }
  onSelect?.(info.object);
}, [acknowledge, onSelect]);
```

Pass these additional values to `buildLayers`:

```ts
reports: simulation.activeReports,
selection,
```

Add `simulation.activeReports` to that effect's dependencies.

- [ ] **Step 4: Render railway and simulator status**

Under the existing map runtime card, add:

```tsx
<div role="status" aria-live="polite" className="rounded border border-[var(--border-default)] bg-[var(--bg-overlay)]/95 px-3 py-2 text-[10px] font-mono text-[var(--text-secondary)]">
  Railway tracks: {railwayState === 'ready' ? 'ready' : railwayState === 'error' ? 'unavailable' : 'loading…'}
</div>
<ReportSimulationControls
  running={simulation.running}
  hasTrackGeometry={simulation.hasTrackGeometry}
  activeCount={simulation.activeReports.length}
  onPause={simulation.pause}
  onResume={simulation.resume}
  onReset={simulation.reset}
/>
```

- [ ] **Step 5: Render selected-report detail**

Add before the attribution:

```tsx
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
```

- [ ] **Step 6: Persist report selection in the URL**

In `network/page.tsx`, define the basemap value outside `NetworkWorkspace`:

```ts
const MAP_STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL || 'https://tiles.openfreemap.org/styles/fiord';
```

Pass `styleUrl={MAP_STYLE_URL}` to `GeographicMap`. Add `reportId: params.get('report') ?? undefined` to `selection`, then replace the selection update with:

```ts
setParams({
  zone: entity.zoneId,
  division: entity.divisionId,
  section: entity.sectionId,
  report: entity.reportId,
});
```

- [ ] **Step 7: Run all automated checks**

From `apps/control-center`:

```powershell
npm test -- src/components/map/__tests__
npm test
npm run lint
npm run build
```

Expected: all map and full-suite tests pass, ESLint exits zero without new warnings, and the Next.js production build exits zero.

- [ ] **Step 8: Commit the integration**

```powershell
git add src/components/map/GeographicMap.tsx 'src/app/(shell)/network/page.tsx'
git commit -m "feat(map): integrate railway tracks and simulated reports"
```

---

### Task 8: Browser acceptance and failure verification

**Files:**
- Modify only if a verified defect is found: files listed in Tasks 1–7

- [ ] **Step 1: Start the API**

From the repository root:

```powershell
python -m uvicorn apps.api.railos_api.main:app --reload --port 8000
```

Expected: Uvicorn reports that it is listening on `http://127.0.0.1:8000`.

- [ ] **Step 2: Start the control center**

From `apps/control-center` in a second terminal:

```powershell
npm run dev
```

Expected: Next.js reports a local URL and compiles `/network` without error.

- [ ] **Step 3: Verify nationwide railway visibility**

Open `/network`, fit the viewport to India, and inspect browser network requests.

Expected:
- Basemap paints.
- Railway tracks appear across India.
- Requests reach `a`, `b`, or `c.tiles.openrailwaymap.org/standard/...png`.
- Railway status changes to `ready`.
- OpenStreetMap, OpenRailwayMap, OpenFreeMap, and MapLibre attribution is visible.

- [ ] **Step 4: Verify report behavior**

Wait for two spawn intervals, pause, resume, reset, and select a triangle from both the canvas and “Browse map features.”

Expected:
- Reports appear on RailOS segment paths in multiple Indian regions over time.
- Triangle orientation follows the selected segment.
- Pause stops new reports; resume restarts them.
- Reset clears reports and repeats the seeded sequence.
- Detail shows ID, severity, lifecycle status, section, segment, coordinates, ±2–3 m uncertainty, and synthetic source.
- Selecting `NEW` changes it to `ACKNOWLEDGED`; `CLEARED` disappears from the active layer.

- [ ] **Step 5: Verify failure and accessibility behavior**

Block `tiles.openrailwaymap.org` in browser developer tools and reload. Then test with `prefers-reduced-motion: reduce`, keyboard-only navigation, and 200% zoom.

Expected:
- Railway status becomes `unavailable`; basemap and local RailOS overlays remain usable.
- No off-track fallback report appears.
- Controls and report buttons have visible focus and descriptive names.
- Status is textually available and not colour-only.
- No motion is required to understand state.
- Map controls and report detail remain usable at 200% zoom.

- [ ] **Step 6: Re-run checks after any browser-found fix**

```powershell
npm test
npm run lint
npm run build
```

Expected: all commands exit zero. Commit only if files changed:

```powershell
git add src/components/map src/types/network.ts 'src/app/(shell)/network/page.tsx'
git commit -m "fix(map): satisfy railway report acceptance checks"
```

Do not create an empty commit when acceptance passes without changes.

---

## Completion gate

- [ ] Hosted railway tiles visibly render across India.
- [ ] Railway failure has its own truthful status.
- [ ] Reports come from seeded code and vector geometry, not fixed coordinates.
- [ ] Triangles are track-aligned, selectable, and labelled synthetic with ±2–3 m uncertainty.
- [ ] Pause, resume, reset, acknowledge, and clear behavior works.
- [ ] Keyboard, screen-reader text, reduced motion, and 200% zoom checks pass.
- [ ] Focused tests, full tests, lint, and production build pass.
