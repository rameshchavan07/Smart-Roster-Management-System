import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Button,
  Input,
  Select,
  Badge,
  Skeleton,
  useToast,
} from '../../components/ui';
import {
  useEmployeeQuery,
  useEmployeeCompOffBalanceQuery,
  useEmployeeAssignmentsQuery,
  useEmployeeWeeklyOffRulesQuery,
  useUpdateEmployeeMutation,
  useDeleteEmployeeMutation,
  usePodsQuery,
} from '../../api/team';
import { showApiErrorToast } from '../../api/errorMapping';
import type { EmployeeUpdateInput } from '../../types/team';
import { Award, Briefcase, CalendarCheck } from 'lucide-react';

export interface EmployeeDrawerProps {
  employeeId: string | null;
  isOpen: boolean;
  onClose: () => void;
  canEdit?: boolean;
}

const WEEKDAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const EmployeeDrawer: React.FC<EmployeeDrawerProps> = ({
  employeeId,
  isOpen,
  onClose,
  canEdit = true,
}) => {
  const toast = useToast();

  const { data: employee, isLoading: isEmpLoading } = useEmployeeQuery(employeeId);
  const { data: compOff } = useEmployeeCompOffBalanceQuery(employeeId);
  const { data: assignments } = useEmployeeAssignmentsQuery(employeeId);
  const { data: weeklyOffRules } = useEmployeeWeeklyOffRulesQuery(employeeId);
  const { data: podsData } = usePodsQuery();

  const updateMutation = useUpdateEmployeeMutation();
  const deleteMutation = useDeleteEmployeeMutation();

  const [formData, setFormData] = useState<EmployeeUpdateInput>({});
  const [activeTab, setActiveTab] = useState<'profile' | 'assignments' | 'rules'>('profile');

  useEffect(() => {
    if (employee) {
      setFormData({
        full_name: employee.full_name,
        email: employee.email || '',
        pod_id: employee.pod_id,
        is_floater: employee.is_floater,
        weekly_off_count: employee.weekly_off_count,
        max_consecutive_days: employee.max_consecutive_days,
        max_concurrent_processes: employee.max_concurrent_processes,
        is_active: employee.is_active,
      });
    }
  }, [employee]);

  const handleSave = async () => {
    if (!employeeId) return;
    try {
      await updateMutation.mutateAsync({
        id: employeeId,
        data: formData,
      });
      toast.success('Employee updated', `${formData.full_name || 'Employee'} details saved successfully.`);
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Update failed');
    }
  };

  const handleToggleActive = async () => {
    if (!employeeId || !employee) return;
    const newStatus = !employee.is_active;
    try {
      await updateMutation.mutateAsync({
        id: employeeId,
        data: { is_active: newStatus },
      });
      toast.success(
        newStatus ? 'Employee activated' : 'Employee deactivated',
        `${employee.full_name} is now ${newStatus ? 'active' : 'inactive'}.`
      );
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to change status');
    }
  };

  const handleDelete = async () => {
    if (!employeeId || !employee) return;
    if (!window.confirm(`Are you sure you want to permanently delete ${employee.full_name}?`)) return;
    try {
      await deleteMutation.mutateAsync(employeeId);
      toast.success('Employee deleted', `${employee.full_name} has been removed.`);
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete employee');
    }
  };

  const podOptions = (podsData?.items || []).map((p) => ({
    value: p.id,
    label: p.name,
  }));

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={employee?.full_name || 'Employee Details'}
      subtitle={employee ? `${employee.code} · ${employee.pod_name || 'Pod Member'}` : undefined}
      width="w-[460px]"
      footer={
        canEdit && employee ? (
          <div className="flex w-full items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleToggleActive}
                isLoading={updateMutation.isPending}
              >
                {employee.is_active ? 'Deactivate' : 'Activate'}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                isLoading={deleteMutation.isPending}
                title="Delete employee (blocked if employee has roster history)"
              >
                Delete
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                isLoading={updateMutation.isPending}
              >
                Save Changes
              </Button>
            </div>
          </div>
        ) : undefined
      }
    >
      {isEmpLoading || !employee ? (
        <div className="space-y-4">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Status & Badges header */}
          <div className="flex items-center justify-between rounded-ctl border border-border bg-surface-2/60 p-3">
            <div className="flex items-center gap-2">
              <Badge variant={employee.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                {employee.is_active ? 'Active' : 'Inactive'}
              </Badge>
              {employee.is_floater ? (
                <Badge variant="INFO" size="sm">
                  Floater Resource
                </Badge>
              ) : (
                <Badge variant="neutral" size="sm">
                  Dedicated Pod Member
                </Badge>
              )}
            </div>
            <span className="font-mono text-[11px] text-ink-3">Code: {employee.code}</span>
          </div>

          {/* Comp-Off Balance Card */}
          {compOff && (
            <div className="rounded-ctl border border-border bg-surface p-3.5 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
                <Award className="h-4 w-4 text-accent-600" />
                <span>Comp-off Ledger Balance</span>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                <div className="rounded-ctl bg-surface-2 p-2">
                  <p className="text-[10px] text-ink-3">Earned</p>
                  <p className="font-mono text-base font-semibold text-ink">{compOff.earned}</p>
                </div>
                <div className="rounded-ctl bg-surface-2 p-2">
                  <p className="text-[10px] text-ink-3">Redeemed</p>
                  <p className="font-mono text-base font-semibold text-ink">{compOff.redeemed}</p>
                </div>
                <div className="rounded-ctl bg-accent-50 border border-accent-100 p-2">
                  <p className="text-[10px] text-accent-700 font-medium">Available</p>
                  <p className="font-mono text-base font-semibold text-accent-700">
                    {compOff.available}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Section Navigation Tabs */}
          <div className="flex border-b border-border text-xs font-medium">
            <button
              type="button"
              onClick={() => setActiveTab('profile')}
              className={`pb-2 px-3 border-b-2 transition-colors ${
                activeTab === 'profile'
                  ? 'border-accent-600 font-semibold text-accent-700'
                  : 'border-transparent text-ink-3 hover:text-ink'
              }`}
            >
              Profile & Policy
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('assignments')}
              className={`pb-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === 'assignments'
                  ? 'border-accent-600 font-semibold text-accent-700'
                  : 'border-transparent text-ink-3 hover:text-ink'
              }`}
            >
              Assignments ({assignments?.items?.length ?? 0})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('rules')}
              className={`pb-2 px-3 border-b-2 transition-colors ${
                activeTab === 'rules'
                  ? 'border-accent-600 font-semibold text-accent-700'
                  : 'border-transparent text-ink-3 hover:text-ink'
              }`}
            >
              Weekly-off Rules
            </button>
          </div>

          {/* Tab 1: Profile & Policy */}
          {activeTab === 'profile' && (
            <div className="space-y-3.5">
              <Input
                label="Full Name"
                value={formData.full_name || ''}
                disabled={!canEdit}
                onChange={(e) => setFormData((p) => ({ ...p, full_name: e.target.value }))}
              />

              <Input
                label="Email Address"
                type="email"
                value={formData.email || ''}
                disabled={!canEdit}
                onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
              />

              <Select
                label="Assigned Pod"
                value={formData.pod_id || employee.pod_id}
                disabled={!canEdit}
                options={podOptions}
                onChange={(val) => setFormData((p) => ({ ...p, pod_id: val }))}
              />

              <div className="grid grid-cols-2 gap-3 pt-1">
                <Input
                  label="Weekly Offs (days/wk)"
                  type="number"
                  min={0}
                  max={7}
                  disabled={!canEdit}
                  value={formData.weekly_off_count ?? 1}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, weekly_off_count: parseInt(e.target.value, 10) }))
                  }
                />

                <Input
                  label="Max Consecutive Days"
                  type="number"
                  min={1}
                  max={14}
                  disabled={!canEdit}
                  value={formData.max_consecutive_days ?? 6}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      max_consecutive_days: parseInt(e.target.value, 10),
                    }))
                  }
                />
              </div>

              <Input
                label="Max Concurrent Processes"
                type="number"
                min={1}
                max={10}
                disabled={!canEdit}
                value={formData.max_concurrent_processes ?? 3}
                onChange={(e) =>
                  setFormData((p) => ({
                    ...p,
                    max_concurrent_processes: parseInt(e.target.value, 10),
                  }))
                }
              />

              <label className="flex items-center gap-2 pt-1 text-xs text-ink cursor-pointer select-none">
                <input
                  type="checkbox"
                  disabled={!canEdit}
                  checked={formData.is_floater ?? false}
                  onChange={(e) => setFormData((p) => ({ ...p, is_floater: e.target.checked }))}
                  className="rounded-ctl border-border-strong text-accent-600 focus:ring-accent-600"
                />
                <span className="font-medium">Mark as Floater resource (can support multiple pods)</span>
              </label>
            </div>
          )}

          {/* Tab 2: Brand Process Assignments */}
          {activeTab === 'assignments' && (
            <div className="space-y-2">
              {!assignments?.items || assignments.items.length === 0 ? (
                <div className="rounded-ctl border border-dashed border-border p-6 text-center text-ink-3">
                  <Briefcase className="mx-auto h-5 w-5 mb-1.5 text-ink-3 opacity-60" />
                  <p>No active staffing assignments</p>
                </div>
              ) : (
                assignments.items.map((asgn) => (
                  <div
                    key={asgn.id}
                    className="flex items-center justify-between rounded-ctl border border-border bg-surface p-2.5"
                  >
                    <div>
                      <p className="font-semibold text-xs text-ink">
                        Brand-Process: {asgn.brand_process_id.substring(0, 8)}...
                      </p>
                      <p className="text-[11px] text-ink-3">
                        {asgn.is_active ? 'Active assignment' : 'Inactive'}
                      </p>
                    </div>
                    <Badge
                      variant={asgn.assignment_type === 'PRIMARY' ? 'SUCCESS' : 'INFO'}
                      size="sm"
                    >
                      {asgn.assignment_type}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 3: Weekly-off Rules */}
          {activeTab === 'rules' && (
            <div className="space-y-2">
              {!weeklyOffRules?.items || weeklyOffRules.items.length === 0 ? (
                <div className="rounded-ctl border border-dashed border-border p-6 text-center text-ink-3">
                  <CalendarCheck className="mx-auto h-5 w-5 mb-1.5 text-ink-3 opacity-60" />
                  <p>Standard policy applies (Default: 1 off / week)</p>
                </div>
              ) : (
                weeklyOffRules.items.map((rule) => (
                  <div
                    key={rule.id}
                    className="rounded-ctl border border-border bg-surface p-3 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-ink">Mode: {rule.mode}</span>
                      <Badge variant={rule.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                        {rule.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    {rule.weekdays && rule.weekdays.length > 0 && (
                      <div className="flex items-center gap-1 pt-1">
                        <span className="text-[11px] text-ink-3">Days:</span>
                        {rule.weekdays.map((dayIdx) => (
                          <span
                            key={dayIdx}
                            className="rounded-chip bg-surface-2 px-1.5 py-0.5 text-[10px] font-mono font-medium text-ink"
                          >
                            {WEEKDAY_NAMES[dayIdx] || dayIdx}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
};
