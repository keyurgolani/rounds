import {
  interviewTypeAccent,
  interviewTypeLabel,
  interviewTypeShort,
} from './interviewTypes';

type Props = {
  /** The raw value stored in interview_rounds.round_type. */
  type: string;
  /** Show the short label instead of the full one (tight rows). */
  short?: boolean;
};

/**
 * A small color-coded pill that surfaces an interview round's type
 * at a glance. AI-flavored types share an indigo accent so they
 * cluster visually; legacy types each get their own hue.
 */
export default function InterviewTypePill({ type, short }: Props) {
  const { bg, fg, border } = interviewTypeAccent(type);
  const label = short ? interviewTypeShort(type) : interviewTypeLabel(type);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        fontSize: 11,
        fontWeight: 600,
        lineHeight: 1.5,
        background: bg,
        color: fg,
        border: `1px solid ${border}`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}
