import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, createEvent } from '@testing-library/react';
import { useButtonFileDrop } from '../useButtonFileDrop';

// Tiny harness: a button wired with the hook, exposing isOver via a data attr.
function Harness({ onFile, disabled }: { onFile: (f: File) => void; disabled?: boolean }) {
  const { dropProps, isOver } = useButtonFileDrop({ onFile, disabled });
  return (
    <button data-testid="btn" data-over={isOver} {...dropProps}>
      Import
    </button>
  );
}

const fileDT = (files: File[]) => ({ files, types: ['Files'], dropEffect: '' });

describe('useButtonFileDrop', () => {
  it('ignores drags that do not carry files', () => {
    const onFile = vi.fn();
    render(<Harness onFile={onFile} />);
    const btn = screen.getByTestId('btn');
    fireEvent.dragOver(btn, { dataTransfer: { files: [], types: ['text/plain'], dropEffect: '' } });
    expect(btn.getAttribute('data-over')).toBe('false');
  });

  it('sets isOver on drag-over with files and clears it on leave', () => {
    const onFile = vi.fn();
    render(<Harness onFile={onFile} />);
    const btn = screen.getByTestId('btn');
    fireEvent.dragEnter(btn, { dataTransfer: fileDT([]) });
    fireEvent.dragOver(btn, { dataTransfer: fileDT([]) });
    expect(btn.getAttribute('data-over')).toBe('true');
    // Leaving the button entirely (no relatedTarget inside it) clears the state.
    fireEvent.dragLeave(btn, { dataTransfer: fileDT([]) });
    expect(btn.getAttribute('data-over')).toBe('false');
  });

  it('calls preventDefault and onFile with the first file on drop', () => {
    const onFile = vi.fn();
    render(<Harness onFile={onFile} />);
    const btn = screen.getByTestId('btn');
    const a = new File(['a'], 'a.pdf', { type: 'application/pdf' });
    const b = new File(['b'], 'b.pdf', { type: 'application/pdf' });
    const drop = createEvent.drop(btn, { dataTransfer: fileDT([a, b]) });
    fireEvent(btn, drop);
    expect(drop.defaultPrevented).toBe(true);
    expect(onFile).toHaveBeenCalledTimes(1);
    expect(onFile).toHaveBeenCalledWith(a);
  });

  it('does not call onFile when disabled, and never highlights', () => {
    const onFile = vi.fn();
    render(<Harness onFile={onFile} disabled />);
    const btn = screen.getByTestId('btn');
    fireEvent.dragOver(btn, { dataTransfer: fileDT([]) });
    expect(btn.getAttribute('data-over')).toBe('false');
    const f = new File(['a'], 'a.pdf', { type: 'application/pdf' });
    const drop = createEvent.drop(btn, { dataTransfer: fileDT([f]) });
    fireEvent(btn, drop);
    expect(drop.defaultPrevented).toBe(true); // browser navigation blocked even when disabled
    expect(onFile).not.toHaveBeenCalled();
  });
});
