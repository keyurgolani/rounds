import type { GuideTrack } from '../guideTypes';
import { presetsForTrack, useInterviewLength } from './useInterviewLength';

/** Pill-row picker for the active interview round length. Mounted in
 *  StudyShell so every guide page exposes it. Updates are persisted to
 *  localStorage per track and broadcast to any `Duration` instances on
 *  the page via the shared `useInterviewLength` hook. */
export default function InterviewLengthPicker({ track }: { track: GuideTrack }) {
  const presets = presetsForTrack(track);
  const [active, setActive] = useInterviewLength(track);

  return (
    <div
      className="flex"
      style={{
        gap: 6,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
      aria-label="Interview round length"
    >
      <span
        className="mono uppercase"
        style={{
          fontSize: 10.5,
          letterSpacing: '0.12em',
          color: 'var(--text-4)',
          marginRight: 4,
        }}
      >
        Round length
      </span>
      <div role="radiogroup" aria-label="Interview round length" className="flex" style={{ gap: 4 }}>
        {presets.map((preset) => {
          const isActive = preset.id === active.id;
          return (
            <button
              key={preset.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              onClick={() => setActive(preset.id)}
              className="pill"
              style={{
                border: 0,
                cursor: 'pointer',
                background: isActive ? 'var(--accent-soft)' : 'var(--bg-elev)',
                color: isActive ? 'var(--accent)' : 'var(--text-2)',
                boxShadow: `inset 0 0 0 1px ${isActive ? 'var(--accent)' : 'var(--border)'}`,
                fontSize: 11.5,
                fontWeight: isActive ? 600 : 400,
                padding: '4px 10px',
              }}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
