"""Common generic schemas for pagination and envelopes."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class PaginationParams(BaseModel):
    """Standard query parameters for pagination."""

    limit: int = Field(default=50, ge=1, le=200, description="Number of items to return")
    offset: int = Field(default=0, ge=0, description="Offset starting point")


class PaginatedResponse[T](BaseModel):
    """Standard pagination wrapper conforming to API_DOCUMENTATION.md §2."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(ge=0, description="Total matching items count")
    limit: int = Field(ge=1, description="Items per page")
    offset: int = Field(ge=0, description="Current offset")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: str | None = None


class EntityCreatedResponse(BaseModel):
    """Standard response after creating an entity."""

    id: str
    message: str = "Resource created successfully"
