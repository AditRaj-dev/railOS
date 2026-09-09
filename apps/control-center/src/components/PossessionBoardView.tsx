'use client';

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { AlertTriangle, Radio, RefreshCw, ShieldCheck } from 'lucide-react';
import { usePossessionAction, usePossessions } from '@/lib/queries';
import type { PossessionActionPayload, PossessionView } from '@/lib/api';
import { getTokenDef, POSSESSION_STATE_TOKENS } from './tokens';
import { StatusChip } from './StatusChip';
import { Modal } from './ui/Modal';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

type InlineAction = 'grant-clearance' | 'defer' | 'cancel' | 'close';

const ACTION_LABELS: Record<InlineAction, string> = {
  'grant-clearance': 'Grant clearance',
  defer: 'Defer',
  cancel: 'Cancel',
  close: 'Close block',
};

function formatUtc(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date);
}

function liveOverrunMinutes(possession: PossessionView, now: number) {
  const serverMinutes = possession.overrunMinutesLive || 0;
  if (!['LIVE', 'OVERRUNNING'].includes(possession.state)) return serverMinutes;
  const end = new Date(possession.plannedEndUtc).getTime();
  if (!Number.isFinite(end)) return serverMinutes;
  return Math.max(serverMinutes, Math.max(0, Math.floor((now - end) / 60_000)));
}

function actionIsInline(value: string): value is InlineAction {
  return value in ACTION_LABELS;
}

export function PossessionBoardView() {
  const possessionsQuery = usePossessions();
  const possessionMutation = usePossessionAction();
  const [now, setNow] = useState(() => Date.now());
  const [modal, setModal] = useState<{ possession: PossessionView; action: InlineAction } | null>(null);
  const [note, setNote] = useState('');
  const [deferredUntil, setDeferredUntil] = useState('');
  const [causeCategory, setCauseCategory] = useState('EXECUTION');
  const [notice, setNotice] = useState('');

  const closeModal = useCallback(() => setModal(null), []);

  // A short local clock keeps the overrun visible between server events. The
  // server-provided value remains the floor and source of truth after refresh.
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const possessions = possessionsQuery.data?.items || [];

  const openModal = (possession: PossessionView, action: InlineAction) => {
    setNotice('');
    setNote('');
    setDeferredUntil('');
    setCauseCategory('EXECUTION');
    setModal({ possession, action });
  };

  const runAction = (possession: PossessionView, action: string, payload: PossessionActionPayload = {}) => {
    if (!possession.allowedActions.includes(action)) return;
    setNotice('');
    possessionMutation.mutate(
      { possessionId: possession.possessionId, action, payload },
      {
        onSuccess: () => setNotice(`${action.replaceAll('-', ' ')} accepted for ${possession.possessionId}.`),
      }
    );
  };

  const submitModal = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!modal || !modal.possession.allowedActions.includes(modal.action)) return;
    const payload: PossessionActionPayload = {
      note: note.trim(),
      causeCategory: modal.action === 'close' ? causeCategory : undefined,
      deferredUntilUtc: modal.action === 'defer' && deferredUntil ? new Date(deferredUntil).toISOString() : undefined,
    };
    runAction(modal.possession, modal.action, payload);
    setModal(null);
  };

  return (
    <div className="space-y-5">
      <header className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Stages 5 & 9 · day-of control</p>
            <h1 className="mt-1 text-xl font-bold text-[var(--text-primary)]">Possession board</h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--text-secondary)]">Live block windows, server-authorized actions, and overrun visibility for the Section Controller.</p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)]" role="status" aria-live="polite">
            <span className="inline-flex items-center gap-1.5"><Radio className="h-4 w-4 text-[var(--status-ok-fg)]" aria-hidden="true" /> event stream active</span>
            <button type="button" onClick={() => possessionsQuery.refetch()} disabled={possessionsQuery.isFetching} aria-label="Refresh possessions" className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 text-[var(--text-primary)] hover:border-[var(--accent)] disabled:opacity-50">
              <RefreshCw className={`h-3.5 w-3.5 ${possessionsQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" /> Refresh
            </button>
          </div>
        </div>
      </header>

      {notice && <div className="rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] p-3 text-sm text-[var(--status-ok-text)]" role="status">{notice}</div>}
      {possessionMutation.isError && <div className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-3 text-sm text-[var(--status-critical-text)]" role="alert">{possessionMutation.error.message}</div>}
      {possessionsQuery.isLoading && <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5 text-sm text-[var(--text-secondary)]" role="status">Loading possession state…</div>}
      {possessionsQuery.isError && <div className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-4 text-sm text-[var(--status-critical-text)]" role="alert"><p className="font-semibold">Possession feed unavailable</p><p className="mt-1">{possessionsQuery.error.message}</p></div>}

      {!possessionsQuery.isLoading && !possessionsQuery.isError && possessions.length === 0 && (
        <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-8 text-center" role="status">
          <ShieldCheck className="mx-auto h-8 w-8 text-[var(--text-muted)]" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">No possessions are open</p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Complete a plan sanction chain to open the day-of block records.</p>
        </div>
      )}

      {possessions.length > 0 && (
        <section aria-labelledby="possession-table-title" className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 id="possession-table-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Open possession records <span className="font-normal text-[var(--text-muted)]">({possessions.length})</span></h2>
            <span className="text-xs text-[var(--text-muted)]">Actions are filtered by the API for your acting role.</span>
          </div>
          <Table caption="Live railway possession records">
            <TableHeader><tr><TableHeaderCell>Section / track</TableHeaderCell><TableHeaderCell>State</TableHeaderCell><TableHeaderCell>Planned window</TableHeaderCell><TableHeaderCell>Live overrun</TableHeaderCell><TableHeaderCell>Authority actions</TableHeaderCell></tr></TableHeader>
            <TableBody>
              {possessions.map((possession) => {
                const overrun = liveOverrunMinutes(possession, now);
                const inlineActions = possession.allowedActions.filter(actionIsInline);
                return (
                  <tr key={possession.possessionId} className={possession.state === 'OVERRUNNING' ? 'bg-[var(--status-critical-bg)]/30' : undefined}>
                    <TableCell>
                      <Link href={`/possessions/${encodeURIComponent(possession.possessionId)}`} className="font-mono font-semibold text-[var(--text-primary)] underline decoration-[var(--border-strong)] underline-offset-4 hover:text-[var(--accent)]">{possession.sectionId}</Link>
                      <div className="mt-1 text-xs text-[var(--text-secondary)]">{possession.track} · {possession.possessionId}</div>
                      <div className="mt-1 text-xs text-[var(--text-muted)]">Block {possession.blockId}</div>
                    </TableCell>
                    <TableCell><StatusChip def={getTokenDef(POSSESSION_STATE_TOKENS, possession.state)} compact /></TableCell>
                    <TableCell><div className="font-mono text-xs text-[var(--text-primary)]">{formatUtc(possession.plannedStartUtc)}</div><div className="mt-1 font-mono text-xs text-[var(--text-secondary)]">to {formatUtc(possession.plannedEndUtc)}</div></TableCell>
                    <TableCell>
                      {overrun > 0 ? <span className="inline-flex items-center gap-1.5 font-mono text-sm font-bold text-[var(--status-critical-text)]"><AlertTriangle className="h-4 w-4" aria-hidden="true" /> +{overrun} min</span> : <span className="font-mono text-sm text-[var(--text-muted)]">—</span>}
                    </TableCell>
                    <TableCell>
                      {inlineActions.length > 0 ? <div className="flex flex-wrap gap-2">{inlineActions.map((action) => <button key={action} type="button" onClick={() => action === 'grant-clearance' ? runAction(possession, action) : openModal(possession, action)} disabled={possessionMutation.isPending} className={`min-h-11 rounded border px-3 text-xs font-semibold ${action === 'cancel' ? 'border-[var(--status-critical-border)] text-[var(--status-critical-text)] hover:bg-[var(--status-critical-bg)]' : 'border-[var(--border-strong)] bg-[var(--bg-elevated)] text-[var(--text-primary)] hover:border-[var(--accent)]'} disabled:cursor-not-allowed disabled:opacity-50`}>{ACTION_LABELS[action]}</button>)}</div> : <span className="text-xs text-[var(--text-muted)]">No control action available</span>}
                    </TableCell>
                  </tr>
                );
              })}
            </TableBody>
          </Table>
        </section>
      )}

      <Modal
        open={Boolean(modal)}
        title={modal ? ACTION_LABELS[modal.action] : 'Possession action'}
        description={modal ? `${modal.possession.possessionId} · ${modal.possession.sectionId} ${modal.possession.track}` : undefined}
        onClose={closeModal}
      >
        {modal && (
          <form onSubmit={submitModal} className="space-y-4">
            {modal.action === 'defer' && <div><label htmlFor="defer-until" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">New clearance window <span className="font-normal text-[var(--text-muted)]">(optional)</span></label><input id="defer-until" type="datetime-local" value={deferredUntil} onChange={(event) => setDeferredUntil(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm font-mono text-[var(--text-primary)]" /></div>}
            {modal.action === 'close' && <div><label htmlFor="burst-cause" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Block-burst cause</label><select id="burst-cause" value={causeCategory} onChange={(event) => setCauseCategory(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)]"><option value="EXECUTION">Execution</option><option value="TRAFFIC">Traffic regulation</option><option value="ISOLATION">Isolation / handback</option><option value="WEATHER">Weather</option></select></div>}
            <div><label htmlFor="possession-note" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Audit note <span className="font-normal text-[var(--text-muted)]">(optional)</span></label><textarea id="possession-note" rows={3} value={note} onChange={(event) => setNote(event.target.value)} className="w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]" placeholder="Record the operational reason" /></div>
            <div className="flex justify-end gap-2"><button type="button" onClick={() => setModal(null)} className="min-h-11 rounded border border-[var(--border-strong)] px-4 text-sm font-semibold text-[var(--text-primary)]">Keep open</button><button type="submit" disabled={possessionMutation.isPending} className="min-h-11 rounded border border-[var(--accent)] bg-[var(--accent)] px-4 text-sm font-bold text-[var(--bg-canvas)] disabled:opacity-50">{possessionMutation.isPending ? 'Submitting…' : ACTION_LABELS[modal.action]}</button></div>
          </form>
        )}
      </Modal>
    </div>
  );
}

export { liveOverrunMinutes };
