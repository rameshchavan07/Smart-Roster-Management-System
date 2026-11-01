import React, { useState } from 'react';
import { Modal, Button, Input, Select, Combobox, useToast } from '../../components/ui';
import { useCreateLeaveMutation } from '../../api/leaves';
import { useEmployeesQuery } from '../../api/team';
import type { LeaveType, LeaveStatus } from '../../types/leaves';

export interface LeaveModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultEmployeeId?: string;
  defaultStartDate?: string;
  isManager?: boolean;
}

const LEAVE_TYPES: Array<{ value: LeaveType; label: string }> = [
  { value: 'PLANNED', label: 'PLANNED (Annual, Vacation, Scheduled Leave)' },
  { value: 'UNPLANNED', label: 'UNPLANNED (Sick, Emergency, Short Notice)' },
  { value: 'COMP_OFF', label: 'COMP_OFF (Compensatory Off Redemption)' },
];

export const LeaveModal: React.FC<LeaveModalProps> = ({
  isOpen,
  onClose,
  defaultEmployeeId,
  defaultStartDate = '2026-12-14',
  isManager = true,
}) => {
  const toast = useToast();
  const { data: employeesData } = useEmployeesQuery({ is_active: true, limit: 150 });
  const createMutation = useCreateLeaveMutation();

  const [employeeId, setEmployeeId] = useState(defaultEmployeeId || '');
  const [type, setType] = useState<LeaveType>('PLANNED');
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultStartDate);
  const [note, setNote] = useState('');
  const [autoApprove, setAutoApprove] = useState(isManager);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const employeeOptions = (employeesData?.items || []).map((emp) => ({
    value: emp.id,
    label: `${emp.full_name} (${emp.code})`,
    subtitle: `${emp.pod_name || 'Pod'} · ${emp.is_floater ? 'Floater' : 'Dedicated'}`,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetEmpId = employeeId || defaultEmployeeId || (employeesData?.items?.[0]?.id ?? '');

    if (!targetEmpId) {
      setErrorMsg('Please select an employee.');
      return;
    }

    if (endDate < startDate) {
      setErrorMsg('End date must be on or after start date.');
      return;
    }

    const leaveStatus: LeaveStatus = autoApprove ? 'APPROVED' : 'REQUESTED';

    try {
      await createMutation.mutateAsync({
        employee_id: targetEmpId,
        start_date: startDate,
        end_date: endDate,
        type,
        status: leaveStatus,
        note: note.trim() || null,
      });

      toast.success(
        autoApprove ? 'Leave recorded and approved' : 'Leave request submitted',
        `Leave scheduled for ${startDate} to ${endDate}.`
      );
      setNote('');
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit leave';
      setErrorMsg(msg);
      toast.error('Operation failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Request / Enter Leave"
      description="Record an employee leave absence. Leaves override standard working shifts with status L."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="leave-form"
            isLoading={createMutation.isPending}
          >
            {autoApprove ? 'Record Leave' : 'Submit Request'}
          </Button>
        </div>
      }
    >
      <form id="leave-form" onSubmit={handleSubmit} className="space-y-4">
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

        <Select
          label="Leave Classification"
          value={type}
          options={LEAVE_TYPES}
          onChange={(val) => setType(val as LeaveType)}
        />

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Start Date"
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              if (endDate < e.target.value) {
                setEndDate(e.target.value);
              }
            }}
            required
          />

          <Input
            label="End Date"
            type="date"
            value={endDate}
            min={startDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>

        <Input
          label="Operational Note / Reason"
          placeholder="e.g. Vacation, Medical appointment, Family event"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />

        {isManager && (
          <label className="flex items-center gap-2 pt-1 text-xs text-ink cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoApprove}
              onChange={(e) => setAutoApprove(e.target.checked)}
              className="rounded-ctl border-border-strong text-accent-600 focus:ring-accent-600"
            />
            <span className="font-medium">Directly approve leave without pending approval</span>
          </label>
        )}
      </form>
    </Modal>
  );
};
