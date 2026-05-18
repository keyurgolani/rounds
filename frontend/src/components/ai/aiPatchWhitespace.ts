/**
 * Whitespace-normalisation helpers for AI-emitted patch contents.
 *
 * These exist because models routinely mangle indentation when they
 * regenerate files — docstring leads get halved, newly-added lines
 * get one-space leads, etc. We run a two-pass normalisation any time
 * a patch arrives (live stream, page rehydrate, apply-time) so the
 * diff card the user reviews matches what's actually written to disk.
 *
 * The functions are pure; they're separated from AIChatPanel.tsx so
 * the chat presentation layer can be a thin wrapper around the
 * generic ChatPanel without dragging 400 lines of text utilities
 * along.
 */

/**
 * For every line in `text`, returns whether that line STARTED inside
 * a triple-quoted string (Python `"""…"""` or `'''…'''`). Used to
 * exclude docstring/multi-line-string content from indent detection
 * — the leading whitespace of those lines is part of the string's
 * payload, not a representation of the file's code indent style.
 *
 * Why this matters: a Python file with a docstring like
 *   """Header.
 *
 *   Spec:
 *     count(text) → ...
 *   """
 * has indented lines at width 2 INSIDE the docstring and width 4
 * inside `def`. Min-width detection without this filter picks 2,
 * which then causes matchIndentStyle to halve the model's correct
 * 4-space output and break the function body. Skipping docstring
 * interior lines fixes both detection and re-indentation.
 *
 * Toggle is naïve (doesn't model raw / b strings, escape sequences,
 * or single-line `"""x"""` strings perfectly) but covers the common
 * Python module-docstring case that breaks indent detection.
 */
function isInsideTripleQuotes(text: string): boolean[] {
  const lines = text.split('\n');
  const out: boolean[] = [];
  let inside = false;
  for (const line of lines) {
    const startedInside = inside;
    let i = 0;
    while (i <= line.length - 3) {
      const slice = line.slice(i, i + 3);
      if (slice === '"""' || slice === "'''") {
        inside = !inside;
        i += 3;
      } else {
        i += 1;
      }
    }
    out.push(startedInside);
  }
  return out;
}

/**
 * Detects the indent style ("\t" or N spaces) used by `text` and
 * returns the unit string. Strategy: the SMALLEST non-zero leading
 * whitespace width across all CODE lines (lines outside triple-quoted
 * strings) is the unit. 4-space Python with widths {4, 8, 12} → 4;
 * 2-space JS with {2, 4, 6} → 2.
 */
export function detectIndentUnit(text: string): string | null {
  const lines = text.split('\n');
  const insideStr = isInsideTripleQuotes(text);
  let tabLines = 0;
  let spaceLines = 0;
  let minSpaceWidth = Infinity;
  for (let i = 0; i < lines.length; i++) {
    if (insideStr[i]) continue;
    const line = lines[i];
    if (!line || /^\s*$/.test(line)) continue;
    const m = line.match(/^([ \t]+)/);
    if (!m) continue;
    const lead = m[1];
    if (lead.includes('\t') && lead.includes(' ')) continue;
    if (lead[0] === '\t') {
      tabLines += 1;
    } else {
      spaceLines += 1;
      if (lead.length < minSpaceWidth) minSpaceWidth = lead.length;
    }
  }
  if (tabLines > 0 && tabLines >= spaceLines) return '\t';
  if (spaceLines === 0 || minSpaceWidth === Infinity) return null;
  return ' '.repeat(minSpaceWidth);
}

/**
 * Content-preserving whitespace pass. For each line in `proposed`,
 * if its trimmed body uniquely matches a line in `original`, restore
 * the original's leading whitespace. Only touches lines that
 * unambiguously survive the patch — new lines, modified lines, and
 * lines that appear multiple times in the original (where matching
 * is ambiguous) are passed through verbatim.
 */
export function preserveOriginalWhitespace(
  original: string,
  proposed: string,
): string {
  const oLines = original.split('\n');
  const pLines = proposed.split('\n');
  const trimmedToLead = new Map<string, string | null>();
  for (const o of oLines) {
    const trimmed = o.trimStart();
    if (!trimmed) continue;
    const lead = o.slice(0, o.length - trimmed.length);
    if (trimmedToLead.has(trimmed)) {
      trimmedToLead.set(trimmed, null);
    } else {
      trimmedToLead.set(trimmed, lead);
    }
  }
  return pLines
    .map((line) => {
      const trimmed = line.trimStart();
      if (!trimmed) return line;
      const wantLead = trimmedToLead.get(trimmed);
      if (wantLead == null) return line;
      const haveLead = line.slice(0, line.length - trimmed.length);
      if (haveLead === wantLead) return line;
      return wantLead + trimmed;
    })
    .join('\n');
}

/**
 * Second-pass indent fixer for the lines `preserveOriginalWhitespace`
 * couldn't help — the genuinely-new lines (no body match in original).
 * Walks proposed top-to-bottom and rewrites suspicious leads using a
 * block-opener heuristic for context.
 */
export function inferIndentForNewLines(
  original: string,
  proposed: string,
): string {
  const indentUnit = detectIndentUnit(original);
  if (!indentUnit) return proposed;
  const unitWidth = indentUnit === '\t' ? 1 : indentUnit.length;

  const oLines = original.split('\n');
  const trimmedToLead = new Map<string, string | null>();
  for (const o of oLines) {
    const trimmed = o.trimStart();
    if (!trimmed) continue;
    const lead = o.slice(0, o.length - trimmed.length);
    if (trimmedToLead.has(trimmed)) trimmedToLead.set(trimmed, null);
    else trimmedToLead.set(trimmed, lead);
  }

  const pLines = proposed.split('\n');
  const insideStr = isInsideTripleQuotes(proposed);
  const effectiveLeads: string[] = new Array(pLines.length).fill('');
  const result: string[] = new Array(pLines.length);

  for (let i = 0; i < pLines.length; i++) {
    const line = pLines[i];
    const trimmed = line.trimStart();
    const haveLead = line.slice(0, line.length - trimmed.length);

    if (!trimmed || insideStr[i]) {
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    const wantLead = trimmedToLead.get(trimmed);
    if (wantLead != null) {
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    let j = i - 1;
    while (j >= 0 && (!pLines[j].trim() || insideStr[j])) j--;
    if (j < 0) {
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    const prevLead = effectiveLeads[j];
    const prevTrimmed = pLines[j].trimStart();
    const prevNoComment = prevTrimmed
      .replace(/\s*\/\/.*$/, '')
      .replace(/\s*#.*$/, '')
      .trimEnd();
    const opensBlock =
      prevNoComment.endsWith(':') ||
      prevNoComment.endsWith('{') ||
      prevNoComment.endsWith('(') ||
      prevNoComment.endsWith('[') ||
      prevNoComment.endsWith('=>');

    const expectedLead = opensBlock ? prevLead + indentUnit : prevLead;

    const cleanMultiple =
      indentUnit === '\t'
        ? haveLead === '' || /^\t+$/.test(haveLead)
        : haveLead.length % unitWidth === 0 && !haveLead.includes('\t');
    const tooShallow = opensBlock && haveLead.length < expectedLead.length;
    const tooDeep = haveLead.length > expectedLead.length;

    const finalLead =
      !cleanMultiple || tooShallow || tooDeep ? expectedLead : haveLead;

    result[i] = finalLead + trimmed;
    effectiveLeads[i] = finalLead;
  }

  return result.join('\n');
}

/**
 * Compose the two whitespace-fixing passes used everywhere we accept
 * model-emitted patch contents. Idempotent — running it twice produces
 * the same result.
 */
export function normaliseProposedWhitespace(
  original: string,
  proposed: string,
): string {
  const preserved = preserveOriginalWhitespace(original, proposed);
  return inferIndentForNewLines(original, preserved);
}

/**
 * If `proposed` was emitted with a different indent style than
 * `original`, rewrite proposed's leading whitespace so it matches
 * original's unit. No-op when styles agree or when either side has no
 * indented lines.
 */
export function matchIndentStyle(original: string, proposed: string): string {
  const wantUnit = detectIndentUnit(original);
  const haveUnit = detectIndentUnit(proposed);
  if (!wantUnit || !haveUnit || wantUnit === haveUnit) return proposed;
  const haveIsTab = haveUnit === '\t';
  const haveStep = haveIsTab ? 1 : haveUnit.length;
  const lines = proposed.split('\n');
  const insideStr = isInsideTripleQuotes(proposed);
  return lines
    .map((line, i) => {
      if (insideStr[i]) return line;
      const m = line.match(/^([ \t]+)/);
      if (!m) return line;
      const lead = m[1];
      if (lead.includes('\t') && lead.includes(' ')) return line;
      const steps = haveIsTab
        ? lead.length
        : Math.floor(lead.length / haveStep);
      const leftover = haveIsTab ? 0 : lead.length % haveStep;
      const rest = line.slice(lead.length);
      return wantUnit.repeat(steps) + ' '.repeat(leftover) + rest;
    })
    .join('\n');
}
