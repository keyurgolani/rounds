// Only the lowercase share paths render the share pages, the ones nginx
// serves with the share headers (ROUNDS-00B-L03). /r#<token> is the share
// page. Any /r/<anything> is an older link's address, which opens one
// fixed page: no request, nothing read from the address, and the same
// markup for every value (ROUNDS-00B-L06).

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../client')>();
  return { ...actual, resolveSharedArtifact: vi.fn() };
});

import { resolveSharedArtifact } from '../client';
import App from '../../../../App';
import { AuthProvider } from '../../../../auth/AuthProvider';
import { ThemeProvider } from '../../../../theme/ThemeProvider';
import { SHARE_GONE_HEADING, SHARE_GONE_MESSAGE, SHARE_NOT_FOUND_HEADING, SHARE_NOT_FOUND_MESSAGE } from '../ShareNotFound';

const resolveMock = resolveSharedArtifact as unknown as ReturnType<typeof vi.fn>;
const CAPABILITY_TOKEN = 'sd1_AbCdEfGhIjKlMnOpQrStUv';
const OLDER = 'AbCdEfGhIjKlMnOpQrStUv';
let network: ReturnType<typeof vi.fn>;

function open(path: string) {
  return render(
    <AuthProvider>
      <ThemeProvider>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </AuthProvider>,
  );
}

// Give any route a moment to mount and ask for something.
const settle = () => new Promise((resolve) => setTimeout(resolve, 100));

beforeEach(() => {
  resolveMock.mockReset();
  resolveMock.mockRejectedValue(new Error('x'));
  network = vi.fn(async () => new Response('{}', { status: 404 }));
  vi.stubGlobal('fetch', network);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('an older link’s address', () => {
  it.each([
    `/r/${OLDER}`,
    '/r/x',
    `/r/${CAPABILITY_TOKEN}`,
    '/r/a/b/c',
    `/r/${OLDER}#${CAPABILITY_TOKEN}`,
    `/r/${OLDER}?ref=placeholder`,
    '/r/%E2%9C%93',
  ])('opens the one fixed page on %s, with no request', async (path) => {
    open(path);
    expect(await screen.findByRole('heading', { level: 1, name: SHARE_GONE_HEADING })).toBeInTheDocument();
    expect(screen.getByText(SHARE_GONE_MESSAGE)).toBeInTheDocument();
    await settle();
    expect(resolveMock).not.toHaveBeenCalled();
    expect(network).not.toHaveBeenCalled();
  });

  it('is the same page for every value, and shows nothing from the address', async () => {
    const first = open(`/r/${OLDER}`);
    await screen.findByRole('heading', { name: SHARE_GONE_HEADING });
    const markup = first.container.innerHTML;
    first.unmount();
    const second = open('/r/another0value0entirely');
    await screen.findByRole('heading', { name: SHARE_GONE_HEADING });
    expect(second.container.innerHTML).toBe(markup);
    expect(markup).not.toContain(OLDER);
    expect(screen.queryByText(SHARE_NOT_FOUND_HEADING)).toBeNull();
  });

  it('puts focus on its heading', async () => {
    open(`/r/${OLDER}`);
    const heading = await screen.findByRole('heading', { level: 1, name: SHARE_GONE_HEADING });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it.each([`/R/${OLDER}`, '/R/x'])('is not that page on %s', async (path) => {
    open(path);
    await settle();
    expect(screen.queryByRole('heading', { name: SHARE_GONE_HEADING })).toBeNull();
    expect(resolveMock).not.toHaveBeenCalled();
  });
});

describe('the share page', () => {
  it('renders on the lowercase path, with the token from the fragment, and keeps its not-found', async () => {
    open(`/r#${CAPABILITY_TOKEN}`);
    expect(await screen.findByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeInTheDocument();
    expect(screen.getByText(SHARE_NOT_FOUND_MESSAGE)).toBeInTheDocument();
    expect(resolveMock).toHaveBeenCalledTimes(1);
    expect(resolveMock).toHaveBeenCalledWith(CAPABILITY_TOKEN);
    expect(screen.queryByText(SHARE_GONE_HEADING)).toBeNull();
  });

  it.each([`/R#${CAPABILITY_TOKEN}`, '/R'])('does not render on %s', async (path) => {
    open(path);
    await settle();
    expect(screen.queryByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeNull();
    expect(resolveMock).not.toHaveBeenCalled();
  });
});
