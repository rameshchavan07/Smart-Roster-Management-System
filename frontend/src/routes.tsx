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
  Palette,
  LogOut,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from './features/auth/AuthContext';

export const Layout: React.FC = () => {
  const { user, logout, isOpsManager, isEmployee } = useAuth();

  const getRoleBadge = () => {
    switch (user?.role) {
      case 'OPS_MANAGER':
        return { label: 'Ops Manager', initials: 'OM', color: 'bg-accent-100 text-accent-700' };
      case 'POD_LEAD':
        return { label: 'Pod Lead', initials: 'PL', color: 'bg-ok/10 text-ok' };
      case 'EMPLOYEE':
        return { label: 'Employee', initials: 'EM', color: 'bg-surface-2 text-ink-2' };
      default:
        return { label: 'User', initials: 'U', color: 'bg-surface-2 text-ink-2' };
    }
  };

  const roleInfo = getRoleBadge();

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
        <nav className="flex-1 space-y-1 p-2 text-xs font-medium overflow-y-auto">
          {/* Dashboard: Ops Manager & Pod Lead only */}
          {!isEmployee && (
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
          )}

          {/* Roster Workspace: All roles */}
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
            {isEmployee ? 'My Roster' : 'Roster Workspace'}
          </NavLink>

          {/* Conflicts: Ops Manager & Pod Lead */}
          {!isEmployee && (
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
          )}

          {/* Leaves: All roles */}
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

          {/* Management section: Ops Manager & Pod Lead */}
          {!isEmployee && (
            <>
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
            </>
          )}

          {/* Settings: Ops Manager only */}
          {isOpsManager && (
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
          )}

          <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
            Reference
          </div>

          <NavLink
            to="/design-system"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
                isActive
                  ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
                  : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`
            }
          >
            <Palette className="h-4 w-4 text-accent-600" />
            Design System
          </NavLink>
        </nav>

        {/* User profile footer with Logout */}
        <div className="flex items-center justify-between border-t border-border p-3 text-xs bg-surface">
          <div className="flex items-center gap-2 overflow-hidden">
            <div
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-semibold text-xs ${roleInfo.color}`}
            >
              {roleInfo.initials}
            </div>
            <div className="truncate">
              <p className="font-medium text-ink truncate leading-tight">{roleInfo.label}</p>
              <p className="text-[11px] text-ink-3 truncate leading-tight font-mono">{user?.email}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={logout}
            title="Sign out"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-ctl text-ink-3 hover:text-bad hover:bg-bad/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
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
            <span className="text-[11px] font-mono text-ink-3">
              Role: <span className="font-semibold text-ink">{user?.role}</span>
            </span>
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

