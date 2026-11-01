export type LeaveType = 'PLANNED' | 'UNPLANNED' | 'COMP_OFF';
export type LeaveStatus = 'REQUESTED' | 'APPROVED' | 'REJECTED' | 'CANCELLED';

export interface Leave {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  employee_code?: string | null;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  type: LeaveType;
  status: LeaveStatus;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveCreateInput {
  employee_id: string;
  start_date: string;
  end_date: string;
  type?: LeaveType;
  status?: LeaveStatus;
  note?: string | null;
}

export interface LeaveUpdateInput {
  start_date?: string;
  end_date?: string;
  type?: LeaveType;
  note?: string | null;
}

export type CompOffKind =
  | 'EARNED_HOLIDAY_WORK'
  | 'EARNED_MANUAL'
  | 'REDEEMED'
  | 'EXPIRED'
  | 'CANCELLED';

export interface CompOffEntry {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  employee_code?: string | null;
  entry_date: string;
  kind: CompOffKind;
  source_roster_entry_id: string | null;
  status: string;
  expires_on: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompOffRedeemInput {
  employee_id: string;
  date: string;
  note?: string | null;
}
