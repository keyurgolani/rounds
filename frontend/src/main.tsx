import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ThemeProvider } from './theme/ThemeProvider';
import { AuthProvider } from './auth/AuthProvider';
import './styles/globals.css';

// Demo seed: when URL contains ?_demo=1, pre-populate a sample user so
// screenshot tooling and public showcases can skip the login flow.
// Dev builds only — production builds tree-shake this branch entirely
// so the URL backdoor isn't reachable on shipped artifacts.
if (import.meta.env.DEV) {
  try {
    const p = new URLSearchParams(window.location.search);
    if (p.has('_demo') && !localStorage.getItem('rounds.auth.v1')) {
      localStorage.setItem(
        'rounds.auth.v1',
        JSON.stringify({
          id: 'demo-user',
          name: 'Anika Shah',
          email: 'anika@rounds.dev',
          provider: 'google',
          target: 'Stripe L5 · Backend',
          bio: 'Prepping staff-level interviews — distributed systems and leadership stories.',
          createdAt: new Date().toISOString(),
        }),
      );
    }
  } catch {
    /* noop */
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  </React.StrictMode>
);
