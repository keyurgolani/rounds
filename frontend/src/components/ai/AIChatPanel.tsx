import { useCallback, useMemo, useRef, useState } from 'react';
import { Sparkles, Wand2 } from 'lucide-react';
import { runnerSSE } from '../../lib/runnerFetch';
import ChatPanel, {
  type ChatMessage,
  type ChatSendArgs,
} from '../chat/ChatPanel';
import type { ChatPanelHandle } from '../chat/chatTypes';
import AIPatchView, { type PatchProposal } from './AIPatchView';
import { splitPatches } from './aiPatches';
import { normaliseProposedWhitespace } from './aiPatchWhitespace';

// Re-export the whitespace helpers from their new home so existing
// callers (tests in __tests__/ai-coding/, GradeReport) keep working
// without import-path churn.
export {
  detectIndentUnit,
  preserveOriginalWhitespace,
  inferIndentForNewLines,
  normaliseProposedWhitespace,
  matchIndentStyle,
} from './aiPatchWhitespace';

type Mode = 'ask' | 'edit';

/** Per-message extras the AI Coding chat attaches: a patch proposal
 *  (with its files snapshot), and the applied flag. The snapshot is
 *  the workspace's state at apply time so the diff doesn't drift as
 *  the user keeps editing afterwards. */
type AIChatExtras = {
  patches?: PatchProposal[];
  applied?: boolean;
  filesSnapshot?: Record<string, string>;
};

type ChatMsg = ChatMessage<AIChatExtras>;

type Props = {
  roundSlug: string;
  checkpointIndex: number;
  files: Record<string, string>;
  checkpointPrompt?: string;
  disabled?: boolean;
  initialMessages?: Array<{ role: 'user' | 'assistant'; content: string }>;
  onMessageRecorded?: (m: { role: 'user' | 'assistant'; content: string }) => void;
  onApplyPatches?: (patches: PatchProposal[]) => void;
};

/**
 * AI pair-programming chat. Built on the shared ChatPanel; the AI-
 * Coding-specific behaviour lives here:
 *   - Ask vs Edit mode toggle in the header
 *   - /edit endpoint streams JSON-only; we hide the JSON tail while it
 *     accumulates so the user sees prose-only preamble
 *   - Patches arrive as a separate SSE event; we attach them as
 *     per-message extras and render the diff card via renderExtras
 *   - Apply/Reject flips the `applied` flag on the historical
 *     message via the panel's imperative `updateMessage` handle
 *   - Initial messages with persisted patch JSON are rehydrated via
 *     `splitPatches` so refresh doesn't dump raw JSON
 */
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
  const [mode, setMode] = useState<Mode>('ask');
  const filesRef = useRef(files);
  filesRef.current = files;
  const chatRef = useRef<ChatPanelHandle<AIChatExtras>>(null);

  // Rehydrate persisted messages — parse out any trailing JSON patch
  // tail so the bubble shows the diff card instead of raw JSON.
  const seedMessages = useMemo<ChatMsg[] | undefined>(() => {
    if (!initialMessages) return undefined;
    const startFiles = filesRef.current;
    return initialMessages.map((m, i): ChatMsg => {
      if (m.role !== 'assistant') {
        return { id: `seed-${i}`, role: m.role, content: m.content };
      }
      const { prose, patches } = splitPatches(m.content);
      if (!patches || patches.length === 0) {
        return { id: `seed-${i}`, role: 'assistant', content: m.content };
      }
      const cleaned = patches.map((p) => {
        const original = startFiles[p.file];
        if (typeof original !== 'string') return p;
        const fixed = normaliseProposedWhitespace(original, p.contents);
        return fixed === p.contents ? p : { ...p, contents: fixed };
      });
      return {
        id: `seed-${i}`,
        role: 'assistant',
        content: prose,
        // Do NOT mark as applied on rehydrate — we have no record of
        // whether the user actually accepted before refresh.
        extras: { patches: cleaned, applied: false },
      };
    });
  }, [initialMessages]);

  const handleSend = useCallback(
    async (args: ChatSendArgs<AIChatExtras>) => {
      const { text, history, override, signal, callbacks } = args;
      const currentFiles = filesRef.current;
      const path =
        mode === 'edit' ? '/api/ai-coding/edit' : '/api/ai-coding/chat';

      // Wire-shape history: prior conversation + the user message
      // (sliced off the streaming placeholder). The backend expects
      // {role, content} entries.
      const priorPlusUser = history.slice(0, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      let accumulated = '';
      let receivedPatches: PatchProposal[] | null = null;

      try {
        await runnerSSE(path, {
          method: 'POST',
          auth: 'optional',
          signal,
          body: {
            round_slug: roundSlug,
            checkpoint_index: checkpointIndex,
            provider_id: override?.provider_id,
            model: override?.model,
            messages: [
              ...priorPlusUser.slice(0, -1),
              { role: 'user', content: text },
            ],
            files: currentFiles,
            checkpoint_prompt: checkpointPrompt,
          },
          onDelta: (t) => {
            accumulated += t;
            // In /edit mode the backend streams the raw JSON token by
            // token — strip any nascent JSON tail so the user sees
            // only any prose preamble (usually empty) while the patch
            // accumulates in the background.
            const visible =
              mode === 'edit'
                ? stripPatchJsonFromContent(accumulated)
                : accumulated;
            callbacks.replaceText(visible);
          },
          onEvent: (obj) => {
            if (Array.isArray(obj.patches)) {
              receivedPatches = obj.patches as PatchProposal[];
            }
          },
          onDone: () => {
            if (accumulated) {
              onMessageRecorded?.({
                role: 'assistant',
                content: accumulated,
              });
            }
            if (receivedPatches && receivedPatches.length > 0) {
              const snapshot = { ...filesRef.current };
              const finalPatches = receivedPatches.map((p) => {
                const original = snapshot[p.file];
                if (typeof original !== 'string') return p;
                const fixed = normaliseProposedWhitespace(
                  original,
                  p.contents,
                );
                return fixed === p.contents
                  ? p
                  : { ...p, contents: fixed };
              });
              // Strip the raw JSON from the visible content; attach
              // patches as extras with a snapshot for diff stability.
              callbacks.replaceText(stripPatchJsonFromContent(accumulated));
              callbacks.setExtras(() => ({
                patches: finalPatches,
                filesSnapshot: snapshot,
                applied: false,
              }));
            }
          },
          onError: (e) => {
            callbacks.error(e);
          },
        });
      } catch (err) {
        if ((err as { name?: string }).name === 'AbortError') return;
        throw err;
      }
    },
    [
      mode,
      roundSlug,
      checkpointIndex,
      checkpointPrompt,
      onMessageRecorded,
    ],
  );

  const onUserCommitted = useCallback(
    (m: ChatMsg) => {
      if (m.role === 'user') {
        onMessageRecorded?.({ role: 'user', content: m.content });
      }
    },
    [onMessageRecorded],
  );

  // Apply patches against the current workspace, then flip the message
  // to applied=true so the diff card switches to a read-only badge.
  const handleApply = useCallback(
    (id: string, toApply: PatchProposal[]) => {
      const current = filesRef.current;
      const normalised = toApply.map((p) => {
        const original = current[p.file];
        if (typeof original !== 'string') return p;
        const fixed = normaliseProposedWhitespace(original, p.contents);
        return fixed === p.contents ? p : { ...p, contents: fixed };
      });
      onApplyPatches?.(normalised);
      chatRef.current?.updateMessage(id, (m) => ({
        ...m,
        extras: {
          ...(m.extras ?? {}),
          patches: normalised,
          applied: true,
        },
      }));
    },
    [onApplyPatches],
  );

  const handleReject = useCallback((id: string) => {
    chatRef.current?.updateMessage(id, (m) => ({
      ...m,
      extras: {
        ...(m.extras ?? {}),
        patches: undefined,
        filesSnapshot: undefined,
      },
    }));
  }, []);

  return (
    <ChatPanel<AIChatExtras>
      ref={chatRef}
      onSend={handleSend}
      initialMessages={seedMessages}
      onMessageRecorded={onUserCommitted}
      disabled={disabled}
      composerPlaceholder={
        disabled
          ? 'AI disabled for this checkpoint'
          : mode === 'edit'
            ? 'Describe the change…'
            : 'Ask the model…'
      }
      streamingPlaceholder={mode === 'edit' ? 'Preparing edits…' : undefined}
      headerRight={
        <ModeToggle
          mode={mode}
          onChange={setMode}
          disabled={disabled}
        />
      }
      emptyState={<AIChatEmpty />}
      renderExtras={(msg) => {
        const patches = msg.extras?.patches;
        if (!patches || patches.length === 0) return null;
        const applied = !!msg.extras?.applied;
        const currentForDiff = applied
          ? (msg.extras?.filesSnapshot ?? filesRef.current)
          : filesRef.current;
        return (
          <AIPatchView
            patches={patches}
            currentFiles={currentForDiff}
            applied={applied}
            onApply={applied ? undefined : (toApply) => handleApply(msg.id, toApply)}
            onRejectAll={applied ? undefined : () => handleReject(msg.id)}
          />
        );
      }}
    />
  );
}

function ModeToggle({
  mode,
  onChange,
  disabled,
}: {
  mode: Mode;
  onChange: (m: Mode) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="tablist"
      aria-label="Chat mode"
      className="inline-flex"
      style={{
        background: 'var(--bg-sunken)',
        borderRadius: 999,
        boxShadow: 'inset 0 0 0 1px var(--border)',
        padding: 2,
      }}
    >
      <ModeButton
        active={mode === 'ask'}
        disabled={disabled}
        onClick={() => onChange('ask')}
        label="Ask"
        icon={<Sparkles size={10} strokeWidth={2} />}
      />
      <ModeButton
        active={mode === 'edit'}
        disabled={disabled}
        onClick={() => onChange('edit')}
        label="Edit"
        icon={<Wand2 size={10} strokeWidth={2} />}
      />
    </div>
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

function AIChatEmpty() {
  return (
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
  );
}

/**
 * The /edit endpoint contract: the model outputs ONLY a JSON array,
 * optionally inside a ```json fence. Strip everything from the first
 * plausible JSON-array opener to the end so users see only any prose
 * preamble (usually empty for /edit) while the patch is being
 * generated. Intentionally greedy — prose AFTER the JSON is discarded
 * because the parsed patches tell the real story.
 */
function stripPatchJsonFromContent(content: string): string {
  const fenced = content.search(/```(?:json)?\s*\[/);
  if (fenced !== -1) return content.slice(0, fenced).trimEnd();
  const idx = content.indexOf('[');
  if (idx !== -1) return content.slice(0, idx).trimEnd();
  return content;
}
