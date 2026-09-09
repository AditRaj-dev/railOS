'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getApiRole, getAuthSession } from './api';
import { useRailOSStore } from '@/store/railosStore';

function eventSocketUrl(role: string): string {
  const configured = process.env.NEXT_PUBLIC_RAILOS_API_URL || 'http://localhost:8000';
  const base = configured.replace(/^http/i, 'ws').replace(/\/$/, '');
  const session = getAuthSession();
  const query = session
    ? new URLSearchParams({ access_token: session.accessToken })
    : new URLSearchParams({ user: 'demo-user', role });
  return `${base}/api/v1/events/ws?${query.toString()}`;
}

/**
 * Invalidate server-state caches when the API event stream reports a change.
 * The API remains authoritative; the socket only acts as a near-real-time
 * invalidation signal and never becomes a second client-side data store.
 */
export function useRailOSEventStream(enabled = true) {
  const queryClient = useQueryClient();
  const role = useRailOSStore((state) => state.userRole);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined' || typeof WebSocket === 'undefined') return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;

    const invalidateForEvent = (value: unknown) => {
      const event = value && typeof value === 'object' ? value as { type?: string; events?: unknown[] } : {};
      const events = Array.isArray(event.events) ? event.events : [event];
      if (!events.some((item) => {
        const type = item && typeof item === 'object' ? (item as { type?: string }).type || '' : '';
        return type.startsWith('POSSESSION_')
          || type.startsWith('PLAN_SANCTION')
          || type === 'PLAN_APPROVED'
          || type === 'BLOCK_BURST_RECORDED'
          || type.startsWith('BLOCK_REQUEST_')
          || type.startsWith('TASK_')
          || type.startsWith('DEFECT_')
          || type.startsWith('EVIDENCE_')
          || type === 'DEMO_RESET'
          || type === 'PLAN_GENERATED';
      })) return;

      queryClient.invalidateQueries({ queryKey: ['possessions'] });
      queryClient.invalidateQueries({ queryKey: ['sanctions'] });
      queryClient.invalidateQueries({ queryKey: ['blockBursts'] });
      queryClient.invalidateQueries({ queryKey: ['planning', 'blockPlans'] });
      queryClient.invalidateQueries({ queryKey: ['planning', 'plans'] });
      queryClient.invalidateQueries({ queryKey: ['planning', 'blockWindows'] });
      queryClient.invalidateQueries({ queryKey: ['maintenance', 'tasks'] });
      queryClient.invalidateQueries({ queryKey: ['blockRequests'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'summary'] });
    };

    const connect = () => {
      if (disposed) return;
      try {
        socket = new WebSocket(eventSocketUrl(getApiRole() || role));
        socket.onmessage = (message) => {
          try {
            invalidateForEvent(JSON.parse(message.data as string));
          } catch {
            // Ignore malformed event frames; the next authoritative refetch wins.
          }
        };
        socket.onclose = () => {
          if (!disposed) reconnectTimer = setTimeout(connect, 15_000);
        };
        socket.onerror = () => socket?.close();
      } catch {
        reconnectTimer = setTimeout(connect, 15_000);
      }
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
      socket = null;
    };
  }, [enabled, queryClient, role]);
}

export { eventSocketUrl };
