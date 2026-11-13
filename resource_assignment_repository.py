from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.resource_assignment import ResourceAssignment
from core.constants import ResourceAssignmentStatus


class ResourceAssignmentRepository:

    @staticmethod
    def create(db: Session, assignment: ResourceAssignment):
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def get(db: Session, assignment_id: UUID):
        return db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.id == assignment_id
            )
        )

    @staticmethod
    def get_active_for_gate(db: Session, gate_id: UUID):
        return db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.gate_id == gate_id,
                ResourceAssignment.status == ResourceAssignmentStatus.ACTIVE,
            )
        )

    @staticmethod
    def get_active_for_counter(db: Session, counter_id: UUID):
        return db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.counter_id == counter_id,
                ResourceAssignment.status == ResourceAssignmentStatus.ACTIVE,
            )
        )

    @staticmethod
    def get_active_for_flight_gate(db: Session, flight_id: UUID):
        return db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.flight_id == flight_id,
                ResourceAssignment.gate_id.is_not(None),
                ResourceAssignment.status == ResourceAssignmentStatus.ACTIVE,
            )
        )

    @staticmethod
    def get_active_for_flight_counter(db: Session, flight_id: UUID):
        return db.scalar(
            select(ResourceAssignment).where(
                ResourceAssignment.flight_id == flight_id,
                ResourceAssignment.counter_id.is_not(None),
                ResourceAssignment.status == ResourceAssignmentStatus.ACTIVE,
            )
        )

    @staticmethod
    def list_for_gate(
        db: Session,
        gate_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ):
        query = (
            select(ResourceAssignment)
            .where(ResourceAssignment.gate_id == gate_id)
            .order_by(ResourceAssignment.assigned_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(query).all())

    @staticmethod
    def list_for_counter(
        db: Session,
        counter_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ):
        query = (
            select(ResourceAssignment)
            .where(ResourceAssignment.counter_id == counter_id)
            .order_by(ResourceAssignment.assigned_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(query).all())

    @staticmethod
    def release(db: Session, assignment: ResourceAssignment):
        assignment.status = ResourceAssignmentStatus.RELEASED
        from datetime import datetime, timezone
        assignment.released_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(assignment)
        return assignment