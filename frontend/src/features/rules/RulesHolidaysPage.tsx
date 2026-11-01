import React, { useState, useMemo } from 'react';
import {
  Plus,
  Sliders,
  Trash2,
  CalendarDays,
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
  useToast,
} from '../../components/ui';
import {
  useCoverageRulesQuery,
  useDeleteCoverageRuleMutation,
  useHolidaysQuery,
  useDeleteHolidayMutation,
} from '../../api/rules';
import { useBrandProcessesQuery } from '../../api/brands';
import { showApiErrorToast } from '../../api/errorMapping';
import { useAuth } from '../auth/AuthContext';
import { useMonth } from '../../context/MonthContext';
import { CoverageRuleModal } from './CoverageRuleModal';
import { HolidayModal } from './HolidayModal';
import type { CoverageRule, Holiday } from '../../types/rules';

const WEEKDAY_NAMES = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

export const RulesHolidaysPage: React.FC = () => {
  const toast = useToast();
  const { isOpsManager, isPodLead } = useAuth();
  const canEdit = isOpsManager || isPodLead;
  const { year, monthIndex, monthLabel } = useMonth();

  const [activeTab, setActiveTab] = useState<'rules' | 'holidays'>('rules');

  // Coverage Rules state
  const [selectedBPFilter, setSelectedBPFilter] = useState<string>('all');
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);

  // Holidays state
  const [holidayScopeFilter, setHolidayScopeFilter] = useState<'all' | 'global' | 'brand'>('all');
  const [isHolidayModalOpen, setIsHolidayModalOpen] = useState(false);

  // Queries
  const { data: bpData } = useBrandProcessesQuery({ limit: 100 });

  const {
    data: rulesData,
    isLoading: isRulesLoading,
    isError: isRulesError,
    refetch: refetchRules,
  } = useCoverageRulesQuery({
    brand_process_id: selectedBPFilter !== 'all' ? selectedBPFilter : undefined,
    limit: 100,
  });

  const {
    data: holidaysData,
    isLoading: isHolidaysLoading,
    isError: isHolidaysError,
    refetch: refetchHolidays,
  } = useHolidaysQuery({
    year,
    limit: 100,
  });

  const deleteRuleMutation = useDeleteCoverageRuleMutation();
  const deleteHolidayMutation = useDeleteHolidayMutation();

  // Map brand-process lookup for names
  const bpMap = useMemo(() => {
    const map = new Map<string, { brand: string; process: string }>();
    (bpData?.items || []).forEach((bp) => {
      map.set(bp.id, {
        brand: bp.brand_name || 'Brand',
        process: bp.process_name || 'Process',
      });
    });
    return map;
  }, [bpData]);

  const bpFilterOptions = useMemo(() => {
    const list = [{ value: 'all', label: 'All Capabilities / Brand-Processes' }];
    (bpData?.items || []).forEach((bp) => {
      list.push({
        value: bp.id,
        label: `${bp.brand_name} — ${bp.process_name} (${bp.brand_code || ''})`,
      });
    });
    return list;
  }, [bpData]);

  // Filtered holidays
  const filteredHolidays = useMemo(() => {
    if (!holidaysData?.items) return [];
    if (holidayScopeFilter === 'global') {
      return holidaysData.items.filter((h) => !h.brand_id);
    }
    if (holidayScopeFilter === 'brand') {
      return holidaysData.items.filter((h) => !!h.brand_id);
    }
    return holidaysData.items;
  }, [holidaysData, holidayScopeFilter]);

  // Calendar matrix calculation for current month
  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, monthIndex, 1).getDay(); // 0 is Sunday
    // Adjust to Monday = 0
    const startWeekday = firstDay === 0 ? 6 : firstDay - 1;
    const daysInCurrentMonth = new Date(year, monthIndex + 1, 0).getDate();

    const days: Array<{
      dayNum: number | null;
      dateStr: string | null;
      holidays: Holiday[];
    }> = [];

    // Empty cells before month start
    for (let i = 0; i < startWeekday; i++) {
      days.push({ dayNum: null, dateStr: null, holidays: [] });
    }

    // Days in month
    for (let d = 1; d <= daysInCurrentMonth; d++) {
      const mm = String(monthIndex + 1).padStart(2, '0');
      const dd = String(d).padStart(2, '0');
      const dateStr = `${year}-${mm}-${dd}`;
      const matchingHolidays = (holidaysData?.items || []).filter((h) => h.date === dateStr);
      days.push({ dayNum: d, dateStr, holidays: matchingHolidays });
    }

    return days;
  }, [year, monthIndex, holidaysData]);

  const handleDeleteRule = async (rule: CoverageRule) => {
    try {
      await deleteRuleMutation.mutateAsync(rule.id);
      toast.success('Rule deleted', 'Coverage override rule was removed.');
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete rule');
    }
  };

  const handleDeleteHoliday = async (h: Holiday) => {
    try {
      await deleteHolidayMutation.mutateAsync(h.id);
      toast.success('Holiday deleted', `"${h.name}" was removed.`);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to delete holiday');
    }
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* Page Title & Primary Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink flex items-center gap-2">
            <Sliders className="h-5 w-5 text-accent-600" />
            Rules & Holidays
          </h1>
          <p className="text-xs text-ink-2">
            Manage weekday/date staffing overrides and company/brand public holiday calendars.
          </p>
        </div>

        {canEdit && (
          <div className="flex items-center gap-2">
            {activeTab === 'rules' ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsRuleModalOpen(true)}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Add Coverage Rule
              </Button>
            ) : (
              isOpsManager && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsHolidayModalOpen(true)}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add Holiday
                </Button>
              )
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab('rules')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'rules'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Sliders className="h-3.5 w-3.5" />
          <span>Coverage Rules ({rulesData?.total ?? 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('holidays')}
          className={`pb-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'holidays'
              ? 'border-accent-600 font-semibold text-accent-700'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <CalendarDays className="h-3.5 w-3.5" />
          <span>Holiday Calendar ({holidaysData?.total ?? 0})</span>
        </button>
      </div>

      {/* TAB 1: COVERAGE RULES */}
      {activeTab === 'rules' && (
        <div className="space-y-3.5">
          {/* Capability filter */}
          <div className="bg-surface p-3 rounded-ctl border border-border shadow-xs max-w-md">
            <Select
              label="Filter by Capability"
              value={selectedBPFilter}
              options={bpFilterOptions}
              onChange={setSelectedBPFilter}
            />
          </div>

          {/* Rules Table */}
          {isRulesLoading ? (
            <div className="space-y-2 bg-surface p-4 rounded-ctl border border-border">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : isRulesError ? (
            <div className="rounded-ctl border border-bad/30 bg-bad/10 p-6 text-center space-y-2">
              <AlertCircle className="mx-auto h-6 w-6 text-bad" />
              <p className="text-xs font-semibold text-bad">Failed to load coverage rules</p>
              <Button variant="secondary" size="sm" onClick={() => refetchRules()}>
                Retry
              </Button>
            </div>
          ) : !rulesData?.items || rulesData.items.length === 0 ? (
            <div className="bg-surface p-8 rounded-ctl border border-border">
              <EmptyState
                title="No Coverage Rules Defined"
                description="Coverage rules define minimum staffing overrides for high-volume weekdays or target promotional dates."
                actionLabel={canEdit ? 'Add Coverage Rule' : undefined}
                onAction={() => setIsRuleModalOpen(true)}
              />
            </div>
          ) : (
            <Table dense>
              <TableHeader>
                <TableRow>
                  <TableHead>Brand & Process</TableHead>
                  <TableHead>Schedule / Date</TableHead>
                  <TableHead className="text-center">Min Staff</TableHead>
                  <TableHead>Explanatory Rule Preview</TableHead>
                  <TableHead>Operational Reason</TableHead>
                  <TableHead>Status</TableHead>
                  {canEdit && <TableHead className="text-right w-16">Action</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rulesData.items.map((rule) => {
                  const bp = bpMap.get(rule.brand_process_id);
                  const bpName = bp ? `${bp.brand} — ${bp.process}` : 'Process Capability';
                  const scheduleLabel =
                    rule.weekday !== null
                      ? `Every ${WEEKDAY_NAMES[rule.weekday]}`
                      : rule.specific_date || 'Date';
                  const preview =
                    rule.weekday !== null
                      ? `Min ${rule.min_staff} on ${WEEKDAY_NAMES[rule.weekday]}s`
                      : `Min ${rule.min_staff} on ${rule.specific_date}`;

                  return (
                    <TableRow key={rule.id}>
                      <TableCell className="font-medium text-ink">{bpName}</TableCell>
                      <TableCell>
                        <span className="font-mono text-xs text-ink font-semibold">
                          {scheduleLabel}
                        </span>
                      </TableCell>
                      <TableCell className="text-center font-mono font-bold text-accent-700">
                        {rule.min_staff}
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center rounded-ctl bg-accent-50 text-accent-700 px-2 py-0.5 text-xs font-mono border border-accent-100">
                          {preview}
                        </span>
                      </TableCell>
                      <TableCell className="text-ink-3 italic">
                        {rule.reason || 'Standard operational requirement'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={rule.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      {canEdit && (
                        <TableCell className="text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteRule(rule)}
                            title="Delete rule"
                            className="text-ink-3 hover:text-bad p-1 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      )}

      {/* TAB 2: HOLIDAY CALENDAR */}
      {activeTab === 'holidays' && (
        <div className="space-y-4">
          {/* Controls bar: Scope Filter + Month Indicator */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-surface p-3 rounded-ctl border border-border shadow-xs">
            <div className="flex items-center gap-1.5 text-xs font-medium">
              <span className="text-ink-3 mr-1">Scope:</span>
              <button
                type="button"
                onClick={() => setHolidayScopeFilter('all')}
                className={`rounded-ctl px-2.5 py-1 transition-colors ${
                  holidayScopeFilter === 'all'
                    ? 'bg-accent-600 text-white font-semibold'
                    : 'bg-surface-2 text-ink-2 hover:bg-border'
                }`}
              >
                All Holidays
              </button>
              <button
                type="button"
                onClick={() => setHolidayScopeFilter('global')}
                className={`rounded-ctl px-2.5 py-1 transition-colors ${
                  holidayScopeFilter === 'global'
                    ? 'bg-accent-600 text-white font-semibold'
                    : 'bg-surface-2 text-ink-2 hover:bg-border'
                }`}
              >
                Global Only
              </button>
              <button
                type="button"
                onClick={() => setHolidayScopeFilter('brand')}
                className={`rounded-ctl px-2.5 py-1 transition-colors ${
                  holidayScopeFilter === 'brand'
                    ? 'bg-accent-600 text-white font-semibold'
                    : 'bg-surface-2 text-ink-2 hover:bg-border'
                }`}
              >
                Brand-Specific
              </button>
            </div>

            <div className="text-xs font-mono font-medium text-ink bg-surface-2 px-3 py-1 rounded-ctl border border-border">
              {monthLabel} (Year {year})
            </div>
          </div>

          {/* Month Calendar Grid View */}
          <div className="rounded-ctl border border-border bg-surface overflow-hidden shadow-xs">
            <div className="p-3 border-b border-border bg-surface-2/60 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">
                {monthLabel} Holiday View
              </h3>
              <span className="text-[11px] text-ink-3">
                Public holidays grant compensatory off credits when worked (HW)
              </span>
            </div>

            <div className="grid grid-cols-7 border-b border-border bg-surface-2 text-center text-[11px] font-semibold text-ink-2">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                <div key={day} className="py-2 border-r border-border last:border-r-0">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 divide-y divide-border bg-border">
              {calendarDays.map((cell, idx) => {
                const hasHoliday = cell.holidays.length > 0;
                return (
                  <div
                    key={idx}
                    className={`min-h-[78px] p-2 bg-surface transition-colors ${
                      hasHoliday ? 'bg-warn/5' : ''
                    }`}
                  >
                    {cell.dayNum !== null && (
                      <div className="flex flex-col h-full justify-between">
                        <span
                          className={`font-mono text-xs font-semibold ${
                            hasHoliday ? 'text-warn' : 'text-ink-2'
                          }`}
                        >
                          {cell.dayNum}
                        </span>

                        {cell.holidays.map((h) => (
                          <div
                            key={h.id}
                            className="mt-1 rounded-chip border border-warn/30 bg-[#FBF0D9] p-1 text-[10px] leading-tight text-ink"
                            title={`${h.name} (${h.brand_name || 'Global'})`}
                          >
                            <p className="font-semibold text-warn truncate">{h.name}</p>
                            <p className="text-[9px] text-ink-3 truncate">
                              {h.brand_name ? `Brand: ${h.brand_name}` : 'Global'}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Holidays List Table */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">
              Official Holidays in {year} ({filteredHolidays.length})
            </h3>

            {isHolidaysLoading ? (
              <div className="p-4 space-y-2 bg-surface rounded-ctl border border-border">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : isHolidaysError ? (
              <div className="rounded-ctl border border-bad/30 bg-bad/10 p-6 text-center">
                <p className="text-xs font-semibold text-bad">Failed to load holidays</p>
                <Button variant="secondary" size="sm" onClick={() => refetchHolidays()}>
                  Retry
                </Button>
              </div>
            ) : filteredHolidays.length === 0 ? (
              <div className="bg-surface p-6 rounded-ctl border border-border text-center text-xs text-ink-3">
                No holidays recorded for {year} under selected scope.
              </div>
            ) : (
              <Table dense>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Holiday Name</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Status</TableHead>
                    {isOpsManager && <TableHead className="text-right w-16">Action</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredHolidays.map((h) => (
                    <TableRow key={h.id}>
                      <TableCell className="font-mono text-xs font-semibold text-ink">
                        {h.date}
                      </TableCell>
                      <TableCell className="font-medium text-ink">{h.name}</TableCell>
                      <TableCell>
                        {h.brand_name ? (
                          <Badge variant="INFO" size="sm">
                            Brand: {h.brand_name}
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Global (All Brands)
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={h.is_active ? 'SUCCESS' : 'neutral'} size="sm">
                          {h.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      {isOpsManager && (
                        <TableCell className="text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteHoliday(h)}
                            title="Delete holiday"
                            className="text-ink-3 hover:text-bad p-1 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      )}

      {/* Coverage Rule Modal */}
      <CoverageRuleModal
        isOpen={isRuleModalOpen}
        onClose={() => setIsRuleModalOpen(false)}
        defaultBrandProcessId={selectedBPFilter !== 'all' ? selectedBPFilter : undefined}
      />

      {/* Holiday Modal */}
      <HolidayModal
        isOpen={isHolidayModalOpen}
        onClose={() => setIsHolidayModalOpen(false)}
        defaultDate={`${year}-${String(monthIndex + 1).padStart(2, '0')}-01`}
      />
    </div>
  );
};
