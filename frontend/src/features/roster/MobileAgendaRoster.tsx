import React, { useState, useMemo } from 'react';
import {
  Lock,
  AlertTriangle,
  User,
  Users,
  Edit2,
} from 'lucide-react';
import { Select } from '../../components/ui';
import type {
  RosterGridRow,
  RosterGridCell,
  RosterEntryStatus,
  RosterStatusCode,
} from '../../types/roster';

export interface MobileAgendaRosterProps {
  monthDates: string[];
  rows: RosterGridRow[];
  holidaysSet: Set<string>;
  canEdit: boolean;
  onCellClick: (row: RosterGridRow, date: string, cell: RosterGridCell, e: React.MouseEvent) => void;
  onOpenDayView?: (date: string) => void;
}

const STATUS_CONFIG: Record<
  RosterEntryStatus,
  { code: RosterStatusCode; label: string; bg: string; text: string; border: string }
> = {
  WORK: {
    code: 'W',
    label: 'Working Shift',
    bg: 'bg-white',
    text: 'text-[#1C1B19]',
    border: 'border-border',
  },
  WEEKLY_OFF: {
    code: 'WO',
    label: 'Weekly Off',
    bg: 'bg-[#E9E4F4]',
    text: 'text-[#4B3F72]',
    border: 'border-[#D5CBE8]',
  },
  PUBLIC_HOLIDAY: {
    code: 'PH',
    label: 'Public Holiday',
    bg: 'bg-[#F8E7C6]',
    text: 'text-[#7A5200]',
    border: 'border-[#EAD2A1]',
  },
  HOLIDAY_WORK: {
    code: 'HW',
    label: 'Holiday Work (+1 Comp-off)',
    bg: 'bg-[#CBE3F7]',
    text: 'text-[#194B72]',
    border: 'border-[#A3C8EA]',
  },
  LEAVE: {
    code: 'L',
    label: 'Approved Leave',
    bg: 'bg-[#F6D9D5]',
    text: 'text-[#8A2F25]',
    border: 'border-[#E8B5AE]',
  },
  COMP_OFF: {
    code: 'CO',
    label: 'Comp-Off Leave',
    bg: 'bg-[#EFE8DC]',
    text: 'text-[#5C4A32]',
    border: 'border-[#D9CCA4]',
  },
};

export const MobileAgendaRoster: React.FC<MobileAgendaRosterProps> = ({
  monthDates,
  rows,
  holidaysSet,
  canEdit,
  onCellClick,
  onOpenDayView,
}) => {
  // Selected employee ID
  const [selectedEmpId, setSelectedEmpId] = useState<string>(() => rows[0]?.employee_id || '');

  // Selected week index (0 = Days 1-7, 1 = Days 8-14, 2 = Days 15-21, 3 = Days 22-28, 4 = Days 29-31)
  const [selectedWeekIndex, setSelectedWeekIndex] = useState<number>(0);

  // Filtered employees list
  const filteredRows = rows;

  // Current active employee row
  const activeRow = useMemo(() => {
    const match = rows.find((r) => r.employee_id === selectedEmpId);
    return match || rows[0] || null;
  }, [rows, selectedEmpId]);

  // Split month dates into 5 logical weeks
  const weeks = useMemo(() => {
    const w1 = monthDates.slice(0, 7);
    const w2 = monthDates.slice(7, 14);
    const w3 = monthDates.slice(14, 21);
    const w4 = monthDates.slice(21, 28);
    const w5 = monthDates.slice(28);

    return [
      { label: 'Week 1', sub: '1st - 7th', dates: w1 },
      { label: 'Week 2', sub: '8th - 14th', dates: w2 },
      { label: 'Week 3', sub: '15th - 21st', dates: w3 },
      { label: 'Week 4', sub: '22nd - 28th', dates: w4 },
      { label: 'Week 5', sub: '29th - End', dates: w5 },
    ].filter((w) => w.dates.length > 0);
  }, [monthDates]);

  const activeWeekDates = weeks[selectedWeekIndex]?.dates || [];

  // Weekly stats for the active employee
  const weekStats = useMemo(() => {
    if (!activeRow) return { work: 0, off: 0, leave: 0 };
    let work = 0;
    let off = 0;
    let leave = 0;

    for (const d of activeWeekDates) {
      const cell = activeRow.cells[d];
      if (!cell) continue;
      if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') work++;
      else if (cell.status === 'WEEKLY_OFF' || cell.status === 'PUBLIC_HOLIDAY') off++;
      else if (cell.status === 'LEAVE' || cell.status === 'COMP_OFF') leave++;
    }

    return { work, off, leave };
  }, [activeRow, activeWeekDates]);

  return (
    <div className="space-y-4">
      {/* 1. Employee Selector Strip */}
      <div className="bg-surface p-3 rounded-ctl border border-border shadow-xs space-y-2.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-ink flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-accent-700" />
            Selected Staff Member
          </label>
          <span className="font-mono text-[10px] text-ink-3">
            {rows.length} team members
          </span>
        </div>

        <div className="flex gap-2">
          <div className="flex-1">
            <Select
              value={activeRow?.employee_id || ''}
              onChange={(val) => setSelectedEmpId(val)}
              options={filteredRows.map((r) => ({
                value: r.employee_id,
                label: `${r.employee_name} (${r.employee_code}) · ${r.pod_name || 'No Pod'}`,
              }))}
              className="text-xs h-9 w-full"
            />
          </div>
        </div>

        {/* Selected Employee Card */}
        {activeRow && (
          <div className="flex items-center justify-between p-2 rounded-ctl bg-surface-2 border border-border text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-accent-100 text-accent-800 font-semibold text-xs flex items-center justify-center shrink-0">
                {activeRow.employee_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .slice(0, 2)}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-ink truncate leading-tight">
                  {activeRow.employee_name}
                </p>
                <p className="text-[10px] text-ink-3 font-mono">
                  {activeRow.employee_code} · {activeRow.pod_name || 'Dedicated'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-border text-ink">
                Week: {weekStats.work}W · {weekStats.off}WO
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Horizontal Week Strip Selector */}
      <div className="bg-surface p-2 rounded-ctl border border-border shadow-xs">
        <div className="grid grid-cols-5 gap-1">
          {weeks.map((w, idx) => {
            const isSelected = selectedWeekIndex === idx;
            return (
              <button
                key={w.label}
                type="button"
                onClick={() => setSelectedWeekIndex(idx)}
                className={`py-2 px-1 rounded-ctl text-center transition-all min-h-[44px] flex flex-col items-center justify-center ${
                  isSelected
                    ? 'bg-accent-600 text-surface font-semibold shadow-xs ring-1 ring-accent-600'
                    : 'bg-surface-2 text-ink hover:bg-surface-3'
                }`}
              >
                <span className="text-xs font-semibold leading-tight block">{w.label}</span>
                <span
                  className={`text-[9px] font-mono mt-0.5 block ${
                    isSelected ? 'text-surface/80' : 'text-ink-3'
                  }`}
                >
                  {w.sub}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Vertical Day-by-Day Agenda List */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
            {weeks[selectedWeekIndex]?.label} Agenda ({activeWeekDates.length} Days)
          </h3>
          <span className="text-[10px] text-ink-3">
            Tap card to edit shift
          </span>
        </div>

        {activeWeekDates.map((dateStr) => {
          const d = new Date(dateStr + 'T00:00:00');
          const dayName = d.toLocaleDateString(undefined, { weekday: 'short' });
          const dayNum = d.getDate();
          const isWeekend = d.getDay() === 0 || d.getDay() === 6;
          const isHoliday = holidaysSet.has(dateStr);

          const cell: RosterGridCell =
            activeRow?.cells[dateStr] || {
              date: dateStr,
              status: isWeekend ? 'WEEKLY_OFF' : 'WORK',
              source: 'SOLVER',
              is_locked: false,
            };

          const statusCfg = STATUS_CONFIG[cell.status] || STATUS_CONFIG.WORK;
          const hasConflicts = cell.conflicts && cell.conflicts.length > 0;

          return (
            <div
              key={dateStr}
              onClick={(e) => {
                if (activeRow && canEdit) {
                  onCellClick(activeRow, dateStr, cell, e);
                }
              }}
              className={`p-3 bg-surface rounded-ctl border transition-all ${
                hasConflicts
                  ? 'border-bad/40 bg-bad/5'
                  : isWeekend
                  ? 'border-border/80 bg-surface-2/40'
                  : 'border-border hover:border-accent-400'
              } shadow-xs min-h-[56px] cursor-pointer active:scale-[0.99] group`}
            >
              <div className="flex items-center justify-between gap-3">
                {/* Date Left Box */}
                <div className="flex items-center gap-2.5 shrink-0">
                  <div
                    className={`w-11 h-11 rounded-ctl flex flex-col items-center justify-center font-mono border ${
                      isHoliday
                        ? 'bg-[#F8E7C6] border-[#EAD2A1] text-[#7A5200]'
                        : isWeekend
                        ? 'bg-surface-2 border-border text-ink-2'
                        : 'bg-accent-50 border-accent-200 text-accent-900'
                    }`}
                  >
                    <span className="text-[10px] uppercase font-semibold leading-none">
                      {dayName}
                    </span>
                    <span className="text-sm font-bold leading-none mt-1">{dayNum}</span>
                  </div>

                  {/* Shift status & role */}
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded font-mono font-bold text-xs ${statusCfg.bg} ${statusCfg.text} border ${statusCfg.border}`}
                      >
                        {statusCfg.code}
                      </span>
                      <span className="text-xs font-semibold text-ink">
                        {statusCfg.label}
                      </span>
                      {cell.is_locked && (
                        <span
                          title="Locked"
                          className="inline-flex items-center text-accent-700 bg-accent-100 p-0.5 rounded"
                        >
                          <Lock className="w-3 h-3" />
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-ink-3">
                      {cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK'
                        ? activeRow?.primary_assignments?.join(', ') || 'General Operations (9h)'
                        : cell.status === 'WEEKLY_OFF'
                        ? 'Scheduled Rest Day'
                        : cell.status === 'PUBLIC_HOLIDAY'
                        ? 'Public Holiday'
                        : 'Approved Leave'}
                    </p>
                  </div>
                </div>

                {/* Right Actions */}
                <div className="flex items-center gap-1 shrink-0">
                  {onOpenDayView && (
                    <button
                      type="button"
                      title="Inspect day staffing"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenDayView(dateStr);
                      }}
                      className="h-9 w-9 flex items-center justify-center rounded-ctl text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors"
                      aria-label="Inspect day staffing"
                    >
                      <Users className="w-4 h-4 text-accent-700" />
                    </button>
                  )}

                  {canEdit && (
                    <div className="h-9 w-9 flex items-center justify-center rounded-ctl text-ink-3 group-hover:text-accent-700 group-hover:bg-accent-50 transition-colors">
                      <Edit2 className="w-3.5 h-3.5" />
                    </div>
                  )}
                </div>
              </div>

              {/* Conflict warning banner if any */}
              {hasConflicts && (
                <div className="mt-2 pt-2 border-t border-bad/20 flex items-center gap-1.5 text-[11px] text-bad">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span className="font-medium truncate">
                    Integrity Conflict: {cell.conflicts?.join(', ')}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
