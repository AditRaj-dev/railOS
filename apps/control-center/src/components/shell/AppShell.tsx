'use client';

import React, { type ReactNode } from 'react';
import { useRailOSStore, type UserRole } from '@/store/railosStore';
import { useResetDemo } from '@/lib/queries';
import { setApiRole } from '@/lib/api';
import { useRouter, usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Network,
  Wrench,
  CalendarClock,
  SlidersHorizontal,
  Smartphone,
  BarChart3,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Menu,
  X,
} from 'lucide-react';
import { TerritorySelector } from './TerritorySelector';
import { ContextRail } from './ContextRail';
import { StatusBar } from './StatusBar';

const NAV_ITEMS: Array<{
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: string[];
}> = [
  { href: '/command-center', label: 'Command Center', icon: LayoutDashboard, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT'] },
  { href: '/network', label: 'Network Digital Twin', icon: Network, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT', 'STATION_MASTER', 'TPC'] },
  { href: '/maintenance', label: 'Maintenance Intelligence', icon: Wrench, roles: ['ADMIN', 'PLANNER', 'ENGINEERING', 'SIGNAL_TELECOM', 'TRACTION', 'FIELD_SUPERVISOR'] },
  { href: '/planner', label: 'Block Opportunity Planner', icon: CalendarClock, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER'] },
  { href: '/timeline', label: 'Operational Gantt', icon: CalendarClock, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT'] },
  { href: '/plans', label: 'Plan Sanctions', icon: SlidersHorizontal, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT', 'TPC', 'STATION_MASTER', 'SIGNAL_TELECOM', 'ENGINEERING'] },
  { href: '/possessions', label: 'Possession Board', icon: ShieldCheck, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'TPC', 'STATION_MASTER', 'SIGNAL_TELECOM', 'ENGINEERING', 'TRACTION', 'FIELD_SUPERVISOR'] },
  { href: '/analytics', label: 'Railway Analytics', icon: BarChart3, roles: ['ADMIN', 'MANAGEMENT', 'PLANNER', 'CONTROL_OFFICER'] },
  { href: '/evidence', label: 'Field Evidence', icon: ShieldCheck, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'PLANNER'] },
  { href: '/field', label: 'Field Monitor', icon: Smartphone, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'PLANNER', 'FIELD_SUPERVISOR', 'ENGINEERING', 'SIGNAL_TELECOM', 'TRACTION', 'TPC', 'STATION_MASTER'] },
];

const ROLE_OPTIONS: Array<{ value: UserRole; label: string }> = [
  { value: 'CONTROL_OFFICER', label: 'Section Controller' },
  { value: 'MANAGEMENT', label: 'Sr. DOM / Management' },
  { value: 'TPC', label: 'Traction Power Controller' },
  { value: 'STATION_MASTER', label: 'Station Master' },
  { value: 'ENGINEERING', label: 'SSE / Engineering' },
  { value: 'SIGNAL_TELECOM', label: 'Signal & Telecom' },
  { value: 'TRACTION', label: 'Traction' },
  { value: 'FIELD_SUPERVISOR', label: 'Field Supervisor' },
  { value: 'PLANNER', label: 'Maintenance Planner' },
  { value: 'ADMIN', label: 'Administrator' },
];

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { resetToDefault, isEmergencyActive, userRole, setUserRole } = useRailOSStore();
  const resetDemoMutation = useResetDemo();
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  React.useEffect(() => {
    setApiRole(userRole);
  }, [userRole]);

  const handleRoleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const role = event.target.value as UserRole;
    setUserRole(role);
    // Keep the request layer in sync in the same event turn as the selector.
    setApiRole(role);
  };

  const handleReset = () => {
    resetToDefault();
    resetDemoMutation.mutate();
  };

  // Filter nav items based on user role
  const visibleNavItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole));

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  return (
    <div className="min-h-dvh bg-[var(--bg-canvas)] text-[var(--text-primary)] flex flex-col font-sans selection:bg-sky-500 selection:text-slate-950">
      {/* Top Navigation Bar */}
      <header className="min-h-14 border-b border-slate-800 bg-[var(--bg-surface)] px-3 md:px-4 py-2 flex flex-wrap items-center justify-between gap-2 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 shrink-0 rounded bg-sky-600 border border-sky-400 flex items-center justify-center font-mono font-black text-slate-950 text-sm shadow-md cursor-pointer hover:bg-sky-500 transition-all"
              onClick={() => router.push('/command-center')}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  router.push('/command-center');
                }
              }}
              role="button"
              tabIndex={0}
              aria-label="Home"
            >
              R
            </div>
            <div>
              <span className="font-mono font-bold text-sm tracking-wider text-white">
                RAIL<span className="text-sky-400">OS</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] font-mono text-slate-400 ml-2 px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
                INDIAN RAILWAYS CONTROL CENTER
              </span>
            </div>
          </div>

          {/* Territory Selector */}
          <div className="hidden lg:block border-l border-slate-800/50 pl-4">
            <TerritorySelector />
          </div>
        </div>

        {/* Status & Controls */}
          <div className="flex items-center gap-2 md:gap-3">
          {isEmergencyActive && (
            <div
              role="status"
              className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded bg-red-950/80 border border-red-500 text-red-300 font-mono text-xs animate-pulse"
            >
              <ShieldAlert className="w-4 h-4 text-red-400" />
              <span>EMERGENCY FRACTURE ON DOWN LINE</span>
            </div>
          )}

          <div className="flex items-center gap-2 text-xs font-mono text-slate-300 px-2 py-1 rounded bg-slate-900 border border-slate-800" role="status">
            <span className="w-2 h-2 rounded-full bg-emerald-400" aria-hidden="true" />
            <span>CRIS/NTES FEED LIVE</span>
          </div>

          <div className="flex items-center gap-2 rounded border border-[var(--border-default)] bg-[var(--bg-elevated)] px-2 py-1">
            <label htmlFor="shell-role" className="text-[10px] font-mono font-bold uppercase tracking-wide text-[var(--text-muted)]">Acting role</label>
            <select
              id="shell-role"
              value={userRole}
              onChange={handleRoleChange}
              aria-label="Acting role"
              className="min-h-9 max-w-44 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-2 text-xs font-mono font-semibold text-[var(--text-primary)]"
            >
              {ROLE_OPTIONS.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
            </select>
          </div>

          <button
            onClick={handleReset}
            disabled={resetDemoMutation.isPending}
            title="Reset to Baseline Demo Scenario"
            className="min-h-11 flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono font-medium transition-all cursor-pointer disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetDemoMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{resetDemoMutation.isPending ? 'Resetting...' : 'Reset Demo'}</span>
          </button>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="md:hidden p-2 rounded hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 transition-all"
            aria-label="Toggle navigation"
          >
            {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu */}
      {mobileNavOpen && (
        <nav className="md:hidden px-3 py-2 border-b border-slate-800 bg-slate-950/70 space-y-1">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <button
                key={item.href}
                onClick={() => {
                  router.push(item.href);
                  setMobileNavOpen(false);
                }}
                className={`w-full min-h-11 flex items-center gap-2.5 px-3 py-2 rounded text-xs font-mono font-semibold transition-all border ${
                  active
                    ? 'bg-sky-600/20 text-sky-300 border-sky-500/50'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      )}

      {/* Main Layout */}
      <div className="flex-1 flex">
        {/* Left Sidebar Navigation (Desktop) */}
        <aside
          aria-label="Operational views"
          className="w-64 border-r border-slate-800/90 bg-[var(--bg-surface)] p-3 flex flex-col justify-between hidden md:flex"
        >
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-3 py-1.5 font-bold">
              Operational Views
            </div>

            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <button
                  key={item.href}
                  onClick={() => router.push(item.href)}
                  aria-current={active ? 'page' : undefined}
                  className={`w-full min-h-11 flex items-center gap-2.5 px-3 py-2 rounded text-xs font-mono font-semibold transition-all border cursor-pointer ${
                    active
                      ? 'bg-sky-600/20 text-sky-300 border-sky-500/50 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-sky-400' : 'text-slate-500'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="p-3 rounded border border-slate-800/80 bg-slate-900/50 text-[11px] font-mono text-slate-400 space-y-1">
            <div className="text-slate-200 font-bold">Corridor Division</div>
            <div>Prayagraj (NCR) & Delhi (NR)</div>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
              Trunk: NDLS–GZB–ALJN–TDL
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main
          className="flex-1 flex flex-col"
          id="main-content"
        >
          {/* Content Area */}
          <div className="flex-1 p-3 md:p-4 overflow-y-auto">
            <h1 className="sr-only">RailOS Control Center</h1>
            {children}
          </div>

          {/* Context Rail */}
          <div className="hidden lg:block absolute right-0 top-14 bottom-14 w-80 pointer-events-none">
            <ContextRail />
          </div>
        </main>
      </div>

      {/* Status Bar */}
      <StatusBar />
    </div>
  );
}
