import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  Search,
  Plus,
  CheckCircle2,
  XCircle,
  Calendar,
  Award,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Gift,
  Sparkles,
} from 'lucide-react';
import {
  Button,
  Select,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Skeleton,
  EmptyState,
  useToast,
} from '../../components/ui';
import {
  useLeavesQuery,
  useApproveLeaveMutation,
  useRejectLeaveMutation,
  useCompOffLedgerQuery,
} from '../../api/leaves';
import { useEmployeesQuery } from '../../api/team';
import { showApiErrorToast } from '../../api/errorMapping';
import { useAuth } from '../auth/AuthContext';
import { LeaveDrawer } from './LeaveDrawer';
import { LeaveModal } from './LeaveModal';
import { RedeemCompOffModal } from './RedeemCompOffModal';
import type { Leave, LeaveStatus } from '../../types/leaves';

export const LeavesPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const { isOpsManager, isPodLead, isEmployee, user } = useAuth();
  const canApprove = isOpsManager || isPodLead;

  // Active Tab: 'leaves' | 'compoffs'
  const [activeTab, setActiveTab] = useState<'leaves' | 'compoffs'>('leaves');

  // Leaves filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [pageOffset, setPageOffset] = useState(0);
  const pageSize = 25;

  // Modals & Drawers
  const [selectedLeave, setSelectedLeave] = useState<Leave | null>(null);
  const [isLeaveDrawerOpen, setIsLeaveDrawerOpen] = useState(false);
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [isRedeemModalOpen, setIsRedeemModalOpen] = useState(false);
  const [redeemTargetEmpId, setRedeemTargetEmpId] = useState<string | undefined>(undefined);

  // Queries
  const {
    data: leavesData,
    isLoading: isLeavesLoading,
    isError: isLeavesError,
    refetch: refetchLeaves,
  } = useLeavesQuery({
    offset: pageOffset,
    limit: pageSize,
    status: statusFilter !== 'all' ? (statusFilter as LeaveStatus) : undefined,
  });

  const {
    data: ledgerData,
    isLoading: isLedgerLoading,
    isError: isLedgerError,
  } = useCompOffLedgerQuery({
    limit: 100,
  });

  const { data: employeesData } = useEmployeesQuery({
    is_active: true,
    limit: 150,
  });

  const approveMutation = useApproveLeaveMutation();
  const rejectMutation = useRejectLeaveMutation();

  // Filter leaves client-side for immediate responsive search
  const filteredLeaves = useMemo(() => {
    if (!leavesData?.items) return [];
    let list = leavesData.items;

    if (typeFilter !== 'all') {
      list = list.filter((l) => l.type === typeFilter);
    }

    if (searchQuery.trim()) {
      const lower = searchQuery.toLowerCase();
      list = list.filter(
        (l) =>
          (l.employee_name && l.employee_name.toLowerCase().includes(lower)) ||
          (l.employee_code && l.employee_code.toLowerCase().includes(lower)) ||
          (l.note && l.note.toLowerCase().includes(lower))
      );
    }
    return list;
  }, [leavesData, typeFilter, searchQuery]);

  // Aggregate comp-off balances per employee from ledger
  const employeeBalances = useMemo(() => {
    const balances = new Map<string, { earned: number; redeemed: number; available: number }>();

    (ledgerData?.items || []).forEach((entry) => {
      const current = balances.get(entry.employee_id) || { earned: 0, redeemed: 0, available: 0 };
      if (entry.kind.startsWith('EARNED')) {
        current.earned += 1;
        current.available += 1;
      } else if (entry.kind === 'REDEEMED') {
        current.redeemed += 1;
        current.available = Math.max(0, current.available - 1);
      }
      balances.set(entry.employee_id, current);
    });

    return balances;
  }, [ledgerData]);

  const handleQuickApprove = async (e: React.MouseEvent, leave: Leave) => {
    e.stopPropagation();
    try {
      await approveMutation.mutateAsync(leave.id);
      toast.success('Leave approved', `Approved leave for ${leave.employee_name || 'Staff'}.`);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Approval failed');
    }
  };

  const handleQuickReject = async (e: React.MouseEvent, leave: Leave) => {
    e.stopPropagation();
    try {
      await rejectMutation.mutateAsync(leave.id);
      toast.warning('Leave rejected', `Rejected leave for ${leave.employee_name || 'Staff'}.`);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Rejection failed');
    }
  };

  const getStatusBadge = (status: LeaveStatus) => {
    switch (status) {
      case 'APPROVED':
        return <Badge variant="SUCCESS" size="sm">Approved</Badge>;
      case 'REQUESTED':
        return <Badge variant="WARNING" size="sm">Pending</Badge>;
      case 'REJECTED':
        return <Badge variant="BLOCKING" size="sm">Rejected</Badge>;
      case 'CANCELLED':
        return <Badge variant="neutral" size="sm">Cancelled</Badge>;
    }
  };

  const totalLeaves = leavesData?.total ?? 0;

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* Title & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink flex items-center gap-2">
            <Clock className="h-5 w-5 text-accent-600" />
            Leaves & Comp-offs
          </h1>
          <p className="text-xs text-ink-2">
            Track planned and emergency absences, approve leave requests, and monitor comp-off balances.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setRedeemTargetEmpId(undefined);
              setIsRedeemModalOpen(true);
            }}
          >
            <Gift className="h-3.5 w-3.5 mr-1" />
            Redeem Comp-off
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsLeaveModalOpen(true)}
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            Request Leave
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab('leaves')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'leaves'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Calendar className="h-3.5 w-3.5" />
          <span>Leave Requests ({totalLeaves})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('compoffs')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'compoffs'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Award className="h-3.5 w-3.5" />
          <span>Comp-off Ledger & Balances</span>
        </button>
      </div>

      {/* TAB 1: LEAVES */}
      {activeTab === 'leaves' && (
        <div className="space-y-3.5">
          {/* Filters Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 bg-surface p-3 rounded-ctl border border-border shadow-xs">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-3" />
              <input
                type="text"
                placeholder="Search staff, code, reason..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 w-full rounded-ctl border border-border-strong bg-surface pl-8 pr-3 text-xs text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent-600 focus:ring-1 focus:ring-accent-600"
              />
            </div>

            {/* Status Filter */}
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'all', label: 'All Statuses' },
                { value: 'REQUESTED', label: 'Pending Approval (REQUESTED)' },
                { value: 'APPROVED', label: 'Approved' },
                { value: 'REJECTED', label: 'Rejected' },
                { value: 'CANCELLED', label: 'Cancelled' },
              ]}
            />

            {/* Type Filter */}
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              options={[
                { value: 'all', label: 'All Leave Types' },
                { value: 'PLANNED', label: 'Planned (Vacation/Annual)' },
                { value: 'UNPLANNED', label: 'Unplanned (Sick/Emergency)' },
                { value: 'COMP_OFF', label: 'Comp-Off Redemption' },
              ]}
            />
          </div>

          {/* Table Container */}
          {isLeavesLoading ? (
            <div className="space-y-2 bg-surface p-4 rounded-ctl border border-border">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : isLeavesError ? (
            <div className="rounded-ctl border border-bad/30 bg-bad/10 p-6 text-center space-y-2">
              <AlertCircle className="mx-auto h-6 w-6 text-bad" />
              <p className="text-xs font-semibold text-bad">Failed to load leave records</p>
              <Button variant="secondary" size="sm" onClick={() => refetchLeaves()}>
                Retry
              </Button>
            </div>
          ) : filteredLeaves.length === 0 ? (
            <div className="bg-surface p-8 rounded-ctl border border-border">
              <EmptyState
                title="No Leave Records Found"
                description={
                  searchQuery
                    ? `No leaves matched query "${searchQuery}".`
                    : 'No leave requests submitted under this status.'
                }
                actionLabel="Request Leave"
                onAction={() => setIsLeaveModalOpen(true)}
              />
            </div>
          ) : (
            <div className="space-y-2">
              <Table dense>
                <TableHeader>
                  <TableRow>
                    <TableHead>Staff Member</TableHead>
                    <TableHead>Dates & Duration</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Operational Note</TableHead>
                    <TableHead className="text-right w-36">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLeaves.map((leave) => {
                    const start = new Date(leave.start_date);
                    const end = new Date(leave.end_date);
                    const count =
                      Math.round(
                        Math.abs((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
                      ) + 1;

                    return (
                      <TableRow
                        key={leave.id}
                        className="cursor-pointer"
                        onClick={() => {
                          setSelectedLeave(leave);
                          setIsLeaveDrawerOpen(true);
                        }}
                      >
                        <TableCell>
                          <p className="font-medium text-ink leading-tight">
                            {leave.employee_name || 'Staff Member'}
                          </p>
                          {leave.employee_code && (
                            <p className="text-[10px] text-ink-3 font-mono leading-tight">
                              {leave.employee_code}
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-xs font-semibold text-ink">
                            {leave.start_date === leave.end_date
                              ? leave.start_date
                              : `${leave.start_date} – ${leave.end_date}`}
                          </span>
                          <span className="text-[11px] text-ink-3 ml-1.5 font-sans">
                            ({count} {count === 1 ? 'day' : 'days'})
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-xs text-ink-2 bg-surface-2 px-1.5 py-0.5 rounded">
                            {leave.type}
                          </span>
                        </TableCell>
                        <TableCell>{getStatusBadge(leave.status)}</TableCell>
                        <TableCell className="text-ink-3 italic max-w-xs truncate">
                          {leave.note || '—'}
                        </TableCell>
                        <TableCell
                          className="text-right space-x-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {leave.status === 'REQUESTED' && canApprove && (
                            <>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() =>
                                  navigate(
                                    `/simulator?type=ADD_LEAVE&employeeId=${leave.employee_id}&date=${leave.start_date}&endDate=${leave.end_date}&autoRun=true`
                                  )
                                }
                                className="h-6 px-1.5 text-[11px]"
                                title="Preview schedule impact in Simulator"
                              >
                                <Sparkles className="h-3 w-3 mr-0.5 text-accent-700" />
                                Preview Impact
                              </Button>
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={(e) => handleQuickApprove(e, leave)}
                                className="h-6 px-1.5 text-[11px]"
                                title="Approve leave"
                              >
                                <CheckCircle2 className="h-3 w-3 mr-0.5" />
                                Approve
                              </Button>
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={(e) => handleQuickReject(e, leave)}
                                className="h-6 px-1.5 text-[11px]"
                                title="Reject leave"
                              >
                                <XCircle className="h-3 w-3 mr-0.5" />
                                Reject
                              </Button>
                            </>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedLeave(leave);
                              setIsLeaveDrawerOpen(true);
                            }}
                            className="h-6 px-2 text-[11px]"
                          >
                            Details
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between text-xs text-ink-3 px-2 pt-1">
                <span>
                  Showing {filteredLeaves.length} of {totalLeaves} records
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pageOffset === 0}
                    onClick={() => setPageOffset((p) => Math.max(0, p - pageSize))}
                    className="h-7 px-2"
                  >
                    <ChevronLeft className="h-3 w-3 mr-0.5" />
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pageOffset + pageSize >= totalLeaves}
                    onClick={() => setPageOffset((p) => p + pageSize)}
                    className="h-7 px-2"
                  >
                    Next
                    <ChevronRight className="h-3 w-3 ml-0.5" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: COMP-OFFS */}
      {activeTab === 'compoffs' && (
        <div className="space-y-5">
          {/* Balances Grid */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3 flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5 text-accent-600" />
              Employee Comp-off Balances
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {(employeesData?.items || []).slice(0, 8).map((emp) => {
                const bal = employeeBalances.get(emp.id) || {
                  earned: 0,
                  redeemed: 0,
                  available: 0,
                };
                return (
                  <div
                    key={emp.id}
                    className="rounded-ctl border border-border bg-surface p-3 flex flex-col justify-between shadow-xs hover:border-border-strong transition-colors"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-ink leading-tight truncate">
                          {emp.full_name}
                        </span>
                        <span className="font-mono text-[10px] text-ink-3">{emp.code}</span>
                      </div>
                      <p className="text-[11px] text-ink-3 mt-0.5">{emp.pod_name || 'Pod'}</p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-border flex items-center justify-between">
                      <div className="text-xs">
                        <span className="text-ink-3 text-[10px]">Available: </span>
                        <span className="font-mono font-bold text-accent-700">
                          {bal.available} credits
                        </span>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={bal.available === 0}
                        onClick={() => {
                          setRedeemTargetEmpId(emp.id);
                          setIsRedeemModalOpen(true);
                        }}
                        className="h-6 text-[11px] px-2"
                      >
                        Redeem
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Comp-off Ledger History Table */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">
              Comp-off Transaction Ledger ({ledgerData?.total ?? 0})
            </h3>

            {isLedgerLoading ? (
              <div className="p-4 space-y-2 bg-surface rounded-ctl border border-border">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : isLedgerError ? (
              <div className="p-6 text-center text-xs text-bad">Failed to load comp-off ledger</div>
            ) : !ledgerData?.items || ledgerData.items.length === 0 ? (
              <div className="bg-surface p-6 rounded-ctl border border-border text-center text-xs text-ink-3">
                No comp-off credits or redemptions recorded yet.
              </div>
            ) : (
              <Table dense>
                <TableHeader>
                  <TableRow>
                    <TableHead>Entry Date</TableHead>
                    <TableHead>Staff Member</TableHead>
                    <TableHead>Transaction Kind</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Note / Operational Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ledgerData.items.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-mono text-xs font-semibold text-ink">
                        {entry.entry_date}
                      </TableCell>
                      <TableCell className="font-medium text-ink">
                        {entry.employee_name || 'Staff Member'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={entry.kind.startsWith('EARNED') ? 'SUCCESS' : 'INFO'}
                          size="sm"
                        >
                          {entry.kind}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs text-ink-2">{entry.status}</span>
                      </TableCell>
                      <TableCell className="text-ink-3 italic">{entry.note || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      )}

      {/* Leave Details Drawer */}
      <LeaveDrawer
        leave={selectedLeave}
        isOpen={isLeaveDrawerOpen}
        onClose={() => {
          setIsLeaveDrawerOpen(false);
          setSelectedLeave(null);
        }}
        canApprove={canApprove}
      />

      {/* Leave Modal */}
      <LeaveModal
        isOpen={isLeaveModalOpen}
        onClose={() => setIsLeaveModalOpen(false)}
        defaultEmployeeId={isEmployee ? user?.employee_id || undefined : undefined}
        isManager={canApprove}
      />

      {/* Redeem Comp-off Modal */}
      <RedeemCompOffModal
        isOpen={isRedeemModalOpen}
        onClose={() => {
          setIsRedeemModalOpen(false);
          setRedeemTargetEmpId(undefined);
        }}
        defaultEmployeeId={redeemTargetEmpId || (isEmployee ? user?.employee_id || undefined : undefined)}
      />
    </div>
  );
};
