import React, { useState } from 'react';
import { Download, FileSpreadsheet, FileText, Calendar, ShieldAlert, Grid, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Modal, Button, Input, useToast } from '../../components/ui';
import { downloadRosterExport } from '../../api/rosters';
import type { RosterPeriod } from '../../types/roster';

export interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  period?: RosterPeriod | null;
}

export type ExportViewType = 'grid' | 'day' | 'coverage' | 'conflicts';
export type ExportFormat = 'csv' | 'xlsx';

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, period }) => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [format, setFormat] = useState<ExportFormat>('csv');
  const [view, setView] = useState<ExportViewType>('grid');
  const [selectedDate, setSelectedDate] = useState<string>(
    period?.month || new Date().toISOString().slice(0, 10)
  );
  const [isExporting, setIsExporting] = useState<boolean>(false);

  if (!period) return null;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const filename = await downloadRosterExport(
        period.id,
        format,
        view,
        view === 'day' ? selectedDate : undefined
      );
      success('Export Complete', `Successfully downloaded ${filename}`);
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to export schedule file';
      toastError('Export Failed', message);
    } finally {
      setIsExporting(false);
    }
  };

  const viewOptions: Array<{
    id: ExportViewType;
    title: string;
    description: string;
    icon: React.ReactNode;
  }> = [
    {
      id: 'grid',
      title: 'Full Monthly Matrix (Grid)',
      description: 'Matrix of all employees with daily status codes (W, WO, PH, HW, L, CO) and summary totals.',
      icon: <Grid className="w-4 h-4 text-accent-700" />,
    },
    {
      id: 'day',
      title: 'Daily Operational Schedule (Day View)',
      description: 'Roster details for a specific operational date, grouped by brand-process with contact details.',
      icon: <Calendar className="w-4 h-4 text-accent-700" />,
    },
    {
      id: 'coverage',
      title: 'Brand-Process Coverage Matrix',
      description: 'Headcount scheduled vs minimum staffing requirement per brand-process per date with shortfall flags.',
      icon: <FileSpreadsheet className="w-4 h-4 text-accent-700" />,
    },
    {
      id: 'conflicts',
      title: 'Integrity Violations & Conflicts Report',
      description: 'Audit report of all blocking and warning conflicts, root cause analysis, and acknowledgment state.',
      icon: <ShieldAlert className="w-4 h-4 text-warn" />,
    },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Export Roster Schedule"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onClose();
              navigate('/reports');
            }}
            className="text-xs text-muted hover:text-ink"
          >
            <ExternalLink className="w-3.5 h-3.5 mr-1" />
            Open Full Compare & Reports
          </Button>

          <div className="flex items-center space-x-2">
            <Button variant="secondary" size="sm" onClick={onClose} disabled={isExporting}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleExport}
              isLoading={isExporting}
            >
              <Download className="w-3.5 h-3.5 mr-1" />
              Download {format.toUpperCase()}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Active Period Info */}
        <div className="flex items-center justify-between p-3 bg-surface-muted/50 rounded-ctl border border-border">
          <div>
            <div className="text-xs font-semibold text-ink">
              Roster Version: Version {period.version}
            </div>
            <div className="text-[11px] text-muted">
              Month: {period.month} • Status: {period.status}
            </div>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent-100 text-accent-800 font-medium">
            v{period.version}
          </span>
        </div>

        {/* Format Selector */}
        <div>
          <label className="block text-xs font-semibold text-ink mb-1.5">
            File Format
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setFormat('csv')}
              className={`flex items-center space-x-2.5 p-2.5 rounded-ctl border text-left transition-colors ${
                format === 'csv'
                  ? 'border-accent-700 bg-accent-50/60 ring-1 ring-accent-700'
                  : 'border-border bg-surface hover:bg-surface-muted/50'
              }`}
            >
              <FileText className={`w-4 h-4 ${format === 'csv' ? 'text-accent-700' : 'text-muted'}`} />
              <div>
                <div className="text-xs font-medium text-ink">CSV (Plain Text)</div>
                <div className="text-[11px] text-muted">RFC 4180 standard, lightweight</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setFormat('xlsx')}
              className={`flex items-center space-x-2.5 p-2.5 rounded-ctl border text-left transition-colors ${
                format === 'xlsx'
                  ? 'border-accent-700 bg-accent-50/60 ring-1 ring-accent-700'
                  : 'border-border bg-surface hover:bg-surface-muted/50'
              }`}
            >
              <FileSpreadsheet className={`w-4 h-4 ${format === 'xlsx' ? 'text-accent-700' : 'text-muted'}`} />
              <div>
                <div className="text-xs font-medium text-ink">Excel (XLSX)</div>
                <div className="text-[11px] text-muted">Formatted spreadsheet document</div>
              </div>
            </button>
          </div>
        </div>

        {/* View Mode Selector */}
        <div>
          <label className="block text-xs font-semibold text-ink mb-1.5">
            Report View Mode
          </label>
          <div className="space-y-2">
            {viewOptions.map((opt) => (
              <label
                key={opt.id}
                className={`flex items-start space-x-3 p-3 rounded-ctl border cursor-pointer transition-colors ${
                  view === opt.id
                    ? 'border-accent-700 bg-accent-50/40 ring-1 ring-accent-700'
                    : 'border-border bg-surface hover:bg-surface-muted/30'
                }`}
              >
                <input
                  type="radio"
                  name="exportView"
                  value={opt.id}
                  checked={view === opt.id}
                  onChange={() => setView(opt.id)}
                  className="mt-0.5 text-accent-700 focus:ring-accent-600"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    {opt.icon}
                    <span className="text-xs font-medium text-ink">{opt.title}</span>
                  </div>
                  <p className="text-[11px] text-muted mt-0.5">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Date Selector for Day View */}
        {view === 'day' && (
          <div className="p-3 bg-surface-muted/50 rounded-ctl border border-border">
            <label className="block text-xs font-medium text-ink mb-1">
              Select Operating Date
            </label>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="text-xs"
            />
          </div>
        )}
      </div>
    </Modal>
  );
};
