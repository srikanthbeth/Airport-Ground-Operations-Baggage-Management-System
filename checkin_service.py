from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    BoardingPassStatus,
    CheckInStatus,
    CounterStatus,
    FlightStatus,
    PassengerStatus,
)
from models.checkin import CheckIn
from repositories import (
    boarding_pass_repository,
    checkin_repository,
)
from services.boarding_pass_service import issue_boarding_pass
from models.passenger import Passenger
from models.flight import Flight
from models.checkin_counter import CheckInCounter

def create_checkin(db: Session, data):
    passenger = db.get(Passenger, data.passenger_id)
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    if passenger.status != PassengerStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Passenger is not active")

    from models.flight import Flight
    flight = db.get(Flight, data.flight_id)

    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    if flight.status in (
        FlightStatus.CANCELLED,
        FlightStatus.DEPARTED,
        FlightStatus.ARRIVED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Check-in is not available for this flight",
        )

    from models.checkin_counter import CheckInCounter
    counter = db.get(CheckInCounter, data.counter_id)

    if not counter:
        raise HTTPException(status_code=404, detail="Check-in counter not found")

    if counter.status != CounterStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Check-in counter is not active")

    if not flight.departure_terminal_id:
        raise HTTPException(
            status_code=400,
            detail="Flight has no departure terminal assigned",
        )

    if counter.terminal_id != flight.departure_terminal_id:
        raise HTTPException(
            status_code=400,
            detail="Check-in counter does not belong to the flight departure terminal",
        )

    existing = checkin_repository.get_checkin_by_passenger_and_flight(
        db, data.passenger_id, data.flight_id
    )

    if existing and existing.status == CheckInStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Passenger is already checked in for this flight",
        )

    occupied = checkin_repository.get_checkin_by_flight_and_seat(
        db, data.flight_id, data.seat_number
    )

    if occupied and occupied.status == CheckInStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Seat is already assigned on this flight",
        )

    try:
        if existing:
            existing.counter_id = data.counter_id
            existing.seat_number = data.seat_number
            existing.status = CheckInStatus.COMPLETED
            db.flush()
            checkin = existing
        else:
            checkin = CheckIn(
                passenger_id=data.passenger_id,
                flight_id=data.flight_id,
                counter_id=data.counter_id,
                seat_number=data.seat_number.strip().upper(),
                status=CheckInStatus.COMPLETED,
            )
            checkin_repository.create_checkin(db, checkin)

        boarding_pass = issue_boarding_pass(db, checkin.id)

        if boarding_pass.status == BoardingPassStatus.VOID:
            boarding_pass.status = BoardingPassStatus.ACTIVE

        db.commit()
        db.refresh(checkin)
        return checkin

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Passenger or seat has already been checked in",
        )


def get_checkin(db: Session, checkin_id: UUID):
    checkin = checkin_repository.get_checkin_by_id(db, checkin_id)

    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")

    return checkin


def get_checkins(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    flight_id: UUID | None = None,
    passenger_id: UUID | None = None,
):
    return checkin_repository.list_checkins(
        db,
        skip=skip,
        limit=limit,
        flight_id=flight_id,
        passenger_id=passenger_id,
    )


def cancel_checkin(db: Session, checkin_id: UUID):
    checkin = get_checkin(db, checkin_id)

    if checkin.status == CheckInStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Check-in is already cancelled",
        )

    checkin.status = CheckInStatus.CANCELLED

    boarding_pass = boarding_pass_repository.get_boarding_pass_by_checkin(
        db, checkin.id
    )

    if boarding_pass:
        boarding_pass.status = BoardingPassStatus.VOID

    db.commit()
    db.refresh(checkin)
    return checkin