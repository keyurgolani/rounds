import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  CommandCenterProvider,
  useCommandCenter,
} from '../CommandCenterProvider';
import { CommandCenter } from '../CommandCenter';

function Trigger() {
  const cc = useCommandCenter();
  return (
    <>
      <button onClick={() => cc.open()}>open</button>
      <button onClick={() => cc.openView('add-todo')}>open-todo</button>
    </>
  );
}

function setup() {
  return render(
    <MemoryRouter>
      <CommandCenterProvider>
        <Trigger />
        <CommandCenter />
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('CommandCenter modal', () => {
  it('does not render when closed', () => {
    setup();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders hub with a search input when open', () => {
    setup();
    fireEvent.click(screen.getByText('open'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  it('Esc at hub closes the modal', () => {
    setup();
    fireEvent.click(screen.getByText('open'));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('Esc inside a view returns to the hub', () => {
    setup();
    fireEvent.click(screen.getByText('open-todo'));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  it('clicking the backdrop closes the modal', () => {
    setup();
    fireEvent.click(screen.getByText('open'));
    fireEvent.click(screen.getByTestId('cc-backdrop'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('the X button closes the modal', () => {
    setup();
    fireEvent.click(screen.getByText('open'));
    fireEvent.click(screen.getByLabelText(/close command center/i));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('returns focus to the trigger element when closed', () => {
    setup();
    const trigger = screen.getByText('open');
    trigger.focus();
    fireEvent.click(trigger);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(document.activeElement).toBe(trigger);
  });
});
