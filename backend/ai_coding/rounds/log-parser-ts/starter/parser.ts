export type LogLine = { ts: number; level: string; msg: string };

export function parseLine(line: string): LogLine | null {
  // Format: "2024-05-08T12:34:56Z [INFO] message text"
  const m = line.match(/^(\S+) \[(\w+)] (.*)$/);
  if (!m) return null;
  // The timestamp parsing here doesn't agree with what the tests assert.
  // Find what's wrong and fix it. (Don't change the message/level parsing.)
  return { ts: Date.parse(m[1].slice(0, -3)), level: m[2], msg: m[3] };
}

export function parseAll(input: string): LogLine[] {
  return input.split('\n').map(parseLine).filter((l): l is LogLine => l !== null);
}
