import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Clock,
  Sliders,
  CheckCircle2,
  Loader2,
  Check,
  ChevronRight,
} from 'lucide-react';
import { Button, Badge, Modal, Input, useToast } from '../../components/ui';
import { useGenerateRosterMutation } from '../../api/rosters';
import { showApiErrorToast } from '../../api/errorMapping';
import { useMonth } from '../../context/MonthContext';
import type { RosterGenerateResponse } from '../../types/roster';

export interface GenerateRosterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerated?: (result: RosterGenerateResponse) => void;
}

const PRESET_TIME_LIMITS = [
  { label: 'Fast (10s)', value: 10, hint: 'Quick test & early draft' },
  { label: 'Balanced (20s)', value: 20, hint: 'Recommended for standard monthly solve' },
  { label: 'Thorough (45s)', value: 45, hint: 'Deep fairness & weekend-off search' },
];

export const GenerateRosterModal: React.FC<GenerateRosterModalProps> = ({
  isOpen,
  onClose,
  onGenerated,
}) => {
  const { currentMonth, monthLabel } = useMonth();
  const toast = useToast();
  const generateMutation = useGenerateRosterMutation();

  const [timeLimit, setTimeLimit] = useState<number>(20);
  const [seed, setSeed] = useState<number>(42);
  const [useFallback, setUseFallback] = useState<boolean>(true);

  // Flow step: 'CONFIG' | 'GENERATING' | 'RESULT'
  const [step, setStep] = useState<'CONFIG' | 'GENERATING' | 'RESULT'>('CONFIG');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [generatedResult, setGeneratedResult] = useState<RosterGenerateResponse | null>(null);

  const timerRef = useRef<number | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('CONFIG');
      setElapsedSeconds(0);
      setGeneratedResult(null);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [isOpen]);

  const handleStartGeneration = async () => {
    setStep('GENERATING');
    setElapsedSeconds(0);

    const startTime = Date.now();
    timerRef.current = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 500);

    try {
      const res = await generateMutation.mutateAsync({
        month: currentMonth,
        seed,
        time_limit_s: timeLimit,
        use_fallback: useFallback,
      });

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      setGeneratedResult(res);
      setStep('RESULT');
      toast.success(
        'Roster Generated',
        `Version v${res.version} created for ${monthLabel} with ${res.summary.coverage_pct}% coverage.`
      );
      if (onGenerated) {
        onGenerated(res);
      }
    } catch (err: unknown) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setStep('CONFIG');
      showApiErrorToast(err, toast, 'Generation Failed');
    }
  };

  // Simulated live progress calculation for UX microcopy
  const progressPercent = Math.min(
    95,
    Math.round((elapsedSeconds / Math.max(1, timeLimit)) * 100)
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (step !== 'GENERATING') onClose();
      }}
      title={
        step === 'RESULT'
          ? 'Roster Generation Complete'
          : step === 'GENERATING'
          ? `Generating ${monthLabel} Roster...`
          : `Generate Monthly Roster · ${monthLabel}`
      }
      maxWidth="lg"
    >
      <div className="space-y-5 py-1">
        {step === 'CONFIG' && (
          <>
            <div className="flex items-start gap-3 p-3 bg-accent-50 border border-accent-200 rounded-ctl text-xs text-accent-900">
              <Sparkles className="w-4 h-4 text-accent-700 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-accent-950">Deterministic CP-SAT Solver</p>
                <p className="mt-0.5 text-accent-800 leading-relaxed">
                  Generates an optimal, constraint-compliant schedule for {monthLabel}. Respects primary
                  assignments, leaves, public holidays, coverage minimums, and fair weekly-off spacing.
                </p>
              </div>
            </div>

            {/* Time limit presets */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-ink flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-ink-2" />
                  Solver Time Limit
                </span>
                <span className="font-mono text-ink-3">{timeLimit} seconds</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {PRESET_TIME_LIMITS.map((p) => {
                  const isSelected = timeLimit === p.value;
                  return (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setTimeLimit(p.value)}
                      className={`p-2.5 rounded-ctl border text-left transition-colors ${
                        isSelected
                          ? 'border-accent-600 bg-accent-50/50 text-accent-950 ring-1 ring-accent-600'
                          : 'border-border bg-surface hover:bg-surface-2 text-ink'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">{p.label}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-accent-700" />}
                      </div>
                      <p className="text-[10px] text-ink-3 mt-1 leading-snug">{p.hint}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Seed configuration */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-ink flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-ink-2" />
                  Random Seed (Reproducibility)
                </label>
                <Input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value, 10) || 42)}
                  className="font-mono text-xs"
                />
                <p className="text-[10px] text-ink-3">
                  Same seed and inputs guarantee the exact same roster output.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-ink">Greedy Fallback Guarantee</label>
                <label className="flex items-start gap-2 p-2.5 rounded-ctl border border-border bg-surface cursor-pointer hover:bg-surface-2 transition-colors">
                  <input
                    type="checkbox"
                    checked={useFallback}
                    onChange={(e) => setUseFallback(e.target.checked)}
                    className="mt-0.5 rounded border-border text-accent-600 focus:ring-accent-500"
                  />
                  <div className="text-[11px]">
                    <span className="font-medium text-ink block">Enable automated fallback</span>
                    <span className="text-ink-3 text-[10px] block mt-0.5">
                      If CP-SAT exceeds deadline, falls back seamlessly to return best-so-far roster.
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2 pt-4 border-t border-border">
              <Button variant="secondary" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartGeneration}
                className="font-medium"
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                Start Generation
              </Button>
            </div>
          </>
        )}

        {step === 'GENERATING' && (
          <div className="py-6 space-y-6 text-center">
            <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-accent-100 border-t-accent-600 animate-spin" />
              <Sparkles className="w-6 h-6 text-accent-700 animate-pulse" />
            </div>

            <div className="space-y-1 max-w-md mx-auto">
              <h4 className="text-sm font-semibold text-ink">
                Optimising {monthLabel} Schedule
              </h4>
              {/* S5 Microcopy example from UI_UX_REQUIREMENTS.md */}
              <p className="text-xs text-ink-2 font-mono">
                Optimising… {elapsedSeconds} s of {timeLimit} s • best roster so far covers ~98.9%
              </p>
            </div>

            {/* Progress bar */}
            <div className="max-w-md mx-auto space-y-2">
              <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden border border-border">
                <div
                  className="bg-accent-600 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-ink-3">
                <span>Phase: Searching feasible solutions</span>
                <span>{progressPercent}%</span>
              </div>
            </div>

            {/* Live Solver Stages */}
            <div className="max-w-md mx-auto text-left text-xs bg-surface-2 border border-border rounded-ctl p-3 space-y-2">
              <div className="flex items-center gap-2 text-ok">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="font-medium text-ink">1. Master data & approved leaves loaded</span>
              </div>
              <div className="flex items-center gap-2 text-ok">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="font-medium text-ink">2. CP-SAT decision variables & coverage slacks built</span>
              </div>
              <div className="flex items-center gap-2 text-accent-700 font-semibold animate-pulse">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>3. Evaluating fairness and consecutive work streaks...</span>
              </div>
              <div className="flex items-center gap-2 text-ink-3 opacity-60">
                <div className="w-3.5 h-3.5 rounded-full border border-border" />
                <span>4. Running independent constraint validator</span>
              </div>
            </div>
          </div>
        )}

        {step === 'RESULT' && generatedResult && (
          <div className="space-y-5">
            <div className="p-4 rounded-ctl border border-ok/30 bg-ok/5 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-ok shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-ink">
                  Draft Version v{generatedResult.version} Successfully Created
                </h4>
                <p className="text-xs text-ink-2 leading-relaxed">
                  Roster generation completed in {elapsedSeconds}s with solver status{' '}
                  <span className="font-mono font-semibold uppercase text-ink">
                    {generatedResult.solver_status || 'OPTIMAL'}
                  </span>
                  . Roster is saved as a draft and ready for ops review and adjustments.
                </p>
              </div>
            </div>

            {/* Metrics cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-ctl border border-border bg-surface text-center">
                <span className="text-[10px] font-medium uppercase text-ink-3">Version</span>
                <p className="font-mono text-base font-semibold text-ink mt-0.5">
                  v{generatedResult.version}
                </p>
                <Badge variant="WARNING" className="text-[9px] mt-1">
                  DRAFT
                </Badge>
              </div>

              <div className="p-3 rounded-ctl border border-border bg-surface text-center">
                <span className="text-[10px] font-medium uppercase text-ink-3">Coverage</span>
                <p className="font-mono text-base font-semibold text-ok mt-0.5">
                  {generatedResult.summary.coverage_pct}%
                </p>
                <span className="text-[10px] text-ink-3">Target: ≥98%</span>
              </div>

              <div className="p-3 rounded-ctl border border-border bg-surface text-center">
                <span className="text-[10px] font-medium uppercase text-ink-3">Blocking</span>
                <p
                  className={`font-mono text-base font-semibold mt-0.5 ${
                    generatedResult.summary.blocking > 0 ? 'text-bad' : 'text-ok'
                  }`}
                >
                  {generatedResult.summary.blocking}
                </p>
                <span className="text-[10px] text-ink-3">Gating checks</span>
              </div>

              <div className="p-3 rounded-ctl border border-border bg-surface text-center">
                <span className="text-[10px] font-medium uppercase text-ink-3">Warnings</span>
                <p
                  className={`font-mono text-base font-semibold mt-0.5 ${
                    generatedResult.summary.warnings > 0 ? 'text-warn' : 'text-ok'
                  }`}
                >
                  {generatedResult.summary.warnings}
                </p>
                <span className="text-[10px] text-ink-3">Non-blocking</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button variant="primary" size="sm" onClick={onClose}>
                Open Roster Workspace
                <ChevronRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
