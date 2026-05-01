import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ThemeProvider } from './theme/ThemeProvider';
import { AuthProvider } from './auth/AuthProvider';
import './styles/globals.css';

// Demo seed: when URL contains ?_demo=1, pre-populate a sample user so
// screenshot tooling and public showcases can skip the login flow.
(function seedDemo() {
  try {
    const p = new URLSearchParams(window.location.search);
    if (!p.has('_demo')) return;
    if (localStorage.getItem('rounds.auth.v1')) return;
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
      })
    );
  } catch {
    /* noop */
  }
})();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  </React.StrictMode>
);
