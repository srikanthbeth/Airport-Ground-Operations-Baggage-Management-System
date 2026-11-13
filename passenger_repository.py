from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.passenger import Passenger
from core.constants import PassengerStatus


class PassengerRepository:

    @staticmethod
    def create(db: Session, passenger: Passenger):
        db.add(passenger)
        db.commit()
        db.refresh(passenger)
        return passenger

    @staticmethod
    def get_by_id(db: Session, passenger_id: UUID):
        return db.get(Passenger, passenger_id)

    @staticmethod
    def get_by_identification(
        db: Session,
        flight_id: UUID,
        identification_type,
        identification_number: str,
    ):
        return db.query(Passenger).filter(
            Passenger.flight_id == flight_id,
            Passenger.identification_type == identification_type,
            Passenger.identification_number == identification_number,
        ).first()

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        flight_id: UUID | None = None,
        status: PassengerStatus | None = None,
    ):
        query = db.query(Passenger)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Passenger.full_name.ilike(term),
                    Passenger.email.ilike(term),
                    Passenger.phone.ilike(term),
                    Passenger.identification_number.ilike(term),
                )
            )

        if flight_id:
            query = query.filter(Passenger.flight_id == flight_id)

        if status:
            query = query.filter(Passenger.status == status)

        return (
            query.order_by(Passenger.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, passenger: Passenger, data: dict):
        for key, value in data.items():
            setattr(passenger, key, value)

        db.commit()
        db.refresh(passenger)
        return passenger

    @staticmethod
    def cancel(db: Session, passenger: Passenger):
        passenger.status = PassengerStatus.CANCELLED
        db.commit()
        db.refresh(passenger)
        return passenger

    @staticmethod
    def history(
        db: Session,
        identification_type,
        identification_number: str,
    ):
        return (
            db.query(Passenger)
            .filter(
                Passenger.identification_type == identification_type,
                Passenger.identification_number == identification_number,
            )
            .order_by(Passenger.created_at.desc())
            .all()
        )