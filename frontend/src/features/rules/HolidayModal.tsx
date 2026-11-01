import React, { useState } from 'react';
import { Modal, Button, Input, Select, useToast } from '../../components/ui';
import { useCreateHolidayMutation } from '../../api/rules';
import { useBrandsQuery } from '../../api/brands';

export interface HolidayModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultDate?: string;
}

export const HolidayModal: React.FC<HolidayModalProps> = ({
  isOpen,
  onClose,
  defaultDate,
}) => {
  const toast = useToast();
  const { data: brandsData } = useBrandsQuery({ limit: 100 });
  const createMutation = useCreateHolidayMutation();

  const [name, setName] = useState('');
  const [date, setDate] = useState(defaultDate || '2026-12-25');
  const [isGlobal, setIsGlobal] = useState(true);
  const [brandId, setBrandId] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const brandOptions = (brandsData?.items || []).map((b) => ({
    value: b.id,
    label: `${b.name} (${b.code})`,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !date) {
      setErrorMsg('Holiday name and date are required.');
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        date,
        brand_id: isGlobal ? null : brandId || null,
      });
      toast.success(
        'Holiday added',
        `"${name}" scheduled on ${date} (${isGlobal ? 'Global' : 'Brand-specific'}).`
      );
      setName('');
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add holiday';
      setErrorMsg(msg);
      toast.error('Operation failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Public / Company Holiday"
      description="Add an official public holiday. Employees working on this day qualify for Holiday Worked (HW) with compensatory off accrual."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="holiday-form"
            isLoading={createMutation.isPending}
          >
            Add Holiday
          </Button>
        </div>
      }
    >
      <form id="holiday-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Input
          label="Holiday Name"
          placeholder="e.g. Christmas Day, New Year's Day"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <Input
          label="Holiday Date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          required
        />

        {/* Scope selector */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-ink-2">Holiday Scope</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setIsGlobal(true)}
              className={`rounded-ctl border p-2 text-xs font-medium text-center transition-colors ${
                isGlobal
                  ? 'border-accent-600 bg-accent-50 text-accent-700'
                  : 'border-border bg-surface text-ink-2 hover:bg-surface-2'
              }`}
            >
              Company-wide (Global)
            </button>
            <button
              type="button"
              onClick={() => setIsGlobal(false)}
              className={`rounded-ctl border p-2 text-xs font-medium text-center transition-colors ${
                !isGlobal
                  ? 'border-accent-600 bg-accent-50 text-accent-700'
                  : 'border-border bg-surface text-ink-2 hover:bg-surface-2'
              }`}
            >
              Brand-Specific
            </button>
          </div>

          {!isGlobal && (
            <div className="pt-1">
              <Select
                label="Target Brand"
                value={brandId || (brandsData?.items?.[0]?.id ?? '')}
                options={brandOptions}
                onChange={setBrandId}
              />
            </div>
          )}
        </div>
      </form>
    </Modal>
  );
};
