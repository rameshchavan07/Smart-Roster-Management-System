# 1. Use OR-Tools CP-SAT for Roster Generation

Date: 2026-11-01
Status: Accepted

## Context
Roster scheduling is an NP-hard constraint satisfaction and combinatorial optimization problem. We must enforce mandatory hard constraints (coverage minimums, weekly-off entitlements, maximum consecutive working days, fixed leaves, locked cells) while optimizing soft preference constraints (fair weekend distribution, preferred off days, stability, avoiding employee overload). When a month cannot be fully covered without violating hard constraints, the solver must produce the best possible roster with explicit slack/shortfall reporting rather than failing with "infeasible".

## Decision
We select Google OR-Tools CP-SAT solver as the primary generation engine for the following reasons:
1. Native support for hard constraints and weighted penalty optimization via objective functions.
2. Slack variables on coverage constraints allow soft-fallback optimization and exact quantification of coverage shortfalls.
3. Deterministic execution with fixed random seeds.
4. Fast solution times ($\le 15$ seconds for 36 employees $\times$ 31 days).
5. Paired with a pure-Python independent validator and a deterministic greedy fallback generator.

## Consequences
- Requires Google OR-Tools dependency in the Python backend.
- Pure Python domain and validator ensure zero solver lock-in: the validator treats CP-SAT as just one producer of candidate rosters.

