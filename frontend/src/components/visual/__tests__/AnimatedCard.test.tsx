import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AnimatedCard } from '../AnimatedCard';

describe('AnimatedCard', () => {
  it('renders children', () => {
    render(<AnimatedCard>hello world</AnimatedCard>);
    expect(screen.getByText('hello world')).toBeInTheDocument();
  });

  it('applies a custom className', () => {
    render(
      <AnimatedCard className="my-card" data-testid="card">
        x
      </AnimatedCard>,
    );
    expect(screen.getByTestId('card').className).toMatch(/my-card/);
  });

  it('forwards data-testid for tooling', () => {
    render(<AnimatedCard data-testid="my-card">x</AnimatedCard>);
    expect(screen.getByTestId('my-card')).toBeInTheDocument();
  });
});
