// The demo account's notice (ROUNDS-00B-L07): while the demo account is
// signed in, every page in the signed-in shell opens with it, above the
// page itself. It says visitors share the account, that others can see
// what you add, and that any sign-out clears it. Other accounts never see
// it.

import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { User } from '../../auth/AuthProvider';

const auth = vi.hoisted(() => ({
  user: null as User | null,
  logout: vi.fn(async () => undefined),
}));

vi.mock('../../auth/AuthProvider', () => ({
  useAuth: () => auth,
  useIsDemo: () => auth.user?.isDemo === true,
  initials: (name: string) => name.slice(0, 2).toUpperCase(),
}));

import Layout from '../Layout';

const USER: User = {
  id: 'user00000000001',
  name: 'Rounds Demo',
  email: 'demo@example.test',
  provider: 'email',
  createdAt: '2026-11-01T00:00:00.000Z',
};

function renderShellAs(user: User) {
  auth.user = user;
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<h1>The page</h1>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('the signed-in shell', () => {
  it('opens every page with the demo notice while the demo account is signed in', () => {
    renderShellAs({ ...USER, isDemo: true });
    const notice = screen.getByRole('note', { name: 'Demo account' });
    expect(within(notice).getByText('Shared demo account.')).toBeTruthy();
    expect(notice.textContent).toContain("so don't enter real personal details");
    expect(notice.textContent).toContain('Any sign-out, the 30-minute idle one included, clears what everyone added.');
    // It comes before the page, in the main region.
    const main = screen.getByRole('main');
    const heading = within(main).getByRole('heading', { name: 'The page' });
    expect(main.contains(notice)).toBe(true);
    expect(notice.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows no demo notice to any other account', () => {
    renderShellAs({ ...USER, name: 'Ada', isDemo: false });
    expect(screen.queryByTestId('demo-notice')).toBeNull();
    expect(screen.queryByRole('note', { name: 'Demo account' })).toBeNull();
    expect(screen.getByRole('heading', { name: 'The page' })).toBeTruthy();
  });
});
