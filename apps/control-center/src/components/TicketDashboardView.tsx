'use client';

import React, { useMemo, useRef, useState } from 'react';
import { AlertCircle, ArrowDown, ArrowUp, Inbox, Plus, RefreshCw, Route } from 'lucide-react';
import type { BlockRequest, BlockRequestStatus, DepartmentCode } from '@/lib/api';
import { useBlockRequests } from '@/lib/queries';
import { useRailOSStore } from '@/store/railosStore';
import { DEMO_EPOCH_ISO, formatMinute } from '@/lib/time';
import { BLOCK_REQUEST_STATUS_TOKENS, DEPARTMENT_TOKENS, getTokenDef } from './tokens';
import { StatusChip } from './StatusChip';
import { MetricCard } from './RailwayComponents';
import { Table, TableBody, TableCell, TableHeader, TableHeaderCell } from './ui/Table';
import { Modal } from './ui/Modal';
import { TicketComposer } from './TicketComposer';

type TabId = DepartmentCode | 'ALL';

const DEPARTMENT_TABS: Array<{ id: DepartmentCode; label: string }> = [
  { id: 'ENGG', label: 'ENGG' },
  { id: 'SNT', label: 'SNT' },
  { id: 'TRD', label: 'TRD' },
];

/** Roles that own exactly one department queue and never see the others. */
const DEPARTMENT_BY_ROLE: Partial<Record<string, DepartmentCode>> = {
  ENGINEERING: 'ENGG',
  SIGNAL_TELECOM: 'SNT',
  TRACTION: 'TRD',
};

const BROAD_ROLES = ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT', 'FIELD_SUPERVISOR'];

type SortField = 'createdAt' | 'severity';

/** Requested boundaries may arrive as horizon-relative minutes (numeric) or an
 * ISO timestamp, depending on rollout stage of the underlying record. Render
 * either without guessing wrong and showing "Invalid Date". */
function formatRequestedBoundary(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number' || /^-?\d+$/.test(String(value).trim())) {
    return formatMinute(DEMO_EPOCH_ISO, Number(value));
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(date);
}

function formatCreatedAt(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(date);
}

function isBlockFinderReady(request: BlockRequest): boolean {
  const status = String(request.status) as BlockRequestStatus | string;
  return Boolean(request.linkedTaskId) && (status === 'REQUESTED' || status === 'READY');
}

export const TicketDashboardView: React.FC = () => {
  const userRole = useRailOSStore((state) => state.userRole);
  const lockedDepartment = DEPARTMENT_BY_ROLE[userRole];
  const isBroadRole = BROAD_ROLES.includes(userRole);

  const availableTabs: TabId[] = useMemo(() => (lockedDepartment
    ? [lockedDepartment]
    : isBroadRole
      ? ['ALL', ...DEPARTMENT_TABS.map((tab) => tab.id)]
      : []), [lockedDepartment, isBroadRole]);

  const [selectedTab, setSelectedTab] = useState<TabId>('ALL');
  // The role can change under a mounted dashboard, and a state initializer only
  // runs once — an SNT supervisor was left on the broad 'ALL' tab, which then
  // opened the composer with no department chosen.
  const activeTab: TabId = useMemo(
    () => (availableTabs.includes(selectedTab) ? selectedTab : (availableTabs[0] ?? 'ALL')),
    [availableTabs, selectedTab]
  );
  const setActiveTab = setSelectedTab;
  const [composerOpen, setComposerOpen] = useState(false);
  const [sort, setSort] = useState<{ field: SortField; direction: 'asc' | 'desc' }>({ field: 'createdAt', direction: 'desc' });
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const ticketsQuery = useBlockRequests();
  const allItems = useMemo(() => ticketsQuery.data?.items ?? [], [ticketsQuery.data]);

  const countsByDepartment = useMemo(() => {
    const counts: Record<DepartmentCode, number> = { ENGG: 0, SNT: 0, TRD: 0 };
    for (const item of allItems) {
      if (item.department in counts) counts[item.department] += 1;
    }
    return counts;
  }, [allItems]);

  const scopedItems = useMemo(() => {
    if (activeTab === 'ALL') return allItems;
    return allItems.filter((item) => item.department === activeTab);
  }, [allItems, activeTab]);

  const sortedItems = useMemo(() => {
    const items = [...scopedItems];
    items.sort((a, b) => {
      const direction = sort.direction === 'asc' ? 1 : -1;
      if (sort.field === 'severity') return (a.severity - b.severity) * direction;
      const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0;
      const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0;
      return (aTime - bTime) * direction;
    });
    return items;
  }, [scopedItems, sort]);

  const metrics = useMemo(() => ({
    open: scopedItems.filter((item) => item.status === 'REQUESTED').length,
    awaitingPlanning: scopedItems.filter((item) => item.status === 'UNDER_REVIEW' || item.status === 'READY').length,
    planned: scopedItems.filter((item) => item.status === 'PLANNED').length,
    rejected: scopedItems.filter((item) => item.status === 'REJECTED').length,
  }), [scopedItems]);

  const toggleSort = (field: SortField) => {
    setSort((current) => current.field === field
      ? { field, direction: current.direction === 'asc' ? 'desc' : 'asc' }
      : { field, direction: 'desc' });
  };

  const focusTab = (index: number) => {
    const tab = availableTabs[index];
    if (!tab) return;
    setActiveTab(tab);
    tabRefs.current[tab]?.focus();
  };

  const handleTabKeyDown = (event: React.KeyboardEvent, index: number) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      focusTab((index + 1) % availableTabs.length);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      focusTab((index - 1 + availableTabs.length) % availableTabs.length);
    } else if (event.key === 'Home') {
      event.preventDefault();
      focusTab(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      focusTab(availableTabs.length - 1);
    }
  };

  const tabLabel = (tab: TabId) => tab === 'ALL' ? `All (${allItems.length})` : `${tab} (${countsByDepartment[tab as DepartmentCode]})`;

  return (
    <div className="space-y-5" aria-labelledby="ticket-dashboard-title">
      <header className="flex flex-wrap items-start justify-between gap-4 rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5">
        <div>
          <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-[var(--accent)]">Department demand hub</p>
          <h1 id="ticket-dashboard-title" className="mt-1 text-xl font-bold text-[var(--text-primary)]">Tickets</h1>
          <p className="mt-2 max-w-3xl text-sm text-[var(--text-secondary)]">
            Structured planning requests raised by ENGG, SNT, and TRD, and their readiness for Block Finder.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void ticketsQuery.refetch()}
            disabled={ticketsQuery.isFetching}
            aria-label="Refresh tickets"
            className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text-primary)] hover:border-[var(--accent)] disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${ticketsQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" /> Refresh
          </button>
          <button
            type="button"
            onClick={() => setComposerOpen(true)}
            className="inline-flex min-h-11 items-center gap-2 rounded border border-[var(--accent)] bg-[var(--accent)] px-3 text-sm font-bold text-[var(--bg-canvas)]"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> New ticket
          </button>
        </div>
      </header>

      {availableTabs.length > 0 && (
        <div role="tablist" aria-label="Department" className="flex flex-wrap gap-2 border-b border-[var(--border-subtle)] pb-0">
          {availableTabs.map((tab, index) => {
            const selected = tab === activeTab;
            return (
              <button
                key={tab}
                ref={(node) => { tabRefs.current[tab] = node; }}
                role="tab"
                type="button"
                id={`ticket-tab-${tab}`}
                aria-selected={selected}
                aria-controls={`ticket-tabpanel-${tab}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActiveTab(tab)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
                className={`min-h-11 rounded-t border border-b-0 px-4 text-sm font-mono font-bold uppercase tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
                  selected
                    ? 'border-[var(--border-strong)] bg-[var(--bg-panel)] text-[var(--accent)]'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                {tabLabel(tab)}
              </button>
            );
          })}
        </div>
      )}

      <div
        role="tabpanel"
        id={`ticket-tabpanel-${activeTab}`}
        aria-labelledby={`ticket-tab-${activeTab}`}
        className="space-y-5"
      >
        <section aria-label="Ticket summary" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Open requests" value={metrics.open} status="highlight" icon={Inbox} subValue="Awaiting first review" />
          <MetricCard label="Awaiting planning" value={metrics.awaitingPlanning} status="caution" subValue="Under review / ready" />
          <MetricCard label="Planned" value={metrics.planned} status="normal" subValue="Linked to a block plan" />
          <MetricCard label="Rejected" value={metrics.rejected} status="critical" subValue="Returned by Block Manager" />
        </section>

        {ticketsQuery.isLoading && (
          <p className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-5 text-sm text-[var(--text-secondary)]" role="status">Loading ticket queue…</p>
        )}

        {ticketsQuery.isError && (
          <div className="flex items-start gap-2 rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] p-4 text-sm text-[var(--status-critical-text)]" role="alert">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">Ticket queue unavailable</p>
              <p className="mt-1">{ticketsQuery.error?.message || 'Try again.'}</p>
              <button type="button" onClick={() => void ticketsQuery.refetch()} className="mt-3 inline-flex min-h-9 items-center gap-2 rounded border border-[var(--status-critical-border)] px-3 text-xs font-semibold hover:bg-[var(--status-critical-bg)]">
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Retry
              </button>
            </div>
          </div>
        )}

        {!ticketsQuery.isLoading && !ticketsQuery.isError && sortedItems.length === 0 && (
          <div className="rounded border border-[var(--border-default)] bg-[var(--bg-panel)] p-8 text-center" role="status">
            <Route className="mx-auto h-8 w-8 text-[var(--text-muted)]" aria-hidden="true" />
            <p className="mt-3 text-sm font-semibold text-[var(--text-primary)]">No tickets in this queue</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">Raise a new planning request to send it to the Block Manager.</p>
          </div>
        )}

        {sortedItems.length > 0 && (
          <Table caption="Department ticket queue">
            <TableHeader>
              <tr>
                <TableHeaderCell>Request</TableHeaderCell>
                <TableHeaderCell>Department</TableHeaderCell>
                <TableHeaderCell>Task type</TableHeaderCell>
                <TableHeaderCell>
                  <SortButton label="Severity" field="severity" sort={sort} onSort={toggleSort} />
                </TableHeaderCell>
                <TableHeaderCell>Requested window</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Linked task</TableHeaderCell>
                <TableHeaderCell>Block Finder</TableHeaderCell>
                <TableHeaderCell>
                  <SortButton label="Created" field="createdAt" sort={sort} onSort={toggleSort} />
                </TableHeaderCell>
              </tr>
            </TableHeader>
            <TableBody>
              {sortedItems.map((item) => {
                const ready = isBlockFinderReady(item);
                return (
                  <tr key={item.requestId}>
                    <TableCell>
                      <span className="font-mono font-semibold text-[var(--text-primary)]">{item.requestId}</span>
                      {item.synthetic && (
                        <div className="mt-1 text-[10px] font-mono uppercase tracking-wide text-[var(--text-muted)]">Synthetic demo data</div>
                      )}
                    </TableCell>
                    <TableCell><StatusChip def={getTokenDef(DEPARTMENT_TOKENS, item.department)} compact /></TableCell>
                    <TableCell>{item.taskType.replaceAll('_', ' ')}</TableCell>
                    <TableCell className="font-mono">{item.severity}</TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs">
                      {formatRequestedBoundary(item.requestedStart)} → {formatRequestedBoundary(item.requestedEnd)}
                    </TableCell>
                    <TableCell><StatusChip def={getTokenDef(BLOCK_REQUEST_STATUS_TOKENS, String(item.status))} compact /></TableCell>
                    <TableCell className="font-mono text-xs">{item.linkedTaskId || '—'}</TableCell>
                    <TableCell>
                      {ready ? (
                        <span className="inline-flex items-center gap-1 rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] px-2 py-1 text-xs font-semibold text-[var(--status-ok-text)]">Ready</span>
                      ) : (
                        <span className="text-xs text-[var(--text-muted)]">Not ready</span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs">{formatCreatedAt(item.createdAt)}</TableCell>
                  </tr>
                );
              })}
            </TableBody>
          </Table>
        )}

        <p className="text-xs text-[var(--text-secondary)]">
          Synthetic API connected. Ticket records are deterministic demo data and do not grant operating authority.
        </p>
      </div>

      <Modal
        open={composerOpen}
        title="New planning request"
        description="Submits a structured demand to the Block Manager for the active department."
        onClose={() => setComposerOpen(false)}
        maxWidthClassName="max-w-4xl"
      >
        <TicketComposer
          initialDepartment={activeTab === 'ALL' ? undefined : activeTab}
          onSubmitted={() => setComposerOpen(false)}
        />
      </Modal>
    </div>
  );
};

function SortButton({
  label,
  field,
  sort,
  onSort,
}: {
  label: string;
  field: SortField;
  sort: { field: SortField; direction: 'asc' | 'desc' };
  onSort: (field: SortField) => void;
}) {
  const active = sort.field === field;
  const Icon = sort.direction === 'asc' ? ArrowUp : ArrowDown;
  return (
    <button
      type="button"
      onClick={() => onSort(field)}
      aria-label={`Sort by ${label}${active ? `, currently ${sort.direction === 'asc' ? 'ascending' : 'descending'}` : ''}`}
      className="inline-flex min-h-9 items-center gap-1 font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
    >
      {label}
      {active && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
    </button>
  );
}
