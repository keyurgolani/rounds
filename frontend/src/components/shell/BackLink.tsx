import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

type Props = {
  to: string;
  label?: string;
  className?: string;
};

export default function BackLink({ to, label = 'Back', className }: Props) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center gap-1.5 ${className ?? ''}`}
      style={{
        fontSize: 12.5,
        color: 'var(--text-3)',
        textDecoration: 'none',
        width: 'fit-content',
        transition: 'color 140ms',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = 'var(--text)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = 'var(--text-3)';
      }}
    >
      <ArrowLeft size={14} strokeWidth={1.6} aria-hidden="true" />
      <span>{label}</span>
    </Link>
  );
}
