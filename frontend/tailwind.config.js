/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Instrument Serif', 'Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        paper: {
          DEFAULT: 'var(--paper)',
          2: 'var(--paper-2)',
          3: 'var(--paper-3)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          2: 'var(--ink-2)',
          3: 'var(--ink-3)',
          4: 'var(--ink-4)',
          5: 'var(--ink-5)',
        },
        bg: {
          DEFAULT: 'var(--bg)',
          elev: 'var(--bg-elev)',
          sunken: 'var(--bg-sunken)',
        },
        text: {
          DEFAULT: 'var(--text)',
          2: 'var(--text-2)',
          3: 'var(--text-3)',
          4: 'var(--text-4)',
        },
        border: {
          DEFAULT: 'var(--border)',
          strong: 'var(--border-strong)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          soft: 'var(--accent-soft)',
          // Back-compat aliases for legacy Vercel/Geist accent classes
          blue: '#C9633F',
          red: '#7C3A4E',
          green: '#2F5D4A',
          orange: '#B68C2A',
          pink: '#7C3A4E',
          purple: '#C9633F',
          develop: '#C9633F',
        },
        terracotta: {
          DEFAULT: '#C9633F',
          soft: '#E8C9B8',
        },
        forest: {
          DEFAULT: '#2F5D4A',
          soft: '#C2D4C8',
        },
        ochre: {
          DEFAULT: '#B68C2A',
          soft: '#E8D9A8',
        },
        plum: {
          DEFAULT: '#7C3A4E',
          soft: '#E0C7CE',
        },
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
        lg: 'var(--radius-lg)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        'card-hover': 'var(--shadow-card-hover)',
        elev: 'var(--shadow-elev)',
      },
      letterSpacing: {
        eyebrow: '0.14em',
        display: '-0.02em',
        heading: '-0.01em',
      },
    },
  },
  plugins: [],
};
