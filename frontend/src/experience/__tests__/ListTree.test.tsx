import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ListTree from '../ListTree';
import type { TimelineEntity, EntityKind } from '../experienceApi';
import type { ConnectionMap, ReverseConnectionMap } from '../connectionApi';

const ent = (id: string, kind: EntityKind, date: string): TimelineEntity =>
  ({
    id, kind,
    title: `${id}-title`, company: `${id}-co`, role: '',
    start_date: date, end_date: null, date,
    description: '', tags: [],
    situation: '', task: '', action: '', result: '', impact: '',
  } as unknown as TimelineEntity);

// Title text the cards render: jobs show company, others show title.
const titleOf = (e: TimelineEntity) => (e.kind === 'job' ? `${e.id}-co` : `${e.id}-title`);

function makeById(list: TimelineEntity[]): Record<string, TimelineEntity> {
  const m: Record<string, TimelineEntity> = {};
  for (const e of list) m[e.id] = e;
  return m;
}

describe('ListTree nested mode', () => {
  it('renders children indented below their parent', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const entities = [j1, p1];
    const connMap: ConnectionMap = { j1: { project: ['p1'] } } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = { p1: { job: ['j1'] } } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText(titleOf(j1))).toBeTruthy();
    expect(screen.getByText(titleOf(p1))).toBeTruthy();
  });

  it('duplicates a multi-parent child under each parent', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const b1 = ent('b1', 'bullet', '2021-03-01');
    const entities = [j1, p1, b1];
    // j1 -> p1, j1 -> b1, p1 -> b1  (b1 has two parents: j1 and p1)
    const connMap: ConnectionMap = {
      j1: { project: ['p1'], bullet: ['b1'] },
      p1: { bullet: ['b1'] },
    } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = {
      p1: { job: ['j1'] },
      b1: { job: ['j1'], project: ['p1'] },
    } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    // b1 appears once under j1 directly and once under p1.
    expect(screen.getAllByText(titleOf(b1))).toHaveLength(2);
  });

  it('renders an unfiled (parentless, non-job) entity as a top-level root', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const loose = ent('lb', 'bullet', '2021-05-01');
    const entities = [j1, loose];
    render(
      <ListTree
        entities={entities}
        connMap={{} as ConnectionMap}
        reverseMap={{} as ReverseConnectionMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText(titleOf(loose))).toBeTruthy();
  });

  it('terminates on a connection cycle (cycle guard)', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const a1 = ent('a1', 'anecdote', '2021-03-01');
    const entities = [j1, p1, a1];
    // j1 -> p1 -> a1 -> p1 (a1 links back to p1)
    const connMap: ConnectionMap = {
      j1: { project: ['p1'] },
      p1: { anecdote: ['a1'] },
      a1: { project: ['p1'] },
    } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = {
      p1: { job: ['j1'], anecdote: ['a1'] },
      a1: { project: ['p1'] },
    } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    // p1 renders once (under j1); the back-edge a1 -> p1 is pruned by the guard.
    expect(screen.getAllByText(titleOf(p1))).toHaveLength(1);
  });

  it('uses denser sizing for deeper cards', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const entities = [j1, p1];
    const connMap: ConnectionMap = { j1: { project: ['p1'] } } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = { p1: { job: ['j1'] } } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    const jobTitle = screen.getByText(titleOf(j1)) as HTMLElement;
    const projTitle = screen.getByText(titleOf(p1)) as HTMLElement;
    // React serializes the numeric fontSize to '16px' / '14px' in jsdom.
    // Depth 0 title is 16px; depth 1 title is 14px.
    expect(jobTitle.style.fontSize).toBe('16px');
    expect(projTitle.style.fontSize).toBe('14px');
  });
});

describe('ListTree collapse', () => {
  it('collapsing a parent hides its subtree; expanding shows it again', async () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const entities = [j1, p1];
    const connMap: ConnectionMap = { j1: { project: ['p1'] } } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = { p1: { job: ['j1'] } } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="all"
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText(titleOf(p1))).toBeTruthy();
    await userEvent.click(screen.getByLabelText('Collapse'));
    expect(screen.queryByText(titleOf(p1))).toBeNull();
    await userEvent.click(screen.getByLabelText('Expand'));
    expect(screen.getByText(titleOf(p1))).toBeTruthy();
  });
});

describe('ListTree flat (filtered) mode', () => {
  it('renders a flat list of one kind with no nesting', () => {
    const j1 = ent('j1', 'job', '2021-01-01');
    const p1 = ent('p1', 'project', '2021-02-01');
    const p2 = ent('p2', 'project', '2021-03-01');
    const entities = [j1, p1, p2];
    const connMap: ConnectionMap = { j1: { project: ['p1', 'p2'] } } as unknown as ConnectionMap;
    const reverseMap: ReverseConnectionMap = {
      p1: { job: ['j1'] }, p2: { job: ['j1'] },
    } as unknown as ReverseConnectionMap;
    render(
      <ListTree
        entities={entities}
        connMap={connMap}
        reverseMap={reverseMap}
        entityById={makeById(entities)}
        filter="project"
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText(titleOf(p1))).toBeTruthy();
    expect(screen.getByText(titleOf(p2))).toBeTruthy();
    // The job is not of the filtered kind, so it must not appear.
    expect(screen.queryByText(titleOf(j1))).toBeNull();
    // Flat rows are not expandable.
    expect(screen.queryByLabelText('Collapse')).toBeNull();
    expect(screen.queryByLabelText('Expand')).toBeNull();
  });
});
