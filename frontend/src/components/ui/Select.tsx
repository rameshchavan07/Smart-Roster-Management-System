import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  label?: string;
  error?: string;
  placeholder?: string;
  value?: string;
  options: SelectOption[];
  onChange?: (value: string) => void;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'default';
}

export const Select: React.FC<SelectProps> = ({
  label,
  error,
  placeholder = 'Select an option...',
  value,
  options,
  onChange,
  disabled = false,
  className,
  size = 'default',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  const close = useCallback(() => {
    setIsOpen(false);
    setFocusedIndex(-1);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        close();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return;

      if (event.key === 'Escape') {
        close();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        setFocusedIndex((prev) => (prev < options.length - 1 ? prev + 1 : 0));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setFocusedIndex((prev) => (prev > 0 ? prev - 1 : options.length - 1));
      } else if (event.key === 'Enter' && focusedIndex >= 0) {
        event.preventDefault();
        const option = options[focusedIndex];
        if (option && !option.disabled) {
          onChange?.(option.value);
          close();
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, options, focusedIndex, onChange, close]);

  const sizeStyles = {
    sm: 'h-7 px-2.5 text-xs',
    default: 'h-8 px-3 text-xs',
  };

  return (
    <div className={twMerge('w-full space-y-1', className)} ref={containerRef}>
      {label && <label className="block text-xs font-medium text-ink-2">{label}</label>}

      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => !disabled && setIsOpen(!isOpen)}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          className={twMerge(
            clsx(
              'flex w-full items-center justify-between rounded-ctl border bg-surface text-ink transition-colors select-none text-left',
              'focus-visible:outline-none focus-visible:border-accent-600 focus-visible:ring-1 focus-visible:ring-accent-600',
              disabled
                ? 'cursor-not-allowed bg-surface-2 opacity-50'
                : 'hover:border-ink-3 cursor-pointer',
              error ? 'border-bad' : 'border-border-strong',
              sizeStyles[size]
            )
          )}
        >
          <span className={clsx('truncate', !selectedOption && 'text-ink-3')}>
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <ChevronDown
            className={clsx(
              'h-3.5 w-3.5 text-ink-3 transition-transform shrink-0 ml-1.5',
              isOpen && 'rotate-180'
            )}
          />
        </button>

        {isOpen && (
          <ul
            ref={listRef}
            role="listbox"
            className="absolute left-0 top-full z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-pop border border-border bg-surface p-1 shadow-layer"
          >
            {options.map((option, idx) => {
              const isSelected = option.value === value;
              const isFocused = idx === focusedIndex;

              return (
                <li
                  key={option.value}
                  role="option"
                  aria-selected={isSelected}
                  aria-disabled={option.disabled}
                  onClick={() => {
                    if (!option.disabled) {
                      onChange?.(option.value);
                      close();
                    }
                  }}
                  onMouseEnter={() => setFocusedIndex(idx)}
                  className={twMerge(
                    clsx(
                      'flex items-center justify-between rounded-ctl px-2.5 py-1.5 text-xs transition-colors cursor-pointer select-none',
                      option.disabled && 'cursor-not-allowed opacity-40',
                      isSelected && 'bg-accent-50 font-semibold text-accent-700',
                      isFocused && !isSelected && 'bg-surface-2 text-ink',
                      !isSelected && !isFocused && 'text-ink-2 hover:bg-surface-2'
                    )
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && <Check className="h-3.5 w-3.5 text-accent-600 shrink-0 ml-2" />}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {error && <p className="text-[11px] text-bad mt-0.5">{error}</p>}
    </div>
  );
};
