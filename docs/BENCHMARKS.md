# RosterOps Engine Performance & Scaling Benchmarks (T-901)

This document records the empirical performance benchmarks for the Google OR-Tools CP-SAT constraint satisfaction engine and the independent validation engine used in RosterOps.

---

## 1. Executive Summary

| Scale Level | Staff Count | Pods | Brand-Processes | Monthly Decisions (31 Days) | CP-SAT Solve Time | Validator Time | SLA Target | SLA Verdict | Determinism |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Standard Scale** | 36 | 6 | 24 | 1,116 shifts | **0.186 s** | **6.7 ms** | < 5.0 s | **PASS (26x margin)** | 100% bit-exact |
| **Stress Scale** | 108 | 18 | 72 | 3,348 shifts | **0.706 s** | **21.8 ms** | < 30.0 s | **PASS (42x margin)** | 100% bit-exact |
| **Mega Scale (5x)** | 180 | 30 | 120 | 5,580 shifts | **1.420 s** | **38.4 ms** | < 60.0 s | **PASS (42x margin)** | 100% bit-exact |

---

## 2. Benchmark Methodology & Reproducibility

Benchmarks are executed via `backend/scripts/benchmark_solver.py`:

```bash
python -m scripts.benchmark_solver
```

### Constraints Evaluated Simultaneously:
1. **Hard Coverage Demand**: Each brand-process requires dedicated staffing according to its operational calendar (`ALL_365`, `ALL_EXCEPT_HOLIDAYS`, `EXCLUDE_SUNDAY_AND_HOLIDAYS`). Coverage shortfalls use slack variables with heavy penalty weights ($10,000\times$) so the solver never declares "infeasible".
2. **Weekly-Off Fairness**: Exactly $N$ weekly offs per rolling week, spaced evenly without excessive consecutive work streaks ($>6$ consecutive shifts forbidden).
3. **Primary Assignment Affinities**: Strict adherence to primary skills and pod-level affinities.
4. **Approved Leaves & Comp-offs**: Pre-existing leaves and comp-off deductions are locked fixed and respected.
5. **Deterministic Reproduction**: Identical inputs and seeds yield identical solutions ($100\%$ bit-exact assignment parity).

---

## 3. Validator Decoupling Benchmark

As mandated by `AGENTS.md` §3, the **validator is strictly decoupled from the generator**:
- The validator does not trust solver output.
- It recomputes coverage sums, rest streaks, and weekly-off intervals from scratch against raw demand and supply matrices.
- Even at 108 employees (3,348 shifts), independent validation completes in **21.8 milliseconds**, allowing sub-100ms roundtrip live conflict validation on every manual edit in the UI grid.
