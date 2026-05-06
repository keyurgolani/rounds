// Template gallery. Splits cleanly from Design so this surface can
// scale as more templates land — Design is for typography / colors /
// spacing knobs that apply to *whichever* template is active.
//
// Each card renders the template's metadata only; live preview lives
// in the right pane and updates as soon as a card is clicked.

import type { TemplateConfig } from '../../types';
import { TEMPLATES } from '../../templates/registry';

type Props = {
  templateId: string;
  setTemplateId: (id: string) => void;
  // accepted but currently unused — reserved for per-template defaults
  // when more templates ship with their own design presets.
  design?: TemplateConfig;
};

export default function TemplatesTab({ templateId, setTemplateId }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.5 }}>
        Pick a template; everything else — colors, fonts, margins — lives under{' '}
        <strong>Design</strong>.
      </p>
      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        {TEMPLATES.map((t) => {
          const active = t.id === templateId;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTemplateId(t.id)}
              className="card"
              style={{
                padding: 14,
                textAlign: 'left',
                cursor: 'pointer',
                background: active ? 'var(--accent)' : 'var(--bg-elev)',
                color: active ? 'var(--bg-elev)' : 'var(--text)',
                border: 0,
                boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div className="flex items-center justify-between">
                <span style={{ fontSize: 13, fontWeight: 600 }}>{t.label}</span>
                {active && (
                  <span
                    className="mono"
                    style={{
                      fontSize: 9,
                      letterSpacing: '0.12em',
                      padding: '1px 7px',
                      borderRadius: 999,
                      background: 'var(--bg-elev)',
                      color: 'var(--accent)',
                    }}
                  >
                    SELECTED
                  </span>
                )}
              </div>
              <span style={{ fontSize: 11.5, opacity: 0.85, lineHeight: 1.45 }}>
                {t.blurb}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
