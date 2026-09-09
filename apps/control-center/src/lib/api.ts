/**
 * Typed fetch layer for RailOS API.
 * Centralizes authentication, error mapping, and type conversion.
 *
 * Error responses follow the canonical envelope:
 * { error: { code, message, details, requestId }, ... }
 *
 * Network errors or parse failures are mapped to code "NETWORK_ERROR".
 */

import type { NetworkCatalog, RailwaySection, RailwayZone, RailwayDivision } from '../types/network';

export type RailOSRole =
  | 'ADMIN'
  | 'CONTROL_OFFICER'
  | 'PLANNER'
  | 'ENGINEERING'
  | 'SIGNAL_TELECOM'
  | 'TRACTION'
  | 'FIELD_SUPERVISOR'
  | 'MANAGEMENT'
  | 'STATION_MASTER'
  | 'TPC';

export type SanctionAuthority =
  | 'SANCTION'
  | 'SECTION_CONTROL'
  | 'TRACTION_POWER'
  | 'STATION'
  | 'SNT'
  | 'ENGINEERING_SSE';

export type SignatureDecision = 'GRANTED' | 'REFUSED' | 'DEFERRED' | 'WITHDRAWN';

export type PossessionState =
  | 'SANCTIONED'
  | 'CLEARANCE_REQUESTED'
  | 'DEFERRED'
  | 'CANCELLED'
  | 'CLEARANCE_GRANTED'
  | 'ISOLATION_IN_PROGRESS'
  | 'PROTECTED'
  | 'LIVE'
  | 'OVERRUNNING'
  | 'TESTING'
  | 'HANDBACK_REQUESTED'
  | 'FIT_CERTIFIED'
  | 'CLEARED'
  | 'ABANDONED';

export interface AuthoritySignatureRecord {
  signatureId: string;
  authority: SanctionAuthority;
  decision: SignatureDecision;
  role: RailOSRole | string;
  userId: string;
  reason: string;
  formReference: string;
  signedAtUtc: string;
  planVersion: number;
  possessionId?: string | null;
}

export interface SanctionChain {
  planId: string;
  planVersion: number;
  requiredAuthorities: SanctionAuthority[];
  signatures: AuthoritySignatureRecord[];
  complete: boolean;
  refused: boolean;
  derivedFrom: string[];
  backfilled: boolean;
}

export interface RailOSPlan {
  planId: string;
  planVersion: number;
  parentPlanId?: string | null;
  status: string;
  objectiveProfile: string;
  horizonMinutes: number;
  blocks: Array<{
    blockId: string;
    sectionId: string;
    track: string;
    blockType: string;
    start: number;
    end: number;
    taskIds: string[];
    departments: string[];
    opportunityId?: string | null;
  }>;
  assignments: Array<{ taskId: string; blockId: string; start: number; end: number }>;
  unassigned: Array<{ taskId: string; reason: string }>;
  warnings: string[];
  metrics: Record<string, number>;
  provenance?: string;
  [key: string]: unknown;
}

/** Canonical department codes used by the BlockRequest API and optimizer. */
export type DepartmentCode = 'ENGG' | 'SNT' | 'TRD';

export type BlockRequestStatus =
  | 'DRAFT'
  | 'REQUESTED'
  | 'READY'
  | 'ACCEPTED'
  | 'PLANNED'
  | 'REJECTED'
  | 'CANCELLED';

/**
 * Departmental planning intent. The linked task is the canonical optimizer
 * input; a request is never a second, frontend-only task representation.
 */
export interface BlockRequest {
  requestId: string;
  department: DepartmentCode;
  status: BlockRequestStatus | string;
  corridorId: string;
  sectionId: string;
  track: string;
  kmStart: number;
  kmEnd: number;
  taskType: string;
  severity: number;
  estimatedDuration: number;
  blockType: string;
  requestedStart?: string | null;
  requestedEnd?: string | null;
  earliestRequestedStart?: string | null;
  latestRequestedEnd?: string | null;
  linkedTaskId?: string | null;
  plannedBlockId?: string | null;
  planId?: string | null;
  actor?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  allowedActions?: string[];
  provenance?: string | null;
  synthetic?: boolean;
  [key: string]: unknown;
}

export interface CreateBlockRequestPayload {
  department: DepartmentCode;
  corridorId: string;
  sectionId: string;
  track: string;
  kmStart: number;
  kmEnd: number;
  taskType: string;
  severity: number;
  estimatedDuration: number;
  blockType: string;
  /** Set when the section holds more than one candidate asset for the task type. */
  assetId?: string;
  /** Integer minutes relative to the scenario horizon start, per BlockRequestCreate (extra="forbid"). */
  requestedStart: number;
  requestedEnd: number;
}

export interface BlockRequestFilters {
  department?: DepartmentCode;
  status?: string;
  sectionId?: string;
}

export interface PossessionTransitionRecord {
  transitionId: string;
  fromState: PossessionState;
  toState: PossessionState;
  action: string;
  actor: string;
  role: string;
  occurredAtUtc: string;
  clientEventAtUtc?: string | null;
  ruleCitation: string;
  details?: Record<string, unknown>;
  replayed?: boolean;
}

export interface PossessionView {
  possessionId: string;
  planId: string;
  planVersion: number;
  blockId: string;
  sectionId: string;
  track: string;
  state: PossessionState;
  plannedStartUtc: string;
  plannedEndUtc: string;
  actualStartUtc?: string | null;
  actualEndUtc?: string | null;
  deferralCount: number;
  deferredUntilUtc?: string | null;
  requiresPTW: boolean;
  requiresT351: boolean;
  requiresCorrespondenceTest: boolean;
  stationClosed: boolean;
  formT351?: {
    formNumber: string;
    sectionId: string;
    track: string;
    issuedBy: string;
    issuedAtUtc: string;
    endorsedBy?: string | null;
    endorsedAtUtc?: string | null;
    status: string;
    remarks: string;
  } | null;
  permitToWork?: {
    ptwNumber: string;
    oheSection: string;
    isolatorNumber: string;
    issuedBy: string;
    issuedAtUtc: string;
    earthingConfirmed: boolean;
    cancelledBy?: string | null;
    cancelledAtUtc?: string | null;
    dischargeRodsRemoved: boolean;
    status: string;
    remarks: string;
  } | null;
  protectionRecord?: Record<string, unknown> | null;
  correspondenceTest?: Record<string, unknown> | null;
  fitnessCertificate?: Record<string, unknown> | null;
  transitions: PossessionTransitionRecord[];
  assignedTaskIds: string[];
  department: string;
  leadInMinutes: number;
  overrunMinutesLive: number;
  handbackChecklist: Array<{ item: string; satisfied: boolean; rule: string }>;
  allowedActions: string[];
  blockedActions?: { action: string; reason: string }[];
  [key: string]: unknown;
}

export interface BlockBurstRecord {
  burstId: string;
  possessionId: string;
  planId: string;
  sectionId: string;
  track: string;
  department: string;
  plannedEndUtc: string;
  actualCloseUtc: string;
  overrunMinutes: number;
  causeCategory: string;
  remarks: string;
  occurredAtUtc: string;
}

export interface AnalyticsSummary {
  maintenanceDebt: number;
  criticalDefects: number;
  blockUtilization: number;
  trafficPressure: number;
  tasks?: number;
  defects?: number;
  overdueTasks?: number;
  completedTasks?: number;
  blockBursts?: {
    totalBursts: number;
    totalOverrunMinutes: number;
    byDepartment: Record<string, number>;
    byCause: Record<string, number>;
    items: BlockBurstRecord[];
  };
  synthetic?: boolean;
}

/**
 * Typed RailOS API error with code, message, details, requestId, and HTTP status.
 */
export class RailOSApiError extends Error {
  code: string;
  details: unknown;
  requestId: string;
  status: number;

  constructor(code: string, message: string, details?: unknown, requestId?: string, status?: number) {
    super(message);
    this.name = 'RailOSApiError';
    this.code = code;
    this.details = details;
    this.requestId = requestId || 'unknown';
    this.status = status || 500;
  }
}

interface ApiErrorEnvelope {
  error?: {
    code: string;
    message: string;
    details?: unknown;
    requestId?: string;
  };
  [key: string]: unknown;
}

interface ApiConfig {
  baseUrl: string;
}

/**
 * Get configuration from environment and defaults.
 * Base URL: process.env.NEXT_PUBLIC_RAILOS_API_URL, default 'http://localhost:8000'
 */
function getConfig(): ApiConfig {
  const baseUrl = process.env.NEXT_PUBLIC_RAILOS_API_URL || 'http://localhost:8000';
  return { baseUrl };
}

// The shell owns the role selector; API calls read this value at request time so
// every server-state request carries the same authority context. This drives the
// synthetic X-RailOS-Role header, which is only sent when synthetic auth is
// explicitly enabled, and also mirrors a real login's verified role so both auth
// paths agree on "who is acting" everywhere in the UI.
let activeRole: RailOSRole = 'CONTROL_OFFICER';

export function setApiRole(role: RailOSRole | string | null | undefined) {
  const normalized = String(role || '').trim().toUpperCase() as RailOSRole;
  activeRole = normalized || 'CONTROL_OFFICER';
}

export function getApiRole(): RailOSRole {
  return activeRole;
}

// ============================================================================
// Real authentication (Argon2 + JWT, evidence_routes.py) — coexists with the
// synthetic header path above. When a session is set, its Bearer token is sent
// on every request and every endpoint verifies the caller for real - the
// planning/possession/ticket API in main.py accepts the same token. The
// synthetic headers are a local-development fallback, off unless
// NEXT_PUBLIC_ENABLE_SYNTHETIC_AUTH is set.
// ============================================================================

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
  userId: string;
  role: string;
  employeeId: string;
  name: string;
  /** The account's own department (ENGG/SNT/TRD), when it has one. Supervisors
   * belong to a department that their role alone cannot identify. */
  department?: DepartmentCode;
}

export interface AuthLoginResult {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresInSeconds: number;
  userId: string;
  role: string;
  employeeId: string;
  name: string;
  department?: DepartmentCode;
}

let authSession: AuthSession | null = null;

export function setAuthSession(session: AuthSession | null) {
  authSession = session;
}

export function getAuthSession(): AuthSession | null {
  return authSession;
}

/** Registered by authStore so a transparent refresh (triggered by a 401 retry) is reflected in UI state and persisted storage. */
let onSessionRefreshed: ((session: AuthSession) => void) | undefined;
let onSessionExpired: (() => void) | undefined;

export function setSessionSyncHandlers(handlers: {
  onRefreshed: (session: AuthSession) => void;
  onExpired: () => void;
}) {
  onSessionRefreshed = handlers.onRefreshed;
  onSessionExpired = handlers.onExpired;
}

export async function authLogin(employeeId: string, password: string): Promise<AuthLoginResult> {
  return fetchApi<AuthLoginResult>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ employeeId, password }),
  });
}

export async function authRefresh(refreshToken: string): Promise<AuthLoginResult> {
  return fetchApi<AuthLoginResult>('/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refreshToken }),
  });
}

// The refresh token is single-use and rotates on every call — the server invalidates
// it the instant one request redeems it. Two callers can legitimately race for it (the
// mount-time restoreSession() call and a transparent 401 retry from a parallel query
// both firing on page load); without de-duping, the loser gets REFRESH_TOKEN_INVALID
// and tears down the session the winner just established. Share one in-flight call.
let refreshInFlight: Promise<AuthLoginResult> | null = null;

export function refreshSession(refreshToken: string): Promise<AuthLoginResult> {
  if (!refreshInFlight) {
    refreshInFlight = authRefresh(refreshToken).finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function authLogout(refreshToken: string): Promise<void> {
  await fetchApi('/api/v1/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refreshToken }),
  });
}

function toAuthSession(result: AuthLoginResult): AuthSession {
  return {
    accessToken: result.accessToken,
    refreshToken: result.refreshToken,
    expiresAt: Date.now() + result.expiresInSeconds * 1000,
    userId: result.userId,
    role: result.role,
    employeeId: result.employeeId,
    name: result.name,
    department: result.department,
  };
}

/** Attempt a single transparent refresh using the current session's refresh token. */
async function tryRefreshSession(): Promise<boolean> {
  if (!authSession?.refreshToken) return false;
  const previous = authSession;
  try {
    const result = await refreshSession(previous.refreshToken);
    // A logout or a newer login wins over this older request's completion.
    if (authSession !== previous) return authSession !== null;
    const next = toAuthSession(result);
    authSession = next;
    onSessionRefreshed?.(next);
    return true;
  } catch {
    if (authSession !== previous) return authSession !== null;
    authSession = null;
    onSessionExpired?.();
    return false;
  }
}

export const SYNTHETIC_AUTH_ENABLED =
  process.env.NEXT_PUBLIC_ENABLE_SYNTHETIC_AUTH === 'true';

/**
 * Preserve real identity until the server accepts it or refreshes it. An expired
 * access token must produce a 401, never silently change the actor to demo-user.
 */
function getAuthHeaders(): Record<string, string> {
  if (authSession) {
    return { Authorization: `Bearer ${authSession.accessToken}` };
  }
  // The header path asserts an identity and a role with no credentials at all.
  // The API only honours it when ENABLE_SYNTHETIC_AUTH is on; the client must
  // opt in just as explicitly, so a deployed build sends nothing and an
  // unauthenticated request gets its 401 instead of silently acting as an admin.
  if (SYNTHETIC_AUTH_ENABLED) {
    return { 'X-RailOS-User': 'demo-user', 'X-RailOS-Role': activeRole };
  }
  return {};
}

const AUTH_PATH_PREFIX = '/api/v1/auth/';

/**
 * Fetch from the RailOS API with error handling and type conversion.
 * On a 401 from a real (non-auth) request while a session is active, attempts
 * one transparent refresh-and-retry before surfacing the error.
 */
async function fetchApi<T>(path: string, init?: RequestInit, _retried = false): Promise<T> {
  const config = getConfig();
  const url = `${config.baseUrl}${path}`;
  const fetchInit = init || {};

  try {
    const headers = getAuthHeaders();
    const response = await fetch(url, {
      ...fetchInit,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
        ...(fetchInit?.headers as Record<string, string>),
      },
    });

    if (!response.ok) {
      let errorData: ApiErrorEnvelope = {};
      let errorText = '';

      try {
        errorText = await response.text();
        errorData = errorText ? JSON.parse(errorText) : {};
      } catch {
        // If we can't parse the error response, create a minimal error
      }

      if (
        response.status === 401 &&
        !_retried &&
        !path.startsWith(AUTH_PATH_PREFIX) &&
        authSession
      ) {
        const refreshed = await tryRefreshSession();
        if (refreshed) return fetchApi<T>(path, init, true);
      }

      const error = errorData.error;
      throw new RailOSApiError(
        error?.code || 'API_ERROR',
        error?.message || `HTTP ${response.status}`,
        error?.details,
        error?.requestId,
        response.status
      );
    }

    const text = await response.text();
    if (!text) return {} as T;

    return JSON.parse(text) as T;
  } catch (err) {
    if (err instanceof RailOSApiError) throw err;

    const message = err instanceof Error ? err.message : String(err);
    throw new RailOSApiError('NETWORK_ERROR', message || 'Network request failed');
  }
}

/**
 * Network endpoints — read-only queries
 */

export async function fetchZones(): Promise<RailwayZone[]> {
  const data = await fetchApi<{ items?: RailwayZone[]; zones?: RailwayZone[] }>('/api/v1/network/zones');
  return data.items || data.zones || [];
}

export async function fetchDivisionsForZone(zoneId: string): Promise<RailwayDivision[]> {
  const data = await fetchApi<{ items?: RailwayDivision[]; divisions?: RailwayDivision[] }>(`/api/v1/network/zones/${zoneId}/divisions`);
  return data.items || data.divisions || [];
}

export async function fetchSectionsForDivision(divisionId: string): Promise<RailwaySection[]> {
  const data = await fetchApi<{ items?: RailwaySection[]; sections?: RailwaySection[] }>(`/api/v1/network/divisions/${divisionId}/sections`);
  return data.items || data.sections || [];
}

export async function fetchSectionDetail(sectionId: string): Promise<RailwaySection> {
  const data = await fetchApi<RailwaySection>(`/api/v1/network/sections/${sectionId}`);
  return data;
}

export async function fetchNetworkCatalog(bbox?: string, layer?: string): Promise<NetworkCatalog> {
  const params = new URLSearchParams();
  if (bbox) params.append('bbox', bbox);
  if (layer) params.append('layer', layer);

  const qs = params.toString();
  const path = `/api/v1/network/catalog${qs ? '?' + qs : ''}`;
  const data = await fetchApi<NetworkCatalog>(path);
  return data;
}

export async function fetchNetworkGeoJSON(
  bbox?: string,
  layer?: string
): Promise<GeoJSON.FeatureCollection> {
  const params = new URLSearchParams();
  if (bbox) params.append('bbox', bbox);
  if (layer) params.append('layer', layer);

  const qs = params.toString();
  const path = `/api/v1/network/geojson${qs ? '?' + qs : ''}`;
  const data = await fetchApi<GeoJSON.FeatureCollection>(path);
  return data;
}

export async function fetchNetworkSearch(query: string): Promise<{ results: unknown[] }> {
  const params = new URLSearchParams({ q: query });
  const data = await fetchApi<{ results: unknown[] }>(`/api/v1/network/search?${params}`);
  return data;
}

export async function fetchCorridors(): Promise<unknown[]> {
  const data = await fetchApi<{ items?: unknown[] }>('/api/v1/corridors');
  return data.items || [];
}

export async function fetchTrains(): Promise<unknown[]> {
  const data = await fetchApi<{ items?: unknown[] }>('/api/v1/trains');
  return data.items || [];
}

/**
 * Maintenance task endpoints
 */

export async function fetchMaintenanceTasks(filter?: {
  sectionId?: string;
  status?: string;
  priorityBand?: string;
}): Promise<{ tasks: unknown[] }> {
  const params = new URLSearchParams();
  if (filter?.sectionId) params.append('sectionId', filter.sectionId);
  if (filter?.status) params.append('status', filter.status);
  if (filter?.priorityBand) params.append('priorityBand', filter.priorityBand);

  const qs = params.toString();
  const path = `/api/v1/maintenance/tasks${qs ? '?' + qs : ''}`;
  const data = await fetchApi<{ items?: unknown[]; tasks?: unknown[] }>(path);
  return { tasks: data.items || data.tasks || [] };
}

export async function fetchDefects(filter?: {
  sectionId?: string;
  severity?: string;
}): Promise<{ defects: unknown[] }> {
  const params = new URLSearchParams();
  if (filter?.sectionId) params.append('sectionId', filter.sectionId);
  if (filter?.severity) params.append('severity', filter.severity);

  const qs = params.toString();
  const path = `/api/v1/defects${qs ? '?' + qs : ''}`;
  const data = await fetchApi<{ items?: unknown[]; defects?: unknown[] }>(path);
  return { defects: data.items || data.defects || [] };
}

function requestValue(record: Record<string, unknown>, camel: string, snake: string): unknown {
  return record[camel] ?? record[snake];
}

/**
 * Keep the browser contract camelCase while accepting the API's snake_case
 * aliases during the rollout. This avoids lossy ticket adapters in views.
 */
export function normalizeBlockRequest(value: Record<string, unknown>): BlockRequest {
  return {
    ...value,
    requestId: String(requestValue(value, 'requestId', 'request_id') ?? ''),
    department: String(value.department ?? 'ENGG') as DepartmentCode,
    status: String(value.status ?? 'REQUESTED'),
    corridorId: String(requestValue(value, 'corridorId', 'corridor_id') ?? ''),
    sectionId: String(requestValue(value, 'sectionId', 'section_id') ?? ''),
    track: String(value.track ?? ''),
    kmStart: Number(requestValue(value, 'kmStart', 'km_start') ?? 0),
    kmEnd: Number(requestValue(value, 'kmEnd', 'km_end') ?? 0),
    taskType: String(requestValue(value, 'taskType', 'task_type') ?? ''),
    severity: Number(value.severity ?? 0),
    estimatedDuration: Number(requestValue(value, 'estimatedDuration', 'estimated_duration') ?? 0),
    blockType: String(requestValue(value, 'blockType', 'block_type') ?? ''),
    requestedStart: requestValue(value, 'requestedStart', 'requested_start') as string | null | undefined,
    requestedEnd: requestValue(value, 'requestedEnd', 'requested_end') as string | null | undefined,
    earliestRequestedStart: requestValue(value, 'earliestRequestedStart', 'earliest_requested_start') as string | null | undefined,
    latestRequestedEnd: requestValue(value, 'latestRequestedEnd', 'latest_requested_end') as string | null | undefined,
    linkedTaskId: requestValue(value, 'linkedTaskId', 'linked_task_id') as string | null | undefined,
    plannedBlockId: requestValue(value, 'plannedBlockId', 'planned_block_id') as string | null | undefined,
    planId: requestValue(value, 'planId', 'plan_id') as string | null | undefined,
    createdAt: (requestValue(value, 'createdAt', 'created_at') ?? value.createdAtUtc) as string | null | undefined,
    updatedAt: (requestValue(value, 'updatedAt', 'updated_at') ?? value.updatedAtUtc) as string | null | undefined,
    allowedActions: Array.isArray(value.allowedActions) ? value.allowedActions.map(String) : [],
    provenance: value.provenance as string | null | undefined,
    synthetic: Boolean(value.synthetic),
  };
}

export interface TicketTaskType {
  taskType: string;
  department: DepartmentCode;
  minDurationMinutes: number;
  assetType: string;
  requiresPTW: boolean;
  requiresT351: boolean;
  requiresCorrespondenceTest: boolean;
}

export interface AssetSummary {
  assetId: string;
  assetType: string;
  sectionId: string;
  track?: string | null;
  kmStart?: number | null;
  kmEnd?: number | null;
  name?: string | null;
}

/** Asset inventory; the composer filters it to the work location's candidates. */
export async function fetchAssets(): Promise<AssetSummary[]> {
  const data = await fetchApi<{ items?: AssetSummary[] }>('/api/v1/assets');
  return data.items || [];
}

/** Per-department task types plus their HC-002 duration floors, server-owned. */
export async function fetchTicketTaskTypes(): Promise<TicketTaskType[]> {
  const data = await fetchApi<{ items?: TicketTaskType[] }>('/api/v1/block-requests/task-types');
  return data.items || [];
}

/** List BlockRequest records without inventing a parallel maintenance-task model. */
export async function fetchBlockRequests(filter?: BlockRequestFilters): Promise<{
  items: BlockRequest[];
  count: number;
  synthetic?: boolean;
}> {
  const params = new URLSearchParams();
  if (filter?.department) params.set('department', filter.department);
  if (filter?.status) params.set('status', filter.status);
  if (filter?.sectionId) params.set('sectionId', filter.sectionId);
  const query = params.toString();
  const data = await fetchApi<{
    items?: Record<string, unknown>[];
    blockRequests?: Record<string, unknown>[];
    count?: number;
    synthetic?: boolean;
  }>(`/api/v1/block-requests${query ? `?${query}` : ''}`);
  const items = (data.items || data.blockRequests || []).map(normalizeBlockRequest);
  return { items, count: data.count ?? items.length, synthetic: data.synthetic };
}

export async function fetchBlockRequest(requestId: string): Promise<BlockRequest> {
  const data = await fetchApi<Record<string, unknown>>(`/api/v1/block-requests/${encodeURIComponent(requestId)}`);
  return normalizeBlockRequest(data);
}

export async function createBlockRequest(payload: CreateBlockRequestPayload): Promise<BlockRequest> {
  const data = await fetchApi<Record<string, unknown>>('/api/v1/block-requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return normalizeBlockRequest(data);
}

export type BlockRequestStatusUpdate = {
  requestId: string;
  status: Extract<BlockRequestStatus, 'READY' | 'REJECTED' | 'CANCELLED'>;
  reason: string;
};

export async function updateBlockRequestStatus(payload: BlockRequestStatusUpdate): Promise<BlockRequest> {
  const data = await fetchApi<Record<string, unknown>>(`/api/v1/block-requests/${encodeURIComponent(payload.requestId)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: payload.status, reason: payload.reason }),
  });
  return normalizeBlockRequest(data);
}

/**
 * Block opportunity and planning endpoints
 */

export async function fetchBlockWindows(sectionId?: string): Promise<{ windows: unknown[] }> {
  const params = new URLSearchParams();
  if (sectionId) params.append('sectionId', sectionId);

  const qs = params.toString();
  const path = `/api/v1/block-windows${qs ? '?' + qs : ''}`;
  const data = await fetchApi<{ items?: unknown[]; windows?: unknown[] }>(path);
  return { windows: data.items || data.windows || [] };
}

export async function fetchBlockPlans(filter?: {
  corridorId?: string;
  status?: string;
}): Promise<{ plans: RailOSPlan[] }> {
  const params = new URLSearchParams();
  if (filter?.corridorId) params.append('corridorId', filter.corridorId);
  if (filter?.status) params.append('status', filter.status);

  const qs = params.toString();
  const path = `/api/v1/block-plans${qs ? '?' + qs : ''}`;
  const data = await fetchApi<{ items?: RailOSPlan[]; plans?: RailOSPlan[] }>(path);
  return { plans: data.items || data.plans || [] };
}

export async function fetchPlanDetail(planId: string): Promise<RailOSPlan> {
  const data = await fetchApi<RailOSPlan>(`/api/v1/block-plans/${planId}`);
  return data;
}

/** Fetch the authority chain for a plan. */
export async function fetchPlanSanctions(planId: string): Promise<SanctionChain> {
  return fetchApi<SanctionChain>(`/api/v1/block-plans/${planId}/sanctions`);
}

/**
 * Record one authority's decision. A partial chain is a successful 202 response,
 * so it intentionally resolves with the chain instead of throwing.
 */
export async function signPlanSanction(
  planId: string,
  payload: {
    authority: SanctionAuthority;
    decision: SignatureDecision;
    reason?: string;
    formReference?: string;
    expectedVersion?: number;
  }
): Promise<SanctionChain | RailOSPlan> {
  return fetchApi<SanctionChain | RailOSPlan>(`/api/v1/block-plans/${planId}/sanctions`, {
    method: 'POST',
    body: JSON.stringify({
      authority: payload.authority,
      decision: payload.decision,
      reason: payload.reason || '',
      formReference: payload.formReference || '',
      expectedVersion: payload.expectedVersion,
    }),
  });
}

export interface PossessionActionPayload {
  note?: string;
  formReference?: string;
  clientEventAtUtc?: string;
  durationMinutes?: number;
  tsrSpeedKmph?: number;
  detonatorCount?: number;
  deferredUntilUtc?: string;
  causeCategory?: string;
  details?: Record<string, unknown>;
}

export async function fetchPossessions(filter?: {
  status?: PossessionState;
  sectionId?: string;
}): Promise<{ items: PossessionView[]; count: number; synthetic?: boolean }> {
  const params = new URLSearchParams();
  if (filter?.status) params.set('status', filter.status);
  if (filter?.sectionId) params.set('sectionId', filter.sectionId);
  const query = params.toString();
  return fetchApi<{ items: PossessionView[]; count: number; synthetic?: boolean }>(
    `/api/v1/possessions${query ? `?${query}` : ''}`
  );
}

/** Return only possession records relevant to the acting field role. */
export async function fetchMyPossessions(): Promise<{ items: PossessionView[]; count: number; synthetic?: boolean }> {
  return fetchApi<{ items: PossessionView[]; count: number; synthetic?: boolean }>('/api/v1/possessions/mine');
}

export async function fetchPossession(possessionId: string): Promise<PossessionView> {
  return fetchApi<PossessionView>(`/api/v1/possessions/${possessionId}`);
}

export async function performPossessionAction(
  possessionId: string,
  action: string,
  payload: PossessionActionPayload = {}
): Promise<PossessionView> {
  return fetchApi<PossessionView>(`/api/v1/possessions/${possessionId}/transitions/${action}`, {
    method: 'POST',
    headers: {
      'Idempotency-Key': `desk-${possessionId}-${action}-${Date.now()}`,
    },
    body: JSON.stringify({
      action,
      note: payload.note || '',
      formReference: payload.formReference || '',
      clientEventAtUtc: payload.clientEventAtUtc,
      durationMinutes: payload.durationMinutes,
      tsrSpeedKmph: payload.tsrSpeedKmph,
      detonatorCount: payload.detonatorCount,
      deferredUntilUtc: payload.deferredUntilUtc,
      causeCategory: payload.causeCategory,
      details: payload.details || {},
    }),
  });
}

/**
 * Analytics endpoints
 */

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const data = await fetchApi<Partial<AnalyticsSummary> & { criticalTasks?: number }>(
    '/api/v1/analytics/summary'
  );
  return {
    maintenanceDebt: data.maintenanceDebt ?? 0,
    criticalDefects: data.criticalDefects ?? data.criticalTasks ?? 0,
    // The API may not expose these legacy aggregates; zero keeps the client
    // honest instead of inventing a live operational value.
    blockUtilization: data.blockUtilization ?? 0,
    trafficPressure: data.trafficPressure ?? 0,
    tasks: data.tasks,
    defects: data.defects,
    overdueTasks: data.overdueTasks,
    completedTasks: data.completedTasks,
    blockBursts: data.blockBursts
      ? {
          totalBursts: data.blockBursts.totalBursts ?? 0,
          totalOverrunMinutes: data.blockBursts.totalOverrunMinutes ?? 0,
          byDepartment: data.blockBursts.byDepartment ?? {},
          byCause: data.blockBursts.byCause ?? {},
          items: data.blockBursts.items ?? [],
        }
      : undefined,
    synthetic: data.synthetic,
  };
}

/** Fetch the audit ledger used by the block-burst analytics view. */
export async function fetchBlockBursts(): Promise<{ items: BlockBurstRecord[]; count: number; synthetic?: boolean }> {
  return fetchApi<{ items: BlockBurstRecord[]; count: number; synthetic?: boolean }>('/api/v1/block-bursts');
}

export async function fetchEventsSince(sequence: number): Promise<{ events: unknown[] }> {
  const params = new URLSearchParams({ after: String(sequence) });
  const data = await fetchApi<{ events: unknown[] }>(`/api/v1/events?${params}`);
  return data;
}

/**
 * Mutation endpoints — state-changing operations
 */

export async function generateOptimization(payload: {
  corridorIds?: string[];
  objectiveProfile?: string;
  planningHorizon?: string;
  taskIds?: string[];
}): Promise<unknown> {
  const data = await fetchApi<unknown>('/api/v1/optimization/generate', {
    method: 'POST',
    body: JSON.stringify({
      corridorIds: payload.corridorIds,
      objective: payload.objectiveProfile || 'BALANCED',
      planningHorizon: payload.planningHorizon || 'WEEKLY',
      taskIds: payload.taskIds,
    }),
  });
  return data;
}

export async function approvePlan(planId: string, reason?: string): Promise<unknown> {
  const data = await fetchApi<unknown>(`/api/v1/block-plans/${planId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason || '' }),
  });
  return data;
}

export async function rejectPlan(planId: string, reason?: string): Promise<unknown> {
  const data = await fetchApi<unknown>(`/api/v1/block-plans/${planId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason || '' }),
  });
  return data;
}

export async function requestPlanRevision(planId: string, reason: string): Promise<unknown> {
  const data = await fetchApi<unknown>(`/api/v1/block-plans/${planId}/request-revision`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
  return data;
}

export async function createDefect(payload: {
  defectId: string;
  assetId: string;
  sectionId: string;
  severityCode: string;
  detectedAtMinute: number;
  taskId?: string;
  repeatCount?: number;
}): Promise<unknown> {
  const data = await fetchApi<unknown>('/api/v1/defects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return data;
}

export async function updateWorkAssignment(
  assignmentId: string,
  payload: { status: string; note?: string }
): Promise<unknown> {
  const data = await fetchApi<unknown>(`/api/v1/work/assignments/${assignmentId}/updates`, {
    method: 'POST',
    body: JSON.stringify({
      status: payload.status,
      note: payload.note || '',
    }),
  });
  return data;
}

export interface EmergencyCreatedResponse {
  id: string;
  replanRequired: boolean;
}

export async function createEmergency(payload: {
  title: string;
  corridorId: string;
  sectionId?: string;
  assetId?: string;
  severity?: string;
  durationMinutes?: number;
}): Promise<EmergencyCreatedResponse> {
  const data = await fetchApi<EmergencyCreatedResponse>('/api/v1/emergencies', {
    method: 'POST',
    body: JSON.stringify({
      title: payload.title,
      corridorId: payload.corridorId,
      sectionId: payload.sectionId,
      assetId: payload.assetId,
      severity: payload.severity,
      durationMinutes: payload.durationMinutes,
    }),
  });
  return data;
}

export async function generateReplanning(payload: {
  parentPlanId: string;
  emergencyId: string;
  nowMinute?: number;
  reason: string;
}): Promise<unknown> {
  const data = await fetchApi<unknown>('/api/v1/replanning/generate', {
    method: 'POST',
    body: JSON.stringify({
      parentPlanId: payload.parentPlanId,
      emergencyId: payload.emergencyId,
      nowMinute: payload.nowMinute ?? 0,
      reason: payload.reason,
    }),
  });
  return data;
}

// --- Field Evidence & Supervisor Admin Endpoints -----------------------------

export interface EvidenceRecord {
  evidenceId: string;
  status: string;
  taskId: string;
  stepId?: string;
  supervisorId: string;
  kind?: string;
  geoVerdict?: string;
  distanceToTargetMeters?: number | null;
  exceptionReason?: string;
  reviewNotes?: string;
  captureTimeUtc?: string;
  ed25519Signature?: string | null;
  gpsAccuracyMeters?: number | null;
  originalSha256?: string;
  proofDownloadUrl?: string;
  originalDownloadUrl?: string;
  proofSha256?: string;
  startLatitude?: number | null;
  startLongitude?: number | null;
  [key: string]: unknown;
}

export interface SupervisorRecord {
  userId: string;
  employeeId: string;
  name: string;
  assignedSections?: string[];
  [key: string]: unknown;
}

export async function getEvidenceList(params?: {
  status?: string;
  taskId?: string;
}): Promise<{ items: EvidenceRecord[]; count: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.taskId) query.set('task_id', params.taskId);
  const qStr = query.toString();
  return fetchApi<{ items: EvidenceRecord[]; count: number }>(`/api/v1/evidence${qStr ? `?${qStr}` : ''}`, {
  });
}

export async function getEvidenceDetails(evidenceId: string): Promise<EvidenceRecord> {
  return fetchApi<EvidenceRecord>(`/api/v1/evidence/${evidenceId}`, {
  });
}

export async function reviewEvidence(
  evidenceId: string,
  decision: 'ACCEPT' | 'REJECT',
  reviewNotes: string
): Promise<EvidenceRecord> {
  return fetchApi<EvidenceRecord>(`/api/v1/evidence/${evidenceId}:review`, {
    method: 'POST',
    body: JSON.stringify({ decision, reviewNotes }),
  });
}

export async function getSupervisorsList(): Promise<{ items: SupervisorRecord[]; count: number }> {
  return fetchApi<{ items: SupervisorRecord[]; count: number }>('/api/v1/admin/supervisors', {
  });
}

export async function createSupervisorAccount(payload: {
  employeeId: string;
  name: string;
  password: string;
  role?: string;
  assignedSectionCodes?: string[];
}): Promise<SupervisorRecord> {
  return fetchApi<SupervisorRecord>('/api/v1/admin/supervisors', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateSupervisorAreas(
  supervisorId: string,
  sectionCodes: string[]
): Promise<SupervisorRecord> {
  return fetchApi<SupervisorRecord>(`/api/v1/admin/supervisors/${supervisorId}/areas`, {
    method: 'PUT',
    body: JSON.stringify({ sectionCodes }),
  });
}

