// Where the editor puts its actions: floating over the code, or with
// `actionsBar` in a bar under the files and the code, so a code column the
// AI chat has narrowed keeps its gutter clear and the chat stays full
// height beside them.

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MultiFileEditor from '../MultiFileEditor';

vi.mock('@monaco-editor/react', () => ({
  default: ({ path }: { path: string }) => <div data-testid="code" data-path={path} />,
}));
vi.mock('../../../theme/ThemeProvider', () => ({ useTheme: () => ({ theme: 'light' }) }));
vi.mock('../FileExplorer', () => ({ default: () => <nav data-testid="files" /> }));

function renderEditor(props: Partial<React.ComponentProps<typeof MultiFileEditor>> = {}) {
  return render(
    <MultiFileEditor
      files={{ 'cart.py': 'pass' }}
      activePath="cart.py"
      onActivePathChange={() => {}}
      onFileChange={() => {}}
      bottomActions={
        <>
          <button type="button">Run</button>
          <button type="button">Submit</button>
        </>
      }
      aiChat={<aside data-testid="chat" />}
      aiChatOpen
      {...props}
    />,
  );
}

describe('MultiFileEditor actions', () => {
  it('puts the actions in a bar under the files and the code, not over the code', () => {
    renderEditor({ actionsBar: true });
    const bar = document.querySelector('[data-editor-actions="bar"]');
    expect(bar).not.toBeNull();
    const run = screen.getByRole('button', { name: 'Run' });
    expect(bar).toContainElement(run);
    expect(bar).toContainElement(screen.getByRole('button', { name: 'Submit' }));

    // The bar follows the row that holds the files and the code.
    const code = screen.getByTestId('code');
    const files = screen.getByTestId('files');
    const row = bar!.previousElementSibling as HTMLElement;
    expect(row).toContainElement(code);
    expect(row).toContainElement(files);
    // None of the code column's own boxes holds an action.
    expect(code.parentElement).not.toContainElement(run);
    // The chat stays a column of its own beside them, outside the bar.
    expect(bar!.parentElement).not.toContainElement(screen.getByTestId('chat'));
  });

  it('floats the actions over the code without the bar, as before', () => {
    renderEditor();
    expect(document.querySelector('[data-editor-actions="bar"]')).toBeNull();
    const run = screen.getByRole('button', { name: 'Run' });
    expect(screen.getByTestId('code').parentElement).toContainElement(run);
    expect((run.parentElement as HTMLElement).style.position).toBe('absolute');
  });

  it('shows no bar when there are no actions', () => {
    renderEditor({ actionsBar: true, bottomActions: undefined });
    expect(document.querySelector('[data-editor-actions="bar"]')).toBeNull();
    expect(screen.getByTestId('code')).toBeInTheDocument();
  });
});
