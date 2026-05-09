// Typed PocketBase access for the `campaigns` and `user_preferences`
// collections.
//
// Replaces the `api.get/post/put/del('/api/campaigns/...')` and
// `'/api/user-preferences'` calls that used to flow through
// `frontend/src/api/client.ts`'s adapter shim. Callers see clean
// `Campaign` / `UserPreferences` domain types and a small CRUD
// surface; the relation rename (`user → user_id`,
// `current_campaign → current_campaign_id`) and PB-meta strip lives
// once, here.

import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';
import type { Campaign, CampaignStatus, UserPreferences } from './types';

interface CampaignRow extends RecordModel {
  user: string;
  slug: string;
  name: string;
  description?: string;
  target_role_level?: string;
  target_companies?: string[];
  start_date?: string;
  end_date?: string;
  status?: CampaignStatus;
  color?: string;
  is_default?: boolean;
}

interface UserPreferencesRow extends RecordModel {
  user: string;
  theme?: string;
  accent?: string;
  type_variant?: string;
  density?: string;
  nav_style?: string;
  card_treatment?: string;
  sans_font?: string;
  radius?: string;
  shadow?: string;
  card_accent?: string;
  app_background?: string;
  glass_transparency?: number | null;
  glass_frost?: number | null;
  glass_shadow?: number | null;
  current_campaign?: string;
}

const campaignsCol = () => pb.collection<CampaignRow>('campaigns');
const prefsCol = () => pb.collection<UserPreferencesRow>('user_preferences');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function isNotFound(err: unknown): boolean {
  return (err as { status?: number } | null)?.status === 404;
}

// --- Campaign --------------------------------------------------------

function adaptCampaign(r: CampaignRow): Campaign {
  return {
    id: r.id,
    slug: r.slug,
    name: r.name,
    description: r.description ?? '',
    target_role_level: r.target_role_level ?? '',
    target_companies: r.target_companies ?? [],
    start_date: r.start_date ?? '',
    end_date: r.end_date ?? '',
    status: r.status ?? 'active',
    color: r.color ?? 'accent',
    is_default: r.is_default ?? false,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function campaignPayload(input: Partial<Campaign>, uid: string) {
  return {
    user: uid,
    name: input.name ?? '',
    slug: input.slug ?? '',
    description: input.description ?? '',
    target_role_level: input.target_role_level ?? '',
    target_companies: input.target_companies ?? [],
    start_date: input.start_date ?? '',
    end_date: input.end_date ?? '',
    status: input.status ?? 'active',
    color: input.color ?? 'accent',
    is_default: input.is_default ?? false,
  };
}

export async function listCampaigns(): Promise<Campaign[]> {
  const items = await campaignsCol().getFullList({
    filter: `user = "${userId()}"`,
    sort: '-created',
  });
  return items.map(adaptCampaign);
}

export async function createCampaign(input: Partial<Campaign>): Promise<Campaign> {
  return adaptCampaign(await campaignsCol().create(campaignPayload(input, userId())));
}

export async function updateCampaign(
  id: string,
  input: Partial<Campaign>,
): Promise<Campaign> {
  return adaptCampaign(
    await campaignsCol().update(id, campaignPayload(input, userId())),
  );
}

export async function deleteCampaign(id: string): Promise<void> {
  await campaignsCol().delete(id);
}

// --- UserPreferences -------------------------------------------------

function adaptPrefs(r: UserPreferencesRow): UserPreferences {
  return {
    id: r.id,
    theme: r.theme,
    accent: r.accent,
    type_variant: r.type_variant,
    density: r.density,
    nav_style: r.nav_style,
    card_treatment: r.card_treatment,
    current_campaign_id: r.current_campaign,
  };
}

function prefsPayload(input: Partial<UserPreferences>, uid: string) {
  // PocketBase relation fields reject `""` for an unset relation — use
  // `null` explicitly so the user_preferences row can clear its
  // current_campaign pointer when asked.
  const current = input.current_campaign_id;
  return {
    user: uid,
    theme: input.theme ?? '',
    accent: input.accent ?? '',
    type_variant: input.type_variant ?? '',
    density: input.density ?? '',
    nav_style: input.nav_style ?? '',
    card_treatment: input.card_treatment ?? '',
    current_campaign: current ? current : null,
  };
}

// Returns null when no preferences row exists yet — callers
// distinguish "not set" from a real error.
export async function getUserPreferences(): Promise<UserPreferences | null> {
  try {
    const row = await prefsCol().getFirstListItem(`user = "${userId()}"`);
    return adaptPrefs(row);
  } catch (err) {
    if (isNotFound(err)) return null;
    throw err;
  }
}

// Upsert — exactly one preferences row per user. Find-then-update-or-
// create against the unique index on `user`.
export async function upsertUserPreferences(
  input: Partial<UserPreferences>,
): Promise<UserPreferences> {
  const uid = userId();
  try {
    const existing = await prefsCol().getFirstListItem(`user = "${uid}"`);
    return adaptPrefs(await prefsCol().update(existing.id, prefsPayload(input, uid)));
  } catch (err) {
    if (!isNotFound(err)) throw err;
  }
  return adaptPrefs(await prefsCol().create(prefsPayload(input, uid)));
}
