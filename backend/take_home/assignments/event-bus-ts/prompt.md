# Event Bus

Implement an in-memory pub/sub event bus in `eventBus.ts`.

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
- Optional: `NOTES.md` with any trade-off you made.

## Time budget

~1 hour.
