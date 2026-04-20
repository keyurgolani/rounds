import { CSSProperties } from 'react';

interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  className?: string;
  style?: CSSProperties;
  'data-testid'?: string;
}

export function Skeleton({
  width = '100%',
  height = 16,
  className = '',
  style,
  ...rest
}: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-100 rounded ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      data-testid={rest['data-testid']}
    />
  );
}
