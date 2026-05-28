import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { translateText, SUPPORTED_LANGUAGES } from '../translationService';

describe('translateText', () => {
    let originalFetch;

    beforeEach(() => {
        originalFetch = global.fetch;
    });

    afterEach(() => {
        global.fetch = originalFetch;
    });

    it('returns text as-is when fromLang equals toLang', async () => {
        const result = await translateText('Hello world', 'en', 'en');
        expect(result).toBe('Hello world');
    });

    it('returns text as-is when text is empty after trim', async () => {
        const result = await translateText('   ', 'hi', 'en');
        expect(result).toBe('   ');
    });

    it('returns text as-is when text is only whitespace', async () => {
        const result = await translateText('\t\n', 'fr', 'de');
        expect(result).toBe('\t\n');
    });

    it('handles API error gracefully by returning original text', async () => {
        global.fetch = vi.fn().mockResolvedValueOnce({
            ok: false,
            status: 500
        });

        const result = await translateText('Hello', 'en', 'es');
        expect(result).toBe('Hello');
    });

    it('handles network error gracefully by returning original text', async () => {
        global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

        const result = await translateText('Hello', 'en', 'es');
        expect(result).toBe('Hello');
    });

    it('parses translation response correctly', async () => {
        global.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                responseStatus: 200,
                responseData: {
                    translatedText: 'Hola mundo'
                }
            })
        });

        const result = await translateText('Hello world', 'en', 'es');
        expect(result).toBe('Hola mundo');
    });

    it('handles non-200 response status', async () => {
        global.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                responseStatus: 403,
                responseDetails: 'INVALID LANGUAGE PAIR'
            })
        });

        const result = await translateText('Hello', 'xx', 'yy');
        expect(result).toBe('Hello');
    });
});

describe('SUPPORTED_LANGUAGES', () => {
    it('is a non-empty array', () => {
        expect(Array.isArray(SUPPORTED_LANGUAGES)).toBe(true);
        expect(SUPPORTED_LANGUAGES.length).toBeGreaterThan(0);
    });

    it('each language has code, label, and nativeName', () => {
        SUPPORTED_LANGUAGES.forEach(lang => {
            expect(lang).toHaveProperty('code');
            expect(lang).toHaveProperty('label');
            expect(lang).toHaveProperty('nativeName');
            expect(typeof lang.code).toBe('string');
            expect(typeof lang.label).toBe('string');
            expect(typeof lang.nativeName).toBe('string');
        });
    });

    it('includes English as a supported language', () => {
        const english = SUPPORTED_LANGUAGES.find(l => l.code === 'en');
        expect(english).toBeDefined();
        expect(english.label).toContain('English');
    });

    it('all language codes are 2 characters', () => {
        SUPPORTED_LANGUAGES.forEach(lang => {
            expect(lang.code.length).toBe(2);
        });
    });
});
