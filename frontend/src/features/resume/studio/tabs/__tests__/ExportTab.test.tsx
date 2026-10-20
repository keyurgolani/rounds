// Server PDF export denial state (ROUNDS-00A-L01): a refused or failed
// render reads as a denial with a browser-print fallback, and focus
// stays on the Download button.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../../export/pdf', () => ({
  exportPdfServer: vi.fn(),
  exportPdfPrint: vi.fn(),
}));

import ExportTab from '../ExportTab';
import { exportPdfPrint, exportPdfServer } from '../../../export/pdf';
import { RunnerError } from '../../../../../lib/runnerFetch';
import type { Resume, ResumeData } from '../../../types';

const resume = { id: 'r1', slug: 'jane-doe', name: 'Jane Doe' } as unknown as Resume;
const data = { personalInfo: { fullName: 'Jane Doe' } } as unknown as ResumeData;

function renderTab() {
  const onBeforeExport = vi.fn().mockResolvedValue(undefined);
  render(
    <MemoryRouter>
      <ExportTab resume={resume} data={data} onBeforeExport={onBeforeExport} />
    </MemoryRouter>,
  );
  return { onBeforeExport };
}

function pdfDownload() {
  return screen.getAllByRole('button', { name: /download/i })[0];
}

beforeEach(() => {
  vi.mocked(exportPdfServer).mockReset();
  vi.mocked(exportPdfPrint).mockReset();
});

describe('ExportTab server PDF', () => {
  it('announces a turned-off renderer and offers browser printing by keyboard', async () => {
    vi.mocked(exportPdfServer).mockImplementation(async () => {
      // Browsers drop focus from a button that turns disabled mid-action.
      (document.activeElement as HTMLElement | null)?.blur();
      throw new RunnerError({ message: 'PDF render failed 503: Off.', status: 503, code: 'route_disabled' });
    });
    const user = userEvent.setup();
    const { onBeforeExport } = renderTab();
    const download = pdfDownload();
    download.focus();
    await user.keyboard('{Enter}');

    const region = await screen.findByText('Turned off');
    const status = region.closest('[role="status"]') as HTMLElement;
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveTextContent('Server PDF export is turned off on this server. Your resume is unchanged.');
    await waitFor(() => expect(download).toHaveFocus());

    const print = within(status).getByRole('button', { name: 'Print to PDF instead' });
    print.focus();
    await user.keyboard('{Enter}');
    await waitFor(() => expect(exportPdfPrint).toHaveBeenCalledTimes(1));
    expect(onBeforeExport).toHaveBeenCalledTimes(2);
  });

  it('reads a renderer outage as unavailable, not as raw error text', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(
      new RunnerError({ message: 'PDF render failed 502: chromium crashed at 0x1', status: 502 }),
    );
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Unavailable right now')).toBeInTheDocument();
    expect(screen.queryByText(/chromium crashed/)).not.toBeInTheDocument();
  });

  it('asks the user to sign in again when the bearer is missing', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(
      new RunnerError({ message: 'Not authenticated.', status: 0, code: 'unauthenticated' }),
    );
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Sign in again')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  });

  it('keeps showing other failures inline as before', async () => {
    vi.mocked(exportPdfServer).mockRejectedValue(new Error('No resume preview is currently rendered.'));
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('No resume preview is currently rendered.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  it('clears the denial when the next export succeeds', async () => {
    vi.mocked(exportPdfServer)
      .mockRejectedValueOnce(new RunnerError({ message: 'x', status: 503, code: 'route_disabled' }))
      .mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderTab();
    await user.click(pdfDownload());
    expect(await screen.findByText('Turned off')).toBeInTheDocument();
    await user.click(pdfDownload());
    await waitFor(() => expect(screen.getByRole('status')).toBeEmptyDOMElement());
  });
});
