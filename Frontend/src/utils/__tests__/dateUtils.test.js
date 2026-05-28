import { describe, it, expect } from 'vitest';
import { formatTimelineDate, getTimeZoneAbbr, formatFullTimestamp } from '../dateUtils';

describe('formatTimelineDate', () => {
    it('returns null for null input', () => {
        expect(formatTimelineDate(null)).toBeNull();
    });

    it('returns null for undefined input', () => {
        expect(formatTimelineDate(undefined)).toBeNull();
    });

    it('returns null for empty string', () => {
        expect(formatTimelineDate('')).toBeNull();
    });

    it('returns "Invalid Date" for invalid date string', () => {
        expect(formatTimelineDate('not-a-date')).toBe('Invalid Date');
    });

    it('parses ISO date string with Z suffix correctly', () => {
        const result = formatTimelineDate('2024-01-15T10:30:00Z');
        expect(result).toContain('2024');
        expect(result).toContain('Jan');
        expect(result).toContain('15');
    });

    it('appends Z to date strings without timezone', () => {
        const result = formatTimelineDate('2024-01-15T10:30:00');
        expect(result).toContain('2024');
    });

    it('returns formatted date with day, month, year, hour, minute', () => {
        const result = formatTimelineDate('2024-03-20T14:45:00Z');
        expect(result).toContain('Mar');
        expect(result).toContain('20');
        expect(result).toContain('2024');
    });
});

describe('getTimeZoneAbbr', () => {
    it('returns a string', () => {
        const result = getTimeZoneAbbr();
        expect(typeof result).toBe('string');
    });

    it('returns non-empty string', () => {
        const result = getTimeZoneAbbr();
        expect(result.length).toBeGreaterThan(0);
    });
});

describe('formatFullTimestamp', () => {
    it('returns "Processing..." for null input', () => {
        expect(formatFullTimestamp(null)).toBe('Processing...');
    });

    it('returns "Processing..." for undefined input', () => {
        expect(formatFullTimestamp(undefined)).toBe('Processing...');
    });

    it('returns formatted timestamp with timezone for valid date', () => {
        const result = formatFullTimestamp('2024-01-15T10:30:00Z');
        expect(result).not.toContain('Processing...');
        expect(result).toContain('2024');
    });

    it('includes timezone abbreviation in result', () => {
        const result = formatFullTimestamp('2024-01-15T10:30:00Z');
        expect(result).toMatch(/\([A-Z0-9+-:]+\)/);
    });
});
