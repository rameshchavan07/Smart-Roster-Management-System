import React from 'react';
import { useMonth } from './context/MonthContext';

export { AppShell as Layout } from './components/layout';
export { DashboardPage } from './features/dashboard/DashboardPage';

export const DashboardPlaceholder: React.FC = () => {
  const { monthLabel } = useMonth();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink">Dashboard</h2>
          <p className="text-xs text-ink-2">
            Operational metrics and roster health overview for {monthLabel}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-ctl border border-border bg-surface p-4">
          <p className="text-xs text-ink-3">Coverage Target</p>
          <p className="mt-1 text-2xl font-semibold font-mono text-ok">99.1%</p>
        </div>
        <div className="rounded-ctl border border-border bg-surface p-4">
          <p className="text-xs text-ink-3">Blocking Conflicts</p>
          <p className="mt-1 text-2xl font-semibold font-mono text-bad">2</p>
        </div>
        <div className="rounded-ctl border border-border bg-surface p-4">
          <p className="text-xs text-ink-3">Warnings</p>
          <p className="mt-1 text-2xl font-semibold font-mono text-warn">5</p>
        </div>
        <div className="rounded-ctl border border-border bg-surface p-4">
          <p className="text-xs text-ink-3">Single-Point Brands</p>
          <p className="mt-1 text-2xl font-semibold font-mono text-ink">14</p>
        </div>
      </div>
    </div>
  );
};

export const RosterPlaceholder: React.FC = () => {
  const { monthLabel } = useMonth();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink">Roster Workspace</h2>
          <p className="text-xs text-ink-2">
            Plan, validate, and manage {monthLabel} roster
          </p>
        </div>
      </div>
      <div className="flex h-72 items-center justify-center rounded-ctl border border-dashed border-border-strong bg-surface">
        <p className="text-xs text-ink-3 font-mono">
          RosterGrid workspace ready for {monthLabel}
        </p>
      </div>
    </div>
  );
};
