/**
 * Map rendering modes: MAINTENANCE | RISK | OPERATIONS | OPPORTUNITY.
 * Each mode maps network metrics to colour ramps and line widths.
 * All colours paired with labels/icons for accessibility (no colour-only states).
 */

export type MapMode = 'MAINTENANCE' | 'RISK' | 'OPERATIONS' | 'OPPORTUNITY';

export interface ModeStyleConfig {
  mode: MapMode;
  label: string;
  getColor: (value: number) => string;
  getColorLabel: (value: number) => string;
  getWidth: (value: number) => number;
  metricField: string;
}

/**
 * Colour ramps are derived from the semantic status tokens defined in
 * globals.css (--status-{ok,info,caution,warning,critical,blocked,unknown}-fg),
 * not hand-picked hexes. This keeps map colours, schematic colours, and chip
 * colours in one system. Fallback hexes below mirror the CSS token defaults
 * for server-side/no-DOM contexts; the browser value (if present) wins.
 */
type StatusTokenName = 'ok' | 'info' | 'caution' | 'warning' | 'critical' | 'blocked' | 'unknown';

const STATUS_TOKEN_FALLBACKS: Record<StatusTokenName, string> = {
  ok: '#8fb38b',
  info: '#6b9ac4',
  caution: '#d39a59',
  warning: '#e8a317',
  critical: '#d97864',
  blocked: '#a27dd4',
  unknown: '#918b80',
};

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const bigint = parseInt(clean, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

let cachedTokenColors: Record<StatusTokenName, { hex: string; rgb: number[] }> | null = null;

/** Reads --status-*-fg custom properties from the document once and caches the result. */
function statusTokenColors(): Record<StatusTokenName, { hex: string; rgb: number[] }> {
  if (cachedTokenColors) return cachedTokenColors;
  const result = {} as Record<StatusTokenName, { hex: string; rgb: number[] }>;
  (Object.keys(STATUS_TOKEN_FALLBACKS) as StatusTokenName[]).forEach((name) => {
    let hex = STATUS_TOKEN_FALLBACKS[name];
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      const value = getComputedStyle(document.documentElement)
        .getPropertyValue(`--status-${name}-fg`)
        .trim();
      if (value) hex = value;
    }
    result[name] = { hex, rgb: hexToRgb(hex) };
  });
  cachedTokenColors = result;
  return result;
}

function rampStop(token: StatusTokenName, label: string) {
  const color = statusTokenColors()[token];
  return { hex: color.hex, label, rgb: color.rgb };
}

function buildRamps() {
  return {
    maintenance: {
      // token ok → caution → critical, keyed by maintenanceDebt (0-100)
      0: rampStop('ok', 'Healthy'),
      30: rampStop('caution', 'Due soon'),
      70: rampStop('critical', 'Overdue'),
    },
    risk: {
      // token ok → warning → critical, keyed by riskScore (0-100)
      0: rampStop('ok', 'Low risk'),
      40: rampStop('warning', 'Medium risk'),
      70: rampStop('critical', 'High risk'),
    },
    operations: {
      // token info → caution → warning, keyed by trafficPressure (0-200)
      0: rampStop('info', 'Low pressure'),
      100: rampStop('caution', 'Moderate pressure'),
      160: rampStop('warning', 'High pressure'),
    },
    opportunity: {
      // token unknown → caution → ok, keyed by openOpportunityCount (0-10+)
      0: rampStop('unknown', 'No opportunities'),
      5: rampStop('caution', 'Multiple opportunities'),
      10: rampStop('ok', 'Many opportunities'),
    },
  };
}

function interpolateColor(
  value: number,
  ramp: Record<number, { hex: string; label: string; rgb: number[] }>,
  max: number
): { hex: string; label: string; rgb: number[] } {
  const keys = Object.keys(ramp)
    .map(Number)
    .sort((a, b) => a - b);

  if (value <= keys[0]) return ramp[keys[0]];
  if (value >= keys[keys.length - 1]) return ramp[keys[keys.length - 1]];

  for (let i = 0; i < keys.length - 1; i++) {
    const k1 = keys[i];
    const k2 = keys[i + 1];
    if (value >= k1 && value <= k2) {
      const t = (value - k1) / (k2 - k1);
      const c1 = ramp[k1];
      const c2 = ramp[k2];

      const r = Math.round(c1.rgb[0] + (c2.rgb[0] - c1.rgb[0]) * t);
      const g = Math.round(c1.rgb[1] + (c2.rgb[1] - c1.rgb[1]) * t);
      const b = Math.round(c1.rgb[2] + (c2.rgb[2] - c1.rgb[2]) * t);

      return {
        hex: `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`,
        label: `${c1.label} → ${c2.label}`,
        rgb: [r, g, b],
      };
    }
  }

  return ramp[keys[0]];
}

export const mapModes: Record<MapMode, ModeStyleConfig> = {
  MAINTENANCE: {
    mode: 'MAINTENANCE',
    label: 'Maintenance Debt',
    metricField: 'maintenanceDebt',
    getColor: (value: number) => {
      const result = interpolateColor(value, buildRamps().maintenance, 100);
      return result.hex;
    },
    getColorLabel: (value: number) => {
      const result = interpolateColor(value, buildRamps().maintenance, 100);
      return result.label;
    },
    getWidth: (value: number) => {
      const normalized = Math.max(0, Math.min(100, value));
      return 1.5 + (normalized / 100) * 2;
    },
  },

  RISK: {
    mode: 'RISK',
    label: 'Risk Score',
    metricField: 'riskScore',
    getColor: (value: number) => {
      const result = interpolateColor(value, buildRamps().risk, 100);
      return result.hex;
    },
    getColorLabel: (value: number) => {
      const result = interpolateColor(value, buildRamps().risk, 100);
      return result.label;
    },
    getWidth: (value: number) => {
      const normalized = Math.max(0, Math.min(100, value));
      return 1.5 + (normalized / 100) * 3;
    },
  },

  OPERATIONS: {
    mode: 'OPERATIONS',
    label: 'Traffic Pressure',
    metricField: 'trafficPressure',
    getColor: (value: number) => {
      const result = interpolateColor(value, buildRamps().operations, 200);
      return result.hex;
    },
    getColorLabel: (value: number) => {
      const result = interpolateColor(value, buildRamps().operations, 200);
      return result.label;
    },
    getWidth: (value: number) => {
      const normalized = Math.max(0, Math.min(200, value));
      return 1 + (normalized / 200) * 3;
    },
  },

  OPPORTUNITY: {
    mode: 'OPPORTUNITY',
    label: 'Planning Opportunities',
    metricField: 'openOpportunityCount',
    getColor: (value: number) => {
      const normalizedValue = Math.min(10, value);
      const result = interpolateColor(normalizedValue, buildRamps().opportunity, 10);
      return result.hex;
    },
    getColorLabel: (value: number) => {
      const normalizedValue = Math.min(10, value);
      const result = interpolateColor(normalizedValue, buildRamps().opportunity, 10);
      return result.label;
    },
    getWidth: (value: number) => {
      return value > 0 ? 2.5 : 1;
    },
  },
};

export function getModeConfig(mode: MapMode): ModeStyleConfig {
  return mapModes[mode];
}

export function getStyleForMetric(mode: MapMode, value: number): string {
  const config = mapModes[mode];
  return config.getColor(value);
}

export function getLabelForMetric(mode: MapMode, value: number): string {
  const config = mapModes[mode];
  return config.getColorLabel(value);
}
