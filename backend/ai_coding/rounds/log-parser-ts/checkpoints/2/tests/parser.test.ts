import { test } from 'node:test';
import assert from 'node:assert';
import { parseStream, parseAll, type LogLine } from '../../parser.ts';

function* lineSource(input: string): Iterable<string> {
  for (const line of input.split('\n')) yield line;
}

test('parseStream yields parsed lines lazily', () => {
  const src = lineSource('2024-05-08T12:34:56Z [INFO] a\n2024-05-08T12:34:57Z [WARN] b');
  const out: LogLine[] = [];
  for (const line of parseStream(src)) out.push(line);
  assert.equal(out.length, 2);
  assert.equal(out[0].level, 'INFO');
});

test('parseAll still works as a thin wrapper', () => {
  const out = parseAll('2024-05-08T12:34:56Z [INFO] only');
  assert.equal(out.length, 1);
});

test('parseStream skips invalid lines', () => {
  const src = lineSource('garbage\n2024-05-08T12:34:56Z [INFO] real');
  const out = [...parseStream(src)];
  assert.equal(out.length, 1);
});

test('parseStream is lazy — does not exhaust the iterable upfront', () => {
  let pulled = 0;
  function* counted(): Iterable<string> {
    while (true) {
      pulled++;
      yield '2024-05-08T12:34:56Z [INFO] x';
    }
  }
  const it = parseStream(counted())[Symbol.iterator]();
  it.next();
  it.next();
  it.next();
  // We pulled 3 lines; an eager implementation would have pulled all of
  // them (infinite loop) or many more. Allow up to 4 to tolerate any
  // single-line lookahead a sensible implementation might do.
  assert.ok(pulled <= 4, `parseStream pulled ${pulled} lines for 3 next() calls`);
});
