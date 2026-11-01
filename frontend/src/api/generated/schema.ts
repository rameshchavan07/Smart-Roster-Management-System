/**
 * Auto-generated TypeScript definitions from OpenAPI 3.1.0 specification.
 * Do not edit directly. Run `npm run generate-api` to regenerate.
 */

export interface AssignmentCreate {
  employee_id: string;
  brand_process_id: string;
  type?: AssignmentType;
  allocation_pct?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface AssignmentRead {
  employee_id: string;
  brand_process_id: string;
  type?: AssignmentType;
  allocation_pct?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
  id: string;
  created_at: string;
  updated_at: string;
  employee_name?: string | null;
  employee_code?: string | null;
}

/**
 * Staffing assignment types.
 */
export type AssignmentType = 'PRIMARY' | 'BACKUP';

export interface AssignmentUpdate {
  type?: AssignmentType | null;
  allocation_pct?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

/**
 * Read representation of an audit event.
 */
export interface AuditLogRead {
  id: string;
  user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  created_at: string;
  user_email?: string | null;
}

export interface BrandCreate {
  name: string;
  code: string;
  pod_id?: string | null;
}

export interface BrandProcessCreate {
  brand_id: string;
  process_id: string;
  calendar_type?: CalendarType;
  min_coverage_default?: number;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface BrandProcessRead {
  brand_id: string;
  process_id: string;
  calendar_type?: CalendarType;
  min_coverage_default?: number;
  valid_from?: string | null;
  valid_to?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  brand_name?: string | null;
  brand_code?: string | null;
  process_name?: string | null;
  process_code?: string | null;
}

export interface BrandProcessUpdate {
  calendar_type?: CalendarType | null;
  min_coverage_default?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
  is_active?: boolean | null;
}

export interface BrandRead {
  name: string;
  code: string;
  pod_id?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  pod_name?: string | null;
}

export interface BrandUpdate {
  name?: string | null;
  code?: string | null;
  pod_id?: string | null;
  is_active?: boolean | null;
}

/**
 * Brand operating calendar types.
 */
export type CalendarType = 'ALL_365' | 'ALL_EXCEPT_HOLIDAYS' | 'EXCLUDE_SUNDAY_AND_HOLIDAYS';

export interface CompOffBalanceRead {
  employee_id: string;
  earned: number;
  redeemed: number;
  available: number;
}

/**
 * Comp-off ledger transaction type.
 */
export type CompOffKind = 'EARNED' | 'REDEEMED';

export interface CompOffLedgerCreate {
  employee_id: string;
  entry_date: string;
  kind: CompOffKind;
  source_roster_entry_id?: string | null;
  status?: string;
  expires_on?: string | null;
  note?: string | null;
}

export interface CompOffLedgerRead {
  employee_id: string;
  entry_date: string;
  kind: CompOffKind;
  source_roster_entry_id?: string | null;
  status?: string;
  expires_on?: string | null;
  note?: string | null;
  id: string;
  created_at: string;
  updated_at: string;
}

export interface CompOffRedeemRequest {
  employee_id: string;
  date: string;
  note?: string | null;
}

/**
 * Validation conflict severity classification.
 */
export type ConflictSeverity = 'BLOCKING' | 'WARNING' | 'INFO';

export interface CoverageRuleCreate {
  brand_process_id: string;
  weekday?: number | null;
  specific_date?: string | null;
  min_staff?: number;
  reason?: string | null;
}

export interface CoverageRuleRead {
  brand_process_id: string;
  weekday?: number | null;
  specific_date?: string | null;
  min_staff?: number;
  reason?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CoverageRuleUpdate {
  weekday?: number | null;
  specific_date?: string | null;
  min_staff?: number | null;
  reason?: string | null;
  is_active?: boolean | null;
}

/**
 * Documented demo credentials for evaluators conforming to SAMPLE_DATA.md §8.
 */
export interface DemoAccountRead {
  role: UserRole;
  email: string;
  description: string;
  employee_code?: string | null;
  employee_name?: string | null;
  default_password?: string | null;
}

export interface EmployeeCreate {
  code: string;
  full_name: string;
  email?: string | null;
  pod_id: string;
  is_floater?: boolean;
  weekly_off_count?: number;
  max_consecutive_days?: number;
  max_concurrent_processes?: number;
  joined_on?: string | null;
  left_on?: string | null;
}

export interface EmployeePreferenceCreate {
  employee_id: string;
  kind: PreferenceKind;
  value?: Record<string, unknown>;
  weight?: number;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface EmployeePreferenceRead {
  employee_id: string;
  kind: PreferenceKind;
  value?: Record<string, unknown>;
  weight?: number;
  valid_from?: string | null;
  valid_to?: string | null;
  id: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeePreferenceUpdate {
  kind?: PreferenceKind | null;
  value?: Record<string, unknown> | null;
  weight?: number | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface EmployeeRead {
  code: string;
  full_name: string;
  email?: string | null;
  pod_id: string;
  is_floater?: boolean;
  weekly_off_count?: number;
  max_consecutive_days?: number;
  max_concurrent_processes?: number;
  joined_on?: string | null;
  left_on?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  pod_name?: string | null;
}

export interface EmployeeUpdate {
  code?: string | null;
  full_name?: string | null;
  email?: string | null;
  pod_id?: string | null;
  is_floater?: boolean | null;
  weekly_off_count?: number | null;
  max_consecutive_days?: number | null;
  max_concurrent_processes?: number | null;
  joined_on?: string | null;
  left_on?: string | null;
  is_active?: boolean | null;
}

/**
 * Origin of a roster assignment.
 */
export type EntrySource = 'AUTO' | 'MANUAL' | 'LOCKED_FIXED';

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HolidayCreate {
  date: string;
  name: string;
  brand_id?: string | null;
}

export interface HolidayRead {
  date: string;
  name: string;
  brand_id?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  brand_name?: string | null;
}

export interface HolidayUpdate {
  date?: string | null;
  name?: string | null;
  brand_id?: string | null;
  is_active?: boolean | null;
}

/**
 * Change kinds accepted by what-if impact analysis.
 */
export type ImpactChangeType = 'ADD_LEAVE' | 'REMOVE_LEAVE' | 'CELL_EDIT' | 'MARK_UNAVAILABLE';

export interface LeaveCreate {
  employee_id: string;
  start_date: string;
  end_date: string;
  type?: LeaveType;
  note?: string | null;
  status?: LeaveStatus;
}

export interface LeaveRead {
  employee_id: string;
  start_date: string;
  end_date: string;
  type?: LeaveType;
  note?: string | null;
  id: string;
  status: LeaveStatus;
  created_at: string;
  updated_at: string;
  employee_name?: string | null;
  employee_code?: string | null;
}

/**
 * Leave approval workflow status.
 */
export type LeaveStatus = 'REQUESTED' | 'APPROVED' | 'REJECTED' | 'CANCELLED';

/**
 * Employee leave classification.
 */
export type LeaveType = 'PLANNED' | 'SICK' | 'UNPAID' | 'COMP_OFF';

export interface LeaveUpdate {
  start_date?: string | null;
  end_date?: string | null;
  type?: LeaveType | null;
  note?: string | null;
}

/**
 * Generic message response.
 */
export interface MessageResponse {
  message: string;
  detail?: string | null;
}

export interface PaginatedResponse_AssignmentRead_ {
  items: AssignmentRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_AuditLogRead_ {
  items: AuditLogRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_BrandProcessRead_ {
  items: BrandProcessRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_BrandRead_ {
  items: BrandRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_CompOffLedgerRead_ {
  items: CompOffLedgerRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_CoverageRuleRead_ {
  items: CoverageRuleRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_EmployeePreferenceRead_ {
  items: EmployeePreferenceRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_EmployeeRead_ {
  items: EmployeeRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_HolidayRead_ {
  items: HolidayRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_LeaveRead_ {
  items: LeaveRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_PodRead_ {
  items: PodRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_ProcessRead_ {
  items: ProcessRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse_WeeklyOffRuleRead_ {
  items: WeeklyOffRuleRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface PodCreate {
  name: string;
  lead_employee_id?: string | null;
}

export interface PodRead {
  name: string;
  id: string;
  lead_employee_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  member_count?: number | null;
}

export interface PodUpdate {
  name?: string | null;
  lead_employee_id?: string | null;
  is_active?: boolean | null;
}

/**
 * Employee preference categories.
 */
export type PreferenceKind = 'PREFERRED_OFF_WEEKDAY' | 'PREFERRED_OFF_DATE' | 'AVOID_WEEKEND_WORK';

export interface ProcessCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface ProcessRead {
  name: string;
  code: string;
  description?: string | null;
  id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProcessUpdate {
  name?: string | null;
  code?: string | null;
  description?: string | null;
  is_active?: boolean | null;
}

/**
 * Refresh token submitted to /auth/refresh.
 */
export interface RefreshTokenRequest {
  refresh_token?: string | null;
}

/**
 * Acknowledge a BLOCKING conflict with required reason.
 */
export interface RosterAcknowledgeRequest {
  conflict_id: string;
  reason: string;
}

/**
 * Difference in cell assignment between two roster versions.
 */
export interface RosterCellDiffItem {
  employee_id: string;
  employee_code: string;
  employee_name: string;
  date: string;
  status_a?: RosterEntryStatus | null;
  status_b?: RosterEntryStatus | null;
}

/**
 * Single cell lock specification.
 */
export interface RosterCellLockItem {
  employee_id: string;
  date: string;
  is_locked?: boolean;
}

/**
 * Clone a roster period into a new working version.
 */
export interface RosterCloneRequest {
  parent_period_id?: string | null;
  note?: string | null;
}

/**
 * Summary deltas comparing version B relative to version A (B - A).
 */
export interface RosterCompareDelta {
  blocking_delta: number;
  warnings_delta: number;
  coverage_pct_delta: number;
  fairness_spread_delta: number;
  total_cells_changed: number;
}

/**
 * Side-by-side comparison of two roster periods.
 */
export interface RosterCompareResponse {
  period_a: RosterPeriodRead;
  period_b: RosterPeriodRead;
  metrics_a: RosterVersionMetrics;
  metrics_b: RosterVersionMetrics;
  delta: RosterCompareDelta;
  conflict_diff?: Record<string, Record<string, unknown>[]>;
  cell_diffs?: RosterCellDiffItem[];
}

/**
 * Validation conflict representation.
 */
export interface RosterConflictRead {
  id: string;
  roster_period_id: string;
  code: string;
  severity: ConflictSeverity;
  brand_process_id?: string | null;
  employee_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  root_causes?: string[];
  message: string;
  suggestions?: Record<string, unknown>[];
  is_acknowledged?: boolean;
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

/**
 * Coverage demand vs actual staffing cell.
 */
export interface RosterCoverageCell {
  date: string;
  brand_process_id: string;
  brand_name?: string | null;
  process_name?: string | null;
  required: number;
  actual: number;
  shortfall: number;
}

/**
 * Staffing and coverage state for a brand-process on a specific date.
 */
export interface RosterDayBrandProcessGroup {
  brand_process_id: string;
  brand_name: string;
  process_name: string;
  required: number;
  actual: number;
  shortfall: number;
  is_operating_day?: boolean;
  working_employees?: RosterDayEmployeeItem[];
  off_employees?: RosterDayEmployeeItem[];
}

/**
 * Employee representation in daily view.
 */
export interface RosterDayEmployeeItem {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  assignment_type?: string | null;
  status: RosterEntryStatus;
  is_locked?: boolean;
  note?: string | null;
}

/**
 * Who is working on a date, grouped by brand-process with coverage state.
 */
export interface RosterDayViewResponse {
  period_id: string;
  date: string;
  groups: RosterDayBrandProcessGroup[];
  unassigned_working_employees?: RosterDayEmployeeItem[];
}

/**
 * Batch cell edit request.
 */
export interface RosterEntriesBatchUpdateRequest {
  entries: RosterEntryUpdateItem[];
  acknowledge_blocking?: boolean;
}

/**
 * Lock or unlock schedule cells.
 */
export interface RosterEntriesLockRequest {
  cells?: RosterCellLockItem[];
  employee_ids?: string[];
  dates?: string[];
  is_locked?: boolean;
}

/**
 * Result of locking/unlocking cells.
 */
export interface RosterEntriesLockResponse {
  roster_period_id: string;
  version: number;
  locked_count: number;
  unlocked_count: number;
  updated_entries?: RosterEntryRead[];
}

/**
 * Result of applying cell updates, including conflict diffs.
 */
export interface RosterEntriesUpdateResponse {
  roster_period_id: string;
  version: number;
  status: RosterPeriodStatus;
  updated_entries: RosterEntryRead[];
  new_conflicts?: Record<string, unknown>[];
  resolved_conflicts?: Record<string, unknown>[];
  unchanged_conflicts?: Record<string, unknown>[];
  unchanged?: number;
  net_conflict_change?: number;
  affected_dates?: string[];
}

/**
 * Daily schedule cell for an employee.
 */
export interface RosterEntryRead {
  id: string;
  roster_period_id: string;
  employee_id: string;
  date: string;
  shift_id?: string | null;
  status: RosterEntryStatus;
  source: EntrySource;
  is_locked: boolean;
  note?: string | null;
}

/**
 * Daily operational status assigned to an employee.
 */
export type RosterEntryStatus = 'WORK' | 'WEEKLY_OFF' | 'HOLIDAY_OFF' | 'HOLIDAY_WORK' | 'LEAVE' | 'COMP_OFF';

/**
 * Single cell change payload.
 */
export interface RosterEntryUpdateItem {
  employee_id: string;
  date: string;
  status: RosterEntryStatus;
  source?: EntrySource;
  is_locked?: boolean | null;
  note?: string | null;
  reason?: string | null;
}

/**
 * Execution options for the scheduling solver.
 */
export interface RosterGenerateOptions {
  seed?: number;
  time_limit_s?: number;
  base_roster_id?: string | null;
  use_fallback?: boolean;
}

/**
 * Payload to trigger monthly roster generation.
 */
export interface RosterGenerateRequest {
  month: string;
  pod_id?: string | null;
  options?: RosterGenerateOptions | null;
  seed?: number | null;
  time_limit_s?: number | null;
  weights?: Record<string, number> | null;
}

/**
 * Response returned upon roster creation and generation.
 */
export interface RosterGenerateResponse {
  id: string;
  month: string;
  version: number;
  status: RosterPeriodStatus;
  solver_status?: string | null;
  summary: RosterSummary;
  created_at: string;
}

/**
 * Single cell rendered in the frontend matrix.
 */
export interface RosterGridCell {
  date: string;
  status: RosterEntryStatus;
  source: EntrySource;
  is_locked: boolean;
  note?: string | null;
  conflicts?: string[];
}

/**
 * Row in the roster grid corresponding to an employee.
 */
export interface RosterGridRow {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  pod_name?: string | null;
  primary_assignments?: string[];
  cells: Record<string, RosterGridCell>;
}

/**
 * Complete grid payload for Company, Pod, Brand, Process, or Employee view.
 */
export interface RosterGridViewResponse {
  period: RosterPeriodRead;
  view: string;
  start_date: string;
  end_date: string;
  rows: RosterGridRow[];
}

/**
 * Single proposed modification to simulate.
 */
export interface RosterImpactChangeItem {
  type: ImpactChangeType | string;
  employee_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  date?: string | null;
  status?: RosterEntryStatus | null;
  brand_process_id?: string | null;
}

/**
 * Simulate cell changes or leave additions without committing to database.
 */
export interface RosterImpactRequest {
  changes?: RosterImpactChangeItem[];
  edits?: RosterEntryUpdateItem[];
}

/**
 * Simulation diff output.
 */
export interface RosterImpactResponse {
  is_feasible: boolean;
  new_conflicts?: Record<string, unknown>[];
  resolved_conflicts?: Record<string, unknown>[];
  unchanged_conflicts?: Record<string, unknown>[];
  unchanged?: number;
  net_conflict_change?: number;
  affected_dates?: string[];
}

/**
 * Metadata for a roster version.
 */
export interface RosterPeriodRead {
  id: string;
  month: string;
  version: number;
  status: RosterPeriodStatus;
  solver_status?: string | null;
  generation_params?: Record<string, unknown>;
  parent_period_id?: string | null;
  is_stale?: boolean;
  created_by_id?: string | null;
  published_at?: string | null;
  created_at: string;
  entries_count?: number | null;
  conflicts_count?: number | null;
}

/**
 * Lifecycle state of a roster period.
 */
export type RosterPeriodStatus = 'GENERATING' | 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

/**
 * Request for local repair around an impacted window.
 */
export interface RosterRepairRequest {
  dates?: string[];
  date_from?: string | null;
  date_to?: string | null;
  employee_ids?: string[];
  brand_process_ids?: string[];
  conflict_id?: string | null;
  apply?: boolean;
  use_fallback?: boolean;
}

/**
 * Result of local repair diffing changes and conflicts.
 */
export interface RosterRepairResponse {
  is_feasible: boolean;
  repaired_cells_count: number;
  repaired_cells?: RosterEntryRead[];
  new_conflicts?: Record<string, unknown>[];
  resolved_conflicts?: Record<string, unknown>[];
  unchanged_conflicts?: Record<string, unknown>[];
  net_conflict_change: number;
  solver_status: string;
  solve_time_seconds: number;
  applied: boolean;
  period?: RosterPeriodRead | null;
}

/**
 * Ranked actionable resolution for a roster gap.
 */
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
  score?: number;
  net_effect?: SuggestionNetEffect;
  net_impact?: string;
  apply_payload?: Record<string, unknown>;
}

/**
 * Validation conflict and coverage summary metrics.
 */
export interface RosterSummary {
  blocking?: number;
  warnings?: number;
  info?: number;
  coverage_pct?: number;
}

/**
 * Side-by-side quality and fairness metrics for a single roster version.
 */
export interface RosterVersionMetrics {
  period_id: string;
  version: number;
  status: RosterPeriodStatus;
  month: string;
  blocking_conflicts: number;
  warning_conflicts: number;
  info_conflicts: number;
  total_conflicts: number;
  coverage_pct: number;
  total_shortfall: number;
  shortfall_slots_count: number;
  fairness_spread: number;
  min_weekend_offs: number;
  max_weekend_offs: number;
  weekend_offs_by_employee?: Record<string, number>;
}

/**
 * Impact of applying suggestion on total gaps.
 */
export interface SuggestionNetEffect {
  fixes?: number;
  opens?: number;
}

/**
 * Token response conforming to API_DOCUMENTATION.md §1.
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in?: number;
  user: UserRead;
}

/**
 * Credentials submitted on /auth/login.
 */
export interface UserLoginRequest {
  email: string;
  password: string;
}

/**
 * User account details returned in auth responses.
 */
export interface UserRead {
  id: string;
  email: string;
  role: UserRole;
  employee_id?: string | null;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
}

/**
 * RBAC role tiers per SECURITY.md §2.
 */
export type UserRole = 'OPS_MANAGER' | 'POD_LEAD' | 'EMPLOYEE';

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

/**
 * Weekly off scheduling policy.
 */
export type WeeklyOffMode = 'FIXED_MANDATORY' | 'FIXED_PREFERRED' | 'ROTATING' | 'ANY';

export interface WeeklyOffRuleCreate {
  employee_id: string;
  mode?: WeeklyOffMode;
  weekdays?: number[];
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface WeeklyOffRuleRead {
  employee_id: string;
  mode?: WeeklyOffMode;
  weekdays?: number[];
  valid_from?: string | null;
  valid_to?: string | null;
  id: string;
  created_at: string;
  updated_at: string;
}

export interface WeeklyOffRuleUpdate {
  mode?: WeeklyOffMode | null;
  weekdays?: number[] | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

// Convenient domain aliases
export type LoginRequest = UserLoginRequest;
export type PodListResponse = PaginatedResponse_PodRead_;
export type EmployeeListResponse = PaginatedResponse_EmployeeRead_;
export type ProcessListResponse = PaginatedResponse_ProcessRead_;
export type BrandListResponse = PaginatedResponse_BrandRead_;
export type BrandProcessListResponse = PaginatedResponse_BrandProcessRead_;
export type AssignmentListResponse = PaginatedResponse_AssignmentRead_;
export type CoverageRuleListResponse = PaginatedResponse_CoverageRuleRead_;
export type HolidayListResponse = PaginatedResponse_HolidayRead_;
export type WeeklyOffRuleListResponse = PaginatedResponse_WeeklyOffRuleRead_;
export type EmployeePreferenceListResponse = PaginatedResponse_EmployeePreferenceRead_;
export type LeaveListResponse = PaginatedResponse_LeaveRead_;
export type CompOffLedgerListResponse = PaginatedResponse_CompOffLedgerRead_;
export type AuditLogListResponse = PaginatedResponse_AuditLogRead_;
export type RosterSuggestionRead = RosterSuggestionItem;
