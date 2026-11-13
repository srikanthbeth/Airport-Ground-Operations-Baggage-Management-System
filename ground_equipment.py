import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.constants import GroundEquipmentType, GroundEquipmentStatus


class GroundEquipmentCreate(BaseModel):
    equipment_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    equipment_type: GroundEquipmentType

    airport_id: uuid.UUID
    assigned_flight_id: Optional[uuid.UUID] = None

    manufacturer: Optional[str] = Field(default=None, max_length=100)
    model_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)

    status: GroundEquipmentStatus = GroundEquipmentStatus.AVAILABLE

    last_maintenance_at: Optional[datetime] = None
    next_maintenance_at: Optional[datetime] = None

    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_maintenance_dates(self):
        if (
            self.last_maintenance_at
            and self.next_maintenance_at
            and self.next_maintenance_at < self.last_maintenance_at
        ):
            raise ValueError(
                "Next maintenance date cannot be earlier than last maintenance date"
            )
        return self


class GroundEquipmentUpdate(BaseModel):
    equipment_code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    equipment_type: Optional[GroundEquipmentType] = None

    airport_id: Optional[uuid.UUID] = None
    assigned_flight_id: Optional[uuid.UUID] = None

    manufacturer: Optional[str] = Field(default=None, max_length=100)
    model_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)

    last_maintenance_at: Optional[datetime] = None
    next_maintenance_at: Optional[datetime] = None

    notes: Optional[str] = None


class GroundEquipmentStatusUpdate(BaseModel):
    status: GroundEquipmentStatus


class GroundEquipmentUsageCreate(BaseModel):
    flight_id: Optional[uuid.UUID] = None
    started_at: datetime
    ended_at: datetime
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_usage_period(self):
        if self.ended_at <= self.started_at:
            raise ValueError("Usage end time must be after start time")
        return self


class GroundEquipmentUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_id: uuid.UUID
    flight_id: Optional[uuid.UUID]
    used_by: uuid.UUID
    started_at: datetime
    ended_at: datetime
    notes: Optional[str]
    created_at: datetime


class GroundEquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_code: str
    name: str
    equipment_type: GroundEquipmentType

    airport_id: uuid.UUID
    assigned_flight_id: Optional[uuid.UUID]

    manufacturer: Optional[str]
    model_number: Optional[str]
    serial_number: Optional[str]

    status: GroundEquipmentStatus

    last_maintenance_at: Optional[datetime]
    next_maintenance_at: Optional[datetime]
    last_used_at: Optional[datetime]

    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GroundEquipmentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GroundEquipmentResponse]