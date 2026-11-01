import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Sparkles,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Layers,
  LayoutGrid,
  Loader2,
  Wrench,
  RotateCcw,
} from 'lucide-react';
import {
  Button,
  Input,
  Select,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  useToast,
  Skeleton,
} from '../../components/ui';
import { useMonth } from '../../context/MonthContext';
import { useAuth } from '../auth/AuthContext';
import { showApiErrorToast } from '../../api/errorMapping';
import {
  useRosterPeriodsQuery,
  useRosterGridQuery,
  useRosterImpactMutation,
  useRepairRosterMutation,
  useUpdateRosterEntriesMutation,
} from '../../api/rosters';
import { useEmployeesQuery } from '../../api/team';
import type {
  ImpactChangeType,
  RosterEntryStatus,
  RosterImpactResponse,
  RosterRepairResponse,
} from '../../types/roster';

export const ImpactSimulatorPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentMonth, monthLabel } = useMonth();
  const { isOpsManager, isPodLead } = useAuth();
  const toast = useToast();

  const canEdit = isOpsManager || isPodLead;

  // Form states
  const [changeType, setChangeType] = useState<ImpactChangeType>(
    (searchParams.get('type') as ImpactChangeType) || 'ADD_LEAVE'
  );
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>(
    searchParams.get('employeeId') || ''
  );
  const [startDate, setStartDate] = useState<string>(
    searchParams.get('date') || `${currentMonth}-14`
  );
  const [endDate, setEndDate] = useState<string>(
    searchParams.get('endDate') || searchParams.get('date') || `${currentMonth}-14`
  );
  const [targetStatus, setTargetStatus] = useState<RosterEntryStatus>('LEAVE');
  const [reason, setReason] = useState<string>('What-if simulated operational change');

  // Simulation result & repair result states
  const [simulationResult, setSimulationResult] = useState<RosterImpactResponse | null>(null);
  const [repairResult, setRepairResult] = useState<RosterRepairResponse | null>(null);

  // Queries
  const { data: periods } = useRosterPeriodsQuery(currentMonth);
  const activePeriod = periods && periods.length > 0 ? periods[0] : null;

  const { data: gridData, refetch: refetchGrid } = useRosterGridQuery(activePeriod?.id, 'company');
  const { data: employeesResult } = useEmployeesQuery({ limit: 200 });

  // Mutations
  const impactMutation = useRosterImpactMutation();
  const repairMutation = useRepairRosterMutation();
  const updateEntriesMutation = useUpdateRosterEntriesMutation();

  const employees = employeesResult?.items || [];

  // Auto-select first employee if none selected
  useEffect(() => {
    if (!selectedEmployeeId && employees.length > 0) {
      setSelectedEmployeeId(employees[0].id);
    }
  }, [selectedEmployeeId, employees]);

  // Selected employee metadata
  const selectedEmployee = useMemo(() => {
    return employees.find((e) => e.id === selectedEmployeeId);
  }, [employees, selectedEmployeeId]);

  // Execute simulation
  const handleRunSimulation = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!activePeriod?.id) {
      toast.error('No Active Roster', 'Cannot simulate without an active roster period.');
      return;
    }

    try {
      const res = await impactMutation.mutateAsync({
        periodId: activePeriod.id,
        request: {
          changes: [
            {
              type: changeType,
              employee_id: selectedEmployeeId || undefined,
              start_date: startDate,
              end_date: endDate || startDate,
              date: startDate,
              status: changeType === 'ADD_LEAVE' ? 'LEAVE' : targetStatus,
            },
          ],
        },
      });

      setSimulationResult(res);
      setRepairResult(null);
      toast.success('Simulation Complete', `Evaluated schedule impact for ${selectedEmployee?.full_name || 'employee'}.`);
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Simulation Failed');
    }
  };

  // Run initial simulation if query params were passed in URL
  useEffect(() => {
    if (activePeriod?.id && selectedEmployeeId && searchParams.get('autoRun') === 'true') {
      handleRunSimulation();
    }
  }, [activePeriod?.id, selectedEmployeeId]);

  // Apply change directly to draft roster
  const handleApplyChange = async () => {
    if (!activePeriod?.id || !canEdit) return;

    try {
      // Generate date sequence
      const start = new Date(startDate);
      const end = new Date(endDate || startDate);
      const entries = [];

      const cur = new Date(start);
      while (cur <= end) {
        const isoDate = cur.toISOString().split('T')[0];
        entries.push({
          employee_id: selectedEmployeeId,
          date: isoDate,
          status: changeType === 'ADD_LEAVE' ? ('LEAVE' as RosterEntryStatus) : targetStatus,
          source: 'MANUAL' as const,
          is_locked: true,
          reason: reason || 'Applied from What-If Simulator',
        });
        cur.setDate(cur.getDate() + 1);
      }

      await updateEntriesMutation.mutateAsync({
        periodId: activePeriod.id,
        request: {
          entries,
        },
      });

      toast.success('Changes Applied', `Updated ${entries.length} cell(s) for ${selectedEmployee?.full_name}.`);
      refetchGrid();
      navigate('/roster');
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Failed to apply changes');
    }
  };

  // Apply change AND trigger local solver repair
  const handleApplyAndRepair = async () => {
    if (!activePeriod?.id || !canEdit) return;

    try {
      toast.info('Executing Repair', 'Applying changes and solving impacted window with solver...');

      // 1. Apply cell updates first
      const start = new Date(startDate);
      const end = new Date(endDate || startDate);
      const entries = [];
      const affectedDates: string[] = [];

      const cur = new Date(start);
      while (cur <= end) {
        const isoDate = cur.toISOString().split('T')[0];
        entries.push({
          employee_id: selectedEmployeeId,
          date: isoDate,
          status: changeType === 'ADD_LEAVE' ? ('LEAVE' as RosterEntryStatus) : targetStatus,
          source: 'MANUAL' as const,
          is_locked: true,
          reason: reason || 'Applied from What-If Simulator with repair',
        });
        affectedDates.push(isoDate);
        cur.setDate(cur.getDate() + 1);
      }

      await updateEntriesMutation.mutateAsync({
        periodId: activePeriod.id,
        request: {
          entries,
        },
      });

      // 2. Trigger local repair around impacted window
      const repairRes = await repairMutation.mutateAsync({
        periodId: activePeriod.id,
        request: {
          dates: affectedDates,
          date_from: startDate,
          date_to: endDate || startDate,
          employee_ids: selectedEmployeeId ? [selectedEmployeeId] : [],
          apply: true,
        },
      });

      setRepairResult(repairRes);
      toast.success(
        'Repair Completed',
        `Repaired ${repairRes.repaired_cells_count} cell(s) in ${repairRes.solve_time_seconds.toFixed(2)}s.`
      );
      refetchGrid();
    } catch (err: unknown) {
      showApiErrorToast(err, toast, 'Local repair failed');
    }
  };

  const handleDiscard = () => {
    setSimulationResult(null);
    setRepairResult(null);
    setReason('What-if simulated operational change');
  };

  // Build remaining employees vs demand matrix for affected dates
  const capacityMatrix = useMemo(() => {
    if (!simulationResult || !gridData) return [];

    const dates = simulationResult.affected_dates && simulationResult.affected_dates.length > 0
      ? simulationResult.affected_dates
      : [startDate];

    const resultRows = [];

    for (const d of dates) {
      // Find employees working on this date
      const workingStaff = gridData.rows.filter((r) => {
        const cell = r.cells[d];
        if (!cell) return false;
        // If it's the simulated employee and simulated status is LEAVE/WEEKLY_OFF, they are not working
        if (r.employee_id === selectedEmployeeId) {
          const simStatus = changeType === 'ADD_LEAVE' ? 'LEAVE' : targetStatus;
          return simStatus === 'WORK' || simStatus === 'HOLIDAY_WORK';
        }
        return cell.status === 'WORK' || cell.status === 'HOLIDAY_WORK';
      });

      const empRow = gridData.rows.find((r) => r.employee_id === selectedEmployeeId);
      const brandName = empRow?.primary_assignments?.length
        ? empRow.primary_assignments.join(', ')
        : selectedEmployee?.pod_name
        ? `${selectedEmployee.pod_name} Pool`
        : 'Assigned Processes';

      // Minimum required demand (estimated default or 2)
      const required = 2;
      const actual = workingStaff.length;
      const isCovered = actual >= required;

      resultRows.push({
        date: d,
        brandProcess: brandName,
        required,
        beforeActual: actual + 1, // before taking leave
        afterActual: actual,
        remainingEmployees: workingStaff.map((w) => w.employee_name),
        isCovered,
      });
    }

    return resultRows;
  }, [simulationResult, gridData, startDate, selectedEmployeeId, changeType, targetStatus, selectedEmployee]);

  const changeTypeOptions = [
    { value: 'ADD_LEAVE', label: 'Add Planned Leave (ABSENCE)' },
    { value: 'MARK_UNAVAILABLE', label: 'Mark Unavailable (REST / OFF)' },
    { value: 'CELL_EDIT', label: 'Direct Shift Status Override' },
    { value: 'REMOVE_LEAVE', label: 'Remove Existing Leave (RESTORE)' },
  ];

  const employeeOptions = employees.map((e) => ({
    value: e.id,
    label: `${e.full_name} (${e.code}) · ${e.pod_name || 'Floater'}`,
  }));

  const statusOptions = [
    { value: 'WEEKLY_OFF', label: 'Weekly Off (WO)' },
    { value: 'LEAVE', label: 'Planned Leave (L)' },
    { value: 'COMP_OFF', label: 'Comp-Off (CO)' },
    { value: 'WORK', label: 'Regular Work (W)' },
    { value: 'HOLIDAY_WORK', label: 'Holiday Work (HW)' },
  ];

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-ctl bg-accent-100 text-accent-700">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-ink">
              What-If Impact Simulator
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-2 text-ink-2 border border-border">
              {monthLabel}
            </span>
          </div>
          <p className="text-xs text-ink-3 mt-1">
            Dry-run proposed leaves or cell changes, inspect remaining multi-person capacity, and heal gaps with local solver repair.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/conflicts')}
            className="flex items-center gap-1.5"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Conflicts</span>
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

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Change Configuration Form (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <form
            onSubmit={handleRunSimulation}
            className="p-4 bg-surface border border-border rounded-ctl shadow-xs space-y-4"
          >
            <div className="border-b border-border pb-2.5 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-accent-700" />
                <span>1. Proposed Modification</span>
              </h3>
              <span className="text-[10px] text-ink-3">Dry-run mode</span>
            </div>

            {/* Change Type Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Change Action Type
              </label>
              <Select
                options={changeTypeOptions}
                value={changeType}
                onChange={(val) => setChangeType(val as ImpactChangeType)}
                className="text-xs"
              />
            </div>

            {/* Employee Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Employee Target
              </label>
              <Select
                options={employeeOptions}
                value={selectedEmployeeId}
                onChange={(val) => setSelectedEmployeeId(val)}
                className="text-xs"
              />
              {selectedEmployee && (
                <div className="mt-1.5 p-2 bg-surface-2 rounded border border-border flex items-center justify-between text-[11px] text-ink-2">
                  <span>Pod / Scope:</span>
                  <span className="font-medium text-ink truncate max-w-[200px]">
                    {selectedEmployee.pod_name || (selectedEmployee.is_floater ? 'Dedicated Floater' : 'Pod Member')}
                  </span>
                </div>
              )}
            </div>

            {/* Date Range Fields */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                  Start Date
                </label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                  End Date
                </label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="text-xs font-mono"
                />
              </div>
            </div>

            {/* Shift Status Selector (if cell edit / mark unavailable) */}
            {changeType !== 'ADD_LEAVE' && changeType !== 'REMOVE_LEAVE' && (
              <div>
                <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                  Target Shift Status
                </label>
                <Select
                  options={statusOptions}
                  value={targetStatus}
                  onChange={(val) => setTargetStatus(val as RosterEntryStatus)}
                  className="text-xs"
                />
              </div>
            )}

            {/* Simulation Note */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-3 uppercase tracking-wider mb-1">
                Simulation Note / Justification
              </label>
              <Input
                type="text"
                placeholder="e.g. Unplanned medical leave, emergency swap"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="text-xs"
              />
            </div>

            {/* Submit Simulation Button */}
            <Button
              type="submit"
              variant="primary"
              disabled={impactMutation.isPending || !activePeriod}
              className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold"
            >
              {impactMutation.isPending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Evaluating Schedule Impact...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Run What-If Simulation</span>
                </>
              )}
            </Button>
          </form>

          {/* Guidelines Box */}
          <div className="p-3.5 bg-surface-2/60 border border-border rounded-ctl text-xs text-ink-2 space-y-2">
            <h4 className="font-semibold text-ink text-[11px] uppercase tracking-wider">
              Simulation Rules
            </h4>
            <ul className="list-disc pl-4 space-y-1 text-[11px] text-ink-3">
              <li>Evaluations run purely in-memory and will <strong>not mutate database state</strong> until applied.</li>
              <li>Calculates all first-order coverage shortfalls and second-order worker streak violations.</li>
              <li>Multi-person brand pools automatically compute remaining staffing capacity vs minimum demand.</li>
            </ul>
          </div>
        </div>

        {/* Right Column: Before -> After Results & Capacity Matrix (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {!simulationResult && !impactMutation.isPending ? (
            <div className="p-12 border border-dashed border-border-strong rounded-ctl bg-surface text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-surface-2 flex items-center justify-center mx-auto text-ink-3">
                <Sparkles className="w-6 h-6 text-accent-700" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-ink">Ready for What-If Analysis</h3>
                <p className="text-xs text-ink-3 max-w-md mx-auto mt-1">
                  Select a proposed leave or status change on the left and click <strong>"Run What-If Simulation"</strong> to inspect before/after conflict diffs and remaining employee capacity.
                </p>
              </div>
            </div>
          ) : impactMutation.isPending ? (
            <div className="p-10 border border-border rounded-ctl bg-surface space-y-4">
              <div className="flex items-center gap-2 text-ink">
                <Loader2 className="w-4 h-4 animate-spin text-accent-700" />
                <span className="font-medium text-xs">Simulating matrix constraint impact...</span>
              </div>
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : (
            simulationResult && (
              <div className="space-y-4 animate-in fade-in duration-150">
                {/* Feasibility Alert Banner */}
                <div
                  className={`p-3.5 border rounded-ctl flex items-start justify-between gap-3 ${
                    simulationResult.is_feasible
                      ? 'bg-ok/5 border-ok/30 text-ink'
                      : 'bg-bad/5 border-bad/30 text-ink'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    {simulationResult.is_feasible ? (
                      <CheckCircle2 className="w-5 h-5 text-ok shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-bad shrink-0 mt-0.5" />
                    )}
                    <div>
                      <h4 className="font-semibold text-xs leading-tight">
                        {simulationResult.is_feasible
                          ? 'Feasible: Proposed Change Preserves Coverage'
                          : `Infeasible: Opens ${simulationResult.new_conflicts.length} New Conflict(s)`}
                      </h4>
                      <p className="text-[11px] text-ink-2 mt-0.5">
                        {simulationResult.is_feasible
                          ? 'No blocking coverage shortfalls or hard constraint violations introduced.'
                          : 'Applying this change will introduce blocking gaps that require backup reallocation or solver repair.'}
                      </p>
                    </div>
                  </div>

                  <Badge
                    variant={simulationResult.is_feasible ? 'SUCCESS' : 'BLOCKING'}
                    className="shrink-0 font-mono text-[11px]"
                  >
                    {simulationResult.is_feasible ? 'FEASIBLE' : 'INFEASIBLE'}
                  </Badge>
                </div>

                {/* Before -> After KPI Comparison Strip */}
                <div className="grid grid-cols-4 gap-2.5">
                  <div className="p-3 bg-surface border border-border rounded-card text-center">
                    <span className="text-[10px] font-semibold text-ink-3 uppercase tracking-wider block">
                      Net Delta
                    </span>
                    <span
                      className={`text-xl font-bold font-mono mt-1 block ${
                        simulationResult.net_conflict_change > 0
                          ? 'text-bad'
                          : simulationResult.net_conflict_change < 0
                          ? 'text-ok'
                          : 'text-ink-2'
                      }`}
                    >
                      {simulationResult.net_conflict_change > 0
                        ? `+${simulationResult.net_conflict_change}`
                        : simulationResult.net_conflict_change}
                    </span>
                  </div>

                  <div className="p-3 bg-surface border border-border rounded-card text-center">
                    <span className="text-[10px] font-semibold text-bad uppercase tracking-wider block">
                      New Gaps
                    </span>
                    <span className="text-xl font-bold font-mono text-bad mt-1 block">
                      +{simulationResult.new_conflicts.length}
                    </span>
                  </div>

                  <div className="p-3 bg-surface border border-border rounded-card text-center">
                    <span className="text-[10px] font-semibold text-ok uppercase tracking-wider block">
                      Resolved
                    </span>
                    <span className="text-xl font-bold font-mono text-ok mt-1 block">
                      -{simulationResult.resolved_conflicts.length}
                    </span>
                  </div>

                  <div className="p-3 bg-surface border border-border rounded-card text-center">
                    <span className="text-[10px] font-semibold text-ink-3 uppercase tracking-wider block">
                      Unchanged
                    </span>
                    <span className="text-xl font-bold font-mono text-ink mt-1 block">
                      {simulationResult.unchanged}
                    </span>
                  </div>
                </div>

                {/* Remaining Employees vs Demand Matrix */}
                <div className="p-3.5 bg-surface border border-border rounded-ctl space-y-2.5">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-2 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-accent-700" />
                      <span>Remaining Staff vs Demand Matrix</span>
                    </h4>
                    <span className="text-[10px] text-ink-3 font-mono">
                      {capacityMatrix.length} impacted date(s)
                    </span>
                  </div>

                  <Table dense>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[90px]">Date</TableHead>
                        <TableHead className="min-w-[130px]">Brand / Pool</TableHead>
                        <TableHead className="w-[70px] text-center">Required</TableHead>
                        <TableHead className="w-[80px] text-center">Remaining</TableHead>
                        <TableHead className="min-w-[140px]">Available On Duty</TableHead>
                        <TableHead className="w-[90px] text-right">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {capacityMatrix.map((row) => (
                        <TableRow key={row.date}>
                          <TableCell className="font-mono text-[11px] font-medium text-ink">
                            {row.date}
                          </TableCell>
                          <TableCell className="font-medium text-ink text-xs">
                            {row.brandProcess}
                          </TableCell>
                          <TableCell className="text-center font-mono font-semibold text-xs">
                            {row.required}
                          </TableCell>
                          <TableCell className="text-center font-mono text-xs">
                            <span className={row.afterActual < row.required ? 'text-bad font-bold' : 'text-ok font-bold'}>
                              {row.afterActual}
                            </span>
                            <span className="text-[10px] text-ink-3"> / {row.beforeActual}</span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1 flex-wrap">
                              {row.remainingEmployees.length > 0 ? (
                                row.remainingEmployees.map((emp) => (
                                  <span
                                    key={emp}
                                    className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-ink-2 border border-border"
                                  >
                                    {emp}
                                  </span>
                                ))
                              ) : (
                                <span className="text-[10px] text-bad italic">0 employees on duty</span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${
                                row.isCovered
                                  ? 'bg-ok/10 text-ok border-ok/20'
                                  : 'bg-bad/10 text-bad border-bad/20'
                              }`}
                            >
                              {row.isCovered ? 'COVERED' : 'UNDERSTAFFED'}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* New Conflicts List */}
                {simulationResult.new_conflicts.length > 0 && (
                  <div className="p-3.5 bg-surface border border-border rounded-ctl space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-bad flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-bad" />
                      <span>New Conflicts Introduced ({simulationResult.new_conflicts.length})</span>
                    </h4>

                    <div className="space-y-2">
                      {simulationResult.new_conflicts.map((c, i) => (
                        <div
                          key={i}
                          className="p-2.5 rounded border border-bad/20 bg-bad/5 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-semibold text-bad">
                              {c.code} · {c.brand || 'System'}
                            </span>
                            <span className="font-mono text-[10px] text-ink-3">
                              {c.date || startDate}
                            </span>
                          </div>
                          <p className="text-ink font-medium leading-snug">{c.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Local Repair Result Box (if repair was executed) */}
                {repairResult && (
                  <div className="p-3.5 bg-accent-50/50 border border-accent-600 rounded-ctl space-y-2 animate-in zoom-in-95 duration-100">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-accent-800 flex items-center gap-1.5 uppercase tracking-wider">
                        <Wrench className="w-3.5 h-3.5 text-accent-700" />
                        <span>Solver Local Repair Output</span>
                      </h4>
                      <Badge variant="SUCCESS" className="font-mono text-[10px]">
                        {repairResult.solver_status}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                      <div className="p-2 bg-surface rounded border border-border">
                        <span className="text-[10px] text-ink-3 block">Repaired Cells</span>
                        <span className="font-bold font-mono text-accent-700">
                          {repairResult.repaired_cells_count}
                        </span>
                      </div>
                      <div className="p-2 bg-surface rounded border border-border">
                        <span className="text-[10px] text-ink-3 block">Solve Time</span>
                        <span className="font-bold font-mono text-ink">
                          {repairResult.solve_time_seconds.toFixed(2)}s
                        </span>
                      </div>
                      <div className="p-2 bg-surface rounded border border-border">
                        <span className="text-[10px] text-ink-3 block">Resolved Gaps</span>
                        <span className="font-bold font-mono text-ok">
                          {repairResult.resolved_conflicts.length}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Bottom Action Buttons (S5 requirement: Apply change, Apply + repair, Discard) */}
                <div className="p-3 bg-surface border border-border rounded-ctl flex items-center justify-between gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleDiscard}
                    className="flex items-center gap-1 text-xs text-ink-3 hover:text-ink"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Discard / Reset</span>
                  </Button>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={!canEdit || updateEntriesMutation.isPending}
                      onClick={handleApplyChange}
                      className="text-xs"
                    >
                      {updateEntriesMutation.isPending ? 'Applying...' : 'Apply Change'}
                    </Button>

                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      disabled={!canEdit || repairMutation.isPending}
                      onClick={handleApplyAndRepair}
                      className="flex items-center gap-1.5 text-xs font-semibold"
                    >
                      {repairMutation.isPending ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Solving Repair Window...</span>
                        </>
                      ) : (
                        <>
                          <Wrench className="w-3.5 h-3.5" />
                          <span>Apply + Local Repair</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};
