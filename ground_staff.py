
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import (
    GroundStaffDepartment,
    GroundStaffShift,
    GroundStaffStatus,
)


class GroundStaffCreate(BaseModel):
    user_id: UUID
    employee_number: str = Field(min_length=3, max_length=30)
    department: GroundStaffDepartment
    designation: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=20)
    shift: GroundStaffShift
    airport_id: UUID
    terminal_id: UUID | None = None
    date_of_joining: date


class GroundStaffUpdate(BaseModel):
    employee_number: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
    )
    department: GroundStaffDepartment | None = None
    designation: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
    )
    shift: GroundStaffShift | None = None
    status: GroundStaffStatus | None = None
    airport_id: UUID | None = None
    terminal_id: UUID | None = None
    date_of_joining: date | None = None


class GroundStaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    employee_number: str
    department: GroundStaffDepartment
    designation: str
    phone: str
    shift: GroundStaffShift
    status: GroundStaffStatus
    airport_id: UUID
    terminal_id: UUID | None
    date_of_joining: date
    created_at: datetime
    updated_at: datetime


class GroundStaffListResponse(BaseModel):
    items: list[GroundStaffResponse]
    total: int
    page: int
    page_size: int
    pages: int
