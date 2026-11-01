import React from 'react';
import {
  Calendar,
  AlertTriangle,
  Users,
  Briefcase,
  Sliders,
  FileText,
  Clock,
  LayoutDashboard,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

export const Layout: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-ink">
      {/* Left Sidebar */}
      <aside className="flex w-56 flex-col border-r border-border bg-surface">
        {/* Brand header */}
        <div className="flex h-14 items-center gap-2 px-4 border-b border-border">
          <div className="flex h-7 w-7 items-center justify-center rounded-ctl bg-accent-600 text-surface font-semibold text-sm">
            R
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-ink">RosterOps</h1>
            <p className="text-[11px] text-ink-3">Operations Scheduler</p>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 space-y-1 p-2 text-xs font-medium">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>

          <NavLink
            to="/roster"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Calendar className="h-4 w-4" />
            Roster Workspace
          </NavLink>

          <NavLink
            to="/conflicts"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <AlertTriangle className="h-4 w-4 text-warn" />
            Conflicts
          </NavLink>

          <NavLink
            to="/leaves"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Clock className="h-4 w-4" />
            Leaves & Comp-offs
          </NavLink>

          <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Management
          </div>

          <NavLink
            to="/team"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Users className="h-4 w-4" />
            Team & Pods
          </NavLink>

          <NavLink
            to="/brands"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Briefcase className="h-4 w-4" />
            Brands & Processes
          </NavLink>

          <NavLink
            to="/reports"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <FileText className="h-4 w-4" />
            Reports & Export
          </NavLink>

          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Sliders className="h-4 w-4" />
            Settings
          </NavLink>
        </nav>

        {/* User profile footer */}
        <div className="flex items-center justify-between border-t border-border p-3 text-xs">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-100 font-semibold text-accent-700 text-xs">
              OM
            </div>
            <div className="truncate">
              <p className="font-medium text-ink truncate leading-tight">Ops Manager</p>
              <p className="text-[11px] text-ink-3 truncate leading-tight">ops@example.test</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono font-medium text-ink bg-surface-2 px-2.5 py-1 rounded-ctl border border-border">
              Dec 2026
            </span>
            <span className="inline-flex items-center rounded-chip bg-accent-50 px-2 py-0.5 text-[11px] font-medium text-accent-700 border border-accent-100">
              Roster v1 · DRAFT
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-3 font-mono">Backend: :8000</span>
          </div>
        </header>

        {/* Routed Screen Outlet */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const DashboardPlaceholder: React.FC = () => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold text-ink">Dashboard</h2>
        <p className="text-xs text-ink-2">Monthly operational metrics and roster health overview</p>
      </div>
    </div>

    <div className="grid grid-cols-4 gap-4">
      <div className="rounded-ctl border border-border bg-surface p-4">
        <p className="text-xs text-ink-3">Coverage Target</p>
        <p className="mt-1 text-2xl font-semibold font-mono text-ok">99.1%</p>
      </div>
      <div className="rounded-ctl border border-border bg-surface p-4">
        <p className="text-xs text-ink-3">Blocking Conflicts</p>
        <p className="mt-1 text-2xl font-semibold font-mono text-bad">2</p>
      </div>
      <div className="rounded-ctl border border-border bg-surface p-4">
        <p className="text-xs text-ink-3">Warnings</p>
        <p className="mt-1 text-2xl font-semibold font-mono text-warn">5</p>
      </div>
      <div className="rounded-ctl border border-border bg-surface p-4">
        <p className="text-xs text-ink-3">Single-Point Brands</p>
        <p className="mt-1 text-2xl font-semibold font-mono text-ink">14</p>
      </div>
    </div>
  </div>
);

export const RosterPlaceholder: React.FC = () => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold text-ink">Roster Workspace</h2>
        <p className="text-xs text-ink-2">Plan, validate, and manage December 2026 roster</p>
      </div>
    </div>
    <div className="flex h-72 items-center justify-center rounded-ctl border border-dashed border-border-strong bg-surface">
      <p className="text-xs text-ink-3 font-mono">RosterGrid container ready (:5173 blank shell)</p>
    </div>
  </div>
);
