import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import type { ReactNode } from 'react';

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const location = useLocation();

  if (!ready) {
    // Brief hold while Supabase restores the session from storage. Avoids
    // a login-flash on refresh of a protected route.
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: '100dvh', background: 'var(--bg)', color: 'var(--text-4)', fontSize: 13 }}
      >
        …
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <>{children}</>;
}
