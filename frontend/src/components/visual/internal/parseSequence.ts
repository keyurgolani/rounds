// Parser for the Mermaid `sequenceDiagram` subset used in seed content.
// Supports `participant X as Label`, solid and dashed message arrows
// (`->>`, `-->>`), self-loops, and `alt/else/end` blocks. Anything
// outside this subset returns null so callers can fall back to Mermaid.

export interface SeqParticipant {
  id: string;
  label: string;
}

export type SeqStepKind =
  | { type: 'msg'; from: string; to: string; label: string; dashed: boolean }
  | { type: 'note'; over: string[]; text: string }
  | { type: 'block-open'; kind: 'alt' | 'opt' | 'loop' | 'par'; label: string }
  | { type: 'block-else'; label: string }
  | { type: 'block-close' };

export interface SeqData {
  participants: SeqParticipant[];
  steps: SeqStepKind[];
}

const HEADER_RE = /^sequenceDiagram\s*$/i;
const PARTICIPANT_RE =
  /^(?:participant|actor)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+as\s+(.+))?\s*$/i;
// Message: A->>B: text  |  A-->>B: text  |  A->B: text  |  A-->B: text
const MSG_RE =
  /^([A-Za-z_][A-Za-z0-9_]*)\s*(-->>|->>|-->|->|-\)|--\))\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$/;
const NOTE_RE = /^note\s+(left of|right of|over)\s+([^:]+):\s*(.*)$/i;

function decodeParticipantLabel(raw: string | undefined, id: string): string {
  if (!raw) return id;
  const t = raw.trim();
  if (t.startsWith('"') && t.endsWith('"') && t.length >= 2) return t.slice(1, -1);
  return t;
}

export function parseSequence(source: string): SeqData | null {
  const lines = source.split(/\r?\n/);
  let headerOk = false;
  const body: string[] = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('%%')) continue;
    if (!headerOk) {
      if (!HEADER_RE.test(line)) return null;
      headerOk = true;
      continue;
    }
    body.push(line);
  }
  if (!headerOk) return null;

  const participants: SeqParticipant[] = [];
  const byId = new Map<string, SeqParticipant>();
  const steps: SeqStepKind[] = [];

  function addParticipant(id: string, label?: string) {
    if (byId.has(id)) return;
    const p: SeqParticipant = { id, label: decodeParticipantLabel(label, id) };
    byId.set(id, p);
    participants.push(p);
  }

  for (const line of body) {
    const partMatch = line.match(PARTICIPANT_RE);
    if (partMatch) {
      addParticipant(partMatch[1], partMatch[2]);
      continue;
    }

    const lower = line.toLowerCase();
    if (
      lower.startsWith('alt ') ||
      lower.startsWith('opt ') ||
      lower.startsWith('loop ') ||
      lower.startsWith('par ')
    ) {
      const kind = lower.slice(0, 3).replace('par', 'par').replace('alt', 'alt') as
        | 'alt'
        | 'opt'
        | 'loop'
        | 'par';
      const label = line.slice(kind.length).trim();
      steps.push({ type: 'block-open', kind, label });
      continue;
    }
    if (lower === 'end') {
      steps.push({ type: 'block-close' });
      continue;
    }
    if (lower.startsWith('else')) {
      const label = line.slice(4).trim();
      steps.push({ type: 'block-else', label });
      continue;
    }

    const msg = line.match(MSG_RE);
    if (msg) {
      const [, from, op, to, text] = msg;
      addParticipant(from);
      addParticipant(to);
      steps.push({
        type: 'msg',
        from,
        to,
        label: text.trim(),
        dashed: op.startsWith('--'),
      });
      continue;
    }

    const note = line.match(NOTE_RE);
    if (note) {
      const over = note[2].split(',').map((s) => s.trim()).filter(Boolean);
      for (const id of over) addParticipant(id);
      steps.push({ type: 'note', over, text: note[3].trim() });
      continue;
    }

    // Unrecognized — bail so caller falls back.
    return null;
  }

  if (participants.length === 0) return null;
  return { participants, steps };
}
