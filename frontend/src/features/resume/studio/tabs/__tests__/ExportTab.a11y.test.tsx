// The Export tab's accessibility (ROUNDS-00A-L04). Every server PDF state
// is reached with the keyboard alone, and a polite live region speaks it,
// in words with an icon beside them. Focus never leaves server PDF's
// button. When that button can't act, it says so through aria-disabled,
// takes its description from the message, and can still be focused. The
// six other formats work in every state, and all seven buttons measure
// at least 44 by 44 CSS pixels. Layout at 390 px is checked in a real
// browser (the design review's screenshots); jsdom has no layout.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../../export/pdf', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../../export/pdf')>()),
  exportPdfServer: vi.fn(),
  exportPdfPrint: vi.fn(),
}));
vi.mock('../../../export/docx', () => ({ exportDocx: vi.fn() }));
vi.mock('../../../export/markdown', () => ({ exportMarkdown: vi.fn() }));
vi.mock('../../../../../lib/definitions', () => ({ reloadPage: vi.fn() }));

import ExportTab from '../ExportTab';
import { exportPdfServer, SnapshotIneligible } from '../../../export/pdf';
import { exportDocx } from '../../../export/docx';
import { RunnerError } from '../../../../../lib/runnerFetch';
import type { Resume, ResumeData } from '../../../types';

const SAVED = '2026-11-11 08:00:00.000Z';
const resume = { id: 'resumeaaaaaaaa1', slug: 'jane-doe', name: 'Jane Doe', updated_at: SAVED } as unknown as Resume;
const data = { personalInfo: { fullName: 'Jane Doe' } } as unknown as ResumeData;

const refused = (code: string, status: number, retryAfterSeconds: number | null = null) =>
  new RunnerError({ message: `x ${status}`, status, code, retryAfterSeconds });

type Case = {
  name: string;
  // What the save and the server answer.
  save?: () => Promise<string>;
  server?: () => Promise<void>;
  // The words the state is announced with.
  says: RegExp;
  unavailable: boolean;
};

const CASES: Case[] = [
  { name: 'downloaded', server: async () => undefined, says: /PDF downloaded\./, unavailable: false },
  { name: 'paused after a failed save', save: () => Promise.reject(new Error('offline')), says: /Waiting on your edits/, unavailable: false },
  { name: 'changed elsewhere', server: () => Promise.reject(refused('snapshot_conflict', 409)), says: /Changed somewhere else/, unavailable: false },
  {
    name: 'not available for this resume',
    server: () => Promise.reject(new SnapshotIneligible('design_out_of_domain')),
    says: /No server PDF for this resume/,
    unavailable: true,
  },
  { name: 'at the snapshot limit', server: () => Promise.reject(refused('snapshot_quota_exceeded', 429)), says: /Server copy limit reached/, unavailable: true },
  { name: 'not on the server', server: () => Promise.reject(refused('not_found', 404)), says: /Not on the server/, unavailable: false },
  { name: 'turned off', server: () => Promise.reject(refused('route_disabled', 503)), says: /Turned off/, unavailable: true },
  { name: 'at a limit', server: () => Promise.reject(refused('quota_exceeded', 429, 7200)), says: /Limit reached/, unavailable: true },
  { name: 'not permitted', server: () => Promise.reject(refused('not_permitted', 403)), says: /Not available/, unavailable: true },
  { name: 'degraded', server: () => Promise.reject(refused('materializer_unavailable', 503)), says: /Unavailable right now/, unavailable: false },
  { name: 'signed out', server: () => Promise.reject(refused('unauthenticated', 401)), says: /Sign in again/, unavailable: false },
  { name: 'out of date', server: () => Promise.reject(refused('legacy_request_rejected', 422)), says: /Reload to continue/, unavailable: false },
];

function renderTab(save: () => Promise<string>) {
  render(
    <MemoryRouter>
      <ExportTab resume={resume} data={data} onBeforeExport={save} />
    </MemoryRouter>,
  );
}

function buttons(): HTMLElement[] {
  return screen.getAllByRole('button', { name: /^(download|print|working…)$/i });
}

// Every status region under the server PDF row, as one text.
function announced(): string {
  return screen
    .getAllByRole('status')
    .map((region) => region.textContent ?? '')
    .join(' ');
}

beforeEach(() => {
  vi.mocked(exportPdfServer).mockReset();
  vi.mocked(exportDocx).mockReset();
});

describe('Export tab accessibility', () => {
  it('lists seven buttons, each at least 44 by 44 CSS pixels, in reading order', async () => {
    renderTab(() => Promise.resolve(SAVED));
    const all = buttons();
    expect(all).toHaveLength(7);
    for (const b of all) {
      expect(parseFloat(b.style.minHeight)).toBeGreaterThanOrEqual(44);
      expect(parseFloat(b.style.minWidth)).toBeGreaterThanOrEqual(44);
      expect(b).not.toBeDisabled();
    }
    const user = userEvent.setup();
    for (const b of all) {
      await user.tab();
      expect(b).toHaveFocus();
    }
  });

  it.each(CASES)('by keyboard alone, $name is announced and focus stays on server PDF', async (c) => {
    vi.mocked(exportPdfServer).mockImplementation(c.server ?? (async () => undefined));
    renderTab(c.save ?? (() => Promise.resolve(SAVED)));
    const user = userEvent.setup();
    await user.tab();
    const pdf = buttons()[0];
    expect(pdf).toHaveFocus();
    await user.keyboard('{Enter}');

    await waitFor(() => expect(announced()).toMatch(c.says));
    expect(pdf).toHaveFocus();
    // The message is in a polite status region, with an icon and words.
    const region = screen.getAllByRole('status').find((r) => c.says.test(r.textContent ?? ''))!;
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region.querySelector('svg[aria-hidden="true"]')).not.toBeNull();

    if (c.unavailable) {
      expect(pdf).toHaveAttribute('aria-disabled', 'true');
      const describedBy = pdf.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      expect(document.getElementById(describedBy!)?.textContent).toMatch(c.says);
      // Still focusable, and a press does nothing.
      await user.keyboard('{Enter}');
      expect(exportPdfServer).toHaveBeenCalledTimes(c.save ? 0 : 1);
    } else {
      expect(pdf).not.toHaveAttribute('aria-disabled');
    }

    // The six other formats stay usable.
    for (const other of buttons().slice(1)) expect(other).not.toHaveAttribute('aria-disabled');
    const docx = buttons()[2];
    docx.focus();
    await user.keyboard(' ');
    await waitFor(() => expect(exportDocx).toHaveBeenCalledTimes(1));
  });

  it('announces saving, preparing, and rendering, with the button busy and still focused', async () => {
    let saved: (updated: string) => void = () => undefined;
    let stage: (phase: 'preparing' | 'rendering') => void = () => undefined;
    let rendered: () => void = () => undefined;
    vi.mocked(exportPdfServer).mockImplementation(async ({ onPhase }) => {
      stage = (phase) => onPhase?.(phase);
      await new Promise<void>((resolve) => (rendered = resolve));
    });
    renderTab(() => new Promise<string>((resolve) => (saved = resolve)));
    const user = userEvent.setup();
    await user.tab();
    const pdf = buttons()[0];
    await user.keyboard('{Enter}');

    expect(announced()).toMatch(/Saving your latest edits…/);
    expect(pdf).toHaveAttribute('aria-busy', 'true');
    expect(pdf).toHaveAttribute('aria-disabled', 'true');
    expect(pdf).toHaveFocus();
    await act(async () => saved(SAVED));
    await act(async () => stage('preparing'));
    expect(announced()).toMatch(/Preparing the server copy…/);
    await act(async () => stage('rendering'));
    expect(announced()).toMatch(/Rendering the PDF…/);
    expect(pdf).toHaveFocus();
    await act(async () => rendered());
    expect(announced()).toMatch(/PDF downloaded\./);
    expect(pdf).not.toHaveAttribute('aria-busy');
    expect(pdf).not.toHaveAttribute('aria-disabled');
    expect(pdf).toHaveFocus();
  });

  it('keeps the other buttons from starting a second export while one runs', async () => {
    let rendered: () => void = () => undefined;
    vi.mocked(exportPdfServer).mockImplementation(() => new Promise<void>((resolve) => (rendered = resolve)));
    renderTab(() => Promise.resolve(SAVED));
    const user = userEvent.setup();
    await user.click(buttons()[0]);
    const docx = buttons()[2];
    expect(docx).toHaveAttribute('aria-disabled', 'true');
    await user.click(docx);
    expect(exportDocx).not.toHaveBeenCalled();
    await act(async () => rendered());
    expect(docx).not.toHaveAttribute('aria-disabled');
  });
});
