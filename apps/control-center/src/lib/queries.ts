/**
 * TanStack Query hooks wrapping the RailOS API.
 * Provides typed, cached queries and mutations with server-side data consistency.
 *
 * Stable query keys as arrays (per TanStack Query best practices).
 * All server data lives HERE, never in Zustand — this is architectural.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult, UseMutationResult } from '@tanstack/react-query';

import * as api from './api';
import type { RailwayZone, RailwayDivision, RailwaySection, NetworkCatalog } from '../types/network';
import { useRailOSStore } from '@/store/railosStore';

// ============================================================================
// Query key factories — stable arrays for cache management
// ============================================================================

const queryKeys = {
  zones: {
    all: ['zones'] as const,
    list: () => ['zones', 'list'] as const,
  },
  divisions: {
    all: ['divisions'] as const,
    forZone: (zoneId: string) => ['divisions', 'zone', zoneId] as const,
  },
  sections: {
    all: ['sections'] as const,
    forDivision: (divisionId: string) => ['sections', 'division', divisionId] as const,
    detail: (sectionId: string) => ['sections', 'detail', sectionId] as const,
  },
  network: {
    catalog: ['network', 'catalog'] as const,
    catalogWithParams: (bbox?: string, layer?: string) =>
      ['network', 'catalog', bbox, layer].filter(Boolean),
    geojson: ['network', 'geojson'] as const,
    geojsonWithParams: (bbox?: string, layer?: string) =>
      ['network', 'geojson', bbox, layer].filter(Boolean),
    search: (query: string) => ['network', 'search', query] as const,
  },
  maintenance: {
    tasks: ['maintenance', 'tasks'] as const,
    tasksWithFilter: (filter?: Record<string, string>) =>
      ['maintenance', 'tasks', filter].filter(Boolean),
    defects: ['maintenance', 'defects'] as const,
    defectsWithFilter: (filter?: Record<string, string>) =>
      ['maintenance', 'defects', filter].filter(Boolean),
  },
  blockRequests: {
    all: ['blockRequests'] as const,
    list: (filter?: Record<string, string>) => ['blockRequests', 'list', filter].filter(Boolean),
    detail: (requestId: string) => ['blockRequests', 'detail', requestId] as const,
    taskTypes: ['blockRequests', 'taskTypes'] as const,
  },
  planning: {
    blockWindows: ['planning', 'blockWindows'] as const,
    blockWindowsForSection: (sectionId?: string) =>
      ['planning', 'blockWindows', sectionId].filter(Boolean),
    blockPlans: ['planning', 'blockPlans'] as const,
    blockPlansWithFilter: (filter?: Record<string, string>) =>
      ['planning', 'blockPlans', filter].filter(Boolean),
    planDetail: (planId: string) => ['planning', 'plans', planId] as const,
  },
  analytics: {
    summary: ['analytics', 'summary'] as const,
  },
  trains: {
    all: ['trains'] as const,
  },
  events: {
    since: (sequence: number) => ['events', 'since', sequence] as const,
  },
  possessions: {
    all: ['possessions'] as const,
    list: (role: string, filter?: Record<string, string>) =>
      ['possessions', 'list', role, filter].filter(Boolean),
    mine: (role: string) => ['possessions', 'mine', role] as const,
    detail: (role: string, possessionId: string) => ['possessions', 'detail', role, possessionId] as const,
  },
  sanctions: {
    detail: (planId: string) => ['sanctions', planId] as const,
  },
  bursts: {
    all: ['blockBursts'] as const,
  },
};

// ============================================================================
// Network queries
// ============================================================================

/**
 * Fetch all zones.
 */
export function useZones(): UseQueryResult<RailwayZone[], api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.zones.list(),
    queryFn: () => api.fetchZones(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch divisions for a specific zone.
 */
export function useDivisionsForZone(
  zoneId: string,
  options?: { enabled?: boolean }
): UseQueryResult<RailwayDivision[], api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.divisions.forZone(zoneId),
    queryFn: () => api.fetchDivisionsForZone(zoneId),
    enabled: Boolean(zoneId) && options?.enabled !== false,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch sections for a specific division.
 */
export function useSectionsForDivision(
  divisionId: string,
  options?: { enabled?: boolean }
): UseQueryResult<RailwaySection[], api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.sections.forDivision(divisionId),
    queryFn: () => api.fetchSectionsForDivision(divisionId),
    enabled: Boolean(divisionId) && options?.enabled !== false,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch detail for a specific section.
 */
export function useSection(
  sectionId: string,
  options?: { enabled?: boolean }
): UseQueryResult<RailwaySection, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.sections.detail(sectionId),
    queryFn: () => api.fetchSectionDetail(sectionId),
    enabled: Boolean(sectionId) && options?.enabled !== false,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch the complete network catalog (zones, divisions, sections, segments, stations).
 */
export function useNetworkCatalog(
  bbox?: string,
  layer?: string
): UseQueryResult<NetworkCatalog, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.network.catalogWithParams(bbox, layer),
    queryFn: () => api.fetchNetworkCatalog(bbox, layer),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch network as GeoJSON (for map rendering).
 */
export function useNetworkGeoJSON(
  bbox?: string,
  layer?: string
): UseQueryResult<GeoJSON.FeatureCollection, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.network.geojsonWithParams(bbox, layer),
    queryFn: () => api.fetchNetworkGeoJSON(bbox, layer),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Search the network by name, station, or corridor.
 */
export function useNetworkSearch(query: string): UseQueryResult<{ results: unknown[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.network.search(query),
    queryFn: () => api.fetchNetworkSearch(query),
    enabled: query.length > 0,
    staleTime: 2 * 60 * 1000, // 2 minutes for search
  });
}

// ============================================================================
// Maintenance queries
// ============================================================================

/**
 * Fetch maintenance tasks with optional filter.
 */
export function useMaintenanceTasks(filter?: {
  sectionId?: string;
  status?: string;
  priorityBand?: string;
}): UseQueryResult<{ tasks: unknown[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.maintenance.tasksWithFilter(filter),
    queryFn: () => api.fetchMaintenanceTasks(filter),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch defects with optional filter.
 */
export function useDefects(filter?: {
  sectionId?: string;
  severity?: string;
}): UseQueryResult<{ defects: unknown[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.maintenance.defectsWithFilter(filter),
    queryFn: () => api.fetchDefects(filter),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch live train movements.
 */
export function useTrains(): UseQueryResult<unknown[], api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.trains.all,
    queryFn: () => api.fetchTrains(),
    staleTime: 60 * 1000,
  });
}

// ============================================================================
// Department ticket queries
// ============================================================================

/** Asset inventory; static for the scenario's lifetime. */
export function useAssets(): UseQueryResult<api.AssetSummary[], api.RailOSApiError> {
  return useQuery({
    queryKey: ['assets'] as const,
    queryFn: () => api.fetchAssets(),
    staleTime: 60 * 60 * 1000,
  });
}

/** Task types and their statutory duration floors; effectively static. */
export function useTicketTaskTypes(): UseQueryResult<api.TicketTaskType[], api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.blockRequests.taskTypes,
    queryFn: () => api.fetchTicketTaskTypes(),
    staleTime: 60 * 60 * 1000,
  });
}

export function useBlockRequests(filter?: api.BlockRequestFilters): UseQueryResult<
  { items: api.BlockRequest[]; count: number; synthetic?: boolean },
  api.RailOSApiError
> {
  const queryFilter = filter
    ? Object.fromEntries(Object.entries(filter).filter(([, value]) => Boolean(value))) as Record<string, string>
    : undefined;
  return useQuery({
    queryKey: queryKeys.blockRequests.list(queryFilter),
    queryFn: () => api.fetchBlockRequests(filter),
    staleTime: 15 * 1000,
  });
}

export function useBlockRequest(
  requestId: string,
  options?: { enabled?: boolean }
): UseQueryResult<api.BlockRequest, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.blockRequests.detail(requestId),
    queryFn: () => api.fetchBlockRequest(requestId),
    enabled: Boolean(requestId) && options?.enabled !== false,
    staleTime: 15 * 1000,
  });
}

export function useCreateBlockRequest(): UseMutationResult<
  api.BlockRequest,
  api.RailOSApiError,
  api.CreateBlockRequestPayload
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createBlockRequest,
    onSuccess: (request) => {
      queryClient.setQueryData(queryKeys.blockRequests.detail(request.requestId), request);
      queryClient.invalidateQueries({ queryKey: queryKeys.blockRequests.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.maintenance.tasks });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockWindows });
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics.summary });
    },
  });
}

export function useUpdateBlockRequestStatus(): UseMutationResult<
  api.BlockRequest,
  api.RailOSApiError,
  api.BlockRequestStatusUpdate
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.updateBlockRequestStatus,
    onSuccess: (request) => {
      queryClient.setQueryData(queryKeys.blockRequests.detail(request.requestId), request);
      queryClient.invalidateQueries({ queryKey: queryKeys.blockRequests.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.maintenance.tasks });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockWindows });
    },
  });
}

// ============================================================================
// Planning queries
// ============================================================================

/**
 * Fetch block opportunity windows.
 */
export function useBlockWindows(sectionId?: string): UseQueryResult<{ windows: unknown[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.planning.blockWindowsForSection(sectionId),
    queryFn: () => api.fetchBlockWindows(sectionId),
    staleTime: 3 * 60 * 1000,
  });
}

/**
 * Fetch block plans (maintenance plans) with optional filter.
 */
export function useBlockPlans(filter?: {
  corridorId?: string;
  status?: string;
}): UseQueryResult<{ plans: api.RailOSPlan[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.planning.blockPlansWithFilter(filter),
    queryFn: () => api.fetchBlockPlans(filter),
    staleTime: 3 * 60 * 1000,
  });
}

/**
 * Fetch detail for a specific plan.
 */
export function usePlanDetail(
  planId: string,
  options?: { enabled?: boolean }
): UseQueryResult<api.RailOSPlan, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.planning.planDetail(planId),
    queryFn: () => api.fetchPlanDetail(planId),
    enabled: Boolean(planId) && options?.enabled !== false,
    staleTime: 5 * 60 * 1000,
  });
}

// ============================================================================
// Analytics queries
// ============================================================================

/**
 * Fetch analytics summary (maintenance debt, defects, utilization, traffic).
 */
export function useAnalyticsSummary(): UseQueryResult<
  api.AnalyticsSummary,
  api.RailOSApiError
> {
  return useQuery({
    queryKey: queryKeys.analytics.summary,
    queryFn: () => api.fetchAnalyticsSummary(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBlockBursts(): UseQueryResult<
  { items: api.BlockBurstRecord[]; count: number; synthetic?: boolean },
  api.RailOSApiError
> {
  return useQuery({
    queryKey: queryKeys.bursts.all,
    queryFn: () => api.fetchBlockBursts(),
    staleTime: 5 * 1000,
  });
}

// ============================================================================
// Possession authority queries
// ============================================================================

export function usePossessions(filter?: {
  status?: api.PossessionState;
  sectionId?: string;
}): UseQueryResult<{ items: api.PossessionView[]; count: number; synthetic?: boolean }, api.RailOSApiError> {
  const role = useRailOSStore((state) => state.userRole);
  const queryFilter = filter
    ? Object.fromEntries(Object.entries(filter).filter(([, value]) => Boolean(value))) as Record<string, string>
    : undefined;

  return useQuery({
    queryKey: queryKeys.possessions.list(role, queryFilter),
    queryFn: () => api.fetchPossessions(filter),
    staleTime: 5 * 1000,
  });
}

export function useMyPossessions(): UseQueryResult<
  { items: api.PossessionView[]; count: number; synthetic?: boolean },
  api.RailOSApiError
> {
  const role = useRailOSStore((state) => state.userRole);
  return useQuery({
    queryKey: queryKeys.possessions.mine(role),
    queryFn: () => api.fetchMyPossessions(),
    staleTime: 5 * 1000,
  });
}

export function usePossession(
  possessionId: string,
  options?: { enabled?: boolean }
): UseQueryResult<api.PossessionView, api.RailOSApiError> {
  const role = useRailOSStore((state) => state.userRole);
  return useQuery({
    queryKey: queryKeys.possessions.detail(role, possessionId),
    queryFn: () => api.fetchPossession(possessionId),
    enabled: Boolean(possessionId) && options?.enabled !== false,
    staleTime: 5 * 1000,
  });
}

export function usePlanSanctions(
  planId: string,
  options?: { enabled?: boolean }
): UseQueryResult<api.SanctionChain, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.sanctions.detail(planId),
    queryFn: () => api.fetchPlanSanctions(planId),
    enabled: Boolean(planId) && options?.enabled !== false,
    staleTime: 5 * 1000,
  });
}

export function useSignPlanSanction(): UseMutationResult<
  api.SanctionChain | api.RailOSPlan,
  api.RailOSApiError,
  {
    planId: string;
    authority: api.SanctionAuthority;
    decision: api.SignatureDecision;
    reason?: string;
    formReference?: string;
    expectedVersion?: number;
  }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, ...payload }) => api.signPlanSanction(planId, payload),
    onSuccess: (data, { planId }) => {
      // Both a partial 202 chain and the final plan are successful writes.
      if ('requiredAuthorities' in data && 'signatures' in data) {
        queryClient.setQueryData(queryKeys.sanctions.detail(planId), data);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.sanctions.detail(planId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.planDetail(planId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
      queryClient.invalidateQueries({ queryKey: queryKeys.possessions.all });
    },
  });
}

export function usePossessionAction(): UseMutationResult<
  api.PossessionView,
  api.RailOSApiError,
  { possessionId: string; action: string; payload?: api.PossessionActionPayload }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ possessionId, action, payload }) =>
      api.performPossessionAction(possessionId, action, payload),
    onSuccess: (data, { possessionId }) => {
      queryClient.setQueryData(
        queryKeys.possessions.detail(useRailOSStore.getState().userRole, possessionId),
        data
      );
      queryClient.invalidateQueries({ queryKey: queryKeys.possessions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics.summary });
    },
  });
}

/**
 * Fetch events since a given sequence number (for event streaming).
 */
export function useEventsSince(sequence: number): UseQueryResult<{ events: unknown[] }, api.RailOSApiError> {
  return useQuery({
    queryKey: queryKeys.events.since(sequence),
    queryFn: () => api.fetchEventsSince(sequence),
    staleTime: 10 * 1000, // 10 seconds for near-real-time
  });
}

// ============================================================================
// Mutations — state-changing operations
// ============================================================================

/**
 * Generate an optimization plan.
 */
export function useGeneratePlan(): UseMutationResult<
  unknown,
  api.RailOSApiError,
  {
    corridorIds?: string[];
    objectiveProfile?: string;
    planningHorizon?: string;
    taskIds?: string[];
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => api.generateOptimization(payload),
    onSuccess: () => {
      // Invalidate block plans and related caches
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics.summary });
    },
  });
}

/**
 * Approve a maintenance plan.
 */
export function useApprovePlan(): UseMutationResult<unknown, api.RailOSApiError, { planId: string; reason?: string }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, reason }) => api.approvePlan(planId, reason),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.planDetail(planId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
    },
  });
}

/**
 * Reject a maintenance plan.
 */
export function useRejectPlan(): UseMutationResult<unknown, api.RailOSApiError, { planId: string; reason?: string }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, reason }) => api.rejectPlan(planId, reason),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.planDetail(planId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
    },
  });
}

/**
 * Request revision to a maintenance plan.
 */
export function useRequestPlanRevision(): UseMutationResult<
  unknown,
  api.RailOSApiError,
  { planId: string; reason: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, reason }) => api.requestPlanRevision(planId, reason),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.planDetail(planId) });
    },
  });
}

/**
 * Create a defect record.
 */
export function useCreateDefect(): UseMutationResult<
  unknown,
  api.RailOSApiError,
  {
    defectId: string;
    assetId: string;
    sectionId: string;
    severityCode: string;
    detectedAtMinute: number;
    taskId?: string;
    repeatCount?: number;
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => api.createDefect(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.maintenance.defects });
      queryClient.invalidateQueries({ queryKey: queryKeys.analytics.summary });
    },
  });
}

/**
 * Update a work assignment status.
 */
export function useUpdateWorkAssignment(): UseMutationResult<
  unknown,
  api.RailOSApiError,
  { assignmentId: string; status: string; note?: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ assignmentId, status, note }) => api.updateWorkAssignment(assignmentId, { status, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
    },
  });
}

/**
 * Create an emergency incident.
 */
export function useCreateEmergency(): UseMutationResult<
  api.EmergencyCreatedResponse,
  api.RailOSApiError,
  {
    title: string;
    corridorId: string;
    sectionId?: string;
    assetId?: string;
    severity?: string;
    durationMinutes?: number;
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => api.createEmergency(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.maintenance.defects });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
    },
  });
}

/**
 * Generate a re-plan after an emergency.
 */
export function useGenerateReplanning(): UseMutationResult<
  unknown,
  api.RailOSApiError,
  {
    parentPlanId: string;
    emergencyId: string;
    nowMinute?: number;
    reason: string;
  }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => api.generateReplanning(payload),
    onSuccess: (_, { parentPlanId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.planDetail(parentPlanId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.planning.blockPlans });
    },
  });
}
