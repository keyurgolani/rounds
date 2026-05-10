import { describe, it, expect } from 'vitest';
import {
  detectIndentUnit,
  inferIndentForNewLines,
  matchIndentStyle,
  normaliseProposedWhitespace,
  preserveOriginalWhitespace,
} from '../../components/ai/AIChatPanel';

describe('detectIndentUnit', () => {
  it('IGNORES docstring indentation (the wordcount.py regression)', () => {
    // Real wordcount.py from the seed — module docstring uses 2-space
    // indent for its spec lines, function body uses 4-space. Without
    // the docstring filter, min-width detection returns 2 → matchIndent
    // halves the model's correct 4-space output → Python is destroyed.
    const py = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping each lowercased word to its',
      '  count. Words are split on whitespace, lowercased, then stripped of',
      '  any leading/trailing punctuation (use string.punctuation).',
      '"""',
      '',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower()',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    expect(detectIndentUnit(py)).toBe('    ');
  });

  it("handles single-quoted ''' docstrings the same as triple-double", () => {
    const py = [
      "'''Header.",
      '  spec line at 2 spaces',
      "'''",
      'def f():',
      '    return 1',
    ].join('\n');
    expect(detectIndentUnit(py)).toBe('    ');
  });

  it('detects 4-space Python from {4, 8, 12} widths', () => {
    // The regression we're guarding against: previous logic picked 2
    // because 4, 8, 12 are all divisible by 2. Should pick 4.
    const py = [
      'def foo(x):',
      '    if x:',
      '        return x',
      '    return 0',
    ].join('\n');
    expect(detectIndentUnit(py)).toBe('    ');
  });

  it('detects 2-space JS from {2, 4, 6} widths', () => {
    const js = [
      'function foo(x) {',
      '  if (x) {',
      '    return x;',
      '  }',
      '  return 0;',
      '}',
    ].join('\n');
    expect(detectIndentUnit(js)).toBe('  ');
  });

  it('detects tabs when tab-indented lines dominate', () => {
    const tabs = ['def foo():', '\tx = 1', '\treturn x'].join('\n');
    expect(detectIndentUnit(tabs)).toBe('\t');
  });

  it('returns null when no lines are indented', () => {
    expect(detectIndentUnit('a = 1\nb = 2\nc = 3')).toBeNull();
  });

  it('handles deeply-nested-only files (e.g. starts at indent 8)', () => {
    // First indented line is 8 spaces — we should still pick 4 if a
    // deeper line gives us 12 (smallest width is 8 in this case so
    // we pick 8, not ideal but predictable).
    const py = ['x = 1', '        y = 2', '            z = 3'].join('\n');
    // Width 8 is the smallest indented width; that's our unit.
    expect(detectIndentUnit(py)).toBe('        ');
  });
});

describe('matchIndentStyle', () => {
  const py4 = ['def foo():', '    return 1'].join('\n');

  it('no-ops when styles already match', () => {
    const proposed = ['def foo():', '    return 2'].join('\n');
    expect(matchIndentStyle(py4, proposed)).toBe(proposed);
  });

  it('rewrites 2-space proposed to 4-space when original is 4-space', () => {
    const proposed = ['def foo():', '  return 2'].join('\n');
    expect(matchIndentStyle(py4, proposed)).toBe(
      ['def foo():', '    return 2'].join('\n'),
    );
  });

  it('rewrites tab-indented proposed to 4-space when original is 4-space', () => {
    const proposed = ['def foo():', '\treturn 2', '\tif x:', '\t\treturn 3'].join(
      '\n',
    );
    expect(matchIndentStyle(py4, proposed)).toBe(
      ['def foo():', '    return 2', '    if x:', '        return 3'].join('\n'),
    );
  });

  it('preserves the prose body verbatim — only leading whitespace changes', () => {
    const original = ['def foo():', '    x = "  spaces in string  "'].join('\n');
    const proposed = ['def foo():', '  x = "  spaces in string  "'].join('\n');
    const result = matchIndentStyle(original, proposed);
    // The leading spaces are normalized (2 → 4) but the in-string
    // whitespace stays exactly as-is.
    expect(result).toBe(
      ['def foo():', '    x = "  spaces in string  "'].join('\n'),
    );
  });

  it('returns proposed unchanged when original has no indent baseline', () => {
    const proposed = ['def foo():', '    return 1'].join('\n');
    expect(matchIndentStyle('x = 1', proposed)).toBe(proposed);
  });

  it('does NOT mangle 4-space code when original has 2-space docstring spec lines', () => {
    // The end-to-end wordcount.py case: original docstring uses 2-space
    // indents for spec lines but the code body uses 4-space. The model
    // emits proper 4-space code. matchIndentStyle must NOT halve it just
    // because the docstring detection used to fool min-width.
    const original = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping words to counts.',
      '"""',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower()',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    const proposed = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping words to counts.',
      '"""',
      'import string',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower().strip(string.punctuation)',
      '        if key:',
      '            out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    // wantUnit and haveUnit should both be 4 → no-op (proposed returned verbatim)
    expect(matchIndentStyle(original, proposed)).toBe(proposed);
  });
});

describe('preserveOriginalWhitespace', () => {
  it('restores docstring indent halved by the model (the wordcount.py case)', () => {
    // The exact case observed in Chrome DevTools today: model returned
    // wordcount.py with docstring spec lines indented 1-space instead
    // of 2-space, every other line byte-identical. Without this pass
    // the user accepts and the docstring formatting is silently mangled.
    const original = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping each lowercased word to its',
      '  count. Words are split on whitespace, lowercased.',
      '"""',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    return {}',
    ].join('\n');
    const proposed = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      ' count(text) returns a dict mapping each lowercased word to its',
      ' count. Words are split on whitespace, lowercased.',
      '"""',
      'import string',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    return {}',
    ].join('\n');
    const fixed = preserveOriginalWhitespace(original, proposed);
    // Docstring lines restored to 2-space leading.
    expect(fixed).toContain('  count(text) returns');
    expect(fixed).toContain('  count. Words are split on');
    // The genuinely-new line ('import string') is preserved.
    expect(fixed).toContain('import string');
  });

  it('does not touch lines whose body content actually changed', () => {
    const original = ['def f():', '    return 1'].join('\n');
    const proposed = ['def f():', '    return 2'].join('\n');
    // Line "return 2" is genuinely new content — should NOT match
    // "return 1" by trim and stay as-is.
    expect(preserveOriginalWhitespace(original, proposed)).toBe(proposed);
  });

  it('leaves blank lines alone', () => {
    const original = ['a = 1', '', 'b = 2'].join('\n');
    const proposed = ['a = 1', '   ', 'b = 2'].join('\n');
    // Blank lines (only whitespace) shouldn't be content-matched.
    const result = preserveOriginalWhitespace(original, proposed);
    expect(result.split('\n')[1]).toBe('   ');
  });

  it('leaves ambiguous content alone (multiple originals match)', () => {
    // If two original lines have the same trimmed body, we can't pick
    // which lead is "right" — pass through verbatim.
    const original = ['  pass', '    pass'].join('\n');
    const proposed = ['pass', 'pass'].join('\n');
    const result = preserveOriginalWhitespace(original, proposed);
    expect(result).toBe(proposed);
  });

  it('idempotent — applying twice = applying once', () => {
    const original = ['  count(text)', 'def f():', '    return 1'].join('\n');
    const proposed = [' count(text)', 'def f():', '    return 1'].join('\n');
    const once = preserveOriginalWhitespace(original, proposed);
    const twice = preserveOriginalWhitespace(original, once);
    expect(twice).toBe(once);
  });

  it('END-TO-END: word-count-py with mangled 16/32-space output', () => {
    // The exact scenario captured via Chrome DevTools on 2026-05-10:
    // model returned the file with bizarrely mangled indentation —
    // 16 spaces for level-1 lines, 32 spaces for level-2, 1 space for
    // some new lines. Pre-fix: matchIndentStyle inflated everything 4x
    // and produced unusable Python. Post-fix: preserveOriginalWhitespace
    // restores every line whose body matches the original.
    const original = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping each lowercased word to its',
      '"""',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower()',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    const mangledProposed = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      ' count(text) returns a dict mapping each lowercased word to its',
      '"""',
      'import string',
      '',
      'def count(text: str) -> dict[str, int]:',
      '                out: dict[str, int] = {}',  // 16 spaces (model garbage)
      '                for w in text.split():',     // 16
      ' key = w.lower().strip(string.punctuation)',  // 1 space (new line)
      ' if key:',                                     // 1 space (new line)
      '                                out[key] = out.get(key, 0) + 1',  // 32
      '                return out',                  // 16
    ].join('\n');
    const fixed = preserveOriginalWhitespace(original, mangledProposed);
    const lines = fixed.split('\n');
    // Docstring spec line restored from 1-space → 2-space.
    expect(lines[3]).toBe('  count(text) returns a dict mapping each lowercased word to its');
    // Code body lines whose body is unchanged are restored to 4/4/8/4.
    expect(lines[8]).toBe('    out: dict[str, int] = {}');
    expect(lines[9]).toBe('    for w in text.split():');
    expect(lines[12]).toBe('        out[key] = out.get(key, 0) + 1');
    expect(lines[13]).toBe('    return out');
    // The genuinely-new lines (key=...strip, if key:) stay at the
    // model's lead — preserveOriginalWhitespace can't infer the right
    // indent for them. inferIndentForNewLines (tested below) handles
    // those, and normaliseProposedWhitespace composes both passes.
  });
});

describe('inferIndentForNewLines', () => {
  it('fixes 1-space NEW lines using block-opener context (wordcount.py case)', () => {
    // The exact Chrome-DevTools-captured case: model emits two new
    // lines with 1-space lead. preserveOriginalWhitespace can't fix
    // them (no body match in original). This pass infers the correct
    // 8-space lead from the parent `for w in text.split():` opener.
    const original = [
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower()',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    // After preserveOriginalWhitespace ran, preserved lines have their
    // original leads. The two new lines (`key=...strip`, `if key:`)
    // remain at 1 space — the model garbage we need to fix.
    const afterPreserve = [
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      ' key = w.lower().strip(string.punctuation)',
      ' if key:',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    const fixed = inferIndentForNewLines(original, afterPreserve);
    const lines = fixed.split('\n');
    // First new line: parent `for ...` opens block, expected 4+4=8.
    expect(lines[3]).toBe('        key = w.lower().strip(string.punctuation)');
    // Second new line: previous (key=...) doesn't open block, sibling at 8.
    expect(lines[4]).toBe('        if key:');
    // Preserved lines unchanged.
    expect(lines[5]).toBe('        out[key] = out.get(key, 0) + 1');
    expect(lines[6]).toBe('    return out');
  });

  it('preserves a deliberate dedent (else: clause) on a new line', () => {
    // Model adds an `else:` branch. The else: is a NEW line at depth
    // 0 — same as the `if`. Naive context-inference would over-indent
    // it to 4 (sibling of the previous body line at depth 4). The
    // "cleanMultiple + only-override-when-suspicious" rule must let
    // legitimate dedents through.
    const original = [
      'if x:',
      '    do_thing()',
    ].join('\n');
    const proposed = [
      'if x:',
      '    do_thing()',
      'else:',
      '    do_other()',
    ].join('\n');
    const fixed = inferIndentForNewLines(original, proposed);
    expect(fixed).toBe(proposed);
  });

  it('infers JS new-line indent from { block opener', () => {
    const original = [
      'function foo() {',
      '  return 1;',
      '}',
    ].join('\n');
    // Model adds a body line at 0-space (mangled).
    const afterPreserve = [
      'function foo() {',
      'console.log("added");',
      '  return 1;',
      '}',
    ].join('\n');
    const fixed = inferIndentForNewLines(original, afterPreserve);
    const lines = fixed.split('\n');
    expect(lines[1]).toBe('  console.log("added");');
  });

  it('overrides obviously over-indented new lines (one-extra-level cap)', () => {
    // Model emits a new sibling line one level too deep (e.g. 8 when
    // 4 is expected). tooDeep heuristic catches this.
    const original = ['def f():', '    a = 1'].join('\n');
    // After preserve, the original a=1 stays. Model also added a new
    // `b = 2` at depth 8 (over-indented).
    const afterPreserve = ['def f():', '    a = 1', '        b = 2'].join('\n');
    const fixed = inferIndentForNewLines(original, afterPreserve);
    expect(fixed.split('\n')[2]).toBe('    b = 2');
  });

  it('leaves new lines alone when their lead is already correct', () => {
    const original = ['def f():', '    return 1'].join('\n');
    const proposed = ['def f():', '    x = 2', '    return 1'].join('\n');
    const fixed = inferIndentForNewLines(original, proposed);
    expect(fixed).toBe(proposed);
  });

  it('no-ops when original has no detectable indent unit', () => {
    const original = 'x = 1';
    const proposed = ['x = 1', ' y = 2'].join('\n');
    expect(inferIndentForNewLines(original, proposed)).toBe(proposed);
  });

  it("doesn't touch lines inside docstrings", () => {
    const original = [
      '"""Header.',
      '  spec line at 2 spaces',
      '"""',
      'def f():',
      '    return 1',
    ].join('\n');
    // Model added a new docstring line at 1-space lead (intentional).
    const proposed = [
      '"""Header.',
      ' new spec line at 1 space',
      '  spec line at 2 spaces',
      '"""',
      'def f():',
      '    return 1',
    ].join('\n');
    const fixed = inferIndentForNewLines(original, proposed);
    // Docstring interior must stay verbatim — re-indenting would
    // mutate the string's payload.
    expect(fixed).toBe(proposed);
  });
});

describe('normaliseProposedWhitespace (composed pipeline)', () => {
  it('END-TO-END: word-count-py mangled output → fully clean Python', () => {
    // The full failing case from production: model returns wordcount.py
    // with bizarrely mangled indentation (16/32 on preserved lines,
    // 1-space on new lines). The composed pipeline restores preserved
    // lines AND infers new-line leads from context. Result: every line
    // that the heuristic CAN fix is fixed; the only structural
    // limitation is when a preserved line should now nest deeper into
    // a newly-added block (out[key] should be 12 inside the new
    // `if key:`), which requires real Python parsing to detect.
    const original = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      '  count(text) returns a dict mapping each lowercased word to its',
      '"""',
      '',
      'def count(text: str) -> dict[str, int]:',
      '    out: dict[str, int] = {}',
      '    for w in text.split():',
      '        key = w.lower()',
      '        out[key] = out.get(key, 0) + 1',
      '    return out',
    ].join('\n');
    const mangledProposed = [
      '"""Word-frequency counter.',
      '',
      'Spec:',
      ' count(text) returns a dict mapping each lowercased word to its',
      '"""',
      'import string',
      '',
      'def count(text: str) -> dict[str, int]:',
      '                out: dict[str, int] = {}',
      '                for w in text.split():',
      ' key = w.lower().strip(string.punctuation)',
      ' if key:',
      '                                out[key] = out.get(key, 0) + 1',
      '                return out',
    ].join('\n');
    const fixed = normaliseProposedWhitespace(original, mangledProposed);
    const lines = fixed.split('\n');
    // Docstring spec restored from 1-space → 2-space.
    expect(lines[3]).toBe('  count(text) returns a dict mapping each lowercased word to its');
    // New top-level import sits at 0-space (cleanMultiple → kept).
    expect(lines[5]).toBe('import string');
    // Preserved code-body lines back to original leads.
    expect(lines[8]).toBe('    out: dict[str, int] = {}');
    expect(lines[9]).toBe('    for w in text.split():');
    // The two NEW lines: parent `for ...:` opens block → 4+4=8.
    expect(lines[10]).toBe('        key = w.lower().strip(string.punctuation)');
    expect(lines[11]).toBe('        if key:');
    // Preserved trailing lines.
    expect(lines[12]).toBe('        out[key] = out.get(key, 0) + 1');
    expect(lines[13]).toBe('    return out');
  });

  it('idempotent — second pass is a no-op', () => {
    const original = [
      'def f():',
      '    if x:',
      '        return 1',
    ].join('\n');
    const mangled = [
      'def f():',
      '    if x:',
      ' new_line()',
      '        return 1',
    ].join('\n');
    const once = normaliseProposedWhitespace(original, mangled);
    const twice = normaliseProposedWhitespace(original, once);
    expect(twice).toBe(once);
  });
});
