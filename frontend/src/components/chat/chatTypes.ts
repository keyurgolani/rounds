/**
 * Shared types for the generic ChatPanel.
 *
 * The generic parameter `E` is "extras" — caller-defined per-message
 * data that the shared component is content-agnostic about. AI Coding
 * uses it for patch proposals + apply state; SD practice uses it for
 * tool-call chips; Take-Home doesn't use it at all (`E = never`).
 */
import type { AICodingModel } from '../../pages/ai-coding/aiCodingApi';
import type { ModelOverride } from '../ai/ModelSwitcher';

export type ChatRole = 'user' | 'assistant';

export type ChatMessage<E = unknown> = {
  /** Stable id. Caller may supply one; ChatPanel auto-generates if not. */
  id: string;
  role: ChatRole;
  content: string;
  /** Per-message extras (patches, tool-call chips, …). */
  extras?: E;
  /** When true, the bubble shows the streaming pulse instead of body. */
  streaming?: boolean;
  /** When true, this assistant bubble is in an error state. */
  isError?: boolean;
};

/** Callbacks the caller's `onSend` uses to drive the assistant bubble. */
export type ChatStreamCallbacks<E = unknown> = {
  /** Append a text chunk to the in-flight assistant bubble. */
  appendText: (chunk: string) => void;
  /** Replace the in-flight assistant bubble text wholesale.
   *  AI Coding uses this to strip the streaming JSON tail in /edit
   *  mode without re-allocating on every delta. */
  replaceText: (next: string) => void;
  /** Read or update extras on the in-flight assistant bubble. The
   *  updater receives the current value (or undefined) and returns
   *  the next value (or undefined to clear). */
  setExtras: (updater: (prev: E | undefined) => E | undefined) => void;
  /** Surface an error. Replaces the empty placeholder bubble (or
   *  appends a new one) with role='assistant', isError=true. */
  error: (err: Error | string) => void;
};

/** Arguments passed to the caller's `onSend` handler. */
export type ChatSendArgs<E = unknown> = {
  /** The trimmed user text that triggered this send. */
  text: string;
  /** The conversation history INCLUDING the just-appended user
   *  message AND the streaming-placeholder assistant message. */
  history: ChatMessage<E>[];
  /** Model picker value, or null if "active default". */
  override: ModelOverride;
  /** Abort signal wired to the Stop button. */
  signal: AbortSignal;
  /** Stream callbacks. */
  callbacks: ChatStreamCallbacks<E>;
};

export type ChatPanelHandle<E = unknown> = {
  /** Returns the current message list. */
  getMessages: () => ChatMessage<E>[];
  /** Programmatically clear the conversation. */
  reset: () => void;
  /** Mutate a single message by id. The patch function gets the
   *  current message and returns a new one. No-op if no message
   *  with that id exists. Used by AI Coding to flip the "applied"
   *  flag on a historical assistant turn from the Apply/Reject
   *  buttons in the patch card. */
  updateMessage: (
    id: string,
    patch: (m: ChatMessage<E>) => ChatMessage<E>,
  ) => void;
};

/** Optional filter applied to the model list (e.g. anthropic-only). */
export type ModelFilter = (m: AICodingModel) => boolean;
