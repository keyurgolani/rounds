import { describe, it, expect } from 'vitest';
import { slugify } from '../slug';

describe('slugify', () => {
  it('lowercases and hyphenates', () => {
    expect(slugify('Design a URL Shortener')).toBe('design-a-url-shortener');
  });
  it('strips parentheses and punctuation', () => {
    expect(slugify('Design a URL Shortener (like bit.ly)')).toBe('design-a-url-shortener-like-bit-ly');
  });
  it('collapses consecutive non-alnum into a single hyphen', () => {
    expect(slugify('A   B___C')).toBe('a-b-c');
  });
  it('handles diacritics', () => {
    expect(slugify('Caf\u00e9 r\u00e9sum\u00e9')).toBe('cafe-resume');
  });
  it('returns empty for empty/null input', () => {
    expect(slugify('')).toBe('');
    expect(slugify(null)).toBe('');
    expect(slugify(undefined)).toBe('');
  });
});
