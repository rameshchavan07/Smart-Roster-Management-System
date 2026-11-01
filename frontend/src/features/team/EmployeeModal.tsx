import React, { useState } from 'react';
import { Modal, Button, Input, Select, useToast } from '../../components/ui';
import { useCreateEmployeeMutation, usePodsQuery } from '../../api/team';
import type { EmployeeCreateInput } from '../../types/team';

export interface EmployeeModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPodId?: string;
}

export const EmployeeModal: React.FC<EmployeeModalProps> = ({
  isOpen,
  onClose,
  defaultPodId,
}) => {
  const toast = useToast();
  const { data: podsData } = usePodsQuery();
  const createMutation = useCreateEmployeeMutation();

  const [code, setCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [podId, setPodId] = useState(defaultPodId || '');
  const [isFloater, setIsFloater] = useState(false);
  const [weeklyOffCount, setWeeklyOffCount] = useState(1);
  const [maxConsecutiveDays, setMaxConsecutiveDays] = useState(6);
  const [maxConcurrentProcesses, setMaxConcurrentProcesses] = useState(3);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const podOptions = (podsData?.items || []).map((p) => ({
    value: p.id,
    label: p.name,
  }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const selectedPod = podId || (podsData?.items?.[0]?.id ?? '');

    if (!code.trim() || !fullName.trim() || !selectedPod) {
      setErrorMsg('Please provide employee code, full name, and assign a pod.');
      return;
    }

    const payload: EmployeeCreateInput = {
      code: code.trim(),
      full_name: fullName.trim(),
      email: email.trim() || null,
      pod_id: selectedPod,
      is_floater: isFloater,
      weekly_off_count: weeklyOffCount,
      max_consecutive_days: maxConsecutiveDays,
      max_concurrent_processes: maxConcurrentProcesses,
    };

    try {
      await createMutation.mutateAsync(payload);
      toast.success('Employee created', `${fullName} (${code}) has been added to team roster.`);
      // Reset form
      setCode('');
      setFullName('');
      setEmail('');
      setIsFloater(false);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create employee';
      setErrorMsg(msg);
      toast.error('Creation failed', msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Employee"
      description="Create a team member and configure their staffing pod and constraints."
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="add-employee-form"
            isLoading={createMutation.isPending}
          >
            Create Employee
          </Button>
        </div>
      }
    >
      <form id="add-employee-form" onSubmit={handleSubmit} className="space-y-3.5">
        {errorMsg && (
          <div className="rounded-ctl border border-bad/30 bg-bad/10 p-2.5 text-xs text-bad">
            {errorMsg}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Employee Code"
            placeholder="e.g. EMP-025"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />

          <Select
            label="Assigned Pod"
            value={podId || (podsData?.items?.[0]?.id ?? '')}
            options={podOptions}
            onChange={setPodId}
          />
        </div>

        <Input
          label="Full Name"
          placeholder="e.g. Aditi Verma"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />

        <Input
          label="Email Address (optional)"
          type="email"
          placeholder="e.g. aditi.verma@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <div className="grid grid-cols-3 gap-2.5 pt-1">
          <Input
            label="Weekly Offs (d/wk)"
            type="number"
            min={0}
            max={7}
            value={weeklyOffCount}
            onChange={(e) => setWeeklyOffCount(parseInt(e.target.value, 10))}
          />

          <Input
            label="Max Consecutive"
            type="number"
            min={1}
            max={14}
            value={maxConsecutiveDays}
            onChange={(e) => setMaxConsecutiveDays(parseInt(e.target.value, 10))}
          />

          <Input
            label="Max Concurrent"
            type="number"
            min={1}
            max={10}
            value={maxConcurrentProcesses}
            onChange={(e) => setMaxConcurrentProcesses(parseInt(e.target.value, 10))}
          />
        </div>

        <label className="flex items-center gap-2 pt-1 text-xs text-ink cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isFloater}
            onChange={(e) => setIsFloater(e.target.checked)}
            className="rounded-ctl border-border-strong text-accent-600 focus:ring-accent-600"
          />
          <span className="font-medium">Mark as Floater resource</span>
        </label>
      </form>
    </Modal>
  );
};
