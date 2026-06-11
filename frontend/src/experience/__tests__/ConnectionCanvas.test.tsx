import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConnectionCanvas, { type CanvasItem, type CanvasConnection } from '../ConnectionCanvas';

const items: CanvasItem[] = [
  { localId: 'j1', kind: 'job' },
  { localId: 'p1', kind: 'project' },
  { localId: 'a1', kind: 'anecdote' },
  { localId: 'b1', kind: 'bullet' },
];
// j1->p1 is incident to the pinned job; a1->b1 is not.
const connections: CanvasConnection[] = [
  { parentLocalId: 'j1', childLocalId: 'p1' },
  { parentLocalId: 'a1', childLocalId: 'b1' },
];
const content = (it: CanvasItem) => <span>{it.localId}</span>;

describe('ConnectionCanvas focus mode', () => {
  it('renders a disconnect control only for edges incident to the pinned card', () => {
    const onDisconnect = vi.fn();
    render(
      <ConnectionCanvas
        items={items}
        connections={connections}
        renderCardContent={content}
        onToggleLink={vi.fn()}
        onDisconnect={onDisconnect}
        onSelectItem={vi.fn()}
        selectedId="j1"
        interaction="focus"
      />,
    );
    expect(screen.getAllByLabelText('Remove connection')).toHaveLength(1);
  });

  it('pins a card on click', async () => {
    const onSelectItem = vi.fn();
    render(
      <ConnectionCanvas
        items={items}
        connections={connections}
        renderCardContent={content}
        onToggleLink={vi.fn()}
        onDisconnect={vi.fn()}
        onSelectItem={onSelectItem}
        selectedId={null}
        interaction="focus"
      />,
    );
    await userEvent.click(screen.getByText('p1'));
    expect(onSelectItem).toHaveBeenCalledWith('p1');
  });

  it('disconnects via the neighbor control of the pinned card', async () => {
    const onDisconnect = vi.fn();
    render(
      <ConnectionCanvas
        items={items}
        connections={connections}
        renderCardContent={content}
        onToggleLink={vi.fn()}
        onDisconnect={onDisconnect}
        onSelectItem={vi.fn()}
        selectedId="j1"
        interaction="focus"
      />,
    );
    await userEvent.click(screen.getByLabelText('Remove connection'));
    expect(onDisconnect).toHaveBeenCalledWith('j1', 'p1');
  });

  it("keeps the disconnect control reachable while hovering the pinned card's neighbor", async () => {
    const onDisconnect = vi.fn();
    render(
      <ConnectionCanvas
        items={items}
        connections={connections}
        renderCardContent={content}
        onToggleLink={vi.fn()}
        onDisconnect={onDisconnect}
        onSelectItem={vi.fn()}
        selectedId="j1"
        interaction="focus"
      />,
    );
    // Hovering the neighbor must NOT steal focus from the pinned card, so its ✕ stays live.
    await userEvent.hover(screen.getByText('p1'));
    await userEvent.click(screen.getByLabelText('Remove connection'));
    expect(onDisconnect).toHaveBeenCalledWith('j1', 'p1');
  });
});

describe('ConnectionCanvas always mode (legacy / ImportReview)', () => {
  it('keeps midpoint controls for every edge and opens on click', async () => {
    const onOpenItem = vi.fn();
    render(
      <ConnectionCanvas
        items={items}
        connections={connections}
        renderCardContent={content}
        onToggleLink={vi.fn()}
        onDisconnect={vi.fn()}
        onOpenItem={onOpenItem}
      />,
    );
    expect(screen.getAllByLabelText('Remove connection')).toHaveLength(2);
    await userEvent.click(screen.getByText('p1'));
    expect(onOpenItem).toHaveBeenCalledWith('p1');
  });
});
