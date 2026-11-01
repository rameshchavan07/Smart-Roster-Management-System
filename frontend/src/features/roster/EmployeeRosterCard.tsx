import React, { useMemo } from 'react';
import { Badge, StatusCell } from '../../components/ui';
import type {
  RosterGridRow,
  RosterGridCell,
} from '../../types/roster';
import { mapStatusToCode } from '../../types/roster';

export interface EmployeeRosterCardProps {
  row: RosterGridRow;
  dates: string[]; // YYYY-MM-DD
  monthLabel: string;
  onCellClick?: (cell: RosterGridCell, row: RosterGridRow, date: string) => void;
  className?: string;
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const EmployeeRosterCard: React.FC<EmployeeRosterCardProps> = ({
  row,
  dates,
  monthLabel,
  onCellClick,
  className = '',
}) => {
  // Calendar weeks structure (0=Mon, 6=Sun)
  const { calendarWeeks, stats } = useMemo(() => {
    if (dates.length === 0) {
      return { calendarWeeks: [], stats: { workDays: 0, offDays: 0, leaves: 0, compOffs: 0 } };
    }

    const firstDateStr = dates[0];
    const firstDate = new Date(firstDateStr + 'T00:00:00');
    // Align so 0 is Monday: Sunday is 6, Mon is 0
    let startDayOfWeek = firstDate.getDay() - 1;
    if (startDayOfWeek === -1) startDayOfWeek = 6;

    let workDays = 0;
    let offDays = 0;
    let leaves = 0;
    let compOffs = 0;

    const daysList: Array<{
      dateStr: string | null;
      dayNum: number | null;
      cell: RosterGridCell | null;
    }> = [];

    // Padding before day 1
    for (let i = 0; i < startDayOfWeek; i++) {
      daysList.push({ dateStr: null, dayNum: null, cell: null });
    }

    // Days in month
    for (const dStr of dates) {
      const d = new Date(dStr + 'T00:00:00');
      const cell = row.cells[dStr] || {
        date: dStr,
        status: 'WORK',
        source: 'SOLVER',
        is_locked: false,
      };

      if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') workDays++;
      else if (cell.status === 'WEEKLY_OFF' || cell.status === 'PUBLIC_HOLIDAY') offDays++;
      else if (cell.status === 'LEAVE') leaves++;
      else if (cell.status === 'COMP_OFF') compOffs++;

      daysList.push({
        dateStr: dStr,
        dayNum: d.getDate(),
        cell,
      });
    }

    // Pad end of last week to complete 7 days
    while (daysList.length % 7 !== 0) {
      daysList.push({ dateStr: null, dayNum: null, cell: null });
    }

    // Chunk into weeks
    const weeks: Array<typeof daysList> = [];
    for (let i = 0; i < daysList.length; i += 7) {
      weeks.push(daysList.slice(i, i + 7));
    }

    return {
      calendarWeeks: weeks,
      stats: { workDays, offDays, leaves, compOffs },
    };
  }, [dates, row]);

  return (
    <div className={`space-y-4 p-5 bg-surface-1 border border-border rounded-lg ${className}`}>
      {/* Employee Overview Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent-50 border border-accent-100 flex items-center justify-center text-accent-700 font-semibold text-sm">
            {row.employee_name.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-text-primary">
                {row.employee_name}
              </h2>
              <span className="font-mono text-xs text-text-muted">
                {row.employee_code}
              </span>
              {row.pod_name && (
                <Badge variant="neutral" className="text-xs font-mono">
                  {row.pod_name}
                </Badge>
              )}
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Assignments: {row.primary_assignments.join(', ') || 'General Ops'} · {monthLabel}
            </p>
          </div>
        </div>

        {/* Stats Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="px-3 py-1.5 rounded-md bg-surface-2 border border-border text-center">
            <span className="text-[10px] uppercase text-text-muted font-medium block">
              Days Worked
            </span>
            <span className="text-sm font-mono font-semibold text-text-primary">
              {stats.workDays}
            </span>
          </div>

          <div className="px-3 py-1.5 rounded-md bg-surface-2 border border-border text-center">
            <span className="text-[10px] uppercase text-text-muted font-medium block">
              Weekly Offs
            </span>
            <span className="text-sm font-mono font-semibold text-[#4B3F72]">
              {stats.offDays}
            </span>
          </div>

          <div className="px-3 py-1.5 rounded-md bg-surface-2 border border-border text-center">
            <span className="text-[10px] uppercase text-text-muted font-medium block">
              Leaves Taken
            </span>
            <span className="text-sm font-mono font-semibold text-[#8A2F25]">
              {stats.leaves}
            </span>
          </div>

          <div className="px-3 py-1.5 rounded-md bg-surface-2 border border-border text-center">
            <span className="text-[10px] uppercase text-text-muted font-medium block">
              Comp-Offs
            </span>
            <span className="text-sm font-mono font-semibold text-[#1F4E79]">
              {stats.compOffs}
            </span>
          </div>
        </div>
      </div>

      {/* Monthly Calendar View */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Monthly Shift Calendar
          </span>
          <span className="text-[11px] text-text-muted">
            Click any shift cell to edit status
          </span>
        </div>

        <div className="border border-border rounded-md overflow-hidden bg-surface-1">
          {/* Weekday Headers */}
          <div className="grid grid-cols-7 bg-surface-2 border-b border-border text-center py-2 text-xs font-semibold text-text-secondary">
            {WEEKDAYS.map((w, idx) => (
              <span key={w} className={idx >= 5 ? 'text-[#8A867C]' : ''}>
                {w}
              </span>
            ))}
          </div>

          {/* Weeks Grid */}
          <div className="divide-y divide-border">
            {calendarWeeks.map((week, wIdx) => (
              <div key={wIdx} className="grid grid-cols-7 divide-x divide-border">
                {week.map((day, dIdx) => {
                  if (!day.dateStr || !day.cell) {
                    return (
                      <div
                        key={dIdx}
                        className="h-16 p-1.5 bg-surface-2/30"
                      />
                    );
                  }

                  const statusCode = mapStatusToCode(day.cell.status);
                  const isWeekend = dIdx >= 5;

                  return (
                    <div
                      key={dIdx}
                      onClick={() => onCellClick?.(day.cell!, row, day.dateStr!)}
                      className={`h-16 p-1.5 flex flex-col justify-between cursor-pointer hover:bg-surface-2/80 transition-colors ${
                        isWeekend ? 'bg-surface-2/20' : 'bg-surface-1'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-mono font-medium text-text-muted">
                          {day.dayNum}
                        </span>
                        {day.cell.note && (
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-accent-600"
                            title={day.cell.note}
                          />
                        )}
                      </div>

                      <div className="flex justify-center pb-0.5">
                        <StatusCell
                          status={statusCode}
                          size="sm"
                          isManual={day.cell.source === 'MANUAL'}
                          isLocked={day.cell.is_locked}
                          disabled
                          className="pointer-events-none scale-95"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
