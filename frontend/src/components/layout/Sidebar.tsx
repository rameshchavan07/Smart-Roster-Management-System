import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  AlertTriangle,
  Sparkles,
  Clock,
  Users,
  Briefcase,
  FileText,
  Sliders,
  CalendarDays,
  LogOut,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';

export interface SidebarProps {
  isOpenOnMobile?: boolean;
  onCloseMobile?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpenOnMobile = false,
  onCloseMobile,
  isCollapsed: controlledCollapsed,
  onToggleCollapse,
}) => {
  const { user, logout, isOpsManager, isEmployee } = useAuth();

  // Internal collapse state with auto-collapse between 768px and 1279px (Tablet breakpoint)
  const [internalCollapsed, setInternalCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768 && window.innerWidth < 1280;
    }
    return false;
  });

  const isCollapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed;

  const handleToggle = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  };

  // Responsive listener for auto-collapsing to 56px icon rail on tablet
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width >= 768 && width < 1280) {
        setInternalCollapsed(true);
      } else if (width >= 1280) {
        // preserve user choice if desktop
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
    `flex items-center ${
      isCollapsed ? 'justify-center px-0 h-10 w-10 mx-auto' : 'gap-2.5 px-2.5 py-2'
    } rounded-ctl transition-colors ${
      isActive
        ? 'bg-accent-50 font-semibold text-accent-700 border-l-2 border-accent-600'
        : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
    }`;

  const sidebarContent = (
    <aside
      className={`flex h-full flex-col border-r border-border bg-surface text-ink transition-all duration-200 ${
        isCollapsed ? 'w-14' : 'w-56'
      }`}
    >
      {/* Brand header */}
      <div
        className={`flex h-14 items-center ${
          isCollapsed ? 'justify-center px-2' : 'justify-between px-4'
        } border-b border-border`}
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-ctl bg-accent-600 text-surface font-semibold text-sm shadow-sm"
            title="RosterOps Scheduler"
          >
            R
          </div>
          {!isCollapsed && (
            <div className="truncate">
              <h1 className="text-sm font-semibold tracking-tight text-ink leading-tight truncate">
                RosterOps
              </h1>
              <p className="text-[10px] text-ink-3 uppercase tracking-wider font-medium truncate">
                Scheduler
              </p>
            </div>
          )}
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
          <NavLink
            to="/"
            end
            title="Dashboard"
            className={navLinkClass}
            onClick={onCloseMobile}
          >
            <LayoutDashboard className="h-4 w-4 shrink-0" />
            {!isCollapsed && <span>Dashboard</span>}
          </NavLink>
        )}

        <NavLink
          to="/roster"
          title={isEmployee ? 'My Roster' : 'Roster Workspace'}
          className={navLinkClass}
          onClick={onCloseMobile}
        >
          <Calendar className="h-4 w-4 shrink-0" />
          {!isCollapsed && <span>{isEmployee ? 'My Roster' : 'Roster Workspace'}</span>}
        </NavLink>

        {!isEmployee && (
          <NavLink
            to="/conflicts"
            title="Conflicts"
            className={navLinkClass}
            onClick={onCloseMobile}
          >
            <AlertTriangle className="h-4 w-4 shrink-0 text-warn" />
            {!isCollapsed && <span>Conflicts</span>}
          </NavLink>
        )}

        {!isEmployee && (
          <NavLink
            to="/simulator"
            title="Impact Simulator"
            className={navLinkClass}
            onClick={onCloseMobile}
          >
            <Sparkles className="h-4 w-4 shrink-0 text-accent-700" />
            {!isCollapsed && <span>Impact Simulator</span>}
          </NavLink>
        )}

        <NavLink
          to="/leaves"
          title="Leaves & Comp-offs"
          className={navLinkClass}
          onClick={onCloseMobile}
        >
          <Clock className="h-4 w-4 shrink-0" />
          {!isCollapsed && <span>Leaves & Comp-offs</span>}
        </NavLink>

        {/* Management section */}
        {!isEmployee && (
          <>
            {!isCollapsed ? (
              <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
                Management
              </div>
            ) : (
              <div className="my-2 border-t border-border" />
            )}

            <NavLink
              to="/team"
              title="Team & Pods"
              className={navLinkClass}
              onClick={onCloseMobile}
            >
              <Users className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span>Team & Pods</span>}
            </NavLink>

            <NavLink
              to="/brands"
              title="Brands & Processes"
              className={navLinkClass}
              onClick={onCloseMobile}
            >
              <Briefcase className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span>Brands & Processes</span>}
            </NavLink>

            <NavLink
              to="/rules"
              title="Rules & Holidays"
              className={navLinkClass}
              onClick={onCloseMobile}
            >
              <CalendarDays className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span>Rules & Holidays</span>}
            </NavLink>

            <NavLink
              to="/reports"
              title="Reports & Export"
              className={navLinkClass}
              onClick={onCloseMobile}
            >
              <FileText className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span>Reports & Export</span>}
            </NavLink>
          </>
        )}

        {/* Administration section */}
        {isOpsManager && (
          <>
            {!isCollapsed ? (
              <div className="pt-3 pb-1 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
                Administration
              </div>
            ) : (
              <div className="my-2 border-t border-border" />
            )}

            <NavLink
              to="/settings"
              title="Settings & Audit"
              className={navLinkClass}
              onClick={onCloseMobile}
            >
              <Sliders className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span>Settings & Audit</span>}
            </NavLink>
          </>
        )}
      </nav>

      {/* Collapse / Expand Toggle Button for Desktop */}
      <div className="hidden md:flex border-t border-border p-2">
        <button
          type="button"
          onClick={handleToggle}
          title={isCollapsed ? 'Expand sidebar (232px)' : 'Collapse sidebar to icon rail (56px)'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={`flex h-8 w-full items-center ${
            isCollapsed ? 'justify-center' : 'justify-between px-2.5'
          } rounded-ctl text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors text-xs`}
        >
          {!isCollapsed && <span className="text-[11px] font-medium">Collapse Rail</span>}
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* User profile footer with Logout */}
      <div
        className={`flex items-center ${
          isCollapsed ? 'justify-center p-2' : 'justify-between p-3'
        } border-t border-border text-xs bg-surface`}
      >
        <div
          className="flex items-center gap-2 overflow-hidden"
          title={`${roleInfo.label} (${user?.email})`}
        >
          <div
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-semibold text-xs ${roleInfo.color}`}
          >
            {roleInfo.initials}
          </div>
          {!isCollapsed && (
            <div className="truncate">
              <p className="font-medium text-ink truncate leading-tight">{roleInfo.label}</p>
              <p className="text-[11px] text-ink-3 truncate leading-tight font-mono">
                {user?.email}
              </p>
            </div>
          )}
        </div>

        {!isCollapsed && (
          <button
            type="button"
            onClick={() => logout()}
            title="Sign out"
            aria-label="Sign out"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-ctl text-ink-3 hover:text-bad hover:bg-bad/10 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-600"
          >
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop & Tablet Persistent Sidebar */}
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
