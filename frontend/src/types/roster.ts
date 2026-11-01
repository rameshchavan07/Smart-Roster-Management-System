/**
 * Roster domain and grid types matching backend schemas.
 */

export type RosterEntryStatus =
  | 'WORK'
  | 'WEEKLY_OFF'
  | 'PUBLIC_HOLIDAY'
  | 'HOLIDAY_WORK'
  | 'LEAVE'
  | 'COMP_OFF';

export type RosterStatusCode = 'W' | 'WO' | 'PH' | 'HW' | 'L' | 'CO';

export type EntrySource = 'SOLVER' | 'MANUAL' | 'LEAVE_REQUEST' | 'IMPORT';

export type RosterPeriodStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

export type ConflictSeverity = 'BLOCKING' | 'WARNING' | 'INFO';

export interface RosterGenerateRequest {
  month: string;
  pod_id?: string | null;
  seed?: number;
  time_limit_s?: number;
  use_fallback?: boolean;
}

export interface RosterSummaryMetrics {
  blocking: number;
  warnings: number;
  info: number;
  coverage_pct: number;
}

export interface RosterGenerateResponse {
  id: string;
  month: string;
  version: number;
  status: RosterPeriodStatus;
  solver_status?: string | null;
  summary: RosterSummaryMetrics;
  created_at: string;
}

export interface RosterPeriod {
  id: string;
  month: string; // YYYY-MM-DD
  version: number;
  status: RosterPeriodStatus;
  solver_status?: string | null;
  generation_params?: Record<string, unknown>;
  parent_period_id?: string | null;
  is_stale?: boolean;
  published_at?: string | null;
  created_at: string;
  entries_count?: number | null;
  conflicts_count?: number | null;
}

export interface RosterGridCell {
  date: string; // YYYY-MM-DD
  status: RosterEntryStatus;
  source: EntrySource;
  is_locked: boolean;
  note?: string | null;
  conflicts?: string[];
}

export interface RosterGridRow {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  pod_name?: string | null;
  primary_assignments: string[];
  cells: Record<string, RosterGridCell>; // Keyed by ISO date string (YYYY-MM-DD)
}

export interface RosterGridViewResponse {
  period: RosterPeriod;
  view: string;
  start_date: string;
  end_date: string;
  rows: RosterGridRow[];
}

export interface RosterCoverageCell {
  date: string;
  brand_process_id: string;
  brand_name?: string | null;
  process_name?: string | null;
  required: number;
  actual: number;
  shortfall: number;
}

export type CoverageState = 'COVERED' | 'UNDERSTAFFED' | 'UNCOVERED' | 'CLOSED';

export function getCoverageState(required: number, actual: number): CoverageState {
  if (required <= 0) return 'CLOSED';
  if (actual >= required) return 'COVERED';
  if (actual > 0) return 'UNDERSTAFFED';
  return 'UNCOVERED';
}

export const COVERAGE_CONFIG: Record<
  CoverageState,
  { label: string; text: string; bg: string; border: string; hex: string }
> = {
  COVERED: {
    label: 'Covered',
    text: 'text-[#2E7D5B]',
    bg: 'bg-[#E3F2EA]',
    border: 'border-[#BCE1CE]',
    hex: '#2E7D5B',
  },
  UNDERSTAFFED: {
    label: 'Under-staffed',
    text: 'text-[#B7791F]',
    bg: 'bg-[#FBF0D9]',
    border: 'border-[#F5DCB0]',
    hex: '#B7791F',
  },
  UNCOVERED: {
    label: 'Uncovered',
    text: 'text-[#C2412D]',
    bg: 'bg-[#FBE4DF]',
    border: 'border-[#F5C2BA]',
    hex: '#C2412D',
  },
  CLOSED: {
    label: 'Closed',
    text: 'text-[#8A867C]',
    bg: 'bg-[#F5F3EF]',
    border: 'border-[#E6E3DC]',
    hex: '#8A867C',
  },
};

export interface RosterEntryUpdateItem {
  employee_id: string;
  date: string;
  status: RosterEntryStatus;
  source?: EntrySource;
  is_locked?: boolean | null;
  note?: string | null;
  reason?: string | null;
}

export interface RosterEntriesBatchUpdateRequest {
  entries: RosterEntryUpdateItem[];
  acknowledge_blocking?: boolean;
}

export interface RosterEntriesUpdateResponse {
  roster_period_id: string;
  version: number;
  status: RosterPeriodStatus;
  updated_entries: Array<{
    id: string;
    roster_period_id: string;
    employee_id: string;
    date: string;
    status: RosterEntryStatus;
    source: EntrySource;
    is_locked: boolean;
    note?: string | null;
  }>;
  new_conflicts: Array<Record<string, unknown>>;
  resolved_conflicts: Array<Record<string, unknown>>;
  unchanged_conflicts: Array<Record<string, unknown>>;
  unchanged: number;
  net_conflict_change: number;
  affected_dates: string[];
}

export interface RosterCellLockItem {
  employee_id: string;
  date: string;
  is_locked?: boolean;
}

export type ImpactChangeType =
  | 'ADD_LEAVE'
  | 'REMOVE_LEAVE'
  | 'CELL_EDIT'
  | 'MARK_UNAVAILABLE';

export interface RosterImpactChangeItem {
  type: ImpactChangeType | string;
  employee_id?: string;
  start_date?: string;
  end_date?: string;
  date?: string;
  status?: RosterEntryStatus;
  brand_process_id?: string;
}

export interface RosterImpactConflictItem {
  code: string;
  severity: ConflictSeverity | string;
  brand_process_id?: string | null;
  brand?: string | null;
  process?: string | null;
  employee_id?: string | null;
  employee?: string | null;
  date?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  message: string;
  root_causes?: string[];
  suggestions?: Array<Record<string, unknown>>;
}

export interface RosterConflict {
  id: string;
  roster_period_id: string;
  code: string;
  severity: ConflictSeverity;
  brand_process_id?: string | null;
  employee_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  root_causes: string[];
  message: string;
  suggestions: Array<Record<string, unknown>>;
  is_acknowledged: boolean;
  acknowledged_by_id?: string | null;
  acknowledged_reason?: string | null;
  resolved_at?: string | null;
  brand_name?: string | null;
  brand_code?: string | null;
  process_name?: string | null;
  process_code?: string | null;
  employee_name?: string | null;
  employee_code?: string | null;
}

export interface SuggestionNetEffect {
  fixes: number;
  opens: number;
}

export interface RosterSuggestionItem {
  type: string;
  kind: string;
  action: string;
  description: string;
  employee_id?: string | null;
  employee_name?: string | null;
  employee_code?: string | null;
  brand_process_id?: string | null;
  brand_name?: string | null;
  process_name?: string | null;
  target_date?: string | null;
  source_date?: string | null;
  score: number;
  net_effect: SuggestionNetEffect;
  net_impact: string;
  apply_payload: {
    action?: string;
    employee_id?: string;
    brand_process_id?: string | null;
    date?: string;
    entries?: RosterEntryUpdateItem[];
    cell_edits?: RosterEntryUpdateItem[];
    [key: string]: unknown;
  };
}

export interface RosterAcknowledgeRequest {
  conflict_id: string;
  reason: string;
}

export const CONFLICT_CODE_INFO: Record<string, { label: string; meaning: string }> = {
  E001: { label: 'No Coverage', meaning: 'Required operating day with zero available employees assigned' },
  E002: { label: 'Under-Staffed', meaning: 'Coverage is below minimum required demand' },
  E003: { label: 'Weekly Off Conflict', meaning: 'Scheduled weekly off breaks minimum coverage requirement' },
  E004: { label: 'Leave Conflict', meaning: 'Scheduled leave or comp-off breaks minimum coverage requirement' },
  E005: { label: 'Max Work Streak', meaning: 'Run of consecutive work days exceeds maximum limit' },
  E006: { label: 'Missing Weekly Off', meaning: 'Fewer weekly offs than entitled in the calendar week' },
  E007: { label: 'Invalid Cell Status', meaning: 'Work on leave/comp-off day, or weekly off on non-eligible day' },
  E008: { label: 'Employee Overload', meaning: 'Employee assigned to more than max concurrent processes' },
  E009: { label: 'Comp-Off Balance', meaning: 'Redeemed comp-off days exceed accrued balance' },
  W001: { label: 'Preference Violated', meaning: 'Preferred off-day not honoured' },
  W002: { label: 'Unfair Distribution', meaning: 'Weekend-off distribution imbalance beyond threshold' },
  W003: { label: 'Single Point of Failure', meaning: 'Brand-process on operating days with single employee and no backup' },
};

export interface RosterImpactRequest {
  changes?: RosterImpactChangeItem[];
  edits?: RosterEntryUpdateItem[];
}

export interface RosterImpactResponse {
  is_feasible: boolean;
  new_conflicts: RosterImpactConflictItem[];
  resolved_conflicts: RosterImpactConflictItem[];
  unchanged_conflicts: RosterImpactConflictItem[];
  unchanged: number;
  net_conflict_change: number;
  affected_dates: string[];
}

export interface RosterRepairRequest {
  dates?: string[];
  date_from?: string | null;
  date_to?: string | null;
  employee_ids?: string[];
  brand_process_ids?: string[];
  conflict_id?: string | null;
  apply?: boolean;
  use_fallback?: boolean;
  time_limit_s?: number;
  seed?: number;
}

export interface RosterRepairResponse {
  is_feasible: boolean;
  repaired_cells_count: number;
  repaired_cells: Array<Record<string, unknown>>;
  new_conflicts: Array<Record<string, unknown>>;
  resolved_conflicts: Array<Record<string, unknown>>;
  unchanged_conflicts: Array<Record<string, unknown>>;
  net_conflict_change: number;
  solver_status: string;
  solve_time_seconds: number;
  applied: boolean;
  period?: RosterPeriod | null;
}

export interface RosterEntriesLockRequest {
  cells?: RosterCellLockItem[];
  employee_ids?: string[];
  dates?: string[];
  is_locked?: boolean;
}

export interface RosterEntriesLockResponse {
  roster_period_id: string;
  locked_count: number;
  unlocked_count: number;
}

export type RosterViewMode = 'company' | 'pod' | 'brand' | 'process' | 'employee';

export interface RosterDayEmployeeItem {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  assignment_type?: string | null;
  status: RosterEntryStatus;
  is_locked: boolean;
  note?: string | null;
}

export interface RosterDayBrandProcessGroup {
  brand_process_id: string;
  brand_name: string;
  process_name: string;
  required: number;
  actual: number;
  shortfall: number;
  is_operating_day: boolean;
  working_employees: RosterDayEmployeeItem[];
  off_employees: RosterDayEmployeeItem[];
}

export interface RosterDayViewResponse {
  period_id: string;
  date: string;
  groups: RosterDayBrandProcessGroup[];
  unassigned_working_employees: RosterDayEmployeeItem[];
}

/**
 * Mapping helpers between backend status names and display letter codes.
 */
export function mapStatusToCode(status: RosterEntryStatus): RosterStatusCode {
  switch (status) {
    case 'WORK':
      return 'W';
    case 'WEEKLY_OFF':
      return 'WO';
    case 'PUBLIC_HOLIDAY':
      return 'PH';
    case 'HOLIDAY_WORK':
      return 'HW';
    case 'LEAVE':
      return 'L';
    case 'COMP_OFF':
      return 'CO';
    default:
      return 'W';
  }
}

export function mapCodeToStatus(code: RosterStatusCode): RosterEntryStatus {
  switch (code) {
    case 'W':
      return 'WORK';
    case 'WO':
      return 'WEEKLY_OFF';
    case 'PH':
      return 'PUBLIC_HOLIDAY';
    case 'HW':
      return 'HOLIDAY_WORK';
    case 'L':
      return 'LEAVE';
    case 'CO':
      return 'COMP_OFF';
    default:
      return 'WORK';
  }
}

