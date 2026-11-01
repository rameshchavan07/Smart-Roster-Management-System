import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Calendar, ChevronDown, Check } from 'lucide-react';
import { useMonth } from '../../context/MonthContext';

export const MonthSwitcher: React.FC = () => {
  const {
    currentMonth,
    monthShortLabel,
    monthLabel,
    nextMonth,
    prevMonth,
    setMonth,
    resetToDefault,
    availableMonths,
  } = useMonth();

  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div className="relative inline-flex items-center" ref={containerRef}>
      <div className="inline-flex items-center rounded-ctl border border-border bg-surface shadow-sm">
        {/* Previous Month Chevron */}
        <button
          type="button"
          onClick={prevMonth}
          title="Previous month"
          aria-label="Previous month"
          className="flex h-8 w-7 items-center justify-center rounded-l-ctl text-ink-2 hover:bg-surface-2 hover:text-ink active:bg-surface-2 transition-colors border-r border-border focus:outline-none focus:ring-2 focus:ring-accent-600"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </button>

        {/* Current Month Dropdown Trigger */}
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          title={`Active month: ${monthLabel}. Click to switch.`}
          className="flex h-8 items-center gap-1.5 px-2.5 text-xs font-semibold font-mono text-ink hover:bg-surface-2 active:bg-surface-2 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-600"
        >
          <Calendar className="h-3.5 w-3.5 text-accent-600" />
          <span>{monthShortLabel}</span>
          <ChevronDown
            className={`h-3 w-3 text-ink-3 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {/* Next Month Chevron */}
        <button
          type="button"
          onClick={nextMonth}
          title="Next month"
          aria-label="Next month"
          className="flex h-8 w-7 items-center justify-center rounded-r-ctl text-ink-2 hover:bg-surface-2 hover:text-ink active:bg-surface-2 transition-colors border-l border-border focus:outline-none focus:ring-2 focus:ring-accent-600"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Month Selection Popover */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Select planning month"
          className="absolute left-0 top-full z-50 mt-1.5 w-56 rounded-pop border border-border bg-surface p-1.5 shadow-layer"
        >
          <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-3 border-b border-border mb-1">
            Planning Horizon
          </div>

          <div className="max-h-56 overflow-y-auto space-y-0.5">
            {availableMonths.map((m) => {
              const isSelected = m.value === currentMonth;
              return (
                <button
                  key={m.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    setMonth(m.value);
                    setIsOpen(false);
                  }}
                  className={`flex w-full items-center justify-between rounded-ctl px-2.5 py-1.5 text-xs font-mono transition-colors ${
                    isSelected
                      ? 'bg-accent-50 font-semibold text-accent-700'
                      : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
                  }`}
                >
                  <span>{m.label}</span>
                  {isSelected && <Check className="h-3.5 w-3.5 text-accent-600" />}
                </button>
              );
            })}
          </div>

          {currentMonth !== '2026-12' && (
            <div className="mt-1 pt-1 border-t border-border">
              <button
                type="button"
                onClick={() => {
                  resetToDefault();
                  setIsOpen(false);
                }}
                className="w-full text-left rounded-ctl px-2.5 py-1 text-[11px] text-accent-600 hover:bg-accent-50 font-medium transition-colors"
              >
                Reset to Target (Dec 2026)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
