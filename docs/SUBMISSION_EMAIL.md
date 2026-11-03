# Technical Assessment Submission — Smart Roster Management System (RosterOps)

**Candidate:** Ramesh Chavan  
**Repository:** [https://github.com/rameshchavan07/Smart-Roster-Management-System](https://github.com/rameshchavan07/Smart-Roster-Management-System)  
**Live Application:** [https://rosterops-web.onrender.com](https://rosterops-web.onrender.com)  
**Demo Video:** [https://drive.google.com/file/d/1CgaYl3Nw7C4FywWsiK6Pp96d0_OKQzSv/view?usp=sharing](https://drive.google.com/file/d/1CgaYl3Nw7C4FywWsiK6Pp96d0_OKQzSv/view?usp=sharing)  
**Date:** November 3, 2026  

---

## 1. Approach Note

> We modeled the multi-brand monthly rostering challenge fundamentally as a **demand-versus-supply constraint optimization problem**, using **Google OR-Tools CP-SAT** with weighted slack variables so the solver never raises "infeasible" and guarantees mathematical optimality while surfacing every shortfall.
> 
> A decoupled, pure-Python **independent validator** continuously recomputes conflicts (`E001`–`E009`) with root-cause explanations and second-order simulated recommendations, ensuring no invalid roster is ever presented as valid.
> 
> The platform is wrapped in a high-density, keyboard-accessible **React 18 + TypeScript SPA** and a secure **FastAPI backend** featuring strict role-based access control, automated publish gating, and an immutable audit ledger.

---

## 2. Submission Email Draft

**Subject:** Submission: Smart Roster Management System Technical Assessment — Ramesh Chavan  
**To:** Datastraw Hiring / Evaluation Team  

Dear Datastraw Hiring / Evaluation Team,

I am pleased to submit my technical assessment for the **Smart Roster Management System (RosterOps)**.

The solution has been designed and implemented to address the functional and non-functional requirements outlined in the assessment brief, with a strong focus on scheduling optimization, constraint validation, explainability, security, and user experience.

### Key Links & Resources
- **Live Application:** [https://rosterops-web.onrender.com](https://rosterops-web.onrender.com)
- **API Documentation (Swagger):** [https://rosterops-api.onrender.com/docs](https://rosterops-api.onrender.com/docs)
- **GitHub Repository:** [https://github.com/rameshchavan07/Smart-Roster-Management-System](https://github.com/rameshchavan07/Smart-Roster-Management-System)
- **Demo Video (Walkthrough):** [https://drive.google.com/file/d/1CgaYl3Nw7C4FywWsiK6Pp96d0_OKQzSv/view?usp=sharing](https://drive.google.com/file/d/1CgaYl3Nw7C4FywWsiK6Pp96d0_OKQzSv/view?usp=sharing)
- **Architecture & Design Decisions:** Detailed in the repository's [README.md](https://github.com/rameshchavan07/Smart-Roster-Management-System#readme), including responses to all eight evaluation questions.
- **Automated Test Suite:** 226 passing tests, covering property-based testing with Hypothesis and golden test scenarios S1–S5.

### Demo Credentials
All demo accounts use the password: **`DemoPass123!`**

1. **Operations Manager:** `ops@example.test` — Company-wide scheduling, solver controls, publishing, and comp-off management.
2. **Pod Lead:** `lead.a@example.test` — Pod A operations, localized roster repairs, and what-if simulations.
3. **Regular Employee:** `emp@example.test` — Personal schedules, leave submissions, and comp-off balance.

### Key Technical Highlights
- **Constraint-Based Optimization:** Google OR-Tools CP-SAT with weighted slack variables and deterministic greedy fallback.
- **Independent Validation:** A separate Python validation engine that identifies conflicts (`E001`–`E009`) with root-cause explanations.
- **What-If Simulations:** Impact analysis and actionable recommendations before applying roster changes.
- **Role-Based Access Control:** Secure, role-specific access with automated publishing gates and an immutable audit ledger.
- **Production Deployment:** Docker-based deployment, security headers, rate limiting, and a React 18 + TypeScript frontend backed by FastAPI.

### Approach Note
The system models multi-brand monthly rostering as a demand-versus-supply constraint optimization problem using Google OR-Tools CP-SAT, prioritizing hard constraints while using weighted slack variables to identify and explain unavoidable staffing shortfalls. An independent Python validator verifies roster integrity, detects conflicts, and provides actionable recommendations. The solution is delivered through a keyboard-accessible React 18 + TypeScript interface and a secure FastAPI backend with role-based access control and auditability.

Thank you for the opportunity to work on this assessment. I appreciate your time and consideration and look forward to your feedback and the opportunity to discuss the technical decisions and architecture behind the solution.

Best regards,  
**Ramesh Chavan**  
- **LinkedIn:** [https://linkedin.com/in/rameshchavan07](https://linkedin.com/in/rameshchavan07)  
- **GitHub:** [https://github.com/rameshchavan07](https://github.com/rameshchavan07)  
