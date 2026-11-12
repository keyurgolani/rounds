// The Studio's shell: on a wide screen three columns that each scroll; on
// a narrow one a single stacked column the page scrolls. Stacked, the
// shell takes its content's height rather than the page's, so no pane is
// squeezed under the next one, the Tools list over the Personal form
// included.

import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioShell from '../StudioShell';
import { emptyResumeData } from '../../types';
import type { UseResumeResult } from '../../hooks/useResume';

vi.mock('../SectionNav', () => ({ default: () => <ol data-testid="sections" /> }));
vi.mock('../PreviewPane', () => ({ default: () => <div data-testid="preview" /> }));
vi.mock('../editors/PersonalInfoEditor', () => ({ default: () => <form aria-label="Personal" /> }));
vi.mock('../../links/library', () => ({ loadLibrarySnapshot: () => new Promise(() => {}) }));

function result(): UseResumeResult {
  return {
    resume: null,
    data: emptyResumeData(),
    templateId: 'modern',
    design: {},
    loading: false,
    error: null,
    saveState: 'idle',
    lastSavedAt: null,
    setData: vi.fn(),
    setTemplateId: vi.fn(),
    setDesign: vi.fn(),
    links: {} as UseResumeResult['links'],
    setLinks: vi.fn(),
    rename: vi.fn(),
    flush: vi.fn(),
  };
}

const startWidth = window.innerWidth;

function atWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: width });
}

function renderShell() {
  render(<StudioShell result={result()} active="personal" onActiveChange={() => {}} />);
  const shell = document.querySelector<HTMLElement>('[data-studio-shell]');
  expect(shell).not.toBeNull();
  return shell!;
}

afterEach(() => atWidth(startWidth));

describe('StudioShell', () => {
  it('stacks on a phone at its content height, Tools under the sections, then the form and the preview', () => {
    atWidth(390);
    const shell = renderShell();
    expect(shell).toHaveAttribute('data-studio-shell', 'stacked');
    expect(shell.style.gridTemplateColumns).toBe('minmax(0, 1fr)');
    // Its content's height, never shrunk to the page's.
    expect(shell.style.flexGrow).toBe('0');
    expect(shell.style.flexShrink).toBe('0');
    expect(shell.style.flexBasis).toBe('auto');

    const panes = [...shell.children].map((pane) => pane.getAttribute('data-studio-pane'));
    expect(panes).toEqual(['sections', 'form', 'preview']);
    const sections = shell.querySelector('[data-studio-pane="sections"]');
    expect(sections).toContainElement(screen.getByTestId('sections'));
    expect(sections).toContainElement(shell.querySelector('[data-studio-rail="tools"]') as HTMLElement);
    expect(shell.querySelector('[data-studio-pane="form"]')).toContainElement(screen.getByRole('form', { name: 'Personal' }));
  });

  it('fills the page in three columns on a wide screen', () => {
    atWidth(1280);
    const shell = renderShell();
    expect(shell).toHaveAttribute('data-studio-shell', 'columns');
    expect(shell.style.gridTemplateColumns).toBe('230px minmax(0, 1fr) minmax(0, 1.15fr)');
    // jsdom drops `flex: 1 1 0` (it wants a unit on the basis), so this
    // checks only that the stacked sizing is off.
    expect(shell.style.flexBasis).not.toBe('auto');
  });

  it('stacks when the window narrows', () => {
    atWidth(1280);
    const shell = renderShell();
    act(() => {
      atWidth(390);
      window.dispatchEvent(new Event('resize'));
    });
    expect(shell).toHaveAttribute('data-studio-shell', 'stacked');
    expect(shell.style.flexBasis).toBe('auto');
  });
});
