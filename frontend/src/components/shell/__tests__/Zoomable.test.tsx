import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Zoomable from '../Zoomable';

describe('Zoomable', () => {
  it('renders children inline by default', () => {
    render(<Zoomable><div>child content</div></Zoomable>);
    expect(screen.getByText('child content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('opens a modal on click and duplicates the children inside', () => {
    render(<Zoomable label="My diagram"><div>child content</div></Zoomable>);
    // Click the outer trigger region.
    fireEvent.click(screen.getByRole('button', { name: /expand my diagram/i }));
    expect(screen.getByRole('dialog', { name: /my diagram/i })).toBeInTheDocument();
    // Both instances should be present (inline + modal copy).
    expect(screen.getAllByText('child content').length).toBeGreaterThan(1);
  });

  it('closes the modal via the close button', () => {
    render(<Zoomable label="My diagram"><div>child content</div></Zoomable>);
    fireEvent.click(screen.getByRole('button', { name: /expand my diagram/i }));
    fireEvent.click(screen.getByRole('button', { name: /close zoomed view/i }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('does not trigger zoom when clicking on an interactive element inside', () => {
    render(
      <Zoomable label="My diagram">
        <button>inner</button>
      </Zoomable>,
    );
    fireEvent.click(screen.getByText('inner'));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
