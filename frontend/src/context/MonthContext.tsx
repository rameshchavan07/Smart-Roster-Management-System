import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

export interface MonthContextValue {
  /** Formatted as YYYY-MM (e.g., '2026-12') */
  currentMonth: string;
  year: number;
  /** 0-indexed month (0 = January, 11 = December) */
  monthIndex: number;
  /** Full month label (e.g., 'December 2026') */
  monthLabel: string;
  /** Short month label (e.g., 'Dec 2026') */
  monthShortLabel: string;
  /** First day formatted as YYYY-MM-DD */
  startDate: string;
  /** Last day formatted as YYYY-MM-DD */
  endDate: string;
  /** Total days in month */
  daysInMonth: number;
  /** Advance one month */
  nextMonth: () => void;
  /** Go back one month */
  prevMonth: () => void;
  /** Set to specific month string 'YYYY-MM' */
  setMonth: (monthStr: string) => void;
  /** Reset to default target month ('2026-12') */
  resetToDefault: () => void;
  /** Selection options for quick picker */
  availableMonths: Array<{ value: string; label: string }>;
}

const DEFAULT_MONTH = '2026-12';

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const MONTH_SHORT_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

const MonthContext = createContext<MonthContextValue | undefined>(undefined);

export const MonthProvider: React.FC<{
  initialMonth?: string;
  children: React.ReactNode;
}> = ({ initialMonth = DEFAULT_MONTH, children }) => {
  const [currentMonth, setCurrentMonth] = useState<string>(initialMonth);

  const { year, monthIndex } = useMemo(() => {
    const parts = currentMonth.split('-');
    const y = parseInt(parts[0], 10) || 2026;
    const m = (parseInt(parts[1], 10) || 12) - 1;
    return { year: y, monthIndex: m };
  }, [currentMonth]);

  const daysInMonth = useMemo(() => {
    return new Date(year, monthIndex + 1, 0).getDate();
  }, [year, monthIndex]);

  const monthLabel = useMemo(() => {
    return `${MONTH_NAMES[monthIndex]} ${year}`;
  }, [monthIndex, year]);

  const monthShortLabel = useMemo(() => {
    return `${MONTH_SHORT_NAMES[monthIndex]} ${year}`;
  }, [monthIndex, year]);

  const startDate = useMemo(() => {
    const mm = String(monthIndex + 1).padStart(2, '0');
    return `${year}-${mm}-01`;
  }, [year, monthIndex]);

  const endDate = useMemo(() => {
    const mm = String(monthIndex + 1).padStart(2, '0');
    const dd = String(daysInMonth).padStart(2, '0');
    return `${year}-${mm}-${dd}`;
  }, [year, monthIndex, daysInMonth]);

  const nextMonth = useCallback(() => {
    setCurrentMonth((prev) => {
      const parts = prev.split('-');
      let y = parseInt(parts[0], 10);
      let m = parseInt(parts[1], 10);
      m += 1;
      if (m > 12) {
        m = 1;
        y += 1;
      }
      return `${y}-${String(m).padStart(2, '0')}`;
    });
  }, []);

  const prevMonth = useCallback(() => {
    setCurrentMonth((prev) => {
      const parts = prev.split('-');
      let y = parseInt(parts[0], 10);
      let m = parseInt(parts[1], 10);
      m -= 1;
      if (m < 1) {
        m = 12;
        y -= 1;
      }
      return `${y}-${String(m).padStart(2, '0')}`;
    });
  }, []);

  const setMonth = useCallback((monthStr: string) => {
    if (/^\d{4}-\d{2}$/.test(monthStr)) {
      setCurrentMonth(monthStr);
    }
  }, []);

  const resetToDefault = useCallback(() => {
    setCurrentMonth(DEFAULT_MONTH);
  }, []);

  const availableMonths = useMemo(() => {
    const months: Array<{ value: string; label: string }> = [];
    // Generate months around planning window: 2026-09 to 2027-06
    const startYear = 2026;
    for (let y = startYear; y <= 2027; y++) {
      const startM = y === 2026 ? 8 : 0; // Sept to Dec for 2026
      const endM = y === 2027 ? 5 : 11; // Jan to June for 2027
      for (let m = startM; m <= endM; m++) {
        const val = `${y}-${String(m + 1).padStart(2, '0')}`;
        months.push({
          value: val,
          label: `${MONTH_NAMES[m]} ${y}`,
        });
      }
    }
    return months;
  }, []);

  const value = useMemo<MonthContextValue>(
    () => ({
      currentMonth,
      year,
      monthIndex,
      monthLabel,
      monthShortLabel,
      startDate,
      endDate,
      daysInMonth,
      nextMonth,
      prevMonth,
      setMonth,
      resetToDefault,
      availableMonths,
    }),
    [
      currentMonth,
      year,
      monthIndex,
      monthLabel,
      monthShortLabel,
      startDate,
      endDate,
      daysInMonth,
      nextMonth,
      prevMonth,
      setMonth,
      resetToDefault,
      availableMonths,
    ]
  );

  return <MonthContext.Provider value={value}>{children}</MonthContext.Provider>;
};

export const useMonth = (): MonthContextValue => {
  const context = useContext(MonthContext);
  if (!context) {
    throw new Error('useMonth must be used within a MonthProvider');
  }
  return context;
};

