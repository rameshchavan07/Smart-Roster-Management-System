import React from 'react';
import { Lock } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type RosterStatusCode = 'W' | 'WO' | 'PH' | 'HW' | 'L' | 'CO';

export interface StatusCellProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  status: RosterStatusCode;
  isManual?: boolean;
  isLocked?: boolean;
  isSelected?: boolean;
  size?: 'sm' | 'md';
}

const statusConfig: Record<
  RosterStatusCode,
  { label: string; bg: string; text: string; border: string }
> = {
  W: {
    label: 'Working',
    bg: 'bg-white',
    text: 'text-[#1C1B19]',
    border: 'border-border',
  },
  WO: {
    label: 'Weekly off',
    bg: 'bg-[#E9E4F4]',
    text: 'text-[#4B3F72]',
    border: 'border-[#D5CBE8]',
  },
  PH: {
    label: 'Public holiday off',
    bg: 'bg-[#F8E7C6]',
    text: 'text-[#7A5200]',
    border: 'border-[#EDD4A0]',
  },
  HW: {
    label: 'Holiday worked',
    bg: 'bg-[#DCEEEC]',
    text: 'text-[#0B4F4A]',
    border: 'border-[#B8DED9]',
  },
  L: {
    label: 'Leave',
    bg: 'bg-[#F6D9D5]',
    text: 'text-[#8A2F25]',
    border: 'border-[#E8B5AD]',
  },
  CO: {
    label: 'Comp-off',
    bg: 'bg-[#D9E7F5]',
    text: 'text-[#1F4E79]',
    border: 'border-[#B4D0EC]',
  },
};

export const StatusCell = React.forwardRef<HTMLButtonElement, StatusCellProps>(
  (
    {
      status,
      isManual = false,
      isLocked = false,
      isSelected = false,
      size = 'md',
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    const config = statusConfig[status] || statusConfig.W;

    const dimensions =
      size === 'sm'
        ? 'w-[32px] h-[24px] text-[11px]'
        : 'w-[36px] h-[28px] text-[12px]';

    return (
      <button
        ref={ref}
        type="button"
        disabled={disabled}
        aria-label={`${config.label} (${status})${isLocked ? ', locked' : ''}${isManual ? ', manual edit' : ''}`}
        title={`${config.label} (${status})${isLocked ? ' • Locked' : ''}${isManual ? ' • Manual edit' : ''}`}
        className={twMerge(
          clsx(
            'relative inline-flex items-center justify-center font-mono font-medium select-none transition-colors border',
            dimensions,
            config.bg,
            config.text,
            config.border,
            isSelected && 'ring-2 ring-accent-600 ring-offset-1 z-10',
            disabled ? 'opacity-45 cursor-not-allowed' : 'hover:brightness-95 cursor-pointer',
            className
          )
        )}
        {...props}
      >
        {/* Working dot indicator (from Design System spec) */}
        {status === 'W' && (
          <span
            aria-hidden="true"
            className="absolute top-1 left-1 w-1.5 h-1.5 rounded-full bg-[#2F6F4F]"
          />
        )}

        {/* Manual edit corner marker */}
        {isManual && (
          <span
            aria-hidden="true"
            title="Manual override"
            className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-accent-600"
          />
        )}

        {/* Lock glyph */}
        {isLocked ? (
          <Lock className="w-3 h-3 stroke-[2] opacity-80" aria-hidden="true" />
        ) : (
          <span>{status}</span>
        )}
      </button>
    );
  }
);

StatusCell.displayName = 'StatusCell';
