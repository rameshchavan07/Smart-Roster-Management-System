import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  AlertTriangle,
  Lock,
  ExternalLink,
  Loader2,
  Send,
} from 'lucide-react';
import { Button, Badge, Modal, Input, useToast } from '../../components/ui';
import {
  useRosterConflictsQuery,
  useAcknowledgeConflictMutation,
  usePublishRosterMutation,
} from '../../api/rosters';
import { showApiErrorToast } from '../../api/errorMapping';
import { useAuth } from '../auth/AuthContext';
import type { RosterPeriod, RosterConflict } from '../../types/roster';

export interface PublishConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  period: RosterPeriod | null;
  onPublished?: (publishedPeriod: RosterPeriod) => void;
}

export const PublishConfirmModal: React.FC<PublishConfirmModalProps> = ({
  isOpen,
  onClose,
  period,
  onPublished,
}) => {
  const navigate = useNavigate();
  const { isOpsManager } = useAuth();
  const toast = useToast();

  const publishMutation = usePublishRosterMutation();
  const acknowledgeMutation = useAcknowledgeConflictMutation();

  // Inline acknowledgment reason state per conflict id
  const [inlineReasons, setInlineReasons] = useState<Record<string, string>>({});
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  // Conflicts query
  const {
    data: conflicts,
    refetch: refetchConflicts,
  } = useRosterConflictsQuery(period?.id);

  if (!period) return null;

  const conflictList = conflicts || [];
  const blockingConflicts = conflictList.filter((c) => c.severity === 'BLOCKING');
  const unacknowledgedBlocking = blockingConflicts.filter((c) => !c.is_acknowledged);
  const warningCount = conflictList.filter((c) => c.severity === 'WARNING').length;

  const hasBlockingGaps = unacknowledgedBlocking.length > 0;
  const canPublish = isOpsManager && !hasBlockingGaps && !publishMutation.isPending;

  const handleQuickAcknowledge = async (conflict: RosterConflict) => {
    const reason = inlineReasons[conflict.id]?.trim() || '';
    if (reason.length < 5) {
      toast.error('Reason Required', 'Please provide a valid override reason of at least 5 characters.');
      return;
    }

    try {
      setAcknowledgingId(conflict.id);
      await acknowledgeMutation.mutateAsync({
        periodId: period.id,
        request: {
          conflict_id: conflict.id,
          reason,
        },
      });
      toast.success('Conflict Acknowledged', `Override recorded for ${conflict.code}.`);
      setInlineReasons((prev) => ({ ...prev, [conflict.id]: '' }));
      refetchConflicts();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Acknowledgment Failed');
    } finally {
      setAcknowledgingId(null);
    }
  };

  const handleConfirmPublish = async () => {
    if (!isOpsManager) {
      toast.error('Unauthorized', 'Only an Operations Manager can publish a roster.');
      return;
    }

    try {
      const res = await publishMutation.mutateAsync(period.id);
      toast.success(
        'Roster Published',
        `Version v${res.version} is now the official published roster for this month.`
      );
      if (onPublished) {
        onPublished(res);
      }
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Publish Blocked');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Publish Roster v${period.version} · Gating Review`}
      maxWidth="lg"
    >
      <div className="space-y-4 py-1">
        {/* Version Banner */}
        <div className="flex items-center justify-between p-3 rounded-ctl border border-border bg-surface-2">
          <div className="flex items-center gap-2">
            <Badge variant="WARNING" className="font-mono text-xs">
              {period.status} v{period.version}
            </Badge>
            <span className="text-xs text-ink-2 font-mono">
              Month: {period.month}
            </span>
          </div>
          <span className="text-[11px] text-ink-3">
            Solver: {period.solver_status || 'OPTIMAL'}
          </span>
        </div>

        {/* Gating Check Review Banner */}
        {hasBlockingGaps ? (
          <div className="p-3.5 rounded-ctl border border-bad/30 bg-bad/5 space-y-2">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-bad shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold text-bad">
                  Publish Gating Blocked (Rule A-13)
                </h4>
                {/* Microcopy example from UI_UX_REQUIREMENTS.md */}
                <p className="text-xs text-ink-2 mt-0.5">
                  {unacknowledgedBlocking.length}{' '}
                  {unacknowledgedBlocking.length === 1 ? 'blocking issue remains' : 'blocking issues remain'}.
                  Resolve them or acknowledge each with a reason before publishing.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3.5 rounded-ctl border border-ok/30 bg-ok/5 space-y-1">
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-ok shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-semibold text-ok">
                  Gating Checks Passed
                </h4>
                <p className="text-xs text-ink-2 mt-0.5">
                  Zero unacknowledged blocking conflicts. This roster version is ready to be published as the official operational schedule.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Blocking Conflicts List if any */}
        {hasBlockingGaps && (
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-ink uppercase tracking-wider flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-bad" />
                Unacknowledged Blocking Conflicts ({unacknowledgedBlocking.length})
              </label>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  navigate('/conflicts?severity=BLOCKING');
                }}
                className="text-[11px] text-accent-700 hover:underline inline-flex items-center gap-1 font-medium"
              >
                Open Conflict Drawer
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="border border-border rounded-ctl divide-y divide-border max-h-[220px] overflow-y-auto bg-surface">
              {unacknowledgedBlocking.map((c) => {
                const isAcking = acknowledgingId === c.id;
                const reasonValue = inlineReasons[c.id] || '';

                return (
                  <div key={c.id} className="p-3 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-xs font-semibold text-bad">
                            {c.code}
                          </span>
                          <span className="text-[11px] text-ink-3">·</span>
                          <span className="text-xs font-medium text-ink">
                            {c.brand_name ? `${c.brand_name} · ${c.process_name || ''}` : 'Operational Gap'}
                          </span>
                        </div>
                        <p className="text-[11px] text-ink-2 leading-relaxed">
                          {c.message}
                        </p>
                        <p className="text-[10px] text-ink-3 font-mono">
                          Dates: {c.date_from} {c.date_to !== c.date_from ? `to ${c.date_to}` : ''}
                          {c.employee_name ? ` · Emp: ${c.employee_name}` : ''}
                        </p>
                      </div>
                    </div>

                    {/* Inline Acknowledgment Input for Ops Manager */}
                    {isOpsManager && (
                      <div className="pt-1 flex items-center gap-2">
                        <Input
                          placeholder="Override reason (e.g., 'Approved temporary solo coverage by lead')..."
                          value={reasonValue}
                          onChange={(e) =>
                            setInlineReasons((prev) => ({
                              ...prev,
                              [c.id]: e.target.value,
                            }))
                          }
                          className="h-7 text-xs flex-1"
                        />
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={reasonValue.trim().length < 5 || isAcking}
                          onClick={() => handleQuickAcknowledge(c)}
                          className="h-7 text-xs shrink-0"
                        >
                          {isAcking ? (
                            <Loader2 className="w-3 h-3 animate-spin mr-1" />
                          ) : (
                            <Send className="w-3 h-3 mr-1" />
                          )}
                          Acknowledge
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Warning Review Note */}
        {warningCount > 0 && (
          <div className="flex items-center gap-2 text-xs text-ink-2 bg-surface-2 p-2.5 rounded-ctl border border-border">
            <AlertTriangle className="w-4 h-4 text-warn shrink-0" />
            <span>
              <strong className="text-ink font-semibold">{warningCount} warnings</strong> exist in this roster
              (e.g., preference or weekend spacing guidelines). Warnings do not block publishing.
            </span>
          </div>
        )}

        {/* Important operational notes on publishing */}
        <div className="p-3 bg-surface-2 border border-border rounded-ctl space-y-1.5 text-[11px] text-ink-2">
          <p className="font-semibold text-ink flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-ink-3" />
            Publishing Impacts
          </p>
          <ul className="list-disc list-inside space-y-0.5 text-ink-3">
            <li>Any existing published version for this month will be archived.</li>
            <li>All holiday work shifts (`HW`) will accrue 1 comp-off credit per employee.</li>
            <li>Pod leads and employees will see this version as their active schedule.</li>
          </ul>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>

          <Button
            variant="primary"
            size="sm"
            disabled={!canPublish}
            onClick={handleConfirmPublish}
            className={hasBlockingGaps ? 'opacity-50 cursor-not-allowed' : ''}
            title={
              hasBlockingGaps
                ? 'Resolve or acknowledge all blocking conflicts first'
                : 'Publish official roster'
            }
          >
            {publishMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                Publishing...
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
                Publish Official Roster
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
