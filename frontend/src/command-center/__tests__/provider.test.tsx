import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import {
  CommandCenterProvider,
  useCommandCenter,
} from '../CommandCenterProvider';

function Probe() {
  const cc = useCommandCenter();
  return (
    <div>
      <div data-testid="state">
        {cc.isOpen ? `open:${cc.viewId ?? 'hub'}` : 'closed'}
      </div>
      <button onClick={() => cc.open()}>open</button>
      <button onClick={() => cc.openView('add-todo')}>open-todo</button>
      <button onClick={() => cc.back()}>back</button>
      <button onClick={() => cc.close()}>close</button>
    </div>
  );
}

describe('CommandCenterProvider', () => {
  it('open() opens at hub; close() closes', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId('state').textContent).toBe('closed');
    fireEvent.click(screen.getByText('open'));
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
    fireEvent.click(screen.getByText('close'));
    expect(screen.getByTestId('state').textContent).toBe('closed');
  });

  it('openView() opens the modal at a specific view', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('open-todo'));
    expect(screen.getByTestId('state').textContent).toBe('open:add-todo');
  });

  it('back() pops view → hub → closed', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('open-todo'));
    fireEvent.click(screen.getByText('back'));
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
    fireEvent.click(screen.getByText('back'));
    expect(screen.getByTestId('state').textContent).toBe('closed');
  });

  it('Cmd/Ctrl+K opens the modal', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', metaKey: true }),
      );
    });
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
  });

  it('Cmd/Ctrl+K toggles: a second press closes the modal', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', metaKey: true }),
      );
    });
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', metaKey: true }),
      );
    });
    expect(screen.getByTestId('state').textContent).toBe('closed');
  });

  it('Cmd/Ctrl+K opens even when typing in an input', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <input data-testid="input" />
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    const input = screen.getByTestId('input');
    input.focus();
    act(() => {
      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', metaKey: true }),
      );
    });
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
  });

  it('plain k while typing does NOT open', () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <input data-testid="input" />
          <Probe />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    const input = screen.getByTestId('input');
    input.focus();
    act(() => {
      input.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', bubbles: true }),
      );
    });
    expect(screen.getByTestId('state').textContent).toBe('closed');
  });

  it('closes automatically on route change', () => {
    function Nav() {
      const nav = useNavigate();
      useEffect(() => {
        (window as unknown as { __nav: (p: string) => void }).__nav = nav;
      }, [nav]);
      return null;
    }
    render(
      <MemoryRouter initialEntries={['/a']}>
        <CommandCenterProvider>
          <Nav />
          <Probe />
          <Routes>
            <Route path="/a" element={<div>A</div>} />
            <Route path="/b" element={<div>B</div>} />
          </Routes>
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('open'));
    expect(screen.getByTestId('state').textContent).toBe('open:hub');
    act(() => {
      (window as unknown as { __nav: (p: string) => void }).__nav('/b');
    });
    expect(screen.getByTestId('state').textContent).toBe('closed');
  });
});
