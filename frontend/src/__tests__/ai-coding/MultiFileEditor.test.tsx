import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MultiFileEditor from '../../components/editor/MultiFileEditor';

vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange, path }: any) => (
    <textarea
      data-testid={`mock-monaco-${path}`}
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
    />
  ),
}));

vi.mock('../../theme/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

describe('MultiFileEditor', () => {
  it('renders the file tree and switches between tabs', () => {
    const files = {
      'cart.py': 'pass',
      'tests/test_x.py': 'def test_a(): pass',
    };
    render(
      <MultiFileEditor
        files={files}
        activePath="cart.py"
        onActivePathChange={() => {}}
        onFileChange={() => {}}
      />
    );
    expect(screen.getByText('cart.py')).toBeTruthy();
    expect(screen.getByText('tests/test_x.py')).toBeTruthy();
    expect(screen.getByTestId('mock-monaco-cart.py')).toBeTruthy();
  });

  it('emits onFileChange when buffer changes', () => {
    const onFileChange = vi.fn();
    render(
      <MultiFileEditor
        files={{ 'a.py': 'x = 1' }}
        activePath="a.py"
        onActivePathChange={() => {}}
        onFileChange={onFileChange}
      />
    );
    fireEvent.change(screen.getByTestId('mock-monaco-a.py'), { target: { value: 'x = 2' } });
    expect(onFileChange).toHaveBeenCalledWith('a.py', 'x = 2');
  });

  it('marks dirty files with a dot', () => {
    const { rerender } = render(
      <MultiFileEditor
        files={{ 'a.py': 'x = 1' }}
        savedFiles={{ 'a.py': 'x = 1' }}
        activePath="a.py"
        onActivePathChange={() => {}}
        onFileChange={() => {}}
      />
    );
    expect(screen.queryByTestId('dirty-a.py')).toBeNull();

    rerender(
      <MultiFileEditor
        files={{ 'a.py': 'x = 2' }}
        savedFiles={{ 'a.py': 'x = 1' }}
        activePath="a.py"
        onActivePathChange={() => {}}
        onFileChange={() => {}}
      />
    );
    expect(screen.getByTestId('dirty-a.py')).toBeTruthy();
  });
});
