import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { AuditLog, AuditLogFilters } from '../types/audit';
import type { PaginatedResult } from '../types/team';

export async function getAuditLogsApi(
  filters?: AuditLogFilters
): Promise<PaginatedResult<AuditLog>> {
  const query = new URLSearchParams();
  if (filters?.action) query.set('action', filters.action);
  if (filters?.entity_type) query.set('entity_type', filters.entity_type);
  if (filters?.entity_id) query.set('entity_id', filters.entity_id);
  if (filters?.user_id) query.set('user_id', filters.user_id);
  if (filters?.date_from) query.set('date_from', filters.date_from);
  if (filters?.date_to) query.set('date_to', filters.date_to);
  if (filters?.offset !== undefined) query.set('offset', String(filters.offset));
  if (filters?.limit !== undefined) query.set('limit', String(filters.limit));

  const qs = query.toString();
  return apiClient<PaginatedResult<AuditLog>>(`/audit-logs${qs ? `?${qs}` : ''}`);
}

export function useAuditLogsQuery(filters?: AuditLogFilters) {
  return useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: () => getAuditLogsApi(filters),
  });
}

