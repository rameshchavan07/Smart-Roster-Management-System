export interface Employee {
  id: string;
  code: string;
  full_name: string;
  email: string | null;
  pod_id: string;
  pod_name?: string | null;
  is_floater: boolean;
  weekly_off_count: number;
  max_consecutive_days: number;
  max_concurrent_processes: number;
  joined_on: string | null;
  left_on: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreateInput {
  code: string;
  full_name: string;
  email?: string | null;
  pod_id: string;
  is_floater?: boolean;
  weekly_off_count?: number;
  max_consecutive_days?: number;
  max_concurrent_processes?: number;
  joined_on?: string | null;
}

export interface EmployeeUpdateInput {
  code?: string;
  full_name?: string;
  email?: string | null;
  pod_id?: string;
  is_floater?: boolean;
  weekly_off_count?: number;
  max_consecutive_days?: number;
  max_concurrent_processes?: number;
  joined_on?: string | null;
  left_on?: string | null;
  is_active?: boolean;
}

export interface Pod {
  id: string;
  name: string;
  lead_user_id: string | null;
  is_active: boolean;
  member_count?: number | null;
  created_at: string;
  updated_at: string;
}

export interface PodCreateInput {
  name: string;
  lead_user_id?: string | null;
}

export interface PodUpdateInput {
  name?: string;
  lead_user_id?: string | null;
  is_active?: boolean;
}

export interface CompOffBalance {
  employee_id: string;
  earned: number;
  redeemed: number;
  available: number;
}

export interface Assignment {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  employee_code?: string | null;
  brand_process_id: string;
  assignment_type: 'PRIMARY' | 'BACKUP';
  valid_from: string | null;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WeeklyOffRule {
  id: string;
  employee_id: string;
  mode: 'FIXED_MANDATORY' | 'FIXED_PREFERRED' | 'ROTATING' | 'FLEXIBLE';
  weekdays: number[];
  valid_from: string | null;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

