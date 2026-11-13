from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    FlightStatus,
    GateStatus,
    CounterStatus,
    ResourceAssignmentStatus,
)
from models.flight import Flight
from models.gate import Gate
from models.checkin_counter import CheckInCounter
from models.resource_assignment import ResourceAssignment
from repositories.resource_assignment_repository import (
    ResourceAssignmentRepository,
)


class ResourceAssignmentService:

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
                "Cannot assign resources to a cancelled, departed or arrived flight",
            )

        return flight

    @staticmethod
    def assign_gate(db: Session, gate_id: UUID, flight_id: UUID):
        gate = db.get(Gate, gate_id)

        if not gate:
            raise HTTPException(404, "Gate not found")

        if gate.status != GateStatus.ACTIVE:
            raise HTTPException(400, "Gate is not active")

        flight = ResourceAssignmentService.get_flight(db, flight_id)

        if not flight.departure_terminal_id:
            raise HTTPException(
                400,
                "Flight must have a departure terminal before gate assignment",
            )

        if gate.terminal_id != flight.departure_terminal_id:
            raise HTTPException(
                400,
                "Gate must belong to the flight departure terminal",
            )

        if ResourceAssignmentRepository.get_active_for_gate(db, gate_id):
            raise HTTPException(409, "Gate is already assigned to another flight")

        if ResourceAssignmentRepository.get_active_for_flight_gate(
            db,
            flight_id,
        ):
            raise HTTPException(409, "Flight already has an active gate assignment")

        assignment = ResourceAssignment(
            flight_id=flight_id,
            gate_id=gate_id,
            status=ResourceAssignmentStatus.ACTIVE,
        )

        try:
            return ResourceAssignmentRepository.create(db, assignment)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Gate or flight already has an active assignment",
            )

    @staticmethod
    def assign_counter(db: Session, counter_id: UUID, flight_id: UUID):
        counter = db.get(CheckInCounter, counter_id)

        if not counter:
            raise HTTPException(404, "Check-in counter not found")

        if counter.status != CounterStatus.ACTIVE:
            raise HTTPException(400, "Check-in counter is not active")

        flight = ResourceAssignmentService.get_flight(db, flight_id)

        if not flight.departure_terminal_id:
            raise HTTPException(
                400,
                "Flight must have a departure terminal before counter assignment",
            )

        if counter.terminal_id != flight.departure_terminal_id:
            raise HTTPException(
                400,
                "Counter must belong to the flight departure terminal",
            )

        if ResourceAssignmentRepository.get_active_for_counter(
            db,
            counter_id,
        ):
            raise HTTPException(
                409,
                "Check-in counter is already assigned to another flight",
            )

        if ResourceAssignmentRepository.get_active_for_flight_counter(
            db,
            flight_id,
        ):
            raise HTTPException(
                409,
                "Flight already has an active check-in counter assignment",
            )

        assignment = ResourceAssignment(
            flight_id=flight_id,
            counter_id=counter_id,
            status=ResourceAssignmentStatus.ACTIVE,
        )

        try:
            return ResourceAssignmentRepository.create(db, assignment)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Counter or flight already has an active assignment",
            )

    @staticmethod
    def release(db: Session, assignment_id: UUID):
        assignment = db.get(ResourceAssignment, assignment_id)

        if not assignment:
            raise HTTPException(404, "Resource assignment not found")

        if assignment.status == ResourceAssignmentStatus.RELEASED:
            raise HTTPException(400, "Assignment has already been released")

        return ResourceAssignmentRepository.release(db, assignment)

    @staticmethod
    def gate_history(db: Session, gate_id: UUID, skip: int, limit: int):
        if not db.get(Gate, gate_id):
            raise HTTPException(404, "Gate not found")

        return ResourceAssignmentRepository.list_for_gate(
            db,
            gate_id,
            skip,
            limit,
        )

    @staticmethod
    def counter_history(
        db: Session,
        counter_id: UUID,
        skip: int,
        limit: int,
    ):
        if not db.get(CheckInCounter, counter_id):
            raise HTTPException(404, "Check-in counter not found")

        return ResourceAssignmentRepository.list_for_counter(
            db,
            counter_id,
            skip,
            limit,
        )