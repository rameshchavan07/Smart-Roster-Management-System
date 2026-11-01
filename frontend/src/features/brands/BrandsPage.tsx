import React, { useState, useMemo } from 'react';
import {
  Briefcase,
  Search,
  Plus,
  AlertTriangle,
  UserPlus,
  Trash2,
  Calendar,
  Layers,
  Edit2,
} from 'lucide-react';
import {
  Button,
  Select,
  Badge,
  Skeleton,
  EmptyState,
  useToast,
} from '../../components/ui';
import {
  useBrandsQuery,
  useBrandProcessesQuery,
  useAssignmentsQuery,
  useDeleteAssignmentMutation,
  useDeleteBrandMutation,
  useDeleteBrandProcessMutation,
} from '../../api/brands';
import { usePodsQuery } from '../../api/team';
import { showApiErrorToast } from '../../api/errorMapping';
import { useAuth } from '../auth/AuthContext';
import { BrandModal } from './BrandModal';
import { BrandProcessModal } from './BrandProcessModal';
import { AssignmentModal } from './AssignmentModal';
import type { Brand, BrandProcess } from '../../types/brands';
import type { Assignment } from '../../types/team';

export const BrandsPage: React.FC = () => {
  const toast = useToast();
  const { isOpsManager, isPodLead } = useAuth();
  const canEdit = isOpsManager || isPodLead;

  // Selected Brand state
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPodId, setSelectedPodId] = useState<string>('all');

  // Modals state
  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [brandForEdit, setBrandForEdit] = useState<Brand | null>(null);
  const [isProcessModalOpen, setIsProcessModalOpen] = useState(false);
  const [assignmentModalTarget, setAssignmentModalTarget] = useState<BrandProcess | null>(null);

  // Queries
  const { data: podsData } = usePodsQuery();
  const { data: brandsData, isLoading: isBrandsLoading } = useBrandsQuery({
    pod_id: selectedPodId !== 'all' ? selectedPodId : undefined,
    limit: 100,
  });

  const { data: brandProcessesData, isLoading: isBPLoading } = useBrandProcessesQuery({
    brand_id: selectedBrandId || undefined,
    limit: 100,
  });

  const { data: assignmentsData } = useAssignmentsQuery({
    limit: 300,
  });

  const deleteAssignmentMutation = useDeleteAssignmentMutation();
  const deleteBrandMutation = useDeleteBrandMutation();
  const deleteBPMutation = useDeleteBrandProcessMutation();

  const handleDeleteBrand = async () => {
    if (!activeBrand) return;
    if (!window.confirm(`Are you sure you want to delete brand "${activeBrand.name}"?`)) return;
    try {
      await deleteBrandMutation.mutateAsync(activeBrand.id);
      toast.success('Brand deleted', `Brand "${activeBrand.name}" was removed.`);
      setSelectedBrandId(null);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete brand');
    }
  };

  const handleDeleteBP = async (bp: BrandProcess) => {
    if (!window.confirm(`Are you sure you want to remove process "${bp.process_name || 'Process'}" from ${activeBrand?.name}?`)) return;
    try {
      await deleteBPMutation.mutateAsync(bp.id);
      toast.success('Process removed', `Process removed from ${activeBrand?.name}.`);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to remove process');
    }
  };

  // Filtered brands
  const filteredBrands = useMemo(() => {
    if (!brandsData?.items) return [];
    if (!searchQuery.trim()) return brandsData.items;

    const lower = searchQuery.toLowerCase();
    return brandsData.items.filter(
      (b) =>
        b.name.toLowerCase().includes(lower) ||
        b.code.toLowerCase().includes(lower) ||
        (b.pod_name && b.pod_name.toLowerCase().includes(lower))
    );
  }, [brandsData, searchQuery]);

  // Default selection to first brand once loaded
  const activeBrand = useMemo(() => {
    if (!filteredBrands || filteredBrands.length === 0) return null;
    if (selectedBrandId) {
      const found = filteredBrands.find((b) => b.id === selectedBrandId);
      if (found) return found;
    }
    return filteredBrands[0];
  }, [filteredBrands, selectedBrandId]);

  // Group assignments by brand_process_id
  const assignmentsByBP = useMemo(() => {
    const map = new Map<string, Assignment[]>();
    (assignmentsData?.items || []).forEach((asgn) => {
      const existing = map.get(asgn.brand_process_id) || [];
      existing.push(asgn);
      map.set(asgn.brand_process_id, existing);
    });
    return map;
  }, [assignmentsData]);

  const podFilterOptions = useMemo(() => {
    const list = [{ value: 'all', label: 'All Pods' }];
    if (podsData?.items) {
      podsData.items.forEach((p) => {
        list.push({ value: p.id, label: p.name });
      });
    }
    return list;
  }, [podsData]);

  const handleRemoveAssignment = async (asgn: Assignment) => {
    try {
      await deleteAssignmentMutation.mutateAsync(asgn.id);
      toast.success(
        'Assignment removed',
        `Staff assignment for ${asgn.employee_name || 'Employee'} removed.`
      );
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete assignment');
    }
  };

  const formatCalendarLabel = (calType: string) => {
    switch (calType) {
      case 'ALL_365':
        return '365 Days (All Week)';
      case 'SIX_DAYS_MON_SAT':
        return '6 Days (Mon–Sat)';
      case 'SIX_DAYS_TUE_SUN':
        return '6 Days (Tue–Sun)';
      case 'FIVE_DAYS_MON_FRI':
        return '5 Days (Mon–Fri)';
      default:
        return calType.replace(/_/g, ' ');
    }
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-accent-600" />
            Brands & Processes
          </h1>
          <p className="text-xs text-ink-2">
            Configure client brand portfolios, operating calendar types, and staff assignments.
          </p>
        </div>

        {canEdit && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setBrandForEdit(null);
              setIsBrandModalOpen(true);
            }}
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Create Brand
          </Button>
        )}
      </div>

      {/* Master-Detail Container */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
        {/* LEFT MASTER LIST (4 cols) */}
        <div className="md:col-span-4 rounded-ctl border border-border bg-surface overflow-hidden shadow-xs">
          {/* List Search & Filter */}
          <div className="p-3 border-b border-border space-y-2 bg-surface-2/40">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-3" />
              <input
                type="text"
                placeholder="Search brands or codes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 w-full rounded-ctl border border-border-strong bg-surface pl-8 pr-3 text-xs text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent-600 focus:ring-1 focus:ring-accent-600"
              />
            </div>
            <Select
              value={selectedPodId}
              onChange={setSelectedPodId}
              options={podFilterOptions}
            />
          </div>

          {/* Brands List */}
          <div className="max-h-[640px] overflow-y-auto divide-y divide-border">
            {isBrandsLoading ? (
              <div className="p-4 space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : filteredBrands.length === 0 ? (
              <div className="p-8 text-center text-xs text-ink-3">
                No matching brands found.
              </div>
            ) : (
              filteredBrands.map((brand) => {
                const isSelected = activeBrand?.id === brand.id;
                return (
                  <div
                    key={brand.id}
                    onClick={() => setSelectedBrandId(brand.id)}
                    className={`p-3.5 cursor-pointer transition-colors flex items-center justify-between ${
                      isSelected
                        ? 'bg-accent-50/70 border-l-3 border-accent-600'
                        : 'hover:bg-surface-2/70'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-ink leading-tight">
                          {brand.name}
                        </span>
                        <span className="font-mono text-[10px] text-ink-3 bg-surface-2 px-1.5 py-0.2 rounded">
                          {brand.code}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-3 mt-1">
                        {brand.pod_name ? `Assigned to ${brand.pod_name}` : 'Company-wide'}
                      </p>
                    </div>

                    <Badge variant={brand.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                      {brand.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT DETAIL PANEL (8 cols) */}
        <div className="md:col-span-8 rounded-ctl border border-border bg-surface p-5 shadow-xs space-y-5">
          {!activeBrand ? (
            <EmptyState
              title="No Brand Selected"
              description="Select a brand from the list on the left to view and configure its operational processes and staffing."
            />
          ) : (
            <>
              {/* Brand Detail Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-border gap-3">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-lg font-semibold text-ink leading-tight">
                      {activeBrand.name}
                    </h2>
                    <span className="font-mono text-xs font-semibold text-accent-700 bg-accent-100 px-2 py-0.5 rounded-chip">
                      {activeBrand.code}
                    </span>
                    <Badge variant={activeBrand.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                      {activeBrand.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <p className="text-xs text-ink-3 mt-1">
                    Managing Pod:{' '}
                    <span className="font-medium text-ink">
                      {activeBrand.pod_name || 'Unassigned / Company-wide'}
                    </span>
                  </p>
                </div>

                {canEdit && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setBrandForEdit(activeBrand);
                        setIsBrandModalOpen(true);
                      }}
                    >
                      <Edit2 className="h-3 w-3 mr-1" />
                      Edit Brand
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsProcessModalOpen(true)}
                    >
                      <Plus className="h-3.5 w-3.5 mr-1" />
                      Add Process
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleDeleteBrand}
                      isLoading={deleteBrandMutation.isPending}
                      title="Delete brand (requires 0 active rosters)"
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      Delete
                    </Button>
                  </div>
                )}
              </div>

              {/* Brand Processes List */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3 flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-accent-600" />
                    Operational Capabilities & Processes ({brandProcessesData?.items?.length ?? 0})
                  </h3>
                </div>

                {isBPLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-28 rounded-ctl" />
                    <Skeleton className="h-28 rounded-ctl" />
                  </div>
                ) : !brandProcessesData?.items || brandProcessesData.items.length === 0 ? (
                  <div className="rounded-ctl border border-dashed border-border p-8 text-center space-y-2">
                    <Briefcase className="mx-auto h-6 w-6 text-ink-3 opacity-60" />
                    <p className="text-xs font-medium text-ink">
                      No processes configured for {activeBrand.name}
                    </p>
                    <p className="text-[11px] text-ink-3">
                      Instantiate Customer Support, Accounting, or other capabilities to schedule staff.
                    </p>
                    {canEdit && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setIsProcessModalOpen(true)}
                        className="mt-2"
                      >
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        Add First Process
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3.5">
                    {brandProcessesData.items.map((bp) => {
                      const assignments = assignmentsByBP.get(bp.id) || [];
                      const primaryCount = assignments.filter(
                        (a) => a.assignment_type === 'PRIMARY'
                      ).length;
                      const backupCount = assignments.filter(
                        (a) => a.assignment_type === 'BACKUP'
                      ).length;
                      const totalStaff = assignments.length;
                      const isSinglePoint = totalStaff <= 1;

                      return (
                        <div
                          key={bp.id}
                          className="rounded-ctl border border-border bg-surface p-4 space-y-3.5 hover:border-border-strong transition-colors shadow-xs"
                        >
                          {/* Process Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-xs text-ink">
                                  {bp.process_name || 'Operational Process'}
                                </span>
                                {bp.process_code && (
                                  <span className="font-mono text-[10px] text-ink-3 bg-surface-2 px-1.5 py-0.5 rounded">
                                    {bp.process_code}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 mt-1 text-[11px] text-ink-3">
                                <span className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3 text-ink-3" />
                                  {formatCalendarLabel(bp.calendar_type)}
                                </span>
                                <span>•</span>
                                <span className="font-mono">
                                  Default Min: {bp.min_coverage_default} staff/day
                                </span>
                              </div>
                            </div>

                            {/* Single Point of Resource Flag */}
                            <div className="flex items-center gap-2">
                              {isSinglePoint && (
                                <Badge
                                  variant="WARNING"
                                  size="sm"
                                  icon={<AlertTriangle className="h-3 w-3" />}
                                >
                                  Single Point of Resource ({totalStaff} Staff)
                                </Badge>
                              )}
                              {canEdit && (
                                <>
                                  <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setAssignmentModalTarget(bp)}
                                    className="h-7 text-xs"
                                  >
                                    <UserPlus className="h-3 w-3 mr-1" />
                                    Assign Staff
                                  </Button>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteBP(bp)}
                                    className="text-ink-3 hover:text-bad p-1 rounded transition-colors"
                                    title="Remove process from brand"
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </button>
                                </>
                              )}
                            </div>
                          </div>

                          {/* Assigned Staff Chips */}
                          <div className="pt-2 border-t border-border">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-3 mb-2">
                              Assigned Workforce ({primaryCount} Primary, {backupCount} Backup)
                            </p>

                            {assignments.length === 0 ? (
                              <p className="text-xs text-bad italic">
                                ⚠ No employees currently assigned to this process.
                              </p>
                            ) : (
                              <div className="flex flex-wrap gap-2">
                                {assignments.map((asgn) => (
                                  <div
                                    key={asgn.id}
                                    className="inline-flex items-center gap-1.5 rounded-ctl border border-border bg-surface-2/70 px-2.5 py-1 text-xs"
                                  >
                                    <span className="font-medium text-ink">
                                      {asgn.employee_name || 'Staff Member'}
                                    </span>
                                    {asgn.employee_code && (
                                      <span className="font-mono text-[10px] text-ink-3">
                                        ({asgn.employee_code})
                                      </span>
                                    )}
                                    <Badge
                                      variant={
                                        asgn.assignment_type === 'PRIMARY' ? 'SUCCESS' : 'INFO'
                                      }
                                      size="sm"
                                      className="text-[9px] px-1 py-0"
                                    >
                                      {asgn.assignment_type}
                                    </Badge>

                                    {canEdit && (
                                      <button
                                        type="button"
                                        onClick={() => handleRemoveAssignment(asgn)}
                                        title="Remove assignment"
                                        className="text-ink-3 hover:text-bad ml-1 transition-colors"
                                      >
                                        <Trash2 className="h-3 w-3" />
                                      </button>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Brand Create/Edit Modal */}
      <BrandModal
        isOpen={isBrandModalOpen}
        onClose={() => {
          setIsBrandModalOpen(false);
          setBrandForEdit(null);
        }}
        brand={brandForEdit}
        defaultPodId={selectedPodId !== 'all' ? selectedPodId : undefined}
      />

      {/* Brand Process Modal */}
      {activeBrand && (
        <BrandProcessModal
          isOpen={isProcessModalOpen}
          onClose={() => setIsProcessModalOpen(false)}
          brandId={activeBrand.id}
          brandName={activeBrand.name}
        />
      )}

      {/* Assignment Modal */}
      {assignmentModalTarget && (
        <AssignmentModal
          isOpen={!!assignmentModalTarget}
          onClose={() => setAssignmentModalTarget(null)}
          brandProcessId={assignmentModalTarget.id}
          brandName={assignmentModalTarget.brand_name || activeBrand?.name}
          processName={assignmentModalTarget.process_name || undefined}
        />
      )}
    </div>
  );
};
