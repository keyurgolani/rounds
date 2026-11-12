// The demo account's profile is fixed (ROUNDS-00B-L07): PocketBase
// refuses a change to it, so the page shows it as text, with nothing to
// edit or save. Every other account still edits its profile here.

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { User } from '../../auth/AuthProvider';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';
import Profile from '../Profile';

const auth = vi.hoisted(() => ({
  user: null as User | null,
  updateProfile: vi.fn(async () => undefined),
  logout: vi.fn(async () => undefined),
}));

vi.mock('../../auth/AuthProvider', () => ({
  useAuth: () => auth,
  initials: (name: string) => name.slice(0, 2).toUpperCase(),
}));

vi.mock('../../hooks/useLoginStreak', () => ({
  useLoginStreak: () => ({
    current: 0,
    longest: 0,
    activeToday: false,
    last7: [],
    last30: [],
    totalDays: 0,
    firstLogin: null,
    recent: [],
    all: [],
  }),
}));

const BASE: User = {
  id: 'user00000000001',
  name: 'Rounds Demo',
  email: 'demo@example.test',
  provider: 'email',
  bio: 'Disposable hosted demo account. Changes reset on logout.',
  target: 'Explore Rounds',
  createdAt: '2026-11-01T00:00:00.000Z',
};

function renderAs(user: User) {
  auth.user = user;
  return render(
    <MemoryRouter>
      <CommandCenterProvider>
        <Profile />
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('the profile page', () => {
  it('shows the demo profile with nothing to edit or save', () => {
    const { container } = renderAs({ ...BASE, isDemo: true });
    expect(container.querySelector('form')).toBeNull();
    expect(container.querySelectorAll('input, textarea')).toHaveLength(0);
    expect(screen.queryByRole('button', { name: /save changes/i })).toBeNull();
    expect(screen.getByText("The demo profile can't be changed.")).toBeTruthy();
    const values = Array.from(container.querySelectorAll('dd')).map((dd) => dd.textContent);
    expect(values).toEqual(['Rounds Demo', 'Explore Rounds', 'Disposable hosted demo account. Changes reset on logout.']);
  });

  it('says a demo profile field is not set when it is empty', () => {
    const { container } = renderAs({ ...BASE, isDemo: true, target: '' });
    const values = Array.from(container.querySelectorAll('dd')).map((dd) => dd.textContent);
    expect(values[1]).toBe('Not set');
  });

  it('still lets any other account edit and save its profile', () => {
    const { container } = renderAs({ ...BASE, name: 'Ada', isDemo: false });
    expect(container.querySelector('form')).not.toBeNull();
    expect(screen.getByDisplayValue('Ada')).toBeTruthy();
    expect(screen.getByRole('button', { name: /save changes/i })).toBeTruthy();
    expect(screen.queryByText("The demo profile can't be changed.")).toBeNull();
  });
});
