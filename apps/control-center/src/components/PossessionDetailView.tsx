'use client';

import { useCallback, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, Circle, FileCheck2, History, Shield, Zap } from 'lucide-react';
import { usePossession, usePossessionAction } from '@/lib/queries';
import type { PossessionActionPayload } from '@/lib/api';
import { useRailOSEventStream } from '@/lib/useRailOSEventStream';
import { getTokenDef, POSSESSION_STATE_TOKENS } from './tokens';
import { StatusChip } from './StatusChip';
import { Modal } from './ui/Modal';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';

const STAGES = [
  { number: 5, label: 'Clearance', states: ['SANCTIONED', 'CLEARANCE_REQUESTED', 'DEFERRED', 'CLEARANCE_GRANTED'] },
  { number: 6, label: 'Isolation & protection', states: ['ISOLATION_IN_PROGRESS', 'PROTECTED'] },
  { number: 7, label: 'Live work', states: ['LIVE', 'OVERRUNNING'] },
  { number: 8, label: 'Testing & handback', states: ['TESTING', 'HANDBACK_REQUESTED', 'FIT_CERTIFIED'] },
  { number: 9, label: 'Normalised', states: ['CLEARED'] },
];

function formatUtc(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' }).format(date);
}

function actionLabel(action: string) {
  return action.replaceAll('-', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}

export function PossessionDetailView({ possessionId }: { possessionId: string }) {
  const possessionQuery = usePossession(possessionId);
  const actionMutation = usePossessionAction();
  const [activeAction, setActiveAction] = useState('');
  const [note, setNote] = useState('');
  const [formReference, setFormReference] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('30');
  const [tsrSpeedKmph, setTsrSpeedKmph] = useState('20');
  const [detonatorCount, setDetonatorCount] = useState('3');
  const [deferredUntilUtc, setDeferredUntilUtc] = useState('');
  const [causeCategory, setCauseCategory] = useState('');
  const [notice, setNotice] = useState('');
  useRailOSEventStream();
  const closeAction = useCallback(() => setActiveAction(''), []);

  const possession = possessionQuery.data;
  const currentStage = possession ? STAGES.findIndex((stage) => stage.states.includes(possession.state)) : -1;

  const openAction = (action: string) => {
    if (!possession?.allowedActions.includes(action)) return;
    setActiveAction(action);
    setNote('');
    setFormReference('');
    setDurationMinutes('30');
    setTsrSpeedKmph('20');
    setDetonatorCount('3');
    setDeferredUntilUtc('');
    setCauseCategory('');
    setNotice('');
  };

  const submitAction = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!possession || !activeAction || !possession.allowedActions.includes(activeAction)) return;
    const payload: PossessionActionPayload = {
      note: note.trim() || undefined,
      formReference: formReference.trim() || undefined,
      durationMinutes: activeAction === 'record-correspondence-test' ? Number(durationMinutes) : undefined,
      tsrSpeedKmph: activeAction === 'certify-fitness' ? Number(tsrSpeedKmph) : undefined,
      detonatorCount: activeAction === 'plant-protection' ? Number(detonatorCount) : undefined,
      deferredUntilUtc: activeAction === 'defer' ? deferredUntilUtc || undefined : undefined,
      causeCategory: (activeAction === 'close' || activeAction === 'declare-overrun') ? causeCategory.trim() || undefined : undefined,
    };
    actionMutation.mutate(
      { possessionId: possession.possessionId, action: activeAction, payload },
      { onSuccess: () => setNotice(`${actionLabel(activeAction)} accepted by RailOS.`) }
    );
    setActiveAction('');
  };

  if (possessionQuery.isLoading) return <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-6 text-sm text-[var(--text-secondary)]" role="status">Loading possession detail…</div>;
  if (possessionQuery.isError || !possession) return <div className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-6 text-sm text-[var(--status-critical-text)]" role="alert"><p className="font-semibold">Possession detail unavailable</p><p className="mt-1">{possessionQuery.error?.message || 'The requested possession was not found.'}</p><Link href="/possessions" className="mt-4 inline-flex min-h-11 items-center rounded border border-[var(--status-critical-border)] px-3 font-semibold">Return to possession board</Link></div>;

  return (
    <div className="space-y-5" aria-labelledby="possession-detail-title">
      <Link href="/possessions" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]"><ArrowLeft className="h-4 w-4" aria-hidden="true" /> Possession board</Link>
      <header className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Runtime record · {possession.possessionId}</p>
            <h1 id="possession-detail-title" className="mt-1 text-xl font-bold text-[var(--text-primary)]">{possession.sectionId} · {possession.track} track</h1>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">Block {possession.blockId} · plan {possession.planId} version {possession.planVersion}</p>
          </div>
          <StatusChip def={getTokenDef(POSSESSION_STATE_TOKENS, possession.state)} />
        </div>
        {notice && <p className="mt-4 rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] p-3 text-sm text-[var(--status-ok-text)]" role="status">{notice}</p>}
        {actionMutation.isError && <p className="mt-4 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-3 text-sm text-[var(--status-critical-text)]" role="alert">{actionMutation.error.message}</p>}
      </header>

      <section aria-labelledby="possession-stage-title" className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <h2 id="possession-stage-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Lifecycle spine</h2>
        <ol className="mt-4 grid gap-3 md:grid-cols-5" aria-label="Possession lifecycle stages">
          {STAGES.map((stage, index) => {
            const complete = currentStage > index || possession.state === 'CLEARED';
            const active = currentStage === index;
            return <li key={stage.number} aria-current={active ? 'step' : undefined} className={`rounded border p-3 ${active ? 'border-[var(--accent)] bg-[var(--status-caution-bg)]' : complete ? 'border-[var(--status-ok-border)] bg-[var(--status-ok-bg)]' : 'border-[var(--border-subtle)] bg-[var(--bg-elevated)]'}`}><div className="flex items-center gap-2"><span className="font-mono text-xs font-bold text-[var(--text-muted)]">Stage {stage.number}</span>{complete && <CheckCircle2 className="h-4 w-4 text-[var(--status-ok-fg)]" aria-label="Complete" />}</div><p className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{stage.label}</p>{active && <p className="mt-1 text-xs text-[var(--accent)]">Current state: {possession.state.replaceAll('_', ' ')}</p>}</li>;
          })}
        </ol>
      </section>

      <section aria-labelledby="possession-actions-title" className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div className="flex items-center gap-2"><Zap className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" /><h2 id="possession-actions-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Server-authorized actions</h2></div>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Only actions returned by the API for this state and acting role are enabled.</p>
        <div className="mt-4 flex flex-wrap gap-2">{possession.allowedActions.length ? possession.allowedActions.map((action) => <button key={action} type="button" onClick={() => openAction(action)} disabled={actionMutation.isPending} className="min-h-11 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 text-xs font-semibold text-[var(--text-primary)] hover:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50">{actionLabel(action)}</button>) : <span className="text-sm text-[var(--text-muted)]">No action is available to the current acting role at this stage.</span>}</div>
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <section aria-labelledby="artefact-title" className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
          <h2 id="artefact-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Safety artefacts</h2>
          <div className="mt-4 grid gap-3">
            <article className="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4"><div className="flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" /><h3 className="font-mono text-sm font-bold text-[var(--text-primary)]">Form T/351</h3></div>{possession.formT351 ? <dl className="mt-3 grid gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)] sm:grid-cols-2"><div><dt className="inline text-[var(--text-muted)]">Form: </dt><dd className="inline font-mono text-[var(--text-primary)]">{possession.formT351.formNumber}</dd></div><div><dt className="inline text-[var(--text-muted)]">Status: </dt><dd className="inline font-mono text-[var(--text-primary)]">{possession.formT351.status}</dd></div><div><dt className="inline text-[var(--text-muted)]">Issued by: </dt><dd className="inline">{possession.formT351.issuedBy}</dd></div><div><dt className="inline text-[var(--text-muted)]">Endorsed by: </dt><dd className="inline">{possession.formT351.endorsedBy || 'Awaiting Station Master'}</dd></div></dl> : <p className="mt-3 text-sm text-[var(--text-secondary)]">Not issued. Required: {possession.requiresT351 ? 'yes' : 'no'}.</p>}</article>
            <article className="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4"><div className="flex items-center gap-2"><Shield className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" /><h3 className="font-mono text-sm font-bold text-[var(--text-primary)]">Permit to Work</h3></div>{possession.permitToWork ? <dl className="mt-3 grid gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)] sm:grid-cols-2"><div><dt className="inline text-[var(--text-muted)]">Permit: </dt><dd className="inline font-mono text-[var(--text-primary)]">{possession.permitToWork.ptwNumber}</dd></div><div><dt className="inline text-[var(--text-muted)]">Status: </dt><dd className="inline font-mono text-[var(--text-primary)]">{possession.permitToWork.status}</dd></div><div><dt className="inline text-[var(--text-muted)]">Isolator: </dt><dd className="inline font-mono text-[var(--text-primary)]">{possession.permitToWork.isolatorNumber}</dd></div><div><dt className="inline text-[var(--text-muted)]">Earthing: </dt><dd className="inline">{possession.permitToWork.earthingConfirmed ? 'Confirmed' : 'Pending'}</dd></div></dl> : <p className="mt-3 text-sm text-[var(--text-secondary)]">Not issued. Required: {possession.requiresPTW ? 'yes' : 'no'}.</p>}</article>
          </div>
        </section>

        <section aria-labelledby="handback-title" className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
          <h2 id="handback-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Handback checklist</h2>
          <ul className="mt-4 divide-y divide-[var(--border-subtle)] rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)]">{possession.handbackChecklist.map((item) => <li key={`${item.item}-${item.rule}`} className="flex items-start gap-3 p-3">{item.satisfied ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--status-ok-fg)]" aria-label="Satisfied" /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-label="Outstanding" />}<div><p className="text-sm text-[var(--text-primary)]">{item.item}</p><p className="mt-1 font-mono text-xs text-[var(--text-muted)]">{item.rule}</p></div></li>)}</ul>
        </section>
      </div>

      <section aria-labelledby="timeline-title" className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div className="flex items-center gap-2"><History className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" /><h2 id="timeline-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Transition timeline</h2></div>
        <div className="mt-4"><Table caption="Possession transition audit timeline"><TableHeader><tr><TableHeaderCell>Time</TableHeaderCell><TableHeaderCell>Transition</TableHeaderCell><TableHeaderCell>Actor / role</TableHeaderCell><TableHeaderCell>Rule</TableHeaderCell></tr></TableHeader><TableBody>{possession.transitions.map((transition) => <tr key={transition.transitionId}><TableCell className="font-mono text-xs text-[var(--text-secondary)]">{formatUtc(transition.occurredAtUtc)}</TableCell><TableCell><div className="flex flex-wrap items-center gap-2"><StatusChip def={getTokenDef(POSSESSION_STATE_TOKENS, transition.fromState)} compact /><span aria-hidden="true">→</span><StatusChip def={getTokenDef(POSSESSION_STATE_TOKENS, transition.toState)} compact /></div><p className="mt-1 text-xs text-[var(--text-secondary)]">{actionLabel(transition.action)}{transition.replayed ? ' · replayed' : ''}</p></TableCell><TableCell><div className="font-mono text-xs text-[var(--text-primary)]">{transition.actor}</div><div className="mt-1 text-xs text-[var(--text-secondary)]">{transition.role}</div></TableCell><TableCell className="font-mono text-xs text-[var(--text-secondary)]">{transition.ruleCitation || '—'}</TableCell></tr>)}</TableBody></Table></div>
        {!possession.transitions.length && <p className="mt-3 text-sm text-[var(--text-muted)]">No transitions recorded yet.</p>}
      </section>

      <Modal open={Boolean(activeAction)} title={activeAction ? actionLabel(activeAction) : 'Possession action'} description={`${possession.possessionId} · RailOS will validate this transition`} onClose={closeAction}>
        <form onSubmit={submitAction} className="space-y-4">
          {activeAction === 'record-correspondence-test' && <div><label htmlFor="detail-test-duration" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Test duration (minutes)</label><input id="detail-test-duration" type="number" min={30} value={durationMinutes} onChange={(event) => setDurationMinutes(event.target.value)} required className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]" /><p className="mt-1 text-xs text-[var(--text-muted)]">HC-006 requires a minimum of 30 minutes.</p></div>}
          {activeAction === 'certify-fitness' && <div><label htmlFor="detail-tsr" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Initial TSR speed (km/h)</label><select id="detail-tsr" value={tsrSpeedKmph} onChange={(event) => setTsrSpeedKmph(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]"><option value="20">20</option><option value="45">45</option><option value="75">75</option></select></div>}
          {activeAction === 'plant-protection' && <div><label htmlFor="detail-detonators" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Detonator count</label><input id="detail-detonators" type="number" min={1} value={detonatorCount} onChange={(event) => setDetonatorCount(event.target.value)} required className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]" /></div>}
          {activeAction === 'defer' && <div><label htmlFor="detail-deferred-until" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Deferred until (UTC)</label><input id="detail-deferred-until" type="datetime-local" value={deferredUntilUtc} onChange={(event) => setDeferredUntilUtc(event.target.value)} required className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]" /></div>}
          {(activeAction === 'issue-t351' || activeAction === 'issue-ptw') && <div><label htmlFor="detail-form-reference" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Form reference <span className="font-normal text-[var(--text-muted)]">(optional)</span></label><input id="detail-form-reference" value={formReference} onChange={(event) => setFormReference(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]" /></div>}
          {(activeAction === 'close' || activeAction === 'declare-overrun') && <div><label htmlFor="detail-cause" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Cause category <span className="font-normal text-[var(--text-muted)]">(optional)</span></label><input id="detail-cause" value={causeCategory} onChange={(event) => setCauseCategory(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 font-mono text-[var(--text-primary)]" /></div>}
          <div><label htmlFor="detail-action-note" className="mb-1 block text-sm font-semibold text-[var(--text-secondary)]">Audit note <span className="font-normal text-[var(--text-muted)]">(optional)</span></label><textarea id="detail-action-note" rows={3} value={note} onChange={(event) => setNote(event.target.value)} className="w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]" /></div>
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setActiveAction('')} className="min-h-11 rounded border border-[var(--border-strong)] px-4 text-sm font-semibold text-[var(--text-primary)]">Cancel</button><button type="submit" disabled={actionMutation.isPending || (activeAction === 'record-correspondence-test' && Number(durationMinutes) < 30)} className="min-h-11 rounded border border-[var(--accent)] bg-[var(--accent)] px-4 text-sm font-bold text-[var(--bg-canvas)] disabled:opacity-50">{actionMutation.isPending ? 'Submitting…' : 'Submit action'}</button></div>
        </form>
      </Modal>
    </div>
  );
}
