import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Brand,
  BrandCreateInput,
  BrandUpdateInput,
  Process,
  ProcessCreateInput,
  ProcessUpdateInput,
  BrandProcess,
  BrandProcessCreateInput,
  BrandProcessUpdateInput,
  AssignmentCreateInput,
  AssignmentUpdateInput,
} from '../types/brands';
import type { Assignment, PaginatedResult } from '../types/team';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function getBrandsApi(params?: {
  offset?: number;
  limit?: number;
  pod_id?: string;
  is_active?: boolean;
}): Promise<PaginatedResult<Brand>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.pod_id) query.set('pod_id', params.pod_id);
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<Brand>>(`/brands${qs ? `?${qs}` : ''}`);
}

export async function getBrandApi(id: string): Promise<Brand> {
  return apiClient<Brand>(`/brands/${id}`);
}

export async function createBrandApi(data: BrandCreateInput): Promise<Brand> {
  return apiClient<Brand>('/brands', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBrandApi(id: string, data: BrandUpdateInput): Promise<Brand> {
  return apiClient<Brand>(`/brands/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBrandApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/brands/${id}`, {
    method: 'DELETE',
  });
}

export async function getProcessesApi(params?: {
  offset?: number;
  limit?: number;
  is_active?: boolean;
}): Promise<PaginatedResult<Process>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<Process>>(`/processes${qs ? `?${qs}` : ''}`);
}

export async function createProcessApi(data: ProcessCreateInput): Promise<Process> {
  return apiClient<Process>('/processes', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProcessApi(id: string, data: ProcessUpdateInput): Promise<Process> {
  return apiClient<Process>(`/processes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getBrandProcessesApi(params?: {
  offset?: number;
  limit?: number;
  brand_id?: string;
  process_id?: string;
  is_active?: boolean;
}): Promise<PaginatedResult<BrandProcess>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.brand_id) query.set('brand_id', params.brand_id);
  if (params?.process_id) query.set('process_id', params.process_id);
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<BrandProcess>>(`/brand-processes${qs ? `?${qs}` : ''}`);
}

export async function createBrandProcessApi(
  data: BrandProcessCreateInput
): Promise<BrandProcess> {
  return apiClient<BrandProcess>('/brand-processes', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBrandProcessApi(
  id: string,
  data: BrandProcessUpdateInput
): Promise<BrandProcess> {
  return apiClient<BrandProcess>(`/brand-processes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBrandProcessApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/brand-processes/${id}`, {
    method: 'DELETE',
  });
}

export async function getAssignmentsApi(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
  brand_process_id?: string;
}): Promise<PaginatedResult<Assignment>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.brand_process_id) query.set('brand_process_id', params.brand_process_id);

  const qs = query.toString();
  return apiClient<PaginatedResult<Assignment>>(`/assignments${qs ? `?${qs}` : ''}`);
}

export async function createAssignmentApi(data: AssignmentCreateInput): Promise<Assignment> {
  return apiClient<Assignment>('/assignments', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateAssignmentApi(
  id: string,
  data: AssignmentUpdateInput
): Promise<Assignment> {
  return apiClient<Assignment>(`/assignments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteAssignmentApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/assignments/${id}`, {
    method: 'DELETE',
  });
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useBrandsQuery(params?: {
  offset?: number;
  limit?: number;
  pod_id?: string;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['brands', params],
    queryFn: () => getBrandsApi(params),
  });
}

export function useBrandQuery(id: string | null) {
  return useQuery({
    queryKey: ['brand', id],
    queryFn: () => (id ? getBrandApi(id) : null),
    enabled: !!id,
  });
}

export function useProcessesQuery(params?: {
  offset?: number;
  limit?: number;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['processes', params],
    queryFn: () => getProcessesApi(params),
  });
}

export function useBrandProcessesQuery(params?: {
  offset?: number;
  limit?: number;
  brand_id?: string;
  process_id?: string;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['brand-processes', params],
    queryFn: () => getBrandProcessesApi(params),
  });
}

export function useAssignmentsQuery(params?: {
  offset?: number;
  limit?: number;
  employee_id?: string;
  brand_process_id?: string;
}) {
  return useQuery({
    queryKey: ['assignments', params],
    queryFn: () => getAssignmentsApi(params),
  });
}

export function useCreateBrandMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBrandApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });
}

export function useUpdateBrandMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BrandUpdateInput }) =>
      updateBrandApi(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      queryClient.invalidateQueries({ queryKey: ['brand', variables.id] });
    },
  });
}

export function useCreateBrandProcessMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBrandProcessApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brand-processes'] });
    },
  });
}

export function useUpdateBrandProcessMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BrandProcessUpdateInput }) =>
      updateBrandProcessApi(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brand-processes'] });
    },
  });
}

export function useDeleteBrandProcessMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBrandProcessApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brand-processes'] });
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
    },
  });
}

export function useCreateAssignmentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAssignmentApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
    },
  });
}

export function useDeleteAssignmentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteAssignmentApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
    },
  });
}

