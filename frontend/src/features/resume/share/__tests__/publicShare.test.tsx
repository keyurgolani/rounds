// Public share page and owner dialog (ROUNDS-00B-L03 stage 1): one fixed
// not-found page that shows no server text, a fixed toolbar label, no view
// counts, and resume links limited to http, https, mailto, and tel.

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../client')>();
  return { ...actual, fetchPublicResume: vi.fn(), listShareLinks: vi.fn() };
});
vi.mock('../../ZoomablePage', () => ({
  default: (props: { toolbarLabel?: string; data: unknown }) => (
    <div data-testid="page" data-label={props.toolbarLabel} data-json={JSON.stringify(props.data)} />
  ),
}));

import { fetchPublicResume, listShareLinks } from '../client';
import ShareDialog from '../ShareDialog';
import PublicResume, {
  SHARE_NOT_FOUND_HEADING,
  SHARE_NOT_FOUND_MESSAGE,
  SHARE_TOOLBAR_LABEL,
} from '../../../../pages/PublicResume';
import { Hyperlink, safeHref } from '../../templates/parts';
import { RunnerError } from '../../../../lib/runnerFetch';

const fetchMock = fetchPublicResume as unknown as ReturnType<typeof vi.fn>;
const listMock = listShareLinks as unknown as ReturnType<typeof vi.fn>;

function openShare(token = 'AbCdEfGhIjKlMnOpQrStUv') {
  return render(
    <MemoryRouter initialEntries={[`/r/${token}`]}>
      <Routes>
        <Route path="/r/:token" element={<PublicResume />} />
      </Routes>
    </MemoryRouter>,
  );
}

const DATA = {
  personalInfo: { fullName: 'Ada' },
  experience: [],
  education: [],
  skills: [],
  projects: [],
  publications: [],
  profiles: [],
};

describe('the public share page', () => {
  beforeEach(() => fetchMock.mockReset());

  it.each([
    ['a not-found', new RunnerError({ message: 'Share 404: Not found.', status: 404, detail: 'Not found.' })],
    ['server text', new RunnerError({ message: 'Share 500: PocketBase error: secret detail', status: 500 })],
    ['a network failure', new TypeError('Failed to fetch')],
  ])('shows the one fixed not-found page for %s', async (_name, err) => {
    fetchMock.mockRejectedValue(err);
    openShare();
    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(SHARE_NOT_FOUND_HEADING);
    expect(screen.getByText(SHARE_NOT_FOUND_MESSAGE)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/PocketBase|secret|404|500|fetch/i);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('puts focus on the not-found heading', async () => {
    fetchMock.mockRejectedValue(new Error('x'));
    openShare();
    const heading = await screen.findByRole('heading', { level: 1 });
    await waitFor(() => expect(heading).toHaveFocus());
  });

  it('uses a fixed toolbar label whatever the response carries', async () => {
    fetchMock.mockResolvedValue({
      data: DATA,
      template_id: 'modern',
      design: {},
      name: 'Owner private name',
      kind: 'variant',
    });
    openShare();
    const page = await screen.findByTestId('page');
    expect(page.dataset.label).toBe(SHARE_TOOLBAR_LABEL);
    expect(document.body.innerHTML).not.toContain('Owner private name');
    expect(document.body.innerHTML).not.toContain('variant');
  });
});

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

describe('the share dialog', () => {
  it('lists links without view counts', async () => {
    listMock.mockResolvedValue([
      { id: 'l1', token: 'AbCdEfGhIjKlMnOpQrStUv', resume_id: 'r1', variant_id: null, created: '' },
    ]);
    render(<ShareDialog open onClose={() => {}} resumeId="r1" />);
    await screen.findByText(/\/r\/AbCdEfGhIjKlMnOpQrStUv$/);
    expect(document.body.textContent).not.toMatch(/view count|views/i);
    expect(screen.queryByText('0')).toBeNull();
  });
});
