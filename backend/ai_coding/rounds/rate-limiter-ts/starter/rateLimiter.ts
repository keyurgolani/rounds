/**
 * Sliding-window rate limiter.
 *
 * Spec:
 *   - allow(now: number) records a hit at time `now` (ms-since-epoch)
 *     and returns true if at most `maxRequests` requests have occurred
 *     in the previous `windowMs` (inclusive of `now`).
 *   - When the limit is hit, allow() returns false and does NOT record
 *     the rejected hit.
 *
 * Correctness tests pass against the starter. The perf test does not —
 * the implementation rescans the full history on every call.
 */
export class RateLimiter {
  private readonly max: number;
  private readonly window: number;
  private hits: number[] = [];

  constructor(maxRequests: number, windowMs: number) {
    this.max = maxRequests;
    this.window = windowMs;
  }

  allow(now: number): boolean {
    this.hits = this.hits.filter((t) => t > now - this.window);
    if (this.hits.length >= this.max) return false;
    this.hits.push(now);
    return true;
  }
}
