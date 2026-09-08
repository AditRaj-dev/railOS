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
