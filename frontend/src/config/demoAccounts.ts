/**
 * Seeded Demo Accounts configuration for evaluator access per SAMPLE_DATA.md §8
 * and UI_UX_REQUIREMENTS.md §3.1 (Login screen demo disclosure).
 */

export interface DemoAccount {
  role: 'OPS_MANAGER' | 'POD_LEAD' | 'EMPLOYEE';
  roleLabel: string;
  email: string;
  scope: string;
  employeeCode?: string;
  employeeName?: string;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'OPS_MANAGER',
    roleLabel: 'Ops Manager',
    email: 'ops@example.test',
    scope: 'Full company-wide management, generation, and publishing',
  },
  {
    role: 'POD_LEAD',
    roleLabel: 'Pod Lead (Pod A)',
    email: 'lead.a@example.test',
    scope: 'Pod A scoped management; reviews own pod roster',
    employeeCode: 'EMP-001',
    employeeName: 'Aarav Sharma',
  },
  {
    role: 'EMPLOYEE',
    roleLabel: 'Employee',
    email: 'emp@example.test',
    scope: 'Linked to EMP-007 (Riya Shah); read-only personal schedule & ledger',
    employeeCode: 'EMP-007',
    employeeName: 'Riya Shah',
  },
];

