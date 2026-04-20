import { useEffect, useState } from 'react';
import { useMotionValue, useTransform, animate } from 'framer-motion';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}

const defaultFormat = (n: number) =>
  Math.round(n).toLocaleString('en-US');

export function AnimatedCounter({
  value,
  duration = 1.2,
  format = defaultFormat,
  className = '',
}: AnimatedCounterProps) {
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (latest) => format(latest));
  const [display, setDisplay] = useState(format(0));

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration,
      ease: 'easeOut',
    });
    const unsub = rounded.on('change', (v) => setDisplay(v));
    return () => {
      controls.stop();
      unsub();
    };
  }, [value, duration, motionValue, rounded]);

  return (
    <span className={className} data-testid="counter">
      {display}
    </span>
  );
}
