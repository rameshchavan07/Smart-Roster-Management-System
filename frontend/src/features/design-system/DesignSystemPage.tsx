import React, { useState } from 'react';
import {
  Button,
  Input,
  Badge,
  Skeleton,
  EmptyState,
  Modal,
  Drawer,
  StatusCell,
  RosterStatusCode,
} from '../../components/ui';
import { Calendar, AlertTriangle, Layers, Info } from 'lucide-react';

export const DesignSystemPage: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState<RosterStatusCode>('W');

  const statusCodes: RosterStatusCode[] = ['W', 'WO', 'PH', 'HW', 'L', 'CO'];

  return (
    <div className="min-h-screen bg-bg text-ink p-8 max-w-7xl mx-auto space-y-12">
      <header className="border-b border-border pb-6">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-ctl bg-accent-600 text-white font-mono font-bold flex items-center justify-center text-sm">
            RO
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">RosterOps Design System</h1>
            <p className="text-sm text-ink-2">
              Calm, dense, trustworthy operations software design tokens and component library
            </p>
          </div>
        </div>
      </header>

      {/* 1. Colour Tokens */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink flex items-center gap-2">
          <Layers className="w-4 h-4 text-accent-600" />
          1. Design Tokens & Palette
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Neutrals */}
          <div className="bg-surface p-4 rounded-ctl border border-border space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">Neutrals (Warm Grey)</h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-bg border border-border">
                <span>--bg: #F7F6F3</span>
                <span className="text-ink-3 text-[11px]">App Background</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-surface border border-border">
                <span>--surface: #FFFFFF</span>
                <span className="text-ink-3 text-[11px]">Panels, Tables</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-surface-2 border border-border">
                <span>--surface-2: #F1EFEA</span>
                <span className="text-ink-3 text-[11px]">Headers, Zebra</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-border text-ink">
                <span>--border: #E2DFD8</span>
                <span className="text-ink-3 text-[11px]">Hairlines</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-border-strong text-ink">
                <span>--border-strong: #CFCBC1</span>
                <span className="text-ink-3 text-[11px]">Controls</span>
              </div>
            </div>
          </div>

          {/* Accent Palette */}
          <div className="bg-surface p-4 rounded-ctl border border-border space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">Accent (Teal-Green)</h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-accent-50 text-accent-700 border border-accent-100">
                <span>--accent-50: #EEF7F6</span>
                <span className="text-[11px]">Hover Tint</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-accent-100 text-accent-700 border border-accent-100">
                <span>--accent-100: #DCEEEC</span>
                <span className="text-[11px]">Selected Row</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-accent-600 text-white">
                <span>--accent-600: #0F6B64</span>
                <span className="text-[11px]">Primary Button</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-accent-700 text-white">
                <span>--accent-700: #0B4F4A</span>
                <span className="text-[11px]">Active / Pressed</span>
              </div>
            </div>
          </div>

          {/* Semantic Coverage */}
          <div className="bg-surface p-4 rounded-ctl border border-border space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">Semantic & Severity</h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-[#E3F2EA] text-ok border border-ok/20">
                <span>ok: #2E7D5B</span>
                <span className="text-[11px]">Covered</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-[#FBF0D9] text-warn border border-warn/20">
                <span>warn: #B7791F</span>
                <span className="text-[11px]">Understaffed</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-[#FBE4DF] text-bad border border-bad/20">
                <span>bad: #C2412D</span>
                <span className="text-[11px]">Blocking Conflict</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-[#E4EEF8] text-info border border-info/20">
                <span>info: #356CA5</span>
                <span className="text-[11px]">Information</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Roster Status Cells */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink flex items-center gap-2">
          <Calendar className="w-4 h-4 text-accent-600" />
          2. Roster Grid Status Cells (WCAG AA Compliant)
        </h2>
        <div className="bg-surface p-6 rounded-ctl border border-border space-y-6">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-3">
              Standard Cells (36×28px, 12px IBM Plex Mono)
            </h3>
            <div className="flex flex-wrap items-center gap-4">
              {statusCodes.map((code) => (
                <div key={code} className="flex flex-col items-center gap-1.5">
                  <StatusCell
                    status={code}
                    isSelected={selectedCell === code}
                    onClick={() => setSelectedCell(code)}
                  />
                  <span className="text-[11px] font-mono text-ink-2">{code}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-3">
              Cell Variations: Manual Edit (Dot) and Locked Shift (Lock Glyph)
            </h3>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col items-center gap-1.5">
                <StatusCell status="W" isManual />
                <span className="text-[11px] font-mono text-ink-2">W (manual)</span>
              </div>
              <div className="flex flex-col items-center gap-1.5">
                <StatusCell status="WO" isLocked />
                <span className="text-[11px] font-mono text-ink-2">WO (locked)</span>
              </div>
              <div className="flex flex-col items-center gap-1.5">
                <StatusCell status="L" isManual isLocked />
                <span className="text-[11px] font-mono text-ink-2">L (both)</span>
              </div>
              <div className="flex flex-col items-center gap-1.5">
                <StatusCell status="HW" size="sm" />
                <span className="text-[11px] font-mono text-ink-2">HW (sm: 32×24)</span>
              </div>
              <div className="flex flex-col items-center gap-1.5">
                <StatusCell status="CO" disabled />
                <span className="text-[11px] font-mono text-ink-2">CO (disabled)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Buttons & Actions */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">3. Buttons & Controls</h2>
        <div className="bg-surface p-6 rounded-ctl border border-border space-y-6">
          <div className="flex flex-wrap items-center gap-4">
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="destructive">Destructive Button</Button>
            <Button variant="primary" isLoading>Loading State</Button>
            <Button variant="primary" disabled>Disabled State</Button>
          </div>
          <div className="flex items-center gap-4 pt-2 border-t border-border">
            <Button size="sm" variant="secondary">Small (28px)</Button>
            <Button size="default" variant="secondary">Default (32px)</Button>
            <Button size="lg" variant="secondary">Large (40px)</Button>
          </div>
        </div>
      </section>

      {/* 4. Inputs */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">4. Form Inputs</h2>
        <div className="bg-surface p-6 rounded-ctl border border-border grid grid-cols-1 md:grid-cols-3 gap-6">
          <Input label="Roster Month" placeholder="YYYY-MM (e.g. 2026-11)" defaultValue="2026-11" />
          <Input
            label="Target Headcount"
            placeholder="Min 1"
            defaultValue="0"
            error="Headcount must be at least 1"
          />
          <Input label="Locked Field" defaultValue="Pre-filled value" disabled />
        </div>
      </section>

      {/* 5. Badges & Chips */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">5. Severity Badges & Status Chips</h2>
        <div className="bg-surface p-6 rounded-ctl border border-border flex flex-wrap items-center gap-4">
          <Badge variant="BLOCKING" icon={<AlertTriangle className="w-3 h-3" />}>
            E001: Under-Staffed
          </Badge>
          <Badge variant="WARNING" icon={<AlertTriangle className="w-3 h-3" />}>
            W001: Over-Allocated
          </Badge>
          <Badge variant="INFO" icon={<Info className="w-3 h-3" />}>
            Shift Reassigned
          </Badge>
          <Badge variant="SUCCESS">Roster Published</Badge>
          <Badge variant="neutral">Draft Status</Badge>
        </div>
      </section>

      {/* 6. Overlays: Modal and Drawer */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">6. Overlays (Modal & 420px Drawer)</h2>
        <div className="bg-surface p-6 rounded-ctl border border-border flex items-center gap-4">
          <Button variant="secondary" onClick={() => setModalOpen(true)}>
            Open Test Modal
          </Button>
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
            Open 420px Right Drawer
          </Button>
        </div>

        <Modal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Confirm Roster Regeneration"
          footer={
            <>
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={() => setModalOpen(false)}>
                Regenerate & Overwrite
              </Button>
            </>
          }
        >
          <p className="text-sm text-ink-2">
            Regenerating the roster will recalculate assignments for all 45 employees. Any unlocked
            manual assignments will be re-solved by the engine.
          </p>
        </Modal>

        <Drawer
          isOpen={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          title="Conflict Detail: E001 Under-Staffed"
        >
          <div className="space-y-4">
            <div className="p-3 rounded bg-[#FBE4DF] border border-bad/20">
              <div className="flex items-center gap-2 text-bad font-semibold text-xs">
                <AlertTriangle className="w-4 h-4" />
                BLOCKING CONFLICT
              </div>
              <p className="text-xs text-bad mt-1 font-mono">
                Brand: GlowCare · Process: Inbound Voice · Date: 2026-11-04
              </p>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase text-ink-3">Impact</h4>
              <p className="text-sm text-ink mt-1">
                Required minimum staffing is 2, but only 1 employee is scheduled to work due to weekly off.
              </p>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase text-ink-3">Recommended Actions</h4>
              <div className="mt-2 space-y-2">
                <Button variant="secondary" size="sm" className="w-full justify-start text-xs">
                  Assign Floater Priya Sharma (Available)
                </Button>
                <Button variant="ghost" size="sm" className="w-full justify-start text-xs">
                  Shift weekly off to Wednesday
                </Button>
              </div>
            </div>
          </div>
        </Drawer>
      </section>

      {/* 7. Loading & Empty States */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-ink">7. Feedback & Skeletons</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-surface p-6 rounded-ctl border border-border space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">Skeleton Loading State</h3>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <div className="flex gap-2 pt-2">
              <Skeleton className="h-7 w-20" />
              <Skeleton className="h-7 w-24" />
            </div>
          </div>
          <div className="bg-surface p-6 rounded-ctl border border-border">
            <EmptyState
              title="No Conflicts Detected"
              description="The current roster satisfies all mandatory coverage rules and weekly off policies."
              actionLabel="View Roster"
              onAction={() => alert('Navigate to roster')}
            />
          </div>
        </div>
      </section>
    </div>
  );
};
