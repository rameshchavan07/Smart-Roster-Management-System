import React, { useState, useEffect, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Lock, Unlock, X, AlertTriangle, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { Button, Input } from '../../components/ui';
import { StatusCell, type RosterStatusCode } from '../../components/ui/StatusCell';
import { useRosterImpactMutation } from '../../api/rosters';
import type {
  RosterEntryStatus,
  RosterGridRow,
  RosterGridCell,
  RosterImpactConflictItem,
} from '../../types/roster';
import { mapStatusToCode } from '../../types/roster';

export interface CellEditPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  periodId: string;
  row: RosterGridRow;
  date: string; // ISO date 'YYYY-MM-DD'
  cell: RosterGridCell;
  anchorRect: DOMRect | null;
  onApply: (params: {
    status: RosterEntryStatus;
    isLocked: boolean;
    note: string;
  }) => Promise<void> | void;
  isSaving?: boolean;
  readOnly?: boolean;
}

interface StatusOption {
  status: RosterEntryStatus;
  code: RosterStatusCode;
  label: string;
  description: string;
}

const STATUS_OPTIONS: StatusOption[] = [
  { status: 'WORK', code: 'W', label: 'Working', description: 'Regular shift assignment' },
  { status: 'WEEKLY_OFF', code: 'WO', label: 'Weekly off', description: 'Scheduled rest day' },
  { status: 'LEAVE', code: 'L', label: 'Leave', description: 'Planned approved absence' },
  { status: 'COMP_OFF', code: 'CO', label: 'Comp-off', description: 'Redeemed comp-off credit' },
  { status: 'PUBLIC_HOLIDAY', code: 'PH', label: 'Public holiday', description: 'Paid company holiday off' },
  { status: 'HOLIDAY_WORK', code: 'HW', label: 'Holiday work', description: 'Working on holiday (+1 CO)' },
];

/**
 * Format ISO date string into human friendly format like "14 Dec" or "14 Dec 2026"
 */
function formatShortDate(dateStr: string): string {
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parts[0];
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
      ];
      return `${day} ${months[monthIdx]} ${year}`;
    }
  } catch {
    // fallback
  }
  return dateStr;
}

function formatDayMonth(dateStr: string): string {
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
      ];
      return `${day} ${months[monthIdx]}`;
    }
  } catch {
    // fallback
  }
  return dateStr;
}

/**
 * Generate human readable inline impact summary line according to spec:
 * e.g., "Opens 1 gap: Aurora CS 14 Dec"
 */
function summarizeNewConflicts(
  conflicts: RosterImpactConflictItem[],
  fallbackDate: string
): string {
  if (conflicts.length === 0) return '';
  const first = conflicts[0];
  const dateFormatted = formatDayMonth(first.date || first.date_from || fallbackDate);
  const brandProcess = [first.brand, first.process].filter(Boolean).join(' · ');

  const gapTarget = brandProcess ? `${brandProcess} ${dateFormatted}` : dateFormatted;

  if (conflicts.length === 1) {
    return `Opens 1 gap: ${gapTarget}`;
  }
  return `Opens ${conflicts.length} gaps: ${gapTarget} (+${conflicts.length - 1} more)`;
}

export const CellEditPopover: React.FC<CellEditPopoverProps> = ({
  isOpen,
  onClose,
  periodId,
  row,
  date,
  cell,
  anchorRect,
  onApply,
  isSaving = false,
  readOnly = false,
}) => {
  const popoverRef = useRef<HTMLDivElement>(null);

  // Form states
  const [selectedStatus, setSelectedStatus] = useState<RosterEntryStatus>(cell.status);
  const [isLocked, setIsLocked] = useState<boolean>(cell.is_locked);
  const [note, setNote] = useState<string>(cell.note || '');

  // Live simulation mutation
  const impactMutation = useRosterImpactMutation();

  // Reset form when cell changes or popover opens
  useEffect(() => {
    if (isOpen) {
      setSelectedStatus(cell.status);
      setIsLocked(cell.is_locked);
      setNote(cell.note || '');
    }
  }, [isOpen, cell]);

  // Live impact trigger on status change
  useEffect(() => {
    if (!isOpen || !periodId) return;

    // If same status, no need to query impact unless needed
    if (selectedStatus === cell.status) {
      impactMutation.reset();
      return;
    }

    const timer = setTimeout(() => {
      impactMutation.mutate({
        periodId,
        request: {
          changes: [
            {
              type: 'CELL_EDIT',
              employee_id: row.employee_id,
              date,
              status: selectedStatus,
            },
          ],
        },
      });
    }, 120);

    return () => clearTimeout(timer);
  }, [isOpen, periodId, selectedStatus, cell.status, row.employee_id, date]);

  // Keyboard navigation & click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Calculate anchored portal positioning
  const popoverStyle = useMemo(() => {
    if (!anchorRect) {
      return {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      };
    }

    const popoverWidth = 330;
    const estimatedHeight = 440;
    const padding = 12;

    // Center horizontally on anchor cell, clamped to viewport
    let left = anchorRect.left + anchorRect.width / 2 - popoverWidth / 2;
    left = Math.max(padding, Math.min(left, window.innerWidth - popoverWidth - padding));

    // Place below if space permits, otherwise above
    const spaceBelow = window.innerHeight - anchorRect.bottom;
    const spaceAbove = anchorRect.top;

    let top: number;
    if (spaceBelow >= estimatedHeight || spaceBelow >= spaceAbove) {
      top = anchorRect.bottom + 6;
    } else {
      top = Math.max(padding, anchorRect.top - estimatedHeight - 6);
    }

    return {
      top: `${top}px`,
      left: `${left}px`,
      width: `${popoverWidth}px`,
    };
  }, [anchorRect]);

  if (!isOpen) return null;

  const hasStatusChanged = selectedStatus !== cell.status;
  const hasLockChanged = isLocked !== cell.is_locked;
  const hasNoteChanged = (note || '') !== (cell.note || '');
  const hasChanges = hasStatusChanged || hasLockChanged || hasNoteChanged;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (readOnly || isSaving) return;
    await onApply({
      status: selectedStatus,
      isLocked,
      note: note.trim(),
    });
  };

  const formattedDate = formatShortDate(date);
  const currentStatusCode = mapStatusToCode(cell.status);
  const selectedStatusCode = mapStatusToCode(selectedStatus);

  // Live impact evaluation results
  const isSimulating = impactMutation.isPending;
  const impactData = impactMutation.data;
  const newConflicts = impactData?.new_conflicts || [];
  const resolvedConflicts = impactData?.resolved_conflicts || [];

  return createPortal(
    <div className="fixed inset-0 z-[120] pointer-events-none">
      {/* Dim backdrop on mobile / compact screens */}
      <div className="fixed inset-0 bg-black/10 pointer-events-auto md:bg-transparent" onClick={onClose} />

      <div
        ref={popoverRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Edit cell for ${row.employee_name} on ${formattedDate}`}
        style={popoverStyle}
        onClick={(e) => e.stopPropagation()}
        className="pointer-events-auto absolute bg-surface border border-border rounded-pop shadow-layer flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150 focus:outline-none"
      >
        {/* Popover Header */}
        <div className="px-3.5 py-2.5 bg-surface-2 border-b border-border flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-text-primary truncate">
                {row.employee_name}
              </span>
              <span className="font-mono text-[10px] text-text-muted bg-surface px-1 py-0.5 rounded border border-border flex-shrink-0">
                {row.employee_code}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-text-secondary mt-0.5">
              <span>{row.pod_name || 'No Pod'}</span>
              <span>•</span>
              <span className="font-medium text-text-primary">{formattedDate}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close popover"
            className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-surface border border-transparent hover:border-border transition-colors -mr-1"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Popover Form Body */}
        <form onSubmit={handleSubmit} className="p-3.5 space-y-3.5 overflow-y-auto">
          {/* Status Picker */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                Shift Status
              </label>
              <div className="flex items-center gap-1 text-[11px] text-text-muted">
                <span>Current:</span>
                <span className="font-mono font-medium text-text-primary">
                  {currentStatusCode}
                </span>
                {hasStatusChanged && (
                  <>
                    <ArrowRight className="w-3 h-3 text-text-muted" />
                    <span className="font-mono font-bold text-accent-700">
                      {selectedStatusCode}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-label="Shift status options">
              {STATUS_OPTIONS.map((opt) => {
                const isSelected = selectedStatus === opt.status;
                return (
                  <button
                    key={opt.status}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    disabled={readOnly}
                    onClick={() => setSelectedStatus(opt.status)}
                    className={`flex items-center gap-2 p-1.5 rounded-card border text-left transition-all ${
                      isSelected
                        ? 'border-accent-600 bg-accent-50/50 shadow-xs ring-1 ring-accent-600'
                        : 'border-border bg-surface hover:bg-surface-2'
                    } ${readOnly ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <StatusCell
                      status={opt.code}
                      size="sm"
                      tabIndex={-1}
                      className="pointer-events-none flex-shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-xs text-text-primary leading-tight truncate">
                        {opt.label}
                      </div>
                      <div className="text-[10px] text-text-muted truncate leading-tight">
                        {opt.description}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Live Impact Line Container */}
          <div className="border border-border rounded-card p-2 bg-surface-2/60">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-1 flex items-center justify-between">
              <span>Coverage Impact</span>
              {isSimulating && (
                <span className="flex items-center gap-1 text-accent-700 text-[10px] font-normal lowercase">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  evaluating...
                </span>
              )}
            </div>

            {!hasStatusChanged ? (
              <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                <span className="w-1.5 h-1.5 rounded-full bg-border-dark" />
                <span>Current status · No impact on coverage</span>
              </div>
            ) : isSimulating ? (
              <div className="flex items-center gap-2 text-xs text-text-muted py-0.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-text-secondary" />
                <span>Simulating schedule impact...</span>
              </div>
            ) : newConflicts.length > 0 ? (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-medium text-[#C2412D]">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{summarizeNewConflicts(newConflicts, date)}</span>
                </div>
                {newConflicts[0].message && (
                  <p className="text-[10px] text-text-muted pl-5 truncate" title={newConflicts[0].message}>
                    {newConflicts[0].message}
                  </p>
                )}
              </div>
            ) : resolvedConflicts.length > 0 ? (
              <div className="flex items-center gap-1.5 text-xs font-medium text-[#2E7D5B]">
                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  Resolves {resolvedConflicts.length} gap{resolvedConflicts.length > 1 ? 's' : ''} on {formatDayMonth(date)}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-medium text-[#2E7D5B]">
                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                <span>Preserves coverage (0 new gaps)</span>
              </div>
            )}
          </div>

          {/* Lock Cell Checkbox */}
          <div className="flex items-start gap-2 pt-0.5">
            <input
              id="popover-cell-lock"
              type="checkbox"
              disabled={readOnly}
              checked={isLocked}
              onChange={(e) => setIsLocked(e.target.checked)}
              className="mt-0.5 h-3.5 w-3.5 rounded border-border text-accent-600 focus:ring-accent-500 cursor-pointer"
            />
            <label htmlFor="popover-cell-lock" className="text-xs text-text-primary cursor-pointer select-none">
              <span className="font-medium flex items-center gap-1">
                {isLocked ? (
                  <>
                    <Lock className="w-3 h-3 text-[#B7791F]" />
                    <span>Locked cell</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-3 h-3 text-text-muted" />
                    <span>Lock cell</span>
                  </>
                )}
              </span>
              <span className="block text-[10px] text-text-muted">
                Freezes cell from automatic re-solve and solver repair.
              </span>
            </label>
          </div>

          {/* Audit Note / Reason */}
          <div>
            <label htmlFor="popover-cell-note" className="block text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-1">
              Audit Note / Reason
            </label>
            <Input
              id="popover-cell-note"
              type="text"
              disabled={readOnly}
              placeholder="e.g. Swapped shift with Bob, doctor appt"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="h-8 text-xs font-normal"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={readOnly || !hasChanges || isSaving}
              className="flex items-center gap-1.5"
            >
              {isSaving && <Loader2 className="w-3 h-3 animate-spin" />}
              <span>{isSaving ? 'Applying...' : 'Apply'}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};
