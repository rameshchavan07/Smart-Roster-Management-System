import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Leave,
  LeaveCreateInput,
  LeaveUpdateInput,
  LeaveStatus,
  CompOffEntry,
  CompOffRedeemInput,
} from '../types/leaves';
import type { PaginatedResult, CompOffBalance } from '../types/team';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function getLeavesApi(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
  status?: LeaveStatus;
}): Promise<PaginatedResult<Leave>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.status) query.set('status', params.status);

  const qs = query.toString();
  return apiClient<PaginatedResult<Leave>>(`/leaves${qs ? `?${qs}` : ''}`);
}

export async function getLeaveApi(id: string): Promise<Leave> {
  return apiClient<Leave>(`/leaves/${id}`);
}

export async function createLeaveApi(data: LeaveCreateInput): Promise<Leave> {
  return apiClient<Leave>('/leaves', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateLeaveApi(id: string, data: LeaveUpdateInput): Promise<Leave> {
  return apiClient<Leave>(`/leaves/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function approveLeaveApi(id: string): Promise<Leave> {
  return apiClient<Leave>(`/leaves/${id}/approve`, {
    method: 'POST',
  });
}

export async function rejectLeaveApi(id: string): Promise<Leave> {
  return apiClient<Leave>(`/leaves/${id}/reject`, {
    method: 'POST',
  });
}

export async function cancelLeaveApi(id: string): Promise<Leave> {
  return apiClient<Leave>(`/leaves/${id}/cancel`, {
    method: 'POST',
  });
}

export async function deleteLeaveApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/leaves/${id}`, {
    method: 'DELETE',
  });
}

export async function getCompOffLedgerApi(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
}): Promise<PaginatedResult<CompOffEntry>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.employee_id) query.set('employee_id', params.employee_id);

  const qs = query.toString();
  return apiClient<PaginatedResult<CompOffEntry>>(`/comp-offs${qs ? `?${qs}` : ''}`);
}

export async function getCompOffBalanceApi(employeeId: string): Promise<CompOffBalance> {
  return apiClient<CompOffBalance>(`/comp-offs/balance?employee_id=${employeeId}`);
}

export async function redeemCompOffApi(data: CompOffRedeemInput): Promise<CompOffEntry> {
  return apiClient<CompOffEntry>('/comp-offs/redeem', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useLeavesQuery(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
  status?: LeaveStatus;
}) {
  return useQuery({
    queryKey: ['leaves', params],
    queryFn: () => getLeavesApi(params),
  });
}

export function useLeaveQuery(id: string | null) {
  return useQuery({
    queryKey: ['leave', id],
    queryFn: () => (id ? getLeaveApi(id) : null),
    enabled: !!id,
  });
}

export function useCompOffLedgerQuery(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
}) {
  return useQuery({
    queryKey: ['comp-off-ledger', params],
    queryFn: () => getCompOffLedgerApi(params),
  });
}

export function useCompOffBalanceQuery(employeeId?: string) {
  return useQuery({
    queryKey: ['employee-comp-off', employeeId],
    queryFn: () => (employeeId ? getCompOffBalanceApi(employeeId) : null),
    enabled: Boolean(employeeId),
  });
}

export function useCreateLeaveMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLeaveApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['comp-off-ledger'] });
    },
  });
}

export function useApproveLeaveMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approveLeaveApi,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave', id] });
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-day-view'] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useRejectLeaveMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: rejectLeaveApi,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave', id] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useCancelLeaveMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelLeaveApi,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['leave', id] });
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-day-view'] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useRedeemCompOffMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: redeemCompOffApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      queryClient.invalidateQueries({ queryKey: ['comp-off-ledger'] });
      queryClient.invalidateQueries({ queryKey: ['employee-comp-off'] });
    },
  });
}

