import { useEffect, useRef, useState } from 'react';
import { runnerSSE } from '../../lib/runnerFetch';
import ModelSwitcher, { type ModelOverride } from './ModelSwitcher';
import { listAICodingModels, type AICodingModel } from '../../pages/ai-coding/aiCodingApi';
import AIPatchView, { type PatchProposal } from './AIPatchView';

type Msg = { role: 'user' | 'assistant'; content: string };

type Mode = 'ask' | 'edit';

type Props = {
  roundSlug: string;
  checkpointIndex: number;
  files: Record<string, string>;
  checkpointPrompt?: string;
  disabled?: boolean;
  onMessageRecorded?: (m: Msg) => void;
  onApplyPatches?: (patches: PatchProposal[]) => void;
};

export default function AIChatPanel({
  roundSlug,
  checkpointIndex,
  files,
  checkpointPrompt,
  disabled,
  onMessageRecorded,
  onApplyPatches,
}: Props) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const streamingRef = useRef<string>('');
  const [models, setModels] = useState<AICodingModel[]>([]);
  const [override, setOverride] = useState<ModelOverride>(null);
  const [mode, setMode] = useState<Mode>('ask');
  const [pendingPatches, setPendingPatches] = useState<PatchProposal[] | null>(null);

  useEffect(() => {
    listAICodingModels()
      .then(setModels)
      .catch((err) => {
        // The dropdown gracefully falls back to "Default model" only,
        // but a 401/500 here means the user's configured providers
        // can't be reached — surface it so they can debug.
        console.warn('[ai-coding] failed to load model list:', err);
        setModels([]);
      });
  }, []);

  function stripPatchArrayTrailingMessage() {
    setMessages((m) => {
      const last = m[m.length - 1];
      if (last?.role !== 'assistant') return m;
      const t = last.content.trim();
      if (!t.startsWith('[') || !t.endsWith(']')) return m;
      try {
        const arr = JSON.parse(t);
        if (Array.isArray(arr) && arr.every((x) => typeof x === 'object' && x?.patch_kind)) {
          return m.slice(0, -1);
        }
      } catch {
        /* not JSON — leave it */
      }
      return m;
    });
  }

  async function send() {
    if (!draft.trim() || streaming) return;
    const userMsg: Msg = { role: 'user', content: draft };
    setMessages((m) => [...m, userMsg]);
    onMessageRecorded?.(userMsg);
    setDraft('');
    setStreaming(true);
    streamingRef.current = '';
    const path = mode === 'edit' ? '/api/ai-coding/edit' : '/api/ai-coding/chat';
    try {
      let receivedPatches: PatchProposal[] | null = null;
      await runnerSSE(path, {
        method: 'POST',
        auth: 'optional',
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
          setMessages((m) => {
            const last = m[m.length - 1];
            if (last?.role === 'assistant' && last.content === streamingRef.current.slice(0, last.content.length)) {
              return [...m.slice(0, -1), { role: 'assistant', content: streamingRef.current }];
            }
            return [...m, { role: 'assistant', content: streamingRef.current }];
          });
        },
        onEvent: (obj) => {
          // /edit emits a final {patches, parse_error?} event before {done}
          if (Array.isArray(obj.patches)) {
            receivedPatches = obj.patches as PatchProposal[];
          }
        },
        onDone: () => {
          if (streamingRef.current) {
            onMessageRecorded?.({ role: 'assistant', content: streamingRef.current });
          }
          // Empty patches array = model deliberately declined (per the
          // EDIT_SYSTEM_PROMPT contract). Don't render an empty review
          // surface; the assistant's prose message tells the user why.
          if (receivedPatches && receivedPatches.length > 0) {
            setPendingPatches(receivedPatches);
          }
        },
        onError: (e) => {
          setMessages((m) => [...m, { role: 'assistant', content: `Error: ${e.message}` }]);
        },
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col" style={{ height: '100%', background: 'var(--bg-elev)' }}>
      <div className="border-b flex items-center gap-2" style={{ padding: '6px 10px' }}>
        <span className="text-3 text-xs">Model:</span>
        <ModelSwitcher
          models={models}
          value={override}
          onChange={setOverride}
          disabled={disabled || streaming}
        />
        <div className="ml-auto inline-flex rounded" style={{ overflow: 'hidden' }}>
          <button
            type="button"
            onClick={() => setMode('ask')}
            disabled={disabled || streaming || pendingPatches !== null}
            className="px-2 py-1 text-xs"
            style={{
              background: mode === 'ask' ? 'var(--accent)' : 'var(--bg-elev-2)',
              color: mode === 'ask' ? 'var(--bg)' : 'var(--text-2)',
              border: 0,
            }}
          >
            Ask
          </button>
          <button
            type="button"
            onClick={() => setMode('edit')}
            disabled={disabled || streaming || pendingPatches !== null}
            className="px-2 py-1 text-xs"
            style={{
              background: mode === 'edit' ? 'var(--accent)' : 'var(--bg-elev-2)',
              color: mode === 'edit' ? 'var(--bg)' : 'var(--text-2)',
              border: 0,
            }}
          >
            Edit
          </button>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.length === 0 && (
          <div className="text-3 text-sm">Ask a question about the code or the checkpoint goal.</div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className="card"
            style={{
              padding: 10,
              marginBottom: 8,
              background: m.role === 'user' ? 'var(--bg)' : 'var(--bg-elev-2)',
            }}
          >
            <div className="text-3 text-xs mb-1">{m.role}</div>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13.5 }}>{m.content}</div>
          </div>
        ))}
      </div>
      {pendingPatches && (
        <div className="border-t" style={{ background: 'var(--bg-elev-2)' }}>
          <AIPatchView
            patches={pendingPatches}
            currentFiles={files}
            onApply={(toApply) => {
              onApplyPatches?.(toApply);
              setPendingPatches(null);
              stripPatchArrayTrailingMessage();
            }}
            onRejectAll={() => {
              setPendingPatches(null);
              stripPatchArrayTrailingMessage();
            }}
          />
        </div>
      )}
      <div className="border-t flex items-center gap-2" style={{ padding: 8 }}>
        <textarea
          aria-label="Message to AI assistant"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={disabled || streaming}
          placeholder={disabled ? 'AI disabled for this checkpoint' : 'Ask the model'}
          rows={2}
          style={{ flex: 1, resize: 'none' }}
        />
        <button type="button" onClick={send} disabled={disabled || streaming || !draft.trim()}>
          {streaming ? '…' : 'Send'}
        </button>
      </div>
    </div>
  );
}
