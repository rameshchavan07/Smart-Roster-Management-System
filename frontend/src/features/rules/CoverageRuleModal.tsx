import React, { useState, useMemo } from 'react';
import { Modal, Button, Input, Select, Combobox, useToast } from '../../components/ui';
import { useCreateCoverageRuleMutation } from '../../api/rules';
import { useBrandProcessesQuery } from '../../api/brands';
import type { CoverageRuleCreateInput } from '../../types/rules';

export interface CoverageRuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultBrandProcessId?: string;
}

const WEEKDAYS = [
  { value: '0', label: 'Monday' },
  { value: '1', label: 'Tuesday' },
  { value: '2', label: 'Wednesday' },
  { value: '3', label: 'Thursday' },
  { value: '4', label: 'Friday' },
  { value: '5', label: 'Saturday' },
  { value: '6', label: 'Sunday' },
];

export const CoverageRuleModal: React.FC<CoverageRuleModalProps> = ({
  isOpen,
  onClose,
  defaultBrandProcessId,
}) => {
  const toast = useToast();
  const { data: bpData } = useBrandProcessesQuery({ limit: 100 });
  const createMutation = useCreateCoverageRuleMutation();

  const [brandProcessId, setBrandProcessId] = useState(defaultBrandProcessId || '');
  const [ruleType, setRuleType] = useState<'weekday' | 'date'>('weekday');
  const [weekday, setWeekday] = useState('0');
  const [specificDate, setSpecificDate] = useState('2026-12-25');
  const [minStaff, setMinStaff] = useState(2);
  const [reason, setReason] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const bpOptions = useMemo(() => {
    return (bpData?.items || []).map((bp) => ({
      value: bp.id,
      label: `${bp.brand_name || 'Brand'} — ${bp.process_name || 'Process'}`,
      subtitle: `Code: ${bp.brand_code || ''} · Default Min: ${bp.min_coverage_default}`,
    }));
  }, [bpData]);

  const selectedBP = useMemo(() => {
    const id = brandProcessId || (bpData?.items?.[0]?.id ?? '');
    return bpData?.items?.find((bp) => bp.id === id);
  }, [bpData, brandProcessId]);

  // Explanatory preview text per S9
  const previewText = useMemo(() => {
    const bpLabel = selectedBP
      ? `${selectedBP.brand_name} ${selectedBP.process_name}`
      : 'selected process';
    const staffLabel = `Min ${minStaff} staff`;
    const scheduleLabel =
      ruleType === 'weekday'
        ? `on ${WEEKDAYS.find((w) => w.value === weekday)?.label}s`
        : `on ${specificDate}`;
    const reasonLabel = reason.trim() ? ` ("${reason.trim()}")` : '';
    return `${staffLabel} required ${scheduleLabel} across ${bpLabel}${reasonLabel}.`;
  }, [selectedBP, minStaff, ruleType, weekday, specificDate, reason]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetBPId = brandProcessId || (bpData?.items?.[0]?.id ?? '');

    if (!targetBPId) {
      setErrorMsg('Please select a brand-process capability.');
      return;
    }

    const payload: CoverageRuleCreateInput = {
      brand_process_id: targetBPId,
      min_staff: minStaff,
      reason: reason.trim() || null,
      weekday: ruleType === 'weekday' ? parseInt(weekday, 10) : null,
      specific_date: ruleType === 'date' ? specificDate : null,
    };

    try {
      await createMutation.mutateAsync(payload);
      toast.success(
        'Coverage rule created',
        `Override rule applied: ${previewText}`
      );
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create rule';
      setErrorMsg(msg);
      toast.error('Operation failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Coverage Rule"
      description="Configure minimum staffing overrides for specific weekdays or target calendar dates."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="coverage-rule-form"
            isLoading={createMutation.isPending}
          >
            Create Rule
          </Button>
        </div>
      }
    >
      <form id="coverage-rule-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Combobox
          label="Brand-Process Capability"
          value={brandProcessId || (bpData?.items?.[0]?.id ?? '')}
          options={bpOptions}
          onChange={setBrandProcessId}
          placeholder="Select brand capability..."
        />

        {/* Rule Type Selector */}
        <div className="space-y-1">
          <label className="block text-xs font-medium text-ink-2">Rule Frequency</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setRuleType('weekday')}
              className={`rounded-ctl border p-2 text-xs font-medium text-center transition-colors ${
                ruleType === 'weekday'
                  ? 'border-accent-600 bg-accent-50 text-accent-700'
                  : 'border-border bg-surface text-ink-2 hover:bg-surface-2'
              }`}
            >
              Recurring Weekday
            </button>
            <button
              type="button"
              onClick={() => setRuleType('date')}
              className={`rounded-ctl border p-2 text-xs font-medium text-center transition-colors ${
                ruleType === 'date'
                  ? 'border-accent-600 bg-accent-50 text-accent-700'
                  : 'border-border bg-surface text-ink-2 hover:bg-surface-2'
              }`}
            >
              Specific Date Override
            </button>
          </div>
        </div>

        {ruleType === 'weekday' ? (
          <Select
            label="Day of Week"
            value={weekday}
            options={WEEKDAYS}
            onChange={setWeekday}
          />
        ) : (
          <Input
            label="Target Date"
            type="date"
            value={specificDate}
            onChange={(e) => setSpecificDate(e.target.value)}
            required
          />
        )}

        <Input
          label="Required Staff Headcount (Min Staff)"
          type="number"
          min={1}
          max={50}
          value={minStaff}
          onChange={(e) => setMinStaff(parseInt(e.target.value, 10))}
          required
        />

        <Input
          label="Operational Reason / Context (Optional)"
          placeholder="e.g. Weekend surge, Festive campaign, Peak demand"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />

        {/* Explanatory Live Preview Box per S9 */}
        <div className="rounded-ctl border border-accent-100 bg-accent-50/70 p-3 text-xs text-accent-700 space-y-1">
          <p className="font-semibold text-[11px] uppercase tracking-wider text-accent-700">
            Explanatory Rule Preview
          </p>
          <p className="font-medium">{previewText}</p>
        </div>
      </form>
    </Modal>
  );
};
