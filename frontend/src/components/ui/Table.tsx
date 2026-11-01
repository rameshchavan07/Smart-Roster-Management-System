import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  dense?: boolean;
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className, dense = false, ...props }, ref) => (
    <div className="relative w-full overflow-auto rounded-ctl border border-border bg-surface">
      <table
        ref={ref}
        data-dense={dense}
        className={twMerge(clsx('w-full caption-bottom text-xs text-ink border-collapse', className))}
        {...props}
      />
    </div>
  )
);
Table.displayName = 'Table';

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={twMerge(
      clsx('bg-surface-2 border-b border-border text-ink-2 font-semibold select-none', className)
    )}
    {...props}
  />
));
TableHeader.displayName = 'TableHeader';

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={twMerge(clsx('[&_tr:last-child]:border-0', className))}
    {...props}
  />
));
TableBody.displayName = 'TableBody';

export const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={twMerge(clsx('border-t border-border bg-surface-2 font-medium text-ink', className))}
    {...props}
  />
));
TableFooter.displayName = 'TableFooter';

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  isSelected?: boolean;
}

export const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, isSelected = false, ...props }, ref) => (
    <tr
      ref={ref}
      data-state={isSelected ? 'selected' : undefined}
      className={twMerge(
        clsx(
          'border-b border-border transition-colors hover:bg-surface-2/60',
          isSelected && 'bg-accent-50 hover:bg-accent-50/80',
          className
        )
      )}
      {...props}
    />
  )
);
TableRow.displayName = 'TableRow';

export const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={twMerge(
      clsx(
        'h-9 px-3 text-left align-middle font-semibold text-ink-2 text-xs select-none tracking-normal',
        '[table[data-dense=true]_&]:h-7 [table[data-dense=true]_&]:px-2.5',
        className
      )
    )}
    {...props}
  />
));
TableHead.displayName = 'TableHead';

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={twMerge(
      clsx(
        'p-3 align-middle text-xs text-ink leading-normal',
        '[table[data-dense=true]_&]:py-1.5 [table[data-dense=true]_&]:px-2.5',
        className
      )
    )}
    {...props}
  />
));
TableCell.displayName = 'TableCell';

export const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={twMerge(clsx('mt-4 text-xs text-ink-3', className))}
    {...props}
  />
));
TableCaption.displayName = 'TableCaption';

