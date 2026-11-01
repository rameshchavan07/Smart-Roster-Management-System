import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import {
  RosterCoverageCell,
  CoverageState,
  getCoverageState,
  COVERAGE_CONFIG,
} from '../../types/roster';

export interface CoverageStripProps {
  coverageCells: RosterCoverageCell[];
  dates: string[]; // List of YYYY-MM-DD
  stickyLeftWidth?: number; // default 278px to match RosterGrid (160 + 64 + 54)
  isExpanded?: boolean;
  onToggleExpand?: (expanded: boolean) => void;
  initiallyExpanded?: boolean;
  onCellClick?: (cell: RosterCoverageCell) => void;
  className?: string;
}

interface BrandProcessGroup {
  id: string;
  brandName: string;
  processName: string;
  cellsByDate: Record<string, RosterCoverageCell>;
  totalRequired: number;
  totalActual: number;
  coveragePct: number;
}

export const CoverageStrip: React.FC<CoverageStripProps> = ({
  coverageCells,
  dates,
  stickyLeftWidth = 278,
  isExpanded: controlledExpanded,
  onToggleExpand,
  initiallyExpanded = false,
  onCellClick,
  className = '',
}) => {
  const [internalExpanded, setInternalExpanded] = useState<boolean>(initiallyExpanded);
  const isExpanded = controlledExpanded !== undefined ? controlledExpanded : internalExpanded;

  const handleToggle = () => {
    const next = !isExpanded;
    if (controlledExpanded === undefined) {
      setInternalExpanded(next);
    }
    onToggleExpand?.(next);
  };
  const [hoveredCell, setHoveredCell] = useState<{
    cell: RosterCoverageCell;
    state: CoverageState;
    x: number;
    y: number;
  } | null>(null);

  // Group coverage cells by brand-process
  const { brandProcesses, dailyAggregates } = useMemo(() => {
    const bpMap = new Map<string, BrandProcessGroup>();
    const dailyMap = new Map<
      string,
      { totalRequired: number; totalActual: number; states: CoverageState[] }
    >();

    // Initialize daily map for all dates
    for (const d of dates) {
      dailyMap.set(d, { totalRequired: 0, totalActual: 0, states: [] });
    }

    for (const cell of coverageCells) {
      const bpId = cell.brand_process_id;
      if (!bpMap.has(bpId)) {
        bpMap.set(bpId, {
          id: bpId,
          brandName: cell.brand_name || 'Brand',
          processName: cell.process_name || 'Process',
          cellsByDate: {},
          totalRequired: 0,
          totalActual: 0,
          coveragePct: 100,
        });
      }

      const bp = bpMap.get(bpId)!;
      bp.cellsByDate[cell.date] = cell;
      bp.totalRequired += cell.required;
      bp.totalActual += Math.min(cell.actual, cell.required);

      const dayAgg = dailyMap.get(cell.date);
      if (dayAgg) {
        dayAgg.totalRequired += cell.required;
        dayAgg.totalActual += cell.actual;
        dayAgg.states.push(getCoverageState(cell.required, cell.actual));
      }
    }

    // Compute monthly coverage % for each brand process
    for (const bp of bpMap.values()) {
      bp.coveragePct =
        bp.totalRequired > 0
          ? Math.round((bp.totalActual / bp.totalRequired) * 100)
          : 100;
    }

    // Sort brand-processes by coverage % ascending (problematic first), then name
    const sortedBps = Array.from(bpMap.values()).sort((a, b) => {
      if (a.coveragePct !== b.coveragePct) return a.coveragePct - b.coveragePct;
      return a.brandName.localeCompare(b.brandName);
    });

    // Compute daily aggregated coverage state
    const dailyStates: Record<
      string,
      { state: CoverageState; label: string; shortfall: number }
    > = {};

    for (const [dateStr, agg] of dailyMap.entries()) {
      if (agg.totalRequired <= 0) {
        dailyStates[dateStr] = { state: 'CLOSED', label: 'Closed / Non-operating', shortfall: 0 };
      } else if (agg.states.includes('UNCOVERED')) {
        const shortfall = Math.max(0, agg.totalRequired - agg.totalActual);
        dailyStates[dateStr] = {
          state: 'UNCOVERED',
          label: `Uncovered gap (${shortfall} staff shortfall)`,
          shortfall,
        };
      } else if (agg.states.includes('UNDERSTAFFED')) {
        const shortfall = Math.max(0, agg.totalRequired - agg.totalActual);
        dailyStates[dateStr] = {
          state: 'UNDERSTAFFED',
          label: `Under-staffed (${shortfall} shortfall)`,
          shortfall,
        };
      } else {
        dailyStates[dateStr] = {
          state: 'COVERED',
          label: `Fully covered (${agg.totalActual}/${agg.totalRequired} staffed)`,
          shortfall: 0,
        };
      }
    }

    return {
      brandProcesses: sortedBps,
      dailyAggregates: dailyStates,
    };
  }, [coverageCells, dates]);

  if (coverageCells.length === 0) {
    return null;
  }

  return (
    <div className={`border-b border-border-strong bg-surface-2/40 ${className}`}>
      {/* Aggregated Overview Strip (Compact 4px bar) */}
      <div className="flex items-center h-[26px] border-b border-border text-xs">
        {/* Toggle & Label in Sticky Left Column */}
        <div
          style={{ width: `${stickyLeftWidth}px` }}
          className="sticky left-0 z-30 flex items-center justify-between px-2.5 h-full bg-surface-2 border-r-2 border-border-strong flex-shrink-0"
        >
          <button
            type="button"
            onClick={handleToggle}
            className="flex items-center gap-1.5 text-[11px] font-semibold text-text-secondary hover:text-text-primary transition-colors"
            title="Toggle per brand-process coverage breakdown"
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
            )}
            <span className="uppercase tracking-wider">Demand Coverage</span>
            <span className="font-mono text-[10px] text-text-muted font-normal">
              ({brandProcesses.length})
            </span>
          </button>

          <span className="text-[10px] font-mono text-text-muted">
            {isExpanded ? 'Collapse' : 'Expand'}
          </span>
        </div>

        {/* 4px Bar Segment per Day Column */}
        {dates.map((dateStr) => {
          const dayAgg = dailyAggregates[dateStr] || {
            state: 'CLOSED',
            label: 'No data',
            shortfall: 0,
          };

          return (
            <div
              key={dateStr}
              className="relative w-[36px] h-full flex items-center justify-center border-r border-border flex-shrink-0 group/strip cursor-pointer"
              title={`${dateStr}: ${dayAgg.label}`}
            >
              {/* 4px high continuous coverage bar from Design System */}
              <div
                className={`w-[32px] h-[4px] rounded-full transition-all group-hover/strip:h-[6px] ${
                  dayAgg.state === 'COVERED'
                    ? 'bg-[#2E7D5B]'
                    : dayAgg.state === 'UNDERSTAFFED'
                    ? 'bg-[#B7791F]'
                    : dayAgg.state === 'UNCOVERED'
                    ? 'bg-[#C2412D]'
                    : 'bg-[#C5C0B6]'
                }`}
              />
            </div>
          );
        })}
      </div>

      {/* Expanded Multi-Row Breakdown (One row per Brand-Process) */}
      {isExpanded && (
        <div className="divide-y divide-border bg-surface-1/50 transition-all">
          {brandProcesses.map((bp) => (
            <div
              key={bp.id}
              className="flex items-center h-[24px] hover:bg-surface-2/60 transition-colors"
            >
              {/* Left Sticky Label: Brand · Process + Monthly Coverage % */}
              <div
                style={{ width: `${stickyLeftWidth}px` }}
                className="sticky left-0 z-20 flex items-center justify-between px-2.5 h-full bg-surface-1 border-r-2 border-border-strong flex-shrink-0 overflow-hidden"
              >
                <div className="flex items-center gap-1.5 truncate">
                  <span
                    className="text-[11px] font-medium text-text-primary truncate"
                    title={`${bp.brandName} · ${bp.processName}`}
                  >
                    {bp.brandName}
                  </span>
                  <span className="text-[10px] font-mono font-semibold px-1 py-0 rounded bg-surface-2 text-text-secondary flex-shrink-0">
                    {bp.processName}
                  </span>
                </div>

                <span
                  className={`font-mono text-[10px] font-semibold px-1 py-0 rounded flex-shrink-0 ${
                    bp.coveragePct >= 100
                      ? 'text-[#2E7D5B] bg-[#E3F2EA]'
                      : bp.coveragePct >= 80
                      ? 'text-[#B7791F] bg-[#FBF0D9]'
                      : 'text-[#C2412D] bg-[#FBE4DF]'
                  }`}
                  title={`Monthly coverage rate: ${bp.coveragePct}% (${bp.totalActual}/${bp.totalRequired})`}
                >
                  {bp.coveragePct}%
                </span>
              </div>

              {/* Day Segment Cells */}
              {dates.map((dateStr) => {
                const cell = bp.cellsByDate[dateStr] || {
                  date: dateStr,
                  brand_process_id: bp.id,
                  brand_name: bp.brandName,
                  process_name: bp.processName,
                  required: 0,
                  actual: 0,
                  shortfall: 0,
                };

                const state = getCoverageState(cell.required, cell.actual);

                return (
                  <div
                    key={dateStr}
                    onClick={() => onCellClick?.(cell)}
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setHoveredCell({
                        cell,
                        state,
                        x: rect.left + rect.width / 2,
                        y: rect.top,
                      });
                    }}
                    onMouseLeave={() => setHoveredCell(null)}
                    className="relative w-[36px] h-full flex items-center justify-center border-r border-border flex-shrink-0 cursor-pointer group/cell"
                  >
                    {/* Visual 4px bar with low-saturation fill */}
                    <div
                      className={`w-[30px] h-[5px] rounded-sm transition-all group-hover/cell:h-[10px] ${
                        state === 'COVERED'
                          ? 'bg-[#2E7D5B]'
                          : state === 'UNDERSTAFFED'
                          ? 'bg-[#B7791F]'
                          : state === 'UNCOVERED'
                          ? 'bg-[#C2412D]'
                          : 'bg-[#DCD8D0]'
                      }`}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}

      {/* Floating Hover Tooltip */}
      {hoveredCell && (
        <div
          style={{
            position: 'fixed',
            left: `${hoveredCell.x}px`,
            top: `${hoveredCell.y - 8}px`,
            transform: 'translate(-50%, -100%)',
          }}
          className="z-50 pointer-events-none p-2 rounded shadow-md bg-surface-1 border border-border text-xs min-w-[160px] animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="flex items-center justify-between gap-2 pb-1 mb-1 border-b border-border">
            <span className="font-semibold text-text-primary">
              {hoveredCell.cell.brand_name} · {hoveredCell.cell.process_name}
            </span>
            <span className="font-mono text-[10px] text-text-muted">
              {hoveredCell.cell.date}
            </span>
          </div>

          <div className="space-y-0.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Required staff:</span>
              <span className="font-mono font-medium text-text-primary">
                {hoveredCell.cell.required}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Actual staffed:</span>
              <span className="font-mono font-medium text-text-primary">
                {hoveredCell.cell.actual}
              </span>
            </div>
            {hoveredCell.cell.shortfall > 0 && (
              <div className="flex items-center justify-between text-[#C2412D]">
                <span className="font-medium">Shortfall:</span>
                <span className="font-mono font-semibold">
                  -{hoveredCell.cell.shortfall}
                </span>
              </div>
            )}
            <div className="pt-1 mt-1 border-t border-border flex items-center gap-1.5">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  hoveredCell.state === 'COVERED'
                    ? 'bg-[#2E7D5B]'
                    : hoveredCell.state === 'UNDERSTAFFED'
                    ? 'bg-[#B7791F]'
                    : hoveredCell.state === 'UNCOVERED'
                    ? 'bg-[#C2412D]'
                    : 'bg-[#8A867C]'
                }`}
              />
              <span
                className={`font-semibold ${
                  hoveredCell.state === 'COVERED'
                    ? 'text-[#2E7D5B]'
                    : hoveredCell.state === 'UNDERSTAFFED'
                    ? 'text-[#B7791F]'
                    : hoveredCell.state === 'UNCOVERED'
                    ? 'text-[#C2412D]'
                    : 'text-text-muted'
                }`}
              >
                {COVERAGE_CONFIG[hoveredCell.state].label}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
