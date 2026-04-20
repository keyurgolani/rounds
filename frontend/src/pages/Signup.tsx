import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import {
  AuthShell,
  Divider,
  Field,
  OAuthButton,
  primaryBtnStyle,
} from './Login';
import { oauthConfig } from '../auth/oauthConfig';

export default function Signup() {
  const { signup, oauthSignIn } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signup(name, email, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account');
    } finally {
      setBusy(false);
    }
  }

  async function handleOauth(provider: 'google' | 'github') {
    setError(null);
    setBusy(true);
    try {
      await oauthSignIn(provider);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in');
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Start your rounds"
      title="Create your account."
      subtitle="Write anecdotes, track practice progress, and keep every application in one place. Takes under a minute."
    >
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
          <Divider>or sign up with email</Divider>
        </>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-5">
        <Field
          label="Full name"
          value={name}
          onChange={setName}
          autoComplete="name"
          required
        />
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
          autoComplete="new-password"
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
        <button type="submit" disabled={busy} className="mt-2" style={primaryBtnStyle(busy)}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <div
        className="mono text-center mt-6"
        style={{ fontSize: 11.5, color: 'var(--text-3)', letterSpacing: '0.04em' }}
      >
        Already have an account?{' '}
        <Link
          to="/login"
          className="inline-flex items-center gap-1 align-baseline"
          style={{ color: 'var(--accent)', fontWeight: 500, textDecoration: 'none' }}
        >
          Sign in <ArrowRight size={12} strokeWidth={1.8} />
        </Link>
      </div>
    </AuthShell>
  );
}
