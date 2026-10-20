// Idempotency keys for runner commands (ROUNDS-00A-L01).
//
// One key per user action: a click mints one, and a retry of that same
// action sends it again. The key is the server's `command_id`, which
// #19 and #20 define as a UUIDv7, so keys sort by creation time.

export const UUID_V7_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function randomBytes(n: number): Uint8Array {
  const bytes = new Uint8Array(n);
  crypto.getRandomValues(bytes);
  return bytes;
}

/** A new UUIDv7 (RFC 9562): 48-bit millisecond time, then random bits. */
export function mintIdempotencyKey(
  now: number = Date.now(),
  random: (n: number) => Uint8Array = randomBytes,
): string {
  const bytes = random(16);
  const ms = Math.max(0, Math.floor(now));
  bytes[0] = Math.floor(ms / 2 ** 40) & 0xff;
  bytes[1] = Math.floor(ms / 2 ** 32) & 0xff;
  bytes[2] = Math.floor(ms / 2 ** 24) & 0xff;
  bytes[3] = Math.floor(ms / 2 ** 16) & 0xff;
  bytes[4] = Math.floor(ms / 2 ** 8) & 0xff;
  bytes[5] = ms & 0xff;
  bytes[6] = (bytes[6] & 0x0f) | 0x70; // version 7
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
