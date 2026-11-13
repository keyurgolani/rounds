// The campaign bootstrap: every signed-in account gets a default campaign
// when it has none, and a tab never keeps working in a campaign that's
// gone. Two first loads at once can race on the default's unique slug,
// and on the shared demo account another visitor's sign-out clears the
// campaigns an open tab is using (ROUNDS-00B-L07).

import { act, render, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Campaign } from '../types';

const api = vi.hoisted(() => ({
  listCampaigns: vi.fn(),
  createCampaign: vi.fn(),
  getUserPreferences: vi.fn(),
  updateCampaign: vi.fn(),
  upsertUserPreferences: vi.fn(),
}));

vi.mock('../api', () => api);
// One user object for the whole session, as AuthProvider's state holds it.
const session = vi.hoisted(() => ({ user: { id: 'demo00000000001' }, ready: true }));
vi.mock('../../auth/AuthProvider', () => ({
  useAuth: () => session,
}));
vi.mock('../../hooks/usePracticeStatus', () => ({
  hydrateCampaignProgress: vi.fn(async () => undefined),
  setActiveCampaignForStatus: vi.fn(),
}));
vi.mock('../../hooks/progressApi', () => ({ deleteUserProgress: vi.fn(), listUserProgress: vi.fn(async () => []) }));
vi.mock('../../lib/codeDraftsApi', () => ({ deleteCodeDraft: vi.fn(), listCodeDrafts: vi.fn(async () => []) }));

import { CampaignProvider, useCampaign } from '../CampaignContext';

function campaign(id: string, extra: Partial<Campaign> = {}): Campaign {
  return { id, name: id, slug: id, status: 'active', is_default: false, ...extra } as Campaign;
}

const seen = { currentId: null as string | null, ids: [] as string[], ready: false };

function Probe() {
  const ctx = useCampaign();
  seen.currentId = ctx.currentId;
  seen.ids = ctx.campaigns.map((c) => c.id);
  seen.ready = ctx.ready;
  return null;
}

function renderProvider() {
  return render(
    <CampaignProvider>
      <Probe />
    </CampaignProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  Object.values(api).forEach((fn) => fn.mockReset());
  api.getUserPreferences.mockResolvedValue(null);
  api.upsertUserPreferences.mockResolvedValue(undefined);
  seen.currentId = null;
  seen.ids = [];
  seen.ready = false;
});

describe('the campaign bootstrap', () => {
  it('lists again after a create conflict and takes the default another first load made', async () => {
    const other = campaign('camp00000000002', { slug: 'default', is_default: true });
    api.listCampaigns.mockResolvedValueOnce([]).mockResolvedValueOnce([other]);
    api.createCampaign.mockRejectedValueOnce(Object.assign(new Error('Failed to create record.'), { status: 400 }));
    renderProvider();
    await waitFor(() => expect(seen.currentId).toBe(other.id));
    expect(api.createCampaign).toHaveBeenCalledTimes(1);
    expect(seen.ids).toEqual([other.id]);
    expect(seen.ready).toBe(true);
  });

  it('runs again when the current campaign is gone, once the tab is back in view', async () => {
    const first = campaign('camp00000000001', { slug: 'default', is_default: true });
    const next = campaign('camp00000000009', { slug: 'default', is_default: true });
    api.listCampaigns.mockResolvedValueOnce([first]);
    renderProvider();
    await waitFor(() => expect(seen.currentId).toBe(first.id));
    // Another visitor's sign-out cleared the shared account's campaigns.
    api.listCampaigns.mockResolvedValue([]);
    api.createCampaign.mockResolvedValueOnce(next);
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await waitFor(() => expect(seen.currentId).toBe(next.id));
    expect(seen.ids).toEqual([next.id]);
    expect(window.localStorage.getItem('rounds.currentCampaign.v1')).toBe(next.id);
  });

  it('moves to the default when the current campaign is gone and others remain', async () => {
    const fallback = campaign('camp00000000001', { is_default: true });
    const chosen = campaign('camp00000000002');
    window.localStorage.setItem('rounds.currentCampaign.v1', chosen.id);
    api.listCampaigns.mockResolvedValueOnce([fallback, chosen]);
    renderProvider();
    await waitFor(() => expect(seen.currentId).toBe(chosen.id));
    api.listCampaigns.mockResolvedValue([fallback]);
    await act(async () => {
      window.dispatchEvent(new Event('focus'));
    });
    await waitFor(() => expect(seen.currentId).toBe(fallback.id));
    expect(api.createCampaign).not.toHaveBeenCalled();
  });

  it('keeps the selection while its campaign is still there', async () => {
    const one = campaign('camp00000000001', { is_default: true });
    const two = campaign('camp00000000002');
    window.localStorage.setItem('rounds.currentCampaign.v1', two.id);
    api.listCampaigns.mockResolvedValue([one, two]);
    renderProvider();
    await waitFor(() => expect(seen.currentId).toBe(two.id));
    await act(async () => {
      window.dispatchEvent(new Event('focus'));
    });
    expect(seen.currentId).toBe(two.id);
    expect(api.createCampaign).not.toHaveBeenCalled();
  });

  it('runs again on the next action in a tab that stays in view, at most every 15 seconds', async () => {
    const first = campaign('camp00000000001', { slug: 'default', is_default: true });
    const next = campaign('camp00000000009', { slug: 'default', is_default: true });
    let clock = 1_000_000;
    const now = vi.spyOn(Date, 'now').mockImplementation(() => clock);
    try {
      api.listCampaigns.mockResolvedValueOnce([first]);
      renderProvider();
      await waitFor(() => expect(seen.currentId).toBe(first.id));
      // Another visitor's sign-out cleared the shared account's campaigns.
      api.listCampaigns.mockResolvedValue([]);
      api.createCampaign.mockResolvedValueOnce(next);
      // Too soon after the bootstrap: the click checks nothing.
      await act(async () => {
        window.dispatchEvent(new Event('pointerdown'));
      });
      expect(api.listCampaigns).toHaveBeenCalledTimes(1);
      clock += 15_000;
      await act(async () => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
      });
      await waitFor(() => expect(seen.currentId).toBe(next.id));
      expect(seen.ids).toEqual([next.id]);
    } finally {
      now.mockRestore();
    }
  });
});
