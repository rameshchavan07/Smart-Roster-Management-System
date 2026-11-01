"""Master data domain services implementing business rules and audit hooks.

Covers pods, employees, processes, brands, brand_processes, and assignments.
Conforms to DATABASE_DESIGN.md §3, §5 and API_DOCUMENTATION.md §4.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.core import Assignment, Brand, BrandProcess, Employee, Pod, Process
from app.models.rules import CoverageRule, Leave
from app.repositories.core import (
    AssignmentRepository,
    AuditLogRepository,
    BrandProcessRepository,
    BrandRepository,
    EmployeeRepository,
    PodRepository,
    ProcessRepository,
)
from app.schemas.core import (
    AssignmentCreate,
    AssignmentUpdate,
    BrandCreate,
    BrandProcessCreate,
    BrandProcessUpdate,
    BrandUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    PodCreate,
    PodUpdate,
    ProcessCreate,
    ProcessUpdate,
)


class PodService:
    """Business service for Pod management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = PodRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_pod(self, pod_id: uuid.UUID) -> Pod:
        pod = self.repo.get_by_id(pod_id)
        if not pod:
            raise NotFoundError(f"Pod with id '{pod_id}' not found")
        return pod

    def list_pods(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[Sequence[Pod], int]:
        return self.repo.list(offset=offset, limit=limit, is_active=is_active)

    def create_pod(self, data: PodCreate, actor_id: uuid.UUID | None = None) -> Pod:
        if self.repo.get_by_name(data.name):
            raise ConflictError(f"Pod with name '{data.name}' already exists")

        if data.lead_employee_id:
            lead = self.employee_repo.get_by_id(data.lead_employee_id)
            if not lead:
                raise NotFoundError(f"Lead employee '{data.lead_employee_id}' not found")

        pod = Pod(name=data.name, lead_employee_id=data.lead_employee_id)
        self.repo.create(pod)

        self.audit_repo.log_mutation(
            action="pod.create",
            entity_type="Pod",
            entity_id=str(pod.id),
            user_id=actor_id,
            before=None,
            after={
                "name": pod.name,
                "lead_employee_id": str(pod.lead_employee_id) if pod.lead_employee_id else None,
            },
        )
        return pod

    def update_pod(
        self, pod_id: uuid.UUID, data: PodUpdate, actor_id: uuid.UUID | None = None
    ) -> Pod:
        pod = self.get_pod(pod_id)
        before_state = {
            "name": pod.name,
            "lead_employee_id": str(pod.lead_employee_id) if pod.lead_employee_id else None,
            "is_active": pod.is_active,
        }

        if data.name is not None and data.name != pod.name:
            existing = self.repo.get_by_name(data.name)
            if existing and existing.id != pod.id:
                raise ConflictError(f"Pod with name '{data.name}' already exists")
            pod.name = data.name

        if data.lead_employee_id is not None:
            lead = self.employee_repo.get_by_id(data.lead_employee_id)
            if not lead:
                raise NotFoundError(f"Lead employee '{data.lead_employee_id}' not found")
            pod.lead_employee_id = data.lead_employee_id

        if data.is_active is not None:
            pod.is_active = data.is_active

        self.repo.update(pod)

        after_state = {
            "name": pod.name,
            "lead_employee_id": str(pod.lead_employee_id) if pod.lead_employee_id else None,
            "is_active": pod.is_active,
        }
        self.audit_repo.log_mutation(
            action="pod.update",
            entity_type="Pod",
            entity_id=str(pod.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return pod

    def delete_pod(self, pod_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        pod = self.get_pod(pod_id)
        has_employees = (
            self.session.scalar(
                select(func.count()).select_from(Employee).where(Employee.pod_id == pod_id)
            )
            or 0
        )
        has_brands = (
            self.session.scalar(
                select(func.count()).select_from(Brand).where(Brand.pod_id == pod_id)
            )
            or 0
        )
        if has_employees > 0 or has_brands > 0:
            raise ConflictError(
                "Cannot delete pod with associated employees or brands. Set is_active=false to deactivate."
            )

        before_state = {"name": pod.name, "id": str(pod.id)}
        self.repo.delete(pod)

        self.audit_repo.log_mutation(
            action="pod.delete",
            entity_type="Pod",
            entity_id=str(pod_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class EmployeeService:
    """Business service for Employee management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = EmployeeRepository(session)
        self.pod_repo = PodRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_employee(self, employee_id: uuid.UUID) -> Employee:
        emp = self.repo.get_by_id(employee_id)
        if not emp:
            raise NotFoundError(f"Employee with id '{employee_id}' not found")
        return emp

    def list_employees(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        pod_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        is_floater: bool | None = None,
    ) -> tuple[Sequence[Employee], int]:
        def query_filter(stmt: Any) -> Any:
            if pod_id is not None:
                stmt = stmt.where(Employee.pod_id == pod_id)
            if is_floater is not None:
                stmt = stmt.where(Employee.is_floater == is_floater)
            return stmt

        return self.repo.list(
            offset=offset,
            limit=limit,
            is_active=is_active,
            query_modifier=query_filter,
        )

    def create_employee(self, data: EmployeeCreate, actor_id: uuid.UUID | None = None) -> Employee:
        if self.repo.get_by_code(data.code):
            raise ConflictError(f"Employee code '{data.code}' already exists")

        if data.email and self.repo.get_by_email(data.email):
            raise ConflictError(f"Employee with email '{data.email}' already exists")

        if not self.pod_repo.get_by_id(data.pod_id):
            raise NotFoundError(f"Pod with id '{data.pod_id}' not found")

        emp = Employee(
            code=data.code,
            full_name=data.full_name,
            email=data.email,
            pod_id=data.pod_id,
            is_floater=data.is_floater,
            weekly_off_count=data.weekly_off_count,
            max_consecutive_days=data.max_consecutive_days,
            max_concurrent_processes=data.max_concurrent_processes,
            joined_on=data.joined_on,
            left_on=data.left_on,
        )
        self.repo.create(emp)

        self.audit_repo.log_mutation(
            action="employee.create",
            entity_type="Employee",
            entity_id=str(emp.id),
            user_id=actor_id,
            before=None,
            after={"code": emp.code, "full_name": emp.full_name, "pod_id": str(emp.pod_id)},
        )
        return emp

    def update_employee(
        self,
        employee_id: uuid.UUID,
        data: EmployeeUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Employee:
        emp = self.get_employee(employee_id)
        before_state = {
            "code": emp.code,
            "full_name": emp.full_name,
            "email": emp.email,
            "pod_id": str(emp.pod_id),
            "is_floater": emp.is_floater,
            "is_active": emp.is_active,
        }

        if data.code is not None and data.code != emp.code:
            existing = self.repo.get_by_code(data.code)
            if existing and existing.id != emp.id:
                raise ConflictError(f"Employee code '{data.code}' already exists")
            emp.code = data.code

        if data.email is not None and data.email != emp.email:
            existing_email = self.repo.get_by_email(data.email)
            if existing_email and existing_email.id != emp.id:
                raise ConflictError(f"Employee email '{data.email}' already exists")
            emp.email = data.email

        if data.pod_id is not None and data.pod_id != emp.pod_id:
            if not self.pod_repo.get_by_id(data.pod_id):
                raise NotFoundError(f"Pod with id '{data.pod_id}' not found")
            emp.pod_id = data.pod_id

        if data.full_name is not None:
            emp.full_name = data.full_name
        if data.is_floater is not None:
            emp.is_floater = data.is_floater
        if data.weekly_off_count is not None:
            emp.weekly_off_count = data.weekly_off_count
        if data.max_consecutive_days is not None:
            emp.max_consecutive_days = data.max_consecutive_days
        if data.max_concurrent_processes is not None:
            emp.max_concurrent_processes = data.max_concurrent_processes
        if data.joined_on is not None:
            emp.joined_on = data.joined_on
        if data.left_on is not None:
            emp.left_on = data.left_on
        if data.is_active is not None:
            emp.is_active = data.is_active

        self.repo.update(emp)

        after_state = {
            "code": emp.code,
            "full_name": emp.full_name,
            "email": emp.email,
            "pod_id": str(emp.pod_id),
            "is_floater": emp.is_floater,
            "is_active": emp.is_active,
        }
        self.audit_repo.log_mutation(
            action="employee.update",
            entity_type="Employee",
            entity_id=str(emp.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return emp

    def delete_employee(self, employee_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        emp = self.get_employee(employee_id)
        has_assignments = (
            self.session.scalar(
                select(func.count())
                .select_from(Assignment)
                .where(Assignment.employee_id == employee_id)
            )
            or 0
        )
        has_leaves = (
            self.session.scalar(
                select(func.count()).select_from(Leave).where(Leave.employee_id == employee_id)
            )
            or 0
        )
        if has_assignments > 0 or has_leaves > 0:
            raise ConflictError(
                "Cannot delete employee with associated assignments or records. Set is_active=false to deactivate."
            )

        before_state = {"code": emp.code, "full_name": emp.full_name, "id": str(emp.id)}
        self.repo.delete(emp)

        self.audit_repo.log_mutation(
            action="employee.delete",
            entity_type="Employee",
            entity_id=str(employee_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class ProcessService:
    """Business service for Process management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ProcessRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_process(self, process_id: uuid.UUID) -> Process:
        proc = self.repo.get_by_id(process_id)
        if not proc:
            raise NotFoundError(f"Process with id '{process_id}' not found")
        return proc

    def list_processes(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[Sequence[Process], int]:
        return self.repo.list(offset=offset, limit=limit, is_active=is_active)

    def create_process(self, data: ProcessCreate, actor_id: uuid.UUID | None = None) -> Process:
        if self.repo.get_by_code(data.code):
            raise ConflictError(f"Process code '{data.code}' already exists")
        if self.repo.get_by_name(data.name):
            raise ConflictError(f"Process name '{data.name}' already exists")

        proc = Process(name=data.name, code=data.code, description=data.description)
        self.repo.create(proc)

        self.audit_repo.log_mutation(
            action="process.create",
            entity_type="Process",
            entity_id=str(proc.id),
            user_id=actor_id,
            before=None,
            after={"code": proc.code, "name": proc.name},
        )
        return proc

    def update_process(
        self,
        process_id: uuid.UUID,
        data: ProcessUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Process:
        proc = self.get_process(process_id)
        before_state = {
            "name": proc.name,
            "code": proc.code,
            "description": proc.description,
            "is_active": proc.is_active,
        }

        if data.code is not None and data.code != proc.code:
            existing = self.repo.get_by_code(data.code)
            if existing and existing.id != proc.id:
                raise ConflictError(f"Process code '{data.code}' already exists")
            proc.code = data.code

        if data.name is not None and data.name != proc.name:
            existing_name = self.repo.get_by_name(data.name)
            if existing_name and existing_name.id != proc.id:
                raise ConflictError(f"Process name '{data.name}' already exists")
            proc.name = data.name

        if data.description is not None:
            proc.description = data.description
        if data.is_active is not None:
            proc.is_active = data.is_active

        self.repo.update(proc)

        after_state = {
            "name": proc.name,
            "code": proc.code,
            "description": proc.description,
            "is_active": proc.is_active,
        }
        self.audit_repo.log_mutation(
            action="process.update",
            entity_type="Process",
            entity_id=str(proc.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return proc

    def delete_process(self, process_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        proc = self.get_process(process_id)
        has_brand_processes = (
            self.session.scalar(
                select(func.count())
                .select_from(BrandProcess)
                .where(BrandProcess.process_id == process_id)
            )
            or 0
        )
        if has_brand_processes > 0:
            raise ConflictError(
                "Cannot delete process configured for active brands. Set is_active=false to deactivate."
            )

        before_state = {"code": proc.code, "name": proc.name, "id": str(proc.id)}
        self.repo.delete(proc)

        self.audit_repo.log_mutation(
            action="process.delete",
            entity_type="Process",
            entity_id=str(process_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class BrandService:
    """Business service for Brand management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = BrandRepository(session)
        self.pod_repo = PodRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_brand(self, brand_id: uuid.UUID) -> Brand:
        brand = self.repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundError(f"Brand with id '{brand_id}' not found")
        return brand

    def list_brands(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        pod_id: uuid.UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[Brand], int]:
        def query_filter(stmt: Any) -> Any:
            if pod_id is not None:
                stmt = stmt.where(Brand.pod_id == pod_id)
            return stmt

        return self.repo.list(
            offset=offset,
            limit=limit,
            is_active=is_active,
            query_modifier=query_filter,
        )

    def create_brand(self, data: BrandCreate, actor_id: uuid.UUID | None = None) -> Brand:
        if self.repo.get_by_code(data.code):
            raise ConflictError(f"Brand code '{data.code}' already exists")
        if self.repo.get_by_name(data.name):
            raise ConflictError(f"Brand name '{data.name}' already exists")

        if data.pod_id and not self.pod_repo.get_by_id(data.pod_id):
            raise NotFoundError(f"Pod with id '{data.pod_id}' not found")

        brand = Brand(name=data.name, code=data.code, pod_id=data.pod_id)
        self.repo.create(brand)

        self.audit_repo.log_mutation(
            action="brand.create",
            entity_type="Brand",
            entity_id=str(brand.id),
            user_id=actor_id,
            before=None,
            after={
                "code": brand.code,
                "name": brand.name,
                "pod_id": str(brand.pod_id) if brand.pod_id else None,
            },
        )
        return brand

    def update_brand(
        self,
        brand_id: uuid.UUID,
        data: BrandUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Brand:
        brand = self.get_brand(brand_id)
        before_state = {
            "name": brand.name,
            "code": brand.code,
            "pod_id": str(brand.pod_id) if brand.pod_id else None,
            "is_active": brand.is_active,
        }

        if data.code is not None and data.code != brand.code:
            existing = self.repo.get_by_code(data.code)
            if existing and existing.id != brand.id:
                raise ConflictError(f"Brand code '{data.code}' already exists")
            brand.code = data.code

        if data.name is not None and data.name != brand.name:
            existing_name = self.repo.get_by_name(data.name)
            if existing_name and existing_name.id != brand.id:
                raise ConflictError(f"Brand name '{data.name}' already exists")
            brand.name = data.name

        if data.pod_id is not None and data.pod_id != brand.pod_id:
            if not self.pod_repo.get_by_id(data.pod_id):
                raise NotFoundError(f"Pod with id '{data.pod_id}' not found")
            brand.pod_id = data.pod_id

        if data.is_active is not None:
            brand.is_active = data.is_active

        self.repo.update(brand)

        after_state = {
            "name": brand.name,
            "code": brand.code,
            "pod_id": str(brand.pod_id) if brand.pod_id else None,
            "is_active": brand.is_active,
        }
        self.audit_repo.log_mutation(
            action="brand.update",
            entity_type="Brand",
            entity_id=str(brand.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return brand

    def delete_brand(self, brand_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        brand = self.get_brand(brand_id)
        has_brand_processes = (
            self.session.scalar(
                select(func.count())
                .select_from(BrandProcess)
                .where(BrandProcess.brand_id == brand_id)
            )
            or 0
        )
        if has_brand_processes > 0:
            raise ConflictError(
                "Cannot delete brand with configured processes. Set is_active=false to deactivate."
            )

        before_state = {"code": brand.code, "name": brand.name, "id": str(brand.id)}
        self.repo.delete(brand)

        self.audit_repo.log_mutation(
            action="brand.delete",
            entity_type="Brand",
            entity_id=str(brand_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class BrandProcessService:
    """Business service for BrandProcess management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = BrandProcessRepository(session)
        self.brand_repo = BrandRepository(session)
        self.process_repo = ProcessRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_brand_process(self, bp_id: uuid.UUID) -> BrandProcess:
        bp = self.repo.get_by_id(bp_id)
        if not bp:
            raise NotFoundError(f"BrandProcess with id '{bp_id}' not found")
        return bp

    def list_brand_processes(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        brand_id: uuid.UUID | None = None,
        process_id: uuid.UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[BrandProcess], int]:
        def query_filter(stmt: Any) -> Any:
            if brand_id is not None:
                stmt = stmt.where(BrandProcess.brand_id == brand_id)
            if process_id is not None:
                stmt = stmt.where(BrandProcess.process_id == process_id)
            return stmt

        return self.repo.list(
            offset=offset,
            limit=limit,
            is_active=is_active,
            query_modifier=query_filter,
        )

    def create_brand_process(
        self, data: BrandProcessCreate, actor_id: uuid.UUID | None = None
    ) -> BrandProcess:
        if not self.brand_repo.get_by_id(data.brand_id):
            raise NotFoundError(f"Brand with id '{data.brand_id}' not found")
        if not self.process_repo.get_by_id(data.process_id):
            raise NotFoundError(f"Process with id '{data.process_id}' not found")

        if self.repo.get_by_brand_and_process(data.brand_id, data.process_id):
            raise ConflictError("Process is already configured for this Brand")

        bp = BrandProcess(
            brand_id=data.brand_id,
            process_id=data.process_id,
            calendar_type=data.calendar_type,
            min_coverage_default=data.min_coverage_default,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self.repo.create(bp)

        self.audit_repo.log_mutation(
            action="brand_process.create",
            entity_type="BrandProcess",
            entity_id=str(bp.id),
            user_id=actor_id,
            before=None,
            after={
                "brand_id": str(bp.brand_id),
                "process_id": str(bp.process_id),
                "calendar_type": bp.calendar_type.value,
            },
        )
        return bp

    def update_brand_process(
        self,
        bp_id: uuid.UUID,
        data: BrandProcessUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> BrandProcess:
        bp = self.get_brand_process(bp_id)
        before_state = {
            "calendar_type": bp.calendar_type.value,
            "min_coverage_default": bp.min_coverage_default,
            "is_active": bp.is_active,
        }

        if data.calendar_type is not None:
            bp.calendar_type = data.calendar_type
        if data.min_coverage_default is not None:
            bp.min_coverage_default = data.min_coverage_default
        if data.valid_from is not None:
            bp.valid_from = data.valid_from
        if data.valid_to is not None:
            bp.valid_to = data.valid_to
        if data.is_active is not None:
            bp.is_active = data.is_active

        self.repo.update(bp)

        after_state = {
            "calendar_type": bp.calendar_type.value,
            "min_coverage_default": bp.min_coverage_default,
            "is_active": bp.is_active,
        }
        self.audit_repo.log_mutation(
            action="brand_process.update",
            entity_type="BrandProcess",
            entity_id=str(bp.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return bp

    def delete_brand_process(self, bp_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        bp = self.get_brand_process(bp_id)
        has_assignments = (
            self.session.scalar(
                select(func.count())
                .select_from(Assignment)
                .where(Assignment.brand_process_id == bp_id)
            )
            or 0
        )
        has_coverage_rules = (
            self.session.scalar(
                select(func.count())
                .select_from(CoverageRule)
                .where(CoverageRule.brand_process_id == bp_id)
            )
            or 0
        )
        if has_assignments > 0 or has_coverage_rules > 0:
            raise ConflictError(
                "Cannot delete brand process with active staff assignments or coverage rules. Set is_active=false to deactivate."
            )

        before_state = {
            "brand_id": str(bp.brand_id),
            "process_id": str(bp.process_id),
            "id": str(bp.id),
        }
        self.repo.delete(bp)

        self.audit_repo.log_mutation(
            action="brand_process.delete",
            entity_type="BrandProcess",
            entity_id=str(bp_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class AssignmentService:
    """Business service for staffing assignments."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AssignmentRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.bp_repo = BrandProcessRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_assignment(self, assignment_id: uuid.UUID) -> Assignment:
        assignment = self.repo.get_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment with id '{assignment_id}' not found")
        return assignment

    def list_assignments(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
        brand_process_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[Assignment], int]:
        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(Assignment.employee_id == employee_id)
            if brand_process_id is not None:
                stmt = stmt.where(Assignment.brand_process_id == brand_process_id)
            return stmt

        return self.repo.list(
            offset=offset,
            limit=limit,
            query_modifier=query_filter,
        )

    def create_assignment(
        self, data: AssignmentCreate, actor_id: uuid.UUID | None = None
    ) -> Assignment:
        if not self.emp_repo.get_by_id(data.employee_id):
            raise NotFoundError(f"Employee with id '{data.employee_id}' not found")
        if not self.bp_repo.get_by_id(data.brand_process_id):
            raise NotFoundError(f"BrandProcess with id '{data.brand_process_id}' not found")

        existing = self.repo.get_exact(data.employee_id, data.brand_process_id, data.valid_from)
        if existing:
            raise ConflictError(
                "An assignment for this employee and process starting on this date already exists"
            )

        assignment = Assignment(
            employee_id=data.employee_id,
            brand_process_id=data.brand_process_id,
            type=data.type,
            allocation_pct=data.allocation_pct,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self.repo.create(assignment)

        self.audit_repo.log_mutation(
            action="assignment.create",
            entity_type="Assignment",
            entity_id=str(assignment.id),
            user_id=actor_id,
            before=None,
            after={
                "employee_id": str(assignment.employee_id),
                "brand_process_id": str(assignment.brand_process_id),
                "type": assignment.type.value,
            },
        )
        return assignment

    def update_assignment(
        self,
        assignment_id: uuid.UUID,
        data: AssignmentUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Assignment:
        assignment = self.get_assignment(assignment_id)
        before_state = {
            "type": assignment.type.value,
            "allocation_pct": assignment.allocation_pct,
            "valid_from": str(assignment.valid_from) if assignment.valid_from else None,
            "valid_to": str(assignment.valid_to) if assignment.valid_to else None,
        }

        if data.type is not None:
            assignment.type = data.type
        if data.allocation_pct is not None:
            assignment.allocation_pct = data.allocation_pct
        if data.valid_from is not None:
            assignment.valid_from = data.valid_from
        if data.valid_to is not None:
            assignment.valid_to = data.valid_to

        self.repo.update(assignment)

        after_state = {
            "type": assignment.type.value,
            "allocation_pct": assignment.allocation_pct,
            "valid_from": str(assignment.valid_from) if assignment.valid_from else None,
            "valid_to": str(assignment.valid_to) if assignment.valid_to else None,
        }
        self.audit_repo.log_mutation(
            action="assignment.update",
            entity_type="Assignment",
            entity_id=str(assignment.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return assignment

    def delete_assignment(
        self, assignment_id: uuid.UUID, actor_id: uuid.UUID | None = None
    ) -> None:
        assignment = self.get_assignment(assignment_id)
        before_state = {
            "employee_id": str(assignment.employee_id),
            "brand_process_id": str(assignment.brand_process_id),
            "id": str(assignment.id),
        }
        self.repo.delete(assignment)

        self.audit_repo.log_mutation(
            action="assignment.delete",
            entity_type="Assignment",
            entity_id=str(assignment_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )
