export interface CoverageRule {
  id: string;
  brand_process_id: string;
  brand_name?: string | null;
  process_name?: string | null;
  weekday: number | null; // 0=Mon, 6=Sun
  specific_date: string | null; // YYYY-MM-DD
  min_staff: number;
  reason: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CoverageRuleCreateInput {
  brand_process_id: string;
  weekday?: number | null;
  specific_date?: string | null;
  min_staff: number;
  reason?: string | null;
}

export interface CoverageRuleUpdateInput {
  weekday?: number | null;
  specific_date?: string | null;
  min_staff?: number | null;
  reason?: string | null;
  is_active?: boolean;
}

export interface Holiday {
  id: string;
  name: string;
  date: string; // YYYY-MM-DD
  brand_id: string | null;
  brand_name?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HolidayCreateInput {
  name: string;
  date: string;
  brand_id?: string | null;
}

export interface HolidayUpdateInput {
  name?: string;
  date?: string;
  brand_id?: string | null;
  is_active?: boolean;
}

