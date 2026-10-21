import { describe, expect, it, vi } from 'vitest';

vi.mock('../pocketbase', () => ({ pb: { authStore: { token: '' } } }));

import { RunnerError } from '../runnerFetch';
import { activeTrigger, classifyRunnerError, formatWait } from '../runnerDenial';

function err(status: number, code: string | null = null, extra: Partial<{ retryAfterSeconds: number; correlationId: string }> = {}) {
  return new RunnerError({ message: `Request ${status}: x`, status, code, ...extra });
}

describe('classifyRunnerError', () => {
  it.each([
    [err(503, 'route_disabled'), 'turned_off'],
    [err(503, 'definitions_disabled'), 'turned_off'],
    [err(0, 'unauthenticated'), 'sign_in'],
    [err(401), 'sign_in'],
    [err(429, 'quota_exceeded'), 'limit'],
    [err(429, 'demo_limit_reached'), 'limit'],
    [err(429), 'limit'],
    [err(413, 'payload_too_large'), 'too_large'],
    [err(413, 'limit_exceeded'), 'too_large'],
    [err(413), 'too_large'],
    [err(403, 'not_permitted'), 'not_permitted'],
    [err(503, 'auth_unavailable'), 'unavailable'],
    [err(503, 'quota_unavailable'), 'unavailable'],
    [err(503, 'worker_unavailable'), 'unavailable'],
    [err(0), 'unavailable'],
    [err(500), 'unavailable'],
    [err(502), 'unavailable'],
  ])('maps %o to %s', (error, kind) => {
    expect(classifyRunnerError(error)?.kind).toBe(kind);
  });

  it.each([
    [err(400, 'idempotency_key_required'), 'unavailable'],
    [err(409, 'already_completed'), 'unavailable'],
    [err(409, 'idempotency_mismatch'), 'unavailable'],
    [err(409, 'already_in_flight', { retryAfterSeconds: 4 }), 'unavailable'],
  ])('shows the idempotency refusal %o as %s', (error, kind) => {
    expect(classifyRunnerError(error)?.kind).toBe(kind);
  });

  it.each([err(400), err(403), err(404), err(409), err(422, 'invalid_request'), err(422, 'render_timeout')])(
    'leaves %o to the existing error display',
    (error) => {
      expect(classifyRunnerError(error)).toBeNull();
    },
  );

  it('never classifies errors that are not RunnerErrors', () => {
    expect(classifyRunnerError(new Error('Request 500: boom'))).toBeNull();
    expect(classifyRunnerError('boom')).toBeNull();
    expect(classifyRunnerError(null)).toBeNull();
  });

  it('a route_disabled code wins over the status, and a typed 403 needs its code', () => {
    expect(classifyRunnerError(err(401, 'route_disabled'))?.kind).toBe('turned_off');
    expect(classifyRunnerError(err(403))).toBeNull();
  });

  it('carries the wait, the reference, and the trigger', () => {
    const button = document.createElement('button');
    const denial = classifyRunnerError(
      err(429, 'quota_exceeded', { retryAfterSeconds: 42, correlationId: '0123456789abcdef0123456789abcdef' }),
      button,
    );
    expect(denial).toMatchObject({
      kind: 'limit',
      status: 429,
      code: 'quota_exceeded',
      retryAfterSeconds: 42,
      correlationId: '0123456789abcdef0123456789abcdef',
      trigger: button,
    });
  });
});

describe('definition refusals (ROUNDS-00A-L02)', () => {
  function typed(status: number, code: string, detail = 'A fixed sentence from the server.') {
    return new RunnerError({ message: `Request ${status}: ${detail}`, status, code, detail });
  }

  it.each([
    [typed(422, 'legacy_request_rejected'), 'reload'],
    [typed(422, 'case_unknown'), 'reload'],
    [typed(409, 'definition_superseded'), 'reload'],
    [typed(410, 'definition_retired'), 'retired'],
    [typed(404, 'definition_not_found'), 'not_found'],
    [typed(422, 'runtime_unsupported'), 'unsupported'],
    [typed(422, 'path_not_allowed'), 'path_not_allowed'],
    [typed(503, 'definition_integrity_mismatch'), 'unavailable'],
  ])('maps %o to %s', (error, kind) => {
    expect(classifyRunnerError(error)?.kind).toBe(kind);
  });

  it("keeps the server's fixed sentence only where the notice shows it", () => {
    const unsupported = "This language isn't supported here. Try javascript.";
    expect(classifyRunnerError(typed(422, 'runtime_unsupported', unsupported))?.detail).toBe(unsupported);
    const path = "A file uses a path the grader owns. Rename or remove it and try again.";
    expect(classifyRunnerError(typed(422, 'path_not_allowed', path))?.detail).toBe(path);
    for (const code of ['legacy_request_rejected', 'definition_retired', 'definition_not_found']) {
      expect(classifyRunnerError(typed(422, code))?.detail).toBeNull();
    }
  });
});

describe('activeTrigger', () => {
  it('returns the focused control, or null when focus is on the body', () => {
    const button = document.createElement('button');
    document.body.appendChild(button);
    button.focus();
    expect(activeTrigger()).toBe(button);
    button.blur();
    expect(activeTrigger()).toBeNull();
    button.remove();
  });
});

describe('formatWait', () => {
  it.each([
    [1, 'in 1 second'],
    [0.2, 'in 1 second'],
    [45, 'in 45 seconds'],
    [60, 'in 1 minute'],
    [61, 'in 2 minutes'],
    [3599, 'in 60 minutes'],
    [3600, 'in 1 hour'],
    [7201, 'in 3 hours'],
    [null, 'later'],
    [-1, 'later'],
    [Number.NaN, 'later'],
  ])('formats %s as %s', (seconds, text) => {
    expect(formatWait(seconds as number | null)).toBe(text);
  });
});
