import React from 'react';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'default' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'secondary',
      size = 'default',
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-600 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-45 select-none';

    const variantStyles = {
      primary: 'bg-accent-600 text-surface hover:bg-accent-700 active:bg-accent-700 shadow-sm',
      secondary:
        'border border-border-strong bg-surface text-ink hover:bg-surface-2 hover:border-ink-3',
      ghost: 'text-ink-2 hover:bg-surface-2 hover:text-ink',
      destructive:
        'border border-bad/30 bg-surface text-bad hover:bg-bad/10 focus-visible:ring-bad',
    };

    const sizeStyles = {
      sm: 'h-7 rounded-ctl px-2.5 text-xs',
      default: 'h-8 rounded-ctl px-3.5 text-xs',
      lg: 'h-10 rounded-ctl px-4 text-sm',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={twMerge(clsx(baseStyles, variantStyles[variant], sizeStyles[size], className))}
        {...props}
      >
        {isLoading && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
