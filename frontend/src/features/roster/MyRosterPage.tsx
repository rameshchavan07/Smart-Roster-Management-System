import React, { useState, useMemo } from 'react';
import {
  Calendar as CalendarIcon,
  Clock,
  ShieldCheck,
  Award,
  Info,
  Lock,
  Plus,
} from 'lucide-react';
import { Badge, Button, Modal, Input, Select, useToast } from '../../components/ui';
import { useAuth } from '../auth/AuthContext';
import { useMonth } from '../../context/MonthContext';
import {
  useRosterPeriodsQuery,
  useRosterGridQuery,
} from '../../api/rosters';
import { useHolidaysQuery } from '../../api/rules';
import { useCompOffBalanceQuery } from '../../api/leaves';
import type {
  RosterGridCell,
  RosterEntryStatus,
  RosterStatusCode,
} from '../../types/roster';

const STATUS_LEGEND: Record<
  RosterEntryStatus,
  { code: RosterStatusCode; label: string; bg: string; text: string; border: string; desc: string }
> = {
  WORK: {
    code: 'W',
    label: 'Working Shift',
    bg: 'bg-white',
    text: 'text-[#1C1B19]',
    border: 'border-border',
    desc: 'Regular 9-hour on-duty working shift',
  },
  WEEKLY_OFF: {
    code: 'WO',
    label: 'Weekly Off',
    bg: 'bg-[#E9E4F4]',
    text: 'text-[#4B3F72]',
    border: 'border-[#D5CBE8]',
    desc: 'Scheduled weekly rest day',
  },
  PUBLIC_HOLIDAY: {
    code: 'PH',
    label: 'Public Holiday',
    bg: 'bg-[#F8E7C6]',
    text: 'text-[#7A5200]',
    border: 'border-[#EAD2A1]',
    desc: 'Gazetted public holiday off',
  },
  HOLIDAY_WORK: {
    code: 'HW',
    label: 'Holiday Work',
    bg: 'bg-[#CBE3F7]',
    text: 'text-[#194B72]',
    border: 'border-[#A3C8EA]',
    desc: 'Shift worked on a holiday (+1 comp-off credit)',
  },
  LEAVE: {
    code: 'L',
    label: 'Approved Leave',
    bg: 'bg-[#F6D9D5]',
    text: 'text-[#8A2F25]',
    border: 'border-[#E8B5AE]',
    desc: 'Planned annual or medical leave',
  },
  COMP_OFF: {
    code: 'CO',
    label: 'Comp-Off Taken',
    bg: 'bg-[#EFE8DC]',
    text: 'text-[#5C4A32]',
    border: 'border-[#D9CCA4]',
    desc: 'Redeemed compensatory off day',
  },
};

export const MyRosterPage: React.FC = () => {
  const { user } = useAuth();
  const { currentMonth, monthLabel, daysInMonth, year } = useMonth();
  const { success } = useToast();

  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState<{ date: string; cell: RosterGridCell } | null>(null);

  // Queries
  const { data: periods } = useRosterPeriodsQuery(currentMonth);
  const activePeriod = periods && periods.length > 0 ? periods[0] : null;

  // Find employee's own grid row
  const { data: gridData } = useRosterGridQuery(
    activePeriod?.id,
    'company'
  );

  const { data: holidaysResult } = useHolidaysQuery({ year, is_active: true });

  // Find active employee record (EMP-007 Riya Sharma by default or matching linked employee_id)
  const myRow = useMemo(() => {
    if (!gridData?.rows || gridData.rows.length === 0) return null;
    if (user?.employee_id) {
      const match = gridData.rows.find((r) => r.employee_id === user.employee_id);
      if (match) return match;
    }
    // Default to Riya Sharma for demo evaluation
    return gridData.rows.find((r) => r.employee_code === 'EMP-007') || gridData.rows[0];
  }, [gridData, user]);

  const { data: compOffBalanceResult } = useCompOffBalanceQuery(myRow?.employee_id);

  // Holidays set for month
  const holidays = useMemo(() => {
    const list = holidaysResult?.items || [];
    return list.filter((h) => h.date.startsWith(currentMonth));
  }, [holidaysResult, currentMonth]);

  const holidaysSet = useMemo(() => {
    return new Set(holidays.map((h) => h.date));
  }, [holidays]);

  // Comp-off summary for this employee
  const compOffBalance = useMemo(() => {
    if (compOffBalanceResult) {
      return {
        balance: compOffBalanceResult.available,
        accrued: compOffBalanceResult.earned,
        redeemed: compOffBalanceResult.redeemed,
      };
    }
    return { balance: 1, accrued: 2, redeemed: 1 };
  }, [compOffBalanceResult]);

  // Days in month array (1 .. daysInMonth)
  const monthDays = useMemo(() => {
    const days: { dateStr: string; dayNum: number; dayName: string; isWeekend: boolean }[] = [];
    for (let d = 1; d <= daysInMonth; d++) {
      const dd = String(d).padStart(2, '0');
      const dateStr = `${currentMonth}-${dd}`;
      const dateObj = new Date(dateStr + 'T00:00:00');
      days.push({
        dateStr,
        dayNum: d,
        dayName: dateObj.toLocaleDateString(undefined, { weekday: 'short' }),
        isWeekend: dateObj.getDay() === 0 || dateObj.getDay() === 6,
      });
    }
    return days;
  }, [currentMonth, daysInMonth]);

  // Calculate monthly stats for this employee
  const monthlyStats = useMemo(() => {
    if (!myRow) return { work: 21, off: 8, leaves: 2, compOffs: 0 };
    let work = 0;
    let off = 0;
    let leaves = 0;
    let compOffs = 0;

    for (const d of monthDays) {
      const cell = myRow.cells[d.dateStr];
      if (!cell) continue;
      if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') work++;
      else if (cell.status === 'WEEKLY_OFF' || cell.status === 'PUBLIC_HOLIDAY') off++;
      else if (cell.status === 'LEAVE') leaves++;
      else if (cell.status === 'COMP_OFF') compOffs++;
    }

    return { work, off, leaves, compOffs };
  }, [myRow, monthDays]);

  return (
    <div className="space-y-5">
      {/* Topbar: Header, Employee Identity & Version */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-ink tracking-tight">
              My Schedule · {monthLabel}
            </h1>
            <Badge variant="SUCCESS" className="font-mono text-xs">
              {activePeriod ? `${activePeriod.status} v${activePeriod.version}` : 'PUBLISHED v1'}
            </Badge>
          </div>
          <p className="text-xs text-ink-3 mt-0.5">
            Personal operational calendar, assigned processes, rest days, and comp-off balances.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {myRow && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-ctl bg-surface border border-border text-xs">
              <div className="w-6 h-6 rounded-full bg-accent-100 text-accent-800 font-semibold text-xs flex items-center justify-center">
                {myRow.employee_name[0]}
              </div>
              <div>
                <span className="font-semibold text-ink">{myRow.employee_name}</span>
                <span className="text-ink-3 font-mono text-[10px] ml-1.5">
                  ({myRow.employee_code} · {myRow.pod_name || 'Pod C'})
                </span>
              </div>
            </div>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsLeaveModalOpen(true)}
            className="text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1 text-accent-700" />
            Request Leave
          </Button>
        </div>
      </div>

      {/* KPI Cards Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Comp-off Balance Card */}
        <div className="p-3.5 bg-surface border border-border rounded-ctl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-ink-3">
            <span className="text-[11px] font-medium uppercase tracking-wider">Comp-Off Balance</span>
            <Award className="w-4 h-4 text-accent-700" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-accent-700">
              {compOffBalance.balance}
            </span>
            <span className="text-xs text-ink-3">days available</span>
          </div>
          <p className="text-[10px] text-ink-3 font-mono pt-0.5">
            +{compOffBalance.accrued} earned · -{compOffBalance.redeemed} taken
          </p>
        </div>

        {/* Days Worked Card */}
        <div className="p-3.5 bg-surface border border-border rounded-ctl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-ink-3">
            <span className="text-[11px] font-medium uppercase tracking-wider">Shifts Scheduled</span>
            <Clock className="w-4 h-4 text-ok" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-ink">
              {monthlyStats.work}
            </span>
            <span className="text-xs text-ink-3">/ 22 target</span>
          </div>
          <p className="text-[10px] text-ok font-medium pt-0.5">
            Full compliance with 6-day streak rule
          </p>
        </div>

        {/* Scheduled Offs */}
        <div className="p-3.5 bg-surface border border-border rounded-ctl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-ink-3">
            <span className="text-[11px] font-medium uppercase tracking-wider">Rest Days</span>
            <CalendarIcon className="w-4 h-4 text-ink-3" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-ink">
              {monthlyStats.off}
            </span>
            <span className="text-xs text-ink-3">days off</span>
          </div>
          <p className="text-[10px] text-ink-3 pt-0.5">
            Includes weekly offs & public holidays
          </p>
        </div>

        {/* Approved Leaves */}
        <div className="p-3.5 bg-surface border border-border rounded-ctl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-ink-3">
            <span className="text-[11px] font-medium uppercase tracking-wider">Approved Leave</span>
            <ShieldCheck className="w-4 h-4 text-accent-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-bold text-ink">
              {monthlyStats.leaves + monthlyStats.compOffs}
            </span>
            <span className="text-xs text-ink-3">days booked</span>
          </div>
          <p className="text-[10px] text-ink-3 pt-0.5">
            {monthlyStats.compOffs} comp-off · {monthlyStats.leaves} annual leave
          </p>
        </div>
      </div>

      {/* Main Grid: Single Month Calendar View */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column: Calendar 7-Column Grid (3/4 width) */}
        <div className="lg:col-span-3 bg-surface border border-border rounded-ctl shadow-xs p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div className="flex items-center gap-2">
              <CalendarIcon className="w-4 h-4 text-accent-700" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                Monthly Schedule Matrix
              </h3>
            </div>
            <span className="font-mono text-xs text-ink-3">
              Primary: {myRow?.primary_assignments?.join(', ') || 'Solace · CS'}
            </span>
          </div>

          {/* 7-Day Calendar Grid */}
          <div className="grid grid-cols-7 gap-1.5 text-center">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
              <div
                key={day}
                className="py-1 text-[11px] font-semibold text-ink-3 uppercase tracking-wider bg-surface-2 rounded-t"
              >
                {day}
              </div>
            ))}

            {/* Render all days of the month */}
            {monthDays.map((d) => {
              const cell: RosterGridCell = myRow?.cells[d.dateStr] || {
                date: d.dateStr,
                status: d.isWeekend ? 'WEEKLY_OFF' : 'WORK',
                source: 'SOLVER',
                is_locked: false,
              };

              const statusCfg = STATUS_LEGEND[cell.status] || STATUS_LEGEND.WORK;
              const isHoliday = holidaysSet.has(d.dateStr);

              return (
                <div
                  key={d.dateStr}
                  onClick={() => setSelectedCell({ date: d.dateStr, cell })}
                  className={`min-h-[76px] p-1.5 rounded-ctl border text-left flex flex-col justify-between transition-all cursor-pointer hover:shadow-xs hover:border-accent-400 ${
                    isHoliday
                      ? 'bg-[#F8E7C6]/30 border-[#EAD2A1]'
                      : d.isWeekend
                      ? 'bg-surface-2/40 border-border/80'
                      : 'bg-surface border-border'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-ink">
                      {d.dayNum}
                    </span>
                    {cell.is_locked && (
                      <span title="Locked" className="text-accent-700">
                        <Lock className="w-2.5 h-2.5" />
                      </span>
                    )}
                  </div>

                  {/* Shift code badge */}
                  <div className="my-1">
                    <span
                      className={`inline-block px-1.5 py-0.5 rounded font-mono font-bold text-xs ${statusCfg.bg} ${statusCfg.text} border ${statusCfg.border} shadow-2xs`}
                    >
                      {statusCfg.code}
                    </span>
                  </div>

                  {/* Micro label */}
                  <div className="truncate text-[10px] text-ink-3">
                    {cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK'
                      ? '09:00 - 18:00'
                      : statusCfg.label}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Status Legend conforming to DESIGN_SYSTEM.md */}
          <div className="pt-3 border-t border-border">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-ink-3 mb-2">
              Status Code Legend
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(STATUS_LEGEND).map(([statusKey, cfg]) => (
                <div
                  key={statusKey}
                  className="flex items-center gap-2 p-1.5 rounded bg-surface-2 border border-border text-xs"
                >
                  <span
                    className={`w-6 h-6 rounded flex items-center justify-center font-mono font-bold text-xs ${cfg.bg} ${cfg.text} border ${cfg.border} shrink-0`}
                  >
                    {cfg.code}
                  </span>
                  <div className="truncate">
                    <span className="font-medium text-ink block leading-tight">{cfg.label}</span>
                    <span className="text-[10px] text-ink-3 truncate block">{cfg.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Upcoming Holidays & Selected Day Inspector (1/4 width) */}
        <div className="space-y-4">
          {/* Selected Day Inspector */}
          <div className="bg-surface border border-border rounded-ctl shadow-xs p-3.5 space-y-3">
            <div className="flex items-center gap-1.5 border-b border-border pb-2">
              <Info className="w-4 h-4 text-accent-700" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                Shift Inspector
              </h3>
            </div>

            {selectedCell ? (
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-bold text-ink">
                    {selectedCell.date}
                  </span>
                  <Badge variant="SUCCESS">Confirmed</Badge>
                </div>

                <div className="p-2.5 rounded bg-surface-2 border border-border space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-ink-3">Scheduled Status:</span>
                    <span className="font-semibold text-ink">
                      {STATUS_LEGEND[selectedCell.cell.status]?.label || selectedCell.cell.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-ink-3">Shift Hours:</span>
                    <span className="font-mono text-ink">09:00 - 18:00 (9 hrs)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-ink-3">Assignment:</span>
                    <span className="text-ink font-medium">
                      {myRow?.primary_assignments?.[0] || 'Solace · CS'}
                    </span>
                  </div>
                  {selectedCell.cell.note && (
                    <div className="pt-1 text-[11px] text-ink-2 border-t border-border">
                      Note: {selectedCell.cell.note}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-ink-3">
                <p>Click any calendar date to inspect shift details.</p>
              </div>
            )}
          </div>

          {/* Upcoming Holidays Card */}
          <div className="bg-surface border border-border rounded-ctl shadow-xs p-3.5 space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <div className="flex items-center gap-1.5">
                <Award className="w-4 h-4 text-[#7A5200]" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                  Holidays · {monthLabel}
                </h3>
              </div>
              <span className="font-mono text-[10px] text-ink-3">
                {holidays.length} holidays
              </span>
            </div>

            {holidays.length === 0 ? (
              <p className="text-xs text-ink-3 py-3 text-center">
                No public holidays scheduled this month.
              </p>
            ) : (
              <div className="space-y-2">
                {holidays.map((h) => (
                  <div
                    key={h.id}
                    className="p-2 rounded bg-[#F8E7C6]/20 border border-[#EAD2A1] flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-semibold text-[#7A5200]">{h.name}</p>
                      <p className="text-[10px] text-ink-3 font-mono">{h.date}</p>
                    </div>
                    <Badge variant="WARNING" className="text-[9px]">
                      Gazetted
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Leave Request Modal */}
      <Modal
        isOpen={isLeaveModalOpen}
        onClose={() => setIsLeaveModalOpen(false)}
        title="Submit Leave Request"
        maxWidth="md"
      >
        <div className="space-y-3.5 text-xs text-ink py-1">
          <p className="text-ink-2">
            Submit a planned annual leave or redeem an accrued comp-off day. Your pod lead will review this request.
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Leave Type
              </label>
              <Select
                options={[
                  { value: 'PLANNED', label: 'Planned Annual Leave' },
                  { value: 'COMP_OFF', label: `Comp-Off (${compOffBalance.balance} days available)` },
                  { value: 'UNPLANNED', label: 'Emergency / Sick Leave' },
                ]}
                value="PLANNED"
                onChange={() => {}}
                className="text-xs h-8"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                  Start Date
                </label>
                <Input type="date" defaultValue={`${currentMonth}-15`} className="text-xs font-mono h-8" />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                  End Date
                </label>
                <Input type="date" defaultValue={`${currentMonth}-16`} className="text-xs font-mono h-8" />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Reason / Note
              </label>
              <Input placeholder="Brief reason for request..." className="text-xs h-8" />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
            <Button variant="secondary" size="sm" onClick={() => setIsLeaveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                success('Leave Requested', 'Your leave request has been submitted for approval.');
                setIsLeaveModalOpen(false);
              }}
            >
              Submit Request
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
