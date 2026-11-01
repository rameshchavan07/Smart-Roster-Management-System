import React, { useState, useMemo } from 'react';
import {
  Users,
  Search,
  Plus,
  Layers,
  ChevronLeft,
  ChevronRight,
  Edit2,
  AlertCircle,
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
} from '../../components/ui';
import { useEmployeesQuery, usePodsQuery } from '../../api/team';
import { useAuth } from '../auth/AuthContext';
import { EmployeeDrawer } from './EmployeeDrawer';
import { EmployeeModal } from './EmployeeModal';
import { PodModal } from './PodModal';
import type { Pod } from '../../types/team';

export const TeamPage: React.FC = () => {
  const { isOpsManager, isPodLead } = useAuth();
  const canEdit = isOpsManager || isPodLead;

  // Active Tab: 'employees' | 'pods'
  const [activeTab, setActiveTab] = useState<'employees' | 'pods'>('employees');

  // Employee Filters & Pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPodId, setSelectedPodId] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [floaterFilter, setFloaterFilter] = useState<string>('all');
  const [pageOffset, setPageOffset] = useState(0);
  const pageSize = 25;

  // Modals & Drawers
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);
  const [isEmployeeDrawerOpen, setIsEmployeeDrawerOpen] = useState(false);
  const [isAddEmployeeModalOpen, setIsAddEmployeeModalOpen] = useState(false);
  const [selectedPodForEdit, setSelectedPodForEdit] = useState<Pod | null>(null);
  const [isPodModalOpen, setIsPodModalOpen] = useState(false);

  // Queries
  const {
    data: employeesData,
    isLoading: isEmployeesLoading,
    isError: isEmployeesError,
    error: employeesError,
    refetch: refetchEmployees,
  } = useEmployeesQuery({
    offset: pageOffset,
    limit: pageSize,
    pod_id: selectedPodId !== 'all' ? selectedPodId : undefined,
    is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
    is_floater: floaterFilter === 'all' ? undefined : floaterFilter === 'floater',
  });

  const {
    data: podsData,
    isLoading: isPodsLoading,
    isError: isPodsError,
    refetch: refetchPods,
  } = usePodsQuery();

  // Filter employees client-side for immediate search responsiveness
  const filteredEmployees = useMemo(() => {
    if (!employeesData?.items) return [];
    if (!searchQuery.trim()) return employeesData.items;

    const lower = searchQuery.toLowerCase();
    return employeesData.items.filter(
      (emp) =>
        emp.full_name.toLowerCase().includes(lower) ||
        emp.code.toLowerCase().includes(lower) ||
        (emp.email && emp.email.toLowerCase().includes(lower))
    );
  }, [employeesData, searchQuery]);

  const podFilterOptions = useMemo(() => {
    const list = [{ value: 'all', label: 'All Pods' }];
    if (podsData?.items) {
      podsData.items.forEach((p) => {
        list.push({ value: p.id, label: p.name });
      });
    }
    return list;
  }, [podsData]);

  const totalEmployees = employeesData?.total ?? 0;

  const handleOpenEmployee = (empId: string) => {
    setSelectedEmployeeId(empId);
    setIsEmployeeDrawerOpen(true);
  };

  const handleEditPod = (pod: Pod) => {
    setSelectedPodForEdit(pod);
    setIsPodModalOpen(true);
  };

  const handleCreatePod = () => {
    setSelectedPodForEdit(null);
    setIsPodModalOpen(true);
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* Page Title & Primary Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink flex items-center gap-2">
            <Users className="h-5 w-5 text-accent-600" />
            Team & Pods
          </h1>
          <p className="text-xs text-ink-2">
            Manage operational workforce, staffing pods, weekly-off policies, and constraints.
          </p>
        </div>

        {canEdit && (
          <div className="flex items-center gap-2">
            {activeTab === 'employees' ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsAddEmployeeModalOpen(true)}
              >
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add Employee
              </Button>
            ) : (
              isOpsManager && (
                <Button variant="primary" size="sm" onClick={handleCreatePod}>
                  <Plus className="h-3.5 w-3.5 mr-1.5" />
                  Create Pod
                </Button>
              )
            )}
          </div>
        )}
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-border text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab('employees')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'employees'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          <span>Employees ({totalEmployees || (isEmployeesLoading ? '...' : 0)})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('pods')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'pods'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          <span>Pods ({podsData?.total ?? (isPodsLoading ? '...' : 0)})</span>
        </button>
      </div>

      {/* TAB 1: EMPLOYEES */}
      {activeTab === 'employees' && (
        <div className="space-y-3.5">
          {/* Filter Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 bg-surface p-3 rounded-ctl border border-border shadow-xs">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-3" />
              <input
                type="text"
                placeholder="Search name, code, email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 w-full rounded-ctl border border-border-strong bg-surface pl-8 pr-3 text-xs text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent-600 focus:ring-1 focus:ring-accent-600"
              />
            </div>

            {/* Pod Filter */}
            <Select
              value={selectedPodId}
              onChange={setSelectedPodId}
              options={podFilterOptions}
            />

            {/* Status Filter */}
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'all', label: 'All Statuses' },
                { value: 'active', label: 'Active Only' },
                { value: 'inactive', label: 'Inactive Only' },
              ]}
            />

            {/* Floater Filter */}
            <Select
              value={floaterFilter}
              onChange={setFloaterFilter}
              options={[
                { value: 'all', label: 'All Resource Types' },
                { value: 'floater', label: 'Floaters Only' },
                { value: 'dedicated', label: 'Dedicated Only' },
              ]}
            />
          </div>

          {/* Table Container */}
          {isEmployeesLoading ? (
            <div className="space-y-2 bg-surface p-4 rounded-ctl border border-border">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : isEmployeesError ? (
            <div className="rounded-ctl border border-bad/30 bg-bad/10 p-6 text-center space-y-2">
              <AlertCircle className="mx-auto h-6 w-6 text-bad" />
              <p className="text-xs font-semibold text-bad">Failed to load employees</p>
              <p className="text-[11px] text-ink-3">
                {employeesError instanceof Error ? employeesError.message : 'Network error'}
              </p>
              <Button variant="secondary" size="sm" onClick={() => refetchEmployees()}>
                Retry
              </Button>
            </div>
          ) : filteredEmployees.length === 0 ? (
            <div className="bg-surface p-8 rounded-ctl border border-border">
              <EmptyState
                title="No Employees Found"
                description={
                  searchQuery
                    ? `No employees matched search "${searchQuery}".`
                    : 'No employees are registered under this filter.'
                }
                actionLabel={canEdit ? 'Add First Employee' : undefined}
                onAction={() => setIsAddEmployeeModalOpen(true)}
              />
            </div>
          ) : (
            <div className="space-y-2">
              <Table dense>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">Code</TableHead>
                    <TableHead>Employee</TableHead>
                    <TableHead>Pod</TableHead>
                    <TableHead>Role Type</TableHead>
                    <TableHead className="text-center">Offs / Wk</TableHead>
                    <TableHead className="text-center">Max Days</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right w-20">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEmployees.map((emp) => (
                    <TableRow
                      key={emp.id}
                      className="cursor-pointer"
                      onClick={() => handleOpenEmployee(emp.id)}
                    >
                      <TableCell className="font-mono text-ink-3 font-semibold text-xs">
                        {emp.code}
                      </TableCell>
                      <TableCell>
                        <p className="font-medium text-ink leading-tight">{emp.full_name}</p>
                        {emp.email && (
                          <p className="text-[10px] text-ink-3 font-mono leading-tight">
                            {emp.email}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="font-medium text-xs text-ink">
                          {emp.pod_name || 'Unassigned'}
                        </span>
                      </TableCell>
                      <TableCell>
                        {emp.is_floater ? (
                          <Badge variant="INFO" size="sm">
                            Floater
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Dedicated
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-center font-mono text-xs">
                        {emp.weekly_off_count} d/wk
                      </TableCell>
                      <TableCell className="text-center font-mono text-xs">
                        {emp.max_consecutive_days} d
                      </TableCell>
                      <TableCell>
                        <Badge variant={emp.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                          {emp.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEmployee(emp.id)}
                          className="h-6 px-2 text-[11px]"
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination controls */}
              <div className="flex items-center justify-between text-xs text-ink-3 px-2 pt-1">
                <span>
                  Showing {filteredEmployees.length} of {totalEmployees} employees
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
                    disabled={pageOffset + pageSize >= totalEmployees}
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

      {/* TAB 2: PODS */}
      {activeTab === 'pods' && (
        <div className="space-y-4">
          {isPodsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <Skeleton className="h-32 rounded-ctl" />
              <Skeleton className="h-32 rounded-ctl" />
              <Skeleton className="h-32 rounded-ctl" />
            </div>
          ) : isPodsError ? (
            <div className="rounded-ctl border border-bad/30 bg-bad/10 p-6 text-center">
              <p className="text-xs font-semibold text-bad">Failed to load pods list</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => refetchPods()}
                className="mt-2"
              >
                Retry
              </Button>
            </div>
          ) : !podsData?.items || podsData.items.length === 0 ? (
            <div className="bg-surface p-8 rounded-ctl border border-border">
              <EmptyState
                title="No Pods Configured"
                description="Pods group your workforce into operational teams."
                actionLabel={isOpsManager ? 'Create Pod' : undefined}
                onAction={handleCreatePod}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {podsData.items.map((pod) => (
                <div
                  key={pod.id}
                  className="rounded-ctl border border-border bg-surface p-4 flex flex-col justify-between space-y-4 shadow-xs hover:border-border-strong transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-sm text-ink">{pod.name}</h3>
                        <Badge variant={pod.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                          {pod.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-ink-3 mt-1 font-mono">
                        ID: {pod.id.substring(0, 8)}...
                      </p>
                    </div>

                    {isOpsManager && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditPod(pod)}
                        className="h-7 w-7 p-0 text-ink-3 hover:text-ink"
                        title="Edit pod"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>

                  <div className="pt-2 border-t border-border flex items-center justify-between text-xs">
                    <span className="text-ink-2 font-medium">
                      {pod.member_count ?? 0} members assigned
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedPodId(pod.id);
                        setActiveTab('employees');
                      }}
                      className="text-[11px] h-6 px-2"
                    >
                      View Members
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Employee Details Drawer */}
      <EmployeeDrawer
        employeeId={selectedEmployeeId}
        isOpen={isEmployeeDrawerOpen}
        onClose={() => {
          setIsEmployeeDrawerOpen(false);
          setSelectedEmployeeId(null);
        }}
        canEdit={canEdit}
      />

      {/* Add Employee Modal */}
      <EmployeeModal
        isOpen={isAddEmployeeModalOpen}
        onClose={() => setIsAddEmployeeModalOpen(false)}
        defaultPodId={selectedPodId !== 'all' ? selectedPodId : undefined}
      />

      {/* Pod Modal (Create / Edit) */}
      <PodModal
        isOpen={isPodModalOpen}
        onClose={() => {
          setIsPodModalOpen(false);
          setSelectedPodForEdit(null);
        }}
        pod={selectedPodForEdit}
      />
    </div>
  );
};
