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
