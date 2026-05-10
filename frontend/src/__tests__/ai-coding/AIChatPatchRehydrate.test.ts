import { describe, it, expect } from 'vitest';
import { splitPatches } from '../../components/ai/aiPatches';

describe('aiPatches.splitPatches (chat rehydrate path)', () => {
  it('finds patches even when content is just the JSON array', () => {
    const json = JSON.stringify([
      {
        file: 'cart.py',
        patch_kind: 'replace',
        contents: 'def total(items):\n    return sum(item[1] for item in items)\n',
      },
    ]);
    const { prose, patches } = splitPatches(json);
    expect(prose).toBe('');
    expect(patches).toHaveLength(1);
    expect(patches?.[0].file).toBe('cart.py');
  });

  it('finds patches when content has a prose preamble before JSON', () => {
    const json = JSON.stringify([
      { file: 'a.py', patch_kind: 'replace', contents: 'pass\n' },
    ]);
    const content = "Here are the changes:\n\n" + json;
    const { prose, patches } = splitPatches(content);
    expect(prose).toBe('Here are the changes:');
    expect(patches).toHaveLength(1);
  });

  it('handles fenced ```json blocks', () => {
    const json = JSON.stringify([
      { file: 'a.py', patch_kind: 'replace', contents: 'pass\n' },
    ]);
    const content = '```json\n' + json + '\n```';
    const { patches } = splitPatches(content);
    expect(patches).toHaveLength(1);
  });

  it('does NOT confuse `[` inside a contents string for the array opener', () => {
    // Regression: lastIndexOf-based scanner picked the bracket inside
    // arr[i] and failed to parse, falling back to raw text.
    const json = JSON.stringify([
      {
        file: 'cart.py',
        patch_kind: 'replace',
        contents: 'def total(items):\n    return sum(item[1] for item in items)\n',
      },
    ]);
    const { patches } = splitPatches(json);
    expect(patches).toHaveLength(1);
    expect(patches?.[0].contents).toContain('item[1]');
  });

  it('returns null patches when content has no JSON array', () => {
    const { patches } = splitPatches('Just chatting, no patches here.');
    expect(patches).toBeNull();
  });

  it('returns null patches when JSON is malformed', () => {
    const { patches } = splitPatches('Here you go: [{not valid json');
    expect(patches).toBeNull();
  });
});
