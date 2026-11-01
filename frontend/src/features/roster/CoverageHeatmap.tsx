import React, { useState, useMemo } from 'react';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
} from 'lucide-react';
import { Input, Select, Badge } from '../../components/ui';
import {
  RosterCoverageCell,
  CoverageState,
  getCoverageState,
  COVERAGE_CONFIG,
} from '../../types/roster';

export interface CoverageHeatmapProps {
  coverageCells: RosterCoverageCell[];
  dates: string[]; // Ordered list of YYYY-MM-DD
  onCellClick?: (cell: RosterCoverageCell) => void;
  isLoading?: boolean;
  className?: string;
}

const WEEKDAY_INITIALS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export const CoverageHeatmap: React.FC<CoverageHeatmapProps> = ({
  coverageCells,
  dates,
  onCellClick,
  isLoading = false,
  className = '',
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [hoveredCell, setHoveredCell] = useState<{
    cell: RosterCoverageCell;
    state: CoverageState;
    x: number;
    y: number;
  } | null>(null);

  // Group cells by brand-process
  const { brandProcesses, summaryStats } = useMemo(() => {
    const bpMap = new Map<
      string,
      {
        id: string;
        brandName: string;
        processName: string;
        cellsByDate: Record<string, RosterCoverageCell>;
        totalRequired: number;
        totalActual: number;
        uncoveredCount: number;
        understaffedCount: number;
        coveragePct: number;
      }
    >();

    let totalSlotsRequired = 0;
    let totalSlotsCovered = 0;
    let totalUnderstaffedSlots = 0;
    let totalUncoveredSlots = 0;

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
          uncoveredCount: 0,
          understaffedCount: 0,
          coveragePct: 100,
        });
      }

      const bp = bpMap.get(bpId)!;
      bp.cellsByDate[cell.date] = cell;
      bp.totalRequired += cell.required;
      bp.totalActual += Math.min(cell.actual, cell.required);

      totalSlotsRequired += cell.required;
      totalSlotsCovered += Math.min(cell.actual, cell.required);

      const state = getCoverageState(cell.required, cell.actual);
      if (state === 'UNCOVERED') {
        bp.uncoveredCount++;
        totalUncoveredSlots++;
      } else if (state === 'UNDERSTAFFED') {
        bp.understaffedCount++;
        totalUnderstaffedSlots++;
      }
    }

    for (const bp of bpMap.values()) {
      bp.coveragePct =
        bp.totalRequired > 0
          ? Math.round((bp.totalActual / bp.totalRequired) * 100)
          : 100;
    }

    const overallPct =
      totalSlotsRequired > 0
        ? Math.round((totalSlotsCovered / totalSlotsRequired) * 100)
        : 100;

    const sortedList = Array.from(bpMap.values()).sort((a, b) => {
      // Prioritize brand-processes with uncovered gaps, then understaffed, then name
      if (a.uncoveredCount !== b.uncoveredCount) {
        return b.uncoveredCount - a.uncoveredCount;
      }
      if (a.coveragePct !== b.coveragePct) {
        return a.coveragePct - b.coveragePct;
      }
      return a.brandName.localeCompare(b.brandName);
    });

    return {
      brandProcesses: sortedList,
      summaryStats: {
        totalSlotsRequired,
        totalSlotsCovered,
        totalUnderstaffedSlots,
        totalUncoveredSlots,
        overallPct,
      },
    };
  }, [coverageCells]);

  // Filter rows
  const filteredRows = useMemo(() => {
    return brandProcesses.filter((bp) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesBrand = bp.brandName.toLowerCase().includes(q);
        const matchesProcess = bp.processName.toLowerCase().includes(q);
        if (!matchesBrand && !matchesProcess) return false;
      }

      if (statusFilter === 'UNCOVERED' && bp.uncoveredCount === 0) {
        return false;
      }
      if (statusFilter === 'UNDERSTAFFED' && bp.understaffedCount === 0) {
        return false;
      }

      return true;
    });
  }, [brandProcesses, searchQuery, statusFilter]);

  // Precompute dates metadata
  const datesMetadata = useMemo(() => {
    return dates.map((dateStr) => {
      const d = new Date(dateStr + 'T00:00:00');
      const dayOfWeek = d.getDay();
      return {
        dateStr,
        dayNumber: d.getDate(),
        weekdayInitial: WEEKDAY_INITIALS[dayOfWeek],
        isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      };
    });
  }, [dates]);

  if (isLoading) {
    return (
      <div className="w-full h-80 flex flex-col items-center justify-center bg-surface-1 border border-border rounded-md animate-pulse p-8">
        <div className="h-6 w-56 bg-surface-3 rounded mb-4" />
        <div className="h-4 w-72 bg-surface-2 rounded mb-2" />
        <div className="h-4 w-60 bg-surface-2 rounded" />
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* KPI Overview Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Coverage Rate</span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xl font-mono font-semibold text-text-primary">
              {summaryStats.overallPct}%
            </span>
            <Badge
              variant={summaryStats.overallPct >= 95 ? 'SUCCESS' : 'WARNING'}
              className="text-[10px] font-mono"
            >
              {summaryStats.totalSlotsCovered}/{summaryStats.totalSlotsRequired}
            </Badge>
          </div>
        </div>

        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Fully Covered</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <CheckCircle2 className="w-4 h-4 text-[#2E7D5B]" />
            <span className="text-lg font-mono font-semibold text-[#2E7D5B]">
              {summaryStats.totalSlotsCovered} <span className="text-xs font-normal text-text-muted">slots</span>
            </span>
          </div>
        </div>

        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Under-staffed</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <AlertTriangle className="w-4 h-4 text-[#B7791F]" />
            <span className="text-lg font-mono font-semibold text-[#B7791F]">
              {summaryStats.totalUnderstaffedSlots} <span className="text-xs font-normal text-text-muted">days</span>
            </span>
          </div>
        </div>

        <div className="p-3 bg-surface-1 border border-border rounded-md">
          <span className="text-[11px] font-medium text-text-muted uppercase">Uncovered (Gaps)</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <AlertCircle className="w-4 h-4 text-[#C2412D]" />
            <span className="text-lg font-mono font-semibold text-[#C2412D]">
              {summaryStats.totalUncoveredSlots} <span className="text-xs font-normal text-text-muted">critical</span>
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-surface-1 p-2.5 rounded-md border border-border">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search brand or process..."
              className="pl-8 text-xs h-8"
            />
          </div>

          <div className="w-44">
            <Select
              value={statusFilter}
              onChange={(val) => setStatusFilter(val)}
              options={[
                { value: 'ALL', label: 'All Statuses' },
                { value: 'UNCOVERED', label: 'Uncovered Only' },
                { value: 'UNDERSTAFFED', label: 'Under-staffed Only' },
              ]}
              className="text-xs h-8"
            />
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 text-[11px] text-text-muted flex-wrap">
          <span className="font-semibold text-text-secondary">Legend:</span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#2E7D5B]" />
            Covered
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#B7791F]" />
            Under-staffed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#C2412D]" />
            Uncovered
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#DCD8D0]" />
            Closed
          </span>
        </div>
      </div>

      {/* Heatmap Matrix Table */}
      <div className="border border-border rounded-md bg-surface-1 overflow-x-auto max-h-[560px]">
        <div className="min-w-max">
          {/* Header Row */}
          <div className="sticky top-0 z-30 flex items-center h-[36px] bg-surface-2 border-b border-border-strong text-xs font-semibold text-text-primary">
            {/* Left Sticky Column Header */}
            <div className="sticky left-0 z-40 flex items-center justify-between px-3 w-[220px] h-full bg-surface-2 border-r-2 border-border-strong text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
              <span>Brand · Process</span>
              <span>Rate</span>
            </div>

            {/* Date Headers */}
            {datesMetadata.map((d) => (
              <div
                key={d.dateStr}
                className={`flex flex-col items-center justify-center w-[36px] h-full border-r border-border flex-shrink-0 ${
                  d.isWeekend ? 'bg-[#F0EEEB] text-[#5C5852]' : 'bg-surface-2 text-text-primary'
                }`}
              >
                <span className="text-[10px] font-semibold">{d.weekdayInitial}</span>
                <span className="text-[11px] font-mono font-medium">{d.dayNumber}</span>
              </div>
            ))}
          </div>

          {/* Matrix Body */}
          {filteredRows.length === 0 ? (
            <div className="p-8 text-center text-xs text-text-muted">
              No brand-processes match the current filter.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredRows.map((bp) => (
                <div
                  key={bp.id}
                  className="flex items-center h-[28px] hover:bg-surface-2/60 transition-colors group"
                >
                  {/* Left Sticky Header */}
                  <div className="sticky left-0 z-20 flex items-center justify-between px-3 w-[220px] h-[28px] bg-surface-1 group-hover:bg-surface-2/90 border-r-2 border-border-strong flex-shrink-0 transition-colors">
                    <div className="flex items-center gap-1.5 truncate">
                      <span
                        className="text-xs font-medium text-text-primary truncate"
                        title={`${bp.brandName} · ${bp.processName}`}
                      >
                        {bp.brandName}
                      </span>
                      <span className="text-[10px] font-mono px-1 py-0 rounded bg-surface-2 text-text-secondary">
                        {bp.processName}
                      </span>
                    </div>

                    <span
                      className={`font-mono text-[10px] font-semibold px-1 py-0 rounded ${
                        bp.coveragePct >= 100
                          ? 'text-[#2E7D5B] bg-[#E3F2EA]'
                          : bp.coveragePct >= 80
                          ? 'text-[#B7791F] bg-[#FBF0D9]'
                          : 'text-[#C2412D] bg-[#FBE4DF]'
                      }`}
                    >
                      {bp.coveragePct}%
                    </span>
                  </div>

                  {/* Day Cells */}
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
                    const config = COVERAGE_CONFIG[state];

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
                        className={`w-[36px] h-[28px] border-r border-border flex-shrink-0 flex items-center justify-center font-mono text-[11px] font-medium cursor-pointer transition-colors ${config.bg} ${config.text} hover:brightness-95`}
                      >
                        {state === 'CLOSED' ? (
                          <span className="text-text-muted/50 text-[10px]">-</span>
                        ) : (
                          <span>
                            {cell.actual}
                            <span className="text-[9px] opacity-70">/{cell.required}</span>
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating Hover Tooltip */}
      {hoveredCell && (
        <div
          style={{
            position: 'fixed',
            left: `${hoveredCell.x}px`,
            top: `${hoveredCell.y - 8}px`,
            transform: 'translate(-50%, -100%)',
          }}
          className="z-50 pointer-events-none p-2 rounded shadow-md bg-surface-1 border border-border text-xs min-w-[170px] animate-in fade-in zoom-in-95 duration-100"
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
              <span className="text-text-muted">Required:</span>
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
