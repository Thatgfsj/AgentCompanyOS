import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/cn.js';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

/**
 * Button component — primary UI primitive.
 *
 * Visual per `docs/UI_GUIDELINES.md` §6.1 (shadcn/ui base).
 */
export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center rounded-md font-medium transition-colors ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-chief ' +
    'disabled:pointer-events-none disabled:opacity-50';
  const variants: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'bg-chief text-white hover:bg-chief/90',
    secondary: 'bg-surface-2 text-primary hover:bg-surface-3',
    ghost: 'bg-transparent text-primary hover:bg-surface-2',
    danger: 'bg-status-failed text-white hover:bg-status-failed/90',
  };
  const sizes: Record<NonNullable<ButtonProps['size']>, string> = {
    sm: 'h-8 px-3 text-sm',
    md: 'h-10 px-4 text-sm',
    lg: 'h-12 px-6 text-base',
  };
  return (
    <button
      type="button"
      className={cn(base, variants[variant], sizes[size], className)}
      {...rest}
    >
      {children}
    </button>
  );
}
