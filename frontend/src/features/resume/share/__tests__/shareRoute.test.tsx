// Only the lowercase share path renders the share page, the one nginx
// serves with the share headers (ROUNDS-00B-L03).

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../client')>();
  return { ...actual, fetchPublicResume: vi.fn() };
});

import { fetchPublicResume } from '../client';
import App from '../../../../App';
import { AuthProvider } from '../../../../auth/AuthProvider';
import { ThemeProvider } from '../../../../theme/ThemeProvider';
import { SHARE_NOT_FOUND_HEADING } from '../../../../pages/PublicResume';

const fetchMock = fetchPublicResume as unknown as ReturnType<typeof vi.fn>;

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

describe('the share route', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockRejectedValue(new Error('x'));
  });

  it('renders the share page on the lowercase path', async () => {
    open('/r/AbCdEfGhIjKlMnOpQrStUv');
    expect(await screen.findByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each(['/R/AbCdEfGhIjKlMnOpQrStUv', '/R/x'])('does not render the share page on %s', async (path) => {
    open(path);
    // Give any route a moment to mount and fetch.
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(screen.queryByRole('heading', { name: SHARE_NOT_FOUND_HEADING })).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
