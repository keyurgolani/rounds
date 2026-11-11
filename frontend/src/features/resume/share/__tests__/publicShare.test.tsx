// Resume links in a shared resume (ROUNDS-00B-L03 stage 1): only http,
// https, mailto, and tel links render as links. The share page itself is
// sharedArtifact.test.tsx, and an older link's address shareRoute.test.tsx.

import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Hyperlink, safeHref } from '../../templates/parts';

describe('resume links', () => {
  it.each([
    'javascript:alert(1)',
    ' JavaScript:alert(1)',
    'java\tscript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:x',
    'file:///etc/passwd',
    '/r/other',
    '//evil.example/x',
    'example.com',
    '',
    undefined,
  ])('renders %j as plain text', (href) => {
    expect(safeHref(href as string | undefined)).toBeNull();
    const { container } = render(<Hyperlink href={href as string | undefined}>label</Hyperlink>);
    expect(container.querySelector('a')).toBeNull();
    expect(container).toHaveTextContent('label');
  });

  it.each([
    ['https://example.test/me', 'https://example.test/me'],
    ['http://example.test', 'http://example.test/'],
    ['mailto:ada@example.test', 'mailto:ada@example.test'],
    ['tel:+15550100', 'tel:+15550100'],
  ])('links %s', (href, want) => {
    const { container } = render(<Hyperlink href={href}>label</Hyperlink>);
    expect(container.querySelector('a')?.getAttribute('href')).toBe(want);
  });
});
