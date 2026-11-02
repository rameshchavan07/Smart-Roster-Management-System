import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  LayoutGrid,
  BarChart2,
  Calendar,
  CalendarDays,
  Sparkles,
  ShieldCheck,
  Download,
} from 'lucide-react';
import {
  Button,
  Input,
  Select,
  Badge,
  EmptyState,
  useToast,
} from '../../components/ui';
import { useMonth } from '../../context/MonthContext';
import { useAuth } from '../auth/AuthContext';
import { showApiErrorToast } from '../../api/errorMapping';
import {
  useRosterPeriodsQuery,
  useRosterGridQuery,
  useRosterCoverageQuery,
  useUpdateRosterEntriesMutation,
  useLockRosterEntriesMutation,
} from '../../api/rosters';
import { useHolidaysQuery } from '../../api/rules';
import { usePodsQuery, useEmployeesQuery } from '../../api/team';
import { useBrandsQuery, useProcessesQuery } from '../../api/brands';
import { RosterGrid } from './RosterGrid';
import { CoverageHeatmap } from './CoverageHeatmap';
import { DayViewDrawer } from './DayViewDrawer';
import { EmployeeRosterCard } from './EmployeeRosterCard';
import { CellEditPopover } from './CellEditPopover';
import { GenerateRosterModal } from './GenerateRosterModal';
import { PublishConfirmModal } from './PublishConfirmModal';
import { ExportModal } from './ExportModal';
import { VersionHistoryDropdown } from './VersionHistoryDropdown';
import { MobileAgendaRoster } from './MobileAgendaRoster';
import type {
  RosterGridRow,
  RosterGridCell,
  RosterEntryStatus,
  RosterCoverageCell,
  RosterViewMode,
  RosterPeriod,
} from '../../types/roster';

// Sample fallback employees from SAMPLE_DATA.md when no backend period is active yet
const SAMPLE_EMPLOYEES = [
  { id: 'emp-001', code: 'EMP-001', name: 'Aanya Sharma', pod: 'Pod A', assignment: 'Lead' },
  { id: 'emp-007', code: 'EMP-007', name: 'Riya Shah', pod: 'Pod A', assignment: 'Aurora Lead (CS)' },
  { id: 'emp-008', code: 'EMP-008', name: 'Karan Mehta', pod: 'Pod A', assignment: 'Solace (CS)' },
  { id: 'emp-009', code: 'EMP-009', name: 'Tanvi Rao', pod: 'Pod A', assignment: 'Lumina (CS)' },
  { id: 'emp-010', code: 'EMP-010', name: 'Arjun Das', pod: 'Pod A', assignment: 'Zenith Essentials' },
  { id: 'emp-002', code: 'EMP-002', name: 'Bhavin Patel', pod: 'Pod B', assignment: 'Lead' },
  { id: 'emp-011', code: 'EMP-011', name: 'Kredo Specialist', pod: 'Pod B', assignment: 'Kredo (CS/RET)' },
  { id: 'emp-015', code: 'EMP-015', name: 'Aarav Patel', pod: 'Pod B', assignment: 'Nova (CS)' },
  { id: 'emp-016', code: 'EMP-016', name: 'Pooja Sharma', pod: 'Pod B', assignment: 'Nova (ACC)' },
  { id: 'emp-017', code: 'EMP-017', name: 'Vikram Singh', pod: 'Pod B', assignment: 'Nova (NDR)' },
  { id: 'emp-003', code: 'EMP-003', name: 'Chetan Kumar', pod: 'Pod C', assignment: 'Lead' },
  { id: 'emp-021', code: 'EMP-021', name: 'Neha Gupta', pod: 'Pod C', assignment: 'Pulse (CS)' },
  { id: 'emp-022', code: 'EMP-022', name: 'Rahul Verma', pod: 'Pod C', assignment: 'Pulse (CS)' },
  { id: 'emp-004', code: 'EMP-004', name: 'Divya Nair', pod: 'Pod D', assignment: 'Lead' },
  { id: 'emp-023', code: 'EMP-023', name: 'Aditi Rao', pod: 'Pod D', assignment: 'Orion (CS)' },
  { id: 'emp-024', code: 'EMP-024', name: 'Dev Malhotra', pod: 'Pod D', assignment: 'Orion (CS)' },
  { id: 'emp-005', code: 'EMP-005', name: 'Eshaan Joshi', pod: 'Pod E', assignment: 'Lead' },
  { id: 'emp-028', code: 'EMP-028', name: 'Zoya Khan', pod: 'Pod E', assignment: 'Zenith (CS)' },
  { id: 'emp-029', code: 'EMP-029', name: 'Kunal Kapoor', pod: 'Pod E', assignment: 'Zenith (ACC)' },
  { id: 'emp-030', code: 'EMP-030', name: 'Meera Sen', pod: 'Pod E', assignment: 'Zenith (RET)' },
  { id: 'emp-006', code: 'EMP-006', name: 'Farhan Ali', pod: 'Pod F', assignment: 'Lead' },
  { id: 'emp-033', code: 'EMP-033', name: 'Kabir Nair', pod: 'Pod F', assignment: 'Dedicated Floater' },
  { id: 'emp-034', code: 'EMP-034', name: 'Ananya Verma', pod: 'Pod F', assignment: 'Dedicated Floater' },
  { id: 'emp-035', code: 'EMP-035', name: 'Rohan Mehra', pod: 'Pod F', assignment: 'Dedicated Floater' },
  { id: 'emp-036', code: 'EMP-036', name: 'Priya Pillai', pod: 'Pod F', assignment: 'Dedicated Floater' },
];

export const RosterWorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentMonth, monthLabel, daysInMonth, year } = useMonth();
  const { isOpsManager, isPodLead } = useAuth();
  const toast = useToast();

  const canEdit = isOpsManager || isPodLead;

  // Active workspace presentation tab: 'GRID' (Matrix with 4px strips), 'HEATMAP' (Coverage heatmap), or 'AGENDA' (Mobile agenda)
  const [workspaceTab, setWorkspaceTab] = useState<'GRID' | 'HEATMAP' | 'AGENDA'>(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      return 'AGENDA';
    }
    return 'GRID';
  });

  // View state: 'company' | 'pod' | 'brand' | 'process' | 'employee'
  const [viewMode, setViewMode] = useState<RosterViewMode>('company');
  const [selectedPodFilter, setSelectedPodFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Secondary ref selectors for the 5 view modes
  const [selectedPodId, setSelectedPodId] = useState<string>('');
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');
  const [selectedProcessId, setSelectedProcessId] = useState<string>('');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');

  // Active day view date (for Day View Drawer)
  const [dayViewDate, setDayViewDate] = useState<string | null>(null);

  // Master data queries for secondary view filters
  const { data: podsResult } = usePodsQuery({ limit: 100 });
  const { data: brandsResult } = useBrandsQuery({ limit: 100 });
  const { data: processesResult } = useProcessesQuery({ limit: 100 });
  const { data: employeesResult } = useEmployeesQuery({ limit: 200 });

  // Sync selected employee ID with real backend UUIDs when loaded
  useEffect(() => {
    if (employeesResult?.items && employeesResult.items.length > 0) {
      setSelectedEmployeeId((prev) => {
        if (prev && employeesResult.items.some((e) => e.id === prev)) {
          return prev;
        }
        const riya = employeesResult.items.find((e) => e.code === 'EMP-007');
        return riya ? riya.id : employeesResult.items[0].id;
      });
    }
  }, [employeesResult]);

  // Compute active ref_id for backend view filtering (safeguard against non-UUID mock strings)
  const isUuid = (val?: string): boolean =>
    Boolean(val && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val));

  const activeRefId = useMemo(() => {
    let candidate: string | undefined;
    if (viewMode === 'pod') candidate = selectedPodId || undefined;
    else if (viewMode === 'brand') candidate = selectedBrandId || undefined;
    else if (viewMode === 'process') candidate = selectedProcessId || undefined;
    else if (viewMode === 'employee') candidate = selectedEmployeeId || undefined;

    return isUuid(candidate) ? candidate : undefined;
  }, [viewMode, selectedPodId, selectedBrandId, selectedProcessId, selectedEmployeeId]);

  // Selected cell for CellEditPopover with live impact
  const [selectedCellInfo, setSelectedCellInfo] = useState<{
    row: RosterGridRow;
    date: string;
    cell: RosterGridCell;
    anchorRect: DOMRect | null;
  } | null>(null);

  // Local fallback modifications map (employeeId + date -> updated cell)
  const [localOverrides, setLocalOverrides] = useState<Record<string, RosterGridCell>>({});

  // Modal dialog states
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState<boolean>(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState<boolean>(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);
  const [selectedPeriodId, setSelectedPeriodId] = useState<string | null>(null);

  // Fetch roster periods for the active month
  const {
    data: periods,
    isLoading: isPeriodsLoading,
    refetch: refetchPeriods,
  } = useRosterPeriodsQuery(currentMonth);

  const activePeriod = useMemo<RosterPeriod | null>(() => {
    if (!periods || periods.length === 0) return null;
    if (selectedPeriodId) {
      const match = periods.find((p) => p.id === selectedPeriodId);
      if (match) return match;
    }
    return periods[0];
  }, [periods, selectedPeriodId]);

  // Fetch grid data for active period
  const {
    data: gridData,
    isLoading: isGridLoading,
    refetch: refetchGrid,
  } = useRosterGridQuery(activePeriod?.id, viewMode, activeRefId);

  // Fetch coverage metrics for active period
  const {
    data: coverageData,
    isLoading: isCoverageLoading,
    refetch: refetchCoverage,
  } = useRosterCoverageQuery(activePeriod?.id);

  // Fetch public holidays for the active year
  const { data: holidaysResult } = useHolidaysQuery({ year, is_active: true });
  const holidaysSet = useMemo(() => {
    const set = new Set<string>();
    if (holidaysResult?.items) {
      for (const h of holidaysResult.items) {
        set.add(h.date);
      }
    }
    // Default demo Christmas holiday
    set.add(`${year}-12-25`);
    return set;
  }, [holidaysResult, year]);

  // Mutations
  const updateEntriesMutation = useUpdateRosterEntriesMutation();
  const lockMutation = useLockRosterEntriesMutation();

  // Generate date strings for current month (YYYY-MM-01 .. YYYY-MM-DD)
  const monthDates = useMemo(() => {
    const dates: string[] = [];
    for (let day = 1; day <= daysInMonth; day++) {
      const dd = String(day).padStart(2, '0');
      dates.push(`${currentMonth}-${dd}`);
    }
    return dates;
  }, [currentMonth, daysInMonth]);

  // Effective coverage cells from API or synthesized from SAMPLE_DATA.md scenarios
  const effectiveCoverageCells: RosterCoverageCell[] = useMemo(() => {
    if (coverageData && coverageData.length > 0) {
      return coverageData;
    }

    // Key demo brand processes from SAMPLE_DATA.md
    const DEMO_BPS = [
      { id: 'bp-01-cs', brand: 'Aurora', process: 'CS', calendar: 'ALL_365', baseReq: 1 },
      { id: 'bp-01-acc', brand: 'Aurora', process: 'ACC', calendar: 'ALL_EXCEPT_HOLIDAYS', baseReq: 1 },
      { id: 'bp-01-ndr', brand: 'Aurora', process: 'NDR', calendar: 'EXCLUDE_SUNDAY_AND_HOLIDAYS', baseReq: 1 },
      { id: 'bp-02-cs', brand: 'Solace', process: 'CS', calendar: 'ALL_365', baseReq: 1 },
      { id: 'bp-03-cs', brand: 'Lumina', process: 'CS', calendar: 'ALL_EXCEPT_HOLIDAYS', baseReq: 1 },
      { id: 'bp-21-cs', brand: 'Nova', process: 'CS', calendar: 'ALL_365', baseReq: 1 },
      { id: 'bp-21-acc', brand: 'Nova', process: 'ACC', calendar: 'ALL_EXCEPT_HOLIDAYS', baseReq: 1 },
      { id: 'bp-21-ndr', brand: 'Nova', process: 'NDR', calendar: 'EXCLUDE_SUNDAY_AND_HOLIDAYS', baseReq: 1 },
      { id: 'bp-23-cs', brand: 'Pulse', process: 'CS', calendar: 'ALL_365', baseReq: 1, mondayReq: 2 },
      { id: 'bp-24-cs', brand: 'Orion', process: 'CS', calendar: 'ALL_365', baseReq: 1 },
      { id: 'bp-22-cs', brand: 'Zenith', process: 'CS', calendar: 'ALL_365', baseReq: 1 },
      { id: 'bp-22-acc', brand: 'Zenith', process: 'ACC', calendar: 'ALL_EXCEPT_HOLIDAYS', baseReq: 1 },
    ];

    const cells: RosterCoverageCell[] = [];

    for (const bp of DEMO_BPS) {
      for (const dateStr of monthDates) {
        const d = new Date(dateStr + 'T00:00:00');
        const dayOfWeek = d.getDay(); // 0 = Sun, 1 = Mon, 6 = Sat
        const isXmas = dateStr.endsWith('-12-25');

        let isOperating = true;
        if (bp.calendar === 'ALL_EXCEPT_HOLIDAYS' && isXmas) isOperating = false;
        if (bp.calendar === 'EXCLUDE_SUNDAY_AND_HOLIDAYS' && (dayOfWeek === 0 || isXmas)) {
          isOperating = false;
        }

        const required = isOperating
          ? bp.mondayReq && dayOfWeek === 1
            ? bp.mondayReq
            : bp.baseReq
          : 0;
        let actual = required;

        // Scenario S1: Aurora CS uncovered Dec 13-15
        if (
          bp.id === 'bp-01-cs' &&
          (dateStr.endsWith('-12-13') || dateStr.endsWith('-12-14') || dateStr.endsWith('-12-15'))
        ) {
          actual = 0;
        }

        // Scenario S2: Nova ACC understaffed Dec 9
        if (bp.id === 'bp-21-acc' && dateStr.endsWith('-12-09')) {
          actual = 0;
        }

        // Scenario S3: Pulse CS requires 2 on Mondays, Rahul Verma off on Dec 14
        if (bp.id === 'bp-23-cs' && dateStr.endsWith('-12-14')) {
          actual = 1; // Needs 2, has 1 -> understaffed
        }

        cells.push({
          date: dateStr,
          brand_process_id: bp.id,
          brand_name: bp.brand,
          process_name: bp.process,
          required,
          actual,
          shortfall: Math.max(0, required - actual),
        });
      }
    }

    return cells;
  }, [coverageData, monthDates]);

  // Construct effective grid rows from API data or realistic fallback
  const effectiveRows: RosterGridRow[] = useMemo(() => {
    if (gridData?.rows && gridData.rows.length > 0) {
      return gridData.rows.map((r) => {
        const mergedCells = { ...r.cells };
        for (const [key, override] of Object.entries(localOverrides)) {
          if (key.startsWith(`${r.employee_id}:`)) {
            const date = key.split(':')[1];
            mergedCells[date] = override;
          }
        }
        return {
          ...r,
          cells: mergedCells,
        };
      });
    }

    // Realistic fallback mock grid for seamless inspection & testing
    return SAMPLE_EMPLOYEES.map((emp, empIdx) => {
      const cells: Record<string, RosterGridCell> = {};

      monthDates.forEach((dateStr, dayIdx) => {
        const d = new Date(dateStr + 'T00:00:00');
        const dayOfWeek = d.getDay(); // 0 = Sun, 6 = Sat
        const isXmas = dateStr.endsWith('-12-25');
        const overrideKey = `${emp.id}:${dateStr}`;

        if (localOverrides[overrideKey]) {
          cells[dateStr] = localOverrides[overrideKey];
          return;
        }

        if (isXmas) {
          cells[dateStr] = {
            date: dateStr,
            status: empIdx % 4 === 0 ? 'HOLIDAY_WORK' : 'PUBLIC_HOLIDAY',
            source: 'SOLVER',
            is_locked: false,
            conflicts: [],
          };
        } else if (dayOfWeek === (empIdx % 7)) {
          // Staggered weekly offs across employees
          cells[dateStr] = {
            date: dateStr,
            status: 'WEEKLY_OFF',
            source: 'SOLVER',
            is_locked: false,
            conflicts: [],
          };
        } else if (emp.code === 'EMP-016' && dayIdx >= 7 && dayIdx <= 9) {
          // Pooja Sharma on leave (Scenario S2)
          cells[dateStr] = {
            date: dateStr,
            status: 'LEAVE',
            source: 'LEAVE_REQUEST',
            is_locked: true,
            note: 'Approved annual leave',
            conflicts: [],
          };
        } else {
          cells[dateStr] = {
            date: dateStr,
            status: 'WORK',
            source: 'SOLVER',
            is_locked: false,
            conflicts: [],
          };
        }
      });

      return {
        employee_id: emp.id,
        employee_name: emp.name,
        employee_code: emp.code,
        pod_name: emp.pod,
        primary_assignments: [emp.assignment],
        cells,
      };
    });
  }, [gridData, localOverrides, monthDates]);

  // Options for secondary view mode filters
  const podOptions = useMemo(() => {
    if (podsResult?.items && podsResult.items.length > 0) {
      return podsResult.items.map((p) => ({ value: p.id, label: p.name }));
    }
    return [
      { value: 'Pod A', label: 'Pod A (Support Specialists)' },
      { value: 'Pod B', label: 'Pod B (D2C Accelerators)' },
      { value: 'Pod C', label: 'Pod C (Operations & Retention)' },
      { value: 'Pod D', label: 'Pod D (Logistics & NDR)' },
      { value: 'Pod E', label: 'Pod E (Growth & Engagement)' },
      { value: 'Pod F', label: 'Pod F (Flex & Peak Operations)' },
    ];
  }, [podsResult]);

  const brandOptions = useMemo(() => {
    if (brandsResult?.items && brandsResult.items.length > 0) {
      return brandsResult.items.map((b) => ({ value: b.id, label: `${b.name} (${b.code})` }));
    }
    return [
      { value: 'Aurora', label: 'Aurora (BRD-01)' },
      { value: 'Solace', label: 'Solace (BRD-02)' },
      { value: 'Lumina', label: 'Lumina (BRD-03)' },
      { value: 'Nova', label: 'Nova (BRD-21)' },
      { value: 'Pulse', label: 'Pulse (BRD-23)' },
      { value: 'Orion', label: 'Orion (BRD-24)' },
      { value: 'Zenith', label: 'Zenith (BRD-22)' },
    ];
  }, [brandsResult]);

  const processOptions = useMemo(() => {
    if (processesResult?.items && processesResult.items.length > 0) {
      return processesResult.items.map((p) => ({ value: p.id, label: `${p.name} (${p.code})` }));
    }
    return [
      { value: 'CS', label: 'Customer Support (CS)' },
      { value: 'ACC', label: 'Abandoned Cart (ACC)' },
      { value: 'RET', label: 'Retention (RET)' },
      { value: 'NDR', label: 'Non-Delivery Reports (NDR)' },
    ];
  }, [processesResult]);

  const employeeOptions = useMemo(() => {
    if (employeesResult?.items && employeesResult.items.length > 0) {
      return employeesResult.items.map((e) => ({
        value: e.id,
        label: `${e.full_name} (${e.code})`,
      }));
    }
    return SAMPLE_EMPLOYEES.map((e) => ({
      value: e.id,
      label: `${e.name} (${e.code})`,
    }));
  }, [employeesResult]);

  // Filter rows based on search input, pod filter, and active viewMode
  const filteredRows = useMemo(() => {
    return effectiveRows.filter((row) => {
      // 1. View Mode Filtering
      if (viewMode === 'pod' && selectedPodId) {
        const podObj = podsResult?.items?.find((p) => p.id === selectedPodId);
        const targetName = podObj ? podObj.name : selectedPodId;
        if (row.pod_name !== targetName && !row.pod_name?.includes(targetName)) {
          return false;
        }
      } else if (viewMode === 'brand' && selectedBrandId) {
        const brandObj = brandsResult?.items?.find((b) => b.id === selectedBrandId);
        const targetBrand = (brandObj ? brandObj.name : selectedBrandId).toLowerCase();
        const matchesBrand = row.primary_assignments.some((a) =>
          a.toLowerCase().includes(targetBrand)
        );
        if (!matchesBrand) return false;
      } else if (viewMode === 'process' && selectedProcessId) {
        const procObj = processesResult?.items?.find((p) => p.id === selectedProcessId);
        const targetProc = (procObj ? procObj.code : selectedProcessId).toLowerCase();
        const matchesProc = row.primary_assignments.some((a) =>
          a.toLowerCase().includes(targetProc)
        );
        if (!matchesProc) return false;
      } else if (viewMode === 'employee' && selectedEmployeeId) {
        if (row.employee_id !== selectedEmployeeId && row.employee_code !== selectedEmployeeId) {
          return false;
        }
      }

      // 2. Generic Pod Filter in company view
      if (viewMode === 'company' && selectedPodFilter !== 'ALL' && row.pod_name !== selectedPodFilter) {
        return false;
      }

      // 3. Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = row.employee_name.toLowerCase().includes(q);
        const matchesCode = row.employee_code.toLowerCase().includes(q);
        if (!matchesName && !matchesCode) return false;
      }

      return true;
    });
  }, [
    effectiveRows,
    viewMode,
    selectedPodId,
    selectedBrandId,
    selectedProcessId,
    selectedEmployeeId,
    selectedPodFilter,
    searchQuery,
    podsResult,
    brandsResult,
    processesResult,
  ]);

  // Handle cell click (opens CellEditPopover anchored to clicked cell)
  const handleCellClick = useCallback(
    (
      cell: RosterGridCell,
      row: RosterGridRow,
      date: string,
      targetEl?: HTMLElement | null
    ) => {
      const anchorRect = targetEl ? targetEl.getBoundingClientRect() : null;
      setSelectedCellInfo({ cell, row, date, anchorRect });
    },
    []
  );

  // Quick cell status change shortcut from keyboard navigation
  const handleQuickStatusChange = useCallback(
    (employeeId: string, date: string, newStatus: RosterEntryStatus) => {
      if (!canEdit) return;

      const overrideKey = `${employeeId}:${date}`;
      const newCell: RosterGridCell = {
        date,
        status: newStatus,
        source: 'MANUAL',
        is_locked: false,
        note: 'Quick keyboard update',
        conflicts: [],
      };

      setLocalOverrides((prev) => ({
        ...prev,
        [overrideKey]: newCell,
      }));

      // If active roster period exists, trigger backend mutation
      if (activePeriod?.id) {
        updateEntriesMutation.mutate(
          {
            periodId: activePeriod.id,
            request: {
              entries: [
                {
                  employee_id: employeeId,
                  date,
                  status: newStatus,
                  source: 'MANUAL',
                },
              ],
            },
          },
          {
            onError: (err) => {
              setLocalOverrides((prev) => {
                const next = { ...prev };
                delete next[overrideKey];
                return next;
              });
              showApiErrorToast(err, toast, 'Quick status update failed');
            },
          }
        );
      }

      toast.success('Cell Updated', `Set status to ${newStatus} for ${date}`);
    },
    [canEdit, activePeriod, updateEntriesMutation, toast]
  );

  // Apply edits from CellEditPopover
  const handleApplyCellEdit = async (params: {
    status: RosterEntryStatus;
    isLocked: boolean;
    note: string;
  }) => {
    if (!selectedCellInfo || !canEdit) return;

    const { row, date, cell } = selectedCellInfo;
    const overrideKey = `${row.employee_id}:${date}`;
    const updatedCell: RosterGridCell = {
      date,
      status: params.status,
      source: 'MANUAL',
      is_locked: params.isLocked,
      note: params.note || null,
      conflicts: [],
    };

    setLocalOverrides((prev) => ({
      ...prev,
      [overrideKey]: updatedCell,
    }));

    if (activePeriod?.id) {
      try {
        await updateEntriesMutation.mutateAsync({
          periodId: activePeriod.id,
          request: {
            entries: [
              {
                employee_id: row.employee_id,
                date,
                status: params.status,
                source: 'MANUAL',
                is_locked: params.isLocked,
                reason: params.note || undefined,
              },
            ],
          },
        });

        if (params.isLocked !== cell.is_locked) {
          await lockMutation.mutateAsync({
            periodId: activePeriod.id,
            request: {
              cells: [{ employee_id: row.employee_id, date, is_locked: params.isLocked }],
            },
          });
        }

        toast.success('Schedule Updated', `Saved schedule for ${row.employee_name} on ${date}`);
      } catch (err: unknown) {
        setLocalOverrides((prev) => {
          const next = { ...prev };
          delete next[overrideKey];
          return next;
        });
        showApiErrorToast(err, toast, 'Failed to update schedule cell');
      }
    } else {
      toast.success('Schedule Updated', `Saved schedule for ${row.employee_name} on ${date}`);
    }

    setSelectedCellInfo(null);
  };

  // KPI Calculations
  const stats = useMemo(() => {
    let totalWorkDays = 0;
    let totalOffDays = 0;
    let totalLeaves = 0;

    for (const r of filteredRows) {
      for (const cell of Object.values(r.cells)) {
        if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') totalWorkDays++;
        else if (cell.status === 'WEEKLY_OFF' || cell.status === 'PUBLIC_HOLIDAY')
          totalOffDays++;
        else if (cell.status === 'LEAVE') totalLeaves++;
      }
    }

    return {
      totalStaff: filteredRows.length,
      totalWorkDays,
      totalOffDays,
      totalLeaves,
      conflictsCount: activePeriod?.conflicts_count ?? 0,
    };
  }, [filteredRows, activePeriod]);

  return (
    <div className="space-y-4">
      {/* Topbar: Title, Status Badge, Month Indicator & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-text-primary tracking-tight">
              Roster Workspace
            </h1>
            {periods && periods.length > 0 ? (
              <VersionHistoryDropdown
                periods={periods}
                activePeriod={activePeriod}
                onSelectPeriod={(p) => setSelectedPeriodId(p.id)}
                onPeriodCloned={(p) => {
                  setSelectedPeriodId(p.id);
                  refetchPeriods();
                }}
                onCompareVersions={(idA, idB) => {
                  navigate(`/reports?tab=compare&a=${idA}&b=${idB}`);
                }}
              />
            ) : (
              <Badge variant="WARNING" className="font-mono text-xs">
                No Roster
              </Badge>
            )}
            <Badge variant="neutral" className="text-xs font-mono">
              {monthLabel}
            </Badge>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Interactive virtualised schedule matrix with live conflict validation.
          </p>
        </div>

        {/* Workspace Presentation Switcher & View Mode */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex bg-surface-2 p-0.5 rounded-md border border-border text-xs">
            <button
              type="button"
              onClick={() => setWorkspaceTab('GRID')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                workspaceTab === 'GRID'
                  ? 'bg-surface-1 text-text-primary shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Grid & Strips</span>
            </button>

            <button
              type="button"
              onClick={() => setWorkspaceTab('HEATMAP')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                workspaceTab === 'HEATMAP'
                  ? 'bg-surface-1 text-text-primary shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Coverage Heatmap</span>
            </button>

            <button
              type="button"
              onClick={() => setWorkspaceTab('AGENDA')}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                workspaceTab === 'AGENDA'
                  ? 'bg-surface-1 text-text-primary shadow-sm font-semibold'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span>Agenda</span>
            </button>
          </div>

          {workspaceTab === 'GRID' && (
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex bg-surface-2 p-0.5 rounded-md border border-border text-xs">
                {(['company', 'pod', 'brand', 'process', 'employee'] as RosterViewMode[]).map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setViewMode(v)}
                    className={`px-2 py-1 rounded text-xs font-medium capitalize transition-colors ${
                      viewMode === v
                        ? 'bg-surface-1 text-text-primary shadow-sm font-semibold'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>

              {/* Secondary entity dropdown based on active view mode */}
              {viewMode === 'pod' && (
                <div className="w-44">
                  <Select
                    value={selectedPodId}
                    onChange={(val) => setSelectedPodId(val)}
                    options={[{ value: '', label: 'All Pods' }, ...podOptions]}
                    className="text-xs h-7"
                  />
                </div>
              )}

              {viewMode === 'brand' && (
                <div className="w-48">
                  <Select
                    value={selectedBrandId}
                    onChange={(val) => setSelectedBrandId(val)}
                    options={[{ value: '', label: 'All Brands' }, ...brandOptions]}
                    className="text-xs h-7"
                  />
                </div>
              )}

              {viewMode === 'process' && (
                <div className="w-44">
                  <Select
                    value={selectedProcessId}
                    onChange={(val) => setSelectedProcessId(val)}
                    options={[{ value: '', label: 'All Processes' }, ...processOptions]}
                    className="text-xs h-7"
                  />
                </div>
              )}

              {viewMode === 'employee' && (
                <div className="w-52">
                  <Select
                    value={selectedEmployeeId}
                    onChange={(val) => setSelectedEmployeeId(val)}
                    options={employeeOptions}
                    className="text-xs h-7"
                  />
                </div>
              )}
            </div>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDayViewDate(monthDates[0])}
            title="Inspect operational daily staffing view"
          >
            <Calendar className="w-3.5 h-3.5 mr-1 text-accent-600" />
            Day View
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/simulator')}
            title="Launch What-If Impact Simulator"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1 text-accent-700" />
            Simulator
          </Button>

          {canEdit && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsGenerateModalOpen(true)}
              title="Generate new roster version with CP-SAT solver"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-accent-700" />
              Generate
            </Button>
          )}

          {isOpsManager && activePeriod && activePeriod.status === 'DRAFT' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsPublishModalOpen(true)}
              title="Review gating checks and publish official roster"
            >
              <ShieldCheck className="w-3.5 h-3.5 mr-1" />
              Publish
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsExportModalOpen(true)}
            disabled={!activePeriod}
            title="Export schedule (CSV / Excel XLSX)"
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            Export
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              refetchPeriods();
              if (activePeriod?.id) {
                refetchGrid();
                refetchCoverage();
              }
            }}
            title="Refresh Roster Grid & Coverage"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Sync
          </Button>
        </div>
      </div>

      {/* Stale Roster Banner (A-10) */}
      {activePeriod?.is_stale && (
        <div className="flex items-center justify-between p-3 bg-warn/10 border border-warn/30 rounded-ctl text-xs text-ink">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warn shrink-0" />
            <span>
              <strong>Stale roster:</strong> Inputs (approved leaves, holidays, or coverage rules) have changed since this version was generated.
            </span>
          </div>
          {canEdit && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsGenerateModalOpen(true)}
              className="text-xs h-7 shrink-0"
            >
              <Sparkles className="w-3 h-3 mr-1 text-accent-700" />
              Re-generate
            </Button>
          )}
        </div>
      )}

      {/* Empty State when no roster periods exist for this month */}
      {!isPeriodsLoading && (!periods || periods.length === 0) ? (
        <EmptyState
          title={`No roster for ${monthLabel} yet`}
          description="Generate one from your current team, rules and leaves."
          icon={Calendar}
          actionLabel={canEdit ? 'Generate Roster' : undefined}
          onAction={canEdit ? () => setIsGenerateModalOpen(true) : undefined}
        />
      ) : (
        <>
          {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Staff in View</span>
          <div className="text-lg font-mono font-semibold text-text-primary mt-0.5">
            {stats.totalStaff} <span className="text-xs font-sans text-text-muted font-normal">members</span>
          </div>
        </div>

        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Working Days</span>
          <div className="text-lg font-mono font-semibold text-text-primary mt-0.5">
            {stats.totalWorkDays} <span className="text-xs font-sans text-text-muted font-normal">shifts</span>
          </div>
        </div>

        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Approved Leaves</span>
          <div className="text-lg font-mono font-semibold text-text-primary mt-0.5">
            {stats.totalLeaves} <span className="text-xs font-sans text-text-muted font-normal">days</span>
          </div>
        </div>

        <div
          onClick={() => navigate('/conflicts')}
          className="p-3 bg-surface-1 border border-border rounded-md hover:border-accent-600 cursor-pointer transition-colors"
          title="View all validation conflicts and actionable recommendations"
        >
          <span className="text-[11px] font-medium text-text-muted uppercase flex items-center justify-between">
            <span>Conflicts</span>
            <span className="text-[10px] text-accent-700 font-sans font-normal hover:underline">View all &rarr;</span>
          </span>
          <div className="flex items-center gap-1.5 text-lg font-mono font-semibold mt-0.5">
            {stats.conflictsCount === 0 ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-[#2F6F4F]" />
                <span className="text-[#2F6F4F]">0 Blocking</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 text-[#C2412D]" />
                <span className="text-[#C2412D]">{stats.conflictsCount} Needs Attention</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content: Either Interactive Matrix with Strips OR Full Coverage Heatmap */}
      {workspaceTab === 'GRID' ? (
        <>
          {viewMode === 'employee' && filteredRows.length > 0 ? (
            <EmployeeRosterCard
              row={filteredRows[0]}
              dates={monthDates}
              monthLabel={monthLabel}
              onCellClick={handleCellClick}
            />
          ) : (
            <>
              {/* Search & Filter Bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-surface-1 p-2.5 rounded-md border border-border">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <div className="relative w-full sm:w-64">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                    <Input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search employee or code..."
                      className="pl-8 text-xs h-8"
                    />
                  </div>

                  {viewMode === 'company' && (
                    <div className="w-36">
                      <Select
                        value={selectedPodFilter}
                        onChange={(val) => setSelectedPodFilter(val)}
                        options={[
                          { value: 'ALL', label: 'All Pods' },
                          { value: 'Pod A', label: 'Pod A' },
                          { value: 'Pod B', label: 'Pod B' },
                          { value: 'Pod C', label: 'Pod C' },
                          { value: 'Pod D', label: 'Pod D' },
                          { value: 'Pod E', label: 'Pod E' },
                          { value: 'Pod F', label: 'Pod F' },
                        ]}
                        className="text-xs h-8"
                      />
                    </div>
                  )}
                </div>

                {/* Legend pills */}
                <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-text-muted">
                  <span className="font-semibold text-text-secondary mr-1">Legend:</span>
                  <span className="px-1.5 py-0.5 border border-border rounded font-mono bg-white text-[#1C1B19]">
                    W Work
                  </span>
                  <span className="px-1.5 py-0.5 border border-[#D5CBE8] rounded font-mono bg-[#E9E4F4] text-[#4B3F72]">
                    WO Off
                  </span>
                  <span className="px-1.5 py-0.5 border border-[#F8E7C6] rounded font-mono bg-[#F8E7C6] text-[#7A5200]">
                    PH Holiday
                  </span>
                  <span className="px-1.5 py-0.5 border border-[#F6D9D5] rounded font-mono bg-[#F6D9D5] text-[#8A2F25]">
                    L Leave
                  </span>
                  <span className="px-1.5 py-0.5 border border-[#D9E7F5] rounded font-mono bg-[#D9E7F5] text-[#1F4E79]">
                    CO Comp-off
                  </span>
                </div>
              </div>

              {/* Main Roster Grid with integrated CoverageStrip */}
              <RosterGrid
                rows={filteredRows}
                dates={monthDates}
                holidays={holidaysSet}
                coverageCells={effectiveCoverageCells}
                selectedCell={
                  selectedCellInfo
                    ? {
                        employeeId: selectedCellInfo.row.employee_id,
                        date: selectedCellInfo.date,
                      }
                    : null
                }
                onCellClick={handleCellClick}
                onDayHeaderClick={(date) => setDayViewDate(date)}
                onCoverageCellClick={(cell) => {
                  toast.success(
                    `${cell.brand_name} · ${cell.process_name}`,
                    `Demand: ${cell.required} · Actual: ${cell.actual} · Shortfall: ${cell.shortfall}`
                  );
                }}
                onCellStatusChange={handleQuickStatusChange}
                readOnly={!canEdit}
                isLoading={isPeriodsLoading || isGridLoading}
              />
            </>
          )}
        </>
      ) : workspaceTab === 'HEATMAP' ? (
        /* Standalone Coverage Heatmap View */
        <CoverageHeatmap
          coverageCells={effectiveCoverageCells}
          dates={monthDates}
          isLoading={isPeriodsLoading || isCoverageLoading}
          onCellClick={(cell) => {
            toast.success(
              `${cell.brand_name} · ${cell.process_name}`,
              `Demand: ${cell.required} · Actual: ${cell.actual} · Shortfall: ${cell.shortfall}`
            );
          }}
        />
      ) : (
          <MobileAgendaRoster
            monthDates={monthDates}
            rows={filteredRows}
            holidaysSet={holidaysSet}
            canEdit={canEdit}
            onCellClick={(row, date, cell, e) => {
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
              setSelectedCellInfo({ row, date, cell, anchorRect: rect });
            }}
            onOpenDayView={(d) => setDayViewDate(d)}
          />
        )}
      </>
    )}

      {/* Operational Day View Drawer */}
      <DayViewDrawer
        isOpen={Boolean(dayViewDate)}
        periodId={activePeriod?.id}
        selectedDate={dayViewDate || monthDates[0]}
        onDateChange={(d) => setDayViewDate(d)}
        onClose={() => setDayViewDate(null)}
        onEmployeeSelect={(empId) => {
          setViewMode('employee');
          setSelectedEmployeeId(empId);
          setDayViewDate(null);
        }}
        isHoliday={holidaysSet.has(dayViewDate || '')}
      />

      {/* Cell Edit Popover with Live Impact */}
      {selectedCellInfo && (
        <CellEditPopover
          isOpen={Boolean(selectedCellInfo)}
          onClose={() => setSelectedCellInfo(null)}
          periodId={activePeriod?.id || ''}
          row={selectedCellInfo.row}
          date={selectedCellInfo.date}
          cell={selectedCellInfo.cell}
          anchorRect={selectedCellInfo.anchorRect}
          onApply={handleApplyCellEdit}
          isSaving={updateEntriesMutation.isPending || lockMutation.isPending}
          readOnly={!canEdit}
        />
      )}

      {/* Generate Roster Modal */}
      <GenerateRosterModal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        onGenerated={(res) => {
          setSelectedPeriodId(res.id);
          refetchPeriods();
        }}
      />

      {/* Publish Confirmation Modal with Gating Checks */}
      <PublishConfirmModal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        period={activePeriod}
        onPublished={() => {
          refetchPeriods();
          refetchGrid();
        }}
      />

      {/* Export Modal */}
      <ExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        period={activePeriod}
      />
    </div>
  );
};
