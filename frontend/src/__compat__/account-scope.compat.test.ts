// Account-scope compatibility for SPA writes (ROUNDS-00B-L01 stage 3).
//
// The tightened rules (pocketbase/pb_migrations/1700006000_account_scope_rules.js)
// accept a create only when its body names the caller as `user`, and an
// update only when its body leaves `user` out or names the caller again.
// Every SPA write path below runs its real code against a recording fake of
// the PocketBase client, and every recorded body is held to those two
// conditions. The coverage guard at the bottom scans the source, so a new
// write can't land without a case here.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { createElement, type ReactNode } from 'react';
import { act, fireEvent, render, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

type Row = Record<string, unknown> & { id: string };
type Recorded = { collection: string; op: 'create' | 'update'; id?: string; body: Record<string, unknown> };
type Expected = readonly [collection: string, op: Recorded['op'], user: 'caller' | 'omitted'];

const fake = vi.hoisted(() => {
  const recorded: Recorded[] = [];
  const state = { authId: '', existing: {} as Record<string, Row>, seq: 0 };
  const STAMP = '2026-10-20 00:00:00.000Z';

  // The SDK sends a plain body as JSON, so a key left `undefined` never
  // reaches the server. Record the body the rules will see.
  const onTheWire = (body: unknown): Record<string, unknown> =>
    JSON.parse(JSON.stringify(body ?? {}));
  const notFound = () =>
    Object.assign(new Error("The requested resource wasn't found."), { status: 404, data: {} });
  // A read only ever returns the caller's own row: the list and view rules
  // never hand back anyone else's.
  const read = (name: string): Row | null => {
    const row = state.existing[name];
    return row ? { collectionName: name, ...row, user: state.authId } : null;
  };
  const readOne = async (name: string): Promise<Row> => {
    const row = read(name);
    if (!row) throw notFound();
    return row;
  };
  const readAll = (name: string): Row[] => {
    const row = read(name);
    return row ? [row] : [];
  };

  const collection = (name: string) => ({
    async create(body: unknown) {
      const sent = onTheWire(body);
      recorded.push({ collection: name, op: 'create', body: sent });
      return { id: `${name}-${++state.seq}`, collectionName: name, created: STAMP, updated: STAMP, ...sent };
    },
    async update(id: string, body: unknown) {
      const sent = onTheWire(body);
      recorded.push({ collection: name, op: 'update', id, body: sent });
      return { ...(read(name) ?? { collectionName: name }), id, updated: STAMP, ...sent };
    },
    async delete() {
      return true;
    },
    getOne: () => readOne(name),
    getFirstListItem: () => readOne(name),
    async getList(page = 1, perPage = 30) {
      const items = readAll(name);
      return { page, perPage, totalItems: items.length, totalPages: items.length, items };
    },
    async getFullList() {
      return readAll(name);
    },
    async authRefresh() {
      return { token: 'test-token-placeholder', record: { id: state.authId, collectionName: 'users' } };
    },
  });

  const pb = {
    authStore: {
      get record() {
        return { id: state.authId, collectionName: 'users' };
      },
      get model() {
        return { id: state.authId, collectionName: 'users' };
      },
      token: 'test-token-placeholder',
      isValid: true,
      onChange: () => () => {},
      save: () => {},
      clear: () => {},
    },
    collection,
    autoCancellation: () => {},
    filter: (raw: string) => raw,
    files: { getURL: () => '' },
  };

  return { pb, recorded, state };
});

// Every module under test imports this one client, so one mock reaches all of them.
vi.mock('../lib/pocketbase', () => ({ pb: fake.pb, pocketbaseEnabled: true }));

// DataSection reads the caller's campaigns from context. The caller has none,
// so the import never collides with an existing slug. Only DataSection, of the
// modules this file drives, uses the context.
const campaignContext = vi.hoisted(() => ({
  value: { campaigns: [] as unknown[], currentId: null as string | null, refresh: async () => {} },
}));
vi.mock('../campaign/CampaignContext', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../campaign/CampaignContext')>()),
  useCampaign: () => campaignContext.value,
}));

import {
  createApplication,
  createOffer,
  createRound,
  deleteOffer,
  updateApplication,
  updateApplicationField,
  updateOffer,
  updateRound,
  type ApplicationInput,
  type InterviewRoundInput,
  type OfferInput,
} from '../applications/api';
import { AuthProvider } from '../auth/AuthProvider';
import { createCampaign, updateCampaign, upsertUserPreferences } from '../campaign/api';
import type { Campaign } from '../campaign/types';
import {
  batchCreateConnections,
  createConnection,
  getJunctionTable,
  validChildKinds,
} from '../experience/connectionApi';
import {
  createAnecdote,
  createBullet,
  createJob,
  createProject,
  updateAnecdote,
  updateBullet,
  updateJob,
  updateProject,
  type EntityKind,
} from '../experience/experienceApi';
import {
  createResume,
  createShareLink,
  createVariant,
  createVersion,
  updateResume,
  updateVariant,
  upsertAISettings,
} from '../features/resume/api';
import { emptyResumeData } from '../features/resume/types';
import { createUserProgress, updateUserProgress, type UserProgressInput } from '../hooks/progressApi';
import { useQuestionTimer } from '../hooks/useQuestionTimer';
import { upsertCodeDraft, type CodeDraftInput } from '../lib/codeDraftsApi';
import * as aiCoding from '../pages/ai-coding/aiCodingApi';
import * as takeHome from '../pages/take-home/takeHomeApi';
import DataSection from '../settings/DataSection';
import { ThemeProvider, upsertThemePreferences, useTheme, type Tweaks } from '../theme/ThemeProvider';
import { createTodo, updateTodo, type TodoInput } from '../todos/api';

interface Branch {
  /** What the branch does, for the test title. */
  when: string;
  /** Rows the caller already has, by collection. A read of any other collection 404s. */
  existing?: Record<string, Row>;
  run: () => Promise<unknown>;
  /** Every write the branch makes, in order. */
  writes: Expected[];
}

let signIns = 0;

beforeEach(() => {
  // A new caller for every test: a helper that held on to an earlier
  // caller's id would stamp the wrong account.
  fake.state.authId = `caller-${++signIns}`;
  fake.state.existing = {};
  fake.state.seq = 0;
  fake.recorded.length = 0;
});

/** Whom a recorded write names in `user`. */
function userField({ body }: Recorded): string {
  if (!('user' in body)) return 'omitted';
  return body.user === fake.state.authId ? 'caller' : `not the caller (${JSON.stringify(body.user)})`;
}

/** The body conditions the new create and update rules add. */
function rulesAccept(write: Recorded): boolean {
  const user = userField(write);
  return user === 'caller' || (write.op === 'update' && user === 'omitted');
}

/** Runs `fn` inside act, then lets the async writes it started land. */
async function settle(fn: () => void = () => {}) {
  await act(async () => {
    fn();
    await new Promise((done) => setTimeout(done, 0));
  });
}

// ---- Inputs ---------------------------------------------------------

const OTHER_ACCOUNT = 'someone-else';

/** The input as another account's backup would carry it, owner fields included. */
function fromBackup<T extends object>(input: T): T {
  return { ...input, user: OTHER_ACCOUNT, user_id: OTHER_ACCOUNT };
}

const CAMPAIGN: Partial<Campaign> = { name: 'Fall search', slug: 'fall-search' };
const APPLICATION: ApplicationInput = { company: 'Acme', role: 'Staff Engineer', campaign_id: 'campaigns-1' };
const ROUND: InterviewRoundInput = { round_type: 'Onsite', date: '2026-10-01', interviewer: 'Sam' };
const OFFER: OfferInput = { base_salary: 200000, equity_type: 'RSU' };
const TODO: TodoInput = { body: 'Send the thank-you note', campaign_id: 'campaigns-1' };
const PROGRESS: UserProgressInput = {
  campaign_id: 'campaigns-1',
  question_type: 'coding',
  question_slug: 'two-sum',
  status: 'in-progress',
};
const CODE_DRAFT: CodeDraftInput = { campaign_id: 'campaigns-1', question: 'two-sum', language: 'python', code: 'pass' };
const AI_CODING_DRAFT = { roundId: 'rounds-1', campaignId: 'campaigns-1', filePath: 'main.py', contents: 'print(1)' };
const AI_CODING_ATTEMPT = {
  roundId: 'rounds-1',
  campaignId: 'campaigns-1',
  currentCheckpoint: 1,
  chats: [{ checkpoint: 1, role: 'user', content: 'Where do I start?', ts: 1 }],
};
const TAKE_HOME_ATTEMPT = { assignmentId: 'assignments-1', campaignId: 'campaigns-1', chats: [] };
const TAKE_HOME_DRAFT = { assignmentId: 'assignments-1', campaignId: 'campaigns-1', filePath: 'kv.py', contents: 'class KV: ...' };
const TWEAKS: Tweaks = {
  theme: 'dark',
  accent: 'forest',
  typeVariant: 'fraunces',
  sansFont: 'inter',
  density: 'comfortable',
  navStyle: 'sidebar',
  cardTreatment: 'layered',
  radius: 'soft',
  shadow: 'soft',
  cardAccent: 'neutral',
  appBackground: 'grainy',
  glassTransparency: 0,
  glassFrost: 50,
  glassShadow: 50,
};

// Rows the caller already has, for the update branches.
const ROWS = {
  application: { id: 'applications-1', company: 'Acme', role: 'Staff Engineer', status: 'Interviewing', campaign: 'campaigns-1' },
  round: { id: 'interview_rounds-1', application: 'applications-1', round_type: 'Onsite', date: '2026-10-01' },
  activeOffer: { id: 'offers-1', application: 'applications-1', status: 'pending', trail: [] },
  revisedOffer: { id: 'offers-2', application: 'applications-1', status: 'pending', previous_offer: 'offers-1', trail: [] },
  preferences: { id: 'user_preferences-1', theme: 'light' },
  codeDraft: { id: 'code_drafts-1', campaign: 'campaigns-1', question: 'two-sum', language: 'python', code: '' },
  aiSettings: { id: 'ai_settings-1', provider: 'anthropic', model: 'claude' },
  aiCodingDraft: { id: 'ai_coding_drafts-1', round: 'rounds-1', file_path: 'main.py', contents: '' },
  aiCodingAttempt: { id: 'ai_coding_attempts-1', round: 'rounds-1', status: 'in-progress' },
  takeHomeAttempt: { id: 'take_home_attempts-1', assignment: 'assignments-1', status: 'in-progress' },
  takeHomeDraft: { id: 'take_home_drafts-1', assignment: 'assignments-1', file_path: 'kv.py', contents: '' },
  timer: { id: 'question_timers-7', question_type: 'coding', question_slug: 'two-sum', accumulated_ms: 5000, started_at: '' },
} satisfies Record<string, Row>;

// Every (parent, child) pair the experience hierarchy allows, with its junction table.
const KINDS = Object.keys({ job: 0, project: 0, anecdote: 0, bullet: 0 } satisfies Record<EntityKind, 0>) as EntityKind[];
const JUNCTIONS = KINDS.flatMap((parent) =>
  validChildKinds(parent).map((child) => {
    const table = getJunctionTable(parent, child);
    if (!table) throw new Error(`no junction table for ${parent} -> ${child}`);
    return { parent, child, table };
  }),
);
const withArticle = (kind: EntityKind) => (/^[aeiou]/.test(kind) ? `an ${kind}` : `a ${kind}`);

// ---- Flows that render ----------------------------------------------

async function startPauseAndReset() {
  const timer = renderHook(() => useQuestionTimer('coding', 'two-sum'));
  await settle(); // the initial load finds no row
  expect(timer.result.current.ready).toBe(true);
  await settle(() => timer.result.current.toggle()); // start: the first write creates the row
  await settle(() => timer.result.current.toggle()); // pause
  await settle(() => timer.result.current.reset());
  timer.unmount();
  // Pause and reset patched the row that start created.
  expect(fake.recorded.slice(1).map(({ id }) => id)).toEqual(['question_timers-1', 'question_timers-1']);
}

async function startSavedTimer() {
  const timer = renderHook(() => useQuestionTimer('coding', 'two-sum'));
  await settle(); // the initial load finds the saved row
  await settle(() => timer.result.current.toggle());
  timer.unmount();
  expect(fake.recorded.map(({ id }) => id)).toEqual([ROWS.timer.id]);
}

function SignedIn({ children }: { children: ReactNode }) {
  return createElement(AuthProvider, { children: createElement(ThemeProvider, { children }) });
}

async function changeThemeWhileSignedIn() {
  const theme = renderHook(() => useTheme(), { wrapper: SignedIn });
  await settle(); // AuthProvider's token refresh and ThemeProvider's preference load
  await settle(() => theme.result.current.setTweak('theme', 'dark'));
  await waitFor(() => expect(fake.recorded).toHaveLength(1), { timeout: 2000 }); // the sync is debounced
  theme.unmount();
}

// ---- Write paths ----------------------------------------------------
//
// Keyed by the source function whose create and update calls the branches
// reach, named the way the coverage guard names it.

const WRITE_PATHS: Record<string, Branch[]> = {
  'campaign/api.ts#createCampaign': [
    { when: 'creates a campaign', run: () => createCampaign(CAMPAIGN), writes: [['campaigns', 'create', 'caller']] },
    {
      when: 'restores a campaign from a backup',
      run: () => createCampaign(fromBackup(CAMPAIGN)),
      writes: [['campaigns', 'create', 'caller']],
    },
  ],
  'campaign/api.ts#updateCampaign': [
    {
      when: 'resends the whole campaign',
      run: () => updateCampaign('campaigns-1', { ...CAMPAIGN, status: 'wrapped' }),
      writes: [['campaigns', 'update', 'caller']],
    },
  ],
  'campaign/api.ts#upsertUserPreferences': [
    {
      when: 'creates the preferences row',
      run: () => upsertUserPreferences({ current_campaign_id: 'campaigns-1' }),
      writes: [['user_preferences', 'create', 'caller']],
    },
    {
      when: 'updates the preferences row',
      existing: { user_preferences: ROWS.preferences },
      run: () => upsertUserPreferences({ current_campaign_id: 'campaigns-1' }),
      writes: [['user_preferences', 'update', 'caller']],
    },
  ],

  'applications/api.ts#createApplication': [
    { when: 'creates an application', run: () => createApplication(APPLICATION), writes: [['applications', 'create', 'caller']] },
    {
      when: 'restores an application from a backup',
      run: () => createApplication(fromBackup(APPLICATION)),
      writes: [['applications', 'create', 'caller']],
    },
  ],
  'applications/api.ts#updateApplication': [
    {
      when: 'resends the whole application',
      run: () => updateApplication('applications-1', { ...APPLICATION, status: 'Interviewing' }),
      writes: [['applications', 'update', 'caller']],
    },
  ],
  'applications/api.ts#updateApplicationField': [
    {
      when: 'merges one field into the stored row and resends it',
      existing: { applications: ROWS.application },
      run: () => updateApplicationField('applications-1', { status: 'Offer' }),
      writes: [['applications', 'update', 'caller']],
    },
  ],
  'applications/api.ts#createRound': [
    { when: 'creates a round', run: () => createRound('applications-1', ROUND), writes: [['interview_rounds', 'create', 'caller']] },
    {
      when: 'restores a round from a backup',
      run: () => createRound('applications-1', fromBackup(ROUND)),
      writes: [['interview_rounds', 'create', 'caller']],
    },
  ],
  'applications/api.ts#updateRound': [
    {
      when: 'merges a patch into the stored round and resends it',
      existing: { interview_rounds: ROWS.round },
      run: () => updateRound('interview_rounds-1', { result: 'Passed' }),
      writes: [['interview_rounds', 'update', 'caller']],
    },
  ],
  'applications/api.ts#createOffer': [
    { when: 'records the first offer', run: () => createOffer('applications-1', OFFER), writes: [['offers', 'create', 'caller']] },
    {
      when: 'supersedes the active offer, then records the new one',
      existing: { offers: ROWS.activeOffer },
      run: () => createOffer('applications-1', { ...OFFER, base_salary: 210000 }),
      writes: [
        ['offers', 'update', 'omitted'],
        ['offers', 'create', 'caller'],
      ],
    },
    {
      when: 'restores an offer from a backup',
      run: () => createOffer('applications-1', fromBackup(OFFER)),
      writes: [['offers', 'create', 'caller']],
    },
  ],
  'applications/api.ts#updateOffer': [
    {
      when: 'resends the whole offer',
      run: () => updateOffer('offers-2', 'applications-1', { ...OFFER, status: 'accepted' }),
      writes: [['offers', 'update', 'caller']],
    },
  ],
  'applications/api.ts#deleteOffer': [
    {
      when: 'revives the previous offer after deleting the latest',
      existing: { offers: ROWS.revisedOffer },
      run: () => deleteOffer('offers-2'),
      writes: [['offers', 'update', 'omitted']],
    },
  ],

  'todos/api.ts#createTodo': [
    { when: 'creates a todo', run: () => createTodo(TODO), writes: [['todos', 'create', 'caller']] },
    { when: 'restores a todo from a backup', run: () => createTodo(fromBackup(TODO)), writes: [['todos', 'create', 'caller']] },
  ],
  'todos/api.ts#updateTodo': [
    {
      when: 'resends the whole todo',
      run: () => updateTodo('todos-1', { ...TODO, completed_at: '2026-10-02' }),
      writes: [['todos', 'update', 'caller']],
    },
  ],

  'hooks/progressApi.ts#createUserProgress': [
    { when: 'creates a progress row', run: () => createUserProgress(PROGRESS), writes: [['user_progress', 'create', 'caller']] },
    {
      when: 'restores a progress row from a backup',
      run: () => createUserProgress(fromBackup(PROGRESS)),
      writes: [['user_progress', 'create', 'caller']],
    },
  ],
  'hooks/progressApi.ts#updateUserProgress': [
    {
      when: 'resends the whole progress row',
      run: () => updateUserProgress('user_progress-1', { ...PROGRESS, status: 'mastered' }),
      writes: [['user_progress', 'update', 'caller']],
    },
  ],

  'lib/codeDraftsApi.ts#upsertCodeDraft': [
    { when: 'creates the draft', run: () => upsertCodeDraft(CODE_DRAFT), writes: [['code_drafts', 'create', 'caller']] },
    {
      when: 'updates the stored draft',
      existing: { code_drafts: ROWS.codeDraft },
      run: () => upsertCodeDraft({ ...CODE_DRAFT, code: 'return []' }),
      writes: [['code_drafts', 'update', 'caller']],
    },
    {
      when: 'restores a draft from a backup',
      run: () => upsertCodeDraft(fromBackup(CODE_DRAFT)),
      writes: [['code_drafts', 'create', 'caller']],
    },
  ],

  'experience/experienceApi.ts#createJob': [
    {
      when: 'creates a job',
      run: () => createJob({ company: 'Acme', role: 'Engineer', start_date: '2024-01-01' }),
      writes: [['experience_jobs', 'create', 'caller']],
    },
  ],
  'experience/experienceApi.ts#updateJob': [
    {
      when: 'patches the edited field',
      run: () => updateJob('experience_jobs-1', { role: 'Senior Engineer' }),
      writes: [['experience_jobs', 'update', 'omitted']],
    },
  ],
  'experience/experienceApi.ts#createProject': [
    {
      when: 'creates a project',
      run: () => createProject({ title: 'Billing rewrite', company: 'Acme' }),
      writes: [['experience_projects', 'create', 'caller']],
    },
  ],
  'experience/experienceApi.ts#updateProject': [
    {
      when: 'patches the edited fields',
      run: () => updateProject('experience_projects-1', { title: 'Billing v2', tech_stack: ['go'] }),
      writes: [['experience_projects', 'update', 'omitted']],
    },
  ],
  'experience/experienceApi.ts#createAnecdote': [
    {
      when: 'creates an anecdote',
      run: () => createAnecdote({ title: 'The outage', situation: 'Checkout was down' }),
      writes: [['experience_anecdotes', 'create', 'caller']],
    },
  ],
  'experience/experienceApi.ts#updateAnecdote': [
    {
      when: 'patches the edited fields',
      run: () => updateAnecdote('experience_anecdotes-1', { title: 'The outage retro', category_ids: ['leadership'] }),
      writes: [['experience_anecdotes', 'update', 'omitted']],
    },
    {
      when: 'keeps a stray user out of the patch',
      run: () => updateAnecdote('experience_anecdotes-1', fromBackup({ notes: 'Tell it in two minutes' })),
      writes: [['experience_anecdotes', 'update', 'omitted']],
    },
  ],
  'experience/experienceApi.ts#createBullet': [
    {
      when: 'creates a bullet',
      run: () => createBullet({ title: 'Cut p99 latency by 40%' }),
      writes: [['experience_bullets', 'create', 'caller']],
    },
  ],
  'experience/experienceApi.ts#updateBullet': [
    {
      when: 'patches the edited field',
      run: () => updateBullet('experience_bullets-1', { impact: '40% faster checkout' }),
      writes: [['experience_bullets', 'update', 'omitted']],
    },
  ],

  'experience/connectionApi.ts#createConnection': [
    ...JUNCTIONS.map(({ parent, child, table }): Branch => ({
      when: `links ${withArticle(parent)} to ${withArticle(child)}`,
      run: () => createConnection(parent, `${parent}-1`, child, `${child}-1`),
      writes: [[table, 'create', 'caller']],
    })),
    {
      when: 'links every pair at once through batchCreateConnections (import)',
      run: () =>
        batchCreateConnections(
          JUNCTIONS.map(({ parent, child }) => ({
            parentKind: parent,
            parentId: `${parent}-1`,
            childKind: child,
            childId: `${child}-1`,
          })),
        ),
      writes: JUNCTIONS.map(({ table }): Expected => [table, 'create', 'caller']),
    },
  ],

  'features/resume/api.ts#createResume': [
    { when: 'creates a resume', run: () => createResume({ name: 'Staff resume' }), writes: [['resumes', 'create', 'caller']] },
  ],
  'features/resume/api.ts#updateResume': [
    {
      when: 'patches the edited fields',
      run: () => updateResume('resumes-1', { name: 'Staff resume v2', slug: 'staff-resume-v2' }),
      writes: [['resumes', 'update', 'omitted']],
    },
  ],
  'features/resume/api.ts#createVariant': [
    {
      when: 'creates a variant',
      run: () =>
        createVariant({ resume_id: 'resumes-1', name: 'Acme', data: emptyResumeData(), application_id: 'applications-1' }),
      writes: [['resume_variants', 'create', 'caller']],
    },
  ],
  'features/resume/api.ts#updateVariant': [
    {
      when: 'patches the edited fields',
      run: () => updateVariant('resume_variants-1', { name: 'Acme v2', application_id: 'applications-1' }),
      writes: [['resume_variants', 'update', 'omitted']],
    },
  ],
  'features/resume/api.ts#createVersion': [
    {
      when: 'snapshots a version',
      run: () => createVersion({ resumeId: 'resumes-1', data: emptyResumeData(), label: 'Before edits' }),
      writes: [['resume_versions', 'create', 'caller']],
    },
  ],
  'features/resume/api.ts#upsertAISettings': [
    {
      when: 'creates the settings row',
      run: () => upsertAISettings({ provider: 'anthropic', model: 'claude' }),
      writes: [['ai_settings', 'create', 'caller']],
    },
    {
      when: 'updates the settings row',
      existing: { ai_settings: ROWS.aiSettings },
      run: () => upsertAISettings({ provider: 'openai', model: 'gpt' }),
      writes: [['ai_settings', 'update', 'caller']],
    },
  ],
  'features/resume/api.ts#createShareLink': [
    {
      when: 'creates a share link',
      run: () => createShareLink({ variantId: 'resume_variants-1', token: 'share-token' }),
      writes: [['resume_share_links', 'create', 'caller']],
    },
  ],

  'pages/ai-coding/aiCodingApi.ts#upsertDraft': [
    {
      when: 'creates the file draft',
      run: () => aiCoding.upsertDraft(AI_CODING_DRAFT),
      writes: [['ai_coding_drafts', 'create', 'caller']],
    },
    {
      when: 'patches the stored file draft',
      existing: { ai_coding_drafts: ROWS.aiCodingDraft },
      run: () => aiCoding.upsertDraft(AI_CODING_DRAFT),
      writes: [['ai_coding_drafts', 'update', 'omitted']],
    },
  ],
  'pages/ai-coding/aiCodingApi.ts#upsertInProgressAttempt': [
    {
      when: 'creates the in-progress attempt',
      run: () => aiCoding.upsertInProgressAttempt(AI_CODING_ATTEMPT),
      writes: [['ai_coding_attempts', 'create', 'caller']],
    },
    {
      when: 'updates the in-progress attempt',
      existing: { ai_coding_attempts: ROWS.aiCodingAttempt },
      run: () => aiCoding.upsertInProgressAttempt({ ...AI_CODING_ATTEMPT, currentCheckpoint: 2 }),
      writes: [['ai_coding_attempts', 'update', 'caller']],
    },
  ],
  'pages/ai-coding/aiCodingApi.ts#persistAttempt': [
    {
      when: 'records the graded attempt',
      run: () =>
        aiCoding.persistAttempt({
          roundId: 'rounds-1',
          campaignId: 'campaigns-1',
          currentCheckpoint: 2,
          files: { 'main.py': 'print(1)' },
          test_results: [{ passed: true, passed_count: 3, failed_count: 0, stdout: '', error: null }],
          rubric_review: { items: [], total: 0 },
          ai_chats: AI_CODING_ATTEMPT.chats,
          duration_ms: 60000,
        }),
      writes: [['ai_coding_attempts', 'create', 'caller']],
    },
  ],

  'pages/take-home/takeHomeApi.ts#upsertInProgressTakeHomeAttempt': [
    {
      when: 'creates the in-progress attempt',
      run: () => takeHome.upsertInProgressTakeHomeAttempt(TAKE_HOME_ATTEMPT),
      writes: [['take_home_attempts', 'create', 'caller']],
    },
    {
      when: 'updates the in-progress attempt',
      existing: { take_home_attempts: ROWS.takeHomeAttempt },
      run: () => takeHome.upsertInProgressTakeHomeAttempt(TAKE_HOME_ATTEMPT),
      writes: [['take_home_attempts', 'update', 'caller']],
    },
  ],
  'pages/take-home/takeHomeApi.ts#upsertDraft': [
    {
      when: 'creates the file draft',
      run: () => takeHome.upsertDraft(TAKE_HOME_DRAFT),
      writes: [['take_home_drafts', 'create', 'caller']],
    },
    {
      when: 'patches the stored file draft',
      existing: { take_home_drafts: ROWS.takeHomeDraft },
      run: () => takeHome.upsertDraft(TAKE_HOME_DRAFT),
      writes: [['take_home_drafts', 'update', 'omitted']],
    },
  ],

  'hooks/useQuestionTimer.ts#useQuestionTimer': [
    {
      when: 'creates the timer on the first start, then patches it on pause and reset',
      run: startPauseAndReset,
      writes: [
        ['question_timers', 'create', 'caller'],
        ['question_timers', 'update', 'omitted'],
        ['question_timers', 'update', 'omitted'],
      ],
    },
    {
      when: 'patches a saved timer on start',
      existing: { question_timers: ROWS.timer },
      run: startSavedTimer,
      writes: [['question_timers', 'update', 'omitted']],
    },
  ],

  'theme/ThemeProvider.tsx#upsertThemePreferences': [
    {
      when: 'creates the preferences row',
      run: () => upsertThemePreferences(fake.state.authId, TWEAKS),
      writes: [['user_preferences', 'create', 'caller']],
    },
    {
      when: 'updates the preferences row',
      existing: { user_preferences: ROWS.preferences },
      run: () => upsertThemePreferences(fake.state.authId, TWEAKS),
      writes: [['user_preferences', 'update', 'caller']],
    },
    {
      when: "syncs a ThemeProvider change under the signed-in caller's id",
      run: changeThemeWhileSignedIn,
      writes: [['user_preferences', 'create', 'caller']],
    },
  ],
};

const CASES = Object.entries(WRITE_PATHS).flatMap(([site, branches]) =>
  branches.map((branch) => ({ ...branch, site, title: `${site}: ${branch.when}` })),
);

describe('SPA writes under the account-scope rules', () => {
  it.each(CASES.map((c) => [c.title, c] as const))('%s', async (_title, { existing, run, writes }) => {
    fake.state.existing = existing ?? {};
    await run();
    const rejected = fake.recorded
      .filter((write) => !rulesAccept(write))
      .map((write) => `${write.op} ${write.collection}: user is ${userField(write)}`);
    expect(rejected).toEqual([]);
    expect(fake.recorded.map((write) => [write.collection, write.op, userField(write)])).toEqual(writes);
  });
});

// ---- DataSection import ---------------------------------------------
//
// importBundle is private to DataSection, so this drives the real component:
// a backup file goes in through its file input and the whole import runs. Every
// row in the file names another account, the way a file exported from a
// different account would. DataSection makes no write calls of its own, so the
// coverage guard below doesn't list it; this case covers it instead.

describe('DataSection import', () => {
  it('imports a backup from another account with every row owned by the caller', async () => {
    const bundle = {
      format_version: 1,
      exported_at: '2026-10-01T00:00:00.000Z',
      campaign: fromBackup({ id: 'old-campaign', name: 'Fall search', slug: 'fall-search' }),
      applications: [
        fromBackup({
          id: 'old-application',
          company: 'Acme',
          role: 'Staff Engineer',
          rounds: [fromBackup({ id: 'old-round', round_type: 'Onsite', date: '2026-10-01' })],
          offer: fromBackup({ id: 'old-offer', base_salary: 200000, status: 'pending' }),
        }),
      ],
      todos: [
        fromBackup({
          id: 'old-todo',
          body: 'Send the thank-you note',
          mentions: [{ type: 'application', slug: 'old-application' }],
        }),
      ],
      user_progress: [
        fromBackup({ id: 'old-progress', question_type: 'coding', question_slug: 'two-sum', status: 'in-progress' }),
      ],
      code_drafts: [fromBackup({ id: 'old-draft', question: 'two-sum', language: 'python', code: 'pass' })],
      anecdotes_referenced: [],
    };

    const view = render(createElement(DataSection));
    const input = view.container.querySelector<HTMLInputElement>('#data-import-file');
    expect(input).not.toBeNull();
    const file = new File([JSON.stringify(bundle)], 'backup.json', { type: 'application/json' });
    fireEvent.change(input!, { target: { files: [file] } });
    // The success message only renders once importBundle has finished cleanly.
    await waitFor(() => expect(view.getByText(/Imported 1 campaign\./)).toBeTruthy());
    view.unmount();

    const rejected = fake.recorded
      .filter((write) => !rulesAccept(write))
      .map((write) => `${write.op} ${write.collection}: user is ${userField(write)}`);
    expect(rejected).toEqual([]);
    expect(fake.recorded.map((write) => [write.collection, write.op, userField(write)])).toEqual([
      ['campaigns', 'create', 'caller'],
      ['applications', 'create', 'caller'],
      ['interview_rounds', 'create', 'caller'],
      ['offers', 'create', 'caller'],
      ['todos', 'create', 'caller'],
      ['user_progress', 'create', 'caller'],
      ['code_drafts', 'create', 'caller'],
    ]);
  });
});

// ---- Source scan ----------------------------------------------------

interface WriteSite {
  /** `file#name` of the top-level declaration the write call sits in. */
  site: string;
  op: string;
  collection: string;
}

/** The SPA's own modules: tests, the test setup, and type declarations left out. */
function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      return ['__tests__', '__compat__', 'test'].includes(name) ? [] : sourceFiles(path);
    }
    const code = /\.[cm]?[jt]sx?$/.test(name) && !name.endsWith('.d.ts');
    return code && !/\.(test|spec)\.[cm]?[jt]sx?$/.test(name) ? [path] : [];
  });
}

const USES_POCKETBASE = /from\s+['"](?:[./]+(?:[\w-]+\/)*)?pocketbase['"]/;
// Batch requests, a raw pb.send, or a hand-built record URL would all slip past the scan.
const BYPASS = /\bcreateBatch\s*\(|\bpb\s*\.\s*send\s*\(|['"`]\/api\/collections\//;
const WRITE_CALL = /\.\s*(create|update|upsert)\s*(?:<[^<>()]*>)?\s*\(/g;
const ON_COLLECTION = /\.collection\s*(?:<[^<>()]*>)?\(\s*(?:(['"])([\w-]+)\1|([A-Za-z_$][\w$.]*))\s*\)\s*$/;
const ON_ACCESSOR = /\b([A-Za-z_$][\w$]*)\s*\(\s*\)\s*$/;
const COLLECTION_OF = String.raw`pb\s*\.\s*collection\s*(?:<[^<>()]*>)?\(\s*(['"])([\w-]+)\1\s*\)`;
const TOP_LEVEL = /^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?|class|const|let|var)\s+([A-Za-z_$][\w$]*)/gm;

const asPattern = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function enclosingDeclaration(text: string, at: number): string {
  let name = '<module>';
  for (const match of text.slice(0, at).matchAll(TOP_LEVEL)) name = match[1];
  return name;
}

/** The collections a write call's receiver names, or null when it can't tell. */
function collectionsWritten(
  text: string,
  file: string,
  receiver: string,
  runtime: Record<string, string[]>,
): string[] | null {
  const direct = ON_COLLECTION.exec(receiver);
  if (direct?.[2]) return [direct[2]];
  if (direct?.[3]) {
    const constant = new RegExp(
      String.raw`(?:const|let|var)\s+${asPattern(direct[3])}\s*(?::[^=;]+)?=\s*(['"])([\w-]+)\1`,
    ).exec(text);
    return constant ? [constant[2]] : (runtime[`${file}#${direct[3]}`] ?? null);
  }
  const accessor = ON_ACCESSOR.exec(receiver);
  if (!accessor) return null;
  const name = asPattern(accessor[1]);
  const defined =
    new RegExp(String.raw`(?:const|let|var)\s+${name}\s*=\s*\(\s*\)\s*=>\s*${COLLECTION_OF}`).exec(text) ??
    new RegExp(String.raw`function\s+${name}\s*\(\s*\)[^{]*\{\s*return\s+${COLLECTION_OF}`).exec(text);
  return defined ? [defined[2]] : null;
}

function scanWrites(src: string, runtime: Record<string, string[]>) {
  const sites: WriteSite[] = [];
  const unresolved: string[] = [];
  const bypasses: string[] = [];
  for (const path of sourceFiles(src)) {
    const file = relative(src, path).split(sep).join('/');
    const raw = readFileSync(path, 'utf8');
    if (BYPASS.test(raw)) bypasses.push(file);
    if (!USES_POCKETBASE.test(raw)) continue;
    // Fold chained calls (`pb\n  .collection(...)\n  .create(...)`) onto one line.
    const text = raw.replace(/\s*\n\s*\./g, '.');
    for (const call of text.matchAll(WRITE_CALL)) {
      const at = call.index ?? 0;
      const lineSoFar = text.slice(text.lastIndexOf('\n', at) + 1, at);
      if (/^\s*(?:\/\/|\/\*|\*)/.test(lineSoFar)) continue; // prose in a comment
      const site = `${file}#${enclosingDeclaration(text, at)}`;
      const collections = collectionsWritten(text, file, text.slice(Math.max(0, at - 300), at), runtime);
      if (!collections) unresolved.push(`${site}: ${lineSoFar.trim()}${call[0]}`);
      else for (const collection of collections) sites.push({ site, op: call[1], collection });
    }
  }
  return { sites, unresolved, bypasses };
}

/** `{ site: ['create campaigns', ...] }`, sorted and de-duplicated. */
function bySite(pairs: Array<readonly [string, string]>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [site, write] of pairs) out[site] = [...new Set([...(out[site] ?? []), write])].sort();
  return out;
}

describe('coverage guard', () => {
  const SRC = resolve(__dirname, '..');
  // The auth collection: it has no `user` field, and these rules leave it alone.
  const OUT_OF_SCOPE = new Set(['users']);
  // Every collection the SPA writes. Each one is exercised above.
  const COVERED = new Set([
    'campaigns',
    'user_preferences',
    'applications',
    'interview_rounds',
    'offers',
    'todos',
    'user_progress',
    'code_drafts',
    'experience_jobs',
    'experience_projects',
    'experience_anecdotes',
    'experience_bullets',
    'exp_job_projects',
    'exp_job_anecdotes',
    'exp_job_bullets',
    'exp_project_anecdotes',
    'exp_project_bullets',
    'exp_anecdote_bullets',
    'resumes',
    'resume_variants',
    'resume_versions',
    'resume_share_links',
    'ai_settings',
    'ai_coding_drafts',
    'ai_coding_attempts',
    'take_home_drafts',
    'take_home_attempts',
    'question_timers',
  ]);
  // Writes whose collection is a runtime value, keyed `file#argument`.
  const RUNTIME_COLLECTIONS: Record<string, string[]> = {
    'experience/connectionApi.ts#table': JUNCTIONS.map(({ table }) => table),
  };

  const scan = scanWrites(SRC, RUNTIME_COLLECTIONS);
  const inScope = scan.sites.filter(({ collection }) => !OUT_OF_SCOPE.has(collection));

  it('accounts for every create and update call in modules that use PocketBase', () => {
    expect(scan.unresolved).toEqual([]);
    expect(scan.bypasses).toEqual([]);
  });

  it('finds no written collection missing from COVERED', () => {
    const written = new Set(inScope.map(({ collection }) => collection));
    expect([...written].filter((collection) => !COVERED.has(collection)).sort()).toEqual([]);
    // COVERED claims nothing the cases above don't exercise.
    const exercised = new Set(CASES.flatMap(({ writes }) => writes.map(([collection]) => collection)));
    expect([...COVERED].filter((collection) => !exercised.has(collection)).sort()).toEqual([]);
  });

  it('exercises every create and update call, in every function that makes one', () => {
    const inSource = bySite(inScope.map(({ site, op, collection }) => [site, `${op} ${collection}`] as const));
    const exercised = bySite(
      CASES.flatMap(({ site, writes }) => writes.map(([collection, op]) => [site, `${op} ${collection}`] as const)),
    );
    expect(exercised).toEqual(inSource);
  });
});
