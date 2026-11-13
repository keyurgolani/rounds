// The campaign page while its tab checks the campaign (ROUNDS-00B-L07): a
// check on a click, a key press, or focus leaves an edit in progress alone
// while the campaign is still there, and moves the page on to a new
// default only when the campaign is gone.

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Campaign } from '../../campaign/types';

const api = vi.hoisted(() => ({
  listCampaigns: vi.fn(),
  createCampaign: vi.fn(),
  getUserPreferences: vi.fn(),
  updateCampaign: vi.fn(),
  upsertUserPreferences: vi.fn(),
}));

vi.mock('../../campaign/api', () => api);
// One user object for the whole session, as AuthProvider's state holds it.
const session = vi.hoisted(() => ({ user: { id: 'user00000000001' }, ready: true }));
vi.mock('../../auth/AuthProvider', () => ({
  useAuth: () => session,
}));
vi.mock('../../hooks/usePracticeStatus', () => ({
  hydrateCampaignProgress: vi.fn(async () => undefined),
  setActiveCampaignForStatus: vi.fn(),
}));
vi.mock('../../hooks/progressApi', () => ({ deleteUserProgress: vi.fn(), listUserProgress: vi.fn(async () => []) }));
vi.mock('../../lib/codeDraftsApi', () => ({ deleteCodeDraft: vi.fn(), listCodeDrafts: vi.fn(async () => []) }));
vi.mock('../../components/shell/AppHeader', () => ({ default: () => null }));

import { CampaignProvider } from '../../campaign/CampaignContext';
import CampaignDetail from '../CampaignDetail';

function campaign(id: string, extra: Partial<Campaign> = {}): Campaign {
  return {
    id,
    slug: 'default',
    name: 'Default',
    description: '',
    target_role_level: '',
    target_companies: [],
    start_date: '',
    end_date: '',
    status: 'active',
    color: 'accent',
    is_default: true,
    ...extra,
  };
}

const SAVED = campaign('camp00000000001');
const START = new Date('2026-11-12T12:00:00.000Z').getTime();
// How often the tab's click and key checks may run (CampaignContext).
const INTERVAL_MS = 15_000;

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/campaigns/default']}>
      <CampaignProvider>
        <Routes>
          <Route path="/campaigns/:slug" element={<CampaignDetail />} />
        </Routes>
      </CampaignProvider>
    </MemoryRouter>,
  );
}

// One check: wait for its list call, then let what it sets render.
async function checked(calls: number) {
  await waitFor(() => expect(api.listCampaigns).toHaveBeenCalledTimes(calls));
  await act(async () => {
    await Promise.resolve();
  });
}

beforeEach(() => {
  // Only the clock is fake, so the tab's 15 s throttle moves when the test
  // says; the mocks still resolve on their own.
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(START);
  window.localStorage.clear();
  Object.values(api).forEach((fn) => fn.mockReset());
  api.getUserPreferences.mockResolvedValue(null);
  api.upsertUserPreferences.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('the campaign page', () => {
  it('keeps an edit in progress through the tab checks while its campaign is still there', async () => {
    // Every list is a fresh copy of the same, unchanged campaign.
    api.listCampaigns.mockImplementation(async () => [{ ...SAVED }]);
    renderPage();
    const name = (await screen.findByLabelText('Name')) as HTMLInputElement;
    expect(name.value).toBe('Default');
    fireEvent.change(name, { target: { value: 'Default, renamed' } });

    // Two 15 s intervals, each with a key or click check and a focus check.
    let calls = 1;
    for (const [step, action] of [
      [1, () => fireEvent.keyDown(name, { key: 'a' })],
      [2, () => fireEvent.pointerDown(name)],
    ] as const) {
      vi.setSystemTime(START + step * INTERVAL_MS);
      action();
      await checked((calls += 1));
      expect(name.value).toBe('Default, renamed');
      act(() => {
        window.dispatchEvent(new Event('focus'));
      });
      await checked((calls += 1));
      expect(name.value).toBe('Default, renamed');
    }
    expect(api.createCampaign).not.toHaveBeenCalled();
  });

  it('moves on to a new default when its campaign was deleted elsewhere', async () => {
    const next = campaign('camp00000000009');
    api.listCampaigns.mockResolvedValueOnce([{ ...SAVED }]);
    renderPage();
    const name = (await screen.findByLabelText('Name')) as HTMLInputElement;
    fireEvent.change(name, { target: { value: 'Default, renamed' } });
    // Another visitor's sign-out cleared the shared account's campaigns.
    api.listCampaigns.mockResolvedValue([]);
    api.createCampaign.mockResolvedValueOnce(next);
    vi.setSystemTime(START + INTERVAL_MS);
    fireEvent.keyDown(name, { key: 'a' });
    await waitFor(() => expect(window.localStorage.getItem('rounds.currentCampaign.v1')).toBe(next.id));
    expect(api.createCampaign).toHaveBeenCalledTimes(1);
    // The page now shows the new default, since the old one is gone.
    await waitFor(() => expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Default'));
  });

  it('moves on on focus too, with no click or key press', async () => {
    const next = campaign('camp00000000009');
    api.listCampaigns.mockResolvedValueOnce([{ ...SAVED }]);
    renderPage();
    await screen.findByLabelText('Name');
    api.listCampaigns.mockResolvedValue([]);
    api.createCampaign.mockResolvedValueOnce(next);
    act(() => {
      window.dispatchEvent(new Event('focus'));
    });
    await waitFor(() => expect(window.localStorage.getItem('rounds.currentCampaign.v1')).toBe(next.id));
    expect(api.createCampaign).toHaveBeenCalledTimes(1);
  });
});
