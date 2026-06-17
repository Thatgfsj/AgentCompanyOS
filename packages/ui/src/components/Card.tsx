import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/cn.js';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface-1 p-4 shadow-sm',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
