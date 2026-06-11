import { test } from 'node:test';
import assert from 'node:assert/strict';

import { fetchUser } from '../../client.ts';

test('fetchUser returns the JSON body', async () => {
  const expected = { id: 'u-1', name: 'Alex' };

  // Stand in for both the AI's invented method AND the real
  // `fetch(...).json()` combo so either implementation passes here.
  // That's exactly why the hidden test is needed against a real
  // server — the visible test alone cannot catch the hallucination.
  const fakeFetch: any = async () => ({
    ok: true,
    status: 200,
    json: async () => expected,
  });
  fakeFetch.json = async () => expected;

  const originalFetch = globalThis.fetch;
  globalThis.fetch = fakeFetch;
  try {
    const result = await fetchUser('u-1');
    assert.deepEqual(result, expected);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
