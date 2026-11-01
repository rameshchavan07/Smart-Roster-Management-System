import React from 'react';
import {
  Drawer,
  Button,
  Badge,
  useToast,
} from '../../components/ui';
import {
  useApproveLeaveMutation,
  useRejectLeaveMutation,
  useCancelLeaveMutation,
} from '../../api/leaves';
import { showApiErrorToast } from '../../api/errorMapping';
import type { Leave } from '../../types/leaves';
import { Calendar, User, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

export interface LeaveDrawerProps {
  leave: Leave | null;
  isOpen: boolean;
  onClose: () => void;
  canApprove?: boolean;
}

export const LeaveDrawer: React.FC<LeaveDrawerProps> = ({
  leave,
  isOpen,
  onClose,
  canApprove = true,
}) => {
  const toast = useToast();
  const approveMutation = useApproveLeaveMutation();
  const rejectMutation = useRejectLeaveMutation();
  const cancelMutation = useCancelLeaveMutation();

  if (!leave) return null;

  const startDateObj = new Date(leave.start_date);
  const endDateObj = new Date(leave.end_date);
  const diffDays =
    Math.round(
      Math.abs((endDateObj.getTime() - startDateObj.getTime()) / (1000 * 60 * 60 * 24))
    ) + 1;

  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync(leave.id);
      toast.success(
        'Leave approved',
        `Approved ${diffDays} day(s) for ${leave.employee_name || 'Employee'}.`
      );
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Approval failed');
    }
  };

  const handleReject = async () => {
    try {
      await rejectMutation.mutateAsync(leave.id);
      toast.warning(
        'Leave rejected',
        `Leave request for ${leave.employee_name || 'Employee'} was rejected.`
      );
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Rejection failed');
    }
  };

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(leave.id);
      toast.info(
        'Leave cancelled',
        `Leave on ${leave.start_date} was marked as CANCELLED.`
      );
      onClose();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Cancellation failed');
    }
  };

  const getStatusBadge = () => {
    switch (leave.status) {
      case 'APPROVED':
        return <Badge variant="SUCCESS">Approved</Badge>;
      case 'REQUESTED':
        return <Badge variant="WARNING">Pending Approval</Badge>;
      case 'REJECTED':
        return <Badge variant="BLOCKING">Rejected</Badge>;
      case 'CANCELLED':
        return <Badge variant="neutral">Cancelled</Badge>;
    }
  };

  const isPendingAction =
    approveMutation.isPending || rejectMutation.isPending || cancelMutation.isPending;

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="Leave Request Details"
      subtitle={`${leave.employee_name || 'Employee'} (${leave.employee_code || ''})`}
      width="w-[420px]"
      footer={
        <div className="flex w-full items-center justify-between">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isPendingAction}>
            Close
          </Button>

          <div className="flex items-center gap-2">
            {leave.status === 'REQUESTED' && canApprove && (
              <>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleReject}
                  isLoading={rejectMutation.isPending}
                >
                  <XCircle className="h-3.5 w-3.5 mr-1" />
                  Reject
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleApprove}
                  isLoading={approveMutation.isPending}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                  Approve
                </Button>
              </>
            )}

            {leave.status === 'APPROVED' && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleCancel}
                isLoading={cancelMutation.isPending}
              >
                Cancel Leave
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Status & Header Box */}
        <div className="flex items-center justify-between rounded-ctl border border-border bg-surface-2/60 p-3">
          <div>
            <p className="text-[10px] uppercase font-semibold text-ink-3">Current Status</p>
            <div className="mt-1">{getStatusBadge()}</div>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase font-semibold text-ink-3">Leave Type</p>
            <span className="font-mono text-xs font-semibold text-ink mt-1 inline-block">
              {leave.type}
            </span>
          </div>
        </div>

        {/* Date Range Card */}
        <div className="rounded-ctl border border-border bg-surface p-3.5 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <Calendar className="h-4 w-4 text-accent-600" />
            <span>Requested Period ({diffDays} calendar days)</span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-xs">
            <div className="rounded-ctl bg-surface-2 p-2">
              <p className="text-[10px] text-ink-3 uppercase font-sans">Start Date</p>
              <p className="font-semibold text-ink mt-0.5">{leave.start_date}</p>
            </div>
            <div className="rounded-ctl bg-surface-2 p-2">
              <p className="text-[10px] text-ink-3 uppercase font-sans">End Date</p>
              <p className="font-semibold text-ink mt-0.5">{leave.end_date}</p>
            </div>
          </div>
        </div>

        {/* Employee Info */}
        <div className="rounded-ctl border border-border bg-surface p-3.5 space-y-2 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-ink">
            <User className="h-4 w-4 text-accent-600" />
            <span>Staff Member</span>
          </div>
          <p className="text-ink font-medium">{leave.employee_name}</p>
          <p className="font-mono text-[11px] text-ink-3">ID: {leave.employee_id}</p>
        </div>

        {/* Operational Note */}
        <div className="rounded-ctl border border-border bg-surface p-3.5 space-y-1 text-xs">
          <p className="font-semibold text-ink">Reason / Operational Context</p>
          <p className="text-ink-2 italic">{leave.note || 'No specific reason entered.'}</p>
        </div>

        {/* Operational Impact Notice per S6 */}
        {leave.status === 'REQUESTED' && (
          <div className="rounded-ctl border border-warn/30 bg-[#FBF0D9] p-3 text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-warn">
              <AlertTriangle className="h-4 w-4" />
              <span>Roster Impact Notice</span>
            </div>
            <p className="text-[11px] text-ink">
              Approving this leave will mark the employee as <strong>LEAVE (L)</strong> in active
              draft rosters and trigger coverage re-validation.
            </p>
          </div>
        )}
      </div>
    </Drawer>
  );
};
