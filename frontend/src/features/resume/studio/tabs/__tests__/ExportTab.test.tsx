// The Export tab (ROUNDS-00A-L01, ROUNDS-00A-L04): server PDF saves
// pending edits, then renders the server's snapshot of the saved resume;
// each outcome reads as a state with its next step, never raw error text,
// and the six other formats export what's on screen whatever server PDF
// says.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor, within } from '@testing-library/react';
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
import { exportPdfPrint, exportPdfServer, SnapshotIneligible } from '../../../export/pdf';
import { exportDocx } from '../../../export/docx';
import { exportMarkdown } from '../../../export/markdown';
import { reloadPage } from '../../../../../lib/definitions';
import { RunnerError } from '../../../../../lib/runnerFetch';
import type { Resume, ResumeData } from '../../../types';

const SAVED = '2026-11-11 08:00:00.000Z';
const resume = { id: 'resumeaaaaaaaa1', slug: 'jane-doe', name: 'Jane Doe', updated_at: SAVED } as unknown as Resume;
const data = { personalInfo: { fullName: 'Jane Doe' } } as unknown as ResumeData;

function ui(onBeforeExport: () => Promise<string>, current: Resume = resume) {
  return (
    <MemoryRouter>
      <ExportTab resume={current} data={data} onBeforeExport={onBeforeExport} />
    </MemoryRouter>
  );
}

function renderTab(onBeforeExport = vi.fn().mockResolvedValue(SAVED)) {
  const view = render(ui(onBeforeExport));
  return { onBeforeExport, view };
}

function pdfDownload() {
  return screen.getAllByRole('button', { name: /download/i })[0];
}

function pdfStatus() {
  return screen.getByTestId('server-pdf-status');
}

const refused = (code: string, status: number, extra: Partial<ConstructorParameters<typeof RunnerError>[0]> = {}) =>
  new RunnerError({ message: `Server PDF failed ${status}: x`, status, code, ...extra });

beforeEach(() => {
  vi.mocked(exportPdfServer).mockReset();
  vi.mocked(exportPdfPrint).mockReset();
  vi.mocked(exportDocx).mockReset();
  vi.mocked(exportMarkdown).mockReset();
  vi.mocked(reloadPage).mockReset();
});

describe('ExportTab server PDF', () => {
  it('saves first, then renders the saved resume by id and announces each step', async () => {
    let saved: (updated: string) => void = () => undefined;
    const onBeforeExport = vi.fn(() => new Promise<string>((resolve) => (saved = resolve)));
    let rendered: () => void = () => undefined;
    vi.mocked(exportPdfServer).mockImplementation(async ({ onPhase }) => {
      onPhase?.('preparing');
      onPhase?.('rendering');
      await new Promise<void>((resolve) => (rendered = resolve));
    });
    const user = userEvent.setup();
    renderTab(onBeforeExport);
    await user.click(pdfDownload());

    expect(pdfStatus()).toHaveTextContent('Saving your latest edits…');
    expect(exportPdfServer).not.toHaveBeenCalled();
    await act(async () => saved('2026-11-11 08:00:05.000Z'));
    expect(exportPdfServer).toHaveBeenCalledWith(
      expect.objectContaining({ sourceId: 'resumeaaaaaaaa1', expectedUpdated: '2026-11-11 08:00:05.000Z', filenameBase: 'jane-doe' }),
    );
    expect(pdfStatus()).toHaveTextContent('Rendering the PDF…');
    await act(async () => rendered());
    expect(pdfStatus()).toHaveTextContent('PDF downloaded.');
  });

  it('pauses after a failed save, asks the server nothing, and keeps the other formats working', async () => {
    const onBeforeExport = vi.fn().mockRejectedValue(new Error('offline'));
    const user = userEvent.setup();
    renderTab(onBeforeExport);
    await user.click(pdfDownload());
    expect(await within(pdfStatus()).findByText('Waiting on your edits')).toBeInTheDocument();
    expect(exportPdfServer).not.toHaveBeenCalled();
    expect(screen.queryByText('offline')).not.toBeInTheDocument();

    const [, docx, , markdown] = screen.getAllByRole('button', { name: /download/i });
    await user.click(docx);
    await waitFor(() => expect(exportDocx).toHaveBeenCalledWith(data, 'jane-doe'));
    await user.click(markdown);
    await waitFor(() => expect(exportMarkdown).toHaveBeenCalledWith(data, 'jane-doe'));
  });

  it('offers a reload when the resume changed elsewhere', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused('snapshot_conflict', 409));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    const status = pdfStatus();
    expect(await within(status).findByText('Changed somewhere else')).toBeInTheDocument();
    await user.click(within(status).getByRole('button', { name: 'Reload' }));
    expect(reloadPage).toHaveBeenCalledTimes(1);
    expect(pdfDownload()).not.toHaveAttribute('aria-disabled');
  });

  it('names a design reason, points to the Design tab, and turns the button off', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(new SnapshotIneligible('design_out_of_domain'));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    const status = pdfStatus();
    expect(await within(status).findByText('No server PDF for this resume')).toBeInTheDocument();
    expect(status).toHaveTextContent('outside what the templates render');
    expect(status).toHaveTextContent('Design tab');
    expect(status).toHaveTextContent('browser print still work');
    expect(pdfDownload()).toHaveAttribute('aria-disabled', 'true');

    await user.click(pdfDownload());
    expect(exportPdfServer).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['data_malformed', 'shape the templates can read'],
    ['data_too_large', 'too large'],
    ['markup_unsafe', 'safety checks'],
    ['demo_account', 'demo account'],
  ])('says why for %s, with no design hint', async (reason, words) => {
    vi.mocked(exportPdfServer).mockRejectedValue(new SnapshotIneligible(reason));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    const status = pdfStatus();
    await waitFor(() => expect(status).toHaveTextContent(words));
    expect(status).not.toHaveTextContent('Design tab');
  });

  it('a newer save lifts an answer about the old one', async () => {
    vi.mocked(exportPdfServer).mockRejectedValueOnce(new SnapshotIneligible('design_out_of_domain'));
    const user = userEvent.setup();
    const onBeforeExport = vi.fn().mockResolvedValue(SAVED);
    const { view } = renderTab(onBeforeExport);
    await user.click(pdfDownload());
    await waitFor(() => expect(pdfDownload()).toHaveAttribute('aria-disabled', 'true'));
    view.rerender(ui(onBeforeExport, { ...resume, updated_at: '2026-11-11 08:10:00.000Z' } as Resume));
    expect(pdfDownload()).not.toHaveAttribute('aria-disabled');
    expect(pdfStatus()).toBeEmptyDOMElement();
  });

  it('says the account is at its snapshot limit and turns the button off', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused('snapshot_quota_exceeded', 429));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await within(pdfStatus()).findByText('Server copy limit reached')).toBeInTheDocument();
    expect(pdfDownload()).toHaveAttribute('aria-disabled', 'true');
  });

  it('reads a resume the server no longer has as not on the server', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused('not_found', 404));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await within(pdfStatus()).findByText('Not on the server')).toBeInTheDocument();
  });

  it('announces a turned-off server PDF, offers browser printing, and turns the button off', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused('route_disabled', 503));
    const user = userEvent.setup();
    const { onBeforeExport } = renderTab();
    await user.click(pdfDownload());
    const notice = (await screen.findByText('Turned off')).closest('[role="status"]') as HTMLElement;
    expect(notice).toHaveTextContent('Server PDF export is turned off on this server.');
    expect(pdfDownload()).toHaveAttribute('aria-disabled', 'true');
    await user.click(within(notice).getByRole('button', { name: 'Print to PDF instead' }));
    await waitFor(() => expect(exportPdfPrint).toHaveBeenCalledTimes(1));
    expect(onBeforeExport).toHaveBeenCalledTimes(2);
  });

  it('lifts a limit once its wait is over', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.mocked(exportPdfServer).mockRejectedValue(refused('quota_exceeded', 429, { retryAfterSeconds: 30 }));
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderTab();
      await user.click(pdfDownload());
      expect(await screen.findByText('Limit reached')).toBeInTheDocument();
      expect(pdfDownload()).toHaveAttribute('aria-disabled', 'true');
      await act(async () => vi.advanceTimersByTime(30_000));
      expect(pdfDownload()).not.toHaveAttribute('aria-disabled');
    } finally {
      vi.useRealTimers();
    }
  });

  it.each([
    ['materializer_unavailable', 503],
    ['worker_unavailable', 503],
    ['checksum_mismatch', 409],
    ['invalid_request', 422],
  ])('reads %s as unavailable for now, with the button still live', async (code, status) => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused(code, status));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    const notice = (await screen.findByText('Unavailable right now')).closest('[role="status"]') as HTMLElement;
    expect(within(notice).getByRole('button', { name: 'Print to PDF instead' })).toBeInTheDocument();
    expect(pdfDownload()).not.toHaveAttribute('aria-disabled');
  });

  it('never shows raw error text', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(new Error('chromium crashed at 0x1'));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Unavailable right now')).toBeInTheDocument();
    expect(screen.queryByText(/chromium crashed/)).not.toBeInTheDocument();
  });

  it('asks the user to sign in again when the session ended', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(refused('unauthenticated', 401));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Sign in again')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  });

  it('clears the last answer when the next export succeeds', async () => {
    vi.mocked(exportPdfServer)
      .mockRejectedValueOnce(refused('worker_unavailable', 503))
      .mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Unavailable right now')).toBeInTheDocument();
    await user.click(pdfDownload());
    await waitFor(() => expect(pdfStatus()).toHaveTextContent('PDF downloaded.'));
    expect(screen.queryByText('Unavailable right now')).not.toBeInTheDocument();
  });
});
