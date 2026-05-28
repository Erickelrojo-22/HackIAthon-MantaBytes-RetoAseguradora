import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

type BadgeVariant = 'default' | 'Verde' | 'Amarillo' | 'Rojo' | 'info' | 'success' | 'danger';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants: Record<BadgeVariant, string> = {
    default: 'bg-navy-100 text-navy-800 border-navy-200',
    Verde: 'bg-green-100 text-green-800 border-green-200',
    Amarillo: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    Rojo: 'bg-red-100 text-red-800 border-red-200',
    info: 'bg-cyan-100 text-cyan-800 border-cyan-200',
    success: 'bg-green-100 text-green-800 border-green-200',
    danger: 'bg-red-100 text-red-800 border-red-200',
  };

  return (
    <span
      className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold', variants[variant], className)}
      {...props}
    />
  );
}
