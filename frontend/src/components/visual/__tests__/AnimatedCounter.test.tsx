import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AnimatedCounter } from '../AnimatedCounter';

describe('AnimatedCounter', () => {
  it('eventually displays the final value', async () => {
    render(<AnimatedCounter value={1234} duration={0.05} />);
    await waitFor(
      () => {
        expect(screen.getByTestId('counter').textContent).toBe('1,234');
      },
      { timeout: 1000 },
    );
  });

  it('respects a formatter', async () => {
    render(
      <AnimatedCounter
        value={50}
        duration={0.05}
        format={(n) => `${n.toFixed(0)}%`}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId('counter').textContent).toBe('50%');
    });
  });
});
