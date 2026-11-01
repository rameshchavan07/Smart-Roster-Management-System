import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  AlertTriangle,
  Clock,
  Users,
  Briefcase,
  FileText,
  Sliders,
  Palette,
  LogOut,
  X,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';

export interface SidebarProps {
  isOpenOnMobile?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpenOnMobile = false,
  onCloseMobile,
}) => {
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

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 rounded-ctl px-2.5 py-2 transition-colors ${
      isActive
        ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
        : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
    }`;

  const sidebarContent = (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-surface text-ink">
      {/* Brand header */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-ctl bg-accent-600 text-surface font-semibold text-sm shadow-sm">
            R
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-ink leading-tight">
              RosterOps
            </h1>
            <p className="text-[10px] text-ink-3 uppercase tracking-wider font-medium">
              Scheduler
            </p>
          </div>
        </div>

        {/* Mobile close button */}
        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close sidebar"
            className="md:hidden flex h-7 w-7 items-center justify-center rounded-ctl text-ink-3 hover:text-ink hover:bg-surface-2"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Navigation items */}
      <nav className="flex-1 space-y-1 p-2 text-xs font-medium overflow-y-auto">
        {/* Main section */}
        {!isEmployee && (
          <NavLink to="/" end className={navLinkClass} onClick={onCloseMobile}>
            <LayoutDashboard className="h-4 w-4 shrink-0" />
            <span>Dashboard</span>
          </NavLink>
        )}

        <NavLink to="/roster" className={navLinkClass} onClick={onCloseMobile}>
          <Calendar className="h-4 w-4 shrink-0" />
          <span>{isEmployee ? 'My Roster' : 'Roster Workspace'}</span>
        </NavLink>

        {!isEmployee && (
          <NavLink to="/conflicts" className={navLinkClass} onClick={onCloseMobile}>
            <AlertTriangle className="h-4 w-4 shrink-0 text-warn" />
            <span>Conflicts</span>
          </NavLink>
        )}

        <NavLink to="/leaves" className={navLinkClass} onClick={onCloseMobile}>
          <Clock className="h-4 w-4 shrink-0" />
          <span>Leaves & Comp-offs</span>
        </NavLink>

        {/* Management section */}
        {!isEmployee && (
          <>
            <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
              Management
            </div>

            <NavLink to="/team" className={navLinkClass} onClick={onCloseMobile}>
              <Users className="h-4 w-4 shrink-0" />
              <span>Team & Pods</span>
            </NavLink>

            <NavLink to="/brands" className={navLinkClass} onClick={onCloseMobile}>
              <Briefcase className="h-4 w-4 shrink-0" />
              <span>Brands & Processes</span>
            </NavLink>

            <NavLink to="/reports" className={navLinkClass} onClick={onCloseMobile}>
              <FileText className="h-4 w-4 shrink-0" />
              <span>Reports & Export</span>
            </NavLink>
          </>
        )}

        {/* Settings & Reference */}
        {isOpsManager && (
          <>
            <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
              Administration
            </div>

            <NavLink to="/settings" className={navLinkClass} onClick={onCloseMobile}>
              <Sliders className="h-4 w-4 shrink-0" />
              <span>Settings & Audit</span>
            </NavLink>
          </>
        )}

        <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
          Reference
        </div>

        <NavLink to="/design-system" className={navLinkClass} onClick={onCloseMobile}>
          <Palette className="h-4 w-4 shrink-0 text-accent-600" />
          <span>Design System</span>
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
            <p className="text-[11px] text-ink-3 truncate leading-tight font-mono">
              {user?.email}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => logout()}
          title="Sign out"
          aria-label="Sign out"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-ctl text-ink-3 hover:text-bad hover:bg-bad/10 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-600"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:flex h-full shrink-0">{sidebarContent}</div>

      {/* Mobile Drawer Overlay */}
      {isOpenOnMobile && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          <div
            className="fixed inset-0 bg-ink/30 backdrop-blur-[2px]"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-50 flex h-full">{sidebarContent}</div>
        </div>
      )}
    </>
  );
};
