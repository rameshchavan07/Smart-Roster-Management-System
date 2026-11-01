import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  Search,
  ShieldCheck,
  RefreshCw,
  LayoutGrid,
  Layers,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Badge,
  Button,
  Input,
  Select,
  EmptyState,
  Skeleton,
} from '../../components/ui';
import { useMonth } from '../../context/MonthContext';
import { useAuth } from '../auth/AuthContext';
import { useRosterPeriodsQuery, useRosterConflictsQuery } from '../../api/rosters';
import { useBrandsQuery } from '../../api/brands';
import { ConflictDrawer } from './ConflictDrawer';
import type { RosterConflict, ConflictSeverity } from '../../types/roster';
import { CONFLICT_CODE_INFO } from '../../types/roster';

// Demo sample conflicts matching docs/SAMPLE_DATA.md (S1–S4) for offline/seed demonstration
const FALLBACK_CONFLICTS: RosterConflict[] = [
  {
    id: 'c-001',
    roster_period_id: 'period-demo-2026-12',
    code: 'E001',
    severity: 'BLOCKING',
    brand_process_id: 'bp-aurora-cs',
    brand_name: 'Aurora',
    process_name: 'Customer Support',
    date_from: '2026-12-14',
    date_to: '2026-12-14',
    root_causes: ['LEAVE', 'SOLO_RESOURCE'],
    message: 'Aurora Customer Support requires 1 staff on 14 Dec 2026, but 0 available due to approved annual leave.',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Aarav Sharma',
    employee_code: 'EMP-007',
  },
  {
    id: 'c-002',
    roster_period_id: 'period-demo-2026-12',
    code: 'E002',
    severity: 'BLOCKING',
    brand_process_id: 'bp-nova-acc',
    brand_name: 'Nova',
    process_name: 'Escalations & ACC',
    date_from: '2026-12-20',
    date_to: '2026-12-20',
    root_causes: ['WEEKLY_OFF'],
    message: 'Nova Escalations has coverage shortfall of 1 on 20 Dec 2026 (required 2, scheduled 1).',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Priya Patel',
    employee_code: 'EMP-014',
  },
  {
    id: 'c-003',
    roster_period_id: 'period-demo-2026-12',
    code: 'E005',
    severity: 'BLOCKING',
    date_from: '2026-12-07',
    date_to: '2026-12-14',
    root_causes: ['STREAK_LIMIT'],
    message: 'Rahul Verma assigned to 7 consecutive work days (07 Dec to 13 Dec), exceeding mandatory limit of 6.',
    suggestions: [],
    is_acknowledged: true,
    acknowledged_reason: 'Approved by Ops Manager for urgent holiday peak coverage with subsequent compensatory rest.',
    employee_name: 'Rahul Verma',
    employee_code: 'EMP-021',
  },
  {
    id: 'c-004',
    roster_period_id: 'period-demo-2026-12',
    code: 'W001',
    severity: 'WARNING',
    date_from: '2026-12-18',
    date_to: '2026-12-18',
    root_causes: ['PREFERENCE'],
    message: 'Preferred weekly-off on Friday 18 Dec not honored for Ananya Iyer due to operational coverage demand.',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Ananya Iyer',
    employee_code: 'EMP-033',
  },
  {
    id: 'c-005',
    roster_period_id: 'period-demo-2026-12',
    code: 'W003',
    severity: 'INFO',
    brand_process_id: 'bp-pulse-cs',
    brand_name: 'Pulse',
    process_name: 'Customer Support',
    date_from: '2026-12-01',
    date_to: '2026-12-31',
    root_causes: ['SOLO_RESOURCE'],
    message: 'Single point of failure: Pulse Customer Support operates with exactly 1 primary assigned employee and no dedicated cross-trained backup.',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Devansh Nair',
    employee_code: 'EMP-045',
  },
];

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
      ];
      return `${day} ${months[monthIdx]}`;
    }
  } catch {
    // fallback
  }
  return dateStr;
}

export const ConflictsPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentMonth, monthLabel } = useMonth();
  const { isOpsManager, isPodLead } = useAuth();

  // Selected conflict for right drawer
  const [selectedConflict, setSelectedConflict] = useState<RosterConflict | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'BLOCKING' | 'WARNING' | 'INFO'>('ALL');
  const [brandFilter, setBrandFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'ACKNOWLEDGED'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Fetch active roster period for current month
  const { data: periods, isLoading: isPeriodsLoading, refetch: refetchPeriods } = useRosterPeriodsQuery(currentMonth);
  const activePeriod = periods && periods.length > 0 ? periods[0] : null;

  // Fetch conflicts for period
  const {
    data: backendConflicts,
    isLoading: isConflictsLoading,
    refetch: refetchConflicts,
  } = useRosterConflictsQuery(activePeriod?.id);

  // Master brands for filter dropdown
  const { data: brandsResult } = useBrandsQuery({ limit: 100 });

  // Use backend conflicts when available, fallback to demo seed conflicts
  const conflicts: RosterConflict[] = useMemo(() => {
    if (backendConflicts && backendConflicts.length > 0) {
      return backendConflicts;
    }
    return FALLBACK_CONFLICTS;
  }, [backendConflicts]);

  // Filter conflicts
  const filteredConflicts = useMemo(() => {
    return conflicts.filter((c) => {
      // Severity filter
      if (severityFilter !== 'ALL' && c.severity !== severityFilter) return false;

      // Brand filter
      if (brandFilter !== 'ALL') {
        const matchesBrand =
          (c.brand_name && c.brand_name.toLowerCase() === brandFilter.toLowerCase()) ||
          c.brand_process_id === brandFilter;
        if (!matchesBrand) return false;
      }

      // Status filter
      if (statusFilter === 'ACTIVE' && c.is_acknowledged) return false;
      if (statusFilter === 'ACKNOWLEDGED' && !c.is_acknowledged) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const inCode = c.code.toLowerCase().includes(q);
        const inMsg = c.message.toLowerCase().includes(q);
        const inBrand = c.brand_name?.toLowerCase().includes(q);
        const inProc = c.process_name?.toLowerCase().includes(q);
        const inEmp = c.employee_name?.toLowerCase().includes(q);
        const inCauses = c.root_causes.some((rc) => rc.toLowerCase().includes(q));
        if (!inCode && !inMsg && !inBrand && !inProc && !inEmp && !inCauses) {
          return false;
        }
      }

      return true;
    });
  }, [conflicts, severityFilter, brandFilter, statusFilter, searchQuery]);

  // KPI calculations
  const stats = useMemo(() => {
    let blocking = 0;
    let warning = 0;
    let info = 0;
    let acknowledged = 0;
    let unacknowledgedBlocking = 0;

    for (const c of conflicts) {
      if (c.severity === 'BLOCKING') {
        blocking++;
        if (!c.is_acknowledged) unacknowledgedBlocking++;
      } else if (c.severity === 'WARNING') {
        warning++;
      } else if (c.severity === 'INFO') {
        info++;
      }

      if (c.is_acknowledged) {
        acknowledged++;
      }
    }

    return {
      total: conflicts.length,
      blocking,
      warning,
      info,
      acknowledged,
      unacknowledgedBlocking,
      isPublishable: unacknowledgedBlocking === 0,
    };
  }, [conflicts]);

  const brandOptions = useMemo(() => {
    const list = brandsResult?.items || [];
    return [
      { value: 'ALL', label: 'All Brands' },
      ...list.map((b) => ({ value: b.name, label: b.name })),
    ];
  }, [brandsResult]);

  const handleRefresh = () => {
    refetchPeriods();
    refetchConflicts();
  };

  const severityVariant: Record<ConflictSeverity, 'BLOCKING' | 'WARNING' | 'INFO'> = {
    BLOCKING: 'BLOCKING',
    WARNING: 'WARNING',
    INFO: 'INFO',
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-ink">
              Validation Conflicts & Gaps
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-2 text-ink-2 border border-border">
              {monthLabel}
            </span>
          </div>
          <p className="text-xs text-ink-3 mt-1">
            Engine validation findings, plain-English root causes, and ranked backup recommendations.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRefresh}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/roster')}
            className="flex items-center gap-1.5"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>Roster Grid</span>
          </Button>
        </div>
      </div>

      {/* KPI Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {/* Total Conflicts */}
        <div className="p-3.5 bg-surface border border-border rounded-card flex flex-col justify-between">
          <span className="text-[11px] font-semibold text-ink-3 uppercase tracking-wider">
            Total Conflicts
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-ink">
              {stats.total}
            </span>
            <span className="text-[11px] text-ink-3">
              findings
            </span>
          </div>
        </div>

        {/* Blocking Gaps */}
        <div className="p-3.5 bg-surface border border-border rounded-card flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-bad uppercase tracking-wider">
              Blocking Gaps
            </span>
            <AlertCircle className="w-3.5 h-3.5 text-bad" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-bad">
              {stats.blocking}
            </span>
            <span className="text-[11px] text-ink-3">
              {stats.unacknowledgedBlocking} active
            </span>
          </div>
        </div>

        {/* Warnings */}
        <div className="p-3.5 bg-surface border border-border rounded-card flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-warn uppercase tracking-wider">
              Warnings
            </span>
            <AlertTriangle className="w-3.5 h-3.5 text-warn" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-warn">
              {stats.warning}
            </span>
            <span className="text-[11px] text-ink-3">
              non-blocking
            </span>
          </div>
        </div>

        {/* Acknowledged */}
        <div className="p-3.5 bg-surface border border-border rounded-card flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-ok uppercase tracking-wider">
              Acknowledged
            </span>
            <ShieldCheck className="w-3.5 h-3.5 text-ok" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-ok">
              {stats.acknowledged}
            </span>
            <span className="text-[11px] text-ink-3">
              with audit trail
            </span>
          </div>
        </div>

        {/* Publish Gating Status */}
        <div className={`p-3.5 border rounded-card flex flex-col justify-between col-span-2 md:col-span-1 ${
          stats.isPublishable
            ? 'bg-ok/5 border-ok/30'
            : 'bg-bad/5 border-bad/30'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">
              Publish Gate
            </span>
            {stats.isPublishable ? (
              <CheckCircle2 className="w-4 h-4 text-ok" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-bad" />
            )}
          </div>
          <div className="mt-2">
            <span className={`text-xs font-semibold ${
              stats.isPublishable ? 'text-ok' : 'text-bad'
            }`}>
              {stats.isPublishable ? 'Unblocked for Publish' : 'Gating Blocked'}
            </span>
            <span className="block text-[10px] text-ink-3 mt-0.5">
              {stats.isPublishable
                ? 'All mandatory checks satisfied'
                : `${stats.unacknowledgedBlocking} blocking unresolved`}
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="p-3 bg-surface border border-border rounded-ctl flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search Box */}
          <div className="relative min-w-[220px] max-w-[280px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
            <Input
              type="text"
              placeholder="Search code, message, brand..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 h-8 text-xs font-normal"
            />
          </div>

          {/* Severity Tabs */}
          <div className="inline-flex rounded-ctl border border-border p-0.5 bg-surface-2 text-xs">
            {(['ALL', 'BLOCKING', 'WARNING', 'INFO'] as const).map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setSeverityFilter(sev)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  severityFilter === sev
                    ? 'bg-surface text-ink font-semibold shadow-xs'
                    : 'text-ink-3 hover:text-ink'
                }`}
              >
                {sev === 'ALL' ? 'All' : sev.charAt(0) + sev.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {/* Brand Filter Dropdown */}
          <div className="w-[160px]">
            <Select
              options={brandOptions}
              value={brandFilter}
              onChange={(val) => setBrandFilter(val)}
              className="h-8 text-xs"
            />
          </div>

          {/* Status Filter */}
          <div className="w-[160px]">
            <Select
              options={[
                { value: 'ALL', label: 'All Statuses' },
                { value: 'ACTIVE', label: 'Active (Unresolved)' },
                { value: 'ACKNOWLEDGED', label: 'Acknowledged Only' },
              ]}
              value={statusFilter}
              onChange={(val) => setStatusFilter(val as any)}
              className="h-8 text-xs"
            />
          </div>
        </div>

        {/* Clear Filter count */}
        {(severityFilter !== 'ALL' || brandFilter !== 'ALL' || statusFilter !== 'ALL' || searchQuery) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSeverityFilter('ALL');
              setBrandFilter('ALL');
              setStatusFilter('ALL');
              setSearchQuery('');
            }}
            className="text-xs text-ink-3 hover:text-ink shrink-0"
          >
            Reset Filters
          </Button>
        )}
      </div>

      {/* Conflicts Full-Width Table */}
      {isPeriodsLoading || isConflictsLoading ? (
        <div className="space-y-2 p-4 bg-surface border border-border rounded-ctl">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : filteredConflicts.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No Conflicts Found"
          description={
            searchQuery || severityFilter !== 'ALL' || brandFilter !== 'ALL' || statusFilter !== 'ALL'
              ? 'No validation conflicts match the selected filter criteria.'
              : 'The generated roster passes all mandatory coverage and worker integrity checks.'
          }
          actionLabel="Reset Filters"
          onAction={() => {
            setSeverityFilter('ALL');
            setBrandFilter('ALL');
            setStatusFilter('ALL');
            setSearchQuery('');
          }}
        />
      ) : (
        <Table dense>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">Severity</TableHead>
              <TableHead className="w-[80px]">Code</TableHead>
              <TableHead className="min-w-[160px]">Brand / Process</TableHead>
              <TableHead className="w-[110px]">Date(s)</TableHead>
              <TableHead className="min-w-[150px]">Employee</TableHead>
              <TableHead className="min-w-[200px]">Explanation & Causes</TableHead>
              <TableHead className="w-[120px]">Status</TableHead>
              <TableHead className="w-[100px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredConflicts.map((c) => {
              const codeInfo = CONFLICT_CODE_INFO[c.code] || { label: c.code, meaning: '' };
              const isSelected = selectedConflict?.id === c.id;

              return (
                <TableRow
                  key={c.id}
                  isSelected={isSelected}
                  onClick={() => setSelectedConflict(c)}
                  className="cursor-pointer"
                >
                  {/* Severity */}
                  <TableCell>
                    <Badge
                      variant={severityVariant[c.severity]}
                      icon={
                        c.severity === 'BLOCKING' ? (
                          <AlertCircle className="w-3 h-3 text-bad" />
                        ) : c.severity === 'WARNING' ? (
                          <AlertTriangle className="w-3 h-3 text-warn" />
                        ) : (
                          <Info className="w-3 h-3 text-info" />
                        )
                      }
                      size="sm"
                      className="font-mono"
                    >
                      {c.severity}
                    </Badge>
                  </TableCell>

                  {/* Code */}
                  <TableCell>
                    <span
                      title={codeInfo.meaning}
                      className="font-mono font-semibold text-xs text-ink bg-surface-2 px-1.5 py-0.5 rounded border border-border"
                    >
                      {c.code}
                    </span>
                  </TableCell>

                  {/* Brand / Process */}
                  <TableCell>
                    {c.brand_name ? (
                      <div className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-ink-3 shrink-0" />
                        <span className="font-medium text-ink">
                          {c.brand_name}
                        </span>
                        {c.process_name && (
                          <span className="text-ink-3 text-[11px]">
                            · {c.process_name}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-ink-3 text-[11px]">System Rule</span>
                    )}
                  </TableCell>

                  {/* Dates */}
                  <TableCell className="font-mono text-[11px] text-ink-2 whitespace-nowrap">
                    {c.date_from === c.date_to || !c.date_to
                      ? formatDate(c.date_from)
                      : `${formatDate(c.date_from)} – ${formatDate(c.date_to)}`}
                  </TableCell>

                  {/* Employee */}
                  <TableCell>
                    {c.employee_name ? (
                      <div>
                        <span className="font-medium text-ink block truncate">
                          {c.employee_name}
                        </span>
                        {c.employee_code && (
                          <span className="font-mono text-[10px] text-ink-3">
                            {c.employee_code}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-ink-3 text-[11px]">Demand Level</span>
                    )}
                  </TableCell>

                  {/* Message & Causes */}
                  <TableCell>
                    <div className="space-y-1">
                      <p className="line-clamp-2 text-xs text-ink font-normal leading-snug">
                        {c.message}
                      </p>
                      {c.root_causes && c.root_causes.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap">
                          {c.root_causes.map((rc) => (
                            <span
                              key={rc}
                              className="font-mono text-[9px] bg-surface-2 px-1 py-0.2 rounded border border-border text-ink-3"
                            >
                              {rc}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </TableCell>

                  {/* Status */}
                  <TableCell>
                    {c.is_acknowledged ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ok bg-ok/10 px-2 py-0.5 rounded border border-ok/20">
                        <ShieldCheck className="w-3 h-3 text-ok" />
                        <span>Acknowledged</span>
                      </span>
                    ) : c.severity === 'BLOCKING' ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-bad bg-bad/10 px-2 py-0.5 rounded border border-bad/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-bad animate-pulse" />
                        <span>Active Gate</span>
                      </span>
                    ) : (
                      <span className="text-ink-3 text-[11px] font-medium">
                        Active Notice
                      </span>
                    )}
                  </TableCell>

                  {/* Actions */}
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedConflict(c);
                      }}
                      className="text-xs text-accent-700 hover:text-accent-800 p-1"
                    >
                      <span className="mr-1">Inspect</span>
                      <ArrowRight className="w-3 h-3 inline" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* Right Conflict Detail & Resolution Drawer */}
      <ConflictDrawer
        isOpen={Boolean(selectedConflict)}
        onClose={() => setSelectedConflict(null)}
        periodId={activePeriod?.id || ''}
        conflict={selectedConflict}
        canAcknowledge={isOpsManager}
        canApply={isOpsManager || isPodLead}
        onApplied={() => {
          refetchConflicts();
        }}
      />
    </div>
  );
};
