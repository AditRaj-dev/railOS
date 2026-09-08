/**
 * Tests for time.ts utilities.
 * Covers horizon-minute conversion, IST formatting, and duration formatting.
 * Run with: npx vitest run src/lib
 */

import { describe, it, expect } from 'vitest';
import { minuteToDate, dateToMinute, formatMinute, formatDuration } from '../time';

// Demo epoch from the API
const DEMO_EPOCH = '2026-09-09T00:00:00+05:30';

describe('time utilities', () => {
  describe('minuteToDate', () => {
    it('converts minute 0 to horizon start date', () => {
      const date = minuteToDate(DEMO_EPOCH, 0);
      const horizonStart = new Date(DEMO_EPOCH);
      expect(date.getTime()).toBe(horizonStart.getTime());
    });

    it('converts positive minutes correctly', () => {
      const date = minuteToDate(DEMO_EPOCH, 60);
      const horizonStart = new Date(DEMO_EPOCH);
      const expected = new Date(horizonStart.getTime() + 60 * 60 * 1000);
      expect(date.getTime()).toBe(expected.getTime());
    });

    it('handles negative minutes (before horizon)', () => {
      const date = minuteToDate(DEMO_EPOCH, -30);
      const horizonStart = new Date(DEMO_EPOCH);
      const expected = new Date(horizonStart.getTime() - 30 * 60 * 1000);
      expect(date.getTime()).toBe(expected.getTime());
    });

    it('rounds non-integer minutes', () => {
      const date1 = minuteToDate(DEMO_EPOCH, 30.4);
      const date2 = minuteToDate(DEMO_EPOCH, 30);
      expect(date1.getTime()).toBe(date2.getTime());
    });

    it('rounds 0.5 minutes up', () => {
      const date = minuteToDate(DEMO_EPOCH, 30.5);
      const date2 = minuteToDate(DEMO_EPOCH, 31);
      expect(date.getTime()).toBe(date2.getTime());
    });
  });

  describe('dateToMinute', () => {
    it('converts horizon start date to minute 0', () => {
      const horizonStart = new Date(DEMO_EPOCH);
      const minute = dateToMinute(DEMO_EPOCH, horizonStart);
      expect(minute).toBe(0);
    });

    it('converts dates to positive minutes', () => {
      const horizonStart = new Date(DEMO_EPOCH);
      const date = new Date(horizonStart.getTime() + 90 * 60 * 1000); // 90 minutes later
      const minute = dateToMinute(DEMO_EPOCH, date);
      expect(minute).toBe(90);
    });

    it('converts dates before horizon to negative minutes', () => {
      const horizonStart = new Date(DEMO_EPOCH);
      const date = new Date(horizonStart.getTime() - 45 * 60 * 1000); // 45 minutes before
      const minute = dateToMinute(DEMO_EPOCH, date);
      expect(minute).toBe(-45);
    });

    it('rounds to nearest integer', () => {
      const horizonStart = new Date(DEMO_EPOCH);
      const date = new Date(horizonStart.getTime() + 30.6 * 60 * 1000);
      const minute = dateToMinute(DEMO_EPOCH, date);
      expect(minute).toBe(31);
    });
  });

  describe('round-trip conversion', () => {
    it('minute -> date -> minute preserves value', () => {
      const originalMinute = 120;
      const date = minuteToDate(DEMO_EPOCH, originalMinute);
      const recoveredMinute = dateToMinute(DEMO_EPOCH, date);
      expect(recoveredMinute).toBe(originalMinute);
    });

    it('date -> minute -> date preserves timestamp', () => {
      const horizonStart = new Date(DEMO_EPOCH);
      const originalDate = new Date(horizonStart.getTime() + 45 * 60 * 1000);
      const minute = dateToMinute(DEMO_EPOCH, originalDate);
      const recoveredDate = minuteToDate(DEMO_EPOCH, minute);
      expect(recoveredDate.getTime()).toBe(originalDate.getTime());
    });

    it('handles large positive offsets', () => {
      const originalMinute = 4320; // 3 days
      const date = minuteToDate(DEMO_EPOCH, originalMinute);
      const recoveredMinute = dateToMinute(DEMO_EPOCH, date);
      expect(recoveredMinute).toBe(originalMinute);
    });

    it('handles negative offsets', () => {
      const originalMinute = -720; // 12 hours before
      const date = minuteToDate(DEMO_EPOCH, originalMinute);
      const recoveredMinute = dateToMinute(DEMO_EPOCH, date);
      expect(recoveredMinute).toBe(originalMinute);
    });
  });

  describe('formatMinute', () => {
    it('formats minute 0 as horizon start date', () => {
      // DEMO_EPOCH = 2026-09-09T00:00:00+05:30 (IST)
      // So minute 0 should format as "09 Sep 00:00"
      const formatted = formatMinute(DEMO_EPOCH, 0);
      expect(formatted).toMatch(/09 Sep 00:00/);
    });

    it('formats positive minutes in IST', () => {
      // 120 minutes = 2 hours after epoch
      const formatted = formatMinute(DEMO_EPOCH, 120);
      expect(formatted).toMatch(/09 Sep 02:00/);
    });

    it('formats negative minutes (before horizon)', () => {
      // -240 minutes = 4 hours before epoch = 2026-09-08T20:00 IST
      const formatted = formatMinute(DEMO_EPOCH, -240);
      expect(formatted).toMatch(/08 Sep/);
    });

    it('includes seconds when includeSeconds option is true', () => {
      const formatted = formatMinute(DEMO_EPOCH, 0, { includeSeconds: true });
      expect(formatted).toMatch(/00:00:00/);
    });

    it('uses provided locale', () => {
      // Just verify it doesn't error with a different locale
      const formatted = formatMinute(DEMO_EPOCH, 0, { locale: 'fr-FR' });
      expect(formatted).toBeTruthy();
    });

    it('formats edge case of 23:59', () => {
      // Minute 1439 = 23 hours 59 minutes
      const formatted = formatMinute(DEMO_EPOCH, 1439);
      expect(formatted).toMatch(/09 Sep 23:59/);
    });

    it('wraps to next day correctly', () => {
      // Minute 1440 = 24 hours = next day at 00:00
      const formatted = formatMinute(DEMO_EPOCH, 1440);
      expect(formatted).toMatch(/10 Sep 00:00/);
    });
  });

  describe('formatDuration', () => {
    it('formats zero minutes', () => {
      expect(formatDuration(0)).toBe('0m');
    });

    it('formats minutes only', () => {
      expect(formatDuration(45)).toBe('45m');
      expect(formatDuration(59)).toBe('59m');
    });

    it('formats hours only', () => {
      expect(formatDuration(60)).toBe('1h');
      expect(formatDuration(120)).toBe('2h');
    });

    it('formats hours and minutes', () => {
      expect(formatDuration(90)).toBe('1h 30m');
      expect(formatDuration(135)).toBe('2h 15m');
    });

    it('formats large durations', () => {
      expect(formatDuration(1440)).toBe('24h'); // 24 hours
      expect(formatDuration(1485)).toBe('24h 45m'); // 24h 45m
    });

    it('handles non-integer input (rounds)', () => {
      expect(formatDuration(45.4)).toBe('45m');
      expect(formatDuration(45.6)).toBe('46m');
      expect(formatDuration(90.1)).toBe('1h 30m');
    });

    it('treats negative input as positive for display', () => {
      expect(formatDuration(-45)).toBe('45m');
      expect(formatDuration(-90)).toBe('1h 30m');
    });

    it('handles edge case of 1 minute', () => {
      expect(formatDuration(1)).toBe('1m');
    });

    it('handles edge case of 60 minutes', () => {
      expect(formatDuration(60)).toBe('1h');
    });

    it('handles edge case of 61 minutes', () => {
      expect(formatDuration(61)).toBe('1h 1m');
    });
  });
});
