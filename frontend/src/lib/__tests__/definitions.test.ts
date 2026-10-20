// Definition requests (ROUNDS-00A-L02): the gate the SPA shares with the
// runner, the version a row names, the compiled case ids, and the one
// retry a replaced version gets.

import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../pocketbase', () => ({ pb: { authStore: { token: '' } } }));

import {
  caseIdFor,
  definitionRef,
  definitionVersion,
  definitionsEnforced,
  retrySuperseded,
} from '../definitions';
import { RunnerError } from '../runnerFetch';

type ConfigWindow = { __ROUNDS_CONFIG__?: Record<string, string | undefined> };

function setGate(value: string | undefined) {
  (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { ROUNDS_GATE_EXECUTION_DEFINITIONS: value };
}

afterEach(() => {
  delete (window as unknown as ConfigWindow).__ROUNDS_CONFIG__;
  vi.unstubAllEnvs();
});

const superseded = () => new RunnerError({ message: 'x', status: 409, code: 'definition_superseded' });

describe('definitionsEnforced', () => {
  it('is off by default and while the gate is legacy or disabled', () => {
    expect(definitionsEnforced()).toBe(false);
    setGate('legacy');
    expect(definitionsEnforced()).toBe(false);
    setGate('disabled');
    expect(definitionsEnforced()).toBe(false);
  });

  it('follows runtime-config.js to enforce', () => {
    setGate('enforce');
    expect(definitionsEnforced()).toBe(true);
  });

  it('a value it does not know never sends definition requests', () => {
    setGate('enforced');
    expect(definitionsEnforced()).toBe(false);
  });
});

describe('definitionVersion and caseIdFor', () => {
  it.each([
    [3, 3],
    [1, 1],
    [undefined, 1],
    [null, 1],
    [0, 1],
    [1.5, 1],
  ])('a row recording %o names version %i', (recorded, version) => {
    expect(definitionVersion(recorded as number | null | undefined)).toBe(version);
  });

  it('builds the reference the runner resolves', () => {
    expect(definitionRef('coding', 'two-sum', 'python', 2)).toEqual({
      track: 'coding',
      slug: 'two-sum',
      variant: 'python',
      version: 2,
    });
  });

  it("uses the row's case ids, else the compiled names", () => {
    expect(caseIdFor(1, ['c000', 'c001'])).toBe('c001');
    expect(caseIdFor(12, null)).toBe('c012');
    expect(caseIdFor(2, ['c000'])).toBe('c002');
  });
});

describe('retrySuperseded', () => {
  it('sends once when the version is current', async () => {
    const send = vi.fn().mockResolvedValue('ok');
    const reread = vi.fn();
    await expect(retrySuperseded(1, send, reread)).resolves.toBe('ok');
    expect(send.mock.calls).toEqual([[1]]);
    expect(reread).not.toHaveBeenCalled();
  });

  it('rereads the row and sends once more with the version it names now', async () => {
    const send = vi.fn().mockRejectedValueOnce(superseded()).mockResolvedValueOnce('ok');
    const reread = vi.fn().mockResolvedValue(2);
    await expect(retrySuperseded(1, send, reread)).resolves.toBe('ok');
    expect(send.mock.calls).toEqual([[1], [2]]);
  });

  it('gives a second refusal to the caller instead of retrying again', async () => {
    const second = superseded();
    const send = vi.fn().mockRejectedValueOnce(superseded()).mockRejectedValueOnce(second);
    await expect(retrySuperseded(1, send, vi.fn().mockResolvedValue(2))).rejects.toBe(second);
    expect(send).toHaveBeenCalledTimes(2);
  });

  it('does not resend when the row still names the replaced version', async () => {
    const first = superseded();
    const send = vi.fn().mockRejectedValue(first);
    await expect(retrySuperseded(undefined, send, vi.fn().mockResolvedValue(1))).rejects.toBe(first);
    expect(send).toHaveBeenCalledTimes(1);
  });

  it('keeps the refusal when the row cannot be reread', async () => {
    const first = superseded();
    const send = vi.fn().mockRejectedValue(first);
    await expect(retrySuperseded(1, send, vi.fn().mockRejectedValue(new Error('offline')))).rejects.toBe(first);
    expect(send).toHaveBeenCalledTimes(1);
  });

  it.each([
    new RunnerError({ message: 'x', status: 410, code: 'definition_retired' }),
    new RunnerError({ message: 'x', status: 422, code: 'legacy_request_rejected' }),
    new Error('boom'),
  ])('passes any other failure straight through: %o', async (error) => {
    const send = vi.fn().mockRejectedValue(error);
    const reread = vi.fn();
    await expect(retrySuperseded(1, send, reread)).rejects.toBe(error);
    expect(reread).not.toHaveBeenCalled();
  });
});
