import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  GitCompare,
  Download,
  FileSpreadsheet,
  FileText,
  Calendar,
  Layers,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  AlertOctagon,
  ArrowUpDown,
  Search,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  Button,
  Badge,
  Select,
  EmptyState,
  Skeleton,
  StatusCell,
  useToast,
} from '../../components/ui';
import {
  useRosterPeriodsQuery,
  useCompareRostersQuery,
  downloadRosterExport,
} from '../../api/rosters';
import { useMonth } from '../../context/MonthContext';
import { mapStatusToCode } from '../../types/roster';

type ReportsTab = 'compare' | 'export';
type ConflictDiffTab = 'all' | 'new' | 'resolved' | 'common';

export const ReportsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentMonth, monthLabel } = useMonth();
  const { success, error: toastError } = useToast();

  const tabParam = (searchParams.get('tab') as ReportsTab) || 'compare';
  const [activeTab, setActiveTab] = useState<ReportsTab>(
    tabParam === 'export' ? 'export' : 'compare'
  );

  // Sync tab with URL
  const handleTabChange = (tab: ReportsTab) => {
    setActiveTab(tab);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', tab);
      return next;
    });
  };

  // Fetch roster periods for the active month
  const {
    data: periods = [],
    refetch: refetchPeriods,
  } = useRosterPeriodsQuery(currentMonth);

  // Compare version IDs
  const paramA = searchParams.get('a');
  const paramB = searchParams.get('b');

  const [periodIdA, setPeriodIdA] = useState<string>('');
  const [periodIdB, setPeriodIdB] = useState<string>('');

  // Auto-select periods when loaded
  useEffect(() => {
    if (periods.length >= 2) {
      const validA = periods.find((p) => p.id === paramA);
      const validB = periods.find((p) => p.id === paramB);

      if (validA && validB && validA.id !== validB.id) {
        setPeriodIdA(validA.id);
        setPeriodIdB(validB.id);
      } else {
        const sorted = [...periods].sort((x, y) => x.version - y.version);
        setPeriodIdA(sorted[0].id);
        setPeriodIdB(sorted[sorted.length - 1].id);
      }
    } else if (periods.length === 1) {
      setPeriodIdA(periods[0].id);
      setPeriodIdB('');
    }
  }, [periods, paramA, paramB]);

  // Update URL search params when compare selections change
  const handleSelectA = (id: string) => {
    setPeriodIdA(id);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (id) next.set('a', id);
      else next.delete('a');
      return next;
    });
  };

  const handleSelectB = (id: string) => {
    setPeriodIdB(id);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (id) next.set('b', id);
      else next.delete('b');
      return next;
    });
  };

  const handleSwapVersions = () => {
    const temp = periodIdA;
    setPeriodIdA(periodIdB);
    setPeriodIdB(temp);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (periodIdB) next.set('a', periodIdB);
      if (temp) next.set('b', temp);
      return next;
    });
  };

  // Query backend comparison
  const {
    data: compareData,
    isLoading: isLoadingCompare,
    refetch: refetchCompare,
  } = useCompareRostersQuery(periodIdA, periodIdB);

  // Period Options for dropdowns
  const periodOptions = useMemo(() => {
    return periods.map((p) => ({
      value: p.id,
      label: `v${p.version} · Version ${p.version} (${p.status})`,
    }));
  }, [periods]);

  // Cell diff filtering
  const [cellSearch, setCellSearch] = useState<string>('');
  const [conflictDiffTab, setConflictDiffTab] = useState<ConflictDiffTab>('all');

  const filteredCellDiffs = useMemo(() => {
    if (!compareData?.cell_diffs) return [];
    const query = cellSearch.trim().toLowerCase();
    if (!query) return compareData.cell_diffs;
    return compareData.cell_diffs.filter(
      (item) =>
        item.employee_name.toLowerCase().includes(query) ||
        item.employee_code.toLowerCase().includes(query) ||
        item.date.includes(query)
    );
  }, [compareData?.cell_diffs, cellSearch]);

  // Export State
  const [exportPeriodId, setExportPeriodId] = useState<string>(
    periodIdB || periodIdA || (periods[0]?.id ?? '')
  );
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx'>('csv');
  const [exportDate, setExportDate] = useState<string>(
    periods[0]?.month || new Date().toISOString().slice(0, 10)
  );
  const [isExporting, setIsExporting] = useState<string | null>(null);

  useEffect(() => {
    if (periodIdB) setExportPeriodId(periodIdB);
    else if (periodIdA) setExportPeriodId(periodIdA);
    else if (periods[0]?.id) setExportPeriodId(periods[0].id);
  }, [periodIdA, periodIdB, periods]);

  const handleDownload = async (view: 'grid' | 'day' | 'coverage' | 'conflicts') => {
    if (!exportPeriodId) {
      toastError('Export Error', 'Please select a roster version to export.');
      return;
    }
    setIsExporting(view);
    try {
      const filename = await downloadRosterExport(
        exportPeriodId,
        exportFormat,
        view,
        view === 'day' ? exportDate : undefined
      );
      success('Export Completed', `Successfully downloaded ${filename}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to export file';
      toastError('Export Failed', msg);
    } finally {
      setIsExporting(null);
    }
  };

  const selectedExportPeriod = useMemo(() => {
    return periods.find((p) => p.id === exportPeriodId);
  }, [periods, exportPeriodId]);

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-ink">Reports & Export</h1>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-accent-100 text-accent-800">
              {monthLabel}
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            Compare roster versions side-by-side, inspect operational deltas, and export official schedules.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center bg-surface-muted p-1 rounded-ctl border border-border">
          <button
            type="button"
            onClick={() => handleTabChange('compare')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-ctl transition-colors ${
              activeTab === 'compare'
                ? 'bg-surface text-ink shadow-sm'
                : 'text-muted hover:text-ink'
            }`}
          >
            <GitCompare className="w-3.5 h-3.5 text-accent-700" />
            <span>Version Compare</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('export')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-ctl transition-colors ${
              activeTab === 'export'
                ? 'bg-surface text-ink shadow-sm'
                : 'text-muted hover:text-ink'
            }`}
          >
            <Download className="w-3.5 h-3.5 text-accent-700" />
            <span>Export Center</span>
          </button>
        </div>
      </div>

      {/* TAB 1: VERSION COMPARE VIEW */}
      {activeTab === 'compare' && (
        <div className="space-y-6">
          {/* Version Selectors Bar */}
          <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                {/* Version A Selector */}
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Baseline Version (A)
                  </label>
                  <Select
                    value={periodIdA}
                    onChange={(val) => handleSelectA(val)}
                    options={[
                      { value: '', label: 'Select Baseline Version...' },
                      ...periodOptions,
                    ]}
                    className="text-xs font-medium"
                  />
                </div>

                {/* Swap button on desktop */}
                <div className="flex items-center space-x-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleSwapVersions}
                    disabled={!periodIdA || !periodIdB}
                    title="Swap Version A and B"
                    className="mt-5 shrink-0"
                  >
                    <ArrowUpDown className="w-3.5 h-3.5 rotate-90" />
                  </Button>

                  {/* Version B Selector */}
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-muted mb-1">
                      Comparison Version (B)
                    </label>
                    <Select
                      value={periodIdB}
                      onChange={(val) => handleSelectB(val)}
                      options={[
                        { value: '', label: 'Select Comparison Version...' },
                        ...periodOptions,
                      ]}
                      className="text-xs font-medium"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    refetchPeriods();
                    refetchCompare();
                  }}
                  title="Refresh version comparisons"
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  Refresh
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/roster')}
                  title="Open Roster Workspace"
                >
                  <ExternalLink className="w-3.5 h-3.5 mr-1" />
                  Workspace
                </Button>
              </div>
            </div>

            {/* Validation warning if same version selected */}
            {periodIdA && periodIdB && periodIdA === periodIdB && (
              <div className="mt-3 p-2 bg-warn/10 border border-warn/30 rounded-ctl text-xs text-ink flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-warn shrink-0" />
                <span>
                  Please select two different roster versions to view differences and delta metrics.
                </span>
              </div>
            )}
          </div>

          {/* Loading or Empty State */}
          {isLoadingCompare && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 rounded-card" />
                ))}
              </div>
              <Skeleton className="h-64 rounded-card" />
            </div>
          )}

          {!isLoadingCompare && (!periodIdA || !periodIdB || periodIdA === periodIdB) && (
            <div className="bg-surface rounded-card border border-border p-8">
              <EmptyState
                title="Select Two Versions to Compare"
                description={
                  periods.length < 2
                    ? 'You have fewer than two roster versions for this month. Generate a new version in the Roster Workspace to compare.'
                    : 'Choose a Baseline Version (A) and a Comparison Version (B) from the selectors above to see side-by-side metric deltas and cell modifications.'
                }
                actionLabel={periods.length < 2 ? 'Go to Roster Workspace' : undefined}
                onAction={periods.length < 2 ? () => navigate('/roster') : undefined}
              />
            </div>
          )}

          {/* Compare Content */}
          {!isLoadingCompare && compareData && periodIdA !== periodIdB && (
            <div className="space-y-6">
              {/* 1. Side-by-Side KPI Cards with Delta Indicators */}
              <div>
                <h2 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
                  Key Metric Comparisons (Version A vs Version B)
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                  {/* Blocking Conflicts */}
                  <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
                    <div className="flex items-center justify-between text-muted text-xs">
                      <span className="font-medium">Blocking Violations</span>
                      <ShieldAlert className="w-4 h-4 text-warn" />
                    </div>
                    <div className="flex items-baseline justify-between mt-2">
                      <div className="text-lg font-bold text-ink">
                        {compareData.metrics_b.blocking_count}
                        <span className="text-xs font-normal text-muted ml-1.5">
                          vs {compareData.metrics_a.blocking_count}
                        </span>
                      </div>
                      <Badge
                        variant={
                          compareData.delta.blocking_delta > 0
                            ? 'WARNING'
                            : compareData.delta.blocking_delta < 0
                            ? 'SUCCESS'
                            : 'neutral'
                        }
                      >
                        {compareData.delta.blocking_delta > 0 ? `+${compareData.delta.blocking_delta}` : compareData.delta.blocking_delta}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">
                      {compareData.delta.blocking_delta < 0
                        ? 'Improved: fewer blocking conflicts'
                        : compareData.delta.blocking_delta > 0
                        ? 'Regressed: more blocking conflicts'
                        : 'Unchanged'}
                    </div>
                  </div>

                  {/* Warnings Count */}
                  <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
                    <div className="flex items-center justify-between text-muted text-xs">
                      <span className="font-medium">Warning Conflicts</span>
                      <AlertTriangle className="w-4 h-4 text-warn" />
                    </div>
                    <div className="flex items-baseline justify-between mt-2">
                      <div className="text-lg font-bold text-ink">
                        {compareData.metrics_b.warnings_count}
                        <span className="text-xs font-normal text-muted ml-1.5">
                          vs {compareData.metrics_a.warnings_count}
                        </span>
                      </div>
                      <Badge
                        variant={
                          compareData.delta.warnings_delta > 0
                            ? 'WARNING'
                            : compareData.delta.warnings_delta < 0
                            ? 'SUCCESS'
                            : 'neutral'
                        }
                      >
                        {compareData.delta.warnings_delta > 0 ? `+${compareData.delta.warnings_delta}` : compareData.delta.warnings_delta}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">
                      {compareData.delta.warnings_delta < 0 ? 'Fewer soft warnings' : 'Net warning change'}
                    </div>
                  </div>

                  {/* Coverage Percentage */}
                  <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
                    <div className="flex items-center justify-between text-muted text-xs">
                      <span className="font-medium">Coverage Rate</span>
                      <ShieldCheck className="w-4 h-4 text-accent-700" />
                    </div>
                    <div className="flex items-baseline justify-between mt-2">
                      <div className="text-lg font-bold text-ink">
                        {compareData.metrics_b.coverage_pct.toFixed(1)}%
                        <span className="text-xs font-normal text-muted ml-1.5">
                          vs {compareData.metrics_a.coverage_pct.toFixed(1)}%
                        </span>
                      </div>
                      <Badge
                        variant={
                          compareData.delta.coverage_pct_delta > 0
                            ? 'SUCCESS'
                            : compareData.delta.coverage_pct_delta < 0
                            ? 'WARNING'
                            : 'neutral'
                        }
                      >
                        {compareData.delta.coverage_pct_delta > 0
                          ? `+${compareData.delta.coverage_pct_delta.toFixed(1)}%`
                          : `${compareData.delta.coverage_pct_delta.toFixed(1)}%`}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">
                      Headcount shortfall: {compareData.metrics_b.total_shortfall}
                    </div>
                  </div>

                  {/* Fairness Spread */}
                  <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
                    <div className="flex items-center justify-between text-muted text-xs">
                      <span className="font-medium">Weekend Fairness Spread</span>
                      <Layers className="w-4 h-4 text-accent-700" />
                    </div>
                    <div className="flex items-baseline justify-between mt-2">
                      <div className="text-lg font-bold text-ink">
                        {compareData.metrics_b.fairness_spread.toFixed(1)}
                        <span className="text-xs font-normal text-muted ml-1.5">
                          vs {compareData.metrics_a.fairness_spread.toFixed(1)}
                        </span>
                      </div>
                      <Badge
                        variant={
                          compareData.delta.fairness_spread_delta < 0
                            ? 'SUCCESS'
                            : compareData.delta.fairness_spread_delta > 0
                            ? 'WARNING'
                            : 'neutral'
                        }
                      >
                        {compareData.delta.fairness_spread_delta > 0
                          ? `+${compareData.delta.fairness_spread_delta.toFixed(1)}`
                          : compareData.delta.fairness_spread_delta.toFixed(1)}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">
                      Min {compareData.metrics_b.min_weekend_offs} to Max {compareData.metrics_b.max_weekend_offs} offs
                    </div>
                  </div>

                  {/* Modified Cells */}
                  <div className="bg-surface rounded-card border border-border p-4 shadow-sm">
                    <div className="flex items-center justify-between text-muted text-xs">
                      <span className="font-medium">Total Cell Changes</span>
                      <FileSpreadsheet className="w-4 h-4 text-accent-700" />
                    </div>
                    <div className="flex items-baseline justify-between mt-2">
                      <div className="text-lg font-bold text-ink">
                        {compareData.delta.total_cells_changed}
                      </div>
                      <Badge variant="neutral">
                        {compareData.delta.total_cells_changed} shifts
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">
                      Modified between v{compareData.period_a.version} & v{compareData.period_b.version}
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. Conflict Differences Section */}
              <div className="bg-surface rounded-card border border-border overflow-hidden shadow-sm">
                <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">Conflict Status Differences</h3>
                    <p className="text-xs text-muted">
                      Categorized violations between baseline v{compareData.period_a.version} and comparison v{compareData.period_b.version}
                    </p>
                  </div>

                  {/* Filter Tabs */}
                  <div className="flex items-center space-x-1.5 bg-surface-muted p-1 rounded-ctl border border-border text-xs">
                    <button
                      type="button"
                      onClick={() => setConflictDiffTab('all')}
                      className={`px-2.5 py-1 rounded font-medium transition-colors ${
                        conflictDiffTab === 'all'
                          ? 'bg-surface text-ink shadow-sm'
                          : 'text-muted hover:text-ink'
                      }`}
                    >
                      All (
                      {(compareData.conflict_diff.new_in_b?.length || 0) +
                        (compareData.conflict_diff.resolved_in_b?.length || 0) +
                        (compareData.conflict_diff.common?.length || 0)}
                      )
                    </button>
                    <button
                      type="button"
                      onClick={() => setConflictDiffTab('new')}
                      className={`px-2.5 py-1 rounded font-medium transition-colors ${
                        conflictDiffTab === 'new'
                          ? 'bg-surface text-ink shadow-sm'
                          : 'text-muted hover:text-ink'
                      }`}
                    >
                      <span className="text-warn">New in B ({compareData.conflict_diff.new_in_b?.length || 0})</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setConflictDiffTab('resolved')}
                      className={`px-2.5 py-1 rounded font-medium transition-colors ${
                        conflictDiffTab === 'resolved'
                          ? 'bg-surface text-ink shadow-sm'
                          : 'text-muted hover:text-ink'
                      }`}
                    >
                      <span className="text-accent-800">Resolved ({compareData.conflict_diff.resolved_in_b?.length || 0})</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setConflictDiffTab('common')}
                      className={`px-2.5 py-1 rounded font-medium transition-colors ${
                        conflictDiffTab === 'common'
                          ? 'bg-surface text-ink shadow-sm'
                          : 'text-muted hover:text-ink'
                      }`}
                    >
                      Common ({compareData.conflict_diff.common?.length || 0})
                    </button>
                  </div>
                </div>

                {/* Conflict List */}
                <div className="divide-y divide-border max-h-72 overflow-y-auto">
                  {/* New in B */}
                  {(conflictDiffTab === 'all' || conflictDiffTab === 'new') &&
                    compareData.conflict_diff.new_in_b?.map((c) => (
                      <div key={c.id} className="p-3 bg-warn/5 flex items-start space-x-3">
                        <AlertOctagon className="w-4 h-4 text-warn shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-semibold text-warn">{c.code}</span>
                            <Badge variant="WARNING">New in B</Badge>
                            <span className="text-[11px] text-muted font-mono">
                              {c.date_from ? `${c.date_from}${c.date_to ? ` ~ ${c.date_to}` : ''}` : 'Period-wide'}
                            </span>
                          </div>
                          <p className="text-xs text-ink mt-0.5">{c.message}</p>
                        </div>
                      </div>
                    ))}

                  {/* Resolved in B */}
                  {(conflictDiffTab === 'all' || conflictDiffTab === 'resolved') &&
                    compareData.conflict_diff.resolved_in_b?.map((c) => (
                      <div key={c.id} className="p-3 bg-accent-50/40 flex items-start space-x-3">
                        <CheckCircle2 className="w-4 h-4 text-accent-700 shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-semibold text-accent-800">{c.code}</span>
                            <Badge variant="SUCCESS">Resolved in B</Badge>
                            <span className="text-[11px] text-muted font-mono">
                              {c.date_from ? `${c.date_from}${c.date_to ? ` ~ ${c.date_to}` : ''}` : 'Period-wide'}
                            </span>
                          </div>
                          <p className="text-xs text-ink mt-0.5">{c.message}</p>
                        </div>
                      </div>
                    ))}

                  {/* Common */}
                  {(conflictDiffTab === 'all' || conflictDiffTab === 'common') &&
                    compareData.conflict_diff.common?.map((c) => (
                      <div key={c.id} className="p-3 flex items-start space-x-3 hover:bg-surface-muted/30">
                        <AlertTriangle className="w-4 h-4 text-muted shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-semibold text-muted">{c.code}</span>
                            <Badge variant="neutral">Present in Both</Badge>
                            <span className="text-[11px] text-muted font-mono">
                              {c.date_from ? `${c.date_from}${c.date_to ? ` ~ ${c.date_to}` : ''}` : 'Period-wide'}
                            </span>
                          </div>
                          <p className="text-xs text-ink mt-0.5">{c.message}</p>
                        </div>
                      </div>
                    ))}

                  {/* Empty state for conflicts */}
                  {(!compareData.conflict_diff.new_in_b || compareData.conflict_diff.new_in_b.length === 0) &&
                    (!compareData.conflict_diff.resolved_in_b || compareData.conflict_diff.resolved_in_b.length === 0) &&
                    (!compareData.conflict_diff.common || compareData.conflict_diff.common.length === 0) && (
                      <div className="p-6 text-center text-xs text-muted">
                        No integrity conflict differences detected between these two versions.
                      </div>
                    )}
                </div>
              </div>

              {/* 3. Granular Cell-by-Cell Modifications Table */}
              <div className="bg-surface rounded-card border border-border shadow-sm overflow-hidden">
                <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      Granular Cell Modifications ({compareData.cell_diffs.length} total changes)
                    </h3>
                    <p className="text-xs text-muted">
                      Exact shift state transitions for each employee and date.
                    </p>
                  </div>

                  <div className="w-full sm:w-64 relative">
                    <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-2.5 pointer-events-none" />
                    <input
                      type="text"
                      placeholder="Search employee or date..."
                      value={cellSearch}
                      onChange={(e) => setCellSearch(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface border border-border rounded-ctl focus:outline-none focus:ring-1 focus:ring-accent-600"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-muted/50 border-b border-border text-[11px] font-semibold text-muted uppercase tracking-wider">
                        <th className="py-2.5 px-4">Employee</th>
                        <th className="py-2.5 px-4">Date</th>
                        <th className="py-2.5 px-4 text-center">Version A (Baseline)</th>
                        <th className="py-2.5 px-2 text-center w-8"></th>
                        <th className="py-2.5 px-4 text-center">Version B (Comparison)</th>
                        <th className="py-2.5 px-4">Transition Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-xs">
                      {filteredCellDiffs.length > 0 ? (
                        filteredCellDiffs.map((diff, index) => {
                          const codeA = diff.status_a ? mapStatusToCode(diff.status_a) : null;
                          const codeB = diff.status_b ? mapStatusToCode(diff.status_b) : null;

                          return (
                            <tr key={`${diff.employee_id}-${diff.date}-${index}`} className="hover:bg-surface-muted/30">
                              <td className="py-2.5 px-4">
                                <div className="font-medium text-ink">{diff.employee_name}</div>
                                <div className="text-[11px] text-muted font-mono">{diff.employee_code}</div>
                              </td>
                              <td className="py-2.5 px-4 font-mono text-muted text-xs">
                                {diff.date}
                              </td>
                              <td className="py-2.5 px-4 text-center">
                                {codeA ? (
                                  <div className="inline-block">
                                    <StatusCell status={codeA} size="sm" />
                                  </div>
                                ) : (
                                  <span className="text-muted text-[11px]">None</span>
                                )}
                              </td>
                              <td className="py-2.5 px-2 text-center text-muted">
                                <ArrowRight className="w-3.5 h-3.5 mx-auto text-muted" />
                              </td>
                              <td className="py-2.5 px-4 text-center">
                                {codeB ? (
                                  <div className="inline-block">
                                    <StatusCell status={codeB} size="sm" />
                                  </div>
                                ) : (
                                  <span className="text-muted text-[11px]">None</span>
                                )}
                              </td>
                              <td className="py-2.5 px-4 text-muted text-[11px]">
                                {diff.status_a || 'EMPTY'} → {diff.status_b || 'EMPTY'}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={6} className="py-8 text-center text-muted text-xs">
                            {cellSearch ? 'No cell changes match your search criteria.' : 'No cell changes detected.'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EXPORT CENTER */}
      {activeTab === 'export' && (
        <div className="space-y-6">
          {/* Export Settings Card */}
          <div className="bg-surface rounded-card border border-border p-5 shadow-sm space-y-4">
            <h2 className="text-sm font-semibold text-ink">Schedule Export Configuration</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Select Roster Version */}
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Roster Period / Version
                </label>
                <Select
                  value={exportPeriodId}
                  onChange={(val) => setExportPeriodId(val)}
                  options={
                    periodOptions.length > 0
                      ? periodOptions
                      : [{ value: '', label: 'No versions available' }]
                  }
                  className="text-xs"
                />
                {selectedExportPeriod && (
                  <div className="mt-1.5 flex items-center space-x-2 text-[11px] text-muted">
                    <span>Month: {selectedExportPeriod.month}</span>
                    <span>•</span>
                    <Badge
                      variant={selectedExportPeriod.status === 'PUBLISHED' ? 'SUCCESS' : 'neutral'}
                    >
                      {selectedExportPeriod.status}
                    </Badge>
                  </div>
                )}
              </div>

              {/* Format Toggle */}
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Export Document Format
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setExportFormat('csv')}
                    className={`flex items-center justify-center space-x-1.5 py-2 px-3 rounded-ctl border text-xs font-medium transition-colors ${
                      exportFormat === 'csv'
                        ? 'border-accent-700 bg-accent-50/60 text-accent-900 font-semibold ring-1 ring-accent-700'
                        : 'border-border bg-surface text-ink hover:bg-surface-muted/50'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>CSV</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setExportFormat('xlsx')}
                    className={`flex items-center justify-center space-x-1.5 py-2 px-3 rounded-ctl border text-xs font-medium transition-colors ${
                      exportFormat === 'xlsx'
                        ? 'border-accent-700 bg-accent-50/60 text-accent-900 font-semibold ring-1 ring-accent-700'
                        : 'border-border bg-surface text-ink hover:bg-surface-muted/50'
                    }`}
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    <span>Excel (.xlsx)</span>
                  </button>
                </div>
              </div>

              {/* Day View Date Picker */}
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Operating Date (for Day View export)
                </label>
                <input
                  type="date"
                  value={exportDate}
                  onChange={(e) => setExportDate(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-surface border border-border rounded-ctl focus:outline-none focus:ring-1 focus:ring-accent-600"
                />
              </div>
            </div>
          </div>

          {/* Export View Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* View 1: Full Monthly Matrix Grid */}
            <div className="bg-surface rounded-card border border-border p-5 shadow-sm hover:border-accent-600 transition-colors flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 bg-accent-100 rounded-ctl text-accent-800">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      Full Monthly Matrix Grid
                    </h3>
                    <span className="text-[11px] font-mono text-muted">view=grid</span>
                  </div>
                </div>

                <p className="text-xs text-muted mt-3">
                  Comprehensive 31-day shift calendar for all staff members with status codes (W, WO, PH, HW, L, CO), monthly shift sums, and weekend totals.
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    All Employees
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Full Month
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Letter Status Codes
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                <span className="text-[11px] text-muted">Standard operational matrix</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleDownload('grid')}
                  isLoading={isExporting === 'grid'}
                >
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download {exportFormat.toUpperCase()}
                </Button>
              </div>
            </div>

            {/* View 2: Daily Operational Roster */}
            <div className="bg-surface rounded-card border border-border p-5 shadow-sm hover:border-accent-600 transition-colors flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 bg-accent-100 rounded-ctl text-accent-800">
                    <Calendar className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      Daily Operational Schedule
                    </h3>
                    <span className="text-[11px] font-mono text-muted">view=day</span>
                  </div>
                </div>

                <p className="text-xs text-muted mt-3">
                  Single-day operational snapshot for date <strong className="font-mono text-ink">{exportDate}</strong>. Grouped by brand-process with employee contact information and shift status.
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Target Date: {exportDate}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Brand-Process Grouped
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                <span className="text-[11px] text-muted">Floor management view</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleDownload('day')}
                  isLoading={isExporting === 'day'}
                >
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download {exportFormat.toUpperCase()}
                </Button>
              </div>
            </div>

            {/* View 3: Brand-Process Coverage Matrix */}
            <div className="bg-surface rounded-card border border-border p-5 shadow-sm hover:border-accent-600 transition-colors flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 bg-accent-100 rounded-ctl text-accent-800">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      Brand-Process Coverage Matrix
                    </h3>
                    <span className="text-[11px] font-mono text-muted">view=coverage</span>
                  </div>
                </div>

                <p className="text-xs text-muted mt-3">
                  Day-by-day minimum required coverage versus actual staffed headcount for every active Brand-Process pair, with shortfall deficit indicators.
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Demand vs Actual
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Shortfall Auditing
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                <span className="text-[11px] text-muted">SLA & compliance reporting</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleDownload('coverage')}
                  isLoading={isExporting === 'coverage'}
                >
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download {exportFormat.toUpperCase()}
                </Button>
              </div>
            </div>

            {/* View 4: Integrity Violations & Conflicts Report */}
            <div className="bg-surface rounded-card border border-border p-5 shadow-sm hover:border-accent-600 transition-colors flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 bg-warn/15 rounded-ctl text-warn">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      Integrity Violations & Conflicts Report
                    </h3>
                    <span className="text-[11px] font-mono text-muted">view=conflicts</span>
                  </div>
                </div>

                <p className="text-xs text-muted mt-3">
                  Full list of constraint violations, rule codes, severity levels, affected employees, and Ops Manager acknowledgment overrides.
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Blocking & Warnings
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-muted border border-border text-muted">
                    Audit Trail Records
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
                <span className="text-[11px] text-muted">Governance & audit checklist</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleDownload('conflicts')}
                  isLoading={isExporting === 'conflicts'}
                >
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download {exportFormat.toUpperCase()}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
