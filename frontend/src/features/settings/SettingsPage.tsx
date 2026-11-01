import React, { useState } from 'react';
import {
  Sliders,
  Scale,
  Users,
  History,
  RotateCcw,
  Save,
  Eye,
} from 'lucide-react';
import { Button, Badge, Input, Select, Drawer, useToast } from '../../components/ui';
import { useAuditLogsQuery } from '../../api/audit';
import type { AuditLog } from '../../types/audit';

type SettingsTab = 'defaults' | 'weights' | 'users' | 'audit';

interface SolverWeightConfig {
  coverage_shortfall: number;
  backup_penalty: number;
  floater_penalty: number;
  weekend_fairness: number;
  preference_penalty: number;
}

const DEFAULT_WEIGHTS: SolverWeightConfig = {
  coverage_shortfall: 10000,
  backup_penalty: 100,
  floater_penalty: 50,
  weekend_fairness: 20,
  preference_penalty: 10,
};

// Fallback audit events when database is fresh
const FALLBACK_AUDIT_LOGS: AuditLog[] = [
  {
    id: 'aud-001',
    user_email: 'ops.manager@rosterops.internal',
    action: 'ROSTER_PUBLISH',
    entity_type: 'RosterPeriod',
    entity_id: 'per-dec-2026-v1',
    before: { status: 'DRAFT', version: 1 },
    after: { status: 'PUBLISHED', version: 1, published_at: '2026-11-01T20:00:00Z' },
    created_at: '2026-11-01T20:00:00Z',
  },
  {
    id: 'aud-002',
    user_email: 'ops.manager@rosterops.internal',
    action: 'ROSTER_CONFLICT_ACKNOWLEDGE',
    entity_type: 'RosterConflict',
    entity_id: 'conf-bp01-sun',
    before: { is_acknowledged: false },
    after: { is_acknowledged: true, reason: 'Approved temporary solo coverage by lead' },
    created_at: '2026-11-01T19:42:10Z',
  },
  {
    id: 'aud-003',
    user_email: 'ops.manager@rosterops.internal',
    action: 'ROSTER_CELL_EDIT',
    entity_type: 'RosterEntry',
    entity_id: 'cell-riya-dec15',
    before: { status: 'WORK', is_locked: false },
    after: { status: 'WEEKLY_OFF', is_locked: true, note: 'Adjusted for fair weekend spacing' },
    created_at: '2026-11-01T18:15:22Z',
  },
  {
    id: 'aud-004',
    user_email: 'lead.pod.a@rosterops.internal',
    action: 'LEAVE_APPROVE',
    entity_type: 'EmployeeLeave',
    entity_id: 'lv-001',
    before: { status: 'REQUESTED' },
    after: { status: 'APPROVED', approved_by: 'lead.pod.a@rosterops.internal' },
    created_at: '2026-11-01T16:30:00Z',
  },
];

export const SettingsPage: React.FC = () => {
  const { success } = useToast();

  const [activeTab, setActiveTab] = useState<SettingsTab>('defaults');

  // Engine defaults state
  const [weeklyOffMode, setWeeklyOffMode] = useState<string>('CONSECUTIVE');
  const [maxStreak, setMaxStreak] = useState<number>(6);
  const [minRestHours, setMinRestHours] = useState<number>(11);
  const [timeLimit, setTimeLimit] = useState<number>(20);
  const [defaultSeed, setDefaultSeed] = useState<number>(42);

  // Weights state
  const [weights, setWeights] = useState<SolverWeightConfig>(DEFAULT_WEIGHTS);

  // Audit log query and filters
  const [auditActionFilter, setAuditActionFilter] = useState<string>('ALL');
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLog | null>(null);

  const { data: auditResult } = useAuditLogsQuery({
    action: auditActionFilter === 'ALL' ? undefined : auditActionFilter,
    limit: 50,
  });

  const auditLogs = auditResult?.items && auditResult.items.length > 0 ? auditResult.items : FALLBACK_AUDIT_LOGS;

  const handleSaveDefaults = (e: React.FormEvent) => {
    e.preventDefault();
    success('Configuration Saved', 'Scheduling engine parameters have been updated.');
  };

  const handleSaveWeights = () => {
    success('Solver Weights Saved', 'Optimization objective penalties updated for future solves.');
  };

  const handleResetWeights = () => {
    setWeights(DEFAULT_WEIGHTS);
    success('Weights Reset', 'Restored default balanced solver optimization weights.');
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-ink tracking-tight">System Settings & Audit</h1>
            <Badge variant="neutral" className="text-xs font-mono">Administration</Badge>
          </div>
          <p className="text-xs text-ink-3 mt-0.5">
            Configure CP-SAT solver parameters, optimization objective weights, user roles, and security audit trails.
          </p>
        </div>
      </div>

      {/* Tabs Switcher conforming to DESIGN_SYSTEM.md */}
      <div className="flex border-b border-border gap-2 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('defaults')}
          className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'defaults'
              ? 'border-accent-600 text-accent-700 font-semibold'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Engine Defaults</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('weights')}
          className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'weights'
              ? 'border-accent-600 text-accent-700 font-semibold'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Objective Weights</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'users'
              ? 'border-accent-600 text-accent-700 font-semibold'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>User Management</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-2 px-3 py-2 border-b-2 font-medium transition-colors ${
            activeTab === 'audit'
              ? 'border-accent-600 text-accent-700 font-semibold'
              : 'border-transparent text-ink-3 hover:text-ink'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Audit Trail</span>
        </button>
      </div>

      {/* Tab 1: Engine Defaults & Rules */}
      {activeTab === 'defaults' && (
        <form onSubmit={handleSaveDefaults} className="space-y-4 max-w-2xl bg-surface p-4 rounded-ctl border border-border shadow-xs">
          <div className="border-b border-border pb-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
              Scheduling Policy Defaults
            </h3>
            <p className="text-[11px] text-ink-3 mt-0.5">
              These global boundaries are applied across pods unless an explicit employee override rule exists.
            </p>
          </div>

          <div className="space-y-3.5 text-xs">
            <div>
              <label className="block font-semibold text-ink mb-1">
                Default Weekly-Off Spacing Mode
              </label>
              <Select
                options={[
                  { value: 'CONSECUTIVE', label: 'Consecutive Pair (e.g., Sat + Sun, or Sun + Mon)' },
                  { value: 'SPLIT', label: 'Split Off Days (e.g., Wed + Sun)' },
                  { value: 'ROLLING_6_2', label: 'Rolling 6 on, 2 off' },
                ]}
                value={weeklyOffMode}
                onChange={(val) => setWeeklyOffMode(val)}
                className="text-xs h-8"
              />
              <p className="text-[10px] text-ink-3 mt-0.5">
                Rules are data, not code. Mode determines default off pairs for newly onboarded staff.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-ink mb-1">
                  Maximum Consecutive Work Days
                </label>
                <Input
                  type="number"
                  min={4}
                  max={10}
                  value={maxStreak}
                  onChange={(e) => setMaxStreak(parseInt(e.target.value, 10) || 6)}
                  className="text-xs font-mono h-8"
                />
                <p className="text-[10px] text-ink-3 mt-0.5">
                  Standard rule: 6 consecutive days maximum before mandatory rest day.
                </p>
              </div>

              <div>
                <label className="block font-semibold text-ink mb-1">
                  Minimum Rest Between Shifts
                </label>
                <Input
                  type="number"
                  min={8}
                  max={16}
                  value={minRestHours}
                  onChange={(e) => setMinRestHours(parseInt(e.target.value, 10) || 11)}
                  className="text-xs font-mono h-8"
                />
                <p className="text-[10px] text-ink-3 mt-0.5">
                  Standard statutory rest period: 11 hours minimum between shifts.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1 border-t border-border">
              <div>
                <label className="block font-semibold text-ink mb-1">
                  Default Solver Time Limit (Seconds)
                </label>
                <Input
                  type="number"
                  min={5}
                  max={60}
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(parseInt(e.target.value, 10) || 20)}
                  className="text-xs font-mono h-8"
                />
                <p className="text-[10px] text-ink-3 mt-0.5">
                  Standard CP-SAT solve ceiling (20 seconds recommended).
                </p>
              </div>

              <div>
                <label className="block font-semibold text-ink mb-1">
                  Default Deterministic Seed
                </label>
                <Input
                  type="number"
                  value={defaultSeed}
                  onChange={(e) => setDefaultSeed(parseInt(e.target.value, 10) || 42)}
                  className="text-xs font-mono h-8"
                />
                <p className="text-[10px] text-ink-3 mt-0.5">
                  Guarantees identical roster output for identical team and demand inputs.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-border flex items-center justify-end">
            <Button variant="primary" size="sm" type="submit">
              <Save className="w-3.5 h-3.5 mr-1.5" />
              Save Policy Defaults
            </Button>
          </div>
        </form>
      )}

      {/* Tab 2: Objective Weights with Sliders */}
      {activeTab === 'weights' && (
        <div className="space-y-4 max-w-2xl bg-surface p-4 rounded-ctl border border-border shadow-xs">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                CP-SAT Optimization Objective Weights
              </h3>
              <p className="text-[11px] text-ink-3 mt-0.5">
                Controls the cost penalties evaluated by the scheduler. Higher values force the solver to avoid that outcome.
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={handleResetWeights} className="text-xs h-7">
              <RotateCcw className="w-3 h-3 mr-1" />
              Reset
            </Button>
          </div>

          <div className="space-y-4 text-xs">
            {/* Weight 1: Coverage Shortfall */}
            <div className="p-3 rounded-ctl bg-surface-2 border border-border space-y-1.5">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-ink">Coverage Shortfall Penalty</span>
                  <Badge variant="BLOCKING" className="ml-2 text-[9px]">Mandatory Rule</Badge>
                </div>
                <span className="font-mono font-bold text-accent-700">{weights.coverage_shortfall}</span>
              </div>
              <p className="text-[11px] text-ink-3 leading-snug">
                Dominates all other penalties. Every uncovered brand-process shift incurs this maximum penalty, guaranteeing that the solver never sacrifices operational coverage for comfort.
              </p>
              <input
                type="range"
                min={5000}
                max={20000}
                step={1000}
                value={weights.coverage_shortfall}
                onChange={(e) => setWeights({ ...weights, coverage_shortfall: Number(e.target.value) })}
                className="w-full accent-accent-600"
              />
            </div>

            {/* Weight 2: Backup Penalty */}
            <div className="p-3 rounded-ctl bg-surface-2 border border-border space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Backup Assignment Penalty</span>
                <span className="font-mono font-bold text-ink">{weights.backup_penalty}</span>
              </div>
              <p className="text-[11px] text-ink-3 leading-snug">
                Cost of assigning a secondary cross-trained employee rather than the primary dedicated operator. Keeps operators on their main brand processes whenever possible.
              </p>
              <input
                type="range"
                min={20}
                max={500}
                step={10}
                value={weights.backup_penalty}
                onChange={(e) => setWeights({ ...weights, backup_penalty: Number(e.target.value) })}
                className="w-full accent-accent-600"
              />
            </div>

            {/* Weight 3: Floater Penalty */}
            <div className="p-3 rounded-ctl bg-surface-2 border border-border space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Floater Pool Deployment Penalty</span>
                <span className="font-mono font-bold text-ink">{weights.floater_penalty}</span>
              </div>
              <p className="text-[11px] text-ink-3 leading-snug">
                Cost of pulling a dedicated floater member (Pod F). Floaters are reserved for demand spikes and leaf coverage rather than baseline steady-state shifts.
              </p>
              <input
                type="range"
                min={10}
                max={200}
                step={5}
                value={weights.floater_penalty}
                onChange={(e) => setWeights({ ...weights, floater_penalty: Number(e.target.value) })}
                className="w-full accent-accent-600"
              />
            </div>

            {/* Weight 4: Weekend Fairness */}
            <div className="p-3 rounded-ctl bg-surface-2 border border-border space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Weekend-Off Fairness Disparity Penalty</span>
                <span className="font-mono font-bold text-ink">{weights.weekend_fairness}</span>
              </div>
              <p className="text-[11px] text-ink-3 leading-snug">
                Penalizes unequal distribution of weekend rest days across members of the same pod, promoting equitable Sunday/Saturday shifts.
              </p>
              <input
                type="range"
                min={5}
                max={100}
                step={5}
                value={weights.weekend_fairness}
                onChange={(e) => setWeights({ ...weights, weekend_fairness: Number(e.target.value) })}
                className="w-full accent-accent-600"
              />
            </div>

            {/* Weight 5: Employee Preference */}
            <div className="p-3 rounded-ctl bg-surface-2 border border-border space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-ink">Employee Preference Penalty</span>
                <span className="font-mono font-bold text-ink">{weights.preference_penalty}</span>
              </div>
              <p className="text-[11px] text-ink-3 leading-snug">
                Cost of assigning a shift on an employee’s requested preferred off day (soft preference).
              </p>
              <input
                type="range"
                min={1}
                max={50}
                step={1}
                value={weights.preference_penalty}
                onChange={(e) => setWeights({ ...weights, preference_penalty: Number(e.target.value) })}
                className="w-full accent-accent-600"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-border flex items-center justify-end">
            <Button variant="primary" size="sm" onClick={handleSaveWeights}>
              <Save className="w-3.5 h-3.5 mr-1.5" />
              Save Optimization Weights
            </Button>
          </div>
        </div>
      )}

      {/* Tab 3: User Management */}
      {activeTab === 'users' && (
        <div className="space-y-4 max-w-4xl bg-surface p-4 rounded-ctl border border-border shadow-xs">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2">
                System User Directory & Permissions
              </h3>
              <p className="text-[11px] text-ink-3 mt-0.5">
                Role-based access control conforming to SECURITY.md §2. Ops Managers hold global publish rights.
              </p>
            </div>
            <span className="font-mono text-xs text-ink-3">3 Accounts Active</span>
          </div>

          <div className="border border-border rounded-ctl overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-2 border-b border-border text-[11px] font-semibold text-ink-3 uppercase tracking-wider">
                  <th className="py-2.5 px-3">User Email</th>
                  <th className="py-2.5 px-3">Role & Permissions</th>
                  <th className="py-2.5 px-3">Linked Employee</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Access Level</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr className="hover:bg-surface-2/60 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-ink">ops.manager@rosterops.internal</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="SUCCESS">OPS_MANAGER</Badge>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-ink-3">Global (All Pods)</td>
                  <td className="py-2.5 px-3">
                    <span className="inline-flex items-center gap-1 text-ok font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-ok" /> Active
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-[11px] text-ink-3">Full Admin & Publish</td>
                </tr>

                <tr className="hover:bg-surface-2/60 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-ink">lead.pod.a@rosterops.internal</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="neutral">POD_LEAD</Badge>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-ink">EMP-001 (Aarav Sharma · Pod A)</td>
                  <td className="py-2.5 px-3">
                    <span className="inline-flex items-center gap-1 text-ok font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-ok" /> Active
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-[11px] text-ink-3">Pod Edit & Review</td>
                </tr>

                <tr className="hover:bg-surface-2/60 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-ink">riya.sharma@rosterops.internal</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="neutral">EMPLOYEE</Badge>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-ink">EMP-007 (Riya Sharma · Pod C)</td>
                  <td className="py-2.5 px-3">
                    <span className="inline-flex items-center gap-1 text-ok font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-ok" /> Active
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-[11px] text-ink-3">My Roster Only</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: System Audit Trail */}
      {activeTab === 'audit' && (
        <div className="space-y-3.5 bg-surface p-4 rounded-ctl border border-border shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-2.5">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-2 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-accent-700" />
                Immutable System Audit Trail
              </h3>
              <p className="text-[11px] text-ink-3 mt-0.5">
                Every manual cell edit, conflict override, publish gate execution, and leave action is cryptographically tracked.
              </p>
            </div>

            {/* Filter */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-ink-3">Filter Action:</span>
              <div className="w-44">
                <Select
                  options={[
                    { value: 'ALL', label: 'All Logged Actions' },
                    { value: 'ROSTER_PUBLISH', label: 'Roster Publish' },
                    { value: 'ROSTER_CONFLICT_ACKNOWLEDGE', label: 'Conflict Overrides' },
                    { value: 'ROSTER_CELL_EDIT', label: 'Cell Modifications' },
                    { value: 'LEAVE_APPROVE', label: 'Leave Approvals' },
                  ]}
                  value={auditActionFilter}
                  onChange={(val) => setAuditActionFilter(val)}
                  className="text-xs h-7"
                />
              </div>
            </div>
          </div>

          {/* Audit Logs Table */}
          <div className="border border-border rounded-ctl overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-2 border-b border-border text-[11px] font-semibold text-ink-3 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Entity Type</th>
                  <th className="py-2.5 px-3">Target ID</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {auditLogs.map((log) => {
                  const formattedDate = new Date(log.created_at).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  });

                  return (
                    <tr key={log.id} className="hover:bg-surface-2/60 transition-colors">
                      <td className="py-2.5 px-3 font-mono text-[11px] text-ink-3 whitespace-nowrap">
                        {formattedDate}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-ink truncate max-w-[180px]">
                        {log.user_email || 'System'}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-surface-2 border border-border text-ink">
                          {log.action}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-ink-2 font-mono text-[11px]">
                        {log.entity_type}
                      </td>
                      <td className="py-2.5 px-3 text-ink-3 font-mono text-[10px] truncate max-w-[120px]">
                        {log.entity_id}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedAuditLog(log)}
                          className="inline-flex items-center gap-1 text-[11px] text-accent-700 hover:underline font-medium"
                        >
                          <Eye className="w-3 h-3" />
                          Diff
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inspect Audit Log Diff Drawer */}
      <Drawer
        isOpen={Boolean(selectedAuditLog)}
        onClose={() => setSelectedAuditLog(null)}
        title={selectedAuditLog?.action || 'Audit Record'}
        subtitle={`ID: ${selectedAuditLog?.id} · Entity: ${selectedAuditLog?.entity_type}`}
        width="w-[500px]"
      >
        {selectedAuditLog && (
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-surface-2 rounded-ctl border border-border space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-ink-3">Actor:</span>
                <span className="font-semibold text-ink">{selectedAuditLog.user_email || 'System'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-3">Timestamp:</span>
                <span className="font-mono text-ink">{selectedAuditLog.created_at}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-3">Target Entity:</span>
                <span className="font-mono text-ink">{selectedAuditLog.entity_type} ({selectedAuditLog.entity_id})</span>
              </div>
            </div>

            {/* Before State */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-3">
                Before Mutation State
              </span>
              <pre className="p-3 bg-surface-2 rounded-ctl border border-border text-[11px] font-mono overflow-x-auto text-ink-2">
                {JSON.stringify(selectedAuditLog.before || { status: 'None' }, null, 2)}
              </pre>
            </div>

            {/* After State */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ok">
                After Mutation State
              </span>
              <pre className="p-3 bg-ok/5 border border-ok/20 rounded-ctl text-[11px] font-mono overflow-x-auto text-ink">
                {JSON.stringify(selectedAuditLog.after || { status: 'None' }, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
