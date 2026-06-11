import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LinkableCard } from '../LinkableCard';

const base = {
  innerRef: () => {},
  onBeginDrag: () => {},
  active: false,
  dimmed: false,
  isDropTarget: false,
  isDragSource: false,
  side: 'right' as const,
};

describe('LinkableCard flag', () => {
  it('shows a dashed outline when flagged unfiled', () => {
    render(<LinkableCard {...base} flag="unfiled"><span>card</span></LinkableCard>);
    const card = screen.getByText('card').closest('.card');
    expect(card?.getAttribute('style')).toContain('dashed');
  });

  it('has no dashed outline by default', () => {
    render(<LinkableCard {...base}><span>plain</span></LinkableCard>);
    const card = screen.getByText('plain').closest('.card');
    expect(card?.getAttribute('style') ?? '').not.toContain('dashed');
  });
});
