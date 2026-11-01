export type CalendarType =
  | 'ALL_365'
  | 'SIX_DAYS_MON_SAT'
  | 'SIX_DAYS_TUE_SUN'
  | 'FIVE_DAYS_MON_FRI'
  | 'FOUR_DAYS_CUSTOM'
  | 'SEASONAL_CUSTOM';

export interface Brand {
  id: string;
  name: string;
  code: string;
  pod_id: string | null;
  pod_name?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrandCreateInput {
  name: string;
  code: string;
  pod_id?: string | null;
}

export interface BrandUpdateInput {
  name?: string;
  code?: string;
  pod_id?: string | null;
  is_active?: boolean;
}

export interface Process {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProcessCreateInput {
  name: string;
  code: string;
  description?: string | null;
}

export interface ProcessUpdateInput {
  name?: string;
  code?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface BrandProcess {
  id: string;
  brand_id: string;
  brand_name?: string | null;
  brand_code?: string | null;
  process_id: string;
  process_name?: string | null;
  process_code?: string | null;
  calendar_type: CalendarType;
  min_coverage_default: number;
  valid_from: string | null;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrandProcessCreateInput {
  brand_id: string;
  process_id: string;
  calendar_type?: CalendarType;
  min_coverage_default?: number;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface BrandProcessUpdateInput {
  calendar_type?: CalendarType;
  min_coverage_default?: number;
  valid_from?: string | null;
  valid_to?: string | null;
  is_active?: boolean;
}

export interface AssignmentCreateInput {
  employee_id: string;
  brand_process_id: string;
  assignment_type: 'PRIMARY' | 'BACKUP';
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface AssignmentUpdateInput {
  assignment_type?: 'PRIMARY' | 'BACKUP';
  valid_from?: string | null;
  valid_to?: string | null;
  is_active?: boolean;
}
