import { describe, it, expect } from 'vitest';
import { formatTicketId } from '../format';

describe('formatTicketId', () => {
    it('returns empty string for null input', () => {
        expect(formatTicketId(null)).toBe('');
    });

    it('returns empty string for undefined input', () => {
        expect(formatTicketId(undefined)).toBe('');
    });

    it('returns empty string for empty string input', () => {
        expect(formatTicketId('')).toBe('');
    });

    it('returns single character as-is', () => {
        expect(formatTicketId('A')).toBe('A');
    });

    it('returns short strings (length <= 8) as-is', () => {
        expect(formatTicketId('ABC12345')).toBe('ABC12345');
        expect(formatTicketId('SHORTID')).toBe('SHORTID');
        expect(formatTicketId('12345678')).toBe('12345678');
    });

    it('extracts and uppercases first UUID segment', () => {
        expect(formatTicketId('abc-def-ghi-jkl')).toBe('ABC');
        expect(formatTicketId('550e8400-e29b-41d4-a716-446655440000')).toBe('550E8400');
    });

    it('handles numeric IDs (no hyphen, no truncation)', () => {
        expect(formatTicketId('123456789')).toBe('123456789');
    });

    it('handles mixed case UUID input', () => {
        expect(formatTicketId('aBc-DeF-gHi-jKl')).toBe('ABC');
    });
});
