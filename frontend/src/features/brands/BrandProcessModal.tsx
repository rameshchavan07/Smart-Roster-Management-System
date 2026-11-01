import React, { useState } from 'react';
import { Modal, Button, Input, Select, useToast } from '../../components/ui';
import { useCreateBrandProcessMutation, useProcessesQuery } from '../../api/brands';
import type { CalendarType } from '../../types/brands';

export interface BrandProcessModalProps {
  isOpen: boolean;
  onClose: () => void;
  brandId: string;
  brandName?: string;
}

const CALENDAR_OPTIONS: Array<{ value: CalendarType; label: string }> = [
  { value: 'ALL_365', label: '365 Days / All Week (Mon–Sun)' },
  { value: 'SIX_DAYS_MON_SAT', label: '6 Days (Mon–Sat, Sun Closed)' },
  { value: 'SIX_DAYS_TUE_SUN', label: '6 Days (Tue–Sun, Mon Closed)' },
  { value: 'FIVE_DAYS_MON_FRI', label: '5 Days (Mon–Fri, Weekend Closed)' },
  { value: 'FOUR_DAYS_CUSTOM', label: '4 Days Custom' },
  { value: 'SEASONAL_CUSTOM', label: 'Seasonal Custom' },
];

export const BrandProcessModal: React.FC<BrandProcessModalProps> = ({
  isOpen,
  onClose,
  brandId,
  brandName,
}) => {
  const toast = useToast();
  const { data: processesData } = useProcessesQuery();
  const createMutation = useCreateBrandProcessMutation();

  const [processId, setProcessId] = useState('');
  const [calendarType, setCalendarType] = useState<CalendarType>('ALL_365');
  const [minCoverage, setMinCoverage] = useState(1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const processOptions = (processesData?.items || []).map((p) => ({
    value: p.id,
    label: `${p.name} (${p.code})`,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const selectedProc = processId || (processesData?.items?.[0]?.id ?? '');

    if (!selectedProc) {
      setErrorMsg('Please select an operational process to instantiate.');
      return;
    }

    try {
      await createMutation.mutateAsync({
        brand_id: brandId,
        process_id: selectedProc,
        calendar_type: calendarType,
        min_coverage_default: minCoverage,
      });
      toast.success(
        'Process instantiated',
        `Process configured for ${brandName || 'Brand'} with ${calendarType} calendar.`
      );
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to instantiate process';
      setErrorMsg(msg);
      toast.error('Operation failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Add Process to ${brandName || 'Brand'}`}
      description="Instantiate an operational process for this brand, defining its calendar and minimum staffing requirements."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="brand-process-form"
            isLoading={createMutation.isPending}
          >
            Add Process
          </Button>
        </div>
      }
    >
      <form id="brand-process-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Select
          label="Process Capability"
          value={processId || (processesData?.items?.[0]?.id ?? '')}
          options={processOptions}
          onChange={setProcessId}
        />

        <Select
          label="Operating Calendar Type"
          value={calendarType}
          options={CALENDAR_OPTIONS}
          onChange={(val) => setCalendarType(val as CalendarType)}
        />

        <Input
          label="Default Minimum Coverage (Staff per Day)"
          type="number"
          min={0}
          max={50}
          value={minCoverage}
          onChange={(e) => setMinCoverage(parseInt(e.target.value, 10))}
          required
        />
      </form>
    </Modal>
  );
};

