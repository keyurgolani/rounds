import { describe, expect, it } from 'vitest';
import {
  mentionRoute,
  mentionToken,
  parseMentions,
  splitBody,
  type Mention,
} from '../mentions';

describe('mentions parser', () => {
  it('extracts a single mention token', () => {
    const out = parseMentions('Prep [[coding-question:two-sum|Two Sum]] tonight.');
    expect(out).toEqual([
      { type: 'coding-question', slug: 'two-sum', label: 'Two Sum' },
    ]);
  });

  it('ignores duplicates', () => {
    const out = parseMentions(
      'A [[campaign:swe|SWE]] and another [[campaign:swe|SWE]] mention.',
    );
    expect(out).toHaveLength(1);
  });

  it('treats an unknown type as plain text', () => {
    const chunks = splitBody('Look at [[mystery:42|thing]] please.');
    expect(chunks.map((c) => (c.kind === 'text' ? c.text : c.mention.slug))).toEqual([
      'Look at ',
      '[[mystery:42|thing]]',
      ' please.',
    ]);
  });

  it('falls back to slug when label is omitted', () => {
    const out = parseMentions('Revisit [[behavioral-category:leadership]]');
    expect(out[0].label).toBe('leadership');
  });

  it('roundtrips a mention through token + parse', () => {
    const m: Mention = {
      type: 'application',
      slug: 'meta-sde',
      label: 'Meta SDE',
    };
    const body = `Follow up with ${mentionToken(m)} this week`;
    expect(parseMentions(body)).toEqual([m]);
  });

  it('routes each mention type', () => {
    const cases: Array<[Mention['type'], string, string]> = [
      ['sd-question', 'url-shortener', '/system-design/question/url-shortener'],
      ['coding-question', 'two-sum', '/coding/question/two-sum'],
      ['behavioral-question', 'tell-me-about', '/behavioral/question/tell-me-about'],
      ['behavioral-category', 'leadership', '/behavioral?category=leadership'],
      ['coding-tag', 'dp', '/coding?tag=dp'],
      ['sd-tag', 'cache', '/system-design?tag=cache'],
      ['application', 'meta-sde', '/applications/meta-sde'],
      ['round', 'abc123', '/interviews/abc123'],
      ['anecdote', 'aws-migration', '/experience/list?anecdote=aws-migration'],
      ['campaign', 'summer-hunt', '/campaigns/summer-hunt'],
    ];
    for (const [type, slug, expected] of cases) {
      expect(
        mentionRoute({ type, slug, label: slug } as Mention),
      ).toBe(expected);
    }
  });
});
