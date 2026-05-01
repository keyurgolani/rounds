import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Calendar, CircleDot, User, Briefcase } from 'lucide-react';
import { api } from '../api/client';
import { pb } from '../lib/pocketbase';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import BackLink from '../components/shell/BackLink';

interface Round {
  id: string;
  application_id: string;
  campaign_id?: string;
  round_type: string;
  date: string;
  interviewer: string;
  notes: string;
  result: string;
  scheduled_status: 'scheduled' | 'completed' | 'canceled';
  preparation_notes: string;
  created_at?: string;
  updated_at?: string;
}

interface Application {
  id: string;
  company: string;
  role: string;
}

export default function RoundDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [round, setRound] = useState<Round | null>(null);
  const [app, setApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      setLoading(true);
      try {
        // Direct PB read — rounds don't have a dedicated dispatcher
        // GET yet, so we reach into the SDK for this one.
        const raw = await pb.collection('interview_rounds').getOne(id);
        const r: Round = {
          id: raw.id,
          application_id: (raw as unknown as { application: string }).application,
          campaign_id: (raw as unknown as { campaign?: string }).campaign,
          round_type: (raw as unknown as { round_type: string }).round_type,
          date: (raw as unknown as { date: string }).date ?? '',
          interviewer: (raw as unknown as { interviewer: string }).interviewer ?? '',
          notes: (raw as unknown as { notes: string }).notes ?? '',
          result: (raw as unknown as { result: string }).result ?? '',
          scheduled_status:
            ((raw as unknown as { scheduled_status: string }).scheduled_status as Round['scheduled_status']) ??
            'scheduled',
          preparation_notes:
            (raw as unknown as { preparation_notes: string }).preparation_notes ?? '',
          created_at: (raw as unknown as { created: string }).created,
          updated_at: (raw as unknown as { updated: string }).updated,
        };
        setRound(r);
        if (r.application_id) {
          try {
            const a = await api.get<Application>(`/api/applications/${r.application_id}`);
            setApp(a);
          } catch {
            setApp(null);
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Round not found');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function save(patch: Partial<Round>) {
    if (!round) return;
    setSaving(true);
    try {
      const next = { ...round, ...patch };
      await pb.collection('interview_rounds').update(round.id, {
        round_type: next.round_type,
        date: next.date,
        interviewer: next.interviewer,
        notes: next.notes,
        result: next.result,
        scheduled_status: next.scheduled_status,
        preparation_notes: next.preparation_notes,
      });
      setRound(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ color: 'var(--text-4)', fontSize: 13 }}
      >
        Loading…
      </div>
    );
  }

  if (!round) {
    return (
      <PageShell
        header={
          <div className="px-8 pt-5">
            <BackLink to="/interviews" label="All interviews" />
          </div>
        }
      >
        <div
          className="flex items-center justify-center h-full"
          style={{ color: 'var(--text-3)', fontSize: 13 }}
        >
          Round not found.
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      header={
        <>
          <div className="px-8 pt-5">
            <BackLink to="/interviews" label="All interviews" />
          </div>
          <AppHeader
            eyebrow={`Track · Interview round${app ? ` · ${app.company}` : ''}`}
            title={round.round_type || 'Round'}
            description={
              app
                ? `${app.role} at ${app.company}. Track prep, capture questions asked, and record the outcome.`
                : 'Capture prep, questions asked, and the outcome of this round.'
            }
            actions={
              app && (
                <button
                  type="button"
                  onClick={() => navigate(`/applications/${app.id}`)}
                  style={secondaryBtn}
                >
                  Open application
                </button>
              )
            }
          />
        </>
      }
    >
      <div className="px-5 sm:px-8 py-6 grid gap-5 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-5">
          <div className="card p-6">
            <div
              className="grid gap-3 mb-2"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}
            >
              <Meta label="Round" value={round.round_type || '—'} Icon={CircleDot} />
              <Meta
                label="Date"
                value={round.date || '—'}
                Icon={Calendar}
                mono
              />
              <Meta
                label="Interviewer"
                value={round.interviewer || '—'}
                Icon={User}
              />
              {app && (
                <Meta
                  label="Role"
                  value={app.role}
                  Icon={Briefcase}
                />
              )}
            </div>
          </div>

          <div className="card p-6">
            <div className="eyebrow mb-2">Preparation notes</div>
            <textarea
              rows={4}
              placeholder="What do you want to have top-of-mind going in? Architecture touchstones, past stories, red flags, things to ask."
              value={round.preparation_notes}
              onChange={(e) => setRound({ ...round, preparation_notes: e.target.value })}
              onBlur={() => save({ preparation_notes: round.preparation_notes })}
              style={{ ...textareaStyle, resize: 'vertical' }}
            />
          </div>

          <div className="card p-6">
            <div className="eyebrow mb-2">Notes</div>
            <textarea
              rows={5}
              placeholder="Running notes during or after the round. Questions, reactions, follow-ups."
              value={round.notes}
              onChange={(e) => setRound({ ...round, notes: e.target.value })}
              onBlur={() => save({ notes: round.notes })}
              style={{ ...textareaStyle, resize: 'vertical' }}
            />
          </div>
        </div>

        <aside className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="eyebrow mb-2">Status</div>
            <div className="flex flex-col gap-1.5">
              {(['scheduled', 'completed', 'canceled'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => save({ scheduled_status: s })}
                  disabled={saving}
                  className="flex items-center justify-between"
                  style={{
                    padding: '8px 10px',
                    border: 0,
                    borderRadius: 'var(--radius)',
                    background:
                      round.scheduled_status === s ? 'var(--bg-sunken)' : 'transparent',
                    boxShadow:
                      round.scheduled_status === s ? 'none' : 'inset 0 0 0 1px var(--border)',
                    color: 'var(--text-2)',
                    fontSize: 12.5,
                    cursor: saving ? 'wait' : 'pointer',
                    textAlign: 'left',
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="card p-5">
            <div className="eyebrow mb-2">Result</div>
            <input
              type="text"
              placeholder="Pending / Passed / Follow-up / …"
              value={round.result}
              onChange={(e) => setRound({ ...round, result: e.target.value })}
              onBlur={() => save({ result: round.result })}
              style={inputStyle}
            />
          </div>
          {error && (
            <div style={{ fontSize: 12, color: 'var(--plum)' }}>{error}</div>
          )}
          {app && (
            <Link
              to={`/applications/${app.id}`}
              className="card card-hover"
              style={{
                padding: '12px 16px',
                textDecoration: 'none',
                color: 'var(--accent)',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              Back to {app.company}
            </Link>
          )}
        </aside>
      </div>
    </PageShell>
  );
}

function Meta({
  label,
  value,
  Icon,
  mono,
}: {
  label: string;
  value: string;
  Icon: (p: { size?: number; strokeWidth?: number }) => React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5 min-w-0">
      <span className="eyebrow inline-flex items-center gap-1.5">
        <Icon size={11} strokeWidth={1.7} />
        {label}
      </span>
      <span
        className={mono ? 'mono truncate' : 'truncate'}
        style={{ fontSize: 13, color: 'var(--text)' }}
      >
        {value}
      </span>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '8px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'var(--bg-elev)',
  color: 'var(--text)',
  fontSize: 13,
  width: '100%',
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  fontFamily: 'inherit',
};

const secondaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-2)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};
