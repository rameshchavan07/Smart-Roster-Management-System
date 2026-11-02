import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, apiClientBlob } from './client';
import type {
  RosterPeriod,
  RosterGenerateRequest,
  RosterGenerateResponse,
  RosterCloneRequest,
  RosterGridViewResponse,
  RosterEntriesBatchUpdateRequest,
  RosterEntryUpdateItem,
  RosterEntriesUpdateResponse,
  RosterEntriesLockRequest,
  RosterEntriesLockResponse,
  RosterCoverageCell,
  RosterDayViewResponse,
  RosterImpactRequest,
  RosterImpactResponse,
  RosterConflict,
  RosterSuggestionItem,
  RosterAcknowledgeRequest,
  RosterRepairRequest,
  RosterRepairResponse,
  RosterCompareResponse,
} from '../types/roster';

// ----------------------------------------------------------------------------
// API Fetchers
// ----------------------------------------------------------------------------

export async function generateRosterApi(
  request: RosterGenerateRequest
): Promise<RosterGenerateResponse> {
  return apiClient<RosterGenerateResponse>('/rosters', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getRosterPeriodsApi(month?: string): Promise<RosterPeriod[]> {
  const query = new URLSearchParams();
  if (month) query.set('month', month);
  const qs = query.toString();
  return apiClient<RosterPeriod[]>(`/rosters${qs ? `?${qs}` : ''}`);
}

export async function publishRosterApi(periodId: string): Promise<RosterPeriod> {
  return apiClient<RosterPeriod>(`/rosters/${periodId}/publish`, {
    method: 'POST',
  });
}

export async function cloneRosterApi(
  periodId: string,
  request?: RosterCloneRequest
): Promise<RosterPeriod> {
  return apiClient<RosterPeriod>(`/rosters/${periodId}/clone`, {
    method: 'POST',
    body: request ? JSON.stringify(request) : JSON.stringify({}),
  });
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

export async function getRosterConflictsApi(
  periodId: string,
  params?: {
    severity?: string;
    brand_id?: string;
    date?: string;
    employee_id?: string;
  }
): Promise<RosterConflict[]> {
  const query = new URLSearchParams();
  if (params?.severity) query.set('severity', params.severity);
  if (params?.brand_id) query.set('brand_id', params.brand_id);
  if (params?.date) query.set('date', params.date);
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  const qs = query.toString();
  return apiClient<RosterConflict[]>(`/rosters/${periodId}/conflicts${qs ? `?${qs}` : ''}`);
}

export async function getRosterSuggestionsApi(
  periodId: string,
  params?: {
    conflict_id?: string;
    brand_process_id?: string;
    date?: string;
  }
): Promise<RosterSuggestionItem[]> {
  const query = new URLSearchParams();
  if (params?.conflict_id) query.set('conflict_id', params.conflict_id);
  if (params?.brand_process_id) query.set('brand_process_id', params.brand_process_id);
  if (params?.date) query.set('date', params.date);
  const qs = query.toString();
  return apiClient<RosterSuggestionItem[]>(`/rosters/${periodId}/suggestions${qs ? `?${qs}` : ''}`);
}

export async function acknowledgeRosterConflictApi(
  periodId: string,
  request: RosterAcknowledgeRequest
): Promise<RosterConflict> {
  return apiClient<RosterConflict>(`/rosters/${periodId}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function repairRosterApi(
  periodId: string,
  request: RosterRepairRequest
): Promise<RosterRepairResponse> {
  return apiClient<RosterRepairResponse>(`/rosters/${periodId}/repair`, {
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
      if (!periodId) return null;
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
      if (!periodId) return [];
      return getRosterCoverageApi(periodId, brandProcessId, dateFrom, dateTo);
    },
    enabled: Boolean(periodId),
  });
}

export function useRosterDayViewQuery(periodId?: string, date?: string) {
  return useQuery({
    queryKey: ['roster-day-view', periodId, date],
    queryFn: () => {
      if (!periodId || !date) return null;
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
    onMutate: async ({ request }) => {
      // 1. Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ['roster-grid'] });

      // 2. Snapshot previous grid state
      const previousGrids = queryClient.getQueriesData<RosterGridViewResponse>({
        queryKey: ['roster-grid'],
      });

      // 3. Build lookup of pending entry updates
      const updateMap = new Map<string, RosterEntryUpdateItem>();
      if (request.entries) {
        for (const entry of request.entries) {
          updateMap.set(`${entry.employee_id}:${entry.date}`, entry);
        }
      }

      // 4. Optimistically update all matching grid caches
      queryClient.setQueriesData<RosterGridViewResponse>(
        { queryKey: ['roster-grid'] },
        (old) => {
          if (!old || !old.rows) return old;
          return {
            ...old,
            rows: old.rows.map((row) => {
              let modified = false;
              const newCells = { ...row.cells };
              for (const [date, cell] of Object.entries(row.cells)) {
                const key = `${row.employee_id}:${date}`;
                const upd = updateMap.get(key);
                if (upd) {
                  modified = true;
                  newCells[date] = {
                    ...cell,
                    status: upd.status,
                    source: 'MANUAL',
                    is_locked: typeof upd.is_locked === 'boolean' ? upd.is_locked : cell.is_locked,
                    note: upd.reason !== undefined ? upd.reason : cell.note,
                  };
                }
              }
              return modified ? { ...row, cells: newCells } : row;
            }),
          };
        }
      );

      return { previousGrids };
    },
    onError: (_err, _variables, context) => {
      // Rollback to previous state
      if (context?.previousGrids) {
        for (const [queryKey, data] of context.previousGrids) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-day-view'] });
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
    onMutate: async ({ request }) => {
      await queryClient.cancelQueries({ queryKey: ['roster-grid'] });
      const previousGrids = queryClient.getQueriesData<RosterGridViewResponse>({
        queryKey: ['roster-grid'],
      });

      const lockMap = new Map<string, boolean>();
      if (request.cells) {
        for (const item of request.cells) {
          lockMap.set(`${item.employee_id}:${item.date}`, item.is_locked ?? true);
        }
      }

      queryClient.setQueriesData<RosterGridViewResponse>(
        { queryKey: ['roster-grid'] },
        (old) => {
          if (!old || !old.rows) return old;
          return {
            ...old,
            rows: old.rows.map((row) => {
              let modified = false;
              const newCells = { ...row.cells };
              for (const [date, cell] of Object.entries(row.cells)) {
                const key = `${row.employee_id}:${date}`;
                const lockedState = lockMap.get(key);
                if (lockedState !== undefined) {
                  modified = true;
                  newCells[date] = {
                    ...cell,
                    is_locked: lockedState,
                  };
                }
              }
              return modified ? { ...row, cells: newCells } : row;
            }),
          };
        }
      );

      return { previousGrids };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousGrids) {
        for (const [queryKey, data] of context.previousGrids) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
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

export function useRosterConflictsQuery(
  periodId?: string,
  params?: {
    severity?: string;
    brand_id?: string;
    date?: string;
    employee_id?: string;
  }
) {
  return useQuery({
    queryKey: ['roster-conflicts', periodId, params],
    queryFn: () => {
      if (!periodId) return [];
      return getRosterConflictsApi(periodId, params);
    },
    enabled: Boolean(periodId),
  });
}

export function useRosterSuggestionsQuery(
  periodId?: string,
  params?: {
    conflict_id?: string;
    brand_process_id?: string;
    date?: string;
  }
) {
  return useQuery({
    queryKey: ['roster-suggestions', periodId, params],
    queryFn: () => {
      if (!periodId || (!params?.conflict_id && !params?.brand_process_id)) return [];
      return getRosterSuggestionsApi(periodId, params);
    },
    enabled: Boolean(periodId && (params?.conflict_id || params?.brand_process_id)),
  });
}

export function useAcknowledgeConflictMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request: RosterAcknowledgeRequest;
    }) => acknowledgeRosterConflictApi(periodId, request),
    onMutate: async ({ request }) => {
      await queryClient.cancelQueries({ queryKey: ['roster-conflicts'] });
      const previousConflicts = queryClient.getQueriesData<RosterConflict[]>({
        queryKey: ['roster-conflicts'],
      });

      queryClient.setQueriesData<RosterConflict[]>(
        { queryKey: ['roster-conflicts'] },
        (old) => {
          if (!old || !Array.isArray(old)) return old;
          return old.map((c) =>
            c.id === request.conflict_id
              ? {
                  ...c,
                  is_acknowledged: true,
                  acknowledged_reason: request.reason,
                }
              : c
          );
        }
      );

      return { previousConflicts };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousConflicts) {
        for (const [queryKey, data] of context.previousConflicts) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useRepairRosterMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request: RosterRepairRequest;
    }) => repairRosterApi(periodId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['roster-grid', variables.periodId] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts', variables.periodId] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage', variables.periodId] });
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
    },
  });
}

export function useGenerateRosterMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: RosterGenerateRequest) => generateRosterApi(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-day-view'] });
      queryClient.invalidateQueries({ queryKey: ['roster-dashboard'] });
    },
  });
}

export function usePublishRosterMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (periodId: string) => publishRosterApi(periodId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-dashboard'] });
    },
  });
}

export function useCloneRosterMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      periodId,
      request,
    }: {
      periodId: string;
      request?: RosterCloneRequest;
    }) => cloneRosterApi(periodId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rosters'] });
      queryClient.invalidateQueries({ queryKey: ['roster-grid'] });
      queryClient.invalidateQueries({ queryKey: ['roster-coverage'] });
      queryClient.invalidateQueries({ queryKey: ['roster-conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['roster-dashboard'] });
    },
  });
}

// ----------------------------------------------------------------------------
// Version Comparison & Export APIs (S10 Specification)
// ----------------------------------------------------------------------------

export async function compareRostersApi(
  periodIdA: string,
  periodIdB: string
): Promise<RosterCompareResponse> {
  const query = new URLSearchParams();
  query.set('a', periodIdA);
  query.set('b', periodIdB);
  return apiClient<RosterCompareResponse>(`/rosters/compare?${query.toString()}`);
}

export function useCompareRostersQuery(periodIdA?: string, periodIdB?: string) {
  return useQuery({
    queryKey: ['rosters-compare', periodIdA, periodIdB],
    queryFn: () => {
      if (!periodIdA || !periodIdB) return null;
      return compareRostersApi(periodIdA, periodIdB);
    },
    enabled: Boolean(periodIdA && periodIdB && periodIdA !== periodIdB),
  });
}

export async function downloadRosterExport(
  periodId: string,
  format: 'csv' | 'xlsx' = 'csv',
  view: string = 'grid',
  date?: string
): Promise<string> {
  const query = new URLSearchParams();
  query.set('format', format);
  query.set('view', view);
  if (date) query.set('date', date);

  const { blob, filename } = await apiClientBlob(`/rosters/${periodId}/export?${query.toString()}`);

  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);

  return filename;
}



