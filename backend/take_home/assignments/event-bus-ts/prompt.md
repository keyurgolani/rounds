# Event Bus

A small editor app you're working on has features wired together with
direct method calls, and the result is a dependency knot — the toolbar
imports the document, the document imports the inspector, the
inspector imports back into the toolbar. You're going to break that
with a tiny pub/sub bus: features `emit` events, other features
subscribe with `on`. No external deps; this lives in the editor's lib
folder for the rest of its life, so it has to be small and obvious.

Two details from the bug tracker that already shaped the design:

- A single function may need to subscribe more than once (and each
  subscription has to be independently removable).
- One buggy listener throwing during `emit` must not silently kill the
  rest of the listeners.

Both are in the contract below.

## Contract

```ts
export type Listener<T = unknown> = (data: T) => void;

export class EventBus {
  // Subscribe `fn` to `event`. Returns an unsubscribe function — calling
  // it removes this listener and only this listener (the same fn may be
  // subscribed multiple times; each subscription is independent).
  on<T>(event: string, fn: Listener<T>): () => void;

  // Emit `data` to every current listener of `event`, in registration
  // order. Listeners registered for OTHER events are not called.
  // If a listener throws, the remaining listeners must still be called.
  emit<T>(event: string, data: T): void;
}
```

## Constraints

- TypeScript, no external deps. The harness runs via `node --experimental-strip-types`.
- A given function can be subscribed multiple times. Each subscription is independent (the unsubscribe handle for one subscription doesn't affect others).
- A listener throwing during `emit` MUST NOT prevent remaining listeners from running.

## Deliverables

- `eventBus.ts` exporting the `EventBus` class and `Listener` type.
- `NOTES.md` — what storage you reached for and why (Map vs object,
  array per event, etc.), and what you'd add if this graduated to a
  real library (typed events? wildcard subscribers? once?).

## Time budget

~1 hour. Iterate as much as you want before submitting.
