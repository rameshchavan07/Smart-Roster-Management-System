import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  RosterPeriod,
  RosterGridViewResponse,
  RosterEntriesBatchUpdateRequest,
  RosterEntriesUpdateResponse,
  RosterEntriesLockRequest,
  RosterEntriesLockResponse,
  RosterCoverageCell,
  RosterDayViewResponse,
  RosterImpactRequest,
  RosterImpactResponse,
} from '../types/roster';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function getRosterPeriodsApi(month?: string): Promise<RosterPeriod[]> {
  const query = new URLSearchParams();
  if (month) query.set('month', month);
  const qs = query.toString();
  return apiClient<RosterPeriod[]>(`/rosters${qs ? `?${qs}` : ''}`);
}

export async function getRosterGridApi(
  periodId: string,
  view: string = 'company',
  refId?: string
): Promise<RosterGridViewResponse> {
  const query = new URLSearchParams();
  if (view) query.set('view', view);
  if (refId) query.set('ref_id', refId);
  const qs = query.toString();
  return apiClient<RosterGridViewResponse>(`/rosters/${periodId}/grid${qs ? `?${qs}` : ''}`);
}

export async function getRosterCoverageApi(
  periodId: string,
  brandProcessId?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<RosterCoverageCell[]> {
  const query = new URLSearchParams();
  if (brandProcessId) query.set('brand_process_id', brandProcessId);
  if (dateFrom) query.set('date_from', dateFrom);
  if (dateTo) query.set('date_to', dateTo);
  const qs = query.toString();
  return apiClient<RosterCoverageCell[]>(`/rosters/${periodId}/coverage${qs ? `?${qs}` : ''}`);
}

export async function getRosterDayViewApi(
  periodId: string,
  date?: string
): Promise<RosterDayViewResponse> {
  const query = new URLSearchParams();
  if (date) query.set('date', date);
  const qs = query.toString();
  return apiClient<RosterDayViewResponse>(`/rosters/${periodId}/day${qs ? `?${qs}` : ''}`);
}

export async function updateRosterEntriesApi(
  periodId: string,
  request: RosterEntriesBatchUpdateRequest
): Promise<RosterEntriesUpdateResponse> {
  return apiClient<RosterEntriesUpdateResponse>(`/rosters/${periodId}/entries`, {
    method: 'PUT',
    body: JSON.stringify(request),
  });
}

export async function simulateRosterImpactApi(
  periodId: string,
  request: RosterImpactRequest
): Promise<RosterImpactResponse> {
  return apiClient<RosterImpactResponse>(`/rosters/${periodId}/impact`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function lockRosterEntriesApi(
  periodId: string,
  request: RosterEntriesLockRequest
): Promise<RosterEntriesLockResponse> {
  return apiClient<RosterEntriesLockResponse>(`/rosters/${periodId}/entries/lock`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ----------------------------------------------------------------------------
// React Query Hooks
// ----------------------------------------------------------------------------

export function useRosterPeriodsQuery(month?: string) {
  return useQuery({
    queryKey: ['rosters', month],
    queryFn: () => getRosterPeriodsApi(month),
  });
}

export function useRosterGridQuery(
  periodId?: string,
  view: string = 'company',
  refId?: string
) {
  return useQuery({
    queryKey: ['roster-grid', periodId, view, refId],
    queryFn: () => {
      if (!periodId) throw new Error('periodId is required to fetch grid');
      return getRosterGridApi(periodId, view, refId);
    },
    enabled: Boolean(periodId),
  });
}

export function useRosterCoverageQuery(
  periodId?: string,
  brandProcessId?: string,
  dateFrom?: string,
  dateTo?: string
) {
  return useQuery({
    queryKey: ['roster-coverage', periodId, brandProcessId, dateFrom, dateTo],
    queryFn: () => {
      if (!periodId) throw new Error('periodId is required to fetch coverage');
      return getRosterCoverageApi(periodId, brandProcessId, dateFrom, dateTo);
    },
    enabled: Boolean(periodId),
  });
}

export function useRosterDayViewQuery(periodId?: string, date?: string) {
  return useQuery({
    queryKey: ['roster-day-view', periodId, date],
    queryFn: () => {
      if (!periodId) throw new Error('periodId is required to fetch day view');
      return getRosterDayViewApi(periodId, date);
    },
    enabled: Boolean(periodId && date),
  });
}

export function useUpdateRosterEntriesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request: RosterEntriesBatchUpdateRequest;
    }) => updateRosterEntriesApi(periodId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['roster-grid', variables.periodId] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useLockRosterEntriesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request: RosterEntriesLockRequest;
    }) => lockRosterEntriesApi(periodId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['roster-grid', variables.periodId] });
    },
  });
}

export function useRosterImpactMutation() {
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request: RosterImpactRequest;
    }) => simulateRosterImpactApi(periodId, request),
  });
}


