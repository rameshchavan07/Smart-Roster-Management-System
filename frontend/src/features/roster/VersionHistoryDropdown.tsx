import React, { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  Check,
  Copy,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { Badge, Button, useToast } from '../../components/ui';
import { useCloneRosterMutation } from '../../api/rosters';
import { showApiErrorToast } from '../../api/errorMapping';
import { useAuth } from '../auth/AuthContext';
import type { RosterPeriod } from '../../types/roster';

export interface VersionHistoryDropdownProps {
  periods: RosterPeriod[];
  activePeriod: RosterPeriod | null;
  onSelectPeriod: (period: RosterPeriod) => void;
  onPeriodCloned?: (newPeriod: RosterPeriod) => void;
  onCompareVersions?: (baseId: string, compId: string) => void;
}

export const VersionHistoryDropdown: React.FC<VersionHistoryDropdownProps> = ({
  periods,
  activePeriod,
  onSelectPeriod,
  onPeriodCloned,
  onCompareVersions,
}) => {
  const { isOpsManager, isPodLead } = useAuth();
  const toast = useToast();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const cloneMutation = useCloneRosterMutation();

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleCloneVersion = async (targetPeriod: RosterPeriod) => {
    try {
      const res = await cloneMutation.mutateAsync({
        periodId: targetPeriod.id,
        request: {
          parent_period_id: targetPeriod.id,
          note: `Cloned from v${targetPeriod.version}`,
        },
      });
      toast.success(
        'New Draft Created',
        `Version v${res.version} cloned from v${targetPeriod.version} as an editable draft.`
      );
      setIsOpen(false);
      if (onPeriodCloned) {
        onPeriodCloned(res);
      }
      onSelectPeriod(res);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to clone roster version');
    }
  };

  if (!activePeriod && periods.length === 0) {
    return (
      <Badge variant="neutral" className="text-xs font-mono">
        No Versions
      </Badge>
    );
  }

  const currentPeriod = activePeriod || periods[0];

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-ctl border border-border bg-surface hover:bg-surface-2 transition-colors text-xs font-mono shadow-xs focus:outline-none focus:ring-1 focus:ring-accent-500"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span
          className={`w-2 h-2 rounded-full ${
            currentPeriod.status === 'PUBLISHED'
              ? 'bg-ok'
              : currentPeriod.status === 'DRAFT'
              ? 'bg-warn'
              : 'bg-ink-3'
          }`}
        />
        <span className="font-semibold text-ink">v{currentPeriod.version}</span>
        <span className="text-[11px] text-ink-3 uppercase">· {currentPeriod.status}</span>
        {currentPeriod.is_stale && (
          <span
            title="Stale roster: Inputs changed since generation"
            className="flex items-center text-warn"
          >
            <AlertTriangle className="w-3 h-3 ml-0.5" />
          </span>
        )}
        <ChevronDown className="w-3 h-3 text-ink-3 ml-0.5" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-1 w-72 rounded-ctl bg-surface border border-border shadow-md z-50 divide-y divide-border py-1 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-2 bg-surface-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">
                Version History
              </span>
              <span className="font-mono text-[10px] text-ink-3">
                {periods.length} {periods.length === 1 ? 'version' : 'versions'}
              </span>
            </div>
            <p className="text-[10px] text-ink-3 mt-0.5">
              Select a version to inspect or clone for editing.
            </p>
          </div>

          {/* Versions list */}
          <div className="max-h-56 overflow-y-auto py-1">
            {periods.map((p) => {
              const isSelected = p.id === currentPeriod.id;
              const formattedDate = new Date(p.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <div
                  key={p.id}
                  className={`px-3 py-2 flex items-center justify-between gap-2 hover:bg-surface-2 cursor-pointer transition-colors ${
                    isSelected ? 'bg-accent-50/40 text-accent-950 font-medium' : 'text-ink'
                  }`}
                  onClick={() => {
                    onSelectPeriod(p);
                    setIsOpen(false);
                  }}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isSelected ? (
                      <Check className="w-3.5 h-3.5 text-accent-700 shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 shrink-0" />
                    )}

                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-semibold text-ink">
                          v{p.version}
                        </span>
                        <Badge
                          variant={
                            p.status === 'PUBLISHED'
                              ? 'SUCCESS'
                              : p.status === 'DRAFT'
                              ? 'WARNING'
                              : 'neutral'
                          }
                          className="text-[9px] px-1 py-0"
                        >
                          {p.status}
                        </Badge>
                        {p.is_stale && (
                          <span
                            title="Stale"
                            className="text-[9px] font-medium text-warn bg-warn/10 px-1 rounded"
                          >
                            stale
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-ink-3 font-mono mt-0.5">
                        {formattedDate} {p.solver_status ? `· ${p.solver_status}` : ''}
                      </p>
                    </div>
                  </div>

                  {/* Actions for this item */}
                  <div className="flex items-center gap-1">
                    {(isOpsManager || isPodLead) && (
                      <button
                        type="button"
                        title={`Clone v${p.version} as new draft`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCloneVersion(p);
                        }}
                        className="p-1 rounded text-ink-3 hover:text-ink hover:bg-surface-3 transition-colors"
                      >
                        {cloneMutation.isPending ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Actions Footer */}
          <div className="p-2 bg-surface-2 flex items-center justify-between gap-2">
            {periods.length >= 2 && onCompareVersions && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setIsOpen(false);
                  onCompareVersions(periods[1].id, periods[0].id);
                }}
                className="text-xs h-7 shrink-0"
              >
                Compare
              </Button>
            )}

            {(isOpsManager || isPodLead) && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleCloneVersion(currentPeriod)}
                disabled={cloneMutation.isPending}
                className="w-full text-xs h-7 justify-center"
              >
                {cloneMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                ) : (
                  <Copy className="w-3 h-3 mr-1" />
                )}
                Clone as v{Math.max(...periods.map((p) => p.version), 1) + 1} Draft
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
