import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    BaggageStatus,
    CheckInStatus,
    FlightStatus,
)
from models.baggage import Baggage
from models.checkin import CheckIn
from models.flight import Flight
from models.passenger import Passenger
from schemas.baggage import BaggageCreate
from repositories import baggage_repository


def create_baggage(db: Session, data: BaggageCreate):
    passenger = (
        db.query(Passenger)
        .filter(Passenger.id == data.passenger_id)
        .first()
    )

    if not passenger:
        raise HTTPException(
            status_code=404,
            detail="Passenger not found",
        )

    flight = (
        db.query(Flight)
        .filter(Flight.id == data.flight_id)
        .first()
    )

    if not flight:
        raise HTTPException(
            status_code=404,
            detail="Flight not found",
        )

    if flight.status in (
        FlightStatus.CANCELLED,
        FlightStatus.DEPARTED,
        FlightStatus.ARRIVED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Baggage registration is not available for this flight",
        )

    checkin = (
        db.query(CheckIn)
        .filter(CheckIn.id == data.checkin_id)
        .first()
    )

    if not checkin:
        raise HTTPException(
            status_code=404,
            detail="Check-in not found",
        )

    if checkin.status != CheckInStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Passenger must have a completed check-in",
        )

    if (
        checkin.passenger_id != data.passenger_id
        or checkin.flight_id != data.flight_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Check-in does not belong to this passenger and flight",
        )

    baggage_tag = f"BAG-{uuid.uuid4().hex[:16].upper()}"

    baggage = Baggage(
        baggage_tag=baggage_tag,
        passenger_id=data.passenger_id,
        flight_id=data.flight_id,
        checkin_id=data.checkin_id,
        baggage_type=data.baggage_type,
        weight_kg=data.weight_kg,
        status=BaggageStatus.REGISTERED,
    )

    try:
        baggage_repository.create_baggage(db, baggage)
        db.commit()
        db.refresh(baggage)
        return baggage

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Baggage registration conflict",
        )


def get_baggage(db: Session, baggage_id: uuid.UUID):
    baggage = baggage_repository.get_baggage_by_id(
        db,
        baggage_id,
    )

    if not baggage:
        raise HTTPException(
            status_code=404,
            detail="Baggage not found",
        )

    return baggage


def get_baggage_by_tag(db: Session, baggage_tag: str):
    baggage = baggage_repository.get_baggage_by_tag(
        db,
        baggage_tag,
    )

    if not baggage:
        raise HTTPException(
            status_code=404,
            detail="Baggage not found",
        )

    return baggage


def list_baggage(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    flight_id=None,
    passenger_id=None,
    checkin_id=None,
):
    return baggage_repository.list_baggage(
        db=db,
        skip=skip,
        limit=limit,
        flight_id=flight_id,
        passenger_id=passenger_id,
        checkin_id=checkin_id,
    )


def cancel_baggage(db: Session, baggage_id: uuid.UUID):
    baggage = get_baggage(db, baggage_id)

    if baggage.status == BaggageStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Baggage is already cancelled",
        )

    baggage.status = BaggageStatus.CANCELLED

    db.commit()
    db.refresh(baggage)

    return baggage