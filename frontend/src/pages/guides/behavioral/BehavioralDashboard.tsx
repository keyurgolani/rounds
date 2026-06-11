import type { RefObject } from 'react';
import { Link } from 'react-router-dom';
import type { GuideNavGroup } from '../shared/GuideNav';
import type { TrackConfig } from '../guideTypes';
import StudyShell from '../shared/StudyShell';
import {
  Section,
  Callout,
  Pact,
  Prose,
  GuidanceGrid,
  Guidance,
} from '../shared/primitives';
import { behavioralContent } from '../content/behavioral';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

export default function BehavioralDashboard({ config, navGroups, scrollRef }: Props) {
  const { dashboard } = behavioralContent;
  return (
    <StudyShell
      eyebrow={config.eyebrow}
      title={dashboard.title}
      description={dashboard.description}
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      {/* ─── Prepare-anecdotes-first emphasis ─────────────────────────────── */}
      <Section
        id="anecdote-library"
        title="Build your anecdote library before you interview"
        lede="The number-one mistake candidates make is winging behavioral rounds. Interviewers ask questions designed to surface specific signals — ownership, conflict resolution, ambiguity handling, stretch goals, and more — and you can't manufacture a credible 5-minute STAR story under pressure. Professionals prepare a library of 8–12 high-quality anecdotes that cover the common signals, refine them ahead of time, link them to multiple question categories, and walk in able to select a story to fit the question instead of fabricate one."
      >
        <Callout>
          Behavioral rounds aren't a memory test — they're a curated retrieval test. Don't write anecdotes in the room; write them now and curate which one fits the prompt.
        </Callout>

        <GuidanceGrid>
          <Guidance label="Aim for ~10 anecdotes across the signal spectrum">
            Cover ownership, ambiguity, conflict, failure, leadership, stretch goals, scope, delivery, cross-functional work, and technical depth. Each signal should have at least one dedicated story; high-frequency signals like ownership and conflict deserve two.
          </Guidance>
          <Guidance label="Write the full STAR(R) for each anecdote">
            For every story, write out Situation, Task, Action, Result, and Reflection in 4–6 bullet points before the interview. The act of writing forces precision — you'll catch vague "we improved X" phrases while you still have time to fix them.
          </Guidance>
          <Guidance label="Tag each anecdote with the signals it surfaces">
            After writing a story, note which signals it demonstrates (e.g., "ownership, failure, customer-focus"). When an interviewer asks about conflict, you scan your tags, not your memory — which story covers conflict best becomes a fast lookup, not a slow search.
          </Guidance>
          <Guidance label="Practice out loud, not silently">
            Aim for 90–120 seconds per story spoken aloud. Re-reading your notes quietly doesn't build fluency; recording yourself on voice memo does. You'll hear where setup runs long and where the result disappears.
          </Guidance>
          <Guidance label="Rotate and reuse across companies">
            Interviewers at different companies ask the same underlying signals. After each round, note which stories landed, which ones felt shaky, and update the library. A well-maintained library of 10 stories carries you through a full search cycle.
          </Guidance>
        </GuidanceGrid>

        <Pact>
          <Link
            to="/experience/list?anecdote=new"
            style={{
              color: 'var(--accent)',
              fontWeight: 600,
              textDecoration: 'none',
              fontSize: 13.5,
            }}
          >
            + Add a new anecdote to your library →
          </Link>
        </Pact>
      </Section>

      {/* ─── STAR time budget ─────────────────────────────────────────────── */}
      <Section
        eyebrow="STAR(R)"
        title="The time budget of a good answer"
        lede="A common mistake is spending two minutes on Situation and running out of time before the Result. The breakdown below shows proportionally where your time should go — Action is the core of the answer; everything else is context and payoff."
      >
        <StarTimeBudget segments={dashboard.starStrip} />
      </Section>

      {/* ─── Signal portfolio ─────────────────────────────────────────────── */}
      <Section
        eyebrow="Signals"
        title="The trait portfolio behavioral rounds test"
        lede="Every behavioral opener maps to one or more competencies the interviewer needs to confirm. Knowing which signal is being probed lets you select the story that demonstrates it most clearly — and lets you front-load the most relevant evidence rather than burying the lede."
      >
        <GuidanceGrid>
          {dashboard.signalGrid.map((s) => (
            <Guidance key={s.key} label={s.name}>
              {SIGNAL_DESCRIPTIONS[s.key] ?? 'Prepare at least one strong anecdote that demonstrates this competency with specific decisions and measurable outcomes.'}
            </Guidance>
          ))}
        </GuidanceGrid>
      </Section>

      {/* ─── Evidence pact ────────────────────────────────────────────────── */}
      <Section
        eyebrow="Pact"
        title="Evidence beats adjectives"
        lede="Interviewers are trained to filter out self-assessment. Saying 'I'm a strong collaborator' is invisible; describing a specific decision, trade-off, and outcome is not. Every answer should contain at least one number, one artifact, and one named decision."
      >
        <Pact>{dashboard.evidencePact}</Pact>
      </Section>
    </StudyShell>
  );
}

const SIGNAL_DESCRIPTIONS: Record<string, string> = {
  impact:         'Interviewers want to see a metric that moved because of a specific decision you made — not a team outcome attributed to shared effort. Quantify the before/after and name your exact lever.',
  conflict:       'The signal is judgment and influence, not harmony. A story where you "smoothed things over" without evidence of criteria-driven resolution won\'t land. Show both sides and the decision mechanism.',
  failure:        'Own your bad assumption first, before explaining what went wrong externally. Interviewers are looking for honesty and proof that your operating model updated — a later success that wouldn\'t have happened without the failure.',
  ambiguity:      'Show that you created structure rather than waiting for it. Name the options you considered, the trade-off you made explicit, and how you got others aligned without having authority.',
  leadership:     'Leadership in behavioral interviews means behavior change in others — not titles. Show how peers outside your reporting line changed their approach because of something you built, wrote, or demonstrated.',
  mentorship:     'The signal is multiplied impact: did the person you helped level up, and did the mechanism you used persist beyond a single conversation? Cite the mentee\'s later outcomes.',
  pressure:       'Calm prioritization under constraint is the signal. Show what you cut, why, and that you communicated the trade-off explicitly rather than silently dropping scope.',
  'customer-focus': 'Ground the story in a specific customer pain, not a company goal. The strongest answers name a real user problem, show how you surfaced it, and close with a measurable reduction in that pain.',
};

function StarTimeBudget({ segments }: { segments: { id: string; label: string; seconds: string; what: string }[] }) {
  const widths: Record<string, number> = { '15s': 11, '10s': 8, '60–90s': 52, '15–25s': 16, '10–20s': 13 };
  return (
    <div className="card" style={{ padding: 'var(--pad-md)', display: 'grid', gap: 'var(--gap-sm)' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: segments.map((s) => `${widths[s.seconds] ?? 10}fr`).join(' '),
          gap: 4,
          overflow: 'hidden',
          borderRadius: 'var(--radius)',
        }}
      >
        {segments.map((segment, index) => (
          <div
            key={segment.id}
            style={{
              padding: '10px 12px',
              background: index === 2 ? 'var(--accent)' : 'var(--accent-soft)',
              color: index === 2 ? 'var(--bg-elev)' : 'var(--accent)',
              fontSize: 12.5,
              fontWeight: 600,
              textAlign: 'center',
            }}
          >
            {segment.label} · {segment.seconds}
          </div>
        ))}
      </div>
      <div className="grid" style={{ gap: 6 }}>
        {segments.map((segment) => (
          <div key={segment.id} className="grid" style={{ gridTemplateColumns: '110px 1fr', gap: 'var(--gap-sm)', alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}>
              {segment.label.toUpperCase()}
            </span>
            <span style={{ color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{segment.what}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
