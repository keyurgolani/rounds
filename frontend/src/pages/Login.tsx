import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { RoundsLockup } from '../components/Logo';
import { oauthConfig } from '../auth/oauthConfig';

export default function Login() {
  const { login, oauthSignIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in');
    } finally {
      setBusy(false);
    }
  }

  async function handleOauth(provider: 'google' | 'github') {
    setError(null);
    setBusy(true);
    try {
      await oauthSignIn(provider);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in');
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <AuthFormHeader eyebrow="Welcome back" heading="Sign in" />

      {oauthConfig.anyEnabled && (
        <>
          <div className="flex gap-2 mb-5">
            {oauthConfig.google && (
              <OAuthButton
                provider="google"
                onClick={() => handleOauth('google')}
                disabled={busy}
              />
            )}
            {oauthConfig.github && (
              <OAuthButton
                provider="github"
                onClick={() => handleOauth('github')}
                disabled={busy}
              />
            )}
          </div>
          <Divider>or continue with email</Divider>
        </>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-5">
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          required
        />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
        />
        {error && (
          <div
            className="mono"
            style={{ fontSize: 11.5, color: 'var(--plum)', letterSpacing: '0.02em' }}
          >
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={busy}
          className="mt-2"
          style={primaryBtnStyle(busy)}
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <div
        className="mono text-center mt-6"
        style={{ fontSize: 11.5, color: 'var(--text-3)', letterSpacing: '0.04em' }}
      >
        New here?{' '}
        <Link
          to="/signup"
          className="inline-flex items-center gap-1 align-baseline"
          style={{ color: 'var(--accent)', fontWeight: 500, textDecoration: 'none' }}
        >
          Create an account <ArrowRight size={12} strokeWidth={1.8} />
        </Link>
      </div>
    </AuthShell>
  );
}

const MARKETING_FEATURES = [
  {
    title: 'System design, visually',
    body: 'Mermaid architecture, sequence, and ER diagrams with zoomable charts and animated tradeoff sliders.',
  },
  {
    title: 'Coding with a real runner',
    body: 'Monaco editor, persistent drafts, sandboxed execution against public and hidden tests.',
  },
  {
    title: 'Anecdotes that stay reusable',
    body: 'Write STAR stories once, link them to the behavioral questions they answer.',
  },
  {
    title: 'Pipeline, not spreadsheets',
    body: 'Track every application, round, interviewer, and result in the same surface as your prep.',
  },
];

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex" style={{ background: 'var(--bg)' }}>
      <aside
        className="hidden lg:flex flex-col justify-between p-12"
        style={{
          flexBasis: '46%',
          background: 'var(--bg-sunken)',
          borderRight: '1px solid var(--border)',
        }}
      >
        <RoundsLockup markSize={28} textSize={28} />

        <div style={{ maxWidth: 460 }}>
          <div className="eyebrow mb-3">A calmer way to prep</div>
          <p
            className="display-italic"
            style={{ fontSize: 40, lineHeight: 1.12, margin: 0, fontWeight: 400 }}
          >
            Small, consistent reps beat long cram sessions.
          </p>
          <p
            style={{
              marginTop: 18,
              fontSize: 13.5,
              color: 'var(--text-3)',
              lineHeight: 1.6,
              maxWidth: 420,
            }}
          >
            Rounds is an editorial home for the entire interview cycle — one practice surface for
            System Design, Coding, and Behavioral, plus a tracker for the companies you're pursuing
            and the rounds you're prepping for.
          </p>

          <ul
            className="flex flex-col gap-4"
            style={{ marginTop: 32, listStyle: 'none', padding: 0 }}
          >
            {MARKETING_FEATURES.map((f) => (
              <li key={f.title} className="flex gap-3">
                <span
                  aria-hidden
                  style={{
                    flex: '0 0 auto',
                    marginTop: 7,
                    width: 6,
                    height: 6,
                    borderRadius: 999,
                    background: 'var(--accent)',
                  }}
                />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>
                    {f.title}
                  </div>
                  <div
                    style={{
                      fontSize: 12.5,
                      color: 'var(--text-3)',
                      lineHeight: 1.55,
                      marginTop: 2,
                    }}
                  >
                    {f.body}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div
          className="mono"
          style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.14em' }}
        >
          SYSTEM DESIGN · CODING · BEHAVIORAL
        </div>
      </aside>

      <main className="flex-1 flex items-center justify-center p-6">
        <div style={{ width: '100%', maxWidth: 400 }}>
          <div className="lg:hidden mb-6 flex justify-center">
            <RoundsLockup markSize={24} textSize={24} />
          </div>
          <div className="eyebrow mb-2">Rounds · interview prep</div>
          <h1
            className="display-italic"
            style={{
              fontSize: 38,
              lineHeight: 1.08,
              margin: 0,
              fontWeight: 400,
              letterSpacing: '-0.02em',
            }}
          >
            Your interview command center.
          </h1>
          <p
            style={{
              margin: '12px 0 28px',
              fontSize: 13.5,
              color: 'var(--text-3)',
              lineHeight: 1.6,
              maxWidth: 380,
            }}
          >
            One calm workspace for System Design, Coding, and Behavioral practice — plus the
            pipeline of companies and rounds you're running.
          </p>
          {children}
        </div>
      </main>
    </div>
  );
}

export function AuthFormHeader({
  eyebrow,
  heading,
}: {
  eyebrow: string;
  heading: string;
}) {
  return (
    <div className="mb-5">
      <div className="eyebrow mb-1">{eyebrow}</div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 500,
          color: 'var(--text)',
          letterSpacing: '-0.01em',
        }}
      >
        {heading}
      </div>
    </div>
  );
}

export function Field({
  label,
  type = 'text',
  value,
  onChange,
  autoComplete,
  required,
  placeholder,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="eyebrow">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required={required}
        placeholder={placeholder}
        style={{
          padding: '11px 12px',
          background: 'var(--bg-elev)',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          borderRadius: 'var(--radius)',
          border: 0,
          fontSize: 14,
          color: 'var(--text)',
          outline: 'none',
        }}
      />
    </label>
  );
}

export function Divider({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      <span
        className="mono uppercase"
        style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.14em' }}
      >
        {children}
      </span>
      <span style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
  );
}

export function OAuthButton({
  provider,
  onClick,
  disabled,
}: {
  provider: 'google' | 'github';
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="card card-hover flex items-center justify-center gap-2.5 flex-1"
      style={{
        padding: '10px 14px',
        border: 0,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        fontSize: 13,
        fontWeight: 500,
        color: 'var(--text)',
      }}
    >
      {provider === 'google' ? <GoogleIcon /> : <GitHubIcon />}
      <span>{provider === 'google' ? 'Google' : 'GitHub'}</span>
    </button>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.25h2.92c1.7-1.57 2.68-3.88 2.68-6.61z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.19l-2.92-2.25c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.32A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.82.96 4.04l3.01-2.32z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.96L3.97 7.28C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        fill="var(--text)"
        d="M8 0a8 8 0 0 0-2.53 15.59c.4.08.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.93-.89-1.17-.89-1.17-.72-.5.06-.48.06-.48.8.06 1.22.82 1.22.82.71 1.22 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.64-.89-3.64-3.96 0-.87.31-1.59.82-2.15-.08-.2-.35-1.02.08-2.12 0 0 .67-.22 2.2.82a7.5 7.5 0 0 1 4 0c1.52-1.04 2.2-.82 2.2-.82.43 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.08-1.87 3.76-3.65 3.96.29.25.54.73.54 1.47v2.18c0 .21.14.47.55.38A8 8 0 0 0 8 0z"
      />
    </svg>
  );
}

export function primaryBtnStyle(busy?: boolean): React.CSSProperties {
  return {
    padding: '11px 14px',
    borderRadius: 'var(--radius)',
    border: 0,
    background: 'var(--accent)',
    color: 'var(--bg-elev)',
    fontSize: 13,
    fontWeight: 600,
    cursor: busy ? 'wait' : 'pointer',
    opacity: busy ? 0.7 : 1,
    letterSpacing: '0.01em',
  };
}
