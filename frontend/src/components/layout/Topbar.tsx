import React from 'react';
import { Menu, Search, Command } from 'lucide-react';
import { MonthSwitcher } from './MonthSwitcher';
import { Breadcrumbs } from './Breadcrumbs';
import { useAuth } from '../../features/auth/AuthContext';

export interface TopbarProps {
  onOpenMobileMenu: () => void;
  onOpenCommandPalette: () => void;
  rosterVersion?: number;
  rosterStatus?: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
}

export const Topbar: React.FC<TopbarProps> = ({
  onOpenMobileMenu,
  onOpenCommandPalette,
  rosterVersion = 1,
  rosterStatus = 'DRAFT',
}) => {
  const { user } = useAuth();

  const getStatusChip = () => {
    switch (rosterStatus) {
      case 'PUBLISHED':
        return {
          label: `Roster v${rosterVersion} · PUBLISHED`,
          className: 'bg-ok/10 text-ok border-ok/20',
        };
      case 'ARCHIVED':
        return {
          label: `Roster v${rosterVersion} · ARCHIVED`,
          className: 'bg-surface-2 text-ink-3 border-border',
        };
      default:
        return {
          label: `Roster v${rosterVersion} · DRAFT`,
          className: 'bg-accent-50 text-accent-700 border-accent-100',
        };
    }
  };

  const statusChip = getStatusChip();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6">
      {/* Left: Mobile hamburger + Breadcrumbs & Month Switcher */}
      <div className="flex items-center gap-3 sm:gap-4 overflow-hidden">
        {/* Mobile menu button */}
        <button
          type="button"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation sidebar"
          className="md:hidden flex h-8 w-8 items-center justify-center rounded-ctl border border-border text-ink-2 hover:bg-surface-2"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Month Switcher */}
        <MonthSwitcher />

        {/* Divider */}
        <div className="hidden sm:block h-4 w-px bg-border" />

        {/* Breadcrumb navigation */}
        <div className="hidden lg:block">
          <Breadcrumbs />
        </div>
      </div>

      {/* Right: Command Palette trigger + Roster Status Chip + Role Badge */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Command Palette Button */}
        <button
          type="button"
          onClick={onOpenCommandPalette}
          title="Search or run command (Ctrl+K or ⌘K)"
          aria-label="Open command palette"
          className="flex h-8 items-center gap-2 rounded-ctl border border-border bg-surface-2/60 px-2.5 text-xs text-ink-3 hover:border-border-strong hover:text-ink transition-colors focus:outline-none focus:ring-2 focus:ring-accent-600"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search / Commands</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded-ctl border border-border bg-surface px-1.5 py-0.5 text-[10px] font-mono text-ink-2 shadow-xs">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        {/* Status chip */}
        <span
          className={`hidden xs:inline-flex items-center rounded-chip px-2 py-0.5 text-[11px] font-medium font-mono border ${statusChip.className}`}
        >
          {statusChip.label}
        </span>

        {/* User Role Tag */}
        {user?.role && (
          <span className="hidden md:inline-flex items-center text-[11px] font-mono text-ink-3">
            <span className="text-ink-3 mr-1">Role:</span>
            <span className="font-semibold text-ink">{user.role}</span>
          </span>
        )}
      </div>
    </header>
  );
};
