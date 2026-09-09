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

  it('invents nothing until an operator starts it', () => {
    // These reports are simulated. The digital twin shows them beside real
    // network geometry, so they must never appear unasked.
    const { result } = renderHook(
      () => useReportSimulation([segment], { seed: 42, spawnIntervalMs: 2_000 }),
      { wrapper: StrictMode }
    );
    expect(result.current.running).toBe(false);
    act(() => vi.advanceTimersByTime(60_000));
    expect(result.current.reports).toHaveLength(0);
  });

  it('generates reports over time and pauses cleanly', () => {
    const { result } = renderHook(
      () => useReportSimulation([segment], { seed: 42, spawnIntervalMs: 2_000, autoStart: true }),
      { wrapper: StrictMode }
    );
    act(() => vi.advanceTimersByTime(2_000));
    expect(result.current.reports).toHaveLength(1);
    act(() => result.current.pause());
    act(() => vi.advanceTimersByTime(4_000));
    expect(result.current.reports).toHaveLength(1);
  });

  it('reset reproduces the first report', () => {
    const { result } = renderHook(() => useReportSimulation([segment], { seed: 42, spawnIntervalMs: 2_000, autoStart: true }));
    act(() => vi.advanceTimersByTime(2_000));
    const coordinates = result.current.reports[0].coordinates;
    act(() => result.current.reset());
    act(() => vi.advanceTimersByTime(2_000));
    expect(result.current.reports[0].coordinates).toEqual(coordinates);
  });
});
