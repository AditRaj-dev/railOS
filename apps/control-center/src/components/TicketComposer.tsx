'use client';

import React, { useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, ChevronLeft, ChevronRight, CircleAlert, ClipboardCheck, MessageSquareText, RotateCcw } from 'lucide-react';
import type { BlockRequest, CreateBlockRequestPayload, DepartmentCode, RailOSApiError } from '@/lib/api';
import { useAssets, useCreateBlockRequest, useNetworkCatalog, useTicketTaskTypes } from '@/lib/queries';
import { DEMO_EPOCH_ISO, dateToMinute } from '@/lib/time';

type ComposerStep = 'department' | 'location' | 'work' | 'block' | 'window' | 'review';

interface TicketDraft {
  department: DepartmentCode | '';
  sectionId: string;
  track: string;
  kmStart: string;
  kmEnd: string;
  taskType: string;
  assetId: string;
  severity: string;
  estimatedDuration: string;
  blockType: string;
  requestedStart: string;
  requestedEnd: string;
}

const STEPS: Array<{ id: ComposerStep; label: string; prompt: string }> = [
  { id: 'department', label: 'Department', prompt: 'Which department owns this request?' },
  { id: 'location', label: 'Location', prompt: 'Where and on which line must the work take place?' },
  { id: 'work', label: 'Work', prompt: 'What work is required, and how urgent is it?' },
  { id: 'block', label: 'Block need', prompt: 'What possession or isolation is required to perform it safely?' },
  { id: 'window', label: 'Requested window', prompt: 'When should Block Finder consider this demand?' },
  { id: 'review', label: 'Review', prompt: 'Confirm the structured request before it is sent to the Block Manager.' },
];

const DEPARTMENTS: Array<{ code: DepartmentCode; label: string; role: string; description: string }> = [
  { code: 'ENGG', label: 'ENGG · Civil / P-Way', role: 'ENGINEERING', description: 'Track, turnout, and permanent-way work.' },
  { code: 'SNT', label: 'SNT · Signal & Telecom', role: 'SIGNAL_TELECOM', description: 'Signalling, interlocking, and T/351 work.' },
  { code: 'TRD', label: 'TRD · Traction Distribution', role: 'TRACTION', description: 'OHE, isolation, and power-block work.' },
];

const TASK_TYPES: Record<DepartmentCode, string[]> = {
  ENGG: ['TAMPING', 'DEEP_SCREENING', 'RAIL_REPLACEMENT', 'SLEEPER_RENEWAL', 'TURNOUT_RENEWAL', 'DESTRESSING', 'USFD_INSPECTION'],
  SNT: ['POINT_MACHINE_MAINT', 'TRACK_CIRCUIT_BOND', 'AXLE_COUNTER_CALIB', 'GJ_REPLACEMENT', 'INTERLOCKING_WORK', 'SNT_DISCONNECTION', 'SNT_RECONNECTION'],
  TRD: ['OHE_INSPECTION', 'CATENARY_REPLACEMENT', 'OHE_BRACKET_ADJUST', 'OHE_SLEWING', 'TRD_ISOLATION'],
};

function initialDraft(department?: DepartmentCode): TicketDraft {
  return {
    department: department || '',
    sectionId: '',
    track: 'DOWN',
    kmStart: '',
    kmEnd: '',
    taskType: '',
    assetId: '',
    severity: '5',
    estimatedDuration: '',
    blockType: 'TRAFFIC',
    requestedStart: '',
    requestedEnd: '',
  };
}

function pretty(value: string | undefined | null, fallback = 'Not set') {
  return value && value.trim() ? value.replaceAll('_', ' ') : fallback;
}

function createPayload(draft: TicketDraft): CreateBlockRequestPayload {
  const department = draft.department as DepartmentCode;
  return {
    department,
    corridorId: 'GZB-ALJN',
    sectionId: draft.sectionId,
    track: draft.track,
    kmStart: Number(draft.kmStart),
    kmEnd: Number(draft.kmEnd),
    taskType: draft.taskType,
    ...(draft.assetId ? { assetId: draft.assetId } : {}),
    severity: Number(draft.severity),
    estimatedDuration: Number(draft.estimatedDuration),
    blockType: draft.blockType,
    // requiresPTW/requiresT351/requiresCorrespondenceTest are server-derived
    // from taskType and must not be sent — BlockRequestCreate is extra="forbid".
    requestedStart: dateToMinute(DEMO_EPOCH_ISO, new Date(draft.requestedStart)),
    requestedEnd: dateToMinute(DEMO_EPOCH_ISO, new Date(draft.requestedEnd)),
  };
}

function errorDetails(error: RailOSApiError): Record<string, string> {
  if (!error.details || typeof error.details !== 'object') return {};
  const details = error.details as Record<string, unknown>;
  const fields = details.fields && typeof details.fields === 'object'
    ? details.fields as Record<string, unknown>
    : details;
  return Object.fromEntries(Object.entries(fields)
    .filter(([, value]) => typeof value === 'string')
    .map(([key, value]) => [key.replaceAll('_', ''), String(value)]));
}

/** Which composer step a server-named field belongs to, for the jump-back. */
const FIELD_STEPS: Record<string, ComposerStep> = {
  department: 'department',
  sectionId: 'location',
  track: 'location',
  kmStart: 'location',
  kmEnd: 'location',
  taskType: 'work',
  assetId: 'work',
  severity: 'work',
  estimatedDuration: 'block',
  blockType: 'block',
  requestedStart: 'window',
  requestedEnd: 'window',
};

export interface TicketComposerProps {
  initialDepartment?: DepartmentCode;
  onSubmitted?: (request: BlockRequest) => void;
}

/**
 * A deterministic, chat-assisted request flow. The compact prompt is only a
 * guide; the record beside it is always the authoritative, editable form.
 */
export function TicketComposer({ initialDepartment, onSubmitted }: TicketComposerProps) {
  const [draft, setDraft] = useState<TicketDraft>(() => initialDraft(initialDepartment));
  const [stepIndex, setStepIndex] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  // The server's own complaints live apart from the client-side ones: they are
  // keyed by whatever field the API names, so a per-key delete on edit missed
  // them and the banner stayed up after the operator had fixed the value.
  const [serverErrors, setServerErrors] = useState<string[]>([]);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<BlockRequest | null>(null);
  const errorSummaryRef = useRef<HTMLDivElement>(null);
  const catalogQuery = useNetworkCatalog();
  const taskTypeQuery = useTicketTaskTypes();
  const createMutation = useCreateBlockRequest();
  const step = STEPS[stepIndex];
  const serverTaskTypes = useMemo(
    () => (taskTypeQuery.data || []).filter((entry) => entry.department === draft.department),
    [taskTypeQuery.data, draft.department]
  );
  // Fall back to the static list only while the catalogue is in flight or the
  // call failed; the server copy is the one that carries the HC-002 floors.
  const taskTypes = serverTaskTypes.length
    ? serverTaskTypes.map((entry) => entry.taskType)
    : draft.department ? TASK_TYPES[draft.department] : [];
  const selectedTaskType = serverTaskTypes.find((entry) => entry.taskType === draft.taskType);
  const minDuration = selectedTaskType?.minDurationMinutes ?? 0;
  const assetsQuery = useAssets();
  // Point machines, axle counters and OHE elementary sections each identify the
  // work location by their own asset, and a section can hold several. The API
  // auto-resolves only when exactly one candidate matches, so offer the list
  // rather than letting the operator meet ASSET_REQUIRED after six steps.
  const candidateAssets = useMemo(() => {
    if (!selectedTaskType || !draft.sectionId) return [];
    return (assetsQuery.data || []).filter((asset) =>
      asset.sectionId === draft.sectionId
      && asset.assetType === selectedTaskType.assetType
      && (asset.track == null || asset.track === draft.track));
  }, [assetsQuery.data, selectedTaskType, draft.sectionId, draft.track]);
  const assetChoiceRequired = Boolean(selectedTaskType) && candidateAssets.length !== 1;
  // The catalogue also carries overview-only corridors (planningEnabled
  // false) that no corridor plans, and every section is double line. Offering
  // them produced requests the API could only refuse.
  const sections = useMemo(
    () => (catalogQuery.data?.sections || []).filter((section) => section.planningEnabled),
    [catalogQuery.data]
  );
  const sectionTracks = useMemo(() => {
    const section = sections.find((candidate) => candidate.sectionId === draft.sectionId);
    return (section?.tracks as string[] | undefined) || ['UP', 'DOWN'];
  }, [sections, draft.sectionId]);

  const update = <Key extends keyof TicketDraft>(key: Key, value: TicketDraft[Key]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    setSubmissionError(null);
    setServerErrors([]);
  };

  const validate = (target: ComposerStep): Record<string, string> => {
    const errors: Record<string, string> = {};
    if (target === 'department' && !draft.department) errors.department = 'Choose ENGG, SNT, or TRD to continue.';
    if (target === 'location') {
      if (!draft.sectionId) errors.sectionId = 'Choose the affected railway section.';
      if (!draft.track) errors.track = 'Choose the affected track.';
      else if (draft.sectionId && !sectionTracks.includes(draft.track)) {
        errors.track = `${draft.sectionId} has no ${draft.track} track. Choose ${sectionTracks.join(' or ')}.`;
      }
      if (!draft.kmStart || Number.isNaN(Number(draft.kmStart))) errors.kmStart = 'Enter the start kilometre.';
      if (!draft.kmEnd || Number.isNaN(Number(draft.kmEnd))) errors.kmEnd = 'Enter the end kilometre.';
      if (draft.kmStart && draft.kmEnd && Number(draft.kmEnd) < Number(draft.kmStart)) errors.kmEnd = 'End kilometre must be the same as or later than the start kilometre.';
    }
    if (target === 'work') {
      if (!draft.taskType) errors.taskType = 'Choose the work type.';
      if (!draft.severity || Number(draft.severity) < 1 || Number(draft.severity) > 10) errors.severity = 'Choose a severity from 1 to 10.';
      if (draft.taskType && assetChoiceRequired) {
        if (candidateAssets.length === 0) {
          errors.assetId = `No ${pretty(selectedTaskType?.assetType)} asset is mapped on ${draft.sectionId || 'this section'} ${draft.track}. Choose another section, track, or work type.`;
        } else if (!draft.assetId) {
          errors.assetId = `Choose which ${pretty(selectedTaskType?.assetType)} this request covers.`;
        }
      }
    }
    if (target === 'block') {
      if (!draft.estimatedDuration || Number(draft.estimatedDuration) <= 0) errors.estimatedDuration = 'Enter a duration greater than zero minutes.';
      else if (minDuration > 0 && Number(draft.estimatedDuration) < minDuration) {
        errors.estimatedDuration = `${pretty(draft.taskType)} needs at least ${minDuration} minutes under HC-002.`;
      }
      if (!draft.blockType) errors.blockType = 'Choose the block requirement.';
    }
    if (target === 'window') {
      if (!draft.requestedStart) errors.requestedStart = 'Enter the earliest requested start.';
      if (!draft.requestedEnd) errors.requestedEnd = 'Enter the latest requested end.';
      if (draft.requestedStart && draft.requestedEnd && new Date(draft.requestedEnd) <= new Date(draft.requestedStart)) {
        errors.requestedEnd = 'The requested end must be after the requested start.';
      }
    }
    return errors;
  };

  const focusErrors = () => {
    requestAnimationFrame(() => errorSummaryRef.current?.focus());
  };

  const advance = () => {
    const errors = validate(step.id);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      focusErrors();
      return;
    }
    setStepIndex((value) => Math.min(value + 1, STEPS.length - 1));
  };

  const submit = () => {
    const errors = STEPS.slice(0, -1).reduce<Record<string, string>>((all, current) => ({ ...all, ...validate(current.id) }), {});
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setStepIndex(Math.max(0, STEPS.findIndex((current) => Object.keys(validate(current.id)).length > 0)));
      focusErrors();
      return;
    }
    setSubmissionError(null);
    setServerErrors([]);
    createMutation.mutate(createPayload(draft), {
      onSuccess: (request) => {
        setSubmitted(request);
        onSubmitted?.(request);
      },
      onError: (error) => {
        const serverFields = errorDetails(error);
        setServerErrors(Object.values(serverFields));
        setSubmissionError(error.message);
        const offending = Object.keys(serverFields).map((key) => FIELD_STEPS[key]).find(Boolean);
        if (offending) setStepIndex(STEPS.findIndex((item) => item.id === offending));
        focusErrors();
      },
    });
  };

  const reset = () => {
    setDraft(initialDraft(initialDepartment));
    setStepIndex(0);
    setFieldErrors({});
    setServerErrors([]);
    setSubmissionError(null);
    setSubmitted(null);
  };

  if (submitted) {
    return (
      <section className="rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] p-5" aria-labelledby="ticket-success-title">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-[var(--status-ok-fg)]" aria-hidden="true" />
          <div className="min-w-0">
            <h2 id="ticket-success-title" className="font-mono text-base font-bold text-[var(--status-ok-text)]">Request submitted to Block Manager</h2>
            <p className="mt-1 text-sm text-[var(--text-primary)]" role="status" aria-live="polite">
              Ticket <span className="font-mono font-bold">{submitted.requestId}</span> created linked task <span className="font-mono font-bold">{submitted.linkedTaskId || 'pending assignment'}</span>.
            </p>
            <p className="mt-2 text-xs text-[var(--text-secondary)]">{submitted.provenance || 'Synthetic Hackathon Simulation'} · This is requested demand, not an approved possession.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/planner" className="inline-flex min-h-11 items-center rounded border border-[var(--status-ok-border)] px-3 text-sm font-semibold text-[var(--text-primary)] hover:border-[var(--accent)]">Open Block Finder</Link>
              <Link href="/timeline" className="inline-flex min-h-11 items-center rounded border border-[var(--status-ok-border)] px-3 text-sm font-semibold text-[var(--text-primary)] hover:border-[var(--accent)]">Open Operational Gantt</Link>
              <button type="button" onClick={reset} className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--status-ok-border)] px-3 text-sm font-semibold text-[var(--text-primary)] hover:border-[var(--accent)]"><RotateCcw className="h-4 w-4" aria-hidden="true" /> New request</button>
            </div>
          </div>
        </div>
      </section>
    );
  }

  const errorMessages = [...Object.values(fieldErrors), ...serverErrors, ...(submissionError ? [submissionError] : [])];
  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(19rem,0.8fr)]" aria-labelledby="ticket-composer-title">
      <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Guided intake · deterministic</p>
            <h2 id="ticket-composer-title" className="mt-1 flex items-center gap-2 text-lg font-bold text-[var(--text-primary)]"><MessageSquareText className="h-5 w-5" aria-hidden="true" /> New planning request</h2>
          </div>
          <span className="rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-2 py-1 font-mono text-xs text-[var(--text-secondary)]">Step {stepIndex + 1} of {STEPS.length}</span>
        </div>

        <ol className="mt-4 grid grid-cols-3 gap-2 text-xs sm:grid-cols-6" aria-label="Ticket progress">
          {STEPS.map((item, index) => <li key={item.id} aria-current={index === stepIndex ? 'step' : undefined} className={`rounded border px-2 py-2 font-mono ${index === stepIndex ? 'border-[var(--accent)] bg-[var(--status-caution-bg)] text-[var(--status-caution-text)]' : index < stepIndex ? 'border-[var(--status-ok-border)] text-[var(--status-ok-text)]' : 'border-[var(--border-subtle)] text-[var(--text-muted)]'}`}>{index + 1}. {item.label}</li>)}
        </ol>

        {errorMessages.length > 0 && <div ref={errorSummaryRef} tabIndex={-1} className="mt-4 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-3 text-sm text-[var(--status-critical-text)]" role="alert"><div className="flex items-center gap-2 font-semibold"><CircleAlert className="h-4 w-4" aria-hidden="true" /> Correct the highlighted fields</div><ul className="mt-2 list-disc space-y-1 pl-5">{errorMessages.map((message, index) => <li key={`${message}-${index}`}>{message}</li>)}</ul></div>}

        <form className="mt-5" onSubmit={(event) => { event.preventDefault(); step.id === 'review' ? submit() : advance(); }} noValidate>
          <fieldset>
            <legend className="text-base font-semibold text-[var(--text-primary)]">{step.prompt}</legend>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">Answers are visible in the operational record at every step.</p>

            {step.id === 'department' && <div className="mt-4 grid gap-3 md:grid-cols-3">{DEPARTMENTS.map((department) => <label key={department.code} className={`cursor-pointer rounded border p-3 ${draft.department === department.code ? 'border-[var(--accent)] bg-[var(--status-caution-bg)]' : 'border-[var(--border-strong)] bg-[var(--bg-elevated)]'}`}><input className="mr-2" type="radio" name="department" value={department.code} checked={draft.department === department.code} onChange={() => { update('department', department.code); update('taskType', ''); }} /> <span className="font-mono text-sm font-bold text-[var(--text-primary)]">{department.label}</span><span className="mt-2 block text-xs text-[var(--text-secondary)]">{department.description}</span></label>)}</div>}

            {step.id === 'location' && <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Affected section" error={fieldErrors.sectionId}><select value={draft.sectionId} onChange={(event) => { const nextSection = sections.find((candidate) => candidate.sectionId === event.target.value); update('sectionId', event.target.value); update('assetId', ''); const tracks = (nextSection?.tracks as string[] | undefined) || []; if (tracks.length && !tracks.includes(draft.track)) update('track', tracks[0]); }} aria-describedby={fieldErrors.sectionId ? 'sectionId-error' : undefined}><option value="">Choose section</option>{sections.map((section) => <option key={section.sectionId} value={section.sectionId}>{section.name} ({section.sectionId})</option>)}</select>{catalogQuery.isLoading && <p className="mt-1 text-xs text-[var(--text-muted)]" role="status">Loading section catalogue…</p>}</Field><Field label="Track" error={fieldErrors.track}><select value={draft.track} onChange={(event) => { update('track', event.target.value); update('assetId', ''); }}>{sectionTracks.map((track) => <option key={track} value={track}>{track.charAt(0) + track.slice(1).toLowerCase()}</option>)}</select></Field><Field label="Start kilometre" error={fieldErrors.kmStart}><input type="number" step="0.001" value={draft.kmStart} onChange={(event) => update('kmStart', event.target.value)} /></Field><Field label="End kilometre" error={fieldErrors.kmEnd}><input type="number" step="0.001" value={draft.kmEnd} onChange={(event) => update('kmEnd', event.target.value)} /></Field></div>}

            {step.id === 'work' && <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Work type" error={fieldErrors.taskType}><select value={draft.taskType} onChange={(event) => { update('taskType', event.target.value); update('assetId', ''); }} disabled={!draft.department}><option value="">Choose work type</option>{taskTypes.map((type) => <option key={type} value={type}>{pretty(type)}</option>)}</select></Field><Field label="Severity (1 lowest · 10 highest)" error={fieldErrors.severity}><select value={draft.severity} onChange={(event) => update('severity', event.target.value)}>{Array.from({ length: 10 }, (_, index) => index + 1).map((level) => <option key={level} value={level}>{level}{level >= 9 ? ' · critical' : level >= 7 ? ' · high' : level >= 4 ? ' · medium' : ' · low'}</option>)}</select></Field>{selectedTaskType && <Field label={`Asset (${pretty(selectedTaskType.assetType)})`} error={fieldErrors.assetId}><select value={draft.assetId} onChange={(event) => update('assetId', event.target.value)} disabled={candidateAssets.length === 0}><option value="">{candidateAssets.length === 1 ? `${candidateAssets[0].assetId} (resolved automatically)` : 'Choose asset'}</option>{candidateAssets.map((asset) => <option key={asset.assetId} value={asset.assetId}>{asset.name ? `${asset.name} (${asset.assetId})` : asset.assetId}</option>)}</select>{assetsQuery.isLoading && <span className="mt-1 block text-xs font-normal text-[var(--text-muted)]" role="status">Loading asset inventory…</span>}{!assetsQuery.isLoading && candidateAssets.length === 0 && <span className="mt-1 block text-xs font-normal text-[var(--text-secondary)]">No {pretty(selectedTaskType.assetType)} asset is mapped on {draft.sectionId || 'this section'} {draft.track}.</span>}{candidateAssets.length === 1 && <span className="mt-1 block text-xs font-normal text-[var(--text-secondary)]">One candidate on this section and track; the server resolves it.</span>}</Field>}</div>}

            {step.id === 'block' && <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Estimated duration (minutes)" error={fieldErrors.estimatedDuration}><input type="number" min={minDuration || 1} value={draft.estimatedDuration} onChange={(event) => update('estimatedDuration', event.target.value)} aria-describedby={minDuration > 0 ? 'duration-floor' : undefined} />{minDuration > 0 && <span id="duration-floor" className="mt-1 block text-xs font-normal text-[var(--text-secondary)]">{pretty(draft.taskType)} needs a minimum block of {minDuration} minutes (HC-002).</span>}</Field><Field label="Block requirement" error={fieldErrors.blockType}><select value={draft.blockType} onChange={(event) => update('blockType', event.target.value)}><option value="TRAFFIC">Traffic block</option><option value="POWER">Power block / PTW</option><option value="INTEGRATED">Integrated traffic + power</option><option value="DISCONNECTION">S&T disconnection / T-351</option></select></Field><p className="sm:col-span-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3 text-xs text-[var(--text-secondary)]">{draft.department === 'SNT' ? 'S&T work will carry the required T/351 and correspondence-test flags.' : draft.department === 'TRD' ? 'TRD work will carry PTW and OHE isolation requirements.' : 'Block Finder will retain all resulting safety warnings; submission does not approve a possession.'}</p></div>}

            {step.id === 'window' && <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Earliest requested start" error={fieldErrors.requestedStart}><input type="datetime-local" value={draft.requestedStart} onChange={(event) => update('requestedStart', event.target.value)} /></Field><Field label="Latest requested end" error={fieldErrors.requestedEnd}><input type="datetime-local" value={draft.requestedEnd} onChange={(event) => update('requestedEnd', event.target.value)} /></Field><p className="sm:col-span-2 text-xs text-[var(--text-secondary)]">This is a planning preference. The optimizer may return a different candidate window or an unassigned warning.</p></div>}

            {step.id === 'review' && <div className="mt-4 rounded border border-[var(--status-caution-border)] bg-[var(--status-caution-bg)] p-4 text-sm text-[var(--text-primary)]"><div className="flex items-start gap-2"><ClipboardCheck className="mt-0.5 h-5 w-5 text-[var(--status-caution-fg)]" aria-hidden="true" /><div><p className="font-semibold">Ready to send to Block Manager</p><p className="mt-1 text-xs text-[var(--text-secondary)]">A canonical maintenance task will be created and linked. This request remains <strong>REQUESTED</strong> until the existing planning and sanction workflow acts on it.</p></div></div></div>}
          </fieldset>
          <div className="mt-6 flex flex-wrap justify-between gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={() => setStepIndex((value) => Math.max(0, value - 1))} disabled={stepIndex === 0 || createMutation.isPending} className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--border-strong)] px-3 text-sm font-semibold text-[var(--text-primary)] disabled:opacity-50"><ChevronLeft className="h-4 w-4" aria-hidden="true" /> Back</button>{step.id === 'review' ? <button type="submit" disabled={createMutation.isPending} className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--accent)] bg-[var(--accent)] px-4 text-sm font-bold text-[var(--bg-canvas)] disabled:opacity-50">{createMutation.isPending ? 'Submitting…' : 'Submit to Block Manager'} <CheckCircle2 className="h-4 w-4" aria-hidden="true" /></button> : <button type="submit" className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--accent)] bg-[var(--accent)] px-4 text-sm font-bold text-[var(--bg-canvas)]">Continue <ChevronRight className="h-4 w-4" aria-hidden="true" /></button>}</div>
        </form>
      </div>

      <StructuredPreview draft={draft} onEdit={(target) => setStepIndex(STEPS.findIndex((item) => item.id === target))} />
    </section>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  const id = label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-').replaceAll(/^-|-$/g, '');
  return <label className="block text-sm font-semibold text-[var(--text-primary)]">{label}<span className="mt-1 block [&_input]:min-h-11 [&_input]:w-full [&_input]:rounded [&_input]:border [&_input]:border-[var(--border-strong)] [&_input]:bg-[var(--bg-surface)] [&_input]:px-3 [&_input]:text-[var(--text-primary)] [&_select]:min-h-11 [&_select]:w-full [&_select]:rounded [&_select]:border [&_select]:border-[var(--border-strong)] [&_select]:bg-[var(--bg-surface)] [&_select]:px-3 [&_select]:text-[var(--text-primary)]">{children}</span>{error && <span id={`${id}-error`} className="mt-1 block text-xs text-[var(--status-critical-text)]">{error}</span>}</label>;
}

function StructuredPreview({ draft, onEdit }: { draft: TicketDraft; onEdit: (step: ComposerStep) => void }) {
  const rows: Array<{ label: string; value: string; step: ComposerStep }> = [
    { label: 'Department', value: pretty(draft.department), step: 'department' },
    { label: 'Location', value: draft.sectionId ? `${draft.sectionId} · ${draft.track} · km ${draft.kmStart || '?'}–${draft.kmEnd || '?'}` : 'Not set', step: 'location' },
    { label: 'Work', value: draft.taskType ? `${pretty(draft.taskType)} · severity ${draft.severity}${draft.assetId ? ` · ${draft.assetId}` : ''}` : 'Not set', step: 'work' },
    { label: 'Block need', value: draft.estimatedDuration ? `${draft.estimatedDuration} min · ${pretty(draft.blockType)}` : 'Not set', step: 'block' },
    { label: 'Requested window', value: draft.requestedStart && draft.requestedEnd ? `${draft.requestedStart.replace('T', ' ')} → ${draft.requestedEnd.replace('T', ' ')}` : 'Not set', step: 'window' },
  ];
  return <aside className="h-fit rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-4" aria-labelledby="ticket-preview-title"><div className="flex items-center justify-between gap-2"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Structured record</p><h2 id="ticket-preview-title" className="mt-1 text-base font-bold text-[var(--text-primary)]">Block Finder input preview</h2></div><span className="rounded border border-[var(--status-caution-border)] bg-[var(--status-caution-bg)] px-2 py-1 font-mono text-[10px] font-bold text-[var(--status-caution-text)]">REQUESTED</span></div><p className="mt-2 text-xs text-[var(--text-secondary)]">Visible throughout intake. Edit any captured value before submission.</p><dl className="mt-4 divide-y divide-[var(--border-subtle)]">{rows.map((row) => <div key={row.label} className="py-3"><dt className="text-xs font-mono uppercase tracking-wide text-[var(--text-muted)]">{row.label}</dt><dd className="mt-1 break-words text-sm text-[var(--text-primary)]">{row.value}</dd><button type="button" onClick={() => onEdit(row.step)} className="mt-2 min-h-9 text-xs font-semibold text-[var(--accent)] underline underline-offset-4">Edit {row.label.toLowerCase()}</button></div>)}</dl><p className="mt-4 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3 text-xs text-[var(--text-secondary)]"><strong className="text-[var(--text-primary)]">Synthetic API connected.</strong> Requests are deterministic demo data and do not grant operating authority.</p></aside>;
}
