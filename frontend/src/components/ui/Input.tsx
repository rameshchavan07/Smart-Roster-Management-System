import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-ink-2">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={twMerge(
            clsx(
              'flex h-8 w-full rounded-ctl border bg-surface px-3 py-1 text-xs text-ink placeholder:text-ink-3 transition-colors',
              'focus-visible:outline-none focus-visible:border-accent-600 focus-visible:ring-1 focus-visible:ring-accent-600',
              'disabled:cursor-not-allowed disabled:bg-surface-2 disabled:opacity-50',
              error ? 'border-bad focus-visible:border-bad focus-visible:ring-bad' : 'border-border-strong',
              className
            )
          )}
          {...props}
        />
        {error && <p className="text-[11px] text-bad mt-0.5">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
