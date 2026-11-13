from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.operational_incident import OperationalIncident
from models.airport import Airport
from models.flight import Flight
from models.user import User

from repositories.operational_incident_repository import (
    OperationalIncidentRepository,
)

from schemas.operational_incident import (
    OperationalIncidentCreate,
    OperationalIncidentUpdate,
    IncidentAssignment,
    IncidentStatusUpdate,
)

from core.constants import IncidentStatus


class OperationalIncidentService:

    ALLOWED_TRANSITIONS = {
        IncidentStatus.OPEN.value: {
            IncidentStatus.ACKNOWLEDGED.value,
            IncidentStatus.IN_PROGRESS.value,
            IncidentStatus.REJECTED.value,
        },
        IncidentStatus.ACKNOWLEDGED.value: {
            IncidentStatus.IN_PROGRESS.value,
            IncidentStatus.REJECTED.value,
        },
        IncidentStatus.IN_PROGRESS.value: {
            IncidentStatus.RESOLVED.value,
            IncidentStatus.REJECTED.value,
        },
        IncidentStatus.RESOLVED.value: {
            IncidentStatus.CLOSED.value,
            IncidentStatus.IN_PROGRESS.value,
        },
        IncidentStatus.CLOSED.value: set(),
        IncidentStatus.REJECTED.value: set(),
    }

    @staticmethod
    def _get_incident(db: Session, incident_id: UUID):
        incident = OperationalIncidentRepository.get_by_id(db, incident_id)

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operational incident not found",
            )

        return incident

    @staticmethod
    def _validate_airport(db: Session, airport_id: UUID):
        airport = db.query(Airport).filter(
            Airport.id == airport_id
        ).first()

        if not airport:
            raise HTTPException(
                status_code=404,
                detail="Airport not found",
            )

        return airport

    @staticmethod
    def _validate_flight(db: Session, flight_id: UUID | None):
        if flight_id is None:
            return None

        flight = db.query(Flight).filter(
            Flight.id == flight_id
        ).first()

        if not flight:
            raise HTTPException(
                status_code=404,
                detail="Flight not found",
            )

        return flight

    @staticmethod
    def create(
        db: Session,
        data: OperationalIncidentCreate,
        current_user: User,
    ):
        if OperationalIncidentRepository.get_by_number(
            db, data.incident_number
        ):
            raise HTTPException(
                status_code=409,
                detail="Incident number already exists",
            )

        OperationalIncidentService._validate_airport(
            db, data.airport_id
        )

        OperationalIncidentService._validate_flight(
            db, data.flight_id
        )

        incident = OperationalIncident(
            incident_number=data.incident_number,
            title=data.title,
            description=data.description,
            category=data.category.value,
            severity=data.severity.value,
            status=IncidentStatus.OPEN.value,
            airport_id=data.airport_id,
            flight_id=data.flight_id,
            reported_by_id=current_user.id,
            location=data.location,
            occurred_at=data.occurred_at,
        )

        return OperationalIncidentRepository.create(db, incident)

    @staticmethod
    def get(db: Session, incident_id: UUID):
        return OperationalIncidentService._get_incident(
            db, incident_id
        )

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        airport_id: UUID | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ):
        return OperationalIncidentRepository.list(
            db=db,
            skip=skip,
            limit=limit,
            airport_id=airport_id,
            category=category,
            severity=severity,
            status=status,
        )

    @staticmethod
    def update(
        db: Session,
        incident_id: UUID,
        data: OperationalIncidentUpdate,
    ):
        incident = OperationalIncidentService._get_incident(
            db, incident_id
        )

        if incident.status in {
            IncidentStatus.CLOSED.value,
            IncidentStatus.REJECTED.value,
        }:
            raise HTTPException(
                status_code=409,
                detail="Closed or rejected incidents cannot be edited",
            )

        values = data.model_dump(exclude_unset=True)

        if "flight_id" in values:
            OperationalIncidentService._validate_flight(
                db, values["flight_id"]
            )

        for key, value in values.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(incident, key, value)

        return OperationalIncidentRepository.save(db, incident)

    @staticmethod
    def assign(
        db: Session,
        incident_id: UUID,
        data: IncidentAssignment,
    ):
        incident = OperationalIncidentService._get_incident(
            db, incident_id
        )

        if incident.status in {
            IncidentStatus.CLOSED.value,
            IncidentStatus.REJECTED.value,
        }:
            raise HTTPException(
                status_code=409,
                detail="Cannot assign a closed or rejected incident",
            )

        user = db.query(User).filter(
            User.id == data.assigned_to_id,
            User.is_active.is_(True),
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Active assigned staff member not found",
            )

        incident.assigned_to_id = user.id

        return OperationalIncidentRepository.save(db, incident)

    @staticmethod
    def update_status(
        db: Session,
        incident_id: UUID,
        data: IncidentStatusUpdate,
    ):
        incident = OperationalIncidentService._get_incident(
            db, incident_id
        )

        new_status = data.status.value
        old_status = incident.status

        allowed = OperationalIncidentService.ALLOWED_TRANSITIONS.get(
            old_status, set()
        )

        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid incident status transition: {old_status} to {new_status}",
            )

        now = datetime.now(timezone.utc)

        if new_status == IncidentStatus.ACKNOWLEDGED.value:
            incident.acknowledged_at = now

        if new_status == IncidentStatus.RESOLVED.value:
            incident.resolved_at = now
            incident.resolution_notes = data.resolution_notes.strip()

        if new_status == IncidentStatus.CLOSED.value:
            incident.closed_at = now

        if new_status == IncidentStatus.IN_PROGRESS.value:
            incident.resolved_at = None
            incident.closed_at = None

        incident.status = new_status

        return OperationalIncidentRepository.save(db, incident)

    @staticmethod
    def delete(db: Session, incident_id: UUID):
        incident = OperationalIncidentService._get_incident(
            db, incident_id
        )

        if incident.status not in {
            IncidentStatus.CLOSED.value,
            IncidentStatus.REJECTED.value,
        }:
            raise HTTPException(
                status_code=409,
                detail="Only closed or rejected incidents can be deleted",
            )

        OperationalIncidentRepository.delete(db, incident)
        return {"message": "Operational incident deleted successfully"}