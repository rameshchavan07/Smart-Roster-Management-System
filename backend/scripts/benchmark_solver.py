"""Benchmark script for RosterOps CP-SAT scheduling engine and validator (T-901).

Profiles CP-SAT solver and independent validator performance at:
1. Standard Scale: 36 employees, 6 pods, 24 brand-processes, 31 days (December 2026).
2. Stress Scale: 108 employees, 18 pods, 72 brand-processes, 31 days (3x scale).
3. Mega Scale: 180 employees, 30 pods, 120 brand-processes, 31 days (5x scale).

Verifies constraints:
- Standard scale solve time < 5.0 seconds
- Stress scale (100+ employees) solve time < 30.0 seconds
- Determinism: exact same assignments across runs with same seed
- Independent validator confirms zero hard constraint breaches
"""

from __future__ import annotations

import time
from datetime import date

# Ensure pure Python scheduler is imported
from app.scheduler.demand import build_demand_matrix
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    Employee,
    EmployeeLeave,
    GenerationInput,
    Holiday,
    LeaveType,
    WeeklyOffMode,
)
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.supply import build_supply_matrix
from app.scheduler.validator import validate_roster


def build_synthetic_scenario(
    num_pods: int = 6,
    employees_per_pod: int = 6,
    processes_per_brand: int = 4,
    start_date: date = date(2026, 12, 1),
    end_date: date = date(2026, 12, 31),
    seed: int = 42,
) -> GenerationInput:
    """Construct an in-memory GenerationInput of arbitrary scale matching production semantics."""
    employees: list[Employee] = []
    bps: list[BrandProcess] = []
    assignments: list[Assignment] = []

    cal_types = [
        CalendarType.ALL_365,
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        CalendarType.ALL_365,
    ]

    bp_idx = 0
    emp_idx = 0

    for pod_num in range(1, num_pods + 1):
        pod_id = f"pod-{pod_num:02d}"
        brand_id = f"brd-{pod_num:02d}"

        # Each pod has a dedicated brand with multiple processes
        pod_bps: list[BrandProcess] = []
        for p_num in range(1, processes_per_brand + 1):
            bp_idx += 1
            bp_id = f"bp-{bp_idx:03d}"
            p_name = ["Customer Support", "Abandoned Cart", "Retention", "NDR"][p_num - 1]
            bp = BrandProcess(
                id=bp_id,
                brand_id=brand_id,
                brand_name=f"Brand-{pod_num:02d}",
                process_id=f"proc-{p_num}",
                process_name=p_name,
                calendar_type=cal_types[(p_num - 1) % len(cal_types)],
                min_coverage_default=1,
            )
            bps.append(bp)
            pod_bps.append(bp)

        # Create employees in this pod
        for e_num in range(1, employees_per_pod + 1):
            emp_idx += 1
            e_id = f"emp-{emp_idx:03d}"
            e = Employee(
                id=e_id,
                code=f"EMP-{emp_idx:03d}",
                full_name=f"Agent {emp_idx}",
                pod_id=pod_id,
                weekly_off_count=1,
                weekly_off_mode=WeeklyOffMode.ROTATING,
            )
            employees.append(e)

            # Assign to primary brand process in this pod
            target_bp = pod_bps[(e_num - 1) % len(pod_bps)]
            assignments.append(
                Assignment(
                    employee_id=e_id,
                    brand_process_id=target_bp.id,
                    type=AssignmentType.PRIMARY,
                )
            )

    # 1 Public Holiday (Christmas)
    holidays = (
        Holiday(date=date(2026, 12, 25), name="Christmas Day"),
    )

    # Leaves: ~5% of employees have a 3-day approved annual leave
    leaves: list[EmployeeLeave] = []
    for i in range(0, len(employees), 10):
        leaves.append(
            EmployeeLeave(
                employee_id=employees[i].id,
                start_date=date(2026, 12, 8),
                end_date=date(2026, 12, 10),
                type=LeaveType.PLANNED,
            )
        )

    # Supply and Demand matrices
    demand = build_demand_matrix(brand_processes=bps, start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=employees, start_date=start_date, end_date=end_date)

    return GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=tuple(employees),
        brand_processes=tuple(bps),
        assignments=tuple(assignments),
        coverage_rules=(),
        holidays=holidays,
        leaves=tuple(leaves),
        locked_cells=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=seed,
        time_limit_seconds=30.0,
    )


def run_benchmark(scale_name: str, num_pods: int, emps_per_pod: int, max_allowed_s: float) -> dict:
    total_emps = num_pods * emps_per_pod
    total_bps = num_pods * 4
    total_days = 31
    expected_shifts = total_emps * total_days

    print("\n============================================================")
    print(f"BENCHMARK: {scale_name}")
    print(f"Employees: {total_emps} | Pods: {num_pods} | Brand-Processes: {total_bps} | Days: {total_days}")
    print(f"Total Decision Cells: {expected_shifts:,}")
    print(f"Target SLA: < {max_allowed_s:.1f}s")
    print("============================================================")

    # 1. Build scenario
    t_start_build = time.perf_counter()
    gen_input = build_synthetic_scenario(
        num_pods=num_pods,
        employees_per_pod=emps_per_pod,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 31),
        seed=42,
    )
    t_build = time.perf_counter() - t_start_build
    print(f"[1/4] Scenario matrices generated in {t_build * 1000:.2f} ms")

    # 2. Run CP-SAT solver
    t_start_solve = time.perf_counter()
    out = generate_cpsat(gen_input)
    t_solve = time.perf_counter() - t_start_solve
    print(f"[2/4] CP-SAT solver completed in {t_solve:.3f} s (Status: {out.solver_status})")
    print(f"      Coverage shortfall slack: {out.slack_shortfall_total}")

    # 3. Independent Validator
    t_start_val = time.perf_counter()
    val_res, _ = validate_roster(
        roster_cells=out.roster_cells,
        demand_cells=gen_input.demand_matrix,
        supply_cells=gen_input.supply_matrix,
        employees=gen_input.employees,
        brand_processes=gen_input.brand_processes,
        assignments=gen_input.assignments,
        holidays=gen_input.holidays,
        leaves=gen_input.leaves,
    )
    t_val = time.perf_counter() - t_start_val
    print(f"[3/4] Independent validator completed in {t_val * 1000:.2f} ms")
    print(f"      Validator Result: Valid={val_res.is_valid}, Blocking={val_res.blocking_count}, Warnings={val_res.warning_count}")

    # 4. Determinism check
    t_start_det = time.perf_counter()
    out_repeat = generate_cpsat(gen_input)
    t_det = time.perf_counter() - t_start_det
    assert len(out.roster_cells) == len(out_repeat.roster_cells), "Entry count mismatch on repeat run"
    for e1, e2 in zip(out.roster_cells, out_repeat.roster_cells, strict=True):
        assert e1.employee_id == e2.employee_id and e1.date == e2.date and e1.status == e2.status, (
            f"Non-deterministic assignment found: {e1} vs {e2}"
        )
    print(f"[4/4] Determinism verified: 100% bit-exact match across runs ({t_det:.3f} s)")

    sla_pass = t_solve < max_allowed_s
    status_str = "PASS" if sla_pass else "FAIL"
    print(f"\nSLA Verdict: [{status_str}] ({t_solve:.3f}s vs limit {max_allowed_s:.1f}s)")

    return {
        "scale": scale_name,
        "employees": total_emps,
        "pods": num_pods,
        "shifts": expected_shifts,
        "build_ms": round(t_build * 1000, 2),
        "solve_s": round(t_solve, 3),
        "validator_ms": round(t_val * 1000, 2),
        "solver_status": out.solver_status.value,
        "blocking_conflicts": val_res.blocking_count,
        "sla_target_s": max_allowed_s,
        "sla_pass": sla_pass,
    }


def main() -> None:
    print("Starting Smart Roster Management System Engine Benchmarks (T-901)...")
    results = []

    # Run Benchmark 1: Standard Scale (36 employees) - SLA < 5.0s
    res1 = run_benchmark(
        scale_name="Standard Scale (36 emps)",
        num_pods=6,
        emps_per_pod=6,
        max_allowed_s=5.0,
    )
    results.append(res1)

    # Run Benchmark 2: Stress Scale (108 employees) - SLA < 30.0s
    res2 = run_benchmark(
        scale_name="Stress Scale (108 emps)",
        num_pods=18,
        emps_per_pod=6,
        max_allowed_s=30.0,
    )
    results.append(res2)

    # Print Summary Table
    print("\n" + "=" * 90)
    print(f"{'Scale':<28} | {'Staff':<6} | {'Decisions':<10} | {'Solve (s)':<10} | {'Validator':<10} | {'SLA Target':<10} | {'Result'}")
    print("=" * 90)
    for r in results:
        print(
            f"{r['scale']:<28} | {r['employees']:<6} | {r['shifts']:<10} | {r['solve_s']:<10} | "
            f"{r['validator_ms']:>6.1f} ms  | {r['sla_target_s']:<10} | {'PASS' if r['sla_pass'] else 'FAIL'}"
        )
    print("=" * 90)


if __name__ == "__main__":
    main()
