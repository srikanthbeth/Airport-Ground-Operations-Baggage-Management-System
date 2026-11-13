from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    FlightStatus,
    PassengerStatus,
)
from models.flight import Flight
from models.passenger import Passenger
from repositories.passenger_repository import PassengerRepository


class PassengerService:

    @staticmethod
    def validate_flight(db: Session, flight_id: UUID):
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
                "Passengers cannot be registered for this flight",
            )

        return flight

    @staticmethod
    def create(db: Session, data):
        PassengerService.validate_flight(db, data.flight_id)

        identification_number = data.identification_number.strip().upper()

        existing = PassengerRepository.get_by_identification(
            db,
            data.flight_id,
            data.identification_type,
            identification_number,
        )

        if existing:
            raise HTTPException(
                409,
                "Passenger with this identification already exists for this flight",
            )

        passenger = Passenger(
            **data.model_dump(exclude={"identification_number"}),
            identification_number=identification_number,
        )

        try:
            return PassengerRepository.create(db, passenger)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Passenger identification already exists for this flight",
            )

    @staticmethod
    def get(db: Session, passenger_id: UUID):
        passenger = PassengerRepository.get_by_id(db, passenger_id)

        if not passenger:
            raise HTTPException(404, "Passenger not found")

        return passenger

    @staticmethod
    def list(
        db: Session,
        skip: int,
        limit: int,
        search: str | None,
        flight_id: UUID | None,
        status: PassengerStatus | None,
    ):
        return PassengerRepository.list(
            db,
            skip,
            limit,
            search,
            flight_id,
            status,
        )

    @staticmethod
    def update(db: Session, passenger_id: UUID, data):
        passenger = PassengerService.get(db, passenger_id)

        if passenger.status == PassengerStatus.CANCELLED:
            raise HTTPException(
                400,
                "Cancelled passenger details cannot be updated",
            )

        updates = data.model_dump(exclude_unset=True)

        if "identification_number" in updates and updates["identification_number"]:
            updates["identification_number"] = (
                updates["identification_number"].strip().upper()
            )

        if "date_of_birth" in updates and updates["date_of_birth"] is None:
            raise HTTPException(400, "Date of birth cannot be null")

        if "full_name" in updates and updates["full_name"] is None:
            raise HTTPException(400, "Full name cannot be null")

        if "phone" in updates and updates["phone"] is None:
            raise HTTPException(400, "Phone cannot be null")

        if "nationality" in updates and updates["nationality"] is None:
            raise HTTPException(400, "Nationality cannot be null")

        if (
            "identification_type" in updates
            and updates["identification_type"] is None
        ):
            raise HTTPException(400, "Identification type cannot be null")

        if (
            "identification_number" in updates
            and updates["identification_number"] is None
        ):
            raise HTTPException(400, "Identification number cannot be null")

        new_type = updates.get(
            "identification_type",
            passenger.identification_type,
        )
        new_number = updates.get(
            "identification_number",
            passenger.identification_number,
        )

        duplicate = PassengerRepository.get_by_identification(
            db,
            passenger.flight_id,
            new_type,
            new_number,
        )

        if duplicate and duplicate.id != passenger.id:
            raise HTTPException(
                409,
                "Another passenger already uses this identification for this flight",
            )

        try:
            return PassengerRepository.update(db, passenger, updates)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Passenger identification already exists")

    @staticmethod
    def cancel(db: Session, passenger_id: UUID):
        passenger = PassengerService.get(db, passenger_id)

        if passenger.status == PassengerStatus.CANCELLED:
            raise HTTPException(400, "Passenger is already cancelled")

        return PassengerRepository.cancel(db, passenger)

    @staticmethod
    def history(
        db: Session,
        identification_type,
        identification_number: str,
    ):
        return PassengerRepository.history(
            db,
            identification_type,
            identification_number.strip().upper(),
        )