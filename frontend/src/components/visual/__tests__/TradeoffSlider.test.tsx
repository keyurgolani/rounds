import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TradeoffSlider } from '../TradeoffSlider';
import type { TradeoffVisual } from '../types';

const visual: TradeoffVisual = {
  title: 'SQL vs NoSQL',
  options: [
    {
      label: 'SQL',
      description: 'Relational',
      pros: ['ACID', 'Joins'],
      cons: ['Hard to scale horizontally'],
    },
    {
      label: 'NoSQL',
      description: 'Schemaless',
      pros: ['Horizontal scale'],
      cons: ['Eventual consistency'],
    },
  ],
  recommendation: 'SQL first, NoSQL when needed',
};

describe('TradeoffSlider', () => {
  it('shows the title and both labels', () => {
    render(<TradeoffSlider visual={visual} />);
    expect(screen.getByText('SQL vs NoSQL')).toBeInTheDocument();
    expect(screen.getByText('SQL')).toBeInTheDocument();
    expect(screen.getByText('NoSQL')).toBeInTheDocument();
  });

  it('starts on the left option, switches when slider moves right', () => {
    render(<TradeoffSlider visual={visual} />);
    expect(screen.getByText('Relational')).toBeInTheDocument();
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '100' } });
    expect(screen.getByText('Schemaless')).toBeInTheDocument();
  });

  it('renders the recommendation when provided', () => {
    render(<TradeoffSlider visual={visual} />);
    expect(screen.getByText(/SQL first, NoSQL when needed/)).toBeInTheDocument();
  });
});
