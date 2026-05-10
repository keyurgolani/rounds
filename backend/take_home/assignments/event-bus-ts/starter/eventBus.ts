/**
 * EventBus — implement on() and emit().
 *
 * See prompt.md for the contract.
 */
export type Listener<T = unknown> = (data: T) => void;

export class EventBus {
  on<T>(_event: string, _fn: Listener<T>): () => void {
    throw new Error("not implemented");
  }

  emit<T>(_event: string, _data: T): void {
    throw new Error("not implemented");
  }
}
