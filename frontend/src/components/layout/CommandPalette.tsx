import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Calendar,
  AlertTriangle,
  Clock,
  Users,
  Briefcase,
  FileText,
  Sliders,
  Palette,
  LayoutDashboard,
  LogOut,
  Sparkles,
  Download,
  CalendarDays,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext';
import { useMonth } from '../../context/MonthContext';

export interface CommandItem {
  id: string;
  title: string;
  category: 'Navigation' | 'Planning Month' | 'Quick Actions' | 'Account';
  subtitle?: string;
  icon: React.ReactNode;
  shortcut?: string;
  action: () => void;
  roles?: Array<'OPS_MANAGER' | 'POD_LEAD' | 'EMPLOYEE'>;
}

export const CommandPalette: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { user, logout, isEmployee } = useAuth();
  const { setMonth, currentMonth } = useMonth();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  const commands = useMemo<CommandItem[]>(() => {
    const list: CommandItem[] = [
      // Navigation
      {
        id: 'nav-dashboard',
        title: 'Dashboard',
        subtitle: 'Monthly overview and operational health metrics',
        category: 'Navigation',
        icon: <LayoutDashboard className="h-4 w-4" />,
        shortcut: 'G D',
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/');
          onClose();
        },
      },
      {
        id: 'nav-roster',
        title: isEmployee ? 'My Roster' : 'Roster Workspace',
        subtitle: 'Company, Pod, Brand, Process and Employee views',
        category: 'Navigation',
        icon: <Calendar className="h-4 w-4" />,
        shortcut: 'G R',
        action: () => {
          navigate('/roster');
          onClose();
        },
      },
      {
        id: 'nav-conflicts',
        title: 'Validation Conflicts',
        subtitle: 'Review blocking issues, warnings and root causes',
        category: 'Navigation',
        icon: <AlertTriangle className="h-4 w-4 text-warn" />,
        shortcut: 'G C',
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/conflicts');
          onClose();
        },
      },
      {
        id: 'nav-leaves',
        title: 'Leaves & Comp-offs',
        subtitle: 'Track leave requests, balances and comp-off accruals',
        category: 'Navigation',
        icon: <Clock className="h-4 w-4" />,
        shortcut: 'G L',
        action: () => {
          navigate('/leaves');
          onClose();
        },
      },
      {
        id: 'nav-team',
        title: 'Team & Pods',
        subtitle: 'Employee directory, pods and staffing parameters',
        category: 'Navigation',
        icon: <Users className="h-4 w-4" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/team');
          onClose();
        },
      },
      {
        id: 'nav-brands',
        title: 'Brands & Processes',
        subtitle: 'Operating calendars, coverage demand and assignments',
        category: 'Navigation',
        icon: <Briefcase className="h-4 w-4" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/brands');
          onClose();
        },
      },
      {
        id: 'nav-rules',
        title: 'Rules & Holidays',
        subtitle: 'Staffing coverage rules and public holiday calendar',
        category: 'Navigation',
        icon: <CalendarDays className="h-4 w-4" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/rules');
          onClose();
        },
      },
      {
        id: 'nav-reports',
        title: 'Reports & Export',
        subtitle: 'Download multi-view CSV and Excel spreadsheets',
        category: 'Navigation',
        icon: <FileText className="h-4 w-4" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/reports');
          onClose();
        },
      },
      {
        id: 'nav-settings',
        title: 'Settings & Audit Log',
        subtitle: 'System configuration, solver weights and activity audit trail',
        category: 'Navigation',
        icon: <Sliders className="h-4 w-4" />,
        roles: ['OPS_MANAGER'],
        action: () => {
          navigate('/settings');
          onClose();
        },
      },
      {
        id: 'nav-design-system',
        title: 'Design System Reference',
        subtitle: 'View visual tokens, components and WCAG color scales',
        category: 'Navigation',
        icon: <Palette className="h-4 w-4 text-accent-600" />,
        action: () => {
          navigate('/design-system');
          onClose();
        },
      },

      // Planning Month quick switches
      {
        id: 'month-dec-2026',
        title: 'Switch Month: December 2026 (Target)',
        subtitle: 'Go to primary demonstration planning month',
        category: 'Planning Month',
        icon: <CalendarDays className="h-4 w-4 text-accent-600" />,
        action: () => {
          setMonth('2026-12');
          onClose();
        },
      },
      {
        id: 'month-nov-2026',
        title: 'Switch Month: November 2026',
        subtitle: 'Preceding month horizon',
        category: 'Planning Month',
        icon: <CalendarDays className="h-4 w-4" />,
        action: () => {
          setMonth('2026-11');
          onClose();
        },
      },
      {
        id: 'month-jan-2027',
        title: 'Switch Month: January 2027',
        subtitle: 'Next month horizon',
        category: 'Planning Month',
        icon: <CalendarDays className="h-4 w-4" />,
        action: () => {
          setMonth('2027-01');
          onClose();
        },
      },

      // Quick Actions
      {
        id: 'action-generate',
        title: 'Generate Monthly Roster',
        subtitle: 'Run CP-SAT solver for the selected planning month',
        category: 'Quick Actions',
        icon: <Sparkles className="h-4 w-4 text-accent-600" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/roster');
          onClose();
        },
      },
      {
        id: 'action-export',
        title: 'Export Roster Data',
        subtitle: 'Download grid or summary as CSV / XLSX',
        category: 'Quick Actions',
        icon: <Download className="h-4 w-4" />,
        roles: ['OPS_MANAGER', 'POD_LEAD'],
        action: () => {
          navigate('/reports');
          onClose();
        },
      },

      // Account
      {
        id: 'account-logout',
        title: 'Sign Out',
        subtitle: user ? `Currently signed in as ${user.email}` : undefined,
        category: 'Account',
        icon: <LogOut className="h-4 w-4 text-bad" />,
        action: () => {
          onClose();
          logout();
        },
      },
    ];

    // Filter by user role
    return list.filter((item) => {
      if (!item.roles || !user) return true;
      return item.roles.includes(user.role);
    });
  }, [navigate, onClose, user, isEmployee, setMonth, logout]);

  // Filter commands by query string
  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;
    const lower = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(lower) ||
        cmd.category.toLowerCase().includes(lower) ||
        (cmd.subtitle && cmd.subtitle.toLowerCase().includes(lower))
    );
  }, [commands, query]);

  // Ensure selected index stays in bounds
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard navigation within palette
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < filteredCommands.length - 1 ? prev + 1 : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredCommands.length - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    },
    [filteredCommands, selectedIndex, onClose]
  );

  // Scroll active item into view
  useEffect(() => {
    if (listRef.current) {
      const activeEl = listRef.current.querySelector<HTMLElement>('[data-active="true"]');
      if (activeEl) {
        activeEl.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-ink/30 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-pop border border-border bg-surface shadow-layer animate-in fade-in zoom-in-95 duration-100"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-3 bg-surface">
          <Search className="h-4 w-4 text-ink-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or jump to screen..."
            className="flex-1 bg-transparent text-sm text-ink placeholder-ink-3 outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center rounded-ctl border border-border bg-surface-2 px-1.5 py-0.5 text-[10px] font-mono text-ink-3">
            Esc
          </kbd>
        </div>

        {/* Command list */}
        <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-8 text-center text-xs text-ink-3">
              No matching commands found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            <div className="space-y-1">
              {filteredCommands.map((cmd, idx) => {
                const isSelected = idx === selectedIndex;
                const isFirstOfCategory =
                  idx === 0 || filteredCommands[idx - 1].category !== cmd.category;

                return (
                  <React.Fragment key={cmd.id}>
                    {isFirstOfCategory && (
                      <div className="px-2.5 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-ink-3">
                        {cmd.category}
                      </div>
                    )}
                    <button
                      type="button"
                      data-active={isSelected}
                      onClick={cmd.action}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex w-full items-center justify-between rounded-ctl px-3 py-2 text-left transition-colors ${
                        isSelected
                          ? 'bg-accent-50 text-accent-700 font-medium'
                          : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 overflow-hidden">
                        <div
                          className={`shrink-0 ${
                            isSelected ? 'text-accent-600' : 'text-ink-3'
                          }`}
                        >
                          {cmd.icon}
                        </div>
                        <div className="truncate">
                          <p className="text-xs text-ink font-medium truncate">{cmd.title}</p>
                          {cmd.subtitle && (
                            <p className="text-[11px] text-ink-3 truncate leading-tight">
                              {cmd.subtitle}
                            </p>
                          )}
                        </div>
                      </div>

                      {cmd.shortcut && (
                        <kbd className="ml-2 shrink-0 rounded-ctl border border-border bg-surface-2 px-1.5 py-0.5 text-[10px] font-mono text-ink-3">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  </React.Fragment>
                );
              })}
            </div>
          )}
        </div>

        {/* Palette footer with tips */}
        <div className="flex items-center justify-between border-t border-border bg-surface-2 px-3 py-2 text-[11px] text-ink-3">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="rounded-ctl border border-border bg-surface px-1 py-0.5 text-[9px] font-mono">
                ↑↓
              </kbd>{' '}
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded-ctl border border-border bg-surface px-1 py-0.5 text-[9px] font-mono">
                ↵
              </kbd>{' '}
              Select
            </span>
          </div>
          <span className="font-mono text-[10px]">Active Month: {currentMonth}</span>
        </div>
      </div>
    </div>
  );
};

