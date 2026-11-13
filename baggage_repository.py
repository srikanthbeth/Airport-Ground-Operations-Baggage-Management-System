from uuid import UUID

from sqlalchemy.orm import Session

from models.baggage import Baggage


def create_baggage(db: Session, baggage: Baggage):
    db.add(baggage)
    db.flush()
    return baggage


def get_baggage_by_id(db: Session, baggage_id: UUID):
    return (
        db.query(Baggage)
        .filter(Baggage.id == baggage_id)
        .first()
    )


def get_baggage_by_tag(db: Session, baggage_tag: str):
    return (
        db.query(Baggage)
        .filter(Baggage.baggage_tag == baggage_tag)
        .first()
    )


def list_baggage(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    flight_id: UUID | None = None,
    passenger_id: UUID | None = None,
    checkin_id: UUID | None = None,
):
    query = db.query(Baggage)

    if flight_id:
        query = query.filter(Baggage.flight_id == flight_id)

    if passenger_id:
        query = query.filter(Baggage.passenger_id == passenger_id)

    if checkin_id:
        query = query.filter(Baggage.checkin_id == checkin_id)

    return (
        query.order_by(Baggage.registered_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )