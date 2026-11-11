// The Share Capability page and its frame (ROUNDS-00B-L03 stage 2): the
// frame's attributes are exact and its srcdoc is the markup as answered;
// the markup's nodes never enter this page; the toolbar works from the
// keyboard; every failure is the one not-found, with focus on its heading
// and no server text; no fragment means no request; and the token goes
// only in the POST body, with no account token.
//
// jsdom has no sandbox, so these show that the markup stays out of this
// page. What the sandbox stops in a browser is #12's and #173's to show.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../../lib/pocketbase', () => ({
  pb: { authStore: { token: 'account-token-placeholder', isValid: true, record: null } },
}));

import SharedArtifact from '../../../../pages/SharedArtifact';
import SharedArtifactFrame, {
  SHARED_FRAME_SANDBOX,
  SHARED_FRAME_TITLE,
  SHARED_FRAME_WIDTH_PX,
} from '../SharedArtifactFrame';
import { SHARE_TOOLBAR_LABEL } from '../ReadOnlyBadge';
import { SHARE_NOT_FOUND_HEADING, SHARE_NOT_FOUND_MESSAGE } from '../ShareNotFound';

const TOKEN = 'sd1_AbCdEfGhIjKlMnOpQrStUv';
const MARKUP =
  '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8" />\n  <title>Resume</title>\n' +
  '  <style>p { color: #111; }</style>\n</head>\n<body>\n<article data-resume-page="true">' +
  '<p style="margin:0">Ada Lovelace &amp; co</p><a href="https://example.test/ada" target="_blank" rel="noreferrer">site</a>' +
  '</article>\n</body>\n</html>';
const HOSTILE =
  '<!DOCTYPE html><html><body><p id="hostile-text">Hostile</p>' +
  '<script>window.__sharedFrameRan = 1;</script>' +
  '<a id="hostile-link" href="javascript:window.__sharedFrameRan=2">x</a>' +
  '<img id="hostile-img" src="x" onerror="window.__sharedFrameRan=3"></body></html>';

const fetchMock = vi.fn();

function answer(status: number, body: unknown) {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/r" element={<SharedArtifact />} />
      </Routes>
    </MemoryRouter>,
  );
}

function frame(): HTMLIFrameElement {
  return screen.getByTitle(SHARED_FRAME_TITLE) as HTMLIFrameElement;
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  delete (window as unknown as Record<string, unknown>).__sharedFrameRan;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('the shared artifact frame', () => {
  it('has exactly the sandbox, title, and referrer policy, and the markup verbatim as srcdoc', () => {
    render(<SharedArtifactFrame markup={MARKUP} />);
    const el = frame();
    expect(el.getAttributeNames().sort()).toEqual(['referrerpolicy', 'sandbox', 'srcdoc', 'style', 'title']);
    expect(el.getAttribute('sandbox')).toBe('allow-popups allow-popups-to-escape-sandbox');
    expect(SHARED_FRAME_SANDBOX).not.toMatch(/allow-scripts|allow-same-origin|allow-top-navigation|allow-forms/);
    expect(el.getAttribute('title')).toBe('Shared resume');
    expect(el.getAttribute('referrerpolicy')).toBe('no-referrer');
    expect(el.getAttribute('srcdoc')).toBe(MARKUP);
    expect(el.style.width).toBe(`${SHARED_FRAME_WIDTH_PX}px`);
  });

  it('keeps the markup out of this page', async () => {
    render(<SharedArtifactFrame markup={HOSTILE} />);
    expect(frame().getAttribute('srcdoc')).toBe(HOSTILE);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(document.getElementById('hostile-text')).toBeNull();
    expect(document.getElementById('hostile-link')).toBeNull();
    expect(document.getElementById('hostile-img')).toBeNull();
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
    expect([...document.querySelectorAll('script')].some((s) => s.textContent?.includes('__sharedFrameRan'))).toBe(false);
    expect((window as unknown as Record<string, unknown>).__sharedFrameRan).toBeUndefined();
    expect(document.body.textContent).not.toContain('Hostile');
  });

  it('shows the fixed label and the read-only badge', () => {
    render(<SharedArtifactFrame markup={MARKUP} />);
    expect(screen.getByText(SHARE_TOOLBAR_LABEL)).toBeInTheDocument();
    expect(screen.getByText('Read-only')).toBeInTheDocument();
  });

  it('zooms from the toolbar by keyboard and from the shortcuts', async () => {
    const user = userEvent.setup();
    render(<SharedArtifactFrame markup={MARKUP} />);
    const percent = () => screen.getByTitle(/Reset to 100%/);
    expect(percent()).toHaveTextContent('100%');

    screen.getByRole('button', { name: 'Zoom in' }).focus();
    await user.keyboard('{Enter}');
    expect(percent()).toHaveTextContent('110%');
    await user.tab({ shift: true });
    expect(percent()).toHaveFocus();
    await user.keyboard(' ');
    expect(percent()).toHaveTextContent('100%');
    await user.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Zoom out' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(percent()).toHaveTextContent('90%');

    await user.keyboard('+');
    await user.keyboard('=');
    expect(percent()).toHaveTextContent('110%');
    await user.keyboard('0');
    expect(percent()).toHaveTextContent('100%');
    await user.keyboard('-');
    expect(percent()).toHaveTextContent('90%');
    expect(screen.getByRole('button', { name: /Fit/ })).toBeInTheDocument();
  });

  it('opens fitted to the width, keeps a picked zoom, and fits again on Fit', async () => {
    const user = userEvent.setup();
    const width = vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(390);
    try {
      render(<SharedArtifactFrame markup={MARKUP} />);
      const percent = () => screen.getByTitle(/Reset to 100%/);
      // (390 - 2 * 16) / 826
      expect(percent()).toHaveTextContent('43%');
      await user.keyboard('+');
      expect(percent()).toHaveTextContent('53%');
      await user.click(screen.getByRole('button', { name: /Fit/ }));
      expect(percent()).toHaveTextContent('43%');
      expect(frame().style.transform).toBe(`scale(${(390 - 32) / SHARED_FRAME_WIDTH_PX})`);
    } finally {
      width.mockRestore();
    }
  });

  it('scales the frame with the zoom and leaves the browser zoom keys alone', async () => {
    const user = userEvent.setup();
    render(<SharedArtifactFrame markup={MARKUP} />);
    await user.keyboard('+');
    expect(frame().style.transform).toBe('scale(1.1)');
    await user.keyboard('{Meta>}={/Meta}');
    expect(frame().style.transform).toBe('scale(1.1)');
  });
});

describe('the shared artifact page', () => {
  it('posts the token in the body only, with no account token, and shows the answer', async () => {
    fetchMock.mockResolvedValue(answer(200, { projection_version: 1, markup: MARKUP }));
    open(`/r#${TOKEN}`);
    await waitFor(() => expect(frame().getAttribute('srcdoc')).toBe(MARKUP));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/share/resolve');
    expect(url).not.toContain(TOKEN);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ token: TOKEN });
    const headers = new Headers(init.headers);
    expect(headers.get('Authorization')).toBeNull();
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it.each(['/r', '/r#'])('makes no request without a token (%s)', async (path) => {
    open(path);
    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(SHARE_NOT_FOUND_HEADING);
    await waitFor(() => expect(heading).toHaveFocus());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    ['a not-found', () => answer(404, { detail: 'Not found.' })],
    ['server text', () => answer(500, { detail: 'PocketBase secret detail', code: 'internal' })],
    ['a field too many', () => answer(200, { projection_version: 1, markup: MARKUP, owner: 'Ada' })],
    ['another projection version', () => answer(200, { projection_version: 2, markup: MARKUP })],
    ['empty markup', () => answer(200, { projection_version: 1, markup: '' })],
    ['markup that is not text', () => answer(200, { projection_version: 1, markup: { html: MARKUP } })],
    ['not JSON', () => answer(200, '<html>not json</html>')],
  ])('shows the one fixed not-found page for %s', async (_name, make) => {
    fetchMock.mockResolvedValue(make());
    open(`/r#${TOKEN}`);
    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(SHARE_NOT_FOUND_HEADING);
    expect(screen.getByText(SHARE_NOT_FOUND_MESSAGE)).toBeInTheDocument();
    await waitFor(() => expect(heading).toHaveFocus());
    expect(screen.queryByTitle(SHARED_FRAME_TITLE)).toBeNull();
    expect(document.body.textContent).not.toMatch(/PocketBase|secret|Not found\.|404|500|Ada/);
  });

  it('shows the not-found page when the request fails', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    open(`/r#${TOKEN}`);
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(SHARE_NOT_FOUND_HEADING);
    expect(document.body.textContent).not.toMatch(/fetch/i);
  });
});
