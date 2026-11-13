from sqlalchemy import select
from sqlalchemy.orm import Session

from models.airport import Airport
from schemas.airport import AirportCreate, AirportUpdate
from core.constants import AirportStatus

def create_airport(db: Session, data: AirportCreate):
    existing = db.scalar(
        select(Airport).where(Airport.code == data.code)
    )
    if existing:
        return None

    airport = Airport(**data.model_dump())
    db.add(airport)
    db.commit()
    db.refresh(airport)
    return airport


def get_airport(db: Session, airport_id):
    return db.get(Airport, airport_id)


def list_airports(db: Session, skip: int = 0, limit: int = 100):
    return db.scalars(
        select(Airport)
        .order_by(Airport.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()


def update_airport(db: Session, airport: Airport, data: AirportUpdate):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(airport, field, value)

    db.commit()
    db.refresh(airport)
    return airport


def deactivate_airport(db: Session, airport: Airport):
    airport.is_active = False
    airport.status = AirportStatus.INACTIVE
    db.commit()
    db.refresh(airport)
    return airport