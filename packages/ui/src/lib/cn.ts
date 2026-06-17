import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind class names with conflict resolution.
 *
 * `clsx` for conditional joining, `tailwind-merge` for resolving
 * conflicting utility classes (e.g. `p-2` and `p-4` → `p-4`).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
