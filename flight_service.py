from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import FlightStatus, TerminalStatus
from models.airport import Airport
from models.flight import Flight
from models.terminal import Terminal
from repositories.flight_repository import FlightRepository


class FlightService:

    @staticmethod
    def validate_airport(db: Session, airport_id: UUID):
        airport = db.get(Airport, airport_id)

        if not airport or not airport.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Airport not found or inactive",
            )

        return airport

    @staticmethod
    def validate_terminal(
        db: Session,
        terminal_id: UUID | None,
        airport_id: UUID,
    ):
        if terminal_id is None:
            return None

        terminal = db.get(Terminal, terminal_id)

        if not terminal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Terminal not found",
            )

        if terminal.airport_id != airport_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Terminal does not belong to the selected airport",
            )

        if terminal.status != TerminalStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected terminal is not active",
            )

        return terminal

    @classmethod
    def validate_locations(
        cls,
        db: Session,
        origin_airport_id: UUID,
        destination_airport_id: UUID,
        departure_terminal_id: UUID | None,
        arrival_terminal_id: UUID | None,
    ):
        if origin_airport_id == destination_airport_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Origin and destination airports must be different",
            )

        cls.validate_airport(db, origin_airport_id)
        cls.validate_airport(db, destination_airport_id)

        cls.validate_terminal(
            db,
            departure_terminal_id,
            origin_airport_id,
        )

        cls.validate_terminal(
            db,
            arrival_terminal_id,
            destination_airport_id,
        )

    @staticmethod
    def validate_schedule(departure, arrival):
        if departure is None or arrival is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Departure and arrival times are required",
            )

        if departure.tzinfo is None or arrival.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Flight schedule datetimes must include a timezone",
            )

        if arrival <= departure:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scheduled arrival must be after departure",
            )

    @classmethod
    def create_flight(cls, db: Session, data):
        cls.validate_locations(
            db,
            data.origin_airport_id,
            data.destination_airport_id,
            data.departure_terminal_id,
            data.arrival_terminal_id,
        )

        cls.validate_schedule(
            data.scheduled_departure,
            data.scheduled_arrival,
        )

        existing = FlightRepository.get_by_number_and_departure(
            db,
            data.flight_number,
            data.scheduled_departure,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Flight with this number and departure time already exists",
            )

        flight = Flight(**data.model_dump())

        try:
            return FlightRepository.create(db, flight)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Flight conflicts with an existing record",
            )

    @staticmethod
    def get_flight(db: Session, flight_id: UUID):
        flight = FlightRepository.get_by_id(db, flight_id)

        if not flight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flight not found",
            )

        return flight

    @staticmethod
    def list_flights(
        db: Session,
        skip: int,
        limit: int,
        status_filter=None,
        origin_airport_id=None,
        destination_airport_id=None,
    ):
        return FlightRepository.list(
            db=db,
            skip=skip,
            limit=limit,
            status=status_filter,
            origin_airport_id=origin_airport_id,
            destination_airport_id=destination_airport_id,
        )

    @classmethod
    def update_flight(cls, db: Session, flight_id: UUID, data):
        flight = cls.get_flight(db, flight_id)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided",
            )

        required_fields = {
            "flight_number",
            "airline",
            "flight_type",
            "origin_airport_id",
            "destination_airport_id",
            "scheduled_departure",
            "scheduled_arrival",
            "aircraft_type",
            "capacity",
        }

        for field in required_fields:
            if field in update_data and update_data[field] is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} cannot be null",
                )

        values = {
            "origin_airport_id": flight.origin_airport_id,
            "destination_airport_id": flight.destination_airport_id,
            "departure_terminal_id": flight.departure_terminal_id,
            "arrival_terminal_id": flight.arrival_terminal_id,
            "scheduled_departure": flight.scheduled_departure,
            "scheduled_arrival": flight.scheduled_arrival,
        }
        values.update(update_data)

        cls.validate_locations(
            db,
            values["origin_airport_id"],
            values["destination_airport_id"],
            values["departure_terminal_id"],
            values["arrival_terminal_id"],
        )

        cls.validate_schedule(
            values["scheduled_departure"],
            values["scheduled_arrival"],
        )

        flight_number = update_data.get(
            "flight_number",
            flight.flight_number,
        )
        departure = values["scheduled_departure"]

        duplicate = FlightRepository.get_by_number_and_departure(
            db,
            flight_number,
            departure,
            exclude_id=flight.id,
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another flight already uses this number and departure time",
            )

        try:
            return FlightRepository.update(db, flight, update_data)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Flight update conflicts with an existing record",
            )

    @staticmethod
    def update_flight_status(
        db: Session,
        flight_id: UUID,
        new_status: FlightStatus,
    ):
        flight = FlightService.get_flight(db, flight_id)

        if flight.status == FlightStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancelled flights cannot be updated",
            )

        now = datetime.now(timezone.utc)

        if new_status == FlightStatus.DEPARTED:
            flight.actual_departure = now

        elif new_status == FlightStatus.ARRIVED:
            if flight.status != FlightStatus.DEPARTED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only departed flights can be marked as arrived",
                )

            flight.actual_arrival = now

        try:
            return FlightRepository.update_status(
                db,
                flight,
                new_status,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update flight status",
            )