import { test } from 'node:test';
import assert from 'node:assert';
import { toJsonLines } from '../../parser.ts';

test('emits one JSON object per parsed line', () => {
  const out = toJsonLines('2024-05-08T12:34:56Z [INFO] hello\n2024-05-08T12:34:57Z [WARN] uh');
  const lines = out.split('\n').filter((l) => l.length > 0);
  assert.equal(lines.length, 2);
  const first = JSON.parse(lines[0]);
  assert.equal(first.level, 'INFO');
  assert.equal(first.msg, 'hello');
  assert.equal(first.ts, Date.parse('2024-05-08T12:34:56Z'));
});

test('skips lines that do not parse', () => {
  const out = toJsonLines('garbage\n2024-05-08T12:34:56Z [INFO] real');
  const lines = out.split('\n').filter((l) => l.length > 0);
  assert.equal(lines.length, 1);
});
