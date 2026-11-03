# Technical Assessment Submission — Smart Roster Management System (RosterOps)

**Candidate:** Ramesh Chavan  
**Repository:** https://github.com/rameshchavan07/Smart-Roster-Management-System  
**Date:** November 3, 2026  

---

## 1. Approach Note (2–3 Sentences)

> We modeled the multi-brand monthly rostering challenge fundamentally as a **Demand vs. Supply constraint-satisfaction optimization problem**, using **Google OR-Tools CP-SAT** with heavily weighted slack variables so the solver never raises "infeasible" and guarantees mathematical optimality while surfacing every shortfall. 
> 
> A decoupled, pure-Python **independent validator** continuously recomputes conflicts (`E001`–`E009`) with root-cause explanations and second-order simulated recommendations, ensuring no invalid roster is ever presented as valid. 
> 
> The platform is wrapped in a high-density, keyboard-accessible **React 18 + TypeScript SPA** and a secure **FastAPI backend** featuring strict role-based access control, automated publish gating, and an immutable audit ledger.

---

## 2. Submission Email Draft

**Subject:** Submission: Smart Roster Management System Technical Assessment — Ramesh Chavan

**To:** Datastraw Hiring / Evaluation Team  

Dear Evaluation Team,

I am pleased to submit my technical assessment for the Smart Roster Management System (RosterOps). 

The platform has been built to meet all functional and non-functional requirements outlined in the brief, featuring a pure-Python scheduling engine, Google OR-Tools CP-SAT constraint optimization with deterministic greedy fallback, an independent conflict validator, what-if impact simulation, and a full-featured React 18 / TypeScript operations portal.

### Key Links & Resources
- **GitHub Repository**: https://github.com/rameshchavan07/Smart-Roster-Management-System
- **Interactive API Documentation**: `/docs` (OpenAPI Swagger UI)
- **Architecture & "How Do You Think" Answers**: Detailed in `README.md` (addressing all 8 evaluation questions)
- **Automated Test Suite**: 226 tests passing (`pytest backend/tests` in ~40s) including property-based tests with Hypothesis and golden tests for demo scenarios S1–S5.

### Demo Credentials (All personas use password: `TestPassword123!`)
1. **Operations Manager**: `ops@example.test` (Full company-wide scheduling, solver controls, publish gating, comp-off accruals)
2. **Pod Lead**: `lead.a@example.test` (Aanya Sharma — Pod A scoped operations, localized repairs, what-if simulations)
3. **Regular Employee**: `emp@example.test` (Riya Shah — Personal monthly schedule, leave submissions, comp-off balance)

### Core Highlights
- **Mathematical Integrity**: Hard constraints (locks, leaves, consecutive days limit, mandatory weekly offs) strictly dominate soft preferences.
- **Single-Resource Resolution**: Dedicated floater pool with 1-click recommendations solving single-resource 365-day coverage gaps.
- **Explainability**: Every conflict is classified by severity (`BLOCKING`, `WARNING`, `INFO`), tagged with root causes, and explained in plain language.
- **Production-Ready**: Multi-stage Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`), `docker-compose.prod.yml`, security headers, and rate limiting.

Thank you for the opportunity to work on this challenge. I look forward to your feedback and discussing the architecture in detail.

Sincerely,  
Ramesh Chavan  
LinkedIn: https://linkedin.com/in/rameshchavan07  
GitHub: https://github.com/rameshchavan07  
