import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type SeverityType = 'BLOCKING' | 'WARNING' | 'INFO' | 'SUCCESS';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: SeverityType | 'neutral';
  size?: 'sm' | 'default';
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'neutral',
  size = 'default',
  icon,
  children,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center gap-1 font-medium select-none tracking-tight rounded-chip border';

  const variantStyles = {
    BLOCKING: 'bg-bad/10 text-bad border-bad/20',
    WARNING: 'bg-warn/10 text-warn border-warn/25',
    INFO: 'bg-info/10 text-info border-info/20',
    SUCCESS: 'bg-ok/10 text-ok border-ok/20',
    neutral: 'bg-surface-2 text-ink-2 border-border',
  };

  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-[10px] leading-tight',
    default: 'px-2 py-0.5 text-xs leading-none',
  };

  return (
    <span
      className={twMerge(clsx(baseStyles, variantStyles[variant], sizeStyles[size], className))}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
};
