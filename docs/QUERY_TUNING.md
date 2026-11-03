# Database Query and Index Tuning Report (T-902)

This document records the database index layout and PostgreSQL query execution plans (`EXPLAIN ANALYZE`) for high-frequency operational endpoints.

---

## 1. Index Layout & Definitions

### `roster_entries` Table
- `uq_roster_entry_period_emp_date` (UNIQUE): `(roster_period_id, employee_id, date)`
- `ix_roster_entries_period_date`: `(roster_period_id, date)` — used for Day View drawer and cell popover live impact.
- `ix_roster_entries_period_emp`: `(roster_period_id, employee_id)` — used for Employee-mode filtering.
- `ix_roster_entries_roster_period_id`: `(roster_period_id)` — used for complete monthly grid load.
- `ix_roster_entries_employee_id`: `(employee_id)` — used for employee history lookups.

### `roster_conflicts` Table
- `ix_roster_conflicts_period_severity`: `(roster_period_id, severity)` — used for gating check (0 blocking count) and KPI cards.
- `ix_roster_conflicts_roster_period_id`: `(roster_period_id)` — used for full conflict panel listings.
- `ix_roster_conflicts_brand_process_id`: `(brand_process_id)` — used for process-level conflict grouping.
- `ix_roster_conflicts_employee_id`: `(employee_id)` — used for individual employee conflict badges.

### `assignments` Table
- `uq_employee_bp_valid_from` (UNIQUE): `(employee_id, brand_process_id, valid_from)`
- `ix_assignments_employee_id`: `(employee_id)`
- `ix_assignments_brand_process_id`: `(brand_process_id)`

### `roster_periods` Table
- `uq_roster_periods_month_version` (UNIQUE): `(month, version)`
- `uq_roster_periods_month_published` (UNIQUE Partial): `(month)` WHERE `status = 'PUBLISHED'`
- `ix_roster_periods_month`: `(month)`

---

## 2. EXPLAIN ANALYZE Execution Plans

Empirical query plans generated via PostgreSQL 18 on production-shape data:

### 1. Day View Staffing Query
```sql
EXPLAIN ANALYZE 
SELECT * FROM roster_entries 
WHERE roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade' 
  AND date = '2026-12-15';
```
```
Bitmap Heap Scan on roster_entries  (cost=4.65..53.06 rows=36 width=128) (actual time=0.045..0.118 rows=36.00 loops=1)
  Recheck Cond: ((roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade'::uuid) AND (date = '2026-12-15'::date))
  Heap Blocks: exact=17
  Buffers: shared hit=19
  ->  Bitmap Index Scan on ix_roster_entries_period_date  (cost=0.00..4.64 rows=36 width=0) (actual time=0.021..0.022 rows=36.00 loops=1)
Planning Time: 6.017 ms
Execution Time: 0.141 ms
```
*Index Used:* `ix_roster_entries_period_date`  
*Execution Time:* **0.141 ms** (Sub-millisecond)

---

### 2. Gating & Blocking Conflict Check
```sql
EXPLAIN ANALYZE 
SELECT * FROM roster_conflicts 
WHERE roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade' 
  AND severity = 'BLOCKING';
```
```
Bitmap Heap Scan on roster_conflicts  (cost=5.93..94.54 rows=174 width=1097) (actual time=0.061..0.190 rows=174.00 loops=1)
  Recheck Cond: ((roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade'::uuid) AND ((severity)::text = 'BLOCKING'::text))
  Heap Blocks: exact=27
  Buffers: shared hit=28
  ->  Bitmap Index Scan on ix_roster_conflicts_period_severity  (cost=0.00..5.89 rows=174 width=0) (actual time=0.038..0.038 rows=174.00 loops=1)
Planning Time: 5.653 ms
Execution Time: 0.221 ms
```
*Index Used:* `ix_roster_conflicts_period_severity`  
*Execution Time:* **0.221 ms** (Sub-millisecond)

---

### 3. Full Monthly Grid Load (1,116 cells)
```sql
EXPLAIN ANALYZE 
SELECT * FROM roster_entries 
WHERE roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade';
```
```
Bitmap Heap Scan on roster_entries  (cost=16.91..79.84 rows=1114 width=128) (actual time=0.056..0.170 rows=1116.00 loops=1)
  Recheck Cond: (roster_period_id = '52b8f829-ae35-4880-8aa4-f8ffaf518ade'::uuid)
  Heap Blocks: exact=17
  Buffers: shared hit=19
  ->  Bitmap Index Scan on ix_roster_entries_roster_period_id  (cost=0.00..16.64 rows=1114 width=0) (actual time=0.042..0.042 rows=1116.00 loops=1)
Planning Time: 0.094 ms
Execution Time: 0.237 ms
```
*Index Used:* `ix_roster_entries_roster_period_id`  
*Execution Time:* **0.237 ms** (Sub-millisecond)

---

### 4. Version Listing & History Dropdown
```sql
EXPLAIN ANALYZE 
SELECT * FROM roster_periods 
WHERE month = '2026-12-01' 
ORDER BY version DESC;
```
```
Index Scan Backward using uq_roster_periods_month_version on roster_periods  (cost=0.15..8.17 rows=1 width=269) (actual time=0.009..0.010 rows=3.00 loops=1)
  Index Cond: (month = '2026-12-01'::date)
Planning Time: 0.167 ms
Execution Time: 0.026 ms
```
*Index Used:* `uq_roster_periods_month_version` (Index Scan Backward)  
*Execution Time:* **0.026 ms** (Sub-millisecond)

