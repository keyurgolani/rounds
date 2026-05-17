import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Field } from '../../pages/Login';

describe('Field', () => {
  it('renders password input hidden by default with a show toggle', () => {
    render(<Field label="Password" type="password" value="hunter2" onChange={vi.fn()} />);
    const input = screen.getByLabelText('Password') as HTMLInputElement;
    expect(input.type).toBe('password');
    const toggle = screen.getByRole('button', { name: 'Show password' });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(toggle).toHaveAttribute('type', 'button');
  });

  it('toggles the input type and aria state when clicked', () => {
    render(<Field label="Password" type="password" value="hunter2" onChange={vi.fn()} />);
    const input = screen.getByLabelText('Password') as HTMLInputElement;
    const toggle = screen.getByRole('button', { name: 'Show password' });

    fireEvent.click(toggle);
    expect(input.type).toBe('text');
    expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(input.type).toBe('password');
  });

  it('does not render the toggle for non-password fields', () => {
    render(<Field label="Email" type="email" value="" onChange={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /password/i })).toBeNull();
  });

  it('keeps two password fields toggling independently', () => {
    render(
      <>
        <Field label="Password A" type="password" value="" onChange={vi.fn()} />
        <Field label="Password B" type="password" value="" onChange={vi.fn()} />
      </>,
    );
    const inputA = screen.getByLabelText('Password A') as HTMLInputElement;
    const inputB = screen.getByLabelText('Password B') as HTMLInputElement;
    const toggleA = screen.getAllByRole('button', { name: 'Show password' })[0];
    fireEvent.click(toggleA);
    expect(inputA.type).toBe('text');
    expect(inputB.type).toBe('password');
  });
});
