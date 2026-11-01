import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  AlertTriangle,
  Clock,
  Menu,
  X,
  Users,
  Briefcase,
  CalendarDays,
  Sparkles,
  FileText,
  Sliders,
  Palette,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';
import { useMonth } from '../../context/MonthContext';

export interface BottomTabBarProps {
  conflictsCount?: number;
}

export const BottomTabBar: React.FC<BottomTabBarProps> = ({ conflictsCount = 0 }) => {
  const { user, logout, isOpsManager, isEmployee } = useAuth();
  const { monthLabel } = useMonth();
  const [isMoreSheetOpen, setIsMoreSheetOpen] = useState(false);

  const tabItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-1 flex-col items-center justify-center h-full min-h-[44px] transition-colors ${
      isActive ? 'text-accent-700 font-semibold' : 'text-ink-3 hover:text-ink'
    }`;

  const moreLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-ctl text-xs font-medium transition-colors ${
      isActive
        ? 'bg-accent-50 text-accent-700 font-semibold'
        : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
    }`;

  return (
    <>
      {/* Fixed Bottom Tab Bar for Mobile (< 768px) */}
      <nav
        aria-label="Mobile Navigation"
        className="fixed bottom-0 inset-x-0 z-40 h-14 bg-surface/95 backdrop-blur border-t border-border flex items-center justify-around md:hidden shadow-layer"
      >
        {!isEmployee ? (
          <NavLink to="/" end className={tabItemClass}>
            <LayoutDashboard className="w-5 h-5" />
            <span className="text-[10px] mt-0.5">Home</span>
          </NavLink>
        ) : (
          <NavLink to="/roster" className={tabItemClass}>
            <Calendar className="w-5 h-5" />
            <span className="text-[10px] mt-0.5">My Roster</span>
          </NavLink>
        )}

        {!isEmployee && (
          <NavLink to="/roster" className={tabItemClass}>
            <Calendar className="w-5 h-5" />
            <span className="text-[10px] mt-0.5">Roster</span>
          </NavLink>
        )}

        {!isEmployee && (
          <NavLink to="/conflicts" className={tabItemClass}>
            <div className="relative">
              <AlertTriangle className="w-5 h-5 text-warn" />
              {conflictsCount > 0 && (
                <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-bad animate-pulse" />
              )}
            </div>
            <span className="text-[10px] mt-0.5">Conflicts</span>
          </NavLink>
        )}

        <NavLink to="/leaves" className={tabItemClass}>
          <Clock className="w-5 h-5" />
          <span className="text-[10px] mt-0.5">Leaves</span>
        </NavLink>

        <button
          type="button"
          onClick={() => setIsMoreSheetOpen(true)}
          className="flex flex-1 flex-col items-center justify-center h-full min-h-[44px] text-ink-3 hover:text-ink transition-colors"
          aria-label="Open more menu"
        >
          <Menu className="w-5 h-5" />
          <span className="text-[10px] mt-0.5">More</span>
        </button>
      </nav>

      {/* Slide-up "More" Sheet on Mobile */}
      {isMoreSheetOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex flex-col justify-end">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-ink/40 backdrop-blur-xs transition-opacity"
            onClick={() => setIsMoreSheetOpen(false)}
          />

          {/* Sheet Surface */}
          <div className="relative z-50 w-full max-h-[85vh] bg-surface rounded-t-pop border-t border-border flex flex-col shadow-layer animate-in slide-in-from-bottom duration-200">
            {/* Sheet Header */}
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <h3 className="text-sm font-semibold text-ink">All Operations</h3>
                <p className="text-[11px] text-ink-3">Month: {monthLabel}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsMoreSheetOpen(false)}
                className="h-10 w-10 flex items-center justify-center text-ink-3 hover:text-ink rounded-ctl"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Links List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {!isEmployee && (
                <>
                  <NavLink
                    to="/simulator"
                    className={moreLinkClass}
                    onClick={() => setIsMoreSheetOpen(false)}
                  >
                    <Sparkles className="w-4 h-4 text-accent-700" />
                    <span>Impact Simulator</span>
                  </NavLink>

                  <NavLink
                    to="/team"
                    className={moreLinkClass}
                    onClick={() => setIsMoreSheetOpen(false)}
                  >
                    <Users className="w-4 h-4 text-ink-2" />
                    <span>Team & Pods</span>
                  </NavLink>

                  <NavLink
                    to="/brands"
                    className={moreLinkClass}
                    onClick={() => setIsMoreSheetOpen(false)}
                  >
                    <Briefcase className="w-4 h-4 text-ink-2" />
                    <span>Brands & Processes</span>
                  </NavLink>

                  <NavLink
                    to="/rules"
                    className={moreLinkClass}
                    onClick={() => setIsMoreSheetOpen(false)}
                  >
                    <CalendarDays className="w-4 h-4 text-ink-2" />
                    <span>Rules & Holidays</span>
                  </NavLink>

                  <NavLink
                    to="/reports"
                    className={moreLinkClass}
                    onClick={() => setIsMoreSheetOpen(false)}
                  >
                    <FileText className="w-4 h-4 text-ink-2" />
                    <span>Reports & Export</span>
                  </NavLink>
                </>
              )}

              {isOpsManager && (
                <NavLink
                  to="/settings"
                  className={moreLinkClass}
                  onClick={() => setIsMoreSheetOpen(false)}
                >
                  <Sliders className="w-4 h-4 text-ink-2" />
                  <span>Settings & Audit</span>
                </NavLink>
              )}

              <NavLink
                to="/design-system"
                className={moreLinkClass}
                onClick={() => setIsMoreSheetOpen(false)}
              >
                <Palette className="w-4 h-4 text-accent-600" />
                <span>Design System</span>
              </NavLink>

              {/* User profile & signout */}
              <div className="pt-3 mt-2 border-t border-border">
                <div className="flex items-center justify-between p-2 rounded-ctl bg-surface-2">
                  <div className="truncate">
                    <p className="text-xs font-semibold text-ink truncate">{user?.email}</p>
                    <p className="text-[10px] text-ink-3 uppercase font-mono">{user?.role}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setIsMoreSheetOpen(false);
                      logout();
                    }}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-medium text-bad hover:bg-bad/10 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
