import { test } from 'node:test';
import assert from 'node:assert';
import { parseLine, parseAll } from '../../parser.ts';

const UTC_TS = Date.UTC(2024, 4, 8, 12, 34, 56); // 2024-05-08T12:34:56Z

test('parses a UTC timestamp', () => {
  const r = parseLine('2024-05-08T12:34:56Z [INFO] hello');
  assert.equal(r?.ts, UTC_TS);
  assert.equal(r?.level, 'INFO');
  assert.equal(r?.msg, 'hello');
});

test('parses multiple lines and produces UTC timestamps', () => {
  const out = parseAll('2024-05-08T12:34:56Z [INFO] a\n2024-05-08T12:34:57Z [WARN] b');
  assert.equal(out.length, 2);
  assert.equal(out[0].ts, UTC_TS);
  assert.equal(out[1].ts, Date.UTC(2024, 4, 8, 12, 34, 57));
  assert.equal(out[0].level, 'INFO');
  assert.equal(out[1].level, 'WARN');
});

test('returns null for non-matching line, but still parses valid line in batch', () => {
  assert.equal(parseLine('garbage'), null);
  // Mix valid and invalid: invalid is filtered, valid keeps its UTC timestamp.
  const out = parseAll('garbage\n2024-05-08T12:34:56Z [INFO] real');
  assert.equal(out.length, 1);
  assert.equal(out[0].ts, UTC_TS);
});
