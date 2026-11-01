export interface AuditLog {
  id: string;
  user_id?: string | null;
  user_email?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogFilters {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  offset?: number;
  limit?: number;
}

