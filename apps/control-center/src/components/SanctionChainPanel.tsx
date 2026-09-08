'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { CheckCircle2, FileSignature, LockKeyhole, UserRound } from 'lucide-react';
import {
  usePlanSanctions,
  useSignPlanSanction,
} from '@/lib/queries';
import type {
  RailOSPlan,
  SanctionAuthority,
  SanctionChain,
  SignatureDecision,
} from '@/lib/api';
import { useRailOSStore, type UserRole } from '@/store/railosStore';
import {
  getTokenDef,
  PLAN_STATUS_TOKENS,
  SIGNATURE_DECISION_TOKENS,
} from './tokens';
import { StatusChip } from './StatusChip';

const AUTHORITY_LABELS: Record<SanctionAuthority, string> = {
  SANCTION: 'Sr. DOM / Management',
  SECTION_CONTROL: 'Section Controller',
  TRACTION_POWER: 'Traction Power Controller',
  STATION: 'Station Master',
  SNT: 'Signal & Telecom',
  ENGINEERING_SSE: 'SSE / Engineering',
};

const ROLE_AUTHORITIES: Partial<Record<UserRole, SanctionAuthority>> = {
  MANAGEMENT: 'SANCTION',
  CONTROL_OFFICER: 'SECTION_CONTROL',
  TPC: 'TRACTION_POWER',
  STATION_MASTER: 'STATION',
  SIGNAL_TELECOM: 'SNT',
  ENGINEERING: 'ENGINEERING_SSE',
};

function authorityLabel(authority: SanctionAuthority) {
  return AUTHORITY_LABELS[authority] || authority.replaceAll('_', ' ');
}

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

function isSanctionChain(value: unknown): value is SanctionChain {
  return Boolean(value && typeof value === 'object' && 'requiredAuthorities' in value && 'signatures' in value);
}

interface SanctionChainPanelProps {
  planId?: string;
  plan?: RailOSPlan | null;
}

export function SanctionChainPanel({ planId, plan }: SanctionChainPanelProps) {
  const userRole = useRailOSStore((state) => state.userRole);
  const sanctionsQuery = usePlanSanctions(planId || '', { enabled: Boolean(planId) });
  const signMutation = useSignPlanSanction();
  const [reason, setReason] = useState('');
  const [formReference, setFormReference] = useState('');
  const [decision, setDecision] = useState<SignatureDecision>('GRANTED');

  const chain = useMemo(() => {
    if (isSanctionChain(signMutation.data)) return signMutation.data;
    return sanctionsQuery.data;
  }, [sanctionsQuery.data, signMutation.data]);

  const grantedAuthorities = new Set(
    chain?.signatures
      .filter((signature) => signature.decision === 'GRANTED' && signature.planVersion === chain.planVersion)
      .map((signature) => signature.authority) || []
  );
  const pendingAuthorities = chain?.requiredAuthorities.filter((authority) => !grantedAuthorities.has(authority)) || [];
  const callerAuthority = userRole === 'ADMIN'
    ? pendingAuthorities[0]
    : ROLE_AUTHORITIES[userRole];
  const callerCanAct = Boolean(
    chain && !chain.complete && !chain.refused && callerAuthority &&
    chain.requiredAuthorities.includes(callerAuthority) && !grantedAuthorities.has(callerAuthority)
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!planId || !chain || !callerAuthority || !callerCanAct) return;
    signMutation.mutate({
      planId,
      authority: callerAuthority,
      decision,
      reason,
      formReference,
      expectedVersion: chain.planVersion,
    });
  };

  if (!planId) {
    return (
      <section className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5" aria-labelledby="sanction-chain-empty">
        <h2 id="sanction-chain-empty" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Sanction chain</h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">{plan ? `Plan ${plan.planId} has no sanction identifier.` : 'Select an API-backed plan to inspect and record its statutory authority chain.'}</p>
      </section>
    );
  }

  if (sanctionsQuery.isLoading && !chain) {
    return (
      <section className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5" aria-labelledby="sanction-chain-loading" aria-busy="true">
        <h2 id="sanction-chain-loading" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Sanction chain</h2>
        <p className="mt-3 text-sm text-[var(--text-secondary)]" role="status">Loading authority requirements…</p>
      </section>
    );
  }

  if (sanctionsQuery.isError && !chain) {
    return (
      <section className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-5" aria-labelledby="sanction-chain-error">
        <h2 id="sanction-chain-error" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--status-critical-text)]">Sanction chain unavailable</h2>
        <p className="mt-2 text-sm text-[var(--status-critical-text)]">{sanctionsQuery.error.message}</p>
      </section>
    );
  }

  if (!chain) return null;

  const chainStatus = chain.refused ? 'REJECTED' : chain.complete ? 'APPROVED' : 'PROPOSED';
  const statusLabel = chain.refused
    ? 'Chain refused — plan cannot proceed'
    : chain.complete
      ? 'All required authorities have signed'
      : `${pendingAuthorities.length} authority${pendingAuthorities.length === 1 ? '' : 'ies'} outstanding`;

  return (
    <section className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5" aria-labelledby="sanction-chain-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileSignature className="h-5 w-5 text-[var(--accent)]" aria-hidden="true" />
            <h2 id="sanction-chain-title" className="font-mono text-sm font-bold uppercase tracking-wide text-[var(--text-primary)]">Sanction chain</h2>
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Plan <span className="font-mono text-[var(--text-primary)]">{chain.planId}</span> · version {chain.planVersion}
          </p>
        </div>
        <StatusChip def={getTokenDef(PLAN_STATUS_TOKENS, chainStatus)} />
      </div>

      <div className="mt-4 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3" role="status" aria-live="polite">
        <div className="flex items-center gap-2">
          {chain.complete ? <CheckCircle2 className="h-4 w-4 text-[var(--status-ok-fg)]" aria-hidden="true" /> : <LockKeyhole className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" />}
          <span className="text-sm font-semibold text-[var(--text-primary)]">{statusLabel}</span>
        </div>
        {isSanctionChain(signMutation.data) && (
          <p className="mt-1 text-xs text-[var(--status-info-text)]">Authority response accepted (HTTP 202); progress is saved and the chain remains open.</p>
        )}
      </div>

      <ol className="mt-5 grid gap-3 lg:grid-cols-2" aria-label="Required authorities in signing order">
        {chain.requiredAuthorities.map((authority, index) => {
          const signature = [...chain.signatures].reverse().find((item) => item.authority === authority && item.planVersion === chain.planVersion);
          const isCaller = authority === callerAuthority;
          const token = signature
            ? getTokenDef(SIGNATURE_DECISION_TOKENS, signature.decision)
            : getTokenDef(SIGNATURE_DECISION_TOKENS, 'DEFERRED');
          return (
            <li key={authority} className={`rounded border p-3 ${signature?.decision === 'REFUSED' ? 'border-[var(--status-critical-border)] bg-[var(--status-critical-bg)]' : 'border-[var(--border-subtle)] bg-[var(--bg-elevated)]'}`}>
              <div className="flex items-start gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[var(--border-strong)] bg-[var(--bg-surface)] font-mono text-xs font-bold text-[var(--text-secondary)]" aria-label={`Step ${index + 1}`}>
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-mono text-sm font-bold text-[var(--text-primary)]">{authorityLabel(authority)}</h3>
                    <StatusChip def={token} compact />
                  </div>
                  {signature ? (
                    <dl className="mt-2 grid gap-x-3 gap-y-1 text-xs text-[var(--text-secondary)] sm:grid-cols-2">
                      <div><dt className="inline text-[var(--text-muted)]">Actor: </dt><dd className="inline font-mono text-[var(--text-primary)]">{signature.userId}</dd></div>
                      <div><dt className="inline text-[var(--text-muted)]">Role: </dt><dd className="inline font-mono text-[var(--text-primary)]">{signature.role}</dd></div>
                      <div><dt className="inline text-[var(--text-muted)]">Signed: </dt><dd className="inline">{formatUtc(signature.signedAtUtc)}</dd></div>
                      {signature.formReference && <div><dt className="inline text-[var(--text-muted)]">Form: </dt><dd className="inline font-mono text-[var(--text-primary)]">{signature.formReference}</dd></div>}
                      {signature.reason && <div className="sm:col-span-2"><dt className="inline text-[var(--text-muted)]">Reason: </dt><dd className="inline">{signature.reason}</dd></div>}
                    </dl>
                  ) : (
                    <p className={`mt-2 text-xs ${isCaller ? 'text-[var(--accent)]' : 'text-[var(--text-secondary)]'}`}>
                      {isCaller ? 'This authority is assigned to your acting role.' : `Awaiting ${authorityLabel(authority)}.`}
                    </p>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      {chain.derivedFrom.length > 0 && (
        <p className="mt-4 text-xs text-[var(--text-muted)]">Rules: {chain.derivedFrom.join(', ')}</p>
      )}

      {callerCanAct && (
        <form onSubmit={handleSubmit} className="mt-5 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] p-4" aria-label={`Record ${authorityLabel(callerAuthority || 'SANCTION')} decision`}>
          <div className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" />
            <h3 className="font-mono text-sm font-bold text-[var(--text-primary)]">Your authority: {authorityLabel(callerAuthority || 'SANCTION')}</h3>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div>
              <label htmlFor="sanction-decision" className="mb-1 block text-xs font-semibold text-[var(--text-secondary)]">Decision</label>
              <select id="sanction-decision" value={decision} onChange={(event) => setDecision(event.target.value as SignatureDecision)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)]">
                <option value="GRANTED">Sign / grant</option>
                <option value="REFUSED">Refuse sanction</option>
              </select>
            </div>
            <div>
              <label htmlFor="sanction-form" className="mb-1 block text-xs font-semibold text-[var(--text-secondary)]">Form reference <span className="font-normal text-[var(--text-muted)]">(optional)</span></label>
              <input id="sanction-form" value={formReference} onChange={(event) => setFormReference(event.target.value)} className="min-h-11 w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-sm font-mono text-[var(--text-primary)]" placeholder="e.g. DOM/BLK/2026-091" />
            </div>
          </div>
          <div className="mt-3">
            <label htmlFor="sanction-reason" className="mb-1 block text-xs font-semibold text-[var(--text-secondary)]">Reason {decision === 'REFUSED' ? <span className="text-[var(--status-critical-text)]">(required)</span> : <span className="font-normal text-[var(--text-muted)]">(optional)</span>}</label>
            <textarea id="sanction-reason" value={reason} onChange={(event) => setReason(event.target.value)} required={decision === 'REFUSED'} rows={3} className="w-full rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]" placeholder="Record the operational reason for this decision" />
          </div>
          <button type="submit" disabled={signMutation.isPending || (decision === 'REFUSED' && reason.trim().length === 0)} className="mt-3 min-h-11 rounded border border-[var(--accent)] bg-[var(--accent)] px-4 text-sm font-bold text-[var(--bg-canvas)] disabled:cursor-not-allowed disabled:opacity-50">
            {signMutation.isPending ? 'Recording…' : decision === 'REFUSED' ? 'Refuse sanction' : 'Sign authority chain'}
          </button>
          {signMutation.isError && <p className="mt-2 text-sm text-[var(--status-critical-text)]" role="alert">{signMutation.error.message}</p>}
        </form>
      )}

      {!callerCanAct && !chain.complete && !chain.refused && (
        <p className="mt-4 text-sm text-[var(--text-secondary)]">The next authority is not assigned to the current acting role. Switch roles in the shell header to continue the chain.</p>
      )}
    </section>
  );
}

export { AUTHORITY_LABELS, ROLE_AUTHORITIES, authorityLabel };
