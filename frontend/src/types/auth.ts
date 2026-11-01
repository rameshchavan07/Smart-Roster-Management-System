/**
 * Authentication and User types conforming to SECURITY.md §2 and API_DOCUMENTATION.md §1 & §4.
 */

export type UserRole = 'OPS_MANAGER' | 'POD_LEAD' | 'EMPLOYEE';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  employee_id: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface DemoAccountInfo {
  role: UserRole;
  email: string;
  description: string;
  employee_code?: string | null;
  employee_name?: string | null;
  default_password?: string | null;
}
