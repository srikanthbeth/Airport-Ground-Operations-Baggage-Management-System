from uuid import UUID

from sqlalchemy.orm import Session

from models.checkin import CheckIn


def create_checkin(db: Session, checkin: CheckIn):
    db.add(checkin)
    db.flush()
    return checkin


def get_checkin_by_id(db: Session, checkin_id: UUID):
    return db.query(CheckIn).filter(CheckIn.id == checkin_id).first()


def get_checkin_by_passenger_and_flight(
    db: Session,
    passenger_id: UUID,
    flight_id: UUID,
):
    return (
        db.query(CheckIn)
        .filter(
            CheckIn.passenger_id == passenger_id,
            CheckIn.flight_id == flight_id,
        )
        .first()
    )


def get_checkin_by_flight_and_seat(
    db: Session,
    flight_id: UUID,
    seat_number: str,
):
    return (
        db.query(CheckIn)
        .filter(
            CheckIn.flight_id == flight_id,
            CheckIn.seat_number == seat_number,
        )
        .first()
    )


def list_checkins(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    flight_id: UUID | None = None,
    passenger_id: UUID | None = None,
):
    query = db.query(CheckIn)

    if flight_id:
        query = query.filter(CheckIn.flight_id == flight_id)

    if passenger_id:
        query = query.filter(CheckIn.passenger_id == passenger_id)

    return (
        query.order_by(CheckIn.checked_in_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )