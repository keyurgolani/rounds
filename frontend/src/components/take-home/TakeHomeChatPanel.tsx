import { useCallback } from 'react';
import { Sparkles } from 'lucide-react';
import { runnerSSE } from '../../lib/runnerFetch';
import ChatPanel, {
  type ChatMessage,
  type ChatSendArgs,
} from '../chat/ChatPanel';

type Msg = { role: 'user' | 'assistant'; content: string };

type Props = {
  assignmentSlug: string;
  files: Record<string, string>;
  disabled?: boolean;
  initialMessages?: Msg[];
  onMessageRecorded?: (m: Msg) => void;
};

/**
 * Take-home assignment chat. Pure prose — no per-message extras, no
 * tool-calling. The shared ChatPanel does all the heavy lifting; this
 * file just owns the SSE wiring to /api/take-home/chat.
 */
export default function TakeHomeChatPanel({
  assignmentSlug,
  files,
  disabled,
  initialMessages,
  onMessageRecorded,
}: Props) {
  const handleSend = useCallback(
    async (args: ChatSendArgs<never>) => {
      const { history, override, signal, callbacks } = args;
      // history includes the just-appended user message AND the empty
      // streaming placeholder — we want everything UP TO the user
      // message inclusive when sending to the backend.
      const priorPlusUser = history.slice(0, -1).map<Msg>((m) => ({
        role: m.role,
        content: m.content,
      }));
      let acc = '';
      await runnerSSE('/api/take-home/chat', {
        method: 'POST',
        auth: 'optional',
        signal,
        body: {
          assignment_slug: assignmentSlug,
          provider_id: override?.provider_id,
          model: override?.model,
          messages: priorPlusUser,
          files,
        },
        onDelta: (t) => {
          acc += t;
          callbacks.appendText(t);
        },
        onDone: () => {
          if (acc) {
            onMessageRecorded?.({ role: 'assistant', content: acc });
          }
        },
        onError: (e) => {
          callbacks.error(e);
        },
      });
    },
    [assignmentSlug, files, onMessageRecorded],
  );

  const seed: ChatMessage<never>[] | undefined = initialMessages?.map((m, i) => ({
    id: `seed-${i}`,
    role: m.role,
    content: m.content,
  }));

  return (
    <ChatPanel<never>
      onSend={handleSend}
      initialMessages={seed}
      disabled={disabled}
      composerPlaceholder={disabled ? 'AI disabled' : 'Ask the model…'}
      onMessageRecorded={(m) => {
        if (m.role === 'user') {
          onMessageRecorded?.({ role: 'user', content: m.content });
        }
      }}
      emptyState={
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
          <div>Ask about the prompt or your code.</div>
        </div>
      }
    />
  );
}
