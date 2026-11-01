"""SQLAlchemy 2.0 repositories for master data entities and audit logs."""

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.auth import AuditLog
from app.models.core import Assignment, Brand, BrandProcess, Employee, Pod, Process
from app.repositories.base import BaseRepository


class PodRepository(BaseRepository[Pod]):
    """Data access repository for Pod entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Pod, session)

    def get_by_name(self, name: str) -> Pod | None:
        stmt = select(Pod).where(Pod.name == name)
        return self.session.scalars(stmt).first()

    def get_with_details(self, pod_id: uuid.UUID) -> Pod | None:
        stmt = (
            select(Pod)
            .where(Pod.id == pod_id)
            .options(selectinload(Pod.members), selectinload(Pod.brands))
        )
        return self.session.scalars(stmt).first()


class EmployeeRepository(BaseRepository[Employee]):
    """Data access repository for Employee entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Employee, session)

    def get_by_code(self, code: str) -> Employee | None:
        stmt = select(Employee).where(Employee.code == code)
        return self.session.scalars(stmt).first()

    def get_by_email(self, email: str) -> Employee | None:
        stmt = select(Employee).where(Employee.email == email)
        return self.session.scalars(stmt).first()

    def list_by_pod(self, pod_id: uuid.UUID, is_active: bool | None = None) -> Sequence[Employee]:
        stmt = select(Employee).where(Employee.pod_id == pod_id)
        if is_active is not None:
            stmt = stmt.where(Employee.is_active == is_active)
        return self.session.scalars(stmt).all()

    def list_floaters(self, is_active: bool = True) -> Sequence[Employee]:
        stmt = select(Employee).where(
            Employee.is_floater.is_(True), Employee.is_active == is_active
        )
        return self.session.scalars(stmt).all()


class ProcessRepository(BaseRepository[Process]):
    """Data access repository for Process entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Process, session)

    def get_by_code(self, code: str) -> Process | None:
        stmt = select(Process).where(Process.code == code)
        return self.session.scalars(stmt).first()

    def get_by_name(self, name: str) -> Process | None:
        stmt = select(Process).where(Process.name == name)
        return self.session.scalars(stmt).first()


class BrandRepository(BaseRepository[Brand]):
    """Data access repository for Brand entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Brand, session)

    def get_by_code(self, code: str) -> Brand | None:
        stmt = select(Brand).where(Brand.code == code)
        return self.session.scalars(stmt).first()

    def get_by_name(self, name: str) -> Brand | None:
        stmt = select(Brand).where(Brand.name == name)
        return self.session.scalars(stmt).first()

    def list_by_pod(self, pod_id: uuid.UUID, is_active: bool | None = None) -> Sequence[Brand]:
        stmt = select(Brand).where(Brand.pod_id == pod_id)
        if is_active is not None:
            stmt = stmt.where(Brand.is_active == is_active)
        return self.session.scalars(stmt).all()


class BrandProcessRepository(BaseRepository[BrandProcess]):
    """Data access repository for BrandProcess entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(BrandProcess, session)

    def get_by_brand_and_process(
        self, brand_id: uuid.UUID, process_id: uuid.UUID
    ) -> BrandProcess | None:
        stmt = select(BrandProcess).where(
            BrandProcess.brand_id == brand_id,
            BrandProcess.process_id == process_id,
        )
        return self.session.scalars(stmt).first()

    def list_by_brand(
        self, brand_id: uuid.UUID, is_active: bool | None = None
    ) -> Sequence[BrandProcess]:
        stmt = select(BrandProcess).where(BrandProcess.brand_id == brand_id)
        if is_active is not None:
            stmt = stmt.where(BrandProcess.is_active == is_active)
        return self.session.scalars(stmt).all()


class AssignmentRepository(BaseRepository[Assignment]):
    """Data access repository for Employee-BrandProcess assignments."""

    def __init__(self, session: Session) -> None:
        super().__init__(Assignment, session)

    def get_exact(
        self,
        employee_id: uuid.UUID,
        brand_process_id: uuid.UUID,
        valid_from: date | None,
    ) -> Assignment | None:
        stmt = select(Assignment).where(
            Assignment.employee_id == employee_id,
            Assignment.brand_process_id == brand_process_id,
            Assignment.valid_from == valid_from,
        )
        return self.session.scalars(stmt).first()

    def list_by_employee(self, employee_id: uuid.UUID) -> Sequence[Assignment]:
        stmt = select(Assignment).where(Assignment.employee_id == employee_id)
        return self.session.scalars(stmt).all()

    def list_by_brand_process(self, brand_process_id: uuid.UUID) -> Sequence[Assignment]:
        stmt = select(Assignment).where(Assignment.brand_process_id == brand_process_id)
        return self.session.scalars(stmt).all()


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for recording and querying immutable audit trails."""

    def __init__(self, session: Session) -> None:
        super().__init__(AuditLog, session)

    def log_mutation(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: uuid.UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create and flush an audit log entry."""
        audit_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            before=before,
            after=after,
        )
        self.session.add(audit_entry)
        self.session.flush()
        return audit_entry
