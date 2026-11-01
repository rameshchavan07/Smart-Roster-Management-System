import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { HelpCircle, AlertTriangle } from 'lucide-react';
import { StatusCell, Badge, Modal, Button } from '../../components/ui';
import { CoverageStrip } from './CoverageStrip';
import type {
  RosterGridRow,
  RosterGridCell,
  RosterEntryStatus,
  RosterCoverageCell,
} from '../../types/roster';
import { mapStatusToCode } from '../../types/roster';

export interface RosterGridProps {
  rows: RosterGridRow[];
  dates: string[]; // Ordered list of YYYY-MM-DD
  holidays?: Set<string>; // Set of YYYY-MM-DD holiday dates
  coverageCells?: RosterCoverageCell[];
  selectedCell?: { employeeId: string; date: string } | null;
  onCellClick?: (cell: RosterGridCell, row: RosterGridRow, date: string) => void;
  onCoverageCellClick?: (cell: RosterCoverageCell) => void;
  onDayHeaderClick?: (date: string) => void;
  onCellStatusChange?: (
    employeeId: string,
    date: string,
    newStatus: RosterEntryStatus
  ) => void;
  readOnly?: boolean;
  isLoading?: boolean;
  emptyMessage?: string;
  className?: string;
}

interface FocusedCoordinate {
  rowIndex: number;
  colIndex: number; // 0 to dates.length - 1
}

const WEEKDAY_INITIALS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export const RosterGrid: React.FC<RosterGridProps> = ({
  rows,
  dates,
  holidays = new Set(),
  coverageCells,
  selectedCell,
  onCellClick,
  onCoverageCellClick,
  onDayHeaderClick,
  onCellStatusChange,
  readOnly = false,
  isLoading = false,
  emptyMessage = 'No roster data available for this selection.',
  className = '',
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const activeCellRef = useRef<HTMLButtonElement | null>(null);

  // Active keyboard roving focus coordinate
  const [focusedCoord, setFocusedCoord] = useState<FocusedCoordinate | null>(null);
  const [showShortcutsModal, setShowShortcutsModal] = useState<boolean>(false);
  const [isCoverageExpanded, setIsCoverageExpanded] = useState<boolean>(false);

  // Compute coverage strip dimensions
  const distinctBpCount = useMemo(() => {
    if (!coverageCells || coverageCells.length === 0) return 0;
    return new Set(coverageCells.map((c) => c.brand_process_id)).size;
  }, [coverageCells]);

  const coverageHeight = useMemo(() => {
    if (!coverageCells || coverageCells.length === 0) return 0;
    return 26 + (isCoverageExpanded ? distinctBpCount * 24 : 0);
  }, [coverageCells, isCoverageExpanded, distinctBpCount]);

  const totalHeaderOffset = 38 + coverageHeight;

  // TanStack Virtualizer for performant vertical scrolling across large rosters
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 28, // 28px row height from DESIGN_SYSTEM.md
    overscan: 12,
  });

  // Calculate precomputed metadata for dates (day of week, isWeekend, isHoliday)
  const datesMetadata = useMemo(() => {
    return dates.map((dateStr) => {
      const d = new Date(dateStr + 'T00:00:00');
      const dayOfWeek = d.getDay(); // 0 = Sun, 6 = Sat
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
      const isHoliday = holidays.has(dateStr);
      return {
        dateStr,
        dayNumber: d.getDate(),
        weekdayInitial: WEEKDAY_INITIALS[dayOfWeek],
        isWeekend,
        isHoliday,
      };
    });
  }, [dates, holidays]);

  // Keep DOM focus on active cell when focusedCoord changes
  useEffect(() => {
    if (focusedCoord && activeCellRef.current) {
      activeCellRef.current.focus({ preventScroll: false });
    }
  }, [focusedCoord]);

  // Move focused coordinate and auto-scroll virtualized row into view
  const setFocusAndScroll = useCallback(
    (newCoord: FocusedCoordinate) => {
      // Clamp coordinates
      const clampedRow = Math.max(0, Math.min(rows.length - 1, newCoord.rowIndex));
      const clampedCol = Math.max(0, Math.min(dates.length - 1, newCoord.colIndex));

      // Scroll row into view if out of visible range
      rowVirtualizer.scrollToIndex(clampedRow, { align: 'auto' });
      setFocusedCoord({ rowIndex: clampedRow, colIndex: clampedCol });
    },
    [rows.length, dates.length, rowVirtualizer]
  );

  // Keyboard navigation handler adhering to WAI-ARIA grid design pattern
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Help shortcut: '?'
      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setShowShortcutsModal(true);
        return;
      }

      if (!focusedCoord) {
        // If grid has focus but no cell selected, initialize focus on (0, 0)
        if (['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
          e.preventDefault();
          setFocusAndScroll({ rowIndex: 0, colIndex: 0 });
        }
        return;
      }

      const { rowIndex, colIndex } = focusedCoord;

      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          setFocusAndScroll({ rowIndex: rowIndex - 1, colIndex });
          break;

        case 'ArrowDown':
          e.preventDefault();
          setFocusAndScroll({ rowIndex: rowIndex + 1, colIndex });
          break;

        case 'ArrowLeft':
          e.preventDefault();
          setFocusAndScroll({ rowIndex, colIndex: colIndex - 1 });
          break;

        case 'ArrowRight':
          e.preventDefault();
          setFocusAndScroll({ rowIndex, colIndex: colIndex + 1 });
          break;

        case 'Home':
          e.preventDefault();
          if (e.ctrlKey || e.metaKey) {
            setFocusAndScroll({ rowIndex: 0, colIndex: 0 });
          } else {
            setFocusAndScroll({ rowIndex, colIndex: 0 });
          }
          break;

        case 'End':
          e.preventDefault();
          if (e.ctrlKey || e.metaKey) {
            setFocusAndScroll({
              rowIndex: rows.length - 1,
              colIndex: dates.length - 1,
            });
          } else {
            setFocusAndScroll({ rowIndex, colIndex: dates.length - 1 });
          }
          break;

        case 'PageUp':
          e.preventDefault();
          setFocusAndScroll({ rowIndex: rowIndex - 10, colIndex });
          break;

        case 'PageDown':
          e.preventDefault();
          setFocusAndScroll({ rowIndex: rowIndex + 10, colIndex });
          break;

        case 'Enter':
        case ' ': {
          e.preventDefault();
          const targetRow = rows[rowIndex];
          const targetDate = dates[colIndex];
          if (targetRow && targetDate) {
            const cell = targetRow.cells[targetDate];
            if (cell) {
              onCellClick?.(cell, targetRow, targetDate);
            }
          }
          break;
        }

        case 'Escape':
          e.preventDefault();
          setFocusedCoord(null);
          break;

        // Quick-set status keys (W, O, L, C, P, H)
        case 'w':
        case 'W':
        case 'o':
        case 'O':
        case 'l':
        case 'L':
        case 'c':
        case 'C':
        case 'p':
        case 'P':
        case 'h':
        case 'H': {
          if (readOnly) return;
          const targetRow = rows[rowIndex];
          const targetDate = dates[colIndex];
          if (!targetRow || !targetDate) return;
          const cell = targetRow.cells[targetDate];
          if (!cell || cell.is_locked) return;

          let newStatus: RosterEntryStatus | null = null;
          const lower = e.key.toLowerCase();
          if (lower === 'w') newStatus = 'WORK';
          else if (lower === 'o') newStatus = 'WEEKLY_OFF';
          else if (lower === 'l') newStatus = 'LEAVE';
          else if (lower === 'c') newStatus = 'COMP_OFF';
          else if (lower === 'p') newStatus = 'PUBLIC_HOLIDAY';
          else if (lower === 'h') newStatus = 'HOLIDAY_WORK';

          if (newStatus && newStatus !== cell.status) {
            e.preventDefault();
            onCellStatusChange?.(targetRow.employee_id, targetDate, newStatus);
          }
          break;
        }

        default:
          break;
      }
    },
    [
      focusedCoord,
      rows,
      dates,
      readOnly,
      setFocusAndScroll,
      onCellClick,
      onCellStatusChange,
    ]
  );

  // Compute workload (working days) for each row
  const rowLoads = useMemo(() => {
    const loads = new Map<string, number>();
    for (const r of rows) {
      let count = 0;
      for (const cell of Object.values(r.cells)) {
        if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') {
          count++;
        }
      }
      loads.set(r.employee_id, count);
    }
    return loads;
  }, [rows]);

  if (isLoading) {
    return (
      <div className="w-full h-96 flex flex-col items-center justify-center bg-surface-1 border border-border rounded-md animate-pulse p-8">
        <div className="h-6 w-48 bg-surface-3 rounded mb-4" />
        <div className="h-4 w-72 bg-surface-2 rounded mb-2" />
        <div className="h-4 w-60 bg-surface-2 rounded" />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="w-full py-16 flex flex-col items-center justify-center bg-surface-1 border border-border rounded-md text-center p-6">
        <div className="w-12 h-12 rounded-full bg-surface-2 flex items-center justify-center text-text-muted mb-3">
          <AlertTriangle className="w-6 h-6 stroke-[1.5]" />
        </div>
        <h4 className="text-sm font-semibold text-text-primary mb-1">No Roster Entries</h4>
        <p className="text-xs text-text-muted max-w-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col border border-border rounded-md bg-surface-1 ${className}`}>
      {/* Grid Toolbar & Shortcut Help Prompt */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-2 border-b border-border text-xs text-text-muted">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] font-semibold text-text-secondary">
            {rows.length} {rows.length === 1 ? 'employee' : 'employees'} · {dates.length} days
          </span>
          <span className="hidden sm:inline-block text-[11px] text-text-muted">
            Use <kbd className="px-1 py-0.5 bg-surface-1 border border-border rounded text-[10px]">↑</kbd> <kbd className="px-1 py-0.5 bg-surface-1 border border-border rounded text-[10px]">↓</kbd> <kbd className="px-1 py-0.5 bg-surface-1 border border-border rounded text-[10px]">←</kbd> <kbd className="px-1 py-0.5 bg-surface-1 border border-border rounded text-[10px]">→</kbd> to navigate · Press <kbd className="px-1 py-0.5 bg-surface-1 border border-border rounded text-[10px]">?</kbd> for shortcuts
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowShortcutsModal(true)}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-text-secondary hover:text-text-primary px-1.5 py-0.5 rounded hover:bg-surface-3 transition-colors"
          title="View keyboard navigation shortcuts (?)"
        >
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Shortcuts</span>
        </button>
      </div>

      {/* Virtualized Matrix Container */}
      <div
        ref={parentRef}
        role="grid"
        aria-label="Roster Matrix"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        className="w-full overflow-auto max-h-[calc(100vh-230px)] select-none focus:outline-none focus:ring-1 focus:ring-accent-600"
      >
        <div
          className="relative min-w-max"
          style={{
            height: `${rowVirtualizer.getTotalSize() + totalHeaderOffset}px`,
          }}
        >
          {/* Sticky Header Row */}
          <div
            role="row"
            className="sticky top-0 z-40 flex items-center h-[38px] bg-surface-2 border-b border-border-strong text-xs font-semibold text-text-primary"
          >
            {/* Sticky Column 1: Employee */}
            <div
              role="columnheader"
              className="sticky left-0 z-50 flex items-center px-2.5 w-[160px] h-full bg-surface-2 border-r border-border text-[11px] font-semibold text-text-secondary uppercase tracking-wider"
            >
              Employee
            </div>

            {/* Sticky Column 2: Pod */}
            <div
              role="columnheader"
              className="sticky left-[160px] z-50 flex items-center justify-center w-[64px] h-full bg-surface-2 border-r border-border text-[11px] font-semibold text-text-secondary uppercase tracking-wider"
            >
              Pod
            </div>

            {/* Sticky Column 3: Load (Days worked) */}
            <div
              role="columnheader"
              className="sticky left-[224px] z-50 flex items-center justify-center w-[54px] h-full bg-surface-2 border-r-2 border-border-strong text-[11px] font-semibold text-text-secondary uppercase tracking-wider"
              title="Days worked this month"
            >
              Load
            </div>

            {/* Day Column Headers */}
            {datesMetadata.map((d) => (
              <div
                key={d.dateStr}
                role="columnheader"
                aria-label={`${d.dateStr} (${d.weekdayInitial})`}
                onClick={() => onDayHeaderClick?.(d.dateStr)}
                title={`Click to view daily staffing on ${d.dateStr}`}
                className={`flex flex-col items-center justify-center w-[36px] h-full border-r border-border flex-shrink-0 transition-colors cursor-pointer hover:brightness-95 select-none ${
                  d.isHoliday
                    ? 'bg-[#F8E7C6] text-[#7A5200]'
                    : d.isWeekend
                    ? 'bg-[#F0EEEB] text-[#5C5852]'
                    : 'bg-surface-2 text-text-primary'
                }`}
              >
                <span className="text-[10px] font-semibold leading-tight">
                  {d.weekdayInitial}
                </span>
                <span className="text-[11px] font-mono font-medium leading-tight">
                  {d.dayNumber}
                </span>
              </div>
            ))}
          </div>

          {/* Sticky Demand Coverage Strip */}
          {coverageCells && coverageCells.length > 0 && (
            <div
              className="sticky top-[38px] z-30"
              style={{ width: '100%' }}
            >
              <CoverageStrip
                coverageCells={coverageCells}
                dates={dates}
                stickyLeftWidth={278}
                isExpanded={isCoverageExpanded}
                onToggleExpand={setIsCoverageExpanded}
                onCellClick={onCoverageCellClick}
              />
            </div>
          )}

          {/* Virtualized Employee Rows */}
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            if (!row) return null;

            const rowIndex = virtualRow.index;
            const load = rowLoads.get(row.employee_id) ?? 0;

            return (
              <div
                key={row.employee_id}
                role="row"
                aria-rowindex={rowIndex + 1}
                className="absolute left-0 flex items-center h-[28px] border-b border-border hover:bg-surface-2/60 transition-colors group"
                style={{
                  top: `${virtualRow.start + totalHeaderOffset}px`,
                  width: '100%',
                }}
              >
                {/* Sticky Left Column 1: Employee Name */}
                <div
                  role="rowheader"
                  className="sticky left-0 z-20 flex items-center px-2.5 w-[160px] h-[28px] bg-surface-1 group-hover:bg-surface-2/90 border-r border-border overflow-hidden whitespace-nowrap transition-colors"
                >
                  <span
                    className="text-xs font-medium text-text-primary truncate"
                    title={`${row.employee_name} (${row.employee_code})`}
                  >
                    {row.employee_name}
                  </span>
                  <span className="text-[10px] font-mono text-text-muted ml-1 flex-shrink-0">
                    {row.employee_code}
                  </span>
                </div>

                {/* Sticky Left Column 2: Pod */}
                <div
                  role="gridcell"
                  className="sticky left-[160px] z-20 flex items-center justify-center w-[64px] h-[28px] bg-surface-1 group-hover:bg-surface-2/90 border-r border-border transition-colors"
                >
                  {row.pod_name ? (
                    <Badge variant="neutral" size="sm" className="font-mono text-[10px] px-1 py-0 h-4">
                      {row.pod_name}
                    </Badge>
                  ) : (
                    <span className="text-text-muted text-xs">-</span>
                  )}
                </div>

                {/* Sticky Left Column 3: Load (Days worked) */}
                <div
                  role="gridcell"
                  className="sticky left-[224px] z-20 flex items-center justify-center w-[54px] h-[28px] bg-surface-1 group-hover:bg-surface-2/90 border-r-2 border-border-strong font-mono text-xs font-semibold text-text-primary transition-colors"
                >
                  {load}
                </div>

                {/* Schedule Day Cells */}
                {dates.map((dateStr, colIndex) => {
                  const cell = row.cells[dateStr] || {
                    date: dateStr,
                    status: 'WORK',
                    source: 'SOLVER',
                    is_locked: false,
                    conflicts: [],
                  };

                  const isFocused =
                    focusedCoord?.rowIndex === rowIndex &&
                    focusedCoord?.colIndex === colIndex;

                  const isSelected =
                    selectedCell?.employeeId === row.employee_id &&
                    selectedCell?.date === dateStr;

                  const statusCode = mapStatusToCode(cell.status);
                  const hasConflict = Boolean(cell.conflicts && cell.conflicts.length > 0);

                  return (
                    <div
                      key={dateStr}
                      role="gridcell"
                      aria-colindex={colIndex + 4}
                      className="relative w-[36px] h-[28px] border-r border-border flex-shrink-0 flex items-center justify-center"
                    >
                      <StatusCell
                        ref={isFocused ? activeCellRef : undefined}
                        status={statusCode}
                        isManual={cell.source === 'MANUAL'}
                        isLocked={cell.is_locked}
                        isSelected={isSelected || isFocused}
                        tabIndex={isFocused ? 0 : -1}
                        onClick={() => {
                          setFocusedCoord({ rowIndex, colIndex });
                          onCellClick?.(cell, row, dateStr);
                        }}
                        className={`w-[36px] h-[28px] ${
                          hasConflict ? 'ring-1 ring-inset ring-[#C2412D]' : ''
                        }`}
                      />

                      {/* Conflict Indicator Badge on Cell */}
                      {hasConflict && (
                        <span
                          aria-label="Has conflict"
                          title={`Conflict: ${cell.conflicts?.join(', ')}`}
                          className="absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-[#C2412D] pointer-events-none"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      {/* Keyboard Shortcuts Dialog */}
      <Modal
        isOpen={showShortcutsModal}
        onClose={() => setShowShortcutsModal(false)}
        title="Roster Grid Keyboard Shortcuts"
      >
        <div className="space-y-4 text-xs text-text-primary">
          <p className="text-text-muted">
            The roster grid supports full high-density keyboard navigation and quick cell status toggling.
          </p>

          <div className="border border-border rounded divide-y divide-border font-mono">
            <div className="flex items-center justify-between p-2 bg-surface-2 font-semibold text-[11px] text-text-secondary">
              <span>Shortcut</span>
              <span>Action</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">↑ ↓ ← →</span>
              <span className="text-text-muted font-sans">Move active cell cursor</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">Enter / Space</span>
              <span className="text-text-muted font-sans">Inspect / edit cell details</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">Home / End</span>
              <span className="text-text-muted font-sans">Jump to first / last day of month</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">PageUp / PageDown</span>
              <span className="text-text-muted font-sans">Jump 10 rows up / down</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">W</span>
              <span className="text-text-muted font-sans">Quick-set status to Working (W)</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">O</span>
              <span className="text-text-muted font-sans">Quick-set status to Weekly Off (WO)</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">L</span>
              <span className="text-text-muted font-sans">Quick-set status to Leave (L)</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">C</span>
              <span className="text-text-muted font-sans">Quick-set status to Comp-Off (CO)</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">Esc</span>
              <span className="text-text-muted font-sans">Cancel selection or unfocus</span>
            </div>
            <div className="flex items-center justify-between p-2">
              <span className="font-semibold text-text-primary">?</span>
              <span className="text-text-muted font-sans">Open this shortcut cheat sheet</span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowShortcutsModal(false)}
            >
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
