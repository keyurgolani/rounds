import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Flame } from 'lucide-react';
import { initials, useAuth } from '../auth/AuthProvider';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import { useLoginStreak } from '../hooks/useLoginStreak';

// Profile is the user's identity page. Campaigns used to live inline
// here under a hash anchor; they're now a peer page under the user
// menu so this stays focused on account info.

export default function Profile() {
  const { user } = useAuth();

  if (!user) return null;
  return (
    <PageShell
      header={
        <AppHeader
          eyebrow="Account · Profile"
          title="Your profile"
          description="How you show up inside Rounds — the name at the top of the sidebar, the target role you're prepping for, and a line of context for future you."
        />
      }
    >
      <ProfileBody />
    </PageShell>
  );
}

function ProfileBody() {
  const { user, updateProfile, logout } = useAuth();
  const navigate = useNavigate();
  const streak = useLoginStreak();
  const [name, setName] = useState(user?.name ?? '');
  const [bio, setBio] = useState(user?.bio ?? '');
  const [target, setTarget] = useState(user?.target ?? '');
  const [saved, setSaved] = useState(false);

  if (!user) return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateProfile({ name: name.trim(), bio: bio.trim(), target: target.trim() });
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const since = new Date(user.createdAt).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="px-5 sm:px-8 py-6 grid gap-6 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_320px]">
      <form onSubmit={handleSave} className="card p-6 flex flex-col gap-4">
        <div className="flex items-center gap-4 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <div
            className="display-italic flex items-center justify-center flex-shrink-0"
            style={{
              width: 64,
              height: 64,
              borderRadius: 999,
              background: 'var(--accent-soft)',
              color: 'var(--accent)',
              fontSize: 26,
            }}
          >
            {initials(user.name || 'You')}
          </div>
          <div className="min-w-0">
            <div className="display-italic" style={{ fontSize: 24, fontWeight: 400, lineHeight: 1.1 }}>
              {user.name}
            </div>
            <div className="mono" style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 2 }}>
              {user.email}
            </div>
          </div>
        </div>

        <label className="flex flex-col gap-1">
          <span className="eyebrow">Display name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={inputStyle}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="eyebrow">Target role / company</span>
          <input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="e.g. Stripe L5 — Backend"
            style={inputStyle}
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="eyebrow">Short bio</span>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            placeholder="One line of context — career chapter, focus, or a principle you're leaning on."
            style={{ ...inputStyle, resize: 'vertical', minHeight: 80 }}
          />
        </label>

        <div className="flex items-center gap-3 pt-2">
          <button type="submit" style={primaryBtn}>
            Save changes
          </button>
          {saved && (
            <span
              className="mono"
              style={{ fontSize: 11, color: 'var(--forest)', letterSpacing: '0.1em' }}
            >
              SAVED
            </span>
          )}
        </div>
      </form>

      <aside className="flex flex-col gap-4">
        <div className="card p-5">
          <div className="eyebrow mb-2.5">Account</div>
          <InfoRow label="Provider" value={providerLabel(user.provider)} mono />
          <InfoRow label="Member since" value={since} />
          <InfoRow label="User ID" value={user.id} mono />
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="eyebrow inline-flex items-center gap-1.5">
              <Flame size={11} strokeWidth={1.7} />
              Login streak
            </div>
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}
            >
              LONGEST · {streak.longest}
            </span>
          </div>
          <div className="flex items-baseline gap-2 mb-3.5">
            <span
              className="display-italic"
              style={{
                fontSize: 40,
                lineHeight: 1,
                fontWeight: 400,
                color: streak.current > 0 ? 'var(--text)' : 'var(--text-4)',
                letterSpacing: '-0.02em',
              }}
            >
              {streak.current}
            </span>
            <span
              className="mono uppercase"
              style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.14em' }}
            >
              {streak.current === 1 ? 'day' : 'days'}
            </span>
          </div>
          <LoginHistoryStrip cells={streak.last30} />
          <div
            style={{
              fontSize: 11.5,
              color: 'var(--text-3)',
              marginTop: 12,
              lineHeight: 1.55,
            }}
          >
            One visit a day keeps the streak alive.
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="eyebrow">Login activity</div>
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}
            >
              {streak.totalDays} {streak.totalDays === 1 ? 'day' : 'days'}
            </span>
          </div>
          <div className="grid gap-2" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 12 }}>
            <ActivityStat
              label="First login"
              value={streak.firstLogin ? prettyDate(streak.firstLogin) : '—'}
              sub={streak.firstLogin ? relativeDate(streak.firstLogin) : ''}
            />
            <ActivityStat
              label="Most recent"
              value={streak.all[0] ? prettyDate(streak.all[0]) : '—'}
              sub={streak.all[0] ? relativeDate(streak.all[0]) : ''}
            />
          </div>
          {streak.all.length > 0 ? (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10 }}>
              <ul
                className="flex flex-col gap-1"
                style={{
                  maxHeight: 260,
                  overflowY: 'auto',
                  listStyle: 'none',
                  padding: 0,
                  margin: 0,
                }}
              >
                {streak.all.map((d) => (
                  <li
                    key={d}
                    className="flex items-center justify-between"
                    style={{ fontSize: 12, color: 'var(--text-2)' }}
                  >
                    <span>{prettyDate(d)}</span>
                    <span
                      className="mono"
                      style={{ fontSize: 10.5, color: 'var(--text-4)' }}
                    >
                      {relativeDate(d)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div
              style={{
                fontSize: 11.5,
                color: 'var(--text-3)',
                borderTop: '1px solid var(--border)',
                paddingTop: 10,
              }}
            >
              We'll record every day you open Rounds — come back tomorrow.
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="card card-hover"
          style={{
            padding: '14px 18px',
            textAlign: 'left',
            border: 0,
            cursor: 'pointer',
            background: 'var(--bg-elev)',
            color: 'var(--plum)',
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          <div className="flex items-center justify-between">
            <span>Sign out</span>
            <ArrowRight size={14} strokeWidth={1.7} />
          </div>
          <div
            style={{ fontSize: 11.5, color: 'var(--text-4)', marginTop: 3, fontWeight: 400 }}
          >
            Clears your local session on this device.
          </div>
        </button>
      </aside>
    </div>
  );
}

function LoginHistoryStrip({
  cells,
}: {
  cells: { date: string; active: boolean }[];
}) {
  const today = cells[cells.length - 1]?.date;
  return (
    <div>
      <div
        className="grid gap-1"
        style={{
          gridTemplateColumns: `repeat(${cells.length}, minmax(0, 1fr))`,
          width: '100%',
        }}
      >
        {cells.map((c) => {
          const isToday = c.date === today;
          return (
            <div
              key={c.date}
              title={`${prettyDate(c.date)} · ${c.active ? 'logged in' : 'no visit'}`}
              aria-label={`${c.date} ${c.active ? 'active' : 'inactive'}`}
              style={{
                height: 20,
                borderRadius: 3,
                background: c.active ? 'var(--accent)' : 'transparent',
                boxShadow: c.active
                  ? isToday
                    ? '0 0 0 2px var(--accent-soft)'
                    : 'none'
                  : 'inset 0 0 0 1px var(--border)',
                opacity: c.active ? 1 : 0.8,
              }}
            />
          );
        })}
      </div>
      <div
        className="flex justify-between mt-2 mono"
        style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
      >
        <span>30 DAYS AGO</span>
        <span>TODAY</span>
      </div>
    </div>
  );
}

function prettyDate(d: string) {
  const date = new Date(`${d}T00:00:00`);
  if (Number.isNaN(date.getTime())) return d;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function relativeDate(d: string): string {
  const date = new Date(`${d}T00:00:00`);
  const todayDate = new Date();
  todayDate.setHours(0, 0, 0, 0);
  const diffDays = Math.round((todayDate.getTime() - date.getTime()) / (24 * 60 * 60 * 1000));
  if (diffDays === 0) return 'today';
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 30) return `${diffDays} days ago`;
  if (diffDays < 365) return `${Math.round(diffDays / 30)} mo ago`;
  return `${Math.round(diffDays / 365)} yr ago`;
}

function ActivityStat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div
      className="card"
      style={{
        padding: '10px 12px',
        background: 'var(--bg-sunken)',
        boxShadow: 'none',
        border: '1px solid var(--border)',
      }}
    >
      <div
        className="eyebrow"
        style={{ fontSize: 9.5, marginBottom: 4 }}
      >
        {label}
      </div>
      <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.2 }}>{value}</div>
      {sub && (
        <div
          className="mono"
          style={{ fontSize: 10, color: 'var(--text-4)', marginTop: 2 }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div
      className="flex justify-between py-2.5 gap-4"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{label}</span>
      <span
        className={mono ? 'mono' : undefined}
        style={{ fontSize: 12, color: 'var(--text)', textAlign: 'right' }}
      >
        {value}
      </span>
    </div>
  );
}

function providerLabel(p: string) {
  if (p === 'google') return 'Google';
  if (p === 'github') return 'GitHub';
  return 'Email';
}

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: 'var(--bg)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 14,
  color: 'var(--text)',
  outline: 'none',
  fontFamily: 'inherit',
};

const primaryBtn: React.CSSProperties = {
  padding: '9px 16px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
};
