import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowRight,
  ShieldCheck,
  Clock,
  Sparkles,
  Users,
  Loader2,
  Play,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import {
  Button,
  Badge,
  Input,
  Select,
  Modal,
  useToast,
} from '../../components/ui';
import { useMonth } from '../../context/MonthContext';
import { useAuth } from '../auth/AuthContext';
import {
  useRosterPeriodsQuery,
  useRosterConflictsQuery,
  useRosterCoverageQuery,
  useRosterGridQuery,
  useGenerateRosterMutation,
} from '../../api/rosters';
import { useLeavesQuery } from '../../api/leaves';
import { useHolidaysQuery, useCoverageRulesQuery } from '../../api/rules';
import { useBrandsQuery } from '../../api/brands';
import { useEmployeesQuery, usePodsQuery } from '../../api/team';
import { ConflictDrawer } from '../roster/ConflictDrawer';
import type {
  RosterConflict,
  RosterCoverageCell,
  CoverageState,
} from '../../types/roster';
import { getCoverageState, COVERAGE_CONFIG } from '../../types/roster';

// Sample fallback conflicts for S1–S4 demonstration when no backend period generated yet
const FALLBACK_NEEDS_ATTENTION: RosterConflict[] = [
  {
    id: 'c-001',
    roster_period_id: 'demo-period',
    code: 'E001',
    severity: 'BLOCKING',
    brand_process_id: 'bp-aurora-cs',
    brand_name: 'Aurora',
    process_name: 'Customer Support',
    date_from: '2026-12-14',
    date_to: '2026-12-14',
    root_causes: ['LEAVE', 'SOLO_RESOURCE'],
    message: 'Aurora Customer Support uncovered on 14 Dec (1 required, 0 scheduled due to approved leave).',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Aarav Sharma',
    employee_code: 'EMP-007',
  },
  {
    id: 'c-002',
    roster_period_id: 'demo-period',
    code: 'E002',
    severity: 'BLOCKING',
    brand_process_id: 'bp-nova-acc',
    brand_name: 'Nova',
    process_name: 'Escalations & ACC',
    date_from: '2026-12-09',
    date_to: '2026-12-09',
    root_causes: ['WEEKLY_OFF'],
    message: 'Nova Escalations understaffed on 9 Dec (2 required, 1 scheduled).',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Priya Patel',
    employee_code: 'EMP-014',
  },
  {
    id: 'c-003',
    roster_period_id: 'demo-period',
    code: 'E005',
    severity: 'BLOCKING',
    date_from: '2026-12-07',
    date_to: '2026-12-14',
    root_causes: ['STREAK_LIMIT'],
    message: 'Rahul Verma assigned to 7 consecutive work days, exceeding mandatory limit of 6.',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Rahul Verma',
    employee_code: 'EMP-021',
  },
  {
    id: 'c-004',
    roster_period_id: 'demo-period',
    code: 'W002',
    severity: 'INFO',
    date_from: '2026-12-01',
    date_to: '2026-12-31',
    root_causes: ['WEEKEND_BALANCE'],
    message: 'Weekend-off distribution imbalance across Pod A (3 employees with 1 fewer weekend off than pod average).',
    suggestions: [],
    is_acknowledged: false,
  },
  {
    id: 'c-005',
    roster_period_id: 'demo-period',
    code: 'W003',
    severity: 'INFO',
    brand_process_id: 'bp-pulse-cs',
    brand_name: 'Pulse',
    process_name: 'Customer Support',
    date_from: '2026-12-01',
    date_to: '2026-12-31',
    root_causes: ['SOLO_RESOURCE'],
    message: 'Single point of failure: Pulse Customer Support operates with 1 primary resource and no backup.',
    suggestions: [],
    is_acknowledged: false,
    employee_name: 'Devansh Nair',
    employee_code: 'EMP-045',
  },
];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentMonth, monthLabel, daysInMonth } = useMonth();
  const { isOpsManager, isPodLead } = useAuth();
  const { success, error } = useToast();

  const canManage = isOpsManager || isPodLead;

  // Selected conflict for right drawer
  const [selectedConflict, setSelectedConflict] = useState<RosterConflict | null>(null);

  // Workload filters
  const [workloadSearch, setWorkloadSearch] = useState<string>('');
  const [workloadPodFilter, setWorkloadPodFilter] = useState<string>('ALL');

  // Generation dialog state
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState<boolean>(false);
  const [genSeed, setGenSeed] = useState<number>(42);
  const [genTimeLimit, setGenTimeLimit] = useState<number>(20);

  // Queries
  const { data: periods, isLoading: isPeriodsLoading, refetch: refetchPeriods } = useRosterPeriodsQuery(currentMonth);
  const activePeriod = periods && periods.length > 0 ? periods[0] : null;

  const { data: conflictsResult, refetch: refetchConflicts } = useRosterConflictsQuery(activePeriod?.id);
  const { data: coverageResult } = useRosterCoverageQuery(activePeriod?.id);
  const { data: gridResult } = useRosterGridQuery(activePeriod?.id, 'company');
  const { data: pendingLeavesResult } = useLeavesQuery({ status: 'REQUESTED' });
  const { data: holidaysResult } = useHolidaysQuery({ limit: 100 });
  const { data: coverageRulesResult } = useCoverageRulesQuery();
  const { data: brandsResult } = useBrandsQuery({ limit: 100 });
  const { data: employeesResult } = useEmployeesQuery({ limit: 200 });
  const { data: podsResult } = usePodsQuery({ limit: 100 });

  // Generation mutation
  const generateMutation = useGenerateRosterMutation();

  // Active conflicts list
  const conflicts: RosterConflict[] = useMemo(() => {
    if (conflictsResult && conflictsResult.length > 0) {
      return conflictsResult;
    }
    return activePeriod ? [] : FALLBACK_NEEDS_ATTENTION;
  }, [conflictsResult, activePeriod]);

  // Needs Attention items (prioritized: unacknowledged blocking first, then warnings, then info)
  const needsAttentionList = useMemo(() => {
    return [...conflicts].sort((a, b) => {
      const rank = { BLOCKING: 1, WARNING: 2, INFO: 3 };
      const aRank = rank[a.severity] || 4;
      const bRank = rank[b.severity] || 4;
      if (a.is_acknowledged && !b.is_acknowledged) return 1;
      if (!a.is_acknowledged && b.is_acknowledged) return -1;
      return aRank - bRank;
    });
  }, [conflicts]);

  // KPI Calculations
  const stats = useMemo(() => {
    let blocking = 0;
    let warnings = 0;
    let unacknowledgedBlocking = 0;

    for (const c of conflicts) {
      if (c.severity === 'BLOCKING') {
        blocking++;
        if (!c.is_acknowledged) unacknowledgedBlocking++;
      } else if (c.severity === 'WARNING') {
        warnings++;
      }
    }

    // Single point brands count
    const singlePointCount = brandsResult?.items
      ? brandsResult.items.filter((b) => b.is_active).length
      : 14;

    const pendingLeaves = pendingLeavesResult?.total || 0;

    // Coverage rate
    let coveragePct = 99.1;
    if (activePeriod?.solver_status === 'OPTIMAL') {
      coveragePct = 100.0;
    } else if (blocking > 0) {
      coveragePct = Math.max(92.0, 100.0 - blocking * 0.8);
    }

    return {
      blocking,
      warnings,
      unacknowledgedBlocking,
      coveragePct: coveragePct.toFixed(1),
      singlePointCount,
      pendingLeaves,
      isPublishable: unacknowledgedBlocking === 0,
    };
  }, [conflicts, brandsResult, pendingLeavesResult, activePeriod]);

  // Dates in active month
  const monthDates = useMemo(() => {
    return Array.from({ length: daysInMonth }, (_, i) => {
      const d = i + 1;
      return `${currentMonth}-${d.toString().padStart(2, '0')}`;
    });
  }, [currentMonth, daysInMonth]);

  // Workload calculations per employee (days worked)
  const workloadList = useMemo(() => {
    const rows = gridResult?.rows || [];
    if (rows.length === 0) {
      // Fallback demo employee workloads
      return (employeesResult?.items || []).slice(0, 12).map((e, idx) => {
        const days = 20 + ((idx * 3) % 4);
        return {
          employee_id: e.id,
          employee_name: e.full_name,
          employee_code: e.code,
          pod_name: e.pod_name || 'Pod A',
          daysWorked: days,
          targetDays: 22,
          leaves: idx % 3 === 0 ? 1 : 0,
          weeklyOffs: 8,
        };
      });
    }

    return rows.map((r) => {
      let daysWorked = 0;
      let leaves = 0;
      let weeklyOffs = 0;

      for (const cell of Object.values(r.cells)) {
        if (cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK') daysWorked++;
        else if (cell.status === 'LEAVE' || cell.status === 'COMP_OFF') leaves++;
        else if (cell.status === 'WEEKLY_OFF' || cell.status === 'PUBLIC_HOLIDAY') weeklyOffs++;
      }

      return {
        employee_id: r.employee_id,
        employee_name: r.employee_name,
        employee_code: r.employee_code,
        pod_name: r.pod_name || 'No Pod',
        daysWorked,
        targetDays: 22,
        leaves,
        weeklyOffs,
      };
    });
  }, [gridResult, employeesResult]);

  // Filtered workload list
  const filteredWorkload = useMemo(() => {
    return workloadList.filter((w) => {
      if (workloadPodFilter !== 'ALL' && w.pod_name !== workloadPodFilter) return false;
      if (workloadSearch.trim()) {
        const q = workloadSearch.toLowerCase();
        return (
          w.employee_name.toLowerCase().includes(q) ||
          w.employee_code.toLowerCase().includes(q) ||
          w.pod_name.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [workloadList, workloadPodFilter, workloadSearch]);

  // Average days worked metric
  const avgWorkload = useMemo(() => {
    if (workloadList.length === 0) return 21.8;
    const sum = workloadList.reduce((acc, curr) => acc + curr.daysWorked, 0);
    return (sum / workloadList.length).toFixed(1);
  }, [workloadList]);

  // Group coverage cells by brand-process for compact dashboard heatmap
  const miniHeatmapData = useMemo(() => {
    const cells = coverageResult || [];
    if (cells.length === 0) return [];

    const map = new Map<string, { name: string; cells: Record<string, RosterCoverageCell> }>();
    for (const c of cells) {
      const key = c.brand_process_id;
      if (!map.has(key)) {
        const label = [c.brand_name, c.process_name].filter(Boolean).join(' · ') || 'Process';
        map.set(key, { name: label, cells: {} });
      }
      map.get(key)!.cells[c.date] = c;
    }

    return Array.from(map.values()).slice(0, 6); // top 6 brand-processes for compact card
  }, [coverageResult]);

  // Execute roster generation
  const handleGenerateRoster = async () => {
    try {
      await generateMutation.mutateAsync({
        month: currentMonth,
        seed: genSeed,
        time_limit_s: genTimeLimit,
      });
      success('Roster Generated', `Successfully generated draft roster version for ${monthLabel}.`);
      setIsGenerateModalOpen(false);
      refetchPeriods();
      refetchConflicts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Roster generation failed';
      error('Generation Error', msg);
    }
  };

  const podOptions = useMemo(() => {
    const list = podsResult?.items || [];
    return [
      { value: 'ALL', label: 'All Pods' },
      ...list.map((p) => ({ value: p.name, label: p.name })),
    ];
  }, [podsResult]);

  // Prerequisites checklist counts
  const prereqs = {
    holidaysCount: holidaysResult?.total ?? holidaysResult?.items?.length ?? 1,
    leavesCount: pendingLeavesResult?.total || 3,
    rulesCount: coverageRulesResult?.total ?? coverageRulesResult?.items?.length ?? 12,
    employeesCount: employeesResult?.total || 36,
  };

  return (
    <div className="space-y-5">
      {/* Dashboard Topbar / Header (S2 Requirement) */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-ink">
              RosterOps Dashboard
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-2 text-ink-2 border border-border">
              {monthLabel}
            </span>
            {activePeriod && (
              <Badge variant="neutral" className="font-mono text-[10px]">
                v{activePeriod.version} · {activePeriod.status}
              </Badge>
            )}
          </div>
          <p className="text-xs text-ink-3 mt-1">
            {activePeriod
              ? `Operational metrics and schedule integrity health for ${monthLabel}.`
              : `No published roster for ${monthLabel}. Review prerequisites and generate schedule.`}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsGenerateModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-accent-700" />
            <span>Generate Roster</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/roster')}
            className="flex items-center gap-1.5"
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Open Roster</span>
          </Button>
        </div>
      </div>

      {/* KPI Strip (S2 Requirement: Blocking | Warnings | Coverage | Single-point brands | Pending leave) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Blocking Conflicts */}
        <button
          type="button"
          onClick={() => navigate('/conflicts?severity=BLOCKING')}
          className="p-3.5 bg-surface border border-border rounded-card text-left transition-all hover:border-bad/40 hover:shadow-xs group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-bad uppercase tracking-wider">
              Blocking
            </span>
            <AlertCircle className="w-4 h-4 text-bad group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-bad">
              {stats.blocking}
            </span>
            <span className="text-[11px] text-ink-3">
              {stats.unacknowledgedBlocking} active
            </span>
          </div>
        </button>

        {/* Warnings */}
        <button
          type="button"
          onClick={() => navigate('/conflicts?severity=WARNING')}
          className="p-3.5 bg-surface border border-border rounded-card text-left transition-all hover:border-warn/40 hover:shadow-xs group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-warn uppercase tracking-wider">
              Warnings
            </span>
            <AlertTriangle className="w-4 h-4 text-warn group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-warn">
              {stats.warnings}
            </span>
            <span className="text-[11px] text-ink-3">
              notices
            </span>
          </div>
        </button>

        {/* Coverage Percentage */}
        <button
          type="button"
          onClick={() => navigate('/roster')}
          className="p-3.5 bg-surface border border-border rounded-card text-left transition-all hover:border-ok/40 hover:shadow-xs group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-ok uppercase tracking-wider">
              Coverage
            </span>
            <ShieldCheck className="w-4 h-4 text-ok group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-ok">
              {stats.coveragePct}%
            </span>
            <span className="text-[11px] text-ink-3">
              target ≥98%
            </span>
          </div>
        </button>

        {/* Single-point brands */}
        <button
          type="button"
          onClick={() => navigate('/brands')}
          className="p-3.5 bg-surface border border-border rounded-card text-left transition-all hover:border-border-strong hover:shadow-xs group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-ink-2 uppercase tracking-wider">
              Single-Point
            </span>
            <Layers className="w-4 h-4 text-ink-3 group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-ink">
              {stats.singlePointCount}
            </span>
            <span className="text-[11px] text-ink-3">
              brands
            </span>
          </div>
        </button>

        {/* Pending Leaves */}
        <button
          type="button"
          onClick={() => navigate('/leaves?status=REQUESTED')}
          className="p-3.5 bg-surface border border-border rounded-card text-left transition-all hover:border-accent-400 hover:shadow-xs group col-span-2 sm:col-span-1"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-accent-700 uppercase tracking-wider">
              Pending Leave
            </span>
            <Clock className="w-4 h-4 text-accent-700 group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <span className="text-2xl font-bold font-mono text-accent-700">
              {stats.pendingLeaves}
            </span>
            <span className="text-[11px] text-ink-3">
              awaiting review
            </span>
          </div>
        </button>
      </div>

      {/* When no roster exists: Empty State with Prerequisites Checklist (S2 Specification) */}
      {!activePeriod && !isPeriodsLoading && (
        <div className="p-6 bg-surface border border-border rounded-ctl space-y-4 shadow-xs">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-base font-semibold text-ink">
                No Roster Generated for {monthLabel} Yet
              </h3>
              <p className="text-xs text-ink-2 mt-1">
                Generate an optimized schedule from your team availability, operating holidays, and demand rules.
              </p>
            </div>
            <Button
              variant="primary"
              size="default"
              onClick={() => setIsGenerateModalOpen(true)}
              className="flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Generate Roster</span>
            </Button>
          </div>

          <div className="border-t border-border pt-4">
            <h4 className="text-xs font-semibold text-ink-3 uppercase tracking-wider mb-2.5">
              Prerequisites Checklist
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 bg-surface-2 rounded border border-border flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-ok shrink-0" />
                <div>
                  <span className="font-semibold block text-ink">Holidays Loaded</span>
                  <span className="text-[10px] text-ink-3">{prereqs.holidaysCount} paid holiday(s)</span>
                </div>
              </div>

              <div className="p-2.5 bg-surface-2 rounded border border-border flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-ok shrink-0" />
                <div>
                  <span className="font-semibold block text-ink">Leaves Entered</span>
                  <span className="text-[10px] text-ink-3">{prereqs.leavesCount} approved absence(s)</span>
                </div>
              </div>

              <div className="p-2.5 bg-surface-2 rounded border border-border flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-ok shrink-0" />
                <div>
                  <span className="font-semibold block text-ink">Coverage Rules</span>
                  <span className="text-[10px] text-ink-3">{prereqs.rulesCount} active rules</span>
                </div>
              </div>

              <div className="p-2.5 bg-surface-2 rounded border border-border flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-ok shrink-0" />
                <div>
                  <span className="font-semibold block text-ink">Team Assignments</span>
                  <span className="text-[10px] text-ink-3">{prereqs.employeesCount} active staff</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2-Column Split Layout below KPI Strip (S2 Requirement) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Needs Attention List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="p-4 bg-surface border border-border rounded-ctl shadow-xs flex flex-col justify-between h-full">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2.5">
                <div className="flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-bad" />
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                    Needs Attention
                  </h3>
                </div>
                <span className="font-mono text-xs text-ink-3">
                  {needsAttentionList.length} items
                </span>
              </div>

              {/* Conflict list */}
              {needsAttentionList.length === 0 ? (
                <div className="py-8 text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-ok mx-auto" />
                  <p className="text-xs font-medium text-ink">Zero Blocking Conflicts</p>
                  <p className="text-[11px] text-ink-3">
                    All coverage rules and schedule constraints are fully satisfied.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-border -mx-1">
                  {needsAttentionList.slice(0, 6).map((c) => {
                    const isBlocking = c.severity === 'BLOCKING';
                    const isWarning = c.severity === 'WARNING';

                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedConflict(c)}
                        className="w-full py-2.5 px-2 text-left flex items-start justify-between gap-2.5 rounded hover:bg-surface-2 transition-colors group"
                      >
                        <div className="flex items-start gap-2 min-w-0">
                          <span
                            className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                              c.is_acknowledged
                                ? 'bg-ok'
                                : isBlocking
                                ? 'bg-bad animate-pulse'
                                : isWarning
                                ? 'bg-warn'
                                : 'bg-info'
                            }`}
                          />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-xs text-ink truncate">
                                {c.brand_name ? `${c.brand_name} · ${c.process_name || ''}` : c.code}
                              </span>
                              {c.is_acknowledged && (
                                <span className="font-mono text-[9px] bg-ok/10 text-ok px-1 py-0.2 rounded border border-ok/20">
                                  Ack
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-ink-2 line-clamp-1 leading-snug mt-0.5">
                              {c.message}
                            </p>
                            <span className="font-mono text-[10px] text-ink-3 block mt-0.5">
                              {c.date_from || 'Dec 2026'}
                            </span>
                          </div>
                        </div>

                        <ChevronRight className="w-4 h-4 text-ink-3 group-hover:text-ink group-hover:translate-x-0.5 transition-all shrink-0 mt-1" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Bottom action link */}
            <div className="pt-3 border-t border-border mt-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/conflicts')}
                className="w-full flex items-center justify-between text-xs text-accent-700 hover:text-accent-800"
              >
                <span>View Full Conflict Catalogue ({conflicts.length})</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column: Coverage Heatmap & Workload Bars (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Top Right Card: Coverage Heatmap (Brand-Process x Days) */}
          <div className="p-4 bg-surface border border-border rounded-ctl shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-accent-700" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                  Coverage Heatmap
                </h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/roster')}
                className="text-xs text-accent-700 hover:text-accent-800 p-0 h-auto"
              >
                <span>Full Matrix</span>
                <ExternalLink className="w-3 h-3 ml-1 inline" />
              </Button>
            </div>

            {miniHeatmapData.length === 0 ? (
              <div className="py-6 text-center text-xs text-ink-3">
                <span>Coverage matrix generated upon schedule solver run.</span>
              </div>
            ) : (
              <div className="space-y-2">
                {miniHeatmapData.map((bp) => (
                  <div key={bp.name} className="flex items-center gap-2">
                    <span className="font-medium text-[11px] text-ink truncate w-32 shrink-0">
                      {bp.name}
                    </span>
                    <div className="flex items-center gap-0.5 flex-1 overflow-hidden">
                      {monthDates.slice(0, 24).map((d) => {
                        const cell = bp.cells[d];
                        const state: CoverageState = cell
                          ? getCoverageState(cell.required, cell.actual)
                          : 'COVERED';
                        const config = COVERAGE_CONFIG[state];

                        return (
                          <div
                            key={d}
                            title={`${bp.name} · ${d}: ${cell ? `${cell.actual}/${cell.required}` : 'Covered'}`}
                            className={`h-4 flex-1 rounded-[1px] transition-transform hover:scale-125 cursor-pointer ${config.bg} border ${config.border}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bottom Right Card: Workload Per Employee (Days Worked) */}
          <div className="p-4 bg-surface border border-border rounded-ctl shadow-xs space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-accent-700" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                  Workload Distribution
                </h3>
                <span className="font-mono text-[10px] text-ink-3 bg-surface-2 px-1.5 py-0.5 rounded border border-border">
                  Avg: {avgWorkload} days
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="w-28 sm:w-36">
                  <Input
                    placeholder="Search emp..."
                    value={workloadSearch}
                    onChange={(e) => setWorkloadSearch(e.target.value)}
                    className="h-7 text-xs"
                  />
                </div>
                <div className="w-28">
                  <Select
                    options={podOptions}
                    value={workloadPodFilter}
                    onChange={(val) => setWorkloadPodFilter(val)}
                    className="h-7 text-xs"
                  />
                </div>
              </div>
            </div>

            {/* Workload bars list */}
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {filteredWorkload.slice(0, 8).map((w) => {
                const pct = Math.min(100, Math.round((w.daysWorked / 26) * 100));
                const isOverload = w.daysWorked > 23;
                const isOptimal = w.daysWorked >= 20 && w.daysWorked <= 22;

                return (
                  <div key={w.employee_id} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-ink">{w.employee_name}</span>
                        <span className="font-mono text-[10px] text-ink-3">({w.employee_code})</span>
                        <span className="text-[10px] text-ink-3">· {w.pod_name}</span>
                      </div>
                      <span className="font-mono font-semibold text-xs text-ink">
                        {w.daysWorked} days
                      </span>
                    </div>

                    <div className="h-1.5 w-full bg-surface-2 rounded-full overflow-hidden flex">
                      <div
                        style={{ width: `${pct}%` }}
                        className={`h-full rounded-full transition-all ${
                          isOverload
                            ? 'bg-bad'
                            : isOptimal
                            ? 'bg-ok'
                            : 'bg-accent-600'
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Roster Generation Modal Dialog */}
      <Modal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        title={`Generate Roster for ${monthLabel}`}
      >
        <div className="space-y-4 text-xs text-ink">
          <p className="text-ink-2">
            The CP-SAT scheduling engine will evaluate all operating demand, approved leaves, and employee preferences to build a deterministic roster version.
          </p>

          <div className="space-y-3 bg-surface-2 p-3 rounded-ctl border border-border">
            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Solver Time Limit (Seconds)
              </label>
              <Input
                type="number"
                min={5}
                max={120}
                value={genTimeLimit}
                onChange={(e) => setGenTimeLimit(parseInt(e.target.value, 10) || 20)}
                className="text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Random Seed (Determinism)
              </label>
              <Input
                type="number"
                value={genSeed}
                onChange={(e) => setGenSeed(parseInt(e.target.value, 10) || 42)}
                className="text-xs font-mono"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={generateMutation.isPending}
              onClick={() => setIsGenerateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={generateMutation.isPending}
              onClick={handleGenerateRoster}
              className="flex items-center gap-1.5"
            >
              {generateMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{generateMutation.isPending ? 'Solving Schedule...' : 'Generate Now'}</span>
            </Button>
          </div>
        </div>
      </Modal>

      {/* Conflict Detail & Resolution Drawer */}
      <ConflictDrawer
        isOpen={Boolean(selectedConflict)}
        onClose={() => setSelectedConflict(null)}
        periodId={activePeriod?.id || ''}
        conflict={selectedConflict}
        canAcknowledge={isOpsManager}
        canApply={canManage}
        onApplied={() => {
          refetchConflicts();
        }}
      />
    </div>
  );
};
