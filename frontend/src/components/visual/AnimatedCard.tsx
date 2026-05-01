import type { CSSProperties, ReactNode } from 'react';
import { motion } from 'framer-motion';

interface AnimatedCardProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  delay?: number;
  hover?: boolean;
  'data-testid'?: string;
}

export function AnimatedCard({
  children,
  className = '',
  style,
  delay = 0,
  hover = true,
  ...rest
}: AnimatedCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      whileHover={hover ? { scale: 1.015, y: -1 } : undefined}
      className={className}
      style={style}
      data-testid={rest['data-testid']}
    >
      {children}
    </motion.div>
  );
}
