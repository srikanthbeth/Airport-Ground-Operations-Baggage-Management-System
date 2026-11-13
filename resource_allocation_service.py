
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.constants import (
    AllocationResourceType,
    FlightStatus,
    GateStatus,
    CounterStatus,
    GroundStaffStatus,
    GroundEquipmentStatus,
    ResourceAllocationStatus,
)
from models.flight import Flight
from models.gate import Gate
from models.checkin_counter import CheckInCounter
from models.ground_staff import GroundStaff
from models.ground_equipment import GroundEquipment
from models.resource_allocation import ResourceAllocation
from repositories.resource_allocation_repository import (
    ResourceAllocationRepository,
)


class ResourceAllocationService:

    RESOURCE_COLUMNS = {
        AllocationResourceType.GATE: (
            "gate_id",
            Gate,
            GateStatus.ACTIVE,
        ),
        AllocationResourceType.COUNTER: (
            "counter_id",
            CheckInCounter,
            CounterStatus.ACTIVE,
        ),
        AllocationResourceType.GROUND_STAFF: (
            "ground_staff_id",
            GroundStaff,
            GroundStaffStatus.ACTIVE,
        ),
        AllocationResourceType.GROUND_EQUIPMENT: (
            "equipment_id",
            GroundEquipment,
            GroundEquipmentStatus.AVAILABLE,
        ),
    }

    @staticmethod
    def get_flight(db: Session, flight_id: UUID):
        flight = db.get(Flight, flight_id)

        if not flight:
            raise HTTPException(404, "Flight not found")

        if flight.status in (
            FlightStatus.CANCELLED,
            FlightStatus.DEPARTED,
            FlightStatus.ARRIVED,
        ):
            raise HTTPException(
                400,
                "Cannot allocate resources to a cancelled, departed or arrived flight",
            )

        return flight

    @staticmethod
    def get_resource(db: Session, resource_type, resource_id):
        if resource_type not in ResourceAllocationService.RESOURCE_COLUMNS:
            raise HTTPException(422, "Unsupported resource type")

        column_name, model, active_status = (
            ResourceAllocationService.RESOURCE_COLUMNS[resource_type]
        )

        resource = db.get(model, resource_id)

        if not resource:
            raise HTTPException(404, f"{resource_type.value} resource not found")

        if resource.status != active_status:
            raise HTTPException(
                400,
                f"{resource_type.value} resource is not available",
            )

        return column_name, resource

    @staticmethod
    def validate_resource_location(flight, resource_type, resource):
        if resource_type in (
            AllocationResourceType.GATE,
            AllocationResourceType.COUNTER,
        ):
            if not flight.departure_terminal_id:
                raise HTTPException(
                    400,
                    "Flight must have a departure terminal",
                )

            if resource.terminal_id != flight.departure_terminal_id:
                raise HTTPException(
                    400,
                    "Resource must belong to the flight departure terminal",
                )

        elif resource_type == AllocationResourceType.GROUND_STAFF:
            if resource.airport_id != flight.origin_airport_id:
                raise HTTPException(
                    400,
                    "Ground staff must belong to the flight origin airport",
                )

        elif resource_type == AllocationResourceType.GROUND_EQUIPMENT:
            if resource.airport_id != flight.origin_airport_id:
                raise HTTPException(
                    400,
                    "Equipment must belong to the flight origin airport",
                )

    @staticmethod
    def create(db, data, current_user):
        flight = ResourceAllocationService.get_flight(
            db,
            data.flight_id,
        )

        column_name, resource = ResourceAllocationService.get_resource(
            db,
            data.resource_type,
            data.resource_id,
        )

        ResourceAllocationService.validate_resource_location(
            flight,
            data.resource_type,
            resource,
        )

        resource_column = getattr(ResourceAllocation, column_name)

        if ResourceAllocationRepository.has_overlap(
            db,
            resource_column,
            data.resource_id,
            data.starts_at,
            data.ends_at,
        ):
            raise HTTPException(
                409,
                "Resource already has an overlapping allocation",
            )

        allocation = ResourceAllocation(
            flight_id=data.flight_id,
            resource_type=data.resource_type,
            **{column_name: data.resource_id},
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            notes=data.notes,
            assigned_by=current_user.id,
            status=ResourceAllocationStatus.SCHEDULED,
        )

        return ResourceAllocationRepository.create(db, allocation)

    @staticmethod
    def get(db, allocation_id):
        allocation = ResourceAllocationRepository.get(
            db,
            allocation_id,
        )

        if not allocation:
            raise HTTPException(404, "Resource allocation not found")

        return allocation

    @staticmethod
    def list(
        db,
        skip=0,
        limit=100,
        flight_id=None,
        resource_type=None,
        status=None,
        starts_from=None,
        starts_to=None,
    ):
        return ResourceAllocationRepository.list(
            db,
            skip,
            limit,
            flight_id,
            resource_type,
            status,
            starts_from,
            starts_to,
        )

    @staticmethod
    def update(db, allocation_id, data):
        allocation = ResourceAllocationService.get(db, allocation_id)

        if allocation.status not in (
            ResourceAllocationStatus.SCHEDULED,
            ResourceAllocationStatus.ACTIVE,
        ):
            raise HTTPException(
                400,
                "Only scheduled or active allocations can be updated",
            )

        new_start = data.starts_at or allocation.starts_at
        new_end = data.ends_at or allocation.ends_at

        if new_end <= new_start:
            raise HTTPException(
                422,
                "ends_at must be later than starts_at",
            )

        column_name = ResourceAllocationService.RESOURCE_COLUMNS[
            allocation.resource_type
        ][0]

        resource_id = getattr(allocation, column_name)

        if ResourceAllocationRepository.has_overlap(
            db,
            getattr(ResourceAllocation, column_name),
            resource_id,
            new_start,
            new_end,
            exclude_id=allocation.id,
        ):
            raise HTTPException(
                409,
                "Updated schedule overlaps another allocation",
            )

        allocation.starts_at = new_start
        allocation.ends_at = new_end

        if "notes" in data.model_fields_set:
            allocation.notes = data.notes

        return ResourceAllocationRepository.save(db, allocation)

    @staticmethod
    def change_status(db, allocation_id, new_status):
        allocation = ResourceAllocationService.get(db, allocation_id)

        if allocation.status in (
            ResourceAllocationStatus.COMPLETED,
            ResourceAllocationStatus.CANCELLED,
        ):
            raise HTTPException(
                400,
                "Allocation is already completed or cancelled",
            )

        if new_status == ResourceAllocationStatus.ACTIVE:
            if allocation.status != ResourceAllocationStatus.SCHEDULED:
                raise HTTPException(
                    400,
                    "Only scheduled allocations can be activated",
                )

        allocation.status = new_status

        return ResourceAllocationRepository.save(db, allocation)

    @staticmethod
    def cancel(db, allocation_id):
        return ResourceAllocationService.change_status(
            db,
            allocation_id,
            ResourceAllocationStatus.CANCELLED,
        )

    @staticmethod
    def activate(db, allocation_id):
        return ResourceAllocationService.change_status(
            db,
            allocation_id,
            ResourceAllocationStatus.ACTIVE,
        )

    @staticmethod
    def complete(db, allocation_id):
        return ResourceAllocationService.change_status(
            db,
            allocation_id,
            ResourceAllocationStatus.COMPLETED,
        )
