import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { GuideTrack } from '../guideTypes';
import { TRACK_CONFIGS } from '../guideTypes';
import { effectiveStatus, useStatusMapVersion } from '../../../hooks/usePracticeStatus';
import type { PracticeKind } from '../../../hooks/progressApi';
import {
  listSystemDesignQuestions,
  listCodingQuestions,
  listBehavioralQuestions,
} from '../../../content/api';
import { listMyAttempts } from '../../ai-coding/aiCodingApi';
import { listMyTakeHomeAttempts } from '../../take-home/takeHomeApi';

type QuestionRow = { id: string };
type AttemptRow = { status: 'in-progress' | 'submitted' | 'graded' };

const QUESTION_KIND: Record<'system-design' | 'coding' | 'behavioral', PracticeKind> = {
  'system-design': 'system',
  coding: 'coding',
  behavioral: 'behavioral',
};

const CTA_LABEL: Record<GuideTrack, string> = {
  'system-design': 'Browse questions',
  coding: 'Browse questions',
  behavioral: 'Browse questions',
  'ai-coding': 'View rounds',
  builder: 'View assignments',
};

export default function StudyPracticeBar({ track }: { track: GuideTrack }) {
  const ctaTo = TRACK_CONFIGS[track].questionsPath;
  const ctaLabel = CTA_LABEL[track];

  return (
    <div
      className="card"
      style={{
        position: 'sticky',
        bottom: 0,
        marginTop: 'auto',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        boxShadow: 'var(--shadow-elev)',
        background: 'var(--bg-elev)',
        zIndex: 10,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <ProgressStrip track={track} />
      </div>
      <Link
        to={ctaTo}
        className="flex items-center gap-2"
        style={{
          padding: '9px 14px',
          borderRadius: 'var(--radius)',
          background: 'var(--accent)',
          color: 'var(--bg-elev)',
          fontSize: 13,
          fontWeight: 600,
          textDecoration: 'none',
          letterSpacing: '0.01em',
          whiteSpace: 'nowrap',
        }}
      >
        {ctaLabel}
        <ArrowRight size={14} strokeWidth={1.8} />
      </Link>
    </div>
  );
}

function ProgressStrip({ track }: { track: GuideTrack }) {
  if (track === 'system-design' || track === 'coding' || track === 'behavioral') {
    return <QuestionProgress track={track} />;
  }
  if (track === 'ai-coding') {
    return <AttemptProgress kind="ai-coding" />;
  }
  return <AttemptProgress kind="builder" />;
}

function QuestionProgress({
  track,
}: {
  track: 'system-design' | 'coding' | 'behavioral';
}) {
  const statusVersion = useStatusMapVersion();
  const [rows, setRows] = useState<QuestionRow[] | null>(null);

  useEffect(() => {
    let active = true;
    const fetcher =
      track === 'system-design'
        ? listSystemDesignQuestions<QuestionRow>()
        : track === 'coding'
        ? listCodingQuestions<QuestionRow>()
        : listBehavioralQuestions<QuestionRow>();
    fetcher
      .then((r) => {
        if (active) setRows(r);
      })
      .catch(() => {
        if (active) setRows([]);
      });
    return () => {
      active = false;
    };
  }, [track]);

  const breakdown = useMemo(() => {
    if (!rows) return null;
    const kind = QUESTION_KIND[track];
    let mastered = 0;
    let inProgress = 0;
    for (const q of rows) {
      const s = effectiveStatus(kind, q.id);
      if (s === 'mastered') mastered += 1;
      else if (s === 'in-progress') inProgress += 1;
    }
    return { mastered, inProgress, total: rows.length };
  }, [rows, track, statusVersion]);

  if (!breakdown) {
    return <SkeletonLine />;
  }
  const masteredPct = breakdown.total ? (breakdown.mastered / breakdown.total) * 100 : 0;
  const progressPct = breakdown.total ? (breakdown.inProgress / breakdown.total) * 100 : 0;

  return (
    <div className="flex flex-col gap-1.5" style={{ width: '100%' }}>
      <div className="mono uppercase" style={{ fontSize: 11, color: 'var(--text-3)', letterSpacing: '0.08em' }}>
        <span style={{ color: 'var(--text)', fontWeight: 700 }}>{breakdown.mastered} / {breakdown.total}</span>
        {' mastered'}
        {breakdown.inProgress > 0 && (
          <span style={{ color: 'var(--text-4)' }}> · {breakdown.inProgress} practicing</span>
        )}
      </div>
      <div
        style={{
          position: 'relative',
          height: 4,
          borderRadius: 999,
          background: 'var(--bg-sunken)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            width: `${masteredPct}%`,
            background: 'var(--accent)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${masteredPct}%`,
            width: `${progressPct}%`,
            background: 'var(--accent)',
            opacity: 0.35,
          }}
        />
      </div>
    </div>
  );
}

function AttemptProgress({ kind }: { kind: 'ai-coding' | 'builder' }) {
  const [rows, setRows] = useState<AttemptRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    const fetcher = kind === 'ai-coding' ? listMyAttempts() : listMyTakeHomeAttempts();
    fetcher
      .then((r) => {
        if (active) setRows(r as AttemptRow[]);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [kind]);

  if (failed) {
    return null;
  }
  if (!rows) {
    return <SkeletonLine />;
  }
  const noun = kind === 'ai-coding' ? 'rounds' : 'assignments';
  const total = rows.length;
  const graded = rows.filter((r) => r.status === 'graded').length;
  return (
    <div className="mono uppercase" style={{ fontSize: 11, color: 'var(--text-3)', letterSpacing: '0.08em' }}>
      <span style={{ color: 'var(--text)', fontWeight: 700 }}>{total} {noun}</span>
      {' started'}
      {graded > 0 && <span style={{ color: 'var(--text-4)' }}> · {graded} graded</span>}
    </div>
  );
}

function SkeletonLine() {
  return (
    <div
      style={{
        height: 12,
        width: 180,
        borderRadius: 999,
        background: 'var(--bg-sunken)',
        opacity: 0.6,
      }}
    />
  );
}
