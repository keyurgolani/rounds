// Denial states (ROUNDS-00A-L01): each one is announced politely, reads
// as text with an icon, never takes focus, and hands focus back to the
// control that started the action when that control lost it.

import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

const reloadPage = vi.hoisted(() => vi.fn());
vi.mock('../../../lib/definitions', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  reloadPage,
}));
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { RunnerDenialNotice, type RunnerAction } from '../RunnerDenialNotice';
import type { RunnerDenial, RunnerDenialKind } from '../../../lib/runnerDenial';

const CID = '0123456789abcdef0123456789abcdef';

function denial(kind: RunnerDenialKind, extra: Partial<RunnerDenial> = {}): RunnerDenial {
  return { kind, status: 0, code: null, retryAfterSeconds: null, correlationId: null, ...extra };
}

function LoginProbe() {
  const location = useLocation();
  return <p>Login page from {(location.state as { from?: string } | null)?.from}</p>;
}

function renderNotice(node: React.ReactNode, path = '/coding/question/two-sum') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route path="*" element={node} />
      </Routes>
    </MemoryRouter>,
  );
}

const CASES: Array<[RunnerDenialKind, RunnerAction, string, RegExp]> = [
  ['sign_in', 'run', 'Sign in again', /Your session has ended\. Nothing ran\. Your code is still here\./],
  ['limit', 'tests', 'Limit reached', /Try again in 45 seconds\./],
  ['turned_off', 'grade', 'Turned off', /Grading is turned off on this server\./],
  ['unavailable', 'run', 'Unavailable right now', /Nothing ran\. Your code is still here\. Try again in a moment\./],
  ['too_large', 'grade', 'Too large', /Your files are over the size limit, so nothing was graded\. Trim them and try again\./],
  ['not_permitted', 'pdf', 'Not available', /Server PDF export isn't available for this account\./],
];

describe('RunnerDenialNotice', () => {
  it('keeps an empty polite live region in place before any denial', () => {
    renderNotice(<RunnerDenialNotice denial={null} action="run" />);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveAttribute('aria-atomic', 'true');
    expect(region).toBeEmptyDOMElement();
  });

  it.each(CASES)('%s reads as a titled message inside the live region', (kind, action, title, body) => {
    renderNotice(
      <RunnerDenialNotice denial={denial(kind, { retryAfterSeconds: 45 })} action={action} />,
    );
    const region = screen.getByRole('status');
    expect(within(region).getByText(title)).toBeInTheDocument();
    expect(region.textContent).toMatch(body);
    // The icon is decoration; the words carry the state.
    for (const svg of region.querySelectorAll('svg')) {
      expect(svg).toHaveAttribute('aria-hidden', 'true');
    }
    expect(region.querySelector('[data-denial]')).toHaveAttribute('data-denial', kind);
  });

  it('says how long to wait, or "later" without a Retry-After', () => {
    const { rerender } = renderNotice(
      <RunnerDenialNotice denial={denial('limit', { retryAfterSeconds: 120 })} action="run" />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Try again in 2 minutes.');
    rerender(
      <MemoryRouter>
        <RunnerDenialNotice denial={denial('limit')} action="run" />
      </MemoryRouter>,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Try again later.');
  });

  it('shows a short reference when the server sent a correlation id', () => {
    renderNotice(<RunnerDenialNotice denial={denial('unavailable', { correlationId: CID })} action="tests" />);
    expect(screen.getByRole('status')).toHaveTextContent('Reference 01234567');
    expect(screen.getByRole('status')).not.toHaveTextContent(CID);
  });

  it('offers a keyboard-reachable sign-in link that returns to the page', async () => {
    const user = userEvent.setup();
    renderNotice(<RunnerDenialNotice denial={denial('sign_in')} action="run" />);
    const link = screen.getByRole('link', { name: 'Sign in' });
    expect(link).toHaveAttribute('href', '/login');
    await user.tab();
    expect(link).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByText('Login page from /coding/question/two-sum')).toBeInTheDocument();
  });

  it.each(['turned_off', 'unavailable'] as const)('offers browser printing for a %s server PDF', async (kind) => {
    const user = userEvent.setup();
    const onPrint = vi.fn();
    renderNotice(<RunnerDenialNotice denial={denial(kind)} action="pdf" onPrint={onPrint} />);
    const print = screen.getByRole('button', { name: 'Print to PDF instead' });
    await user.tab();
    expect(print).toHaveFocus();
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(onPrint).toHaveBeenCalledTimes(2);
  });

  it.each(['sign_in', 'limit', 'too_large', 'not_permitted'] as const)('offers no print fallback for %s', (kind) => {
    renderNotice(<RunnerDenialNotice denial={denial(kind)} action="pdf" onPrint={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Print to PDF instead' })).not.toBeInTheDocument();
  });

  it('offers no actions for run surfaces besides signing in', () => {
    renderNotice(<RunnerDenialNotice denial={denial('unavailable')} action="run" onPrint={vi.fn()} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('definition states (ROUNDS-00A-L02)', () => {
  const DEFINITION_CASES: Array<[RunnerDenialKind, RunnerAction, string, RegExp]> = [
    ['reload', 'tests', 'Reload to continue', /This page is out of date\. No tests ran\. Your code is still here\./],
    ['retired', 'grade', 'Retired', /This practice item was retired, so it no longer runs\. Your files and notes are still here\./],
    ['not_found', 'run', 'Not on this server', /doesn't have this practice item in this language\. Nothing ran\./],
  ];

  it.each(DEFINITION_CASES)('%s reads as a titled message', (kind, action, title, body) => {
    renderNotice(<RunnerDenialNotice denial={denial(kind)} action={action} />);
    const region = screen.getByRole('status');
    expect(within(region).getByText(title)).toBeInTheDocument();
    expect(region.textContent).toMatch(body);
    expect(region.querySelector('[data-denial]')).toHaveAttribute('data-denial', kind);
  });

  it.each([
    ['unsupported', "This language isn't supported here. Try javascript."],
    ['path_not_allowed', 'A file uses a path the grader owns. Rename or remove it and try again.'],
  ] as const)("%s shows the server's fixed sentence", (kind, detail) => {
    renderNotice(<RunnerDenialNotice denial={denial(kind, { detail })} action="grade" />);
    expect(screen.getByRole('status')).toHaveTextContent(`${detail} Nothing was graded. Your files and notes are still here.`);
  });

  it('offers a keyboard-reachable Reload that runs what the page passes', async () => {
    const user = userEvent.setup();
    const onReload = vi.fn();
    renderNotice(<RunnerDenialNotice denial={denial('reload')} action="run" onReload={onReload} />);
    const reload = screen.getByRole('button', { name: 'Reload' });
    await user.tab();
    expect(reload).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(reloadPage).not.toHaveBeenCalled();
  });

  it('reloads the page itself when no handler is passed', async () => {
    const user = userEvent.setup();
    reloadPage.mockClear();
    renderNotice(<RunnerDenialNotice denial={denial('reload')} action="tests" />);
    await user.click(screen.getByRole('button', { name: 'Reload' }));
    expect(reloadPage).toHaveBeenCalledTimes(1);
  });

  it.each(['retired', 'not_found', 'unsupported', 'path_not_allowed'] as const)('%s offers no Reload', (kind) => {
    renderNotice(<RunnerDenialNotice denial={denial(kind)} action="run" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('focus', () => {
  function Surface({ next }: { next: RunnerDenial | null }) {
    const [shown, setShown] = useState<RunnerDenial | null>(null);
    return (
      <div>
        <button type="button" onClick={() => setShown(next)}>
          Run
        </button>
        <input aria-label="Notes" />
        <RunnerDenialNotice denial={shown} action="run" />
      </div>
    );
  }

  it('never moves focus into the notice', async () => {
    const user = userEvent.setup();
    renderNotice(<Surface next={denial('unavailable')} />);
    const run = screen.getByRole('button', { name: 'Run' });
    await user.click(run);
    expect(screen.getByRole('status')).toHaveTextContent('Unavailable right now');
    expect(screen.getByRole('status')).not.toContainElement(document.activeElement as HTMLElement);
  });

  it('hands focus back to the trigger when the action dropped it', () => {
    renderNotice(<RunnerDenialNotice denial={null} action="run" />);
    const trigger = document.createElement('button');
    trigger.textContent = 'Run';
    document.body.appendChild(trigger);
    trigger.focus();
    trigger.blur();
    expect(document.activeElement).toBe(document.body);
    renderNotice(<RunnerDenialNotice denial={denial('limit', { trigger })} action="run" />);
    expect(trigger).toHaveFocus();
    trigger.remove();
  });

  it('leaves focus alone when the user moved on', () => {
    const trigger = document.createElement('button');
    const elsewhere = document.createElement('input');
    document.body.append(trigger, elsewhere);
    elsewhere.focus();
    renderNotice(<RunnerDenialNotice denial={denial('limit', { trigger })} action="run" />);
    expect(elsewhere).toHaveFocus();
    trigger.remove();
    elsewhere.remove();
  });

  it('does not focus a trigger that is still disabled or gone', () => {
    const disabled = document.createElement('button');
    disabled.disabled = true;
    document.body.appendChild(disabled);
    const detached = document.createElement('button');
    act(() => {
      renderNotice(<RunnerDenialNotice denial={denial('limit', { trigger: disabled })} action="run" />);
    });
    expect(document.activeElement).toBe(document.body);
    renderNotice(<RunnerDenialNotice denial={denial('limit', { trigger: detached })} action="run" />);
    expect(document.activeElement).toBe(document.body);
    disabled.remove();
  });
});
