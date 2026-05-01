import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Accordion } from '../Accordion';

const items = [
  { id: 'a', title: 'Alpha', summary: 'first', children: <p>Alpha body</p> },
  { id: 'b', title: 'Beta', summary: 'second', children: <p>Beta body</p> },
  { id: 'c', title: 'Gamma', children: <p>Gamma body</p> },
];

describe('Accordion', () => {
  it('opens the first item by default', () => {
    render(<Accordion items={items} />);
    expect(screen.getByText('Alpha body')).toBeInTheDocument();
    expect(screen.queryByText('Beta body')).not.toBeInTheDocument();
  });

  it('respects defaultOpenId', () => {
    render(<Accordion items={items} defaultOpenId="b" />);
    expect(screen.getByText('Beta body')).toBeInTheDocument();
    expect(screen.queryByText('Alpha body')).not.toBeInTheDocument();
  });

  it('single-open: clicking another header closes the previous one', () => {
    render(<Accordion items={items} />);
    fireEvent.click(screen.getByRole('button', { name: /Beta/ }));
    expect(screen.getByText('Beta body')).toBeInTheDocument();
    expect(screen.queryByText('Alpha body')).not.toBeInTheDocument();
  });

  it('clicking the open header closes it', () => {
    render(<Accordion items={items} />);
    fireEvent.click(screen.getByRole('button', { name: /Alpha/ }));
    expect(screen.queryByText('Alpha body')).not.toBeInTheDocument();
  });

  it('renders header text (title + summary) for every item', () => {
    render(<Accordion items={items} />);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('Gamma')).toBeInTheDocument();
    expect(screen.getByText('first')).toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });
});
