import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Employee,
  EmployeeCreateInput,
  EmployeeUpdateInput,
  Pod,
  PodCreateInput,
  PodUpdateInput,
  CompOffBalance,
  Assignment,
  WeeklyOffRule,
  PaginatedResult,
} from '../types/team';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function getEmployeesApi(params?: {
  offset?: number;
  limit?: number;
  pod_id?: string;
  is_active?: boolean;
  is_floater?: boolean;
}): Promise<PaginatedResult<Employee>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.pod_id) query.set('pod_id', params.pod_id);
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
  if (params?.is_floater !== undefined) query.set('is_floater', String(params.is_floater));

  const qs = query.toString();
  return apiClient<PaginatedResult<Employee>>(`/employees${qs ? `?${qs}` : ''}`);
}

export async function getEmployeeApi(id: string): Promise<Employee> {
  return apiClient<Employee>(`/employees/${id}`);
}

export async function createEmployeeApi(data: EmployeeCreateInput): Promise<Employee> {
  return apiClient<Employee>('/employees', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateEmployeeApi(
  id: string,
  data: EmployeeUpdateInput
): Promise<Employee> {
  return apiClient<Employee>(`/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteEmployeeApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/employees/${id}`, {
    method: 'DELETE',
  });
}

export async function getEmployeeCompOffBalanceApi(id: string): Promise<CompOffBalance> {
  return apiClient<CompOffBalance>(`/employees/${id}/comp-off-balance`);
}

export async function getEmployeeAssignmentsApi(
  id: string
): Promise<PaginatedResult<Assignment>> {
  return apiClient<PaginatedResult<Assignment>>(`/assignments?employee_id=${id}`);
}

export async function getEmployeeWeeklyOffRulesApi(
  id: string
): Promise<PaginatedResult<WeeklyOffRule>> {
  return apiClient<PaginatedResult<WeeklyOffRule>>(`/weekly-off-rules?employee_id=${id}`);
}

export async function getPodsApi(params?: {
  offset?: number;
  limit?: number;
  is_active?: boolean;
}): Promise<PaginatedResult<Pod>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<Pod>>(`/pods${qs ? `?${qs}` : ''}`);
}

export async function getPodApi(id: string): Promise<Pod> {
  return apiClient<Pod>(`/pods/${id}`);
}

export async function createPodApi(data: PodCreateInput): Promise<Pod> {
  return apiClient<Pod>('/pods', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updatePodApi(id: string, data: PodUpdateInput): Promise<Pod> {
  return apiClient<Pod>(`/pods/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deletePodApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/pods/${id}`, {
    method: 'DELETE',
  });
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useEmployeesQuery(params?: {
  offset?: number;
  limit?: number;
  pod_id?: string;
  is_active?: boolean;
  is_floater?: boolean;
}) {
  return useQuery({
    queryKey: ['employees', params],
    queryFn: () => getEmployeesApi(params),
  });
}

export function useEmployeeQuery(id: string | null) {
  return useQuery({
    queryKey: ['employee', id],
    queryFn: () => (id ? getEmployeeApi(id) : null),
    enabled: !!id,
  });
}

export function useEmployeeCompOffBalanceQuery(id: string | null) {
  return useQuery({
    queryKey: ['employee-comp-off', id],
    queryFn: () => (id ? getEmployeeCompOffBalanceApi(id) : null),
    enabled: !!id,
  });
}

export function useEmployeeAssignmentsQuery(id: string | null) {
  return useQuery({
    queryKey: ['employee-assignments', id],
    queryFn: () => (id ? getEmployeeAssignmentsApi(id) : null),
    enabled: !!id,
  });
}

export function useEmployeeWeeklyOffRulesQuery(id: string | null) {
  return useQuery({
    queryKey: ['employee-weekly-off-rules', id],
    queryFn: () => (id ? getEmployeeWeeklyOffRulesApi(id) : null),
    enabled: !!id,
  });
}

export function usePodsQuery(params?: {
  offset?: number;
  limit?: number;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['pods', params],
    queryFn: () => getPodsApi(params),
  });
}

export function useCreateEmployeeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createEmployeeApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['pods'] });
    },
  });
}

export function useUpdateEmployeeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EmployeeUpdateInput }) =>
      updateEmployeeApi(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['employee', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['pods'] });
    },
  });
}

export function useDeleteEmployeeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteEmployeeApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['pods'] });
    },
  });
}

export function useCreatePodMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPodApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pods'] });
    },
  });
}

export function useUpdatePodMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PodUpdateInput }) =>
      updatePodApi(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pods'] });
      queryClient.invalidateQueries({ queryKey: ['pod', variables.id] });
    },
  });
}
