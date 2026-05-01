import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Skeleton } from '../Skeleton';

describe('Skeleton', () => {
  it('renders a pulsing block with the provided dimensions', () => {
    render(<Skeleton width={120} height={20} data-testid="skel" />);
    const el = screen.getByTestId('skel');
    expect(el).toBeInTheDocument();
    expect(el.style.width).toBe('120px');
    expect(el.style.height).toBe('20px');
    expect(el.className).toMatch(/animate-pulse/);
  });

  it('accepts a className override', () => {
    render(<Skeleton className="rounded-full" data-testid="skel" />);
    expect(screen.getByTestId('skel').className).toMatch(/rounded-full/);
  });
});
