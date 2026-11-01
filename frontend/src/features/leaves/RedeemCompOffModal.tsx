import React, { useState } from 'react';
import { Modal, Button, Input, Combobox, useToast } from '../../components/ui';
import { useRedeemCompOffMutation } from '../../api/leaves';
import { useEmployeesQuery } from '../../api/team';

export interface RedeemCompOffModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultEmployeeId?: string;
}

export const RedeemCompOffModal: React.FC<RedeemCompOffModalProps> = ({
  isOpen,
  onClose,
  defaultEmployeeId,
}) => {
  const toast = useToast();
  const { data: employeesData } = useEmployeesQuery({ is_active: true, limit: 150 });
  const redeemMutation = useRedeemCompOffMutation();

  const [employeeId, setEmployeeId] = useState(defaultEmployeeId || '');
  const [date, setDate] = useState('2026-12-18');
  const [note, setNote] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const employeeOptions = (employeesData?.items || []).map((emp) => ({
    value: emp.id,
    label: `${emp.full_name} (${emp.code})`,
    subtitle: `${emp.pod_name || 'Pod'}`,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetEmpId = employeeId || defaultEmployeeId;

    if (!targetEmpId) {
      setErrorMsg('Please select an employee.');
      return;
    }

    try {
      await redeemMutation.mutateAsync({
        employee_id: targetEmpId,
        date,
        note: note.trim() || 'Comp-off redemption',
      });
      toast.success(
        'Comp-off redeemed',
        `Comp-off scheduled for ${date}. Created approved COMP_OFF leave.`
      );
      setNote('');
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Redemption failed';
      setErrorMsg(msg);
      toast.error('Redemption failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Redeem Comp-off Credit"
      description="Redeem an accumulated compensatory off credit earned from working on public holidays."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="redeem-form"
            isLoading={redeemMutation.isPending}
          >
            Redeem Credit
          </Button>
        </div>
      }
    >
      <form id="redeem-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Combobox
          label="Staff Member"
          placeholder="Search employee..."
          value={employeeId || defaultEmployeeId}
          options={employeeOptions}
          onChange={setEmployeeId}
        />

        <Input
          label="Redemption Date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          required
        />

        <Input
          label="Note (Optional)"
          placeholder="e.g. Redeemed for festive shift worked"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </form>
    </Modal>
  );
};
