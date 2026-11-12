// The leaf DAG (ROUNDS-01-L03 S2, DR-0003 decisions P1, P11, P13): reads the
// committed issue export (docs/program/issue-export.json), parses each
// issue's "Exact prerequisite leaf issues" section into edges, adds the
// stage lists and program fields of docs/program/leaf-program.json, and
// builds docs/program/leaf-dag.json. The conformance rule
// scripts/conformance/rules/program.mjs regenerates it in memory and fails
// on drift, so the committed DAG is always this function of its two inputs.
// Node built-ins only; nothing here calls GitHub.
//
// TODO(ROUNDS-01-L03): after re-authorization item 6 the catalog carries
// each leaf's phase, milestone, and stages, and its export replaces
// leaf-program.json's draft fields under a new DR-0003 revision.

import { canonical, finding, jsonLine, sha256 } from '../conformance/lib/context.mjs';
import { validate } from '../conformance/lib/json-schema.mjs';
import { LEAF_IDS_PATH, loadLeafIds } from '../conformance/lib/leaf-ids.mjs';
import { prettyJson } from '../conformance/lib/pretty-json.mjs';

export const EXPORT_PATH = 'docs/program/issue-export.json';
export const EXPORT_SCHEMA = 'docs/program/issue-export.schema.json';
export const INPUTS_PATH = 'docs/program/leaf-program.json';
export const INPUTS_SCHEMA = 'docs/program/leaf-program.schema.json';
export const DAG_PATH = 'docs/program/leaf-dag.json';
export const DAG_SCHEMA = 'docs/program/leaf-dag.schema.json';
export const SECTION = 'Exact prerequisite leaf issues';
export const STAGE_ID = /^[A-Za-z0-9.]+$/;

// ------------------------------------------------------------ export

// The section's text in an issue body: from its heading to the next heading
// of the same or a higher level. Returns null when the body has no section.
export function prerequisiteSection(body) {
  const lines = String(body || '').replace(/\r\n/g, '\n').split('\n');
  const start = lines.findIndex((l) => /^#{2,4} /.test(l) && l.replace(/^#+ /, '').trim() === SECTION);
  if (start < 0) return null;
  const level = lines[start].match(/^#+/)[0].length;
  const out = [];
  for (let i = start + 1; i < lines.length; i++) {
    const m = /^(#+) /.exec(lines[i]);
    if (m && m[1].length <= level) break;
    out.push(lines[i]);
  }
  return out.join('\n').trim();
}

export const exportDigest = (issues) => sha256(canonical(issues));

// Trims `gh issue list --json number,title,body` output to the export: each
// issue's number, title, and prerequisite section, nothing else from the body.
export function trimExport(raw, { repo, exportedOn }) {
  if (!Array.isArray(raw)) throw new Error('the gh output is not a JSON array');
  const issues = raw.map((i) => {
    if (!Number.isInteger(i?.number) || typeof i?.title !== 'string' || typeof i?.body !== 'string') throw new Error('every issue needs number, title, and body');
    const prerequisites = prerequisiteSection(i.body);
    return { number: i.number, title: i.title, prerequisites };
  }).sort((a, b) => a.number - b.number);
  return {
    $schema: './issue-export.schema.json',
    description: `The "${SECTION}" section of each filed issue, as GitHub held it on exportedOn, trimmed by scripts/program/export.mjs. scripts/program/dag.mjs builds leaf-dag.json from it, so CI never reads GitHub. sha256 covers the issues array (canonical JSON); refresh both with the command below and export.mjs.`,
    source: { repo, command: `gh issue list --repo ${repo} --state all --limit 300 --json number,title,body`, exportedOn, section: SECTION },
    sha256: exportDigest(issues),
    issues,
  };
}

// ------------------------------------------------------------ section parser

// Stage tokens as bodies write them: S3, stage 3, Stage 1b, Stage A, PR 2.
const STAGE_TOKEN = /(?:[Ss]tages?\s+|\bS(?=\d)|\bPRs?\s+)([0-9]+[a-z]?|[A-H](?![A-Za-z]))/y;
const LIST_JOIN = /\s*(?:\([^()]*\)\s*)?(?:,\s*(?:and\s+)?|\s+and\s+|\s+or\s+|\s+to\s+)/y;
const BARE_STAGE = /(?:[Ss]tages?\s+|\bS(?=\d)|\bPRs?\s+)?([0-9]+[a-z]?|[A-H](?![A-Za-z]))/y;

// Reads "stage 1", "stages 0 (inventory) and 2", "S1 and S2", "Stages 0 to 3
// and 5" at text[pos]. Returns { tokens: [{ kind, value }], ranges, end } or null.
export function readStageList(text, pos) {
  STAGE_TOKEN.lastIndex = pos;
  const first = STAGE_TOKEN.exec(text);
  if (!first) return null;
  const kind = /^PR/.test(first[0]) ? 'P' : 'S';
  const tokens = [{ kind, value: first[1] }];
  let end = STAGE_TOKEN.lastIndex;
  for (;;) {
    LIST_JOIN.lastIndex = end;
    const j = LIST_JOIN.exec(text);
    if (!j) break;
    BARE_STAGE.lastIndex = LIST_JOIN.lastIndex;
    const next = BARE_STAGE.exec(text);
    if (!next || !/^(?:[Ss]tages?\s+|S|PRs?\s+)?[0-9A-H]/.test(next[0])) break;
    // A bare letter only continues a list of letters, a bare number one of numbers.
    if (!/^(?:[Ss]tage|S|PR)/.test(next[0]) && /^\d/.test(next[1]) !== /^\d/.test(tokens[tokens.length - 1].value)) break;
    const range = /\s+to\s+$/.test(j[0]);
    tokens.push({ kind: /^PR/.test(next[0]) ? 'P' : kind, value: next[1], range });
    end = BARE_STAGE.lastIndex;
  }
  return { tokens, end };
}

// Stage id for a token on a leaf: S<n>, S<letter>, P<n>, or the bare number
// for leaves whose PRs are labeled by number (decision X4).
export function stageId(token, numbered) {
  if (numbered && /^\d/.test(token.value)) return token.value;
  if (token.kind === 'P') return `P${token.value}`;
  return `S${token.value}`;
}

// A curated list may alias a stage a body names to the stages it covers
// ("stage 1" of a leaf staged 1a and 1b).
export function applyAliases(ids, entry) {
  if (!entry?.aliases) return ids;
  return [...new Set(ids.flatMap((s) => entry.aliases[s] || [s]))];
}

// Expands a token list into stage ids, with "a to b" ranges resolved over
// the leaf's known stages (or over integers when none are known).
export function expandTokens(tokens, numbered, known = []) {
  const out = [];
  tokens.forEach((t, i) => {
    const id = stageId(t, numbered);
    if (t.range && out.length) {
      const from = out[out.length - 1];
      const order = known.length ? known : null;
      if (order && order.includes(from) && order.includes(id)) {
        for (const s of order.slice(order.indexOf(from) + 1, order.indexOf(id) + 1)) out.push(s);
        return;
      }
      const a = Number(String(from).replace(/^[SP]/, ''));
      const b = Number(String(id).replace(/^[SP]/, ''));
      if (Number.isInteger(a) && Number.isInteger(b) && b > a) {
        const prefix = String(id).match(/^[SP]?/)[0];
        for (let k = a + 1; k <= b; k++) out.push(`${prefix}${k}`);
        return;
      }
    }
    out.push(id);
  });
  return [...new Set(out)];
}

// A block or clause that starts like this lists leaves that are not this
// leaf's prerequisites (downstream, transitive, dropped, rollout-only); the
// rest of the block is skipped.
export const SKIP_BLOCK = /^(?:downstream|blocks\b|this leaf (?:is|becomes) a prerequisite|transitive|via\b|dropped|dropped generator edges|[^:.]*\bnot (?:merge )?(?:edges|blockers|prerequisites)\b|adopted in place|soft edges|state gates only|not blocking|rollout gate only|paper-fetch pr only|stage gates, not edges|stage \d+ gates, not merge edges|coordination\b|asks:|section gates\b|[^:.]*\bonly the clos(?:e|ure)\b|[^:.]*\bedges onto this leaf\b|closure edges|removed\b|order:|soft\b)/i;
// A clause that says something other than "this leaf needs X".
export const SKIP_CLAUSE = new RegExp([
  String.raw`\bdownstream\b`, String.raw`\bis a prerequisite of\b`, String.raw`\bbecomes a prerequisite of\b`, String.raw`\bthis leaf blocks\b`,
  String.raw`\barrives? through\b`, String.raw`\bcomes? through\b`, String.raw`\b(?:is|are|edges? (?:are|is)|edge is) dropped\b`, String.raw`\bdrops? (?:it|their|its|the)\b`,
  String.raw`^(?:never|not|all but|until)\s`, String.raw`\bships? (?:in|with)\b`, String.raw`^milestone \d+\b`, String.raw`^order\b`, String.raw`\bforward edges?\b`, String.raw`\bgenerator edges?\b`, String.raw`\bis a (?:section |rollout )?gate\b`, String.raw`^the\s+[\w\x60-]+\s+(?:flag|gate|key|switch)\b`, String.raw`\bgates? the opening\b`, String.raw`\bnot the merge\b`, String.raw`\bis downstream\b`, String.raw`\bgates? only\b`, String.raw`\bprecede\b`, String.raw`^lands?\b`, String.raw`\blands? before\b`, String.raw`\bisn't a prerequisite\b`, String.raw`\b(?:isn't|is not|aren't|are not) needed\b`, String.raw`\bmoves? (?:there|here) for\b`, String.raw`\bedges? goes? to\b`, String.raw`\bnot (?:a )?prerequisites?\b`, String.raw`\bnot edges\b`, String.raw`\bnot blocking\b`, String.raw`\bdoes not block\b`,
  String.raw`\bgate-only\b`, String.raw`\bis a rollout gate\b`, String.raw`\bare rollout gates\b`, String.raw`\bgates opening\b`, String.raw`\bmust (?:list|show)\b`,
  String.raw`\brecords? (?:both|the) edges?\b`, String.raw`\bas \x60?leaf-dag\.json\x60? in #17\b`, String.raw`\bfilled-in example\b`, String.raw`\bcloses? (?:after|when|before)\b`, String.raw`^it closes\b`,
].join('|'), 'i');
// "#N ... needs/depends on/waits on/takes ..." with another leaf as subject.
const SUBJECT = String.raw`(?:#\d+(?:\s+to\s+#\d+)?|\x60ROUNDS-[^\x60]+\x60)(?:\s*\([^()]*\))?(?:'s\s+(?:[Ss]tages?\s+\w+|[\w\x60-]+(?:\s+[\w\x60-]+){0,2}?)|\s+(?:[Ss]tages?\s+|S(?=\d)|PRs?\s+)\w+)?(?:\s*\([^()]*\))?`;
const OTHER_SUBJECT = new RegExp(String.raw`^(?:only\s+|and\s+)?${SUBJECT}(?:\s*(?:,\s*(?:and\s+)?|\s+and\s+|\s+or\s+)(?:\([^()]*\)\s*)?(?:parts? of\s+)?${SUBJECT})*,?\s+(?:also\s+|first\s+|then\s+|later\s+|only\s+)?(?:needs?|depends?\s+on|depend\s+on|waits?\s+(?:on|for)|wait\s+(?:on|for)|takes?|consumes?|runs?|feeds?|adopts?|packages|documents|lands?|stays?\s+ahead|generalizes|fills?|owns?|routes?|retires?|retire|leaves|keeps|gates|need|cites?|reads?|uses?|marks?|lists?|list|is|are|joins?|join|moves?|ships?|opens?|writes?|extends?|becomes?|become)\b`, 'i');

const REF = /#(\d+)(?:\s+to\s+#(\d+))?|`(ROUNDS-\d{2}[A-Z]?)-L(\d{2})(?:\/([A-Za-z0-9.]+))?`(?:\s+to\s+`(?:(ROUNDS-\d{2}[A-Z]?)-|-)?L(\d{2})`)?|`-?L(\d{2})`(?:\s+to\s+`-?L(\d{2})`)?/g;

// Leaf references in a clause, each with the stage list that qualifies it:
// "#1's stage 3", "#91 Stage 1", "#170 (`ROUNDS-34-L01`, harness) S2".
export function clauseRefs(text, issueLeaf, leafIssue) {
  const out = [];
  let lastCap = null;
  let prev = null;
  for (const m of text.matchAll(REF)) {
    const ids = [];
    let explicitStage = null;
    if (m[1]) {
      const a = Number(m[1]);
      const b = m[2] ? Number(m[2]) : a;
      for (let n = a; n <= b; n++) ids.push(issueLeaf.get(n) || `#${n}`);
    } else if (m[3]) {
      lastCap = m[3];
      const cap = m[6] || m[3];
      const a = Number(m[4]);
      const b = m[7] ? Number(m[7]) : a;
      for (let k = a; k <= b; k++) ids.push(`${k === a ? m[3] : cap}-L${String(k).padStart(2, '0')}`);
      explicitStage = m[5] || null;
    } else if (m[8] && lastCap) {
      const a = Number(m[8]);
      const b = m[9] ? Number(m[9]) : a;
      for (let k = a; k <= b; k++) ids.push(`${lastCap}-L${String(k).padStart(2, '0')}`);
    } else continue;
    // "#1 (`ROUNDS-00A-L01`, ...)": the backticked id repeats the issue number.
    const at = m.index;
    const pairsWithPrev = prev && !m[1] && ids.length === 1 && prev.ids.length === 1 && at - prev.end <= 3 && prev.ids[0] === ids[0];
    const pairsWithPrevReverse = prev && m[1] && ids.length === 1 && prev.ids.length === 1 && at - prev.end <= 3 && prev.ids[0] === ids[0];
    let end = at + m[0].length;
    // Qualifier: optional 's, optional parenthetical, optional comma or colon, then a stage list.
    let p = end;
    if (text.startsWith("'s", p)) p += 2;
    const skipWs = () => { while (p < text.length && /\s/.test(text[p])) p++; };
    skipWs();
    let inParen = null;
    if (text[p] === '(') {
      let depth = 0;
      let q = p;
      for (; q < text.length; q++) {
        if (text[q] === '(') depth++;
        else if (text[q] === ')') { depth--; if (depth === 0) break; }
      }
      // "#91 (`ROUNDS-18-L03`, export, Stage 1 only)": a stage list closing the parenthetical.
      const inner = text.slice(p + 1, q);
      const tail = /,\s*((?:[Ss]tages?\s+|S(?=\d)|PRs?\s+)[0-9A-H][0-9a-z]*)(?:\s+only)?\s*$/.exec(inner);
      if (tail) inParen = readStageList(tail[1], 0)?.tokens || null;
      // "#178 (1a and 1b)", "#73 (stage A)": a parenthetical that is only a stage list.
      else if (/^\s*(?:(?:[Ss]tages?\s+|S(?=\d)|PRs?\s+)?(?:\d+[a-z]?|[A-H])\s*(?:,\s*|\s+and\s+|\s+or\s+|$))+$/.test(inner)) {
        inParen = [...inner.matchAll(/(PRs?\s+)?(?:[Ss]tages?\s+|S(?=\d))?(\d+[a-z]?|\b[A-H]\b)/g)].map((m) => ({ kind: m[1] ? 'P' : 'S', value: m[2] }));
      }
      p = q + 1;
      skipWs();
    }
    // After a colon the stage list may name the prerequisite's stage
    // ("#1 (...): stage 3 only") or this leaf's ("#13 (...): S1"); the build
    // settles it from the curated stage lists.
    let afterColon = false;
    if (text[p] === ',' || text[p] === ':') { afterColon = text[p] === ':'; p++; skipWs(); }
    if (text.startsWith('its ', p)) p += 4;
    const list = readStageList(text, p);
    // "#178 1a caches and 1b commands": bare stage ids after the reference.
    const bare = !list && /^(\d+[a-z])\b(?:[^,;.()]*?\band\s+(\d+[a-z])\b)?/.exec(text.slice(p));
    const bareTokens = bare ? [bare[1], bare[2]].filter(Boolean).map((value) => ({ kind: 'S', value })) : null;
    const qualifier = (list && !/^\s*(?:[Ss]tages?|S|PRs?)\s*$/.test(text.slice(p, list.end)) ? list.tokens : null) || inParen || bareTokens;
    if (inParen && qualifier === inParen) afterColon = false;
    if (list) end = Math.max(end, list.end);
    if ((pairsWithPrev || pairsWithPrevReverse) && prev) {
      if (explicitStage && !prev.explicitStage) prev.explicitStage = explicitStage;
      if (qualifier && !prev.qualifier) { prev.qualifier = qualifier; prev.afterColon = afterColon; }
      prev.end = end;
      continue;
    }
    const ref = { ids, explicitStage, qualifier, afterColon: Boolean(qualifier) && afterColon, start: at, end };
    out.push(ref);
    prev = ref;
  }
  // Each reference's span runs to the next one, for phrase qualifiers.
  out.forEach((r, i) => { r.span = text.slice(r.start, out[i + 1]?.start ?? text.length); });
  return out;
}

// "#132 to #136 depend on Stage A, and #138 and #140 on Stage B" in a
// leaf's own section: the stage of this leaf those dependents wait on.
// Returns [{ dependents: [ids], tokens }].
const DOWNSTREAM_VERB = /^(.*?)\s+(?:depends?\s+on|depend\s+on|needs?|need|takes?|take|on)\s+(?:only\s+)?((?:[Ss]tages?\s+|S(?=\d)|PRs?\s+)(?:\d+[a-z]?|[A-H])\b|\d+[a-z]\b)/;
export function downstreamStages(clause, issueLeaf) {
  const out = [];
  let verbSeen = false;
  for (const part of clause.split(/,\s+and\s+|;\s+/)) {
    const m = DOWNSTREAM_VERB.exec(part.replace(/^and\s+/, ''));
    if (!m) continue;
    if (/\son$/.test(part.slice(0, m[0].length).replace(/\s+(?:only\s+)?\S+$/, '').trim() + ' on') && !verbSeen && !/depend/.test(part)) {
      // "#138 and #140 on Stage B" only continues an earlier verb.
    }
    const hasVerb = /\b(?:depends?|depend|needs?|need|takes?|take)\b/.test(part);
    if (!hasVerb && !verbSeen) continue;
    verbSeen = verbSeen || hasVerb;
    // The subject: references, with their own stage ("#26's stage A") dropped.
    const subject = m[1].replace(/'s\s+(?:[Ss]tage|S)\s*\w+/g, '');
    const refs = clauseRefs(subject, issueLeaf).flatMap((r) => r.ids);
    const stageText = /^\d+[a-z]$/.test(m[2]) ? `Stage ${m[2]}` : m[2];
    const tokens = readStageList(stageText, 0)?.tokens;
    if (refs.length && tokens) out.push({ dependents: refs, tokens });
  }
  return out;
}

// Splits a section into blocks (bullets and paragraphs) and each block into
// clauses (sentences, then semicolon parts), keeping the source line.
export function sectionBlocks(text) {
  const lines = String(text || '').split('\n');
  const blocks = [];
  let cur = null;
  lines.forEach((raw, i) => {
    const line = raw.trimEnd();
    if (!line.trim()) { cur = null; return; }
    const bullet = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (bullet || !cur) {
      cur = { line: i + 1, text: (bullet ? bullet[1] : line).replace(/\*\*/g, '').trim(), bullet: Boolean(bullet), indent: /^\s*/.exec(line)[0].length };
      blocks.push(cur);
    } else {
      cur.text += ` ${line.replace(/\*\*/g, '').trim()}`;
    }
  });
  return blocks;
}

export function splitClauses(text) {
  return text.split(/(?<=[.!?])\s+(?=[A-Z0-9#`(])|;\s+/).map((c) => c.trim()).filter(Boolean);
}

// The dependent stages a clause names at its start: "Stage 1:", "S2:",
// "Stages 0 to 3 and 5:", "Stage 2 adds", "PR 1 needs only", "1b needs".
export function leadingStages(clause) {
  const m = /^(?:all prs\b)/i.exec(clause);
  if (m) return { all: true };
  const head = /^(?=[Ss]tages?\s|S\d|PRs?\s|\d+[a-z]\s)/.exec(clause);
  if (!head) return null;
  let text = clause;
  if (/^\d+[a-z]\s/.test(text)) text = `Stage ${text}`;
  const list = readStageList(text, 0);
  if (!list) return null;
  const rest = text.slice(list.end);
  if (!/^\s*(?:\([^()]*\)\s*)?(?::|,|'s\b|\badds?\b|\bneeds?\b|\bhas\b|\bis\b|\bonly\b)/i.test(rest) && rest.trim()) return null;
  return { tokens: list.tokens, rest };
}

const oneLine = (s) => String(s).replace(/\s+/g, ' ').trim();
export const REASON_MAX = 200;
export function reasonText(text) {
  const t = oneLine(text);
  return t.length > REASON_MAX ? `${t.slice(0, REASON_MAX - 3).trimEnd()}...` : t;
}

// An edge's reason: what the body says about that reference ("#1
// (`ROUNDS-00A-L01`, route auth): the account dependency, ..."), or the
// whole bullet when the reference stands alone in a list ("#19, #20").
export function edgeReason(span, blockText) {
  const own = oneLine(span).replace(/[\s,;]+(?:and|or)?\s*$/, '');
  const bare = own.replace(/#\d+(?:\s+to\s+#\d+)?|\x60[^\x60]*\x60|[\s,.;:()]|\band\b|\bor\b/g, '');
  return reasonText(bare.length >= 3 ? own : blockText);
}

// Parses one section into raw edges for `self`:
// [{ prerequisite: { id, stages|null }, forStages: { tokens }|{ from }|null, reason, line }].
export function parseSection(text, self, issueLeaf) {
  const edges = [];
  const mentions = [];
  const exclusive = [];
  const downstream = [];
  let skipNested = null;
  let context = null;
  for (const block of sectionBlocks(text)) {
    if (skipNested !== null && block.bullet && block.indent >= skipNested.indent) continue;
    skipNested = null;
    if (!block.bullet) context = null;
    // "Downstream edges: #26 and #145 on S1; #125 and #162 on S3": which of
    // this leaf's stages each dependent needs. Not this leaf's prerequisites.
    const down = /\bdownstream edges?:\s*(.*)$/i.exec(block.text);
    if (down) {
      for (const part of down[1].split(/;\s+/)) {
        const m = /^(?:and\s+)?(.*?)\s+on\s+((?:[Ss]tages?\s+|S(?=\d))(?:\d+[a-z]?|[A-H]))\b/.exec(part);
        if (!m) continue;
        const refs = clauseRefs(m[1].replace(/'s\s+[^,;]*?(?=,|\s+and\s+|$)/g, ''), issueLeaf).flatMap((r) => r.ids);
        const tokens = readStageList(m[2], 0)?.tokens;
        if (refs.length && tokens) downstream.push({ dependents: refs, tokens });
      }
    }
    if (SKIP_BLOCK.test(block.text)) {
      // "Inherited, not functional; drop with owner approval:" and similar
      // headers cover the bullets under them.
      if (/:\s*$/.test(block.text)) skipNested = { indent: block.indent };
      continue;
    }
    let scope = context;
    const clauses = splitClauses(block.text);
    const blockEdges = [];
    for (const clause of clauses) {
      if (SKIP_BLOCK.test(clause)) break;
      const lead = leadingStages(clause);
      if (lead) {
        scope = lead.all ? null : lead;
        if (lead.tokens) mentions.push(lead.tokens);
        // "Stage 1 needs only #45", "1a has none", "Stages 0 to 3 and 5:
        // none": those stages take no leaf-wide edge but the ones named here.
        if (lead.tokens && /^\s*(?:\([^()]*\)\s*)?(?::\s*none\b|'s first pr:.*\bonly\b|,?\s*(?:needs?|has)\s+(?:only|none)\b|:.*\bonly\.?$)/i.test(lead.rest)) {
          exclusive.push(lead.tokens);
          // "#1 (...). Stage 1 needs only this.": the block's references so far.
          if (/\bonly this\b/i.test(lead.rest)) for (const e of blockEdges) e.alsoExclusive = true;
        }
      }
      if (OTHER_SUBJECT.test(clause)) {
        downstream.push(...downstreamStages(clause, issueLeaf));
        continue;
      }
      if (SKIP_CLAUSE.test(clause)) continue;
      // "From stage 3." scopes the clause's references, or, alone, the
      // block's earlier ones: "#3 (`ROUNDS-00A-L03`, job protocol). From stage 3."
      const from = /(?:^|,\s*)from (?:stage|S)\s*([0-9]+[a-z]?|[A-H])\b/i.exec(clause);
      // "the fixture that #137 and #163 cite": other leaves, not prerequisites.
      // ", recorded in #17 as `ROUNDS-00A-L01/S3`": this leaf's program, not a prerequisite.
      const body = (lead?.rest !== undefined ? lead.rest : clause)
        .replace(/\bthat (?:#\d+|\x60ROUNDS-[^\x60]+\x60)[^.;]*?\bcites?\b/g, '')
        .replace(/,?\s*recorded in #17(?:\s+as\s+\x60[^\x60]+\x60)?/g, '');
      const refs = clauseRefs(body, issueLeaf);
      if (!refs.length) {
        // A clause without references qualifies the block's earlier ones:
        // "#3 (...). From stage 3." or "#8 (...). Corpus stage only."
        for (const e of blockEdges) {
          if (from && !e.forStages) e.forStages = { from: from[1] };
          e.after = `${e.after || ''} ${clause}`;
        }
        continue;
      }
      // A plain reference repeating a qualified one in the same clause
      // ("`ROUNDS-18-L03`: Stage 1 exporter registration (#91)") adds nothing.
      const qualified = new Set(refs.filter((r) => r.ids.length === 1 && (r.qualifier || r.explicitStage)).map((r) => r.ids[0]));
      for (const r of refs) {
        if (r.ids.length === 1 && !r.qualifier && !r.explicitStage && qualified.has(r.ids[0])) continue;
        for (const id of r.ids) {
          if (id === self) continue;
          const stages = r.explicitStage ? [{ explicit: r.explicitStage }] : r.qualifier;
          const forStages = from ? { from: from[1] } : scope && !scope.all ? scope : null;
          const edge = { prerequisite: { id, stages: r.ids.length === 1 ? stages : null, afterColon: Boolean(r.afterColon && !r.explicitStage) }, forStages, reason: edgeReason(r.span, block.text), line: block.line, span: r.span };
          edges.push(edge);
          blockEdges.push(edge);
        }
      }
    }
    // A header like "Part (b): part (a), plus" or "Stage A, complete unless a
    // state is given:" scopes the bullets that follow it.
    if (!block.bullet && /:\s*$/.test(block.text)) {
      const lead = leadingStages(block.text);
      context = lead && !lead.all ? lead : null;
    }
  }
  return { edges, mentions, exclusive, downstream };
}

// ------------------------------------------------------------ build

// "#156 (...), for PR 9": the reference serves that stage of this leaf.
const FOR_STAGE = /\bfor (PR|[Ss]tage|S)\s*(\d+[a-z]?|[A-H])\b/;
const isLeafId = (s) => /^ROUNDS-\d{2}[A-Z]?-L\d{2}$/.test(s);
const capabilityOf = (id) => id.replace(/-L\d{2}$/, '');

function stageSort(list) {
  const key = (s) => {
    const m = /^([A-Za-z]*)(\d*)([a-z]*)(?:\.(\d+))?$/.exec(s) || [];
    return [m[1] || '', m[2] ? Number(m[2]) : -1, m[3] || '', m[4] ? Number(m[4]) : 0];
  };
  return [...list].sort((a, b) => {
    const x = key(a);
    const y = key(b);
    for (let i = 0; i < 4; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
    return 0;
  });
}

// Resolves a rule list ([{ match, phase|milestone, ... }]) for a leaf id: the
// last rule whose match (a leaf id, a capability, or "<leaf> to <leaf>")
// covers the leaf wins.
export function ruleValue(rules, id, field) {
  let value;
  let source;
  for (const r of rules || []) {
    const ms = Array.isArray(r.match) ? r.match : [r.match];
    for (const m of ms) {
      const range = /^(ROUNDS-\d{2}[A-Z]?-L\d{2}) to (ROUNDS-\d{2}[A-Z]?-L\d{2})$/.exec(m);
      let hit = false;
      if (range) hit = capabilityOf(range[1]) === capabilityOf(id) && id >= range[1] && id <= range[2];
      else hit = m === id || m === capabilityOf(id);
      if (hit) { value = r[field]; source = r; }
    }
  }
  return { value, source };
}

// Builds the DAG from the export and inputs. Returns { dag, findings }:
// findings are build problems (unknown references, stale overrides) that
// the conformance rule reports.
export function buildDag({ exportFile, inputs, registry }) {
  const findings = [];
  const leaves = (registry?.leaves || []).filter((l) => l.status !== 'rejected');
  const issueLeaf = new Map(leaves.filter((l) => l.issue).map((l) => [l.issue, l.id]));
  const byId = new Map((registry?.leaves || []).map((l) => [l.id, l]));
  const curated = inputs?.stages || {};
  const numbered = new Set(Object.entries(curated).filter(([, s]) => s.numbered).map(([id]) => id));
  const issues = new Map((exportFile?.issues || []).map((i) => [i.number, i]));
  const ids = (tokens, id, known) => applyAliases(expandTokens(tokens, numbered.has(id), known), curated[id]);

  // Pass 1: raw edges per leaf, and the stages each reference implies.
  const raw = new Map();
  const exclusiveOf = new Map();
  // prerequisite -> dependent -> stage tokens its own section says the dependent needs.
  const downstreamOf = new Map();
  const derived = new Map();
  const addDerived = (id, stage) => {
    if (!derived.has(id)) derived.set(id, new Set());
    derived.get(id).add(stage);
  };
  for (const leaf of leaves) {
    const issue = issues.get(leaf.issue);
    if (!issue) { findings.push(finding('PROGRAM_EXPORT_INVALID', EXPORT_PATH, 1, `issue #${leaf.issue} (${leaf.id}) is not in the export`)); continue; }
    const titleId = /^\[(ROUNDS-\d{2}[A-Z]?-L\d{2})\]/.exec(issue.title)?.[1];
    if (titleId !== leaf.id) findings.push(finding('PROGRAM_EXPORT_INVALID', EXPORT_PATH, 1, `issue #${leaf.issue} is titled ${titleId || 'without a leaf id'}, but ${LEAF_IDS_PATH} says ${leaf.id}`));
    if (issue.prerequisites === null) { findings.push(finding('PROGRAM_EXPORT_INVALID', EXPORT_PATH, 1, `issue #${leaf.issue} has no "${SECTION}" section`)); raw.set(leaf.id, []); continue; }
    const { edges, mentions, exclusive, downstream } = parseSection(issue.prerequisites, leaf.id, issueLeaf);
    raw.set(leaf.id, edges);
    exclusiveOf.set(leaf.id, exclusive);
    for (const d of downstream) {
      for (const dep of d.dependents) {
        if (!downstreamOf.has(leaf.id)) downstreamOf.set(leaf.id, new Map());
        if (!downstreamOf.get(leaf.id).has(dep)) downstreamOf.get(leaf.id).set(dep, d.tokens);
      }
      for (const st of ids(d.tokens, leaf.id)) addDerived(leaf.id, st);
    }
    for (const tokens of mentions) for (const s of ids(tokens, leaf.id)) addDerived(leaf.id, s);
    for (const e of edges) {
      const forPr = FOR_STAGE.exec(e.span || '');
      if (!e.forStages && forPr) addDerived(leaf.id, ids([{ kind: forPr[1] === 'PR' ? 'P' : 'S', value: forPr[2] }], leaf.id)[0]);
      if (e.forStages?.tokens) for (const s of ids(e.forStages.tokens, leaf.id)) addDerived(leaf.id, s);
      if (e.forStages?.from) addDerived(leaf.id, stageId({ kind: 'S', value: e.forStages.from }, numbered.has(leaf.id)));
      const p = e.prerequisite;
      if (isLeafId(p.id) && p.stages && p.afterColon) {
        // "#1 (...): stage 3 only" names #1's stage; "#13 (...): S1" this
        // leaf's. A curated list settles it, the prerequisite's first.
        const asPrereq = ids(p.stages, p.id, curated[p.id]?.stages);
        const asOwn = ids(p.stages, leaf.id, curated[leaf.id]?.stages);
        if (curated[p.id] && asPrereq.every((s) => curated[p.id].stages.includes(s))) p.colon = 'prerequisite';
        else if (curated[leaf.id] && asOwn.every((s) => curated[leaf.id].stages.includes(s))) p.colon = 'own';
        else if (curated[p.id]) p.colon = 'none';
        else { p.colon = 'prerequisite'; for (const s of asPrereq) addDerived(p.id, s); }
      } else if (isLeafId(p.id) && p.stages) {
        for (const s of p.stages) {
          if (s.explicit) addDerived(p.id, s.explicit);
        }
        const tokens = p.stages.filter((s) => !s.explicit);
        if (tokens.length) for (const s of ids(tokens, p.id)) addDerived(p.id, s);
      }
    }
  }
  for (const e of inputs?.edges?.add || []) {
    const [leaf, stage] = String(e.prerequisite).split('/');
    if (stage) addDerived(leaf, stage);
    for (const s of e.forStages || []) addDerived(e.dependent, s);
  }

  // Stage lists: curated where the inputs give one, else derived.
  const stagesOf = new Map();
  for (const leaf of leaves) {
    const c = curated[leaf.id];
    const d = [...(derived.get(leaf.id) || [])];
    if (c) {
      for (const s of d) {
        if (!c.stages.includes(s)) findings.push(finding('PROGRAM_STAGE_UNKNOWN', INPUTS_PATH, 1, `the export names stage ${s} of ${leaf.id}, which its stage list (${c.stages.join(', ')}) does not have`));
      }
      stagesOf.set(leaf.id, { stages: c.stages, complete: c.complete !== false, source: c.source });
    } else if (d.length) {
      stagesOf.set(leaf.id, { stages: stageSort(d), complete: false, source: `references in ${EXPORT_PATH}` });
    }
  }

  // Pass 2: normalize edges.
  const dropped = new Map((inputs?.edges?.drop || []).map((d, i) => [`${d.dependent} ${d.prerequisite}`, { ...d, i, used: false }]));
  const nodes = [];
  for (const leaf of leaves) {
    const own = stagesOf.get(leaf.id);
    const ownStages = own?.stages || [];
    const list = [];
    const seen = new Map();
    const push = (edge) => {
      const key = `${edge.prerequisite} ${(edge.forStages || []).join(',')}`;
      if (seen.has(key)) return;
      seen.set(key, edge);
      list.push(edge);
    };
    for (const e of raw.get(leaf.id) || []) {
      const p = e.prerequisite;
      if (!isLeafId(p.id)) {
        findings.push(finding('PROGRAM_UNRESOLVED_REF', EXPORT_PATH, 1, `#${leaf.issue} (${leaf.id}) names ${p.id}, which is not a leaf in ${LEAF_IDS_PATH}`));
        continue;
      }
      const target = byId.get(p.id);
      if (!target) {
        findings.push(finding('PROGRAM_UNRESOLVED_REF', EXPORT_PATH, 1, `#${leaf.issue} (${leaf.id}) names ${p.id}, which is not in ${LEAF_IDS_PATH}`));
        continue;
      }
      let prereqStages = [null];
      let colonStages = null;
      if (p.stages && p.afterColon) {
        if (p.colon === 'prerequisite') prereqStages = ids(p.stages, p.id, stagesOf.get(p.id)?.stages);
        else if (p.colon === 'own') colonStages = ids(p.stages, leaf.id, ownStages);
      } else if (p.stages) {
        const explicit = p.stages.filter((s) => s.explicit).map((s) => s.explicit);
        const tokens = p.stages.filter((s) => !s.explicit);
        prereqStages = [...explicit, ...(tokens.length ? ids(tokens, p.id, stagesOf.get(p.id)?.stages) : [])];
      }
      // The prerequisite's own section may say which of its stages this leaf
      // needs ("#132 to #136 depend on Stage A"); a whole-leaf edge takes it.
      if (!p.stages && prereqStages.length === 1 && prereqStages[0] === null && downstreamOf.get(p.id)?.has(leaf.id)) {
        prereqStages = ids(downstreamOf.get(p.id).get(leaf.id), p.id, stagesOf.get(p.id)?.stages);
      }
      // A curated phrase names a stage: #8's "corpus stage" is S1.
      if (!p.stages && curated[p.id]?.phrases && e.span) {
        const text = `${e.span} ${e.after || ''}`.toLowerCase();
        const hit = Object.entries(curated[p.id].phrases).find(([phrase]) => text.includes(phrase));
        if (hit) prereqStages = [hit[1]];
      }
      let forStages = colonStages;
      // "#156 (...), for PR 9": the reference is for this leaf's stage.
      const forPr = FOR_STAGE.exec(e.span || '');
      if (!forStages && !e.forStages && forPr) forStages = ids([{ kind: forPr[1] === 'PR' ? 'P' : 'S', value: forPr[2] }], leaf.id, ownStages);
      if (e.forStages?.tokens) forStages = ids(e.forStages.tokens, leaf.id, ownStages);
      else if (e.forStages?.from) {
        const start = stageId({ kind: 'S', value: e.forStages.from }, numbered.has(leaf.id));
        forStages = ownStages.includes(start) ? ownStages.slice(ownStages.indexOf(start)) : [start];
      }
      for (const s of prereqStages) {
        const ref = s ? `${p.id}/${s}` : p.id;
        const key = `${leaf.id} ${ref}`;
        if (dropped.has(key)) { dropped.get(key).used = true; continue; }
        push({ prerequisite: ref, ...(forStages ? { forStages } : {}), reason: e.reason, source: `${EXPORT_PATH} #${leaf.issue} line ${e.line}`, ...(e.alsoExclusive ? { alsoExclusive: true } : {}) });
      }
    }
    for (const a of inputs?.edges?.add || []) {
      if (a.dependent !== leaf.id) continue;
      push({ prerequisite: a.prerequisite, ...(a.forStages ? { forStages: a.forStages } : {}), reason: a.reason, source: INPUTS_PATH });
    }
    // A stage-scoped edge that repeats a leaf-wide one adds nothing.
    const wide = new Set(list.filter((e) => !e.forStages).map((e) => e.prerequisite));
    const edges = list.filter((e) => !e.forStages || !wide.has(e.prerequisite));
    // Stages a body says need only their own list ("1a has none") take no
    // other leaf-wide edge: those edges are scoped to the remaining stages.
    const exclusive = new Set((exclusiveOf.get(leaf.id) || []).flatMap((tokens) => ids(tokens, leaf.id, ownStages)));
    const rest = ownStages.filter((st) => !exclusive.has(st));
    for (const e of edges) {
      if (!e.forStages && !e.alsoExclusive && exclusive.size && rest.length) e.forStages = rest;
      delete e.alsoExclusive;
    }
    const capability = capabilityOf(leaf.id);
    const node = { id: leaf.id, issue: leaf.issue, status: leaf.status, capability };
    if (own) {
      node.stages = own.stages;
      node.stagesComplete = own.complete;
      node.stagesSource = own.source;
    }
    // satisfiedBy: the stages a dependent of the whole leaf waits on, when
    // that is not every stage (#17's dependents need S2, decision P13).
    const need = inputs?.satisfiedBy?.[leaf.id];
    if (need) node.satisfiedBy = need.stages;
    node.filedPrerequisites = edges;
    nodes.push(node);
  }
  for (const d of dropped.values()) {
    if (!d.used) findings.push(finding('PROGRAM_OVERRIDE_STALE', INPUTS_PATH, 1, `edges.drop ${d.dependent} on ${d.prerequisite} matches no edge in the export; remove it`));
  }

  // Phase and milestone: the inputs' base value, then pulled earlier so no
  // leaf-wide prerequisite lands after a leaf that needs it (spec 3072-3091;
  // "a leaf that a dependent in an earlier phase needs is pulled into that phase").
  for (const field of ['phase', 'milestone']) {
    const rules = inputs?.[field === 'phase' ? 'phases' : 'milestones']?.rules;
    for (const n of nodes) {
      const { value } = ruleValue(rules, n.id, field);
      if (value === undefined) findings.push(finding('PROGRAM_FIELD_MISSING', INPUTS_PATH, 1, `no ${field} rule covers ${n.id}`));
      n[field] = value ?? null;
    }
    const byNode = new Map(nodes.map((n) => [n.id, n]));
    for (let changed = true, rounds = 0; changed && rounds < nodes.length + 1; rounds++) {
      changed = false;
      for (const n of nodes) {
        if (n[field] === null) continue;
        for (const e of n.filedPrerequisites) {
          if (e.forStages) continue;
          const p = byNode.get(e.prerequisite.split('/')[0]);
          if (p && p[field] !== null && p[field] > n[field]) { p[field] = n[field]; changed = true; }
        }
      }
    }
  }
  // Key order for readability.
  const ordered = nodes.map((n) => {
    const { id, issue, status, capability, phase, milestone, stages, stagesComplete, stagesSource, satisfiedBy, filedPrerequisites } = n;
    return { id, issue, status, capability, phase, milestone, ...(stages ? { stages, stagesComplete, stagesSource } : {}), ...(satisfiedBy ? { satisfiedBy } : {}), filedPrerequisites };
  });

  const dag = {
    $schema: './leaf-dag.schema.json',
    description: `Generated by scripts/program/dag.mjs from ${EXPORT_PATH} and ${INPUTS_PATH}; do not edit. Regenerate with node scripts/conformance/run.mjs --write. One node per leaf in ${LEAF_IDS_PATH}, with its stages and the edges its issue's "${SECTION}" section names. edgeSet filed: these are the filed edges; docs/program/reauthorization.md lists the edges the owner's re-authorization adds or drops.`,
    decision: inputs?.decision || null,
    edgeSet: 'filed',
    source: {
      export: EXPORT_PATH,
      exportSha256: exportFile?.sha256 || null,
      exportedOn: exportFile?.source?.exportedOn || null,
      inputs: INPUTS_PATH,
      inputsSha256: inputs ? sha256(canonical(inputs)) : null,
    },
    phases: inputs?.phases?.titles || [],
    milestones: inputs?.milestones?.titles || [],
    nodes: ordered,
    dropped: (registry?.leaves || []).filter((l) => l.status === 'rejected').map((l) => ({ id: l.id, foldedInto: l.foldedInto || null })),
  };
  return { dag, findings };
}

export function renderDag(dag) {
  return prettyJson(dag);
}

// ------------------------------------------------------------ graph checks

// The stage-level graph: a leaf without stages is one vertex, a staged leaf
// one vertex per stage. A leaf-wide edge runs from every stage of the
// dependent; an edge on a whole staged leaf reaches every stage of it, or
// the stages its satisfiedBy names.
export function stageGraph(dag) {
  const nodes = new Map((dag?.nodes || []).map((n) => [n.id, n]));
  const vertices = (id) => {
    const n = nodes.get(id);
    return n?.stages?.length ? n.stages.map((s) => `${id}/${s}`) : [id];
  };
  const targets = (ref) => {
    const [id, stage] = String(ref).split('/');
    const n = nodes.get(id);
    if (!n) return [];
    if (stage) return n.stages?.length ? [`${id}/${stage}`] : [id];
    if (n.satisfiedBy?.length && n.stages?.length) return n.satisfiedBy.map((st) => `${id}/${st}`);
    return vertices(id);
  };
  const adj = new Map();
  for (const n of nodes.values()) for (const v of vertices(n.id)) adj.set(v, new Set());
  for (const n of nodes.values()) {
    for (const e of n.filedPrerequisites || []) {
      const from = e.forStages ? e.forStages.map((s) => (n.stages?.length ? `${n.id}/${s}` : n.id)) : vertices(n.id);
      for (const f of from) for (const t of targets(e.prerequisite)) {
        if (!adj.has(f)) adj.set(f, new Set());
        if (f !== t) adj.get(f).add(t);
      }
    }
  }
  return adj;
}

// Every elementary cycle is too many to list; this returns one cycle per
// strongly connected component with more than one vertex (Tarjan).
export function findCycles(adj) {
  let index = 0;
  const idx = new Map();
  const low = new Map();
  const onStack = new Set();
  const stack = [];
  const comps = [];
  const strong = (v) => {
    idx.set(v, index); low.set(v, index); index++;
    stack.push(v); onStack.add(v);
    for (const w of adj.get(v) || []) {
      if (!idx.has(w)) { strong(w); low.set(v, Math.min(low.get(v), low.get(w))); }
      else if (onStack.has(w)) low.set(v, Math.min(low.get(v), idx.get(w)));
    }
    if (low.get(v) === idx.get(v)) {
      const comp = [];
      let w;
      do { w = stack.pop(); onStack.delete(w); comp.push(w); } while (w !== v);
      if (comp.length > 1) comps.push(comp);
    }
  };
  for (const v of [...adj.keys()].sort()) if (!idx.has(v)) strong(v);
  // One concrete cycle through each component, for the message.
  return comps.map((comp) => {
    const inComp = new Set(comp);
    const startV = [...comp].sort()[0];
    const prev = new Map([[startV, null]]);
    const queue = [startV];
    while (queue.length) {
      const v = queue.shift();
      for (const w of adj.get(v) || []) {
        if (!inComp.has(w)) continue;
        if (w === startV) {
          const path = [v];
          for (let x = prev.get(v); x !== null && x !== undefined; x = prev.get(x)) path.push(x);
          return { size: comp.length, cycle: [...path.reverse(), startV] };
        }
        if (!prev.has(w)) { prev.set(w, v); queue.push(w); }
      }
    }
    return { size: comp.length, cycle: comp };
  });
}

export { loadLeafIds };

// ------------------------------------------------------------ checks

const DR_REF = /\bDR-(\d{4})@(\d+)(?::([A-Za-z0-9.-]+))?/g;
export const GATE_PATH = 'docs/program/leaf-gate.json';
export const GATE_SCHEMA = 'docs/program/leaf-gate.schema.json';
// The export is issue text; the other three pin the current revision below.
const DR_SCAN_SKIP = new Set([EXPORT_PATH, DAG_PATH, INPUTS_PATH, GATE_PATH]);
export const PROGRAM_DR = 'DR-0003';

// Decision records by id: { path, revision, compatibility, artifacts }.
export function decisionRecords(ctx) {
  const out = new Map();
  for (const rel of ctx.files().filter((f) => /^docs\/decisions\/DR-\d{4}-[^/]+\.json$/.test(f))) {
    try {
      const r = ctx.readJson(rel);
      if (typeof r?.id === 'string') out.set(r.id, { path: rel, revision: r.revision, compatibility: r.compatibility, artifacts: new Set((r.gateArtifacts || []).map((a) => a.id)) });
    } catch {
      // The decision-records rule reports an unreadable record.
    }
  }
  return out;
}

// Loads the DAG's inputs, the DAG, and the gate mode file; each unreadable
// one is a PROGRAM_FILE_INVALID finding and null.
export function loadDagFiles(ctx, findings = []) {
  const json = (rel) => {
    if (!ctx.exists(rel)) { findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} is missing`)); return null; }
    try {
      return ctx.readJson(rel);
    } catch (err) {
      findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} is not valid JSON: ${err.message}`));
      return null;
    }
  };
  return {
    exportFile: json(EXPORT_PATH), exportSchema: json(EXPORT_SCHEMA),
    inputs: json(INPUTS_PATH), inputsSchema: json(INPUTS_SCHEMA),
    dag: json(DAG_PATH), dagSchema: json(DAG_SCHEMA),
    gate: json(GATE_PATH), gateSchema: json(GATE_SCHEMA),
    registry: loadLeafIds(ctx),
  };
}

// The DAG the committed inputs produce, or null when one is unreadable.
export function generateDag(ctx) {
  const f = loadDagFiles(ctx, []);
  if (!f.exportFile || !f.inputs || !f.registry) return null;
  return buildDag(f);
}

// Checks the export, the inputs, the committed DAG, and the gate mode file
// (ROUNDS-01-L03 criteria 4 and 6): schemas, the export checksum, node ids
// against leaf-ids.json (unknown, duplicate, dropped, missing), edges (a
// reason, a known prerequisite and stage), cycles, and decision-record
// references. Drift between the inputs and the committed DAG is the
// runner's CONFORMANCE_DRIFT, from program.mjs's generate().
export function checkDag(ctx) {
  const findings = [];
  const f = loadDagFiles(ctx, findings);
  const lineIn = (rel, parts) => {
    try {
      return jsonLine(ctx.read(rel), parts);
    } catch {
      return 1;
    }
  };
  const schemaCheck = (value, schema, rel) => {
    if (!value || !schema) return;
    for (const err of validate(value, schema)) {
      const parts = err.pointer.split('/').slice(1).map((p) => (/^\d+$/.test(p) ? Number(p) : p));
      findings.push(finding('PROGRAM_FILE_INVALID', rel, lineIn(rel, parts), `${err.pointer || '/'} ${err.message}`));
    }
  };
  schemaCheck(f.exportFile, f.exportSchema, EXPORT_PATH);
  schemaCheck(f.inputs, f.inputsSchema, INPUTS_PATH);
  schemaCheck(f.dag, f.dagSchema, DAG_PATH);
  schemaCheck(f.gate, f.gateSchema, GATE_PATH);
  if (!f.registry) findings.push(finding('PROGRAM_FILE_INVALID', LEAF_IDS_PATH, 1, `${LEAF_IDS_PATH} is missing or invalid; the DAG is unchecked`));

  // The export's checksum, and the DAG's record of both inputs.
  if (f.exportFile) {
    const actual = exportDigest(Array.isArray(f.exportFile.issues) ? f.exportFile.issues : []);
    if (actual !== f.exportFile.sha256) {
      findings.push(finding('PROGRAM_EXPORT_STALE', EXPORT_PATH, lineIn(EXPORT_PATH, ['sha256']), `the issues array hashes to ${actual.slice(0, 12)}..., not the recorded ${String(f.exportFile.sha256).slice(0, 12)}...; re-export with scripts/program/export.mjs instead of editing it`));
    }
  }
  if (f.dag && f.exportFile && f.dag.source?.exportSha256 !== f.exportFile.sha256) {
    findings.push(finding('PROGRAM_EXPORT_STALE', DAG_PATH, lineIn(DAG_PATH, ['source', 'exportSha256']), `${DAG_PATH} was built from export ${String(f.dag.source?.exportSha256).slice(0, 12)}..., not the committed ${String(f.exportFile.sha256).slice(0, 12)}...; run node scripts/conformance/run.mjs --write`));
  }
  if (f.dag && f.inputs && f.dag.source?.inputsSha256 !== sha256(canonical(f.inputs))) {
    findings.push(finding('PROGRAM_EXPORT_STALE', DAG_PATH, lineIn(DAG_PATH, ['source', 'inputsSha256']), `${DAG_PATH} was built from other ${INPUTS_PATH} contents; run node scripts/conformance/run.mjs --write`));
  }

  // Build problems: a reference no leaf matches, a stale override.
  if (f.exportFile && f.inputs && f.registry) findings.push(...buildDag(f).findings);

  if (f.dag && f.registry) checkDagGraph(f.dag, f.registry, findings, (parts) => lineIn(DAG_PATH, parts));

  // Decision-record references.
  const records = decisionRecords(ctx);
  const current = records.get(PROGRAM_DR);
  const pinned = `${PROGRAM_DR}@${current?.revision}`;
  for (const [rel, value] of [[DAG_PATH, f.dag], [INPUTS_PATH, f.inputs], [GATE_PATH, f.gate]]) {
    if (!value || value.decision === undefined) continue;
    if (value.decision !== pinned) findings.push(finding('PROGRAM_DR_UNRESOLVED', rel, lineIn(rel, ['decision']), `${rel} cites ${value.decision}; the current program decision is ${current ? pinned : `missing (${PROGRAM_DR} is not in docs/decisions)`}`));
  }
  for (const rel of ctx.files().filter((p) => /^docs\/program\/.+\.(?:json|md)$/.test(p) && !DR_SCAN_SKIP.has(p))) {
    const text = ctx.read(rel);
    for (const m of text.matchAll(DR_REF)) {
      const id = `DR-${m[1]}`;
      const rev = Number(m[2]);
      const record = records.get(id);
      const line = text.slice(0, m.index).split('\n').length;
      if (!record) findings.push(finding('PROGRAM_DR_UNRESOLVED', rel, line, `${m[0]} names no decision record in docs/decisions`));
      else if (!(rev >= 1 && rev <= record.revision)) findings.push(finding('PROGRAM_DR_UNRESOLVED', rel, line, `${m[0]}: ${id} is at revision ${record.revision}`));
      else if (rev < record.revision && record.compatibility === 'breaking') findings.push(finding('PROGRAM_DR_UNRESOLVED', rel, line, `${m[0]} was superseded by the breaking ${id}@${record.revision}; cite the successor`));
      else if (m[3] && record.artifacts.size && !record.artifacts.has(m[3])) findings.push(finding('PROGRAM_DR_UNRESOLVED', rel, line, `${m[0]}: ${id} has no gate artifact ${m[3]}`));
    }
  }
  return findings;
}

// Node, edge, and cycle checks on a DAG value.
export function checkDagGraph(dag, registry, findings = [], line = () => 1) {
  const byId = new Map((registry?.leaves || []).map((l) => [l.id, l]));
  const nodes = new Map();
  (dag.nodes || []).forEach((n, i) => {
    const at = () => line(['nodes', i]);
    if (nodes.has(n.id)) { findings.push(finding('PROGRAM_DAG_DUPLICATE', DAG_PATH, at(), `${n.id} has two nodes`)); return; }
    nodes.set(n.id, n);
    const leaf = byId.get(n.id);
    if (!leaf) findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, at(), `node ${n.id} is not in ${LEAF_IDS_PATH}`));
    else if (leaf.status === 'rejected') findings.push(finding('PROGRAM_DAG_DROPPED', DAG_PATH, at(), `node ${n.id} was folded into ${leaf.foldedInto}; it belongs in dropped, not nodes`));
    else if (leaf.issue !== n.issue) findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, at(), `node ${n.id} says issue #${n.issue}; ${LEAF_IDS_PATH} says #${leaf.issue}`));
  });
  for (const l of registry?.leaves || []) {
    if (l.status !== 'rejected' && !nodes.has(l.id)) findings.push(finding('PROGRAM_DAG_MISSING', DAG_PATH, line(['nodes']), `${l.id} (#${l.issue}) has no node`));
  }
  const rejected = (registry?.leaves || []).filter((l) => l.status === 'rejected').map((l) => l.id).sort();
  const dropped = (dag.dropped || []).map((d) => d.id).sort();
  if (JSON.stringify(rejected) !== JSON.stringify(dropped)) {
    findings.push(finding('PROGRAM_DAG_DROPPED', DAG_PATH, line(['dropped']), `dropped lists ${dropped.join(', ') || 'none'}; ${LEAF_IDS_PATH} rejects ${rejected.join(', ') || 'none'}`));
  }
  (dag.nodes || []).forEach((n, i) => {
    const own = n.stages || [];
    for (const s of n.satisfiedBy || []) {
      if (!own.includes(s)) findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, line(['nodes', i, 'satisfiedBy']), `${n.id} satisfiedBy names stage ${s}, which it does not have`));
    }
    const seen = new Set();
    (n.filedPrerequisites || []).forEach((e, j) => {
      const at = () => line(['nodes', i, 'filedPrerequisites', j]);
      const key = `${e.prerequisite} ${(e.forStages || []).join(',')}`;
      if (seen.has(key)) findings.push(finding('PROGRAM_DAG_DUPLICATE', DAG_PATH, at(), `${n.id} lists the edge on ${e.prerequisite}${e.forStages ? ` for ${e.forStages.join(', ')}` : ''} twice`));
      seen.add(key);
      if (typeof e.reason !== 'string' || !e.reason.trim()) findings.push(finding('PROGRAM_EDGE_REASON', DAG_PATH, at(), `${n.id}'s edge on ${e.prerequisite} has no reason`));
      for (const s of e.forStages || []) {
        if (!own.includes(s)) findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, at(), `${n.id}'s edge on ${e.prerequisite} is for stage ${s}, which ${n.id} does not have`));
      }
      const [pid, stage] = String(e.prerequisite).split('/');
      if (pid === n.id) { findings.push(finding('PROGRAM_DAG_CYCLE', DAG_PATH, at(), `${n.id} depends on itself`)); return; }
      const leaf = byId.get(pid);
      if (!leaf) { findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, at(), `${n.id} depends on ${e.prerequisite}, which is not in ${LEAF_IDS_PATH}`)); return; }
      if (leaf.status === 'rejected') { findings.push(finding('PROGRAM_DAG_DROPPED', DAG_PATH, at(), `${n.id} depends on ${pid}, which was folded into ${leaf.foldedInto}`)); return; }
      const target = nodes.get(pid);
      if (stage && !(target?.stages || []).includes(stage)) findings.push(finding('PROGRAM_DAG_UNKNOWN', DAG_PATH, at(), `${n.id} depends on ${e.prerequisite}, but ${pid} has no stage ${stage}`));
    });
  });
  for (const c of findCycles(stageGraph(dag))) {
    findings.push(finding('PROGRAM_DAG_CYCLE', DAG_PATH, line(['nodes']), `${c.size} stage nodes form a cycle, for example ${c.cycle.join(' > ')}`));
  }
  return findings;
}
