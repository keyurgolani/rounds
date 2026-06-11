import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LibraryPicker from '../LibraryPicker';
import { loadLibrarySnapshot } from '../library';

vi.mock('../library', () => ({ loadLibrarySnapshot: vi.fn() }));

const mockSnapshot = {
  jobs: {
    j1: { id: 'j1', company: 'Acme', role: 'Staff Eng', location: '', employment_type: '', start_date: '2021-01-01', end_date: null, description: '', tags: [] },
  },
  projects: {},
  bullets: {
    b1: { id: 'b1', title: 'Cut p99 40%', impact: '', category: '', date: '2021-06-01', tags: [] },
    b2: { id: 'b2', title: 'Led migration', impact: '', category: '', date: '2021-07-01', tags: [] },
  },
  connMap: {
    j1: { bullet: ['b1', 'b2'] } as Record<string, string[]>,
  },
};

beforeEach(() => {
  vi.mocked(loadLibrarySnapshot).mockResolvedValue(mockSnapshot as never);
});

describe('LibraryPicker', () => {
  it('renders bullet titles with checkboxes checked by default after expanding the job row', async () => {
    render(
      <LibraryPicker kind="job" open onClose={vi.fn()} onPick={vi.fn()} />,
    );

    // Wait for snapshot to load and job row to appear
    const jobHeader = await screen.findByText('Staff Eng · Acme');
    fireEvent.click(jobHeader);

    // Both bullet titles should now be visible
    expect(await screen.findByText('Cut p99 40%')).toBeInTheDocument();
    expect(screen.getByText('Led migration')).toBeInTheDocument();

    // Both checkboxes should be checked by default
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(2);
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).toBeChecked();
  });

  it('calls onPick with only checked bullet ids/titles and then calls onClose', async () => {
    const onPick = vi.fn();
    const onClose = vi.fn();

    render(
      <LibraryPicker kind="job" open onClose={onClose} onPick={onPick} />,
    );

    // Wait for snapshot to load and expand the job row
    const jobHeader = await screen.findByText('Staff Eng · Acme');
    fireEvent.click(jobHeader);

    // Wait for bullets
    await screen.findByText('Cut p99 40%');

    // Uncheck b2's checkbox (second checkbox)
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[1]); // uncheck b2 "Led migration"

    // Click the "Add to resume" button
    const addButton = screen.getByRole('button', { name: /add to resume/i });
    fireEvent.click(addButton);

    expect(onPick).toHaveBeenCalledWith({
      ref: 'j1',
      bulletIds: ['b1'],
      bulletTitles: ['Cut p99 40%'],
    });
    expect(onClose).toHaveBeenCalled();
  });
});
