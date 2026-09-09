/**
 * Time conversion utilities between horizon-relative minutes and display timestamps.
 * The API expresses schedule times as integer minutes relative to horizonStartIso (IST).
 * This module bridges that to user-visible dates and formatted times.
 */

// ponytail: the API has no typed endpoint yet exposing horizonStartIso to the
// browser (it lives on the server's ScenarioWorld dump only) — mirror the
// backend's DEMO_EPOCH (apps/api/railos_api/main.py) until it is. Real
// horizon-relative round-tripping still lives entirely in dateToMinute below.
export const DEMO_EPOCH_ISO = '2026-09-09T00:00:00+05:30';

/**
 * Convert horizon-relative minutes to an absolute Date.
 * @param horizonStartIso - ISO 8601 string marking minute 0 (typically IST)
 * @param minute - integer minutes since horizon start (may be negative for times before horizon)
 * @returns Date object in UTC
 */
export function minuteToDate(horizonStartIso: string, minute: number): Date {
  const horizonStart = new Date(horizonStartIso);
  // Add minutes as milliseconds
  return new Date(horizonStart.getTime() + Math.round(minute) * 60 * 1000);
}

/**
 * Convert an absolute Date back to horizon-relative minutes.
 * @param horizonStartIso - ISO 8601 string marking minute 0
 * @param date - Date object (any timezone)
 * @returns integer minutes since horizon start (may be negative)
 */
export function dateToMinute(horizonStartIso: string, date: Date): number {
  const horizonStart = new Date(horizonStartIso);
  const deltaMs = date.getTime() - horizonStart.getTime();
  return Math.round(deltaMs / (60 * 1000));
}

/**
 * Format a horizon-relative minute as a human-readable timestamp.
 * Displays in IST (Asia/Kolkata), 24-hour format: "09 Sep 14:30"
 *
 * @param horizonStartIso - ISO 8601 string marking minute 0
 * @param minute - integer minutes since horizon start
 * @param opts - optional formatting options
 * @returns formatted string, e.g. "09 Sep 14:30"
 */
export function formatMinute(
  horizonStartIso: string,
  minute: number,
  opts?: { locale?: string; includeSeconds?: boolean }
): string {
  const date = minuteToDate(horizonStartIso, minute);
  const locale = opts?.locale || 'en-IN';

  const formatter = new Intl.DateTimeFormat(locale, {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(opts?.includeSeconds && { second: '2-digit' }),
  });

  // Build the "DD Mon HH:MM[:SS]" contract directly from parts rather than the
  // locale's assembled string: ICU data varies by locale/runtime in ways that
  // are irrelevant here (comma-vs-space separators, 12h vs 24h, "Sept" vs
  // "Sep"), and this display format is a fixed product contract, not a
  // locale-sensitive rendering.
  const parts = formatter.formatToParts(date);
  const get = (type: Intl.DateTimeFormatPartTypes) => parts.find(p => p.type === type)?.value ?? '';

  const day = get('day');
  const month = get('month').slice(0, 3);
  const hour = get('hour');
  const minutePart = get('minute');

  let result = `${day} ${month} ${hour}:${minutePart}`;
  if (opts?.includeSeconds) result += `:${get('second')}`;
  return result;
}

/**
 * Format a duration in minutes as human-readable text.
 * Examples: "2h 15m", "45m", "1h", "0m"
 *
 * Handles negative durations defensively (treats as positive for display).
 * Handles non-integer input (rounds).
 *
 * @param minutes - integer minutes (or close to it)
 * @returns formatted string, e.g. "2h 15m"
 */
export function formatDuration(minutes: number): string {
  const abs = Math.abs(Math.round(minutes));

  if (abs === 0) return '0m';

  const hours = Math.floor(abs / 60);
  const mins = abs % 60;

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (mins > 0) parts.push(`${mins}m`);

  return parts.join(' ');
}
