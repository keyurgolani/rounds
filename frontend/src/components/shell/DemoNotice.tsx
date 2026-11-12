import { Users } from 'lucide-react';

// The demo account's notice (ROUNDS-00B-L07), above every signed-in page
// while the demo account is signed in. Visitors share that account, so
// what one adds is visible to the others until a sign-out clears it. It
// sits in the page flow, wraps on a phone, and never takes focus.
export default function DemoNotice() {
  return (
    <aside
      aria-label="Demo account"
      data-testid="demo-notice"
      className="flex items-start gap-2.5 px-5 sm:px-8 py-2.5"
      style={{
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-sunken)',
        fontSize: 12.5,
        lineHeight: 1.45,
        color: 'var(--text-2)',
      }}
    >
      <Users
        aria-hidden="true"
        size={15}
        strokeWidth={1.8}
        style={{ flexShrink: 0, marginTop: 1, color: 'var(--ochre)' }}
      />
      <p style={{ margin: 0, minWidth: 0, maxWidth: '75ch' }}>
        <strong style={{ color: 'var(--text)', fontWeight: 600 }}>Shared demo account.</strong>{' '}
        Other visitors can see what you add while it lasts, so don't enter real personal details. Any
        sign-out, the 30-minute idle one included, clears what everyone added.
      </p>
    </aside>
  );
}
