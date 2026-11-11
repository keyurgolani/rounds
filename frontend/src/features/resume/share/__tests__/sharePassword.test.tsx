// The share page's password field and its 429 text (ROUNDS-00B-L04): a
// link that needs a password opens with it, sent only in the resolve's
// body; any other answer shows fixed text, never the server's; a throttled
// resolve says only how long to wait, in whole minutes; and with no token
// in the address there's no field at all.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../../../lib/pocketbase', () => ({
  pb: { authStore: { token: 'account-token-placeholder', isValid: true, record: null } },
}));

import SharedArtifact from '../../../../pages/SharedArtifact';
import { SHARED_FRAME_TITLE } from '../SharedArtifactFrame';
import { SHARE_NOT_FOUND_HEADING, SHARE_THROTTLED_HEADING, throttledText, throttledWait } from '../ShareNotFound';
import { SHARE_PASSWORD_HINT, SHARE_PASSWORD_RETRY } from '../SharePasswordForm';

const TOKEN = 'sd1_AbCdEfGhIjKlMnOpQrStUv';
const PASSWORD = 'correct horse battery';
const MARKUP = '<!DOCTYPE html><html><body><p>Ada</p></body></html>';
const fetchMock = vi.fn();

function answer(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

const NOT_FOUND = () => answer(404, { detail: 'Not found.' });

function open(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/r" element={<SharedArtifact />} />
      </Routes>
    </MemoryRouter>,
  );
}

function bodies(): unknown[] {
  return fetchMock.mock.calls.map(([, init]) => JSON.parse((init as RequestInit).body as string));
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('the password field', () => {
  it('opens a link that needs a password, with the password only in the body', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(NOT_FOUND()).mockResolvedValueOnce(answer(200, { projection_version: 1, markup: MARKUP }));
    open(`/r#${TOKEN}`);
    expect(await screen.findByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeInTheDocument();
    expect(screen.getByText(SHARE_PASSWORD_HINT)).toBeInTheDocument();
    const field = screen.getByLabelText('Password') as HTMLInputElement;
    expect(field.type).toBe('password');
    await user.type(field, PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(screen.getByTitle(SHARED_FRAME_TITLE)).toBeInTheDocument());
    expect(bodies()).toEqual([{ token: TOKEN }, { token: TOKEN, password: PASSWORD }]);
    for (const [url, init] of fetchMock.mock.calls as [string, RequestInit][]) {
      expect(url).toBe('/api/share/resolve');
      expect(new Headers(init.headers).get('Authorization')).toBeNull();
    }
  });

  it.each([
    ['a not-found', () => NOT_FOUND()],
    ['server text', () => answer(500, { detail: 'PocketBase secret detail', code: 'internal' })],
  ])('answers %s with fixed text and keeps the field', async (_name, make) => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(NOT_FOUND()).mockResolvedValueOnce(make());
    open(`/r#${TOKEN}`);
    await user.type(await screen.findByLabelText('Password'), 'a wrong password');
    await user.click(screen.getByRole('button', { name: 'Open' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(SHARE_PASSWORD_RETRY);
    expect(document.body.textContent).not.toContain('PocketBase');
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('says how long to wait when a password try is throttled', async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce(NOT_FOUND())
      .mockResolvedValueOnce(answer(429, { detail: 'Too many attempts.' }, { 'Retry-After': '30' }));
    open(`/r#${TOKEN}`);
    await user.type(await screen.findByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Open' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts. Wait 1 minute, then try again.');
  });

  it('has no field without a token', async () => {
    open('/r');
    expect(await screen.findByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeInTheDocument();
    expect(screen.queryByLabelText('Password')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('a throttled resolve', () => {
  it.each([
    ['120', 'Wait 2 minutes, then try again.'],
    ['61', 'Wait 2 minutes, then try again.'],
    [null, 'Wait 1 minute, then try again.'],
  ])('with Retry-After %s says only how long to wait', async (wait, text) => {
    fetchMock.mockResolvedValue(
      answer(429, { detail: 'Server text that is never shown' }, wait === null ? {} : { 'Retry-After': wait }),
    );
    open(`/r#${TOKEN}`);
    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(SHARE_THROTTLED_HEADING);
    await waitFor(() => expect(heading).toHaveFocus());
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('Server text');
    expect(screen.queryByLabelText('Password')).toBeNull();
  });

  it('reads "minute" for one and "minutes" for more', () => {
    expect(throttledWait(1)).toBe('Wait 1 minute, then try again.');
    expect(throttledWait(15)).toBe('Wait 15 minutes, then try again.');
    expect(throttledText(1)).toBe('Too many attempts. Wait 1 minute, then try again.');
  });
});
