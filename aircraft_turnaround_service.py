
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.constants import (
    AircraftTurnaroundStatus,
    TurnaroundMilestone,
    GroundStaffStatus,
)
from models.airport import Airport
from models.terminal import Terminal
from models.flight import Flight
from models.ground_staff import GroundStaff
from repositories.aircraft_turnaround_repository import AircraftTurnaroundRepository


MILESTONE_FIELDS = {
    TurnaroundMilestone.PASSENGERS_DISEMBARKED: "passengers_disembarked_at",
    TurnaroundMilestone.BAGGAGE_UNLOADED: "baggage_unloaded_at",
    TurnaroundMilestone.CLEANING_COMPLETED: "cleaning_completed_at",
    TurnaroundMilestone.CATERING_COMPLETED: "catering_completed_at",
    TurnaroundMilestone.REFUELLING_COMPLETED: "refuelling_completed_at",
    TurnaroundMilestone.BAGGAGE_LOADED: "baggage_loaded_at",
    TurnaroundMilestone.BOARDING_COMPLETED: "boarding_completed_at",
    TurnaroundMilestone.CHOCKS_OFF: "chocks_off_at",
}


def to_uuid(value):
    """Normalize UUID strings and UUID objects."""
    if value is None:
        return None

    if isinstance(value, uuid.UUID):
        return value

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=422, detail="Invalid UUID value")


def validate_references(
    db: Session,
    airport_id,
    terminal_id=None,
    flight_id=None,
    supervisor_id=None,
):
    airport_id = to_uuid(airport_id)
    terminal_id = to_uuid(terminal_id)
    flight_id = to_uuid(flight_id)
    supervisor_id = to_uuid(supervisor_id)

    airport = db.query(Airport).filter(Airport.id == airport_id).first()

    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")

    if terminal_id is not None:
        terminal = (
            db.query(Terminal)
            .filter(Terminal.id == terminal_id)
            .first()
        )

        if not terminal:
            raise HTTPException(status_code=404, detail="Terminal not found")

        if to_uuid(terminal.airport_id) != airport_id:
            raise HTTPException(
                status_code=400,
                detail="Terminal does not belong to this airport",
            )

    if flight_id is not None:
        flight = db.query(Flight).filter(Flight.id == flight_id).first()

        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found")

    if supervisor_id is not None:
        supervisor = (
            db.query(GroundStaff)
            .filter(GroundStaff.id == supervisor_id)
            .first()
        )

        if not supervisor:
            raise HTTPException(
                status_code=404,
                detail="Ground staff supervisor not found",
            )

        if supervisor.status != GroundStaffStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Supervisor is not active",
            )

        if to_uuid(supervisor.airport_id) != airport_id:
            raise HTTPException(
                status_code=400,
                detail="Supervisor does not belong to this airport",
            )


def create_turnaround(db: Session, data: dict, current_user):
    if AircraftTurnaroundRepository.get_by_number(
        db, data["turnaround_number"]
    ):
        raise HTTPException(
            status_code=409,
            detail="Turnaround number already exists",
        )

    if data["scheduled_departure"] <= data["scheduled_arrival"]:
        raise HTTPException(
            status_code=400,
            detail="Scheduled departure must be after scheduled arrival",
        )

    data = data.copy()

    data["airport_id"] = to_uuid(data["airport_id"])
    data["terminal_id"] = to_uuid(data.get("terminal_id"))
    data["flight_id"] = to_uuid(data.get("flight_id"))
    data["supervisor_id"] = to_uuid(data.get("supervisor_id"))

    validate_references(
        db,
        airport_id=data["airport_id"],
        terminal_id=data.get("terminal_id"),
        flight_id=data.get("flight_id"),
        supervisor_id=data.get("supervisor_id"),
    )

    data["created_by"] = current_user.id

    return AircraftTurnaroundRepository.create(db, data)


def get_turnaround(db: Session, turnaround_id):
    turnaround_id = to_uuid(turnaround_id)

    turnaround = AircraftTurnaroundRepository.get_by_id(
        db, turnaround_id
    )

    if not turnaround:
        raise HTTPException(
            status_code=404,
            detail="Aircraft turnaround not found",
        )

    return turnaround


def list_turnarounds(
    db: Session,
    airport_id=None,
    flight_id=None,
    status=None,
    page=1,
    page_size=20,
):
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination values",
        )

    if airport_id is not None:
        airport_id = to_uuid(airport_id)

    if flight_id is not None:
        flight_id = to_uuid(flight_id)

    total, items = AircraftTurnaroundRepository.list_turnarounds(
        db,
        airport_id=airport_id,
        flight_id=flight_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def update_turnaround(db: Session, turnaround_id, data: dict):
    turnaround = get_turnaround(db, turnaround_id)

    if turnaround.status in (
        AircraftTurnaroundStatus.COMPLETED,
        AircraftTurnaroundStatus.CANCELLED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Completed or cancelled turnarounds cannot be updated",
        )

    updates = {
        key: value
        for key, value in data.items()
        if value is not None
    }

    arrival = updates.get(
        "scheduled_arrival",
        turnaround.scheduled_arrival,
    )
    departure = updates.get(
        "scheduled_departure",
        turnaround.scheduled_departure,
    )

    if departure <= arrival:
        raise HTTPException(
            status_code=400,
            detail="Scheduled departure must be after scheduled arrival",
        )

    airport_id = to_uuid(turnaround.airport_id)

    terminal_id = to_uuid(
        updates.get("terminal_id", turnaround.terminal_id)
    )
    supervisor_id = to_uuid(
        updates.get("supervisor_id", turnaround.supervisor_id)
    )

    validate_references(
        db,
        airport_id=airport_id,
        terminal_id=terminal_id,
        supervisor_id=supervisor_id,
    )

    for key, value in updates.items():
        if key in ("terminal_id", "supervisor_id"):
            value = to_uuid(value)

        setattr(turnaround, key, value)

    db.commit()
    db.refresh(turnaround)

    return turnaround


def update_turnaround_status(db: Session, turnaround_id, new_status):
    turnaround = get_turnaround(db, turnaround_id)
    current = turnaround.status

    allowed = {
        AircraftTurnaroundStatus.SCHEDULED: {
            AircraftTurnaroundStatus.IN_PROGRESS,
            AircraftTurnaroundStatus.DELAYED,
            AircraftTurnaroundStatus.CANCELLED,
        },
        AircraftTurnaroundStatus.IN_PROGRESS: {
            AircraftTurnaroundStatus.DELAYED,
            AircraftTurnaroundStatus.COMPLETED,
            AircraftTurnaroundStatus.CANCELLED,
        },
        AircraftTurnaroundStatus.DELAYED: {
            AircraftTurnaroundStatus.IN_PROGRESS,
            AircraftTurnaroundStatus.CANCELLED,
        },
        AircraftTurnaroundStatus.COMPLETED: set(),
        AircraftTurnaroundStatus.CANCELLED: set(),
    }

    if new_status not in allowed[current]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change turnaround status from "
                f"{current.value} to {new_status.value}"
            ),
        )

    if (
        new_status == AircraftTurnaroundStatus.COMPLETED
        and not turnaround.actual_departure
    ):
        raise HTTPException(
            status_code=400,
            detail="Record actual departure before completing turnaround",
        )

    if (
        new_status == AircraftTurnaroundStatus.IN_PROGRESS
        and not turnaround.actual_arrival
    ):
        turnaround.actual_arrival = datetime.now(timezone.utc)

    turnaround.status = new_status

    db.commit()
    db.refresh(turnaround)

    return turnaround


def record_milestone(
    db: Session,
    turnaround_id,
    milestone,
    completed_at=None,
):
    turnaround = get_turnaround(db, turnaround_id)

    if turnaround.status != AircraftTurnaroundStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Milestones can only be recorded while turnaround is in progress",
        )

    field_name = MILESTONE_FIELDS.get(milestone)

    if not field_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid turnaround milestone",
        )

    if getattr(turnaround, field_name):
        raise HTTPException(
            status_code=409,
            detail="This milestone has already been recorded",
        )

    timestamp = completed_at or datetime.now(timezone.utc)

    if milestone == TurnaroundMilestone.CHOCKS_OFF:
        turnaround.actual_departure = timestamp

    setattr(turnaround, field_name, timestamp)

    db.commit()
    db.refresh(turnaround)

    return turnaround
