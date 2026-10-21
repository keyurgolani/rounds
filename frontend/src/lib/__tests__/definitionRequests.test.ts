// What the six execution calls send under each value of
// ROUNDS_GATE_EXECUTION_DEFINITIONS (ROUNDS-00A-L02): #1's shapes at
// legacy, and at enforce the definition and the candidate's inputs only,
// with nothing that chooses what runs or how it scores.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder', model: null } } }));

import { evaluateCode, runCode } from '../../pages/coding/runnerApi';
import { gradeAttempt, runProject as runAICodingProject } from '../../pages/ai-coding/aiCodingApi';
import { runProject as runTakeHome, submitAttempt } from '../../pages/take-home/takeHomeApi';

type ConfigWindow = { __ROUNDS_CONFIG__?: Record<string, string | undefined> };

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => new Response('{}', { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  delete (window as unknown as ConfigWindow).__ROUNDS_CONFIG__;
  vi.unstubAllGlobals();
});

function setGate(value: string) {
  (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { ROUNDS_GATE_EXECUTION_DEFINITIONS: value };
}

function sent(): Record<string, unknown> {
  return JSON.parse(fetchMock.mock.calls[0][1]!.body as string) as Record<string, unknown>;
}

const FILES = { 'client.py': 'x = 1\n' };
const CHATS = [{ checkpoint: 0, role: 'user', content: 'hi', ts: 1 }];

const CALLS: Array<[string, () => Promise<unknown>]> = [
  [
    'run',
    () =>
      runCode({
        question_slug: 'two-sum',
        language: 'python',
        code: 'def f(): pass',
        input: { nums: [1] },
        definition_version: 2,
      }),
  ],
  [
    'evaluate by case',
    () =>
      evaluateCode({
        question_slug: 'two-sum',
        language: 'javascript',
        code: 'function f() {}',
        filter: { indices: [1] },
        definition_version: 2,
        definition_case_ids: ['c000', 'c001'],
      }),
  ],
  [
    'evaluate by tag',
    () =>
      evaluateCode({
        question_slug: 'two-sum',
        language: 'python',
        code: 'def f(): pass',
        filter: { tags: ['basic'] },
      }),
  ],
  [
    'run-project',
    () =>
      runAICodingProject({
        round_slug: 'hallucinated-http-client',
        language: 'typescript',
        checkpoint_index: 0,
        files: FILES,
        definition_version: 1,
      }),
  ],
  [
    'grade',
    () =>
      gradeAttempt({
        round_slug: 'hallucinated-http-client',
        files: FILES,
        ai_chats: CHATS,
        language: 'python',
        definition_version: 1,
      }),
  ],
  [
    'take-home run',
    () => runTakeHome('kv-store-py', FILES, { language: 'python', definition_version: 1 }),
  ],
  [
    'take-home submit',
    () =>
      submitAttempt({
        assignment_slug: 'kv-store-py',
        files: FILES,
        notes: 'n',
        ai_chats: CHATS,
        campaign_id: 'abcdefghijklmno',
        duration_ms: 5,
        language: 'python',
        definition_version: 1,
      }),
  ],
];

const LEGACY: Record<string, Record<string, unknown>> = {
  run: { question_slug: 'two-sum', language: 'python', code: 'def f(): pass', input: { nums: [1] } },
  'evaluate by case': {
    question_slug: 'two-sum',
    language: 'javascript',
    code: 'function f() {}',
    filter: { indices: [1] },
  },
  'evaluate by tag': {
    question_slug: 'two-sum',
    language: 'python',
    code: 'def f(): pass',
    filter: { tags: ['basic'] },
  },
  'run-project': {
    round_slug: 'hallucinated-http-client',
    language: 'typescript',
    checkpoint_index: 0,
    files: FILES,
  },
  grade: { round_slug: 'hallucinated-http-client', files: FILES, ai_chats: CHATS },
  'take-home run': { assignment_slug: 'kv-store-py', files: FILES },
  'take-home submit': {
    assignment_slug: 'kv-store-py',
    files: FILES,
    notes: 'n',
    ai_chats: CHATS,
    campaign_id: 'abcdefghijklmno',
    duration_ms: 5,
  },
};

const ENFORCED: Record<string, Record<string, unknown>> = {
  run: {
    definition: { track: 'coding', slug: 'two-sum', variant: 'python', version: 2 },
    code: 'def f(): pass',
    input: { nums: [1] },
  },
  'evaluate by case': {
    definition: { track: 'coding', slug: 'two-sum', variant: 'javascript', version: 2 },
    code: 'function f() {}',
    case_ids: ['c001'],
  },
  'evaluate by tag': {
    definition: { track: 'coding', slug: 'two-sum', variant: 'python', version: 1 },
    code: 'def f(): pass',
    tags: ['basic'],
  },
  'run-project': {
    definition: { track: 'ai-coding', slug: 'hallucinated-http-client', variant: 'typescript', version: 1 },
    checkpoint: 0,
    files: FILES,
  },
  grade: {
    definition: { track: 'ai-coding', slug: 'hallucinated-http-client', variant: 'python', version: 1 },
    files: FILES,
    ai_chats: CHATS,
  },
  'take-home run': {
    definition: { track: 'take-home', slug: 'kv-store-py', variant: 'python', version: 1 },
    files: FILES,
  },
  'take-home submit': {
    definition: { track: 'take-home', slug: 'kv-store-py', variant: 'python', version: 1 },
    files: FILES,
    notes: 'n',
    ai_chats: CHATS,
    campaign_id: 'abcdefghijklmno',
    duration_ms: 5,
  },
};

describe('the six execution calls', () => {
  it.each(CALLS)('%s sends exactly the legacy shape by default', async (name, call) => {
    await call();
    expect(sent()).toEqual(LEGACY[name]);
  });

  it.each(CALLS)('%s sends exactly the legacy shape while the gate is disabled', async (name, call) => {
    setGate('disabled');
    await call();
    expect(sent()).toEqual(LEGACY[name]);
  });

  it.each(CALLS)('%s sends only the definition and the inputs at enforce', async (name, call) => {
    setGate('enforce');
    await call();
    expect(sent()).toEqual(ENFORCED[name]);
  });

  it('an evaluate of everything sends no selection at enforce', async () => {
    setGate('enforce');
    await evaluateCode({ question_slug: 'two-sum', language: 'python', code: 'x' });
    expect(sent()).toEqual({
      definition: { track: 'coding', slug: 'two-sum', variant: 'python', version: 1 },
      code: 'x',
    });
  });
});
