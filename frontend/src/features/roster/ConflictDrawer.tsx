import React, { useState } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Calendar,
  Layers,
  User,
  ArrowRight,
  ShieldCheck,
  Check,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Drawer, Badge, Button, useToast } from '../../components/ui';
import {
  useRosterSuggestionsQuery,
  useAcknowledgeConflictMutation,
  useUpdateRosterEntriesMutation,
} from '../../api/rosters';
import type {
  RosterConflict,
  RosterSuggestionItem,
  ConflictSeverity,
} from '../../types/roster';
import { CONFLICT_CODE_INFO } from '../../types/roster';

export interface ConflictDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  periodId: string;
  conflict: RosterConflict | null;
  onApplied?: () => void;
  canAcknowledge?: boolean;
  canApply?: boolean;
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return 'N/A';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parts[0];
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ];
      return `${day} ${months[monthIdx]} ${year}`;
    }
  } catch {
    // fallback
  }
  return dateStr;
}

export const ConflictDrawer: React.FC<ConflictDrawerProps> = ({
  isOpen,
  onClose,
  periodId,
  conflict,
  onApplied,
  canAcknowledge = true,
  canApply = true,
}) => {
  const { success, error } = useToast();
  const [ackReason, setAckReason] = useState<string>('');
  const [applyingSuggestionId, setApplyingSuggestionId] = useState<string | null>(null);

  // Queries & Mutations
  const { data: suggestions, isLoading: isSuggestionsLoading } = useRosterSuggestionsQuery(
    periodId,
    conflict
      ? {
          conflict_id: conflict.id,
          brand_process_id: conflict.brand_process_id || undefined,
          date: conflict.date_from || undefined,
        }
      : undefined
  );

  const ackMutation = useAcknowledgeConflictMutation();
  const updateEntriesMutation = useUpdateRosterEntriesMutation();

  if (!conflict) return null;

  const codeInfo = CONFLICT_CODE_INFO[conflict.code] || {
    label: conflict.code,
    meaning: conflict.message,
  };

  const handleAcknowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ackReason || ackReason.trim().length < 5) {
      error('Reason Required', 'Please provide an acknowledgment justification of at least 5 characters.');
      return;
    }

    try {
      await ackMutation.mutateAsync({
        periodId,
        request: {
          conflict_id: conflict.id,
          reason: ackReason.trim(),
        },
      });
      success('Conflict Acknowledged', 'Gating requirement satisfied for draft publication.');
      setAckReason('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to acknowledge conflict';
      error('Acknowledgment Failed', msg);
    }
  };

  const handleApplySuggestion = async (suggestion: RosterSuggestionItem, idx: number) => {
    if (!canApply) return;
    const sugId = `${suggestion.type}-${idx}`;
    setApplyingSuggestionId(sugId);

    try {
      const payload = suggestion.apply_payload;
      const entriesToUpdate = payload.entries || payload.cell_edits || [];

      if (entriesToUpdate.length === 0) {
        error('Cannot Apply', 'Suggestion does not contain automated cell updates.');
        setApplyingSuggestionId(null);
        return;
      }

      await updateEntriesMutation.mutateAsync({
        periodId,
        request: {
          entries: entriesToUpdate.map((e) => ({
            employee_id: e.employee_id,
            date: e.date,
            status: e.status,
            source: 'MANUAL',
            is_locked: e.is_locked,
            reason: e.reason || suggestion.description,
          })),
        },
      });

      success('Recommendation Applied', `Applied: ${suggestion.action}`);
      onApplied?.();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to apply recommendation';
      error('Apply Failed', msg);
    } finally {
      setApplyingSuggestionId(null);
    }
  };

  const severityVariant: Record<ConflictSeverity, 'BLOCKING' | 'WARNING' | 'INFO'> = {
    BLOCKING: 'BLOCKING',
    WARNING: 'WARNING',
    INFO: 'INFO',
  };

  const severityIcon = {
    BLOCKING: <AlertCircle className="w-3.5 h-3.5 text-bad shrink-0" />,
    WARNING: <AlertTriangle className="w-3.5 h-3.5 text-warn shrink-0" />,
    INFO: <Info className="w-3.5 h-3.5 text-info shrink-0" />,
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={`${conflict.code} · ${codeInfo.label}`}
      subtitle={conflict.brand_name ? `${conflict.brand_name} · ${conflict.process_name || ''}` : 'Schedule Integrity Rule'}
      width="w-[500px]"
    >
      <div className="space-y-5 text-xs text-ink pb-6">
        {/* Status & Severity Bar */}
        <div className="flex items-center justify-between p-3 bg-surface-2 border border-border rounded-ctl">
          <div className="flex items-center gap-2">
            <Badge
              variant={severityVariant[conflict.severity]}
              icon={severityIcon[conflict.severity]}
              className="font-mono text-xs font-semibold"
            >
              {conflict.severity}
            </Badge>
            <span className="font-mono text-[11px] font-semibold text-ink-2 bg-surface px-2 py-0.5 rounded border border-border">
              {conflict.code}
            </span>
          </div>

          <div>
            {conflict.is_acknowledged ? (
              <Badge variant="SUCCESS" icon={<ShieldCheck className="w-3.5 h-3.5 text-ok" />}>
                Acknowledged
              </Badge>
            ) : conflict.severity === 'BLOCKING' ? (
              <Badge variant="BLOCKING" icon={<AlertCircle className="w-3 h-3 text-bad" />}>
                Unresolved Gate
              </Badge>
            ) : (
              <Badge variant="neutral">Active Notice</Badge>
            )}
          </div>
        </div>

        {/* Plain Language Message / Explainer */}
        <div className="p-3.5 bg-surface border border-border rounded-ctl space-y-2">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">
            Explainer & Impact
          </h4>
          <p className="text-sm font-medium text-ink leading-relaxed">
            {conflict.message}
          </p>
          <p className="text-xs text-ink-2 leading-normal">
            {codeInfo.meaning}
          </p>

          {/* Root Cause Badges */}
          {conflict.root_causes && conflict.root_causes.length > 0 && (
            <div className="pt-2 border-t border-border flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] text-ink-3 font-medium">Root Causes:</span>
              {conflict.root_causes.map((rc) => (
                <span
                  key={rc}
                  className="font-mono text-[10px] bg-surface-2 px-1.5 py-0.5 rounded border border-border text-ink-2"
                >
                  {rc}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Conflict Context Metadata */}
        <div className="border border-border rounded-ctl divide-y divide-border bg-surface">
          {/* Target Dates */}
          <div className="p-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-ink-3">
              <Calendar className="w-4 h-4 shrink-0 text-ink-3" />
              <span className="font-medium">Impacted Date(s):</span>
            </div>
            <span className="font-mono font-medium text-ink">
              {conflict.date_from === conflict.date_to || !conflict.date_to
                ? formatDate(conflict.date_from)
                : `${formatDate(conflict.date_from)} – ${formatDate(conflict.date_to)}`}
            </span>
          </div>

          {/* Brand & Process */}
          {conflict.brand_name && (
            <div className="p-2.5 flex items-center justify-between">
              <div className="flex items-center gap-2 text-ink-3">
                <Layers className="w-4 h-4 shrink-0 text-ink-3" />
                <span className="font-medium">Brand & Process:</span>
              </div>
              <span className="font-medium text-ink">
                {conflict.brand_name} · {conflict.process_name || 'All'}
              </span>
            </div>
          )}

          {/* Employee */}
          {conflict.employee_name && (
            <div className="p-2.5 flex items-center justify-between">
              <div className="flex items-center gap-2 text-ink-3">
                <User className="w-4 h-4 shrink-0 text-ink-3" />
                <span className="font-medium">Affected Employee:</span>
              </div>
              <div className="text-right">
                <span className="font-medium text-ink">{conflict.employee_name}</span>
                {conflict.employee_code && (
                  <span className="ml-1.5 font-mono text-[10px] text-ink-3">
                    ({conflict.employee_code})
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Ranked Automated Suggestions */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-accent-700" />
              <h4 className="text-xs font-semibold text-ink uppercase tracking-wider">
                Actionable Recommendations
              </h4>
            </div>
            <span className="text-[11px] text-ink-3">
              Ranked by net impact & suitability
            </span>
          </div>

          {isSuggestionsLoading ? (
            <div className="p-5 border border-border rounded-ctl bg-surface-2 flex items-center justify-center gap-2 text-ink-3">
              <Loader2 className="w-4 h-4 animate-spin text-ink-2" />
              <span>Analyzing second-order schedule impact...</span>
            </div>
          ) : !suggestions || suggestions.length === 0 ? (
            <div className="p-4 border border-dashed border-border rounded-ctl bg-surface text-center space-y-1">
              <p className="font-medium text-ink-2">No automated suggestions available</p>
              <p className="text-[11px] text-ink-3">
                Consider adjusting shift status in the Roster Grid or initiating a local repair.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {suggestions.map((sug, idx) => {
                const isTop = idx === 0;
                const isApplying = applyingSuggestionId === `${sug.type}-${idx}`;

                return (
                  <div
                    key={`${sug.type}-${idx}`}
                    className={`border rounded-card p-3 bg-surface space-y-2 transition-all ${
                      isTop
                        ? 'border-accent-600 ring-1 ring-accent-600 shadow-xs'
                        : 'border-border'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase ${
                            isTop
                              ? 'bg-accent-700 text-white'
                              : 'bg-surface-2 text-ink-2 border border-border'
                          }`}
                        >
                          #{idx + 1} {sug.kind.replace(/_/g, ' ')}
                        </span>
                        {isTop && (
                          <span className="text-[10px] font-medium text-accent-800">
                            Highest Match
                          </span>
                        )}
                      </div>

                      {/* Net Effect Badge */}
                      <span className="inline-flex items-center gap-1 font-mono text-[11px] font-medium text-ok bg-ok/10 px-2 py-0.5 rounded-full border border-ok/20 shrink-0">
                        <Check className="w-3 h-3" />
                        {sug.net_impact || `Fixes ${sug.net_effect?.fixes || 1}, opens ${sug.net_effect?.opens || 0}`}
                      </span>
                    </div>

                    <p className="text-xs font-semibold text-ink leading-snug">
                      {sug.action}
                    </p>
                    <p className="text-[11px] text-ink-2 leading-relaxed">
                      {sug.description}
                    </p>

                    {/* Candidate Details */}
                    {sug.employee_name && (
                      <div className="p-2 bg-surface-2 rounded border border-border flex items-center justify-between text-[11px]">
                        <span className="text-ink-3">Candidate Employee:</span>
                        <span className="font-medium text-ink">
                          {sug.employee_name}{' '}
                          {sug.employee_code && (
                            <span className="font-mono text-[10px] text-ink-3">
                              ({sug.employee_code})
                            </span>
                          )}
                        </span>
                      </div>
                    )}

                    {/* Apply Button */}
                    <div className="pt-1 flex justify-end">
                      <Button
                        type="button"
                        size="sm"
                        variant={isTop ? 'primary' : 'secondary'}
                        disabled={!canApply || Boolean(applyingSuggestionId)}
                        onClick={() => handleApplySuggestion(sug, idx)}
                        className="flex items-center gap-1.5 text-xs"
                      >
                        {isApplying ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Applying...</span>
                          </>
                        ) : (
                          <>
                            <span>Apply Recommendation</span>
                            <ArrowRight className="w-3 h-3" />
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Ops Manager Acknowledgment Section */}
        <div className="p-3.5 bg-surface-2 border border-border rounded-ctl space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-ink-3 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-accent-700" />
              <span>Publish Gating & Override</span>
            </h4>
            {conflict.is_acknowledged && (
              <span className="font-mono text-[10px] text-ok bg-ok/10 px-1.5 py-0.5 rounded border border-ok/20">
                Acknowledged
              </span>
            )}
          </div>

          {conflict.is_acknowledged ? (
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-1.5 text-ok font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>This conflict has been acknowledged and will not block roster publishing.</span>
              </div>
              {conflict.acknowledged_reason && (
                <div className="p-2 bg-surface rounded border border-border text-[11px]">
                  <span className="font-medium text-ink-3 block">Logged Reason:</span>
                  <p className="text-ink mt-0.5 italic">"{conflict.acknowledged_reason}"</p>
                </div>
              )}
            </div>
          ) : conflict.severity === 'BLOCKING' ? (
            <form onSubmit={handleAcknowledge} className="space-y-2.5">
              <p className="text-[11px] text-ink-2 leading-relaxed">
                As Ops Manager, you can override this BLOCKING conflict with a mandatory logged reason. This satisfies publish gating for this version.
              </p>

              <div>
                <textarea
                  id="conflict-ack-reason"
                  rows={2}
                  disabled={!canAcknowledge || ackMutation.isPending}
                  value={ackReason}
                  onChange={(e) => setAckReason(e.target.value)}
                  placeholder="Mandatory reason for override (min 5 characters, e.g. Client agreed to reduced staffing on Sunday)..."
                  className="w-full text-xs p-2 rounded border border-border bg-surface text-ink placeholder:text-ink-4 focus:outline-none focus:ring-1 focus:ring-accent-600 resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px] text-ink-3">
                  {ackReason.length < 5 ? `${5 - ackReason.length} more characters required` : '✓ Ready to acknowledge'}
                </span>

                <Button
                  type="submit"
                  variant="secondary"
                  size="sm"
                  disabled={!canAcknowledge || ackReason.trim().length < 5 || ackMutation.isPending}
                  className="flex items-center gap-1.5 text-xs"
                >
                  {ackMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                  <span>Acknowledge with Reason</span>
                </Button>
              </div>
            </form>
          ) : (
            <p className="text-[11px] text-ink-3">
              This notice is non-blocking and does not prevent roster publication.
            </p>
          )}
        </div>
      </div>
    </Drawer>
  );
};

