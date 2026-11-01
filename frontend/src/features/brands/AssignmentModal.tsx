import React, { useState } from 'react';
import { Modal, Button, Combobox, Select, useToast } from '../../components/ui';
import { useCreateAssignmentMutation } from '../../api/brands';
import { useEmployeesQuery } from '../../api/team';

export interface AssignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  brandProcessId: string;
  brandName?: string;
  processName?: string;
}

export const AssignmentModal: React.FC<AssignmentModalProps> = ({
  isOpen,
  onClose,
  brandProcessId,
  brandName,
  processName,
}) => {
  const toast = useToast();
  const { data: employeesData } = useEmployeesQuery({ is_active: true, limit: 150 });
  const createMutation = useCreateAssignmentMutation();

  const [employeeId, setEmployeeId] = useState('');
  const [assignmentType, setAssignmentType] = useState<'PRIMARY' | 'BACKUP'>('PRIMARY');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const employeeOptions = (employeesData?.items || []).map((emp) => ({
    value: emp.id,
    label: `${emp.full_name} (${emp.code})`,
    subtitle: `${emp.pod_name || 'Pod'} · ${emp.is_floater ? 'Floater' : 'Dedicated'}`,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId) {
      setErrorMsg('Please select an employee to assign.');
      return;
    }

    try {
      await createMutation.mutateAsync({
        employee_id: employeeId,
        brand_process_id: brandProcessId,
        assignment_type: assignmentType,
      });
      toast.success(
        'Assignment created',
        `Employee assigned as ${assignmentType} resource to ${brandName || ''} - ${processName || ''}.`
      );
      setEmployeeId('');
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create assignment';
      setErrorMsg(msg);
      toast.error('Assignment failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Assign Staff to Process"
      description={`Add an employee assignment for ${brandName || 'Brand'} — ${processName || 'Process'}.`}
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="assignment-form"
            isLoading={createMutation.isPending}
          >
            Assign Employee
          </Button>
        </div>
      }
    >
      <form id="assignment-form" onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <Combobox
          label="Select Employee"
          placeholder="Search employee by name, code or pod..."
          value={employeeId}
          options={employeeOptions}
          onChange={setEmployeeId}
        />

        <Select
          label="Assignment Role"
          value={assignmentType}
          options={[
            {
              value: 'PRIMARY',
              label: 'PRIMARY (Responsible for regular daily shifts)',
            },
            {
              value: 'BACKUP',
              label: 'BACKUP (Called when primary is on leave/off or coverage shortfall exists)',
            },
          ]}
          onChange={(val) => setAssignmentType(val as 'PRIMARY' | 'BACKUP')}
        />
      </form>
    </Modal>
  );
};
