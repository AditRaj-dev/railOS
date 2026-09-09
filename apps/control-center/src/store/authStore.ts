'use client';

import { create } from 'zustand';
import * as api from '@/lib/api';
import type { AuthSession } from '@/lib/api';
import { useRailOSStore, type UserRole } from './railosStore';

const STORAGE_KEY = 'railos-auth-refresh';

/** railos_model.UserRole (backend account roles) -> the frontend's operational role
 * vocabulary, mirroring roles.py's ROLE_ALIASES so a real login lands on the same
 * nav/query context a synthetic-header selection of the equivalent role would. */
const BACKEND_ROLE_TO_FRONTEND: Record<string, UserRole> = {
  SUPERVISOR: 'FIELD_SUPERVISOR',
  DISPATCHER: 'CONTROL_OFFICER',
  INSPECTOR: 'MANAGEMENT',
  ADMIN: 'ADMIN',
  CONTROL_OFFICER: 'CONTROL_OFFICER',
  STATION_MASTER: 'STATION_MASTER',
  TPC: 'TPC',
  ENGINEERING: 'ENGINEERING',
  SIGNAL_TELECOM: 'SIGNAL_TELECOM',
  PLANNER: 'PLANNER',
  TRACTION: 'TRACTION',
  FIELD_SUPERVISOR: 'FIELD_SUPERVISOR',
  MANAGEMENT: 'MANAGEMENT',
};

function toFrontendRole(role: string): UserRole {
  return BACKEND_ROLE_TO_FRONTEND[role.toUpperCase()] ?? 'FIELD_SUPERVISOR';
}

interface PersistedRefresh {
  refreshToken: string;
}

function persistRefreshToken(refreshToken: string) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ refreshToken } satisfies PersistedRefresh));
  } catch {
    // Private browsing / storage disabled — session just won't survive a reload.
  }
}

function readPersistedRefreshToken(): string | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedRefresh;
    return parsed.refreshToken || null;
  } catch {
    return null;
  }
}

function clearPersistedRefreshToken() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore.
  }
}

interface AuthStoreState {
  session: AuthSession | null;
  status: 'idle' | 'restoring' | 'authenticated' | 'unauthenticated';
  error: string | null;
  login: (employeeId: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  clearError: () => void;
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let sessionRevision = 0;

function clearRefreshTimer() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

function scheduleRefresh(session: AuthSession, refresh: () => Promise<void>) {
  clearRefreshTimer();
  // Refresh ~60s before expiry (access tokens are short-lived, 15 minutes by default).
  const delay = Math.max(5_000, session.expiresAt - Date.now() - 60_000);
  refreshTimer = setTimeout(() => {
    void refresh();
  }, delay);
}

function applySession(session: AuthSession) {
  api.setAuthSession(session);
  api.setApiRole(toFrontendRole(session.role));
  useRailOSStore.getState().setUserRole(toFrontendRole(session.role));
  persistRefreshToken(session.refreshToken);
}

export const useAuthStore = create<AuthStoreState>((set, get) => {
  // Keep the store in sync with a transparent refresh triggered internally by
  // api.ts (e.g. a 401 retry mid-request), and fall back to synthetic mode
  // cleanly if the refresh token itself has expired or been revoked.
  api.setSessionSyncHandlers({
    onRefreshed: (session) => {
      applySession(session);
      set({ session, status: 'authenticated', error: null });
      scheduleRefresh(session, async () => {
        await get().restoreSession();
      });
    },
    onExpired: () => {
      // A failure here can be for a refresh token a concurrent call already
      // rotated past (the in-flight dedup only covers callers that overlap in
      // time; a staggered caller can still capture a token, get delayed, and
      // fail against it after a sibling call already succeeded). Don't tear
      // down a session a sibling call has already legitimately established.
      if (api.getAuthSession()) return;
      clearRefreshTimer();
      clearPersistedRefreshToken();
      set({ session: null, status: 'unauthenticated' });
    },
  });

  return {
    session: null,
    status: 'idle',
    error: null,

    login: async (employeeId, password) => {
      const revision = ++sessionRevision;
      set({ error: null });
      try {
        const result = await api.authLogin(employeeId, password);
        if (revision !== sessionRevision) return;
        const session = {
          accessToken: result.accessToken,
          refreshToken: result.refreshToken,
          expiresAt: Date.now() + result.expiresInSeconds * 1000,
          userId: result.userId,
          role: result.role,
          employeeId: result.employeeId,
          name: result.name,
        };
        applySession(session);
        set({ session, status: 'authenticated', error: null });
        scheduleRefresh(session, async () => {
          await get().restoreSession();
        });
      } catch (err) {
        const message = err instanceof api.RailOSApiError ? err.message : 'Login failed';
        set({ error: message });
        throw err;
      }
    },

    logout: async () => {
      sessionRevision += 1;
      const session = get().session;
      clearRefreshTimer();
      clearPersistedRefreshToken();
      api.setAuthSession(null);
      set({ session: null, status: 'unauthenticated', error: null });
      if (session?.refreshToken) {
        try {
          await api.authLogout(session.refreshToken);
        } catch {
          // Best-effort; the session is already cleared client-side.
        }
      }
    },

    restoreSession: async () => {
      const revision = sessionRevision;
      const refreshToken = readPersistedRefreshToken();
      if (!refreshToken) {
        set({ status: 'unauthenticated' });
        return;
      }
      set({ status: 'restoring' });
      try {
        const result = await api.refreshSession(refreshToken);
        if (revision !== sessionRevision) return;
        const session = {
          accessToken: result.accessToken,
          refreshToken: result.refreshToken,
          expiresAt: Date.now() + result.expiresInSeconds * 1000,
          userId: result.userId,
          role: result.role,
          employeeId: result.employeeId,
          name: result.name,
        };
        applySession(session);
        set({ session, status: 'authenticated', error: null });
        scheduleRefresh(session, async () => {
          await get().restoreSession();
        });
      } catch {
        if (revision !== sessionRevision) return;
        // Same staggered-caller race as onExpired above: this refreshToken may
        // already have been rotated past by a concurrent success.
        if (get().status === 'authenticated') return;
        clearPersistedRefreshToken();
        api.setAuthSession(null);
        set({ session: null, status: 'unauthenticated' });
      }
    },

    clearError: () => set({ error: null }),
  };
});
