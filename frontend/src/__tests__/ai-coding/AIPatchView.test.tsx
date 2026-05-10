import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AIPatchView from '../../components/ai/AIPatchView';

vi.mock('@monaco-editor/react', () => ({
  DiffEditor: ({ original, modified }: { original: string; modified: string }) => (
    <div data-testid="diff-editor">
      <pre data-testid="orig">{original}</pre>
      <pre data-testid="mod">{modified}</pre>
    </div>
  ),
}));

vi.mock('../../theme/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

describe('AIPatchView', () => {
  const patches = [
    { file: 'a.py', patch_kind: 'replace' as const, contents: 'x = 1' },
    { file: 'b.py', patch_kind: 'replace' as const, contents: 'y = 2' },
  ];
  const currentFiles = { 'a.py': 'x = 0', 'b.py': 'y = 0' };

  it('renders one DiffEditor per patch', () => {
    render(<AIPatchView patches={patches} currentFiles={currentFiles} onApply={() => {}} onRejectAll={() => {}} />);
    expect(screen.getAllByTestId('diff-editor')).toHaveLength(2);
  });

  it('Accept invokes onApply with that single patch', () => {
    const onApply = vi.fn();
    render(<AIPatchView patches={patches} currentFiles={currentFiles} onApply={onApply} onRejectAll={() => {}} />);
    fireEvent.click(screen.getAllByRole('button', { name: /^Accept$/ })[0]);
    expect(onApply).toHaveBeenCalledWith([patches[0]]);
  });

  it('Reject all invokes onRejectAll and not onApply', () => {
    const onApply = vi.fn();
    const onRejectAll = vi.fn();
    render(<AIPatchView patches={patches} currentFiles={currentFiles} onApply={onApply} onRejectAll={onRejectAll} />);
    fireEvent.click(screen.getByRole('button', { name: /Reject all/ }));
    expect(onRejectAll).toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
  });
});
