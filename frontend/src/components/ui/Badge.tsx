import React from 'react';
import { cn } from './Card';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'Verde' | 'Amarillo' | 'Rojo';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: "bg-navy-100 text-navy-800 border-navy-200",
    Verde: "bg-green-100 text-green-800 border-green-200",
    Amarillo: "bg-yellow-100 text-yellow-800 border-yellow-200",
    Rojo: "bg-red-100 text-red-800 border-red-200"
  };

  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border", variants[variant], className)} {...props} />
  );
}
