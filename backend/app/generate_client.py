"""Generate TypeScript types and client from OpenAPI 3.1 schema.

Reads frontend/openapi.json and generates:
- frontend/src/api/generated/schema.ts (Type definitions)
- frontend/src/api/generated/client.ts (Typed HTTP API client)
"""

import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.export_openapi import export_openapi  # noqa: E402


def map_schema_type(prop: dict, required: bool = True) -> str:
    """Map OpenAPI property schema to TypeScript type."""
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        return ref_name

    if "anyOf" in prop:
        subtypes = [map_schema_type(sub) for sub in prop["anyOf"]]
        # filter duplicates while preserving order
        unique_subtypes = list(dict.fromkeys(subtypes))
        return " | ".join(unique_subtypes)

    t = prop.get("type")
    if t == "string":
        if prop.get("format") in ("date", "date-time"):
            return "string"
        return "string"
    elif t in ("integer", "number"):
        return "number"
    elif t == "boolean":
        return "boolean"
    elif t == "null":
        return "null"
    elif t == "array":
        items = prop.get("items", {})
        item_type = map_schema_type(items)
        if " | " in item_type:
            return f"({item_type})[]"
        return f"{item_type}[]"
    elif t == "object":
        if "additionalProperties" in prop:
            add_prop = prop["additionalProperties"]
            if isinstance(add_prop, dict):
                val_type = map_schema_type(add_prop)
                return f"Record<string, {val_type}>"
            return "Record<string, unknown>"
        return "Record<string, unknown>"

    return "unknown"


def generate_typescript_types(openapi: dict) -> str:
    """Generate TypeScript interfaces and types from OpenAPI components.schemas."""
    schemas = openapi.get("components", {}).get("schemas", {})
    lines = [
        "/**",
        " * Auto-generated TypeScript definitions from OpenAPI 3.1.0 specification.",
        " * Do not edit directly. Run `npm run generate-api` to regenerate.",
        " */",
        "",
    ]

    for name, schema in sorted(schemas.items()):
        description = schema.get("description", "")
        if description:
            lines.append("/**")
            for d_line in description.splitlines():
                lines.append(f" * {d_line}")
            lines.append(" */")

        # Enum type
        if "enum" in schema:
            values = schema["enum"]
            ts_values = " | ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
            lines.append(f"export type {name} = {ts_values};")
            lines.append("")
            continue

        # Object / Interface
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        lines.append(f"export interface {name} {{")
        for prop_name, prop_schema in properties.items():
            is_req = prop_name in required_fields
            ts_type = map_schema_type(prop_schema, required=is_req)
            opt_mark = "" if is_req else "?"
            lines.append(f"  {prop_name}{opt_mark}: {ts_type};")

        # additionalProperties on root object
        if schema.get("additionalProperties") is True:
            lines.append("  [key: string]: unknown;")

        lines.append("}")
        lines.append("")

    # Add convenient aliases for paginated responses and common domain schemas
    lines.extend([
        "// Convenient domain aliases",
        "export type LoginRequest = UserLoginRequest;",
        "export type PodListResponse = PaginatedResponse_PodRead_;",
        "export type EmployeeListResponse = PaginatedResponse_EmployeeRead_;",
        "export type ProcessListResponse = PaginatedResponse_ProcessRead_;",
        "export type BrandListResponse = PaginatedResponse_BrandRead_;",
        "export type BrandProcessListResponse = PaginatedResponse_BrandProcessRead_;",
        "export type AssignmentListResponse = PaginatedResponse_AssignmentRead_;",
        "export type CoverageRuleListResponse = PaginatedResponse_CoverageRuleRead_;",
        "export type HolidayListResponse = PaginatedResponse_HolidayRead_;",
        "export type WeeklyOffRuleListResponse = PaginatedResponse_WeeklyOffRuleRead_;",
        "export type EmployeePreferenceListResponse = PaginatedResponse_EmployeePreferenceRead_;",
        "export type LeaveListResponse = PaginatedResponse_LeaveRead_;",
        "export type CompOffLedgerListResponse = PaginatedResponse_CompOffLedgerRead_;",
        "export type AuditLogListResponse = PaginatedResponse_AuditLogRead_;",
        "export type RosterSuggestionRead = RosterSuggestionItem;",
        "",
    ])

    return "\n".join(lines)


def generate_typescript_client(openapi: dict) -> str:
    """Generate typed API client methods grouped by domain service."""
    lines = [
        "/**",
        " * Auto-generated typed API Client using apiClient with Bearer auth and 401 refresh.",
        " * Do not edit directly. Run `npm run generate-api` to regenerate.",
        " */",
        "",
        "import { apiClient, apiClientBlob } from '../client';",
        "import type * as Schema from './schema';",
        "",
        "function buildQuery(params?: Record<string, unknown>): string {",
        "  if (!params) return '';",
        "  const query = new URLSearchParams();",
        "  for (const [key, val] of Object.entries(params)) {",
        "    if (val !== undefined && val !== null && val !== '') {",
        "      query.set(key, String(val));",
        "    }",
        "  }",
        "  const qs = query.toString();",
        "  return qs ? `?${qs}` : '';",
        "}",
        "",
        "export class ApiClient {",
        "  // --------------------------------------------------------------------------",
        "  // Auth",
        "  // --------------------------------------------------------------------------",
        "  readonly auth = {",
        "    login: (body: Schema.LoginRequest) =>",
        "      apiClient<Schema.TokenResponse>('/auth/login', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    refresh: () =>",
        "      apiClient<Schema.TokenResponse>('/auth/refresh', {",
        "        method: 'POST',",
        "      }),",
        "    logout: () =>",
        "      apiClient<{ message: string }>('/auth/logout', {",
        "        method: 'POST',",
        "      }),",
        "    me: () => apiClient<Schema.UserRead>('/auth/me'),",
        "    demoAccounts: () =>",
        "      apiClient<Schema.DemoAccountRead[]>('/auth/demo-accounts'),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Pods",
        "  // --------------------------------------------------------------------------",
        "  readonly pods = {",
        "    list: (params?: { page?: number; size?: number; search?: string }) =>",
        "      apiClient<Schema.PodListResponse>(`/pods${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.PodRead>(`/pods/${id}`),",
        "    create: (body: Schema.PodCreate) =>",
        "      apiClient<Schema.PodRead>('/pods', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.PodUpdate) =>",
        "      apiClient<Schema.PodRead>(`/pods/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/pods/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Employees",
        "  // --------------------------------------------------------------------------",
        "  readonly employees = {",
        "    list: (params?: {",
        "      page?: number;",
        "      size?: number;",
        "      search?: string;",
        "      pod_id?: string;",
        "      role?: string;",
        "      weekly_off_mode?: string;",
        "      is_active?: boolean;",
        "    }) => apiClient<Schema.EmployeeListResponse>(`/employees${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.EmployeeRead>(`/employees/${id}`),",
        "    create: (body: Schema.EmployeeCreate) =>",
        "      apiClient<Schema.EmployeeRead>('/employees', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.EmployeeUpdate) =>",
        "      apiClient<Schema.EmployeeRead>(`/employees/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/employees/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "    compOffBalance: (id: string) =>",
        "      apiClient<Schema.CompOffBalanceRead>(`/employees/${id}/comp-off-balance`),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Processes",
        "  // --------------------------------------------------------------------------",
        "  readonly processes = {",
        "    list: (params?: { page?: number; size?: number; search?: string }) =>",
        "      apiClient<Schema.ProcessListResponse>(`/processes${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.ProcessRead>(`/processes/${id}`),",
        "    create: (body: Schema.ProcessCreate) =>",
        "      apiClient<Schema.ProcessRead>('/processes', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.ProcessUpdate) =>",
        "      apiClient<Schema.ProcessRead>(`/processes/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/processes/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Brands",
        "  // --------------------------------------------------------------------------",
        "  readonly brands = {",
        "    list: (params?: { page?: number; size?: number; search?: string; tier?: string }) =>",
        "      apiClient<Schema.BrandListResponse>(`/brands${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.BrandRead>(`/brands/${id}`),",
        "    create: (body: Schema.BrandCreate) =>",
        "      apiClient<Schema.BrandRead>('/brands', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.BrandUpdate) =>",
        "      apiClient<Schema.BrandRead>(`/brands/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/brands/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Brand Processes",
        "  // --------------------------------------------------------------------------",
        "  readonly brandProcesses = {",
        "    list: (params?: { brand_id?: string; process_id?: string; is_active?: boolean }) =>",
        "      apiClient<Schema.BrandProcessListResponse>(`/brand-processes${buildQuery(params)}`),",
        "    get: (id: string) =>",
        "      apiClient<Schema.BrandProcessRead>(`/brand-processes/${id}`),",
        "    create: (body: Schema.BrandProcessCreate) =>",
        "      apiClient<Schema.BrandProcessRead>('/brand-processes', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.BrandProcessUpdate) =>",
        "      apiClient<Schema.BrandProcessRead>(`/brand-processes/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/brand-processes/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Assignments",
        "  // --------------------------------------------------------------------------",
        "  readonly assignments = {",
        "    list: (params?: { employee_id?: string; brand_process_id?: string; type?: string }) =>",
        "      apiClient<Schema.AssignmentListResponse>(`/assignments${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.AssignmentRead>(`/assignments/${id}`),",
        "    create: (body: Schema.AssignmentCreate) =>",
        "      apiClient<Schema.AssignmentRead>('/assignments', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.AssignmentUpdate) =>",
        "      apiClient<Schema.AssignmentRead>(`/assignments/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/assignments/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Coverage Rules",
        "  // --------------------------------------------------------------------------",
        "  readonly coverageRules = {",
        "    list: (params?: { brand_process_id?: string }) =>",
        "      apiClient<Schema.CoverageRuleListResponse>(`/coverage-rules${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.CoverageRuleRead>(`/coverage-rules/${id}`),",
        "    create: (body: Schema.CoverageRuleCreate) =>",
        "      apiClient<Schema.CoverageRuleRead>('/coverage-rules', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.CoverageRuleUpdate) =>",
        "      apiClient<Schema.CoverageRuleRead>(`/coverage-rules/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/coverage-rules/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Holidays",
        "  // --------------------------------------------------------------------------",
        "  readonly holidays = {",
        "    list: (params?: { year?: number; brand_id?: string }) =>",
        "      apiClient<Schema.HolidayListResponse>(`/holidays${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.HolidayRead>(`/holidays/${id}`),",
        "    create: (body: Schema.HolidayCreate) =>",
        "      apiClient<Schema.HolidayRead>('/holidays', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.HolidayUpdate) =>",
        "      apiClient<Schema.HolidayRead>(`/holidays/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/holidays/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Weekly-Off Rules",
        "  // --------------------------------------------------------------------------",
        "  readonly weeklyOffRules = {",
        "    list: (params?: { employee_id?: string }) =>",
        "      apiClient<Schema.WeeklyOffRuleListResponse>(`/weekly-off-rules${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.WeeklyOffRuleRead>(`/weekly-off-rules/${id}`),",
        "    create: (body: Schema.WeeklyOffRuleCreate) =>",
        "      apiClient<Schema.WeeklyOffRuleRead>('/weekly-off-rules', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.WeeklyOffRuleUpdate) =>",
        "      apiClient<Schema.WeeklyOffRuleRead>(`/weekly-off-rules/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/weekly-off-rules/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Preferences",
        "  // --------------------------------------------------------------------------",
        "  readonly preferences = {",
        "    list: (params?: { employee_id?: string; month?: string }) =>",
        "      apiClient<Schema.EmployeePreferenceListResponse>(`/preferences${buildQuery(params)}`),",
        "    get: (id: string) =>",
        "      apiClient<Schema.EmployeePreferenceRead>(`/preferences/${id}`),",
        "    create: (body: Schema.EmployeePreferenceCreate) =>",
        "      apiClient<Schema.EmployeePreferenceRead>('/preferences', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.EmployeePreferenceUpdate) =>",
        "      apiClient<Schema.EmployeePreferenceRead>(`/preferences/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/preferences/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Leaves",
        "  // --------------------------------------------------------------------------",
        "  readonly leaves = {",
        "    list: (params?: { employee_id?: string; status?: string; month?: string }) =>",
        "      apiClient<Schema.LeaveListResponse>(`/leaves${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.LeaveRead>(`/leaves/${id}`),",
        "    create: (body: Schema.LeaveCreate) =>",
        "      apiClient<Schema.LeaveRead>('/leaves', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    update: (id: string, body: Schema.LeaveUpdate) =>",
        "      apiClient<Schema.LeaveRead>(`/leaves/${id}`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    approve: (id: string) =>",
        "      apiClient<Schema.LeaveRead>(`/leaves/${id}/approve`, {",
        "        method: 'POST',",
        "      }),",
        "    reject: (id: string) =>",
        "      apiClient<Schema.LeaveRead>(`/leaves/${id}/reject`, {",
        "        method: 'POST',",
        "      }),",
        "    cancel: (id: string) =>",
        "      apiClient<Schema.LeaveRead>(`/leaves/${id}/cancel`, {",
        "        method: 'POST',",
        "      }),",
        "    delete: (id: string) =>",
        "      apiClient<{ message: string }>(`/leaves/${id}`, {",
        "        method: 'DELETE',",
        "      }),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Comp-Offs",
        "  // --------------------------------------------------------------------------",
        "  readonly compOffs = {",
        "    list: (params?: { employee_id?: string; kind?: string }) =>",
        "      apiClient<Schema.CompOffLedgerListResponse>(`/comp-offs${buildQuery(params)}`),",
        "    balance: () => apiClient<Schema.CompOffBalanceRead>('/comp-offs/balance'),",
        "    credit: (body: Schema.CompOffLedgerCreate) =>",
        "      apiClient<Schema.CompOffLedgerRead>('/comp-offs', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    redeem: (body: Schema.CompOffRedeemRequest) =>",
        "      apiClient<Schema.CompOffLedgerRead>('/comp-offs/redeem', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    accrueFromRoster: (rosterId: string) =>",
        "      apiClient<{ message: string; accrued_count: number }>(",
        "        `/comp-offs/accrue-from-roster/${rosterId}`,",
        "        { method: 'POST' }",
        "      ),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Rosters",
        "  // --------------------------------------------------------------------------",
        "  readonly rosters = {",
        "    list: (params?: { month?: string; status?: string }) =>",
        "      apiClient<Schema.RosterPeriodRead[]>(`/rosters${buildQuery(params)}`),",
        "    get: (id: string) => apiClient<Schema.RosterPeriodRead>(`/rosters/${id}`),",
        "    generate: (body: Schema.RosterGenerateRequest) =>",
        "      apiClient<Schema.RosterGenerateResponse>('/rosters', {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    publish: (id: string) =>",
        "      apiClient<Schema.RosterPeriodRead>(`/rosters/${id}/publish`, {",
        "        method: 'POST',",
        "      }),",
        "    clone: (id: string, body?: Schema.RosterCloneRequest) =>",
        "      apiClient<Schema.RosterPeriodRead>(`/rosters/${id}/clone`, {",
        "        method: 'POST',",
        "        body: JSON.stringify(body || {}),",
        "      }),",
        "    grid: (id: string, params?: { view?: string; ref_id?: string }) =>",
        "      apiClient<Schema.RosterGridViewResponse>(`/rosters/${id}/grid${buildQuery(params)}`),",
        "    coverage: (id: string, params?: { brand_process_id?: string; date_from?: string; date_to?: string }) =>",
        "      apiClient<Schema.RosterCoverageCell[]>(`/rosters/${id}/coverage${buildQuery(params)}`),",
        "    day: (id: string, params?: { date?: string }) =>",
        "      apiClient<Schema.RosterDayViewResponse>(`/rosters/${id}/day${buildQuery(params)}`),",
        "    entries: (id: string, body: Schema.RosterEntriesBatchUpdateRequest) =>",
        "      apiClient<Schema.RosterEntriesUpdateResponse>(`/rosters/${id}/entries`, {",
        "        method: 'PUT',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    lock: (id: string, body: Schema.RosterEntriesLockRequest) =>",
        "      apiClient<Schema.RosterEntriesLockResponse>(`/rosters/${id}/entries/lock`, {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    impact: (id: string, body: Schema.RosterImpactRequest) =>",
        "      apiClient<Schema.RosterImpactResponse>(`/rosters/${id}/impact`, {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    conflicts: (id: string, params?: { severity?: string }) =>",
        "      apiClient<Schema.RosterConflictRead[]>(`/rosters/${id}/conflicts${buildQuery(params)}`),",
        "    suggestions: (id: string, params?: { conflict_id?: string; brand_process_id?: string; date?: string }) =>",
        "      apiClient<Schema.RosterSuggestionRead[]>(`/rosters/${id}/suggestions${buildQuery(params)}`),",
        "    acknowledge: (id: string, body: Schema.RosterAcknowledgeRequest) =>",
        "      apiClient<Schema.RosterConflictRead>(`/rosters/${id}/acknowledge`, {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    repair: (id: string, body: Schema.RosterRepairRequest) =>",
        "      apiClient<Schema.RosterRepairResponse>(`/rosters/${id}/repair`, {",
        "        method: 'POST',",
        "        body: JSON.stringify(body),",
        "      }),",
        "    compare: (a: string, b: string) =>",
        "      apiClient<Schema.RosterCompareResponse>(`/rosters/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),",
        "    export: (id: string, params?: { format?: 'csv' | 'xlsx'; view?: string; date?: string }) =>",
        "      apiClientBlob(`/rosters/${id}/export${buildQuery(params)}`),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Audit Logs",
        "  // --------------------------------------------------------------------------",
        "  readonly auditLogs = {",
        "    list: (params?: {",
        "      page?: number;",
        "      size?: number;",
        "      entity_type?: string;",
        "      action?: string;",
        "      user_email?: string;",
        "    }) => apiClient<Schema.AuditLogListResponse>(`/audit-logs${buildQuery(params)}`),",
        "  };",
        "",
        "  // --------------------------------------------------------------------------",
        "  // Health & Readiness",
        "  // --------------------------------------------------------------------------",
        "  readonly health = {",
        "    checkHealth: () => apiClient<Record<string, unknown>>('/health'),",
        "    checkReady: () => apiClient<Record<string, string>>('/ready'),",
        "  };",
        "}",
        "",
        "export const api = new ApiClient();",
        "",
    ]
    return "\n".join(lines)


def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    frontend_dir = root_dir / "frontend"
    openapi_file = frontend_dir / "openapi.json"

    # 1. Export OpenAPI JSON
    openapi = export_openapi(openapi_file)

    # 2. Generate TypeScript Types
    generated_dir = frontend_dir / "src" / "api" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    types_file = generated_dir / "schema.ts"
    types_content = generate_typescript_types(openapi)
    types_file.write_text(types_content, encoding="utf-8")
    print(f"Generated TypeScript types at {types_file}")

    # 3. Generate Typed Client
    client_file = generated_dir / "client.ts"
    client_content = generate_typescript_client(openapi)
    client_file.write_text(client_content, encoding="utf-8")
    print(f"Generated Typed API Client at {client_file}")


if __name__ == "__main__":
    main()
