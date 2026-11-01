import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  CoverageRule,
  CoverageRuleCreateInput,
  CoverageRuleUpdateInput,
  Holiday,
  HolidayCreateInput,
  HolidayUpdateInput,
} from '../types/rules';
import type { PaginatedResult } from '../types/team';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function getCoverageRulesApi(params?: {
  offset?: number;
  limit?: number;
  brand_process_id?: string;
  is_active?: boolean;
}): Promise<PaginatedResult<CoverageRule>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.brand_process_id) query.set('brand_process_id', params.brand_process_id);
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<CoverageRule>>(`/coverage-rules${qs ? `?${qs}` : ''}`);
}

export async function getCoverageRuleApi(id: string): Promise<CoverageRule> {
  return apiClient<CoverageRule>(`/coverage-rules/${id}`);
}

export async function createCoverageRuleApi(
  data: CoverageRuleCreateInput
): Promise<CoverageRule> {
  return apiClient<CoverageRule>('/coverage-rules', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCoverageRuleApi(
  id: string,
  data: CoverageRuleUpdateInput
): Promise<CoverageRule> {
  return apiClient<CoverageRule>(`/coverage-rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCoverageRuleApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/coverage-rules/${id}`, {
    method: 'DELETE',
  });
}

export async function getHolidaysApi(params?: {
  offset?: number;
  limit?: number;
  brand_id?: string;
  year?: number;
  is_active?: boolean;
}): Promise<PaginatedResult<Holiday>> {
  const query = new URLSearchParams();
  if (params?.offset !== undefined) query.set('offset', String(params.offset));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.brand_id) query.set('brand_id', params.brand_id);
  if (params?.year !== undefined) query.set('year', String(params.year));
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));

  const qs = query.toString();
  return apiClient<PaginatedResult<Holiday>>(`/holidays${qs ? `?${qs}` : ''}`);
}

export async function createHolidayApi(data: HolidayCreateInput): Promise<Holiday> {
  return apiClient<Holiday>('/holidays', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateHolidayApi(
  id: string,
  data: HolidayUpdateInput
): Promise<Holiday> {
  return apiClient<Holiday>(`/holidays/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteHolidayApi(id: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/holidays/${id}`, {
    method: 'DELETE',
  });
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useCoverageRulesQuery(params?: {
  offset?: number;
  limit?: number;
  brand_process_id?: string;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['coverage-rules', params],
    queryFn: () => getCoverageRulesApi(params),
  });
}

export function useHolidaysQuery(params?: {
  offset?: number;
  limit?: number;
  brand_id?: string;
  year?: number;
  is_active?: boolean;
}) {
  return useQuery({
    queryKey: ['holidays', params],
    queryFn: () => getHolidaysApi(params),
  });
}

export function useCreateCoverageRuleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCoverageRuleApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coverage-rules'] });
    },
  });
}

export function useDeleteCoverageRuleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCoverageRuleApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coverage-rules'] });
    },
  });
}

export function useCreateHolidayMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createHolidayApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] });
    },
  });
}

export function useDeleteHolidayMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteHolidayApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holidays'] });
    },
  });
}
