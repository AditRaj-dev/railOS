'use client';

import React, { type ReactNode } from 'react';
import { useRailOSStore, type UserRole } from '@/store/railosStore';
import { useAuthStore } from '@/store/authStore';
import { setApiRole } from '@/lib/api';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard,
  Network,
  Wrench,
  CalendarClock,
  SlidersHorizontal,
  Smartphone,
  BarChart3,
  ShieldCheck,
  Film,
  Menu,
  X,
  LogIn,
  LogOut,
  Ticket,
} from 'lucide-react';
import { TerritorySelector } from './TerritorySelector';
import { ContextRail } from './ContextRail';
import { StatusBar } from './StatusBar';
import { LoginModal } from '../LoginModal';
import { useRailOSEventStream } from '@/lib/useRailOSEventStream';

const NAV_ITEMS: Array<{
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: string[];
}> = [
  { href: '/command-center', label: 'Command Center', icon: LayoutDashboard, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT'] },
  { href: '/network', label: 'Network Digital Twin', icon: Network, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT', 'STATION_MASTER', 'TPC'] },
  // Placed before /maintenance: the route guard below redirects an
  // unauthorized role to visibleNavItems[0], and department roles
  // (ENGG/SNT/TRD) should land on their ticket queue, not maintenance intel.
  { href: '/tickets', label: 'Tickets', icon: Ticket, roles: ['ENGINEERING', 'SIGNAL_TELECOM', 'TRACTION', 'FIELD_SUPERVISOR', 'PLANNER', 'CONTROL_OFFICER', 'MANAGEMENT', 'ADMIN'] },
  { href: '/maintenance', label: 'Maintenance Intelligence', icon: Wrench, roles: ['ADMIN', 'PLANNER', 'ENGINEERING', 'SIGNAL_TELECOM', 'TRACTION', 'FIELD_SUPERVISOR'] },
  { href: '/planner', label: 'Block Opportunity Planner', icon: CalendarClock, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER'] },
  { href: '/timeline', label: 'Operational Gantt', icon: CalendarClock, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT'] },
  { href: '/plans', label: 'Plan Sanctions', icon: SlidersHorizontal, roles: ['ADMIN', 'CONTROL_OFFICER', 'PLANNER', 'MANAGEMENT', 'TPC', 'STATION_MASTER', 'SIGNAL_TELECOM', 'ENGINEERING'] },
  { href: '/possessions', label: 'Possession Board', icon: ShieldCheck, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'TPC', 'STATION_MASTER', 'SIGNAL_TELECOM', 'ENGINEERING', 'TRACTION', 'FIELD_SUPERVISOR'] },
  { href: '/analytics', label: 'Railway Analytics', icon: BarChart3, roles: ['ADMIN', 'MANAGEMENT', 'PLANNER', 'CONTROL_OFFICER'] },
  { href: '/evidence', label: 'Field Evidence', icon: ShieldCheck, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'PLANNER'] },
  { href: '/evidence-media', label: 'Evidence Media Gallery', icon: Film, roles: ['ADMIN', 'CONTROL_OFFICER', 'MANAGEMENT', 'PLANNER'] },
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
  const { userRole, setUserRole } = useRailOSStore();
  const authSession = useAuthStore((s) => s.session);
  const authStatus = useAuthStore((s) => s.status);
  const restoreSession = useAuthStore((s) => s.restoreSession);
  const logout = useAuthStore((s) => s.logout);
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const [loginModalOpen, setLoginModalOpen] = React.useState(false);

  // Mounted once here rather than per-view: it already invalidates the
  // relevant query caches on BLOCK_REQUEST_CREATED and friends, and every
  // view under the shell benefits without opening a socket per view.
  // Unauthenticated, the socket has no token to send and the API closes it,
  // so it would only reconnect in a loop behind the login prompt.
  useRailOSEventStream(Boolean(authSession));

  React.useEffect(() => {
    // Attempt to restore a real session from a persisted refresh token once,
    // on first mount. If none exists (or it's expired/revoked) this settles
    // to 'unauthenticated' and the synthetic role selector remains in charge.
    void restoreSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    // Without a session every view renders empty on a wall of 401s, which
    // reads as "the data is missing" rather than "you are signed out". Ask
    // for credentials instead of leaving the operator to find the button.
    if (authStatus === 'unauthenticated') setLoginModalOpen(true);
  }, [authStatus]);

  React.useEffect(() => {
    // The acting role is a demo-session choice, not an identity: keep it across
    // reloads so a refresh doesn't silently drop an SSE back to Section
    // Controller. Restored after mount (not in the store's initial state) so
    // server and client render the same first paint.
    try {
      const stored = window.sessionStorage.getItem('railos.actingRole');
      if (stored) {
        setUserRole(stored as UserRole);
        setApiRole(stored as UserRole);
      }
    } catch {
      // Private mode / blocked storage: the default role still works.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    // Only push the dropdown's role when there's no real session — a login
    // already drives setApiRole itself via authStore, and re-running this on
    // every userRole change would fight a real session's role right after login
    // (setUserRole(realRole) below also updates userRole, re-triggering this
    // effect — guarding on authSession keeps the two paths from racing).
    if (!authSession) {
      setApiRole(userRole);
    }
  }, [userRole, authSession]);

  const handleRoleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const role = event.target.value as UserRole;
    setUserRole(role);
    // Keep the request layer in sync in the same event turn as the selector.
    setApiRole(role);
    try {
      window.sessionStorage.setItem('railos.actingRole', role);
    } catch {
      // Storage unavailable: the role still applies for this page's lifetime.
    }
  };

  const handleLogout = () => {
    void logout();
  };

  // Filter nav items based on user role
  const visibleNavItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole));

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  React.useEffect(() => {
    // The nav list hides items the acting role can't use, but hiding a link
    // doesn't stop a user from already being on that page — e.g. `/` always
    // redirects to `/command-center` before any role is known, and switching
    // roles via the dropdown doesn't otherwise navigate anywhere. Bounce to
    // the first page this role's own nav actually offers.
    const currentPageAllowed = NAV_ITEMS.some(
      (item) => item.roles.includes(userRole) && isActive(item.href)
    );
    if (!currentPageAllowed && visibleNavItems.length > 0) {
      router.replace(visibleNavItems[0].href);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userRole, pathname]);

  return (
    <div className="min-h-dvh bg-[var(--bg-canvas)] text-[var(--text-primary)] flex flex-col font-sans selection:bg-sky-500 selection:text-slate-950">
      {/* Top Navigation Bar */}
      <header className="min-h-14 border-b border-slate-800 bg-[var(--bg-surface)] px-3 md:px-4 py-2 flex flex-wrap items-center justify-between gap-2 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Link
              href="/command-center"
              className="w-8 h-8 shrink-0 rounded bg-[var(--accent)] border border-[var(--border-strong)] flex items-center justify-center font-mono font-black text-[var(--bg-canvas)] text-sm shadow-md hover:opacity-90 transition-all"
              aria-label="Railblock home"
            >
              R
            </Link>
            <div>
              <span className="font-mono font-bold text-sm tracking-wider text-[var(--text-primary)]">
                RAIL<span className="text-[var(--accent)]">BLOCK</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] font-mono text-[var(--text-muted)] ml-2 px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)]">
                INDIAN RAILWAYS CONTROL CENTER
              </span>
            </div>
          </div>

          {/* Territory Selector */}
          <div className="hidden lg:block border-l border-[var(--border-default)] pl-4">
            <TerritorySelector />
          </div>
        </div>

        {/* Status & Controls */}
          <div className="flex items-center gap-2 md:gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-secondary)] px-2 py-1 rounded bg-[var(--bg-panel)] border border-[var(--border-default)]" role="status">
            <span className="w-2 h-2 rounded-full bg-[var(--status-ok-fg)]" aria-hidden="true" />
            <span>SYNTHETIC API CONNECTED</span>
          </div>

          {authSession ? (
            <div className="flex items-center gap-2 rounded border border-[var(--status-ok-border)] bg-[var(--status-ok-bg)] px-2 py-1">
              <div className="flex flex-col leading-tight">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wide text-[var(--status-ok-text)]">
                  Signed in · {authSession.role.replace('_', ' ')}
                </span>
                <span className="text-xs font-mono font-semibold text-[var(--status-ok-text)]">{authSession.name}</span>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                aria-label="Sign out"
                className="min-h-9 flex items-center gap-1 px-2 rounded border border-[var(--status-ok-border)] text-[var(--status-ok-text)] hover:bg-[var(--status-ok-border)]/20 text-xs font-mono font-semibold"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
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
              <button
                onClick={() => setLoginModalOpen(true)}
                title="Sign in with a real account"
                aria-label="Sign in"
                disabled={authStatus === 'restoring'}
                className="min-h-9 flex items-center gap-1 px-2 rounded border border-[var(--border-strong)] text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--text-primary)] text-xs font-mono font-semibold disabled:opacity-50"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{authStatus === 'restoring' ? 'Checking…' : 'Log in'}</span>
              </button>
            </div>
          )}

          <button
            onClick={() => {
              const current = useRailOSStore.getState().activeDrawer;
              useRailOSStore.getState().setActiveDrawer(current ? null : 'alerts');
            }}
            title="Toggle Right Context Rail"
            aria-label="Toggle context panel"
            className="min-h-11 flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--bg-elevated)] hover:bg-[var(--bg-panel)] text-[var(--text-primary)] border border-[var(--border-default)] text-xs font-mono font-medium transition-all cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span className="hidden sm:inline">Panel</span>
          </button>


          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="md:hidden p-2 rounded hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all"
            aria-label="Toggle navigation"
          >
            {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu */}
      {mobileNavOpen && (
        <nav className="md:hidden px-3 py-2 border-b border-[var(--border-default)] bg-[var(--bg-panel)] space-y-1">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileNavOpen(false)}
                className={`w-full min-h-11 flex items-center gap-2.5 px-3 py-2 rounded text-xs font-mono font-semibold transition-all border ${
                  active
                    ? 'bg-[var(--status-caution-bg)] text-[var(--status-caution-text)] border-[var(--status-caution-border)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}

      {/* Main Layout */}
      <div className="flex-1 flex">
        {/* Left Sidebar Navigation (Desktop) */}
        <aside
          aria-label="Operational views"
          className="w-64 border-r border-[var(--border-default)] bg-[var(--bg-surface)] p-3 flex flex-col justify-between hidden md:flex"
        >
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] px-3 py-1.5 font-bold">
              Operational Views
            </div>

            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={`w-full min-h-11 flex items-center gap-2.5 px-3 py-2 rounded text-xs font-mono font-semibold transition-all border cursor-pointer ${
                    active
                      ? 'bg-[var(--status-caution-bg)] text-[var(--status-caution-text)] border-[var(--status-caution-border)] shadow-sm'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="p-3 rounded border border-[var(--border-default)] bg-[var(--bg-elevated)] text-[11px] font-mono text-[var(--text-muted)] space-y-1">
            <div className="text-[var(--text-primary)] font-bold">Corridor Division</div>
            <div>Prayagraj (NCR) & Delhi (NR)</div>
            <div className="text-[10px] text-[var(--text-muted)] pt-1 border-t border-[var(--border-default)]">
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
            <h1 className="sr-only">Railblock Control Center</h1>
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

      <LoginModal open={loginModalOpen} onClose={() => setLoginModalOpen(false)} />
    </div>
  );
}
