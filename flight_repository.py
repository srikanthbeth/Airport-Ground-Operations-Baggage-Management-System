from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.flight import Flight
from core.constants import FlightStatus


class FlightRepository:

    @staticmethod
    def create(db: Session, flight: Flight):
        db.add(flight)
        db.commit()
        db.refresh(flight)
        return flight

    @staticmethod
    def get_by_id(db: Session, flight_id: UUID):
        return db.scalar(
            select(Flight).where(Flight.id == flight_id)
        )

    @staticmethod
    def get_by_number_and_departure(
        db: Session,
        flight_number: str,
        scheduled_departure,
        exclude_id: UUID | None = None,
    ):
        query = select(Flight).where(
            Flight.flight_number == flight_number,
            Flight.scheduled_departure == scheduled_departure,
        )

        if exclude_id is not None:
            query = query.where(Flight.id != exclude_id)

        return db.scalar(query)

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: FlightStatus | None = None,
        origin_airport_id: UUID | None = None,
        destination_airport_id: UUID | None = None,
    ):
        query = select(Flight)

        if status is not None:
            query = query.where(Flight.status == status)

        if origin_airport_id is not None:
            query = query.where(
                Flight.origin_airport_id == origin_airport_id
            )

        if destination_airport_id is not None:
            query = query.where(
                Flight.destination_airport_id == destination_airport_id
            )

        query = (
            query
            .order_by(Flight.scheduled_departure.asc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    @staticmethod
    def update(db: Session, flight: Flight, update_data: dict):
        for field, value in update_data.items():
            setattr(flight, field, value)

        db.commit()
        db.refresh(flight)
        return flight

    @staticmethod
    def update_status(db: Session, flight: Flight, status: FlightStatus):
        flight.status = status
        db.commit()
        db.refresh(flight)
        return flight