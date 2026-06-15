// src/components/dashboard/__tests__/widgets.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PracticeReadiness from '../PracticeReadiness';
import type { TrackReadiness } from '../derive';
import BehavioralDepth from '../BehavioralDepth';
import type { BehavioralDepthResult } from '../derive';
import PipelinePulse from '../PipelinePulse';
import UpcomingInterviews from '../UpcomingInterviews';
import type { DashRound, DashApp } from '../derive';
import ResumeCoverage from '../ResumeCoverage';
import type { ResumeCoverageResult } from '../derive';
import ExperienceLibraryOverview from '../ExperienceLibraryOverview';
import type { ExperienceOverviewResult } from '../derive';

const tracks: TrackReadiness[] = [
  { key: 'coding', name: 'Coding', to: '/coding/guide', color: 'var(--forest)', total: 40, mastered: 14, inProgress: 5 },
  { key: 'ai-coding', name: 'AI-Assisted Coding', to: '/ai-coding/guide', color: 'var(--ochre)', total: 8, mastered: 2, inProgress: 1 },
];

describe('PracticeReadiness', () => {
  it('renders a row per track with mastered/total', () => {
    render(<MemoryRouter><PracticeReadiness tracks={tracks} /></MemoryRouter>);
    expect(screen.getByText('Coding')).toBeInTheDocument();
    expect(screen.getByText('AI-Assisted Coding')).toBeInTheDocument();
    expect(screen.getByText('14/40')).toBeInTheDocument();
  });
});

const depth: BehavioralDepthResult = {
  covered: 11, total: 18, storyCount: 9, categoryCount: 6,
  thinCategories: [{ id: 'c1', name: 'Conflict', count: 0 }, { id: 'c2', name: 'Failure', count: 1 }],
};

describe('BehavioralDepth', () => {
  it('shows question coverage and thin categories', () => {
    render(<MemoryRouter><BehavioralDepth depth={depth} /></MemoryRouter>);
    expect(screen.getByText(/11/)).toBeInTheDocument();
    expect(screen.getByText('Conflict · 0')).toBeInTheDocument();
  });
});

describe('PipelinePulse', () => {
  it('renders a bar per status with counts', () => {
    render(<MemoryRouter><PipelinePulse counts={{ Wishlist: 3, Applied: 5, Interviewing: 2, Offer: 1 }} /></MemoryRouter>);
    expect(screen.getByText('Applied')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});

const rounds: DashRound[] = [{ id: 'r1', application_id: 'a1', round_type: 'System Design', date: '2026-06-16T00:00:00Z' }];
const apps: DashApp[] = [{ id: 'a1', company: 'Stripe', role: 'SWE', status: 'Interviewing' }];

describe('UpcomingInterviews', () => {
  it('lists rounds with their application', () => {
    render(<MemoryRouter><UpcomingInterviews rounds={rounds} apps={apps} /></MemoryRouter>);
    expect(screen.getByText('System Design')).toBeInTheDocument();
    expect(screen.getByText(/Stripe/)).toBeInTheDocument();
  });
  it('shows an empty state when there are no rounds', () => {
    render(<MemoryRouter><UpcomingInterviews rounds={[]} apps={[]} /></MemoryRouter>);
    expect(screen.getByText(/No scheduled rounds/i)).toBeInTheDocument();
  });
});

describe('ResumeCoverage', () => {
  it('names applications missing a tailored variant', () => {
    const cov: ResumeCoverageResult = {
      resumeCount: 3, lastEditedAt: '2026-06-12T00:00:00Z', relevant: 4, covered: 2,
      missing: [{ id: 'a3', company: 'Figma' }, { id: 'a4', company: 'Ramp' }],
    };
    render(<MemoryRouter><ResumeCoverage coverage={cov} /></MemoryRouter>);
    expect(screen.getByText('Figma')).toBeInTheDocument();
    expect(screen.getByText('Ramp')).toBeInTheDocument();
  });
  it('renders an empty-state when there are no resumes', () => {
    const cov: ResumeCoverageResult = { resumeCount: 0, lastEditedAt: null, relevant: 0, covered: 0, missing: [] };
    render(<MemoryRouter><ResumeCoverage coverage={cov} /></MemoryRouter>);
    expect(screen.getByText(/Create your first resume/i)).toBeInTheDocument();
  });
});

describe('ExperienceLibraryOverview', () => {
  it('shows entity counts and unused bullets', () => {
    const ov: ExperienceOverviewResult = { jobs: 5, projects: 8, anecdotes: 9, bullets: 23, addedThisWeek: 3, unusedBullets: 4 };
    render(<MemoryRouter><ExperienceLibraryOverview overview={ov} /></MemoryRouter>);
    expect(screen.getByText('jobs')).toBeInTheDocument();
    expect(screen.getByText(/4 bullets not yet/i)).toBeInTheDocument();
  });
});
