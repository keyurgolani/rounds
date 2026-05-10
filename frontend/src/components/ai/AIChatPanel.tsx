import { memo, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Sparkles, Square, User, Wand2 } from 'lucide-react';
import { runnerSSE } from '../../lib/runnerFetch';
import BlockMarkdown from '../shell/BlockMarkdown';
import ModelSwitcher, { type ModelOverride } from './ModelSwitcher';
import { listAICodingModels, type AICodingModel } from '../../pages/ai-coding/aiCodingApi';
import AIPatchView, { type PatchProposal } from './AIPatchView';
import { splitPatches } from './aiPatches';

type Msg = {
  role: 'user' | 'assistant';
  content: string;
  /** Patches attached to this message (assistant only). When set, the
   *  diff card renders INSIDE the bubble; the prose pre-amble (if any)
   *  is rendered above it. */
  patches?: PatchProposal[];
  /** When true, the diff card renders read-only with an "Applied"
   *  badge. Set after the user accepts. We keep the snapshot of files
   *  *before* apply so the diff stays meaningful in the history. */
  applied?: boolean;
  /** Files snapshot used as the "original" side for the diff. Stored
   *  on the message so the diff doesn't mutate as the user edits the
   *  workspace afterwards. */
  filesSnapshot?: Record<string, string>;
};

type Mode = 'ask' | 'edit';

type Props = {
  roundSlug: string;
  checkpointIndex: number;
  files: Record<string, string>;
  checkpointPrompt?: string;
  disabled?: boolean;
  /** Optional rehydration source — used when the page restores a
   *  persisted chat log on mount so the bubble history is visible
   *  immediately. We only consume this to seed `messages` once,
   *  changes to the prop afterwards are ignored (the local state
   *  takes over to avoid clobbering streaming deltas). */
  initialMessages?: Array<{ role: 'user' | 'assistant'; content: string }>;
  onMessageRecorded?: (m: { role: 'user' | 'assistant'; content: string }) => void;
  onApplyPatches?: (patches: PatchProposal[]) => void;
};

export default function AIChatPanel({
  roundSlug,
  checkpointIndex,
  files,
  checkpointPrompt,
  disabled,
  initialMessages,
  onMessageRecorded,
  onApplyPatches,
}: Props) {
  // Owns the live AbortController for the in-flight SSE so the Stop
  // button can cancel it. Set during send(), cleared in finally.
  const abortRef = useRef<AbortController | null>(null);
  // Snapshot of `files` at mount time, used as the "original" side
  // for normalising rehydrated patches. Live `files` would be wrong
  // as the user keeps editing, but at first paint they're effectively
  // the same as when the patch was authored.
  const initialFilesRef = useRef(files);
  const [messages, setMessages] = useState<Msg[]>(() => {
    // Rehydrate persisted assistant messages: if any of them ended in
    // a JSON patch tail (i.e. came from /edit mode), parse it back
    // out so the bubble renders the diff card with an "Applied" badge
    // instead of dumping raw JSON in the bubble.
    const startFiles = initialFilesRef.current;
    return (initialMessages ?? []).map((m) => {
      if (m.role !== 'assistant') return { role: m.role, content: m.content };
      const { prose, patches } = splitPatches(m.content);
      if (!patches || patches.length === 0) {
        return { role: m.role, content: m.content };
      }
      // Normalise rehydrated patches against the workspace snapshot so
      // the diff card displays clean whitespace (matches what would
      // actually be applied), not the raw model garbage that's been
      // sitting in PocketBase since the original turn.
      const cleaned = patches.map((p) => {
        const original = startFiles[p.file];
        if (typeof original !== 'string') return p;
        const fixed = normaliseProposedWhitespace(original, p.contents);
        return fixed === p.contents ? p : { ...p, contents: fixed };
      });
      return {
        role: 'assistant',
        content: prose,
        patches: cleaned,
        // Do NOT mark as applied on rehydrate — we have no record of
        // whether the user actually accepted before refresh. The
        // previous heuristic (always applied) caused the UI to claim
        // "APPLIED" even when onApplyPatches was never fired (panel
        // remount path). Show the patches as proposed so the user
        // can re-accept; the apply is idempotent thanks to the
        // normaliseProposedWhitespace pipeline.
        applied: false,
      };
    });
  });
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const streamingRef = useRef<string>('');
  const [models, setModels] = useState<AICodingModel[]>([]);
  const [override, setOverride] = useState<ModelOverride>(null);
  const [mode, setMode] = useState<Mode>('ask');
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Bubbles widen as the panel gets narrower so the user always has
  // room to read — 90% by default, 95% when the panel gets tight,
  // 100% when very narrow. Measured via ResizeObserver on the scroll
  // container so it reacts as the user drags the chat rail wider.
  const [bubbleWidthPct, setBubbleWidthPct] = useState<number>(90);

  useEffect(() => {
    listAICodingModels()
      .then(setModels)
      .catch((err) => {
        console.warn('[ai-coding] failed to load model list:', err);
        setModels([]);
      });
  }, []);

  useLayoutEffect(() => {
    const el = composerRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }, [draft]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      // Tiered bubble width: tighter container → bubble takes more
      // of the row to keep prose readable.
      const next = w >= 480 ? 90 : w >= 360 ? 95 : 100;
      setBubbleWidthPct((prev) => (prev === next ? prev : next));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  function stripPatchJsonFromContent(content: string): string {
    // The /edit endpoint contract: model outputs ONLY a JSON array,
    // optionally inside a ```json fence. Strip everything from the
    // first plausible JSON-array opener (`[`, `\`\`\`json`, or `\`\`\``
    // followed shortly by `[`) to the end so users see only any prose
    // preamble (usually empty for /edit). This is intentionally greedy:
    // even if the model emits prose AFTER the JSON, we discard it
    // because the parsed patches tell the real story.
    const fenced = content.search(/```(?:json)?\s*\[/);
    if (fenced !== -1) return content.slice(0, fenced).trimEnd();
    const idx = content.indexOf('[');
    if (idx !== -1) return content.slice(0, idx).trimEnd();
    return content;
  }

  async function send() {
    if (!draft.trim() || streaming) return;
    const userMsg: Msg = { role: 'user', content: draft };
    // Eagerly append the user message AND an empty assistant placeholder
    // so the avatar + "Responding…" indicator appears the instant the
    // user hits send — without this the user stares at their own bubble
    // for a (sometimes long) round-trip before any feedback shows.
    setMessages((m) => [...m, userMsg, { role: 'assistant', content: '' }]);
    onMessageRecorded?.(userMsg);
    setDraft('');
    setStreaming(true);
    streamingRef.current = '';
    const ac = new AbortController();
    abortRef.current = ac;
    const path = mode === 'edit' ? '/api/ai-coding/edit' : '/api/ai-coding/chat';
    try {
      let receivedPatches: PatchProposal[] | null = null;
      await runnerSSE(path, {
        method: 'POST',
        auth: 'optional',
        signal: ac.signal,
        body: {
          round_slug: roundSlug,
          checkpoint_index: checkpointIndex,
          provider_id: override?.provider_id,
          model: override?.model,
          messages: [...messages, userMsg],
          files,
          checkpoint_prompt: checkpointPrompt,
        },
        onDelta: (t) => {
          streamingRef.current += t;
          // In /edit mode the backend streams the raw JSON token-by-token
          // (the model is instructed to emit ONLY the JSON array). We
          // strip any nascent JSON tail before showing it so the user
          // never sees raw `[{"file":...` building up — only the prose
          // preamble (usually empty) plus a "preparing edits" indicator.
          const visible =
            mode === 'edit'
              ? stripPatchJsonFromContent(streamingRef.current)
              : streamingRef.current;
          setMessages((m) => {
            const last = m[m.length - 1];
            const next: Msg = { role: 'assistant', content: visible };
            if (last?.role === 'assistant' && !last.patches) {
              return [...m.slice(0, -1), next];
            }
            return [...m, next];
          });
        },
        onEvent: (obj) => {
          if (Array.isArray(obj.patches)) {
            receivedPatches = obj.patches as PatchProposal[];
          }
        },
        onDone: () => {
          if (streamingRef.current) {
            onMessageRecorded?.({
              role: 'assistant',
              content: streamingRef.current,
            });
          }
          if (receivedPatches && receivedPatches.length > 0) {
            // Attach patches to the last assistant message and strip
            // the raw JSON from its content so the user sees just the
            // preamble + the diff card. We also snapshot `files` here
            // so the diff stays visible (and accurate) after the user
            // edits the workspace.
            //
            // Normalise the patches against the snapshot RIGHT NOW so
            // the diff card displays the cleaned-up version (correct
            // leads on preserved lines, context-inferred leads on new
            // lines) instead of the raw model output. Without this
            // step the user sees collapsed/garbage whitespace on the
            // proposed side of the diff and is confused why apply
            // produces something different than what they reviewed.
            const snapshot = { ...files };
            const finalPatches = receivedPatches.map((p) => {
              const original = snapshot[p.file];
              if (typeof original !== 'string') return p;
              const fixed = normaliseProposedWhitespace(original, p.contents);
              return fixed === p.contents ? p : { ...p, contents: fixed };
            });
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role !== 'assistant') {
                return [
                  ...m,
                  {
                    role: 'assistant',
                    content: '',
                    patches: finalPatches,
                    filesSnapshot: snapshot,
                  },
                ];
              }
              return [
                ...m.slice(0, -1),
                {
                  role: 'assistant',
                  content: stripPatchJsonFromContent(last.content),
                  patches: finalPatches,
                  filesSnapshot: snapshot,
                },
              ];
            });
          }
        },
        onError: (e) => {
          // Replace the empty assistant placeholder (or append if there
          // isn't one) so the spinner doesn't get stranded above the
          // error bubble.
          setMessages((m) => {
            const last = m[m.length - 1];
            const errMsg: Msg = {
              role: 'assistant',
              content: `Error: ${e.message}`,
            };
            if (last?.role === 'assistant' && !last.content && !last.patches) {
              return [...m.slice(0, -1), errMsg];
            }
            return [...m, errMsg];
          });
        },
      });
    } finally {
      setStreaming(false);
      abortRef.current = null;
      // If we still have a stranded empty assistant bubble (e.g. the
      // model returned an empty response, the SSE closed without
      // delta/patches/error, or the user hit Stop before the first
      // token arrived), drop it so the "Responding…" spinner doesn't
      // linger forever.
      setMessages((m) => {
        const last = m[m.length - 1];
        if (last?.role === 'assistant' && !last.content && !last.patches) {
          return m.slice(0, -1);
        }
        return m;
      });
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  function onComposerKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      send();
    }
  }

  function applyAndMark(idx: number, toApply: PatchProposal[]) {
    // Whitespace defence: models frequently mangle indentation when
    // regenerating files (e.g. halving docstring indent, inflating
    // code body to 16 spaces, emitting newly-added lines at 1 space).
    // normaliseProposedWhitespace runs two passes: restore preserved
    // lines from the original AND infer new-line leads from context
    // (block-opener heuristic). Patches received over SSE are already
    // normalised once on arrival; this is the idempotent re-pass for
    // the workspace-current snapshot in case files changed since.
    const normalised = toApply.map((p) => {
      const original = files[p.file];
      if (typeof original !== 'string') return p;
      const fixed = normaliseProposedWhitespace(original, p.contents);
      return fixed === p.contents ? p : { ...p, contents: fixed };
    });
    onApplyPatches?.(normalised);
    setMessages((m) => {
      const next = [...m];
      const cur = next[idx];
      if (!cur) return m;
      // Keep the diff visible — flip to applied so it renders read-only
      // with an "Applied" badge instead of Accept/Reject buttons. The
      // pre-apply snapshot stays put so the diff doesn't drift as the
      // user keeps editing.
      next[idx] = { ...cur, applied: true, patches: normalised };
      return next;
    });
  }

  function rejectAll(idx: number) {
    setMessages((m) => {
      const next = [...m];
      const cur = next[idx];
      if (!cur) return m;
      // Reject removes the diff card entirely (and the snapshot) —
      // there's nothing meaningful to keep around for a rejected diff.
      next[idx] = { ...cur, patches: undefined, filesSnapshot: undefined };
      return next;
    });
  }

  return (
    <div
      className="flex flex-col"
      style={{ height: '100%', background: 'var(--bg)', minHeight: 0 }}
    >
      <div
        className="flex items-center"
        style={{
          padding: '8px 10px',
          gap: 8,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
        }}
      >
        <ModelSwitcher
          models={models}
          value={override}
          onChange={setOverride}
          disabled={disabled || streaming}
          fullWidth
        />
        <div
          role="tablist"
          aria-label="Chat mode"
          className="ml-auto inline-flex"
          style={{
            background: 'var(--bg-sunken)',
            borderRadius: 999,
            boxShadow: 'inset 0 0 0 1px var(--border)',
            padding: 2,
          }}
        >
          <ModeButton
            active={mode === 'ask'}
            disabled={disabled || streaming}
            onClick={() => setMode('ask')}
            label="Ask"
            icon={<Sparkles size={10} strokeWidth={2} />}
          />
          <ModeButton
            active={mode === 'edit'}
            disabled={disabled || streaming}
            onClick={() => setMode('edit')}
            label="Edit"
            icon={<Wand2 size={10} strokeWidth={2} />}
          />
        </div>
      </div>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 12,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {messages.length === 0 && !streaming && (
          <div
            style={{
              margin: 'auto 0',
              padding: 14,
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
              fontSize: 12.5,
              color: 'var(--text-3)',
              lineHeight: 1.55,
              textAlign: 'center',
            }}
          >
            <div
              className="eyebrow"
              style={{
                marginBottom: 6,
                color: 'var(--accent)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Sparkles size={11} strokeWidth={2} /> AI PAIR
            </div>
            <div>
              Ask about the code or the checkpoint. In{' '}
              <strong style={{ color: 'var(--text-2)' }}>Edit</strong> mode the
              model proposes patches you can review and apply.
            </div>
          </div>
        )}
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          const placeholder =
            isLast &&
            streaming &&
            mode === 'edit' &&
            m.role === 'assistant' &&
            !m.patches
              ? 'Preparing edits…'
              : undefined;
          return (
            <Bubble
              key={i}
              role={m.role}
              content={m.content}
              placeholder={placeholder}
              patches={m.patches}
              applied={m.applied}
              widthPct={bubbleWidthPct}
              // For applied diffs, render against the snapshot we took
              // at apply-time so the diff doesn't drift as the user
              // continues editing the workspace.
              currentFiles={m.applied ? (m.filesSnapshot ?? files) : files}
              onApply={(toApply) => applyAndMark(i, toApply)}
              onReject={() => rejectAll(i)}
            />
          );
        })}
      </div>

      <div
        style={{
          padding: 8,
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
        }}
      >
        <div
          data-ai-processing-glow={streaming ? 'true' : undefined}
          className="flex items-end"
          style={{
            gap: 6,
            background: 'var(--bg)',
            borderRadius: 'var(--radius)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            padding: '6px 6px 6px 10px',
          }}
        >
          <textarea
            ref={composerRef}
            aria-label="Message to AI assistant"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onComposerKey}
            disabled={disabled || streaming}
            placeholder={
              disabled
                ? 'AI disabled for this checkpoint'
                : mode === 'edit'
                  ? 'Describe the change…'
                  : 'Ask the model…'
            }
            rows={1}
            style={{
              flex: 1,
              resize: 'none',
              background: 'transparent',
              border: 0,
              outline: 'none',
              color: 'var(--text)',
              fontSize: 13,
              fontFamily: 'var(--font-sans)',
              lineHeight: 1.45,
              padding: '4px 0',
              minHeight: 22,
              maxHeight: 160,
            }}
          />
          {streaming ? (
            <StopButton onClick={stop} />
          ) : (
            <SendButton
              onClick={send}
              disabled={!!disabled || !draft.trim()}
            />
          )}
        </div>
      </div>
    </div>
  );
}

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
    // Toggle on every triple-quote occurrence in the line.
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
 *
 * Edit history:
 * - v1 iterated candidates [2, 4, 3, 8] and picked the first that
 *   divided all widths — silently coerced 4-space → 2-space. Bad.
 * - v2 used min-width across all indented lines — broke on Python
 *   files where docstring-interior lines were indented narrower
 *   than the function body (the wordcount.py case).
 * - v3 (here) excludes docstring interior lines via triple-quote
 *   tracking, so the "real" code indent wins.
 */
export function detectIndentUnit(text: string): string | null {
  const lines = text.split('\n');
  const insideStr = isInsideTripleQuotes(text);
  let tabLines = 0;
  let spaceLines = 0;
  let minSpaceWidth = Infinity;
  for (let i = 0; i < lines.length; i++) {
    if (insideStr[i]) continue; // line is inside a docstring → skip
    const line = lines[i];
    if (!line || /^\s*$/.test(line)) continue;
    const m = line.match(/^([ \t]+)/);
    if (!m) continue;
    const lead = m[1];
    // Mixed lead (tabs + spaces) is ambiguous — skip.
    if (lead.includes('\t') && lead.includes(' ')) continue;
    if (lead[0] === '\t') {
      tabLines += 1;
    } else {
      spaceLines += 1;
      if (lead.length < minSpaceWidth) minSpaceWidth = lead.length;
    }
  }
  // Tabs win iff they dominate. Otherwise fall back to spaces.
  if (tabLines > 0 && tabLines >= spaceLines) return '\t';
  if (spaceLines === 0 || minSpaceWidth === Infinity) return null;
  return ' '.repeat(minSpaceWidth);
}

/**
 * If `proposed` was emitted with a different indent style than `original`,
 * rewrite proposed's leading whitespace so it matches original's unit.
 * No-op when the styles already agree, when either file has no indented
 * lines, or when the proposed file has tab-mixed leading whitespace
 * (we don't want to risk breaking deliberate alignment).
 */
/**
 * Content-preserving whitespace pass. For each line in `proposed`,
 * if its trimmed body uniquely matches a line in `original`, restore
 * the original's leading whitespace. Only touches lines that
 * unambiguously survive the patch — new lines, modified lines, and
 * lines that appear multiple times in the original (where matching
 * is ambiguous) are passed through verbatim.
 *
 * Why this exists: even with the strongest prompt, models routinely
 * "tidy" docstring or comment indentation when regenerating the file
 * (observed on wordcount.py: 2-space spec lines silently halved to
 * 1-space). matchIndentStyle correctly leaves docstring lines alone
 * — they're string payload, not code indent — but that means the
 * bad indent reaches the file. This pass surgically restores it.
 *
 * Idempotent and safe: if proposed already matches original exactly
 * for a given line, this is a no-op for that line.
 */
export function preserveOriginalWhitespace(
  original: string,
  proposed: string,
): string {
  const oLines = original.split('\n');
  const pLines = proposed.split('\n');
  // Index original lines by trimmed body. Only entries with exactly
  // ONE original line are usable — otherwise we can't tell which
  // original-indent the proposed line should inherit.
  const trimmedToLead = new Map<string, string | null>();
  for (const o of oLines) {
    const trimmed = o.trimStart();
    if (!trimmed) continue;
    const lead = o.slice(0, o.length - trimmed.length);
    if (trimmedToLead.has(trimmed)) {
      // Multiple originals match this trimmed body → ambiguous.
      trimmedToLead.set(trimmed, null);
    } else {
      trimmedToLead.set(trimmed, lead);
    }
  }
  return pLines
    .map((line) => {
      const trimmed = line.trimStart();
      if (!trimmed) return line; // blank line — leave alone
      const wantLead = trimmedToLead.get(trimmed);
      if (wantLead == null) return line; // not unique → leave alone
      const haveLead = line.slice(0, line.length - trimmed.length);
      if (haveLead === wantLead) return line; // already correct
      return wantLead + trimmed;
    })
    .join('\n');
}

/**
 * Second-pass indent fixer for the lines `preserveOriginalWhitespace`
 * couldn't help — the genuinely-new lines (no body match in original).
 * Walks proposed top-to-bottom, and for each new line whose lead is
 * "suspicious" (not a clean multiple of the indent unit, or shallower
 * than where a parent block-opener would put it, or deeper than the
 * preceding line warrants), rewrites the lead to the context-inferred
 * value.
 *
 * Inference rule (block-opener heuristic):
 *   expected = prevLead + indentUnit  (if previous non-blank line ends
 *              with `:`/`{`/`(`/`[`/`=>`)
 *   expected = prevLead               (otherwise — sibling at same depth)
 *
 * Conservative on preserved lines (leaves them at their preserved
 * lead — the case where the model intentionally re-nested a preserved
 * line into a new block requires real parsing to detect, and any
 * heuristic that overrides preserves risks breaking deliberate dedents
 * like `else:` clauses).
 *
 * Used as the second pass in `normaliseProposedWhitespace`.
 */
export function inferIndentForNewLines(
  original: string,
  proposed: string,
): string {
  const indentUnit = detectIndentUnit(original);
  if (!indentUnit) return proposed;
  const unitWidth = indentUnit === '\t' ? 1 : indentUnit.length;

  // Same trimmed-body → unique-lead map as preserveOriginalWhitespace
  // — used here only to identify which proposed lines are NEW (not
  // present in the original) so we don't override preserved leads.
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

  // Effective lead each output line carries — fed forward as context
  // for subsequent lines' inference.
  const effectiveLeads: string[] = new Array(pLines.length).fill('');
  const result: string[] = new Array(pLines.length);

  for (let i = 0; i < pLines.length; i++) {
    const line = pLines[i];
    const trimmed = line.trimStart();
    const haveLead = line.slice(0, line.length - trimmed.length);

    if (!trimmed || insideStr[i]) {
      // Blank or inside docstring — pass through verbatim.
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    const wantLead = trimmedToLead.get(trimmed);
    if (wantLead != null) {
      // Preserved line — keep its (already-restored) lead.
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    // NEW line. Look back for the most recent non-blank, non-docstring
    // line in the input — that's our context anchor.
    let j = i - 1;
    while (j >= 0 && (!pLines[j].trim() || insideStr[j])) j--;
    if (j < 0) {
      // No preceding context (start of file) — keep model's lead.
      result[i] = line;
      effectiveLeads[i] = haveLead;
      continue;
    }

    const prevLead = effectiveLeads[j];
    const prevTrimmed = pLines[j].trimStart();
    // Strip trailing line comments before testing for block-opener
    // tokens. Both `//` (JS/TS/Java/C) and `#` (Python/shell).
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

    // Decide whether the model's lead is "wrong enough" to override.
    // Three failure modes we override on:
    //   1. Not a clean multiple of the indent unit (e.g. 1-space when
    //      unit is 4 — the wordcount.py "key=...".strip() case).
    //   2. Shallower than the expected child depth when the previous
    //      line opened a block (model under-indented a child).
    //   3. Deeper than the expected sibling depth when no block opener
    //      precedes it (model over-indented). Only one extra level is
    //      tolerated — beyond that is almost certainly garbage.
    //
    // Otherwise, the model's lead is plausible — keep it. This protects
    // legitimate dedents like an `else:` clause that follows a block.
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
 * model-emitted patch contents:
 *   1. preserveOriginalWhitespace — restores leads on lines whose
 *      body still matches the original (the "model didn't change this
 *      line, why is the indent different" case).
 *   2. inferIndentForNewLines — fills in plausible leads for newly
 *      inserted lines whose lead the model mangled (the "if key:" /
 *      "key = w.lower()..." 1-space-lead case from wordcount.py).
 *
 * Called at THREE points so the cleaned version flows everywhere:
 *   - SSE `onDone`: normalise patches as soon as they arrive so the
 *     diff card displays clean whitespace, not raw model garbage.
 *   - useState rehydrate: same, on page-refresh restore.
 *   - applyAndMark: idempotent re-normalisation against current
 *     workspace so the apply matches what the diff showed.
 */
export function normaliseProposedWhitespace(
  original: string,
  proposed: string,
): string {
  const preserved = preserveOriginalWhitespace(original, proposed);
  return inferIndentForNewLines(original, preserved);
}

export function matchIndentStyle(original: string, proposed: string): string {
  const wantUnit = detectIndentUnit(original);
  const haveUnit = detectIndentUnit(proposed);
  if (!wantUnit || !haveUnit || wantUnit === haveUnit) return proposed;
  // Compute width-per-step for the proposed style. If it's tab-based,
  // each leading tab becomes one step. If space-based, the step length
  // is haveUnit's length.
  const haveIsTab = haveUnit === '\t';
  const haveStep = haveIsTab ? 1 : haveUnit.length;
  // Lines INSIDE a docstring are part of the string's payload — their
  // leading whitespace is content, not code indent. Re-indenting them
  // would mutate the string's value. Identify them and pass through
  // verbatim. (Same triple-quote tracker we use for detection.)
  const lines = proposed.split('\n');
  const insideStr = isInsideTripleQuotes(proposed);
  return lines
    .map((line, i) => {
      if (insideStr[i]) return line;
      const m = line.match(/^([ \t]+)/);
      if (!m) return line;
      const lead = m[1];
      // Mixed tabs+spaces in the proposed lead → bail out for this line.
      if (lead.includes('\t') && lead.includes(' ')) return line;
      const steps = haveIsTab
        ? lead.length // each tab = 1 step
        : Math.floor(lead.length / haveStep);
      const leftover = haveIsTab ? 0 : lead.length % haveStep;
      const rest = line.slice(lead.length);
      return wantUnit.repeat(steps) + ' '.repeat(leftover) + rest;
    })
    .join('\n');
}

/** Send pill that surfaces the ⌘ Enter shortcut inline (so we don't
 *  need a helper row beneath the composer). Goes muted when disabled. */
function SendButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label="Send message"
      title="Send (⌘ Enter)"
      className="inline-flex items-center"
      style={{
        gap: 6,
        height: 28,
        padding: '0 4px 0 10px',
        border: 0,
        borderRadius: 999,
        background: disabled ? 'var(--bg-sunken)' : 'var(--accent)',
        color: disabled ? 'var(--text-4)' : 'var(--bg)',
        cursor: disabled ? 'default' : 'pointer',
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      <span>Send</span>
      <span
        className="mono inline-flex items-center"
        aria-hidden="true"
        style={{
          fontSize: 9.5,
          letterSpacing: '0.04em',
          padding: '2px 6px',
          marginRight: 2,
          borderRadius: 999,
          background: disabled ? 'transparent' : 'rgba(0,0,0,0.18)',
          color: disabled ? 'var(--text-4)' : 'var(--bg)',
          opacity: disabled ? 0.6 : 1,
        }}
      >
        ⌘ ↵
      </span>
    </button>
  );
}

/** Replaces SendButton while the AI is streaming so the user has a
 *  clear way to interrupt a long/destructive response. Aborts the
 *  in-flight SSE via the panel's AbortController. */
function StopButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Stop AI response"
      title="Stop AI response"
      className="inline-flex items-center"
      style={{
        gap: 6,
        height: 28,
        padding: '0 12px',
        border: 0,
        borderRadius: 999,
        background: 'var(--plum)',
        color: 'var(--bg)',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      <Square size={10} strokeWidth={0} fill="currentColor" />
      <span>Stop</span>
    </button>
  );
}

function ModeButton({
  active,
  disabled,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      role="tab"
      aria-selected={active}
      className="inline-flex items-center gap-1"
      style={{
        padding: '3px 9px',
        fontSize: 11,
        fontWeight: active ? 600 : 500,
        background: active ? 'var(--accent)' : 'transparent',
        color: active ? 'var(--bg)' : 'var(--text-3)',
        border: 0,
        borderRadius: 999,
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled && !active ? 0.5 : 1,
      }}
    >
      {icon}
      {label}
    </button>
  );
}

const Bubble = memo(function Bubble({
  role,
  content,
  placeholder,
  patches,
  applied,
  widthPct,
  currentFiles,
  onApply,
  onReject,
}: {
  role: 'user' | 'assistant';
  content: string;
  /** Replaces the "…" thinking dots when set — used during /edit
   *  streaming to show "Preparing edits…" instead of a blank bubble. */
  placeholder?: string;
  patches?: PatchProposal[];
  applied?: boolean;
  /** Bubble width as a percentage of the chat scroll container width.
   *  Tiered by parent ResizeObserver: 90/95/100 depending on rail size. */
  widthPct?: number;
  currentFiles: Record<string, string>;
  onApply?: (patches: PatchProposal[]) => void;
  onReject?: () => void;
}) {
  const isUser = role === 'user';
  return (
    <div
      className="flex"
      style={{
        gap: 8,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          flexShrink: 0,
          width: 22,
          height: 22,
          borderRadius: 999,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: isUser ? 'var(--bg-sunken)' : 'var(--accent-soft)',
          color: isUser ? 'var(--text-3)' : 'var(--accent)',
          marginTop: 2,
        }}
      >
        {isUser ? (
          <User size={11} strokeWidth={2} />
        ) : (
          <Sparkles size={11} strokeWidth={2} />
        )}
      </span>
      <div
        style={{
          maxWidth: `${widthPct ?? 90}%`,
          flex: '1 1 auto',
          minWidth: 0,
          padding: '8px 10px',
          background: isUser ? 'var(--bg-sunken)' : 'var(--bg-elev)',
          borderRadius: 'var(--radius)',
          fontSize: 13,
          color: 'var(--text)',
          lineHeight: 1.5,
          wordWrap: 'break-word',
          boxShadow: isUser ? 'none' : 'inset 0 0 0 1px var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {content && (
          <div style={{ minWidth: 0 }}>
            {isUser ? (
              <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
            ) : (
              <BlockMarkdown text={content} />
            )}
          </div>
        )}
        {!content && !patches && (
          <span
            className="inline-flex items-center"
            style={{ gap: 8, fontSize: 13, fontWeight: 600 }}
          >
            <span
              aria-hidden="true"
              style={{
                width: 7,
                height: 7,
                borderRadius: 999,
                background: 'var(--accent)',
                boxShadow: '0 0 8px var(--accent)',
                animation: 'rounds-ai-pulse 1.2s ease-in-out infinite',
              }}
            />
            <span className="rounds-ai-shimmer">
              {placeholder ?? 'Responding…'}
            </span>
          </span>
        )}
        {patches && patches.length > 0 && (
          <AIPatchView
            patches={patches}
            currentFiles={currentFiles}
            applied={applied}
            onApply={applied ? undefined : (toApply) => onApply?.(toApply)}
            onRejectAll={applied ? undefined : () => onReject?.()}
          />
        )}
      </div>
    </div>
  );
});
