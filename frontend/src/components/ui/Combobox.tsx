import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { ChevronDown, Check, Search, X } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ComboboxOption {
  value: string;
  label: string;
  subtitle?: string;
  disabled?: boolean;
}

export interface ComboboxProps {
  label?: string;
  error?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  value?: string;
  options: ComboboxOption[];
  onChange?: (value: string) => void;
  disabled?: boolean;
  className?: string;
  allowClear?: boolean;
}

export const Combobox: React.FC<ComboboxProps> = ({
  label,
  error,
  placeholder = 'Select or search...',
  searchPlaceholder = 'Type to search...',
  value,
  options,
  onChange,
  disabled = false,
  className,
  allowClear = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  const filteredOptions = useMemo(() => {
    if (!query.trim()) return options;
    const lower = query.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(lower) ||
        (opt.subtitle && opt.subtitle.toLowerCase().includes(lower))
    );
  }, [options, query]);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery('');
    setFocusedIndex(-1);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isOpen]);

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
        setFocusedIndex((prev) => (prev < filteredOptions.length - 1 ? prev + 1 : 0));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setFocusedIndex((prev) => (prev > 0 ? prev - 1 : filteredOptions.length - 1));
      } else if (event.key === 'Enter' && focusedIndex >= 0) {
        event.preventDefault();
        const option = filteredOptions[focusedIndex];
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
  }, [isOpen, filteredOptions, focusedIndex, onChange, close]);

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
              'flex h-8 w-full items-center justify-between rounded-ctl border bg-surface px-3 py-1 text-xs text-ink transition-colors select-none text-left',
              'focus-visible:outline-none focus-visible:border-accent-600 focus-visible:ring-1 focus-visible:ring-accent-600',
              disabled
                ? 'cursor-not-allowed bg-surface-2 opacity-50'
                : 'hover:border-ink-3 cursor-pointer',
              error ? 'border-bad' : 'border-border-strong'
            )
          )}
        >
          <span className={clsx('truncate', !selectedOption && 'text-ink-3')}>
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <div className="flex items-center gap-1 shrink-0 ml-1.5">
            {allowClear && selectedOption && (
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation();
                  onChange?.('');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.stopPropagation();
                    onChange?.('');
                  }
                }}
                className="text-ink-3 hover:text-ink p-0.5"
                title="Clear selection"
              >
                <X className="h-3 w-3" />
              </span>
            )}
            <ChevronDown
              className={clsx('h-3.5 w-3.5 text-ink-3 transition-transform', isOpen && 'rotate-180')}
            />
          </div>
        </button>

        {isOpen && (
          <div className="absolute left-0 top-full z-50 mt-1 max-h-64 w-full overflow-hidden rounded-pop border border-border bg-surface p-1.5 shadow-layer">
            {/* Search Input */}
            <div className="flex items-center gap-2 border-b border-border px-2 py-1.5 mb-1">
              <Search className="h-3.5 w-3.5 text-ink-3 shrink-0" />
              <input
                ref={searchInputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setFocusedIndex(0);
                }}
                placeholder={searchPlaceholder}
                className="flex-1 bg-transparent text-xs text-ink placeholder-ink-3 outline-none"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="text-ink-3 hover:text-ink"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>

            {/* Options list */}
            <ul role="listbox" className="max-h-48 overflow-y-auto space-y-0.5">
              {filteredOptions.length === 0 ? (
                <li className="py-4 text-center text-xs text-ink-3">No matching options</li>
              ) : (
                filteredOptions.map((option, idx) => {
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
                      <div className="truncate">
                        <p className="truncate font-medium">{option.label}</p>
                        {option.subtitle && (
                          <p className="text-[10px] text-ink-3 truncate">{option.subtitle}</p>
                        )}
                      </div>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 text-accent-600 shrink-0 ml-2" />
                      )}
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        )}
      </div>

      {error && <p className="text-[11px] text-bad mt-0.5">{error}</p>}
    </div>
  );
};
